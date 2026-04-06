"""Cross-process SearXNG singleton manager.

Ensures exactly ONE SearXNG instance runs, shared across all Python
processes (multiple MCP plugins, kcore consumers, etc).

Priority order:
1. If ``SEARXNG_URL`` env var is set -- use external instance (e.g., Docker on VM)
2. Check discovery file -- reuse existing SearXNG started by another process
3. Start new SearXNG subprocess with file-lock singleton

Resilience features:
- Auto-restart on crash detection (poll() check)
- Force-kill stale processes before restart to avoid port conflicts
- Health check verification after (re)start
- Configurable max restart attempts to prevent restart loops
- Shared instance: multiple processes reuse one SearXNG process
- Cross-platform: Windows ctypes + Linux /proc zombie check
"""

from __future__ import annotations

import asyncio
import atexit
import json as _json
import logging
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Maximum number of restart attempts before giving up.
_MAX_RESTART_ATTEMPTS = 3

# Cooldown between restart attempts (seconds).
_RESTART_COOLDOWN = 2.0

# Health check timeout per probe (seconds).
_HEALTH_CHECK_TIMEOUT = 2.0

# Maximum time to wait for SearXNG to become healthy after start (seconds).
# Cold start (first run) includes package installation + Flask init which can
# take 90-120s on slow machines.
_STARTUP_HEALTH_TIMEOUT = 120.0

# Config directory for web-core.
_CONFIG_DIR = Path.home() / ".web-core"

# Discovery file for sharing SearXNG across multiple processes.
# Contains {pid, port, owner_pid, started_at} of the running SearXNG process.
_DISCOVERY_FILE = _CONFIG_DIR / "searxng_instance.json"

# SearXNG install URL (zip archive avoids git filename issues on Windows).
_SEARXNG_INSTALL_URL = "https://github.com/searxng/searxng/archive/refs/heads/master.zip"

# Minimal SearXNG settings template.
_SETTINGS_TEMPLATE = """\
general:
  debug: false
  instance_name: "web-core SearXNG"

brand: {{}}

server:
  port: {port}
  bind_address: "127.0.0.1"
  secret_key: "{secret_key}"

search:
  safe_search: 0
  default_lang: ""

enabled_plugins:
  - 'Hash plugin'
  - 'Tracker URL remover'

outgoing:
  request_timeout: 5.0
  max_request_timeout: 15.0
  enable_http2: {enable_http2}

engines:
  - name: google
    engine: google
    shortcut: go
  - name: bing
    engine: bing
    shortcut: bi
  - name: duckduckgo
    engine: duckduckgo
    shortcut: ddg
  - name: brave
    engine: brave
    shortcut: br
  - name: wikipedia
    engine: wikipedia
    shortcut: wp
"""

# Module-level process reference for cleanup.
_searxng_process: subprocess.Popen | None = None
_searxng_port: int | None = None
_restart_count: int = 0
_last_restart_time: float = 0.0

# Shared instance tracking.
_is_owner: bool = False  # True if this instance started the SearXNG process
_startup_lock: asyncio.Lock | None = None  # Lazy-init to avoid event loop issues


def _get_startup_lock() -> asyncio.Lock:
    """Get or create the startup lock (lazy init for event loop safety)."""
    global _startup_lock
    if _startup_lock is None:
        _startup_lock = asyncio.Lock()
    return _startup_lock


# ---------------------------------------------------------------------------
# Shared instance discovery
# ---------------------------------------------------------------------------


def _is_pid_alive(pid: int) -> bool:  # pragma: no cover
    """Check if a process with the given PID is alive (not zombie).

    On Windows, uses ctypes ``OpenProcess`` since ``os.kill(pid, 0)`` does
    not work for non-child processes.  On Linux, additionally checks
    ``/proc/{pid}/status`` for zombie state.
    """
    if pid <= 0:
        return False

    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
            return True
        return False

    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False

    # On Linux, check /proc/{pid}/status for zombie state.
    # os.kill(pid, 0) succeeds for zombie processes (PID still in table),
    # but they are defunct and cannot serve requests.
    try:
        status_path = Path(f"/proc/{pid}/status")
        if status_path.exists():
            for line in status_path.read_text().splitlines():
                if line.startswith("State:"):
                    if "Z" in line.split(":")[1]:
                        logger.debug("PID %d is a zombie process", pid)
                        return False
                    break
    except OSError:
        pass

    return True


def _read_discovery() -> dict | None:
    """Read SearXNG discovery file.

    Returns dict with ``{pid, port, owner_pid, started_at}`` or ``None``.
    """
    try:
        if _DISCOVERY_FILE.exists():
            data = _json.loads(_DISCOVERY_FILE.read_text())
            if isinstance(data, dict) and "port" in data and "pid" in data:
                return data
    except Exception:
        pass
    return None


def _write_discovery(port: int, pid: int) -> None:
    """Write SearXNG discovery file for other instances to find."""
    try:
        _DISCOVERY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DISCOVERY_FILE.parent.chmod(0o700)
        content = _json.dumps(
            {
                "pid": pid,
                "port": port,
                "owner_pid": os.getpid(),
                "started_at": time.time(),
            }
        )
        fd = os.open(_DISCOVERY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e: # pragma: no cover
        logger.debug("Failed to write discovery file: %s", e)


def _remove_discovery() -> None:
    """Remove stale discovery file."""
    try:
        if _DISCOVERY_FILE.exists():
            _DISCOVERY_FILE.unlink()
    except Exception: # pragma: no cover
        pass


async def _quick_health_check(url: str, retries: int = 3) -> bool:
    """Health check against a SearXNG URL with retries.

    Reuses a single ``AsyncClient`` across retries to avoid creating/tearing
    down TCP connections on each attempt.  Retries with exponential backoff
    (0.5s, 1s, 2s) and a generous per-probe timeout.
    """
    async with httpx.AsyncClient() as client:
        for attempt in range(retries):
            try:
                response = await client.get(
                    f"{url}/healthz",
                    headers={
                        "X-Real-IP": "127.0.0.1",
                        "X-Forwarded-For": "127.0.0.1",
                    },
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return True
            except Exception: # pragma: no cover
                pass
            if attempt < retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
    return False


async def _try_reuse_existing() -> str | None:
    """Try to reuse a SearXNG instance started by another process.

    Reads the discovery file, verifies the process is alive and healthy,
    and returns the URL if reusable.
    """
    data = await asyncio.to_thread(_read_discovery)
    if not data:
        return None

    port = data.get("port")
    pid = data.get("pid")
    if not port or not pid:
        return None

    # Check if the SearXNG process is still alive
    if not _is_pid_alive(pid):
        logger.debug("Discovery file points to dead process (PID=%d), cleaning up", pid)
        _remove_discovery()
        return None

    # Health check the existing instance
    url = f"http://127.0.0.1:{port}"
    if await _quick_health_check(url):
        return url

    logger.debug("Discovery file points to unhealthy instance at %s, cleaning up", url)
    _remove_discovery()
    return None


# ---------------------------------------------------------------------------
# Port management
# ---------------------------------------------------------------------------


def _find_available_port(start_port: int, max_tries: int = 50) -> int:
    """Find an available port, randomizing offset to avoid collisions.

    When multiple processes start concurrently, they all call this function
    at roughly the same time.  A deterministic port scan can hit a TOCTOU
    race: two instances both see the same port as free, then one fails to
    bind.  Randomizing the starting offset avoids this.

    Raises ``RuntimeError`` if no port is available within ``max_tries``.
    """
    import random

    offsets = list(range(max_tries))
    random.shuffle(offsets)

    for offset in offsets:
        port = start_port + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue

    msg = f"No available port found in range {start_port}-{start_port + max_tries - 1}"
    raise RuntimeError(msg)


async def _wait_for_service(url: str, timeout: float = _STARTUP_HEALTH_TIMEOUT) -> bool:
    """Wait for SearXNG service to be healthy via async HTTP check."""
    start_time = time.time()
    logger.debug("Waiting for SearXNG at %s...", url)

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(
                    f"{url}/healthz",
                    headers={
                        "X-Real-IP": "127.0.0.1",
                        "X-Forwarded-For": "127.0.0.1",
                    },
                    timeout=_HEALTH_CHECK_TIMEOUT,
                )
                if response.status_code == 200:
                    return True
            except Exception: # pragma: no cover
                pass
            await asyncio.sleep(1.0)
    return False


# ---------------------------------------------------------------------------
# SearXNG installation
# ---------------------------------------------------------------------------


def _get_pip_command() -> list[str]:
    """Get cross-platform pip install command.

    Priority:
    1. ``uv pip`` (for uv environments -- no pip module)
    2. ``pip`` (for traditional venvs)
    3. ``python -m pip`` (fallback)
    """
    uv_path = shutil.which("uv")
    if uv_path:
        return [uv_path, "pip", "install", "--python", sys.executable]

    pip_path = shutil.which("pip")
    if pip_path:
        return [pip_path, "install"]

    return [sys.executable, "-m", "pip", "install"]


def _is_searxng_installed() -> bool:
    """Check if the SearXNG Python package is fully installed.

    Uses ``importlib.util.find_spec`` instead of a direct import to avoid
    executing module-level code in ``searx.webapp`` which calls ``sys.exit(1)``
    when ``secret_key`` is unchanged (the default ``ultrasecretkey``).
    """
    import importlib.util

    try:
        return importlib.util.find_spec("searx.webapp") is not None
    except ModuleNotFoundError:
        return False


def _install_searxng() -> bool:  # pragma: no cover
    """Install SearXNG from GitHub zip archive.

    Uses zip URL instead of ``git+`` to avoid filename issues on some
    platforms. Pre-installs build dependencies before SearXNG.

    Returns ``True`` if installation succeeded.
    """
    logger.info("Installing SearXNG from GitHub (first run)...")

    try:
        pip_cmd = _get_pip_command()
        logger.debug("Using pip command: %s", pip_cmd)

        # Pre-install build dependencies required by SearXNG.
        # On Windows, also install waitress (production WSGI server) to replace
        # Flask's Werkzeug dev server which deadlocks under concurrent requests.
        build_deps = ["msgspec", "setuptools", "wheel", "pyyaml"]
        if sys.platform == "win32":
            build_deps.append("waitress>=3.0.0")

        logger.debug("Installing SearXNG build dependencies...")
        deps_result = subprocess.run(
            [*pip_cmd, "--quiet", *build_deps],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if deps_result.returncode != 0:
            logger.error("Build deps installation failed: %s", deps_result.stderr[:500])
            return False

        # Install SearXNG with --no-build-isolation (uses pre-installed deps).
        result = subprocess.run(
            [*pip_cmd, "--quiet", "--no-build-isolation", _SEARXNG_INSTALL_URL],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            logger.info("SearXNG installed successfully")
            return True

        logger.error("SearXNG installation failed: %s", result.stderr[:500])
        return False

    except subprocess.TimeoutExpired:
        logger.error("SearXNG installation timed out")
        return False
    except Exception as e:
        logger.error("Failed to install SearXNG: %s", e)
        return False


# ---------------------------------------------------------------------------
# SearXNG settings
# ---------------------------------------------------------------------------


def _get_settings_path(port: int) -> Path:
    """Get path to SearXNG settings file.

    Uses per-process file to avoid write conflicts when multiple
    server instances run simultaneously.  Generates settings inline
    from the bundled template.
    """
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_DIR.chmod(0o700)

    # Per-process settings file (avoids race condition between instances).
    settings_file = _CONFIG_DIR / f"searxng_settings_{os.getpid()}.yml"

    secret = secrets.token_hex(32)
    enable_http2 = "false" if sys.platform == "win32" else "true"

    content = _SETTINGS_TEMPLATE.format(
        port=port,
        secret_key=secret,
        enable_http2=enable_http2,
    )

    fd = os.open(settings_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug("SearXNG settings written to: %s", settings_file)

    return settings_file


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------


def _sigterm_then_kill(pid: int, label: str = "") -> bool:  # pragma: no cover
    """Send SIGTERM to a PID, wait briefly, then SIGKILL if needed.

    Returns ``True`` if the process was successfully terminated.
    """
    tag = f" ({label})" if label else ""
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return True  # Already dead or inaccessible

    # Wait up to 3 seconds for graceful exit.
    for _ in range(30):
        try:
            os.kill(pid, 0)  # Check if alive
        except ProcessLookupError:
            logger.debug("Process PID=%d%s terminated gracefully", pid, tag)
            return True
        except PermissionError:
            return True
        time.sleep(0.1)

    # Force kill.
    try:
        os.kill(pid, signal.SIGKILL)
        logger.debug("Process PID=%d%s force-killed", pid, tag)
        return True
    except (ProcessLookupError, PermissionError):
        return True


def _force_kill_process(proc: subprocess.Popen) -> None:  # pragma: no cover
    """Force-kill a subprocess and all its children.

    Tries graceful SIGTERM first, then SIGKILL after a short timeout.
    On Unix, kills the entire process group to avoid orphaned children.
    """
    if proc.poll() is not None:
        return  # Already dead

    pid = proc.pid
    logger.debug("Force-killing SearXNG process (PID=%d)...", pid)

    try:
        if sys.platform != "win32":
            # Kill the entire process group on Unix.
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                proc.terminate()

            try:
                proc.wait(timeout=3)
                logger.debug("SearXNG process (PID=%d) terminated gracefully", pid)
                return
            except subprocess.TimeoutExpired:
                pass

            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()

            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                logger.warning("SearXNG process (PID=%d) could not be killed", pid)
        else:
            _sigterm_then_kill(pid, "SearXNG")
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception as e:
        logger.debug("Error killing SearXNG process: %s", e)


def _kill_stale_port_process(port: int) -> None:  # pragma: no cover
    """Kill any process still holding the target port.

    This prevents 'address already in use' errors when restarting
    after a crash that left a zombie process behind.
    """
    if not isinstance(port, int) or not (1 <= port <= 65535):
        return

    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                if f"127.0.0.1:{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid_str = parts[-1]
                    try:
                        pid = int(pid_str)
                        if pid > 0:
                            _sigterm_then_kill(pid, f"stale port {port}")
                    except (ValueError, ProcessLookupError, PermissionError) as e:
                        logger.debug("Could not kill process %s on port %d: %s", pid_str, port, e)
        except Exception as e:
            logger.debug("Error finding processes on port %d using netstat: %s", port, e)
    else:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                for pid_str in result.stdout.strip().splitlines():
                    try:
                        pid = int(pid_str.strip())
                        if pid > 0 and pid != os.getpid():
                            _sigterm_then_kill(pid, f"stale port {port}")
                    except (ValueError, ProcessLookupError, PermissionError) as e:
                        logger.debug("Could not kill process %s on port %d: %s", pid_str, port, e)
        except FileNotFoundError:
            # lsof not available, try fuser.
            try:
                subprocess.run(
                    ["fuser", "-k", f"{port}/tcp"],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    timeout=5,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                logger.debug("Could not free port %d using fuser: %s", port, e)
        except Exception as e:
            logger.debug("Error finding processes on port %d using lsof: %s", port, e)


def _get_process_kwargs() -> dict:  # pragma: no cover
    """Get platform-specific subprocess kwargs."""
    if sys.platform != "win32":
        return {"preexec_fn": os.setsid}
    return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}


def _cleanup_process() -> None:  # pragma: no cover
    """Cleanup SearXNG subprocess and per-process settings file on exit.

    Only kills SearXNG if this instance owns it (started it).
    Non-owner instances just clear their local references.
    """
    global _searxng_process, _searxng_port, _is_owner
    if _searxng_process is not None:
        if _is_owner:
            try:
                logger.debug("Stopping owned SearXNG subprocess...")
                _force_kill_process(_searxng_process)
                logger.debug("SearXNG subprocess stopped")
            except Exception as e:
                logger.debug("Error stopping SearXNG: %s", e)
            _remove_discovery()
        else:
            logger.debug("Not owner, leaving SearXNG subprocess running")
        _searxng_process = None
        _searxng_port = None
        _is_owner = False

    # Cleanup per-process settings file.
    try:
        pid_settings = _CONFIG_DIR / f"searxng_settings_{os.getpid()}.yml"
        if pid_settings.exists():
            pid_settings.unlink()
    except Exception:
        pass


def _is_process_alive() -> bool:
    """Check if the SearXNG subprocess is still running."""
    return _searxng_process is not None and _searxng_process.poll() is None


# ---------------------------------------------------------------------------
# Subprocess start
# ---------------------------------------------------------------------------


async def _start_searxng_subprocess(start_port: int) -> str | None:  # pragma: no cover
    """Start a fresh SearXNG subprocess.

    Returns the URL if started successfully, ``None`` on failure.
    Handles port conflicts by killing stale processes first.
    Writes discovery file so other processes can reuse this SearXNG.
    """
    global _searxng_process, _searxng_port, _is_owner

    # Kill any existing process first.
    if _searxng_process is not None:
        _force_kill_process(_searxng_process)
        _searxng_process = None
        _searxng_port = None

    try:
        # Find available port.
        port = await asyncio.to_thread(_find_available_port, start_port)
        if port != start_port:
            logger.info("Port %d in use, using %d", start_port, port)

        # Kill any stale process on the target port.
        await asyncio.to_thread(_kill_stale_port_process, port)
        await asyncio.sleep(0.5)

        _searxng_port = port

        # Write settings with correct port.
        settings_path = await asyncio.to_thread(_get_settings_path, port)

        # Build environment for SearXNG.
        env = os.environ.copy()
        env["SEARXNG_SETTINGS_PATH"] = str(settings_path)

        logger.info("Starting SearXNG on port %d...", port)

        # On Windows, stderr=PIPE without a reader causes a deadlock.
        stderr_target = subprocess.DEVNULL if sys.platform == "win32" else subprocess.PIPE

        # On Windows, use waitress instead of Flask's Werkzeug dev server.
        if sys.platform == "win32":
            cmd = [
                sys.executable,
                "-c",
                (
                    "from waitress import serve;"
                    " from searx.webapp import app;"
                    f" serve(app,"
                    f" host='127.0.0.1', port={port},"
                    f" threads=8, channel_timeout=120,"
                    f" cleanup_interval=30)"
                ),
            ]
        else:
            cmd = [sys.executable, "-m", "searx.webapp"]

        _searxng_process = await asyncio.to_thread(
            lambda: subprocess.Popen(
                cmd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr_target,
                **_get_process_kwargs(),
            )
        )

        # Register cleanup (idempotent -- atexit deduplicates internally).
        atexit.register(_cleanup_process)

        url = f"http://127.0.0.1:{port}"

        # Wait for SearXNG to be healthy.
        if await _wait_for_service(url, timeout=_STARTUP_HEALTH_TIMEOUT):
            logger.info("SearXNG ready at %s", url)
            await asyncio.to_thread(_write_discovery, port, _searxng_process.pid)
            _is_owner = True
            return url

        # Health check timed out.
        logger.warning("SearXNG started but not healthy at %s", url)
        if _searxng_process.poll() is not None:
            if _searxng_process.stderr:
                stderr_raw = await asyncio.to_thread(_searxng_process.stderr.read)
                stderr = stderr_raw.decode()
            else:
                stderr = ""
            logger.error("SearXNG process exited during startup: %s", stderr[:500])
        else:
            logger.warning(
                "SearXNG process (PID=%d) alive but not serving, killing stuck process",
                _searxng_process.pid,
            )
            _force_kill_process(_searxng_process)
        _searxng_process = None
        _searxng_port = None
        return None

    except Exception as e:
        logger.error("Failed to start SearXNG subprocess: %s", e)
        if _searxng_process is not None:
            _force_kill_process(_searxng_process)
            _searxng_process = None
            _searxng_port = None
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def ensure_searxng(
    url: str | None = None,
    auto_start: bool = True,
    start_port: int = 18888,
) -> str:
    """Ensure SearXNG is available. Returns URL.

    Priority:
    1. Explicit ``url`` parameter or ``SEARXNG_URL`` env var -- use directly
    2. Discovery file -- reuse existing SearXNG started by another process
    3. Auto-start a new SearXNG subprocess (if ``auto_start=True``)

    Parameters
    ----------
    url:
        Explicit URL to use (skip auto-start). Falls back to
        ``SEARXNG_URL`` env var.
    auto_start:
        If ``False``, only check existing instances -- never start new ones.
    start_port:
        Base port for auto-start (default 18888).

    Returns
    -------
    str
        The URL of the running SearXNG instance.

    Raises
    ------
    RuntimeError
        If no SearXNG instance is available and auto-start is disabled
        or all start attempts failed.
    """
    # 1. Explicit URL or env var.
    effective_url = url or os.environ.get("SEARXNG_URL")
    if effective_url:
        logger.info("Using external SearXNG at %s", effective_url)
        return effective_url.rstrip("/")

    # Serialize startup attempts to prevent concurrent starts.
    async with _get_startup_lock():
        return await _ensure_searxng_locked(auto_start=auto_start, start_port=start_port)


async def _ensure_searxng_locked(*, auto_start: bool, start_port: int) -> str:
    """Inner ensure_searxng logic, called under lock."""
    global _searxng_process, _searxng_port

    # Fast path: our own process is alive and port is known.
    if _is_process_alive() and _searxng_port is not None and _searxng_process is not None:
        url = f"http://127.0.0.1:{_searxng_port}"
        if await _quick_health_check(url, retries=1):
            logger.debug("SearXNG already running at %s", url)
            return url
        # Process alive but not serving -- kill and restart.
        logger.warning(
            "SearXNG process alive (PID=%d) but not healthy at %s, killing",
            _searxng_process.pid,
            url,
        )
        _force_kill_process(_searxng_process)
        _searxng_process = None
        _searxng_port = None

    # Try reusing existing SearXNG from another process.
    reused_url = await _try_reuse_existing()
    if reused_url:
        logger.info("Reusing existing SearXNG instance at %s", reused_url)
        return reused_url

    if not auto_start:
        msg = "No running SearXNG instance found and auto_start is disabled"
        raise RuntimeError(msg)

    # Process is dead or not started -- need to (re)start.
    return await _handle_restart_and_start(start_port=start_port)


async def _handle_restart_and_start(*, start_port: int) -> str:  # pragma: no cover
    """Detect crashes, manage restart budget, install if needed, and start.

    Returns the local SearXNG URL on success.

    Raises ``RuntimeError`` if all attempts fail.
    """
    global _searxng_process, _searxng_port, _restart_count, _last_restart_time

    # Crash detection -- log diagnostics and clear stale process reference.
    if _searxng_process is not None:
        exit_code = _searxng_process.poll()
        stderr_output = ""
        if _searxng_process.stderr:
            try:
                stderr_raw = await asyncio.to_thread(_searxng_process.stderr.read)
                stderr_output = stderr_raw.decode(errors="replace")[:500]
            except Exception:
                pass
        logger.warning("SearXNG process crashed (exit_code=%s). stderr: %s", exit_code, stderr_output)
        _searxng_process = None

    # Reset restart counter if enough time has passed since last restart.
    now = time.time()
    if now - _last_restart_time > 300:  # 5 minutes
        _restart_count = 0

    # Check restart budget.
    if _restart_count >= _MAX_RESTART_ATTEMPTS:
        msg = f"SearXNG restart limit reached ({_MAX_RESTART_ATTEMPTS} attempts)"
        raise RuntimeError(msg)

    # Ensure SearXNG package is installed.
    if not await asyncio.to_thread(_is_searxng_installed) and not await asyncio.to_thread(_install_searxng):
        msg = "SearXNG installation failed"
        raise RuntimeError(msg)

    # Attempt to start with cooldown between restarts.
    if _restart_count > 0:
        cooldown = _RESTART_COOLDOWN * _restart_count
        logger.info("Waiting %.1fs before SearXNG restart attempt %d...", cooldown, _restart_count + 1)
        await asyncio.sleep(cooldown)

    _restart_count += 1
    _last_restart_time = time.time()

    url = await _start_searxng_subprocess(start_port)
    if url is not None:
        _restart_count = 0
        return url

    msg = "SearXNG start failed after all attempts"
    raise RuntimeError(msg)


def shutdown_searxng() -> None: # pragma: no cover
    """Stop SearXNG if we started it.

    Safe to call multiple times.  Only kills the process if this Python
    process owns it (i.e. started it).
    """
    _cleanup_process()
