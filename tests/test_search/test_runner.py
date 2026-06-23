"""Tests for web_core.search.runner -- SearXNG cross-process singleton manager.

All subprocess/network calls are mocked. No real SearXNG processes.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import httpx
import pytest

from web_core.search import ensure_searxng, shutdown_searxng
from web_core.search.runner import (
    _SETTINGS_TEMPLATE,
    _cleanup_process,
    _find_available_port,
    _get_docker_lock,
    _get_pip_command,
    _get_process_kwargs,
    _get_settings_path,
    _get_startup_lock,
    _handle_restart_and_start,
    _install_searxng,
    _is_pid_alive,
    _is_process_alive,
    _is_searxng_installed,
    _kill_stale_port_process,
    _quick_health_check,
    _read_discovery,
    _remove_discovery,
    _start_docker_searxng,
    _try_reuse_existing,
    _wait_for_service,
    _write_discovery,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# _is_pid_alive
# ===========================================================================


class TestIsPidAlive:
    def test_current_process_is_alive(self):
        """os.getpid() should always be alive."""
        assert _is_pid_alive(os.getpid()) is True

    def test_pid_zero_is_not_alive(self):
        """PID 0 (kernel/idle) should not be considered alive."""
        assert _is_pid_alive(0) is False

    def test_negative_pid_is_not_alive(self):
        """Negative PIDs are invalid and should not be alive."""
        assert _is_pid_alive(-1) is False
        assert _is_pid_alive(-9999) is False

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only zombie check")
    def test_zombie_process_detected(self, tmp_path):
        """A zombie process on Linux should be detected as not alive."""
        # Mock /proc/{pid}/status with zombie state
        pid = 99999
        with (
            patch("os.kill") as mock_kill,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="State:\tZ (zombie)\n"),
        ):
            mock_kill.return_value = None  # os.kill succeeds (PID in table)
            assert _is_pid_alive(pid) is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only ctypes check")
    def test_windows_dead_process(self):
        """A non-existent PID on Windows should return False."""
        # PID 4000000 is very unlikely to exist
        assert _is_pid_alive(4000000) is False

    def test_very_large_pid_not_alive(self):
        """An absurdly large PID should not be alive."""
        assert _is_pid_alive(999999999) is False


# ===========================================================================
# Discovery file management
# ===========================================================================


class TestDiscovery:
    def test_read_discovery_no_file(self, tmp_discovery):
        """Returns None when discovery file doesn't exist."""
        assert _read_discovery() is None

    def test_write_and_read_discovery(self, tmp_discovery):
        """Write then read round-trips correctly."""
        _write_discovery(18888, 12345)
        data = _read_discovery()
        assert data is not None
        assert data["port"] == 18888
        assert data["pid"] == 12345
        assert data["owner_pid"] == os.getpid()
        assert "started_at" in data

    def test_read_discovery_invalid_json(self, tmp_discovery):
        """Returns None on malformed JSON."""
        tmp_discovery.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(tmp_discovery, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("not json")
        assert _read_discovery() is None

    def test_read_discovery_missing_keys(self, tmp_discovery):
        """Returns None when required keys are missing."""
        tmp_discovery.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(tmp_discovery, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps({"port": 8080}))  # Missing pid
        assert _read_discovery() is None

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions not supported on Windows")
    def test_read_discovery_insecure_permissions(self, tmp_discovery):
        """Returns None when discovery file has insecure permissions."""
        _write_discovery(18888, 12345)
        os.chmod(tmp_discovery, 0o644)
        assert _read_discovery() is None

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions not supported on Windows")
    def test_write_discovery_secure_permissions(self, tmp_discovery):
        """Discovery file is created with 0o600 permissions."""
        _write_discovery(18888, 12345)
        assert (os.stat(tmp_discovery).st_mode & 0o777) == 0o600

    def test_remove_discovery(self, tmp_discovery):
        """Removes the discovery file if it exists."""
        _write_discovery(18888, 12345)
        assert tmp_discovery.exists()
        _remove_discovery()
        assert not tmp_discovery.exists()

    def test_remove_discovery_nonexistent(self, tmp_discovery):
        """Does not raise when file doesn't exist."""
        _remove_discovery()  # Should not raise


# ===========================================================================
# _quick_health_check
# ===========================================================================


class TestQuickHealthCheck:
    async def test_healthy_instance(self):
        """Returns True when /healthz returns 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("web_core.search.runner.safe_httpx_client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _quick_health_check("http://127.0.0.1:18888")
            assert result is True

    async def test_unhealthy_instance(self):
        """Returns False when all retries fail."""
        with patch("web_core.search.runner.safe_httpx_client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _quick_health_check("http://127.0.0.1:18888", retries=1)
            assert result is False

    async def test_retries_on_failure_then_succeeds(self):
        """Retries and returns True on eventual success."""
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        mock_ok = MagicMock()
        mock_ok.status_code = 200

        with patch("web_core.search.runner.safe_httpx_client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[mock_fail, mock_ok])
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _quick_health_check("http://127.0.0.1:18888", retries=2)
            assert result is True


# ===========================================================================
# _try_reuse_existing
# ===========================================================================


class TestTryReuseExisting:
    async def test_returns_url_if_instance_running(self, tmp_discovery):
        """Returns URL if discovery file points to a healthy instance."""
        _write_discovery(18888, os.getpid())

        with patch("web_core.search.runner._quick_health_check", new_callable=AsyncMock, return_value=True):
            url = await _try_reuse_existing()
            assert url == "http://127.0.0.1:18888"

    async def test_returns_none_if_not_running(self, tmp_discovery):
        """Returns None if health check fails."""
        _write_discovery(18888, os.getpid())

        with patch("web_core.search.runner._quick_health_check", new_callable=AsyncMock, return_value=False):
            url = await _try_reuse_existing()
            assert url is None

    async def test_returns_none_if_no_discovery(self, tmp_discovery):
        """Returns None when discovery file doesn't exist."""
        url = await _try_reuse_existing()
        assert url is None

    async def test_returns_none_if_pid_dead(self, tmp_discovery):
        """Returns None and cleans up if PID in discovery is dead."""
        _write_discovery(18888, 999999999)

        with patch("web_core.search.runner._is_pid_alive", return_value=False):
            url = await _try_reuse_existing()
            assert url is None
            assert not tmp_discovery.exists()

    async def test_returns_none_if_missing_port(self, tmp_discovery):
        """Returns None if discovery data is missing port."""
        tmp_discovery.parent.mkdir(parents=True, exist_ok=True)
        tmp_discovery.write_text(json.dumps({"pid": 1234}))  # Missing port
        url = await _try_reuse_existing()
        assert url is None


# ===========================================================================
# _find_available_port
# ===========================================================================


class TestFindAvailablePort:
    def test_returns_valid_port(self):
        """Returns a valid non-privileged port."""
        port = _find_available_port(18888, max_tries=50)
        assert 1024 <= port <= 65535

    def test_raises_if_no_port_available(self):
        """Raises RuntimeError if all ports in range are in use."""
        with patch("socket.socket") as mock_socket_cls:
            mock_socket = MagicMock()
            mock_socket.__enter__ = MagicMock(return_value=mock_socket)
            mock_socket.__exit__ = MagicMock(return_value=False)
            mock_socket.bind = MagicMock(side_effect=OSError("Address in use"))
            mock_socket_cls.return_value = mock_socket

            with pytest.raises(RuntimeError, match="No available port found"):
                _find_available_port(18888, max_tries=5)

    def test_skips_used_ports(self):
        """Finds a free port even if some are in use."""
        # Bind a port to make it unavailable, then check the function works
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            _ = s.getsockname()[1]

        # The function should still find a port (just not the used one)
        port = _find_available_port(18888, max_tries=50)
        assert isinstance(port, int)
        assert port >= 18888

    def test_find_available_port_invalid_range(self):
        """Covers the case where start_port is outside [1024, 65535]."""
        # Low port
        port = _find_available_port(80, max_tries=5)
        assert 49152 <= port <= 65535

        # High port
        port = _find_available_port(70000, max_tries=5)
        assert 49152 <= port <= 65535

    def test_find_available_port_retries_on_bind_error(self):
        """Covers OSError during s.bind()."""
        with patch("socket.socket") as mock_socket_cls:
            # First mock socket fails on bind, second succeeds
            mock_s1 = MagicMock()
            mock_s1.__enter__.return_value = mock_s1
            mock_s1.bind.side_effect = OSError("First port taken")

            mock_s2 = MagicMock()
            mock_s2.__enter__.return_value = mock_s2
            # mock_s2.bind succeeds (default)

            mock_socket_cls.side_effect = [mock_s1, mock_s2]

            port = _find_available_port(18888, max_tries=5)
            assert isinstance(port, int)
            assert mock_socket_cls.call_count == 2

    def test_find_available_port_retries_on_socket_creation_error(self):
        """Covers OSError during socket.socket() instantiation."""
        with patch("socket.socket") as mock_socket_cls:
            # First call to socket.socket() fails
            mock_s2 = MagicMock()
            mock_s2.__enter__.return_value = mock_s2

            mock_socket_cls.side_effect = [OSError("Socket creation failed"), mock_s2]

            port = _find_available_port(18888, max_tries=5)
            assert isinstance(port, int)
            assert mock_socket_cls.call_count == 2


# ===========================================================================
# _wait_for_service
# ===========================================================================


class TestWaitForService:
    async def test_returns_true_when_healthy(self):
        """Returns True immediately when service is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("web_core.search.runner.safe_httpx_client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _wait_for_service("http://127.0.0.1:18888", timeout=2.0)
            assert result is True

    async def test_returns_false_on_timeout(self):
        """Returns False when service never becomes healthy."""
        with patch("web_core.search.runner.safe_httpx_client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _wait_for_service("http://127.0.0.1:18888", timeout=0.5)
            assert result is False


# ===========================================================================
# _is_searxng_installed / _install_searxng
# ===========================================================================


class TestSearxngInstallation:
    def test_is_searxng_installed_true(self):
        """Returns True when searx.webapp is importable."""
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            assert _is_searxng_installed() is True

    def test_is_searxng_installed_false(self):
        """Returns False when searx.webapp is not found."""
        with patch("importlib.util.find_spec", return_value=None):
            assert _is_searxng_installed() is False

    def test_is_searxng_installed_module_not_found(self):
        """Returns False when find_spec raises ModuleNotFoundError."""
        with patch("importlib.util.find_spec", side_effect=ModuleNotFoundError):
            assert _is_searxng_installed() is False

    def test_install_searxng_success(self):
        """Returns True when pip install succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("web_core.search.runner._get_pip_command", return_value=["pip", "install"]),
        ):
            assert _install_searxng() is True

    def test_install_searxng_failure(self):
        """Returns False when pip install fails."""
        mock_ok = MagicMock()
        mock_ok.returncode = 0
        mock_ok.stderr = ""

        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_fail.stderr = "error: could not build"

        with (
            patch("subprocess.run", side_effect=[mock_ok, mock_fail]),
            patch("web_core.search.runner._get_pip_command", return_value=["pip", "install"]),
        ):
            assert _install_searxng() is False

    def test_install_searxng_timeout(self):
        """Returns False when pip install times out."""
        with (
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pip", timeout=120)),
            patch("web_core.search.runner._get_pip_command", return_value=["pip", "install"]),
        ):
            assert _install_searxng() is False

    def test_install_searxng_deps_failure(self):
        """Returns False when build deps installation fails."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_fail.stderr = "dependency error"

        with (
            patch("subprocess.run", return_value=mock_fail),
            patch("web_core.search.runner._get_pip_command", return_value=["pip", "install"]),
        ):
            assert _install_searxng() is False


# ===========================================================================
# _get_pip_command
# ===========================================================================


class TestGetPipCommand:
    def test_prefers_uv(self):
        """Uses uv pip when uv is available."""
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/uv" if x == "uv" else None):
            cmd = _get_pip_command()
            assert cmd[0] == "/usr/bin/uv"
            assert "pip" in cmd
            assert "--python" in cmd

    def test_uses_pip(self):
        """Uses pip when uv is not available."""
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/pip" if x == "pip" else None):
            cmd = _get_pip_command()
            assert cmd == ["/usr/bin/pip", "install"]

    def test_fallback_python_m_pip(self):
        """Falls back to python -m pip."""
        with patch("shutil.which", return_value=None):
            cmd = _get_pip_command()
            assert cmd == [sys.executable, "-m", "pip", "install"]


# ===========================================================================
# _get_settings_path
# ===========================================================================


class TestGetSettingsPath:
    def test_creates_settings_file(self, tmp_config_dir):
        """Creates a per-process settings file with correct port and secret."""
        path = _get_settings_path(18888)
        assert path.exists()
        content = path.read_text()
        assert "port: 18888" in content
        assert "web-core SearXNG" in content
        # Secret should be a hex string (not the template placeholder)
        assert "{secret_key}" not in content
        assert "{port}" not in content

    def test_per_process_filename(self, tmp_config_dir):
        """Settings file is securely named with a prefix and correct suffix."""
        path = _get_settings_path(18888)
        assert path.name.startswith("searxng_settings_")
        assert path.name.endswith(".yml")

    def test_http2_disabled_on_windows(self, tmp_config_dir):
        """HTTP/2 is disabled on Windows to avoid deadlocks."""
        with patch("sys.platform", "win32"):
            path = _get_settings_path(18888)
            content = path.read_text()
            assert "enable_http2: false" in content

    def test_http2_enabled_on_linux(self, tmp_config_dir):
        """HTTP/2 is enabled on non-Windows platforms."""
        with patch("sys.platform", "linux"):
            path = _get_settings_path(18888)
            content = path.read_text()
            assert "enable_http2: true" in content


# ===========================================================================
# _get_process_kwargs
# ===========================================================================


class TestGetProcessKwargs:
    def test_unix_uses_start_new_session(self):
        """On Unix, uses start_new_session=True for process group management."""
        with patch("sys.platform", "linux"), patch("os.getuid", return_value=1000, create=True):
            kwargs = _get_process_kwargs()
            assert kwargs.get("start_new_session") is True
            assert "preexec_fn" not in kwargs

    def test_unix_root_drops_privileges(self):
        """On Unix as root, drops privileges to 'nobody'."""
        mock_pw = MagicMock()
        mock_pw.pw_uid = 65534
        mock_pw.pw_gid = 65534
        mock_pwd = MagicMock()
        mock_pwd.getpwnam.return_value = mock_pw
        with (
            patch("sys.platform", "linux"),
            patch("os.getuid", return_value=0, create=True),
            patch.dict("sys.modules", {"pwd": mock_pwd}),
        ):
            kwargs = _get_process_kwargs()
            assert kwargs["user"] == 65534
            assert kwargs["group"] == 65534

    @pytest.mark.skipif(sys.platform != "win32", reason="CREATE_NEW_PROCESS_GROUP only exists on Windows")
    def test_windows_uses_creation_flags(self):
        """On Windows, uses CREATE_NEW_PROCESS_GROUP."""
        with patch("sys.platform", "win32"):
            kwargs = _get_process_kwargs()
            assert "creationflags" in kwargs
            assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP


# ===========================================================================
# _is_process_alive
# ===========================================================================


class TestGetSecureEnv:
    def test_filters_environment(self):
        """Only whitelisted environment variables are kept."""
        from web_core.search.runner import _get_secure_env

        settings_path = Path("/tmp/settings.yml")
        with patch.dict("os.environ", {"PATH": "/bin", "MY_VAR": "discarded_value", "PYTHONPATH": "src"}):
            env = _get_secure_env(settings_path)
            assert env["PATH"] == "/bin"
            assert env["PYTHONPATH"] == "src"
            assert "MY_VAR" not in env
            assert env["SEARXNG_SETTINGS_PATH"] == str(settings_path)


class TestIsProcessAlive:
    def test_returns_false_when_no_process(self):
        """Returns False when _searxng_process is None."""
        assert _is_process_alive() is False

    def test_returns_true_when_alive(self):
        """Returns True when process poll() returns None (alive)."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mod._searxng_process = mock_proc
        assert _is_process_alive() is True

    def test_returns_false_when_dead(self):
        """Returns False when process poll() returns exit code."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        mod._searxng_process = mock_proc
        assert _is_process_alive() is False


# ===========================================================================
# _kill_stale_port_process
# ===========================================================================


class TestKillStalePortProcess:
    async def test_invalid_port_noop(self):
        """Invalid ports are silently ignored."""
        await _kill_stale_port_process(0)  # No error
        await _kill_stale_port_process(-1)  # No error
        await _kill_stale_port_process(70000)  # No error
        await _kill_stale_port_process("abc")  # type: ignore[arg-type]  # No error

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    async def test_windows_netstat(self):
        """On Windows, uses netstat to find stale PIDs."""
        mock_result = MagicMock()
        mock_result.stdout = "  TCP    127.0.0.1:18888    0.0.0.0:0    LISTENING    99999\n"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_kill,
        ):
            await _kill_stale_port_process(18888)
            mock_kill.assert_called_once_with(99999, "stale port 18888")

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
    async def test_unix_lsof_not_found_falls_back_to_fuser(self):
        """On Unix, if lsof is not found, falls back to fuser."""
        mock_fuser_result = MagicMock()
        mock_fuser_result.returncode = 0

        def side_effect(args, **kwargs):
            if args[0] == "lsof":
                raise FileNotFoundError("lsof not found")
            return mock_fuser_result

        with (
            patch("subprocess.run", side_effect=side_effect) as mock_run,
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_kill,
        ):
            await _kill_stale_port_process(18888)
            # Verify both lsof and fuser were tried
            assert mock_run.call_count == 2
            mock_run.assert_any_call(
                ["lsof", "-ti", ":18888"],
                shell=False,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=5,
            )
            mock_run.assert_any_call(
                ["fuser", "-k", "18888/tcp"],
                shell=False,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=5,
            )
            # fuser -k handles killing, so _sigterm_then_kill shouldn't be called by us
            mock_kill.assert_not_called()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
    async def test_unix_lsof_and_fuser_not_found(self):
        """On Unix, handles cases where both lsof and fuser are missing."""
        with (
            patch("subprocess.run", side_effect=FileNotFoundError("not found")),
            patch("web_core.search.runner.logger") as mock_logger,
        ):
            await _kill_stale_port_process(18888)
            # Should log debug message for fuser failure
            mock_logger.debug.assert_any_call("Could not free port %d using fuser: %s", 18888, ANY)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
    async def test_unix_lsof(self):
        """On Unix, uses lsof to find stale PIDs."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "99999\n"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_kill,
        ):
            await _kill_stale_port_process(18888)
            mock_kill.assert_called_once_with(99999, "stale port 18888")


# ===========================================================================
# _cleanup_process / shutdown_searxng
# ===========================================================================


class TestCleanupProcess:
    def test_cleanup_as_owner(self, tmp_discovery, tmp_path):
        """Owner kills process, removes discovery file, and deletes settings path."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345
        mock_proc.stderr = None

        mod._searxng_process = mock_proc
        mod._searxng_port = 18888
        mod._is_owner = True

        # Mock settings path
        dummy_settings = tmp_path / "searxng_settings_test.yml"
        dummy_settings.write_text("test")
        mod._searxng_settings_path = dummy_settings

        _write_discovery(18888, 12345)
        assert tmp_discovery.exists()

        _cleanup_process()

        assert mod._searxng_process is None
        assert mod._searxng_port is None
        assert mod._is_owner is False
        assert not tmp_discovery.exists()
        assert not dummy_settings.exists()

    def test_cleanup_as_non_owner(self, tmp_discovery):
        """Non-owner clears local refs but does not kill or remove discovery."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345

        mod._searxng_process = mock_proc
        mod._searxng_port = 18888
        mod._is_owner = False

        _write_discovery(18888, 12345)

        _cleanup_process()

        assert mod._searxng_process is None
        assert mod._searxng_port is None
        # Discovery file should still exist (not our responsibility)
        assert tmp_discovery.exists()

    def test_cleanup_no_process(self):
        """Does not raise when no process exists."""
        _cleanup_process()  # Should not raise

    def test_shutdown_searxng_calls_cleanup(self, tmp_discovery):
        """shutdown_searxng delegates to _cleanup_process."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345
        mock_proc.stderr = None

        mod._searxng_process = mock_proc
        mod._searxng_port = 18888
        mod._is_owner = True

        shutdown_searxng()

        assert mod._searxng_process is None

    def test_cleanup_removes_settings_file(self, tmp_config_dir):
        """Cleanup removes the dynamically generated settings file."""
        import web_core.search.runner as mod

        settings_file = tmp_config_dir / "searxng_settings_test.yml"
        settings_file.write_text("test")
        mod._searxng_settings_path = settings_file
        assert settings_file.exists()

        _cleanup_process()

        assert not settings_file.exists()

    def test_cleanup_settings_file_error(self):
        """Cleanup handles errors when removing the settings file by logging."""
        import web_core.search.runner as mod

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.unlink.side_effect = Exception("permission denied")

        mod._searxng_settings_path = mock_path

        with patch("web_core.search.runner.logger") as mock_logger:
            _cleanup_process()
            mock_logger.debug.assert_any_call("Failed to cleanup settings file: %s", ANY)


# ===========================================================================
# ensure_searxng
# ===========================================================================


class TestEnsureSearxng:
    async def test_returns_env_var_url(self, monkeypatch):
        """Returns SEARXNG_URL env var if set, no auto-start."""
        monkeypatch.setenv("SEARXNG_URL", "http://external:8080")
        url = await ensure_searxng()
        assert url == "http://external:8080"

    async def test_returns_explicit_url(self, monkeypatch):
        """Returns explicit url parameter, no auto-start."""
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        url = await ensure_searxng(url="http://my-searxng:9999")
        assert url == "http://my-searxng:9999"

    async def test_explicit_url_overrides_env(self, monkeypatch):
        """Explicit url parameter takes priority over env var."""
        monkeypatch.setenv("SEARXNG_URL", "http://env:8080")
        url = await ensure_searxng(url="http://explicit:9999")
        assert url == "http://explicit:9999"

    async def test_strips_trailing_slash(self, monkeypatch):
        """Strips trailing slash from URL."""
        monkeypatch.setenv("SEARXNG_URL", "http://external:8080/")
        url = await ensure_searxng()
        assert url == "http://external:8080"

    async def test_returns_url_from_discovery(self, tmp_discovery, monkeypatch):
        """Returns URL from discovery file if valid instance is running."""
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        _write_discovery(18888, os.getpid())

        with patch("web_core.search.runner._quick_health_check", new_callable=AsyncMock, return_value=True):
            url = await ensure_searxng()
            assert url == "http://127.0.0.1:18888"

    async def test_auto_start_disabled_raises(self, tmp_discovery, monkeypatch):
        """Raises RuntimeError when no instance found and auto_start=False."""
        monkeypatch.delenv("SEARXNG_URL", raising=False)

        with pytest.raises(RuntimeError, match="auto_start is disabled"):
            await ensure_searxng(auto_start=False)

    async def test_concurrent_calls_use_lock(self, monkeypatch):
        """Concurrent calls are serialized by the asyncio lock."""
        monkeypatch.setenv("SEARXNG_URL", "http://external:8080")

        # Launch multiple concurrent calls
        results = await asyncio.gather(
            ensure_searxng(),
            ensure_searxng(),
            ensure_searxng(),
        )
        assert all(r == "http://external:8080" for r in results)

    async def test_fast_path_reuses_alive_process(self, monkeypatch):
        """Fast path returns URL when our own process is alive and healthy."""
        import web_core.search.runner as mod

        monkeypatch.delenv("SEARXNG_URL", raising=False)

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # alive
        mock_proc.pid = 12345

        mod._searxng_process = mock_proc
        mod._searxng_port = 18888

        with patch("web_core.search.runner._quick_health_check", new_callable=AsyncMock, return_value=True):
            url = await ensure_searxng()
            assert url == "http://127.0.0.1:18888"

    async def test_restart_on_crash(self, tmp_discovery, monkeypatch):
        """Restarts SearXNG when the process has crashed."""
        import web_core.search.runner as mod

        monkeypatch.delenv("SEARXNG_URL", raising=False)

        # Simulate a crashed process
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # exited
        mock_proc.pid = 12345
        mock_proc.stderr = None
        mod._searxng_process = mock_proc
        mod._searxng_port = 18888

        with (
            patch("web_core.search.runner._try_reuse_existing", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=True),
            patch(
                "web_core.search.runner._start_docker_searxng",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "web_core.search.runner._start_searxng_subprocess",
                new_callable=AsyncMock,
                return_value="http://127.0.0.1:18889",
            ),
        ):
            url = await ensure_searxng()
            assert url == "http://127.0.0.1:18889"

    async def test_installs_and_starts(self, tmp_discovery, monkeypatch):
        """Installs SearXNG and starts when not installed."""
        monkeypatch.delenv("SEARXNG_URL", raising=False)

        with (
            patch("web_core.search.runner._try_reuse_existing", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=False),
            patch("web_core.search.runner._install_searxng", return_value=True),
            patch(
                "web_core.search.runner._start_searxng_subprocess",
                new_callable=AsyncMock,
                return_value="http://127.0.0.1:18888",
            ),
        ):
            url = await ensure_searxng()
            assert url == "http://127.0.0.1:18888"

    async def test_install_failure_raises(self, tmp_discovery, monkeypatch):
        """Raises RuntimeError when SearXNG installation fails."""
        monkeypatch.delenv("SEARXNG_URL", raising=False)

        with (
            patch("web_core.search.runner._try_reuse_existing", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=False),
            patch("web_core.search.runner._install_searxng", return_value=False),
            pytest.raises(RuntimeError, match="installation failed"),
        ):
            await ensure_searxng()

    async def test_restart_limit_reached(self, tmp_discovery, monkeypatch):
        """Raises RuntimeError when restart limit is reached."""
        import web_core.search.runner as mod

        monkeypatch.delenv("SEARXNG_URL", raising=False)

        mod._restart_count = 3
        mod._last_restart_time = time.time()  # Recent, so counter won't reset

        with (
            patch("web_core.search.runner._try_reuse_existing", new_callable=AsyncMock, return_value=None),
            pytest.raises(RuntimeError, match="restart limit reached"),
        ):
            await ensure_searxng()

    async def test_start_failure_raises(self, tmp_discovery, monkeypatch):
        """Raises RuntimeError when subprocess start fails."""
        monkeypatch.delenv("SEARXNG_URL", raising=False)

        with (
            patch("web_core.search.runner._try_reuse_existing", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=True),
            patch("web_core.search.runner._start_searxng_subprocess", new_callable=AsyncMock, return_value=None),
            pytest.raises(RuntimeError, match="start failed"),
        ):
            await ensure_searxng()


# ===========================================================================
# _get_startup_lock
# ===========================================================================


class TestGetStartupLock:
    def test_returns_asyncio_lock(self):
        """Returns an asyncio.Lock instance."""
        lock = _get_startup_lock()
        assert isinstance(lock, asyncio.Lock)

    def test_returns_same_lock(self):
        """Returns the same lock on subsequent calls."""
        lock1 = _get_startup_lock()
        lock2 = _get_startup_lock()
        assert lock1 is lock2


# ===========================================================================
# Settings template
# ===========================================================================


# ===========================================================================
# _start_docker_searxng
# ===========================================================================


class TestStartDockerSearxng:
    async def test_docker_binary_not_found(self):
        """Returns None if docker binary is not in PATH."""
        with patch("shutil.which", return_value=None):
            url = await _start_docker_searxng(8888)
            assert url is None

    async def test_docker_daemon_not_running(self):
        """Returns None if docker info fails (daemon not running)."""
        mock_res = MagicMock()
        mock_res.returncode = 1
        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("subprocess.run", return_value=mock_res),
        ):
            url = await _start_docker_searxng(8888)
            assert url is None

    async def test_reuse_healthy_container(self, tmp_config_dir):
        """Reuses an existing container if it is healthy."""
        import web_core.search.runner as mod

        mock_res_info = MagicMock()
        mock_res_info.returncode = 0

        mock_res_ps = MagicMock()
        mock_res_ps.stdout = "container_id_123"

        mock_lock = MagicMock()

        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("subprocess.run", side_effect=[mock_res_info, mock_res_ps]),
            patch("web_core.search.runner._get_docker_lock", return_value=mock_lock),
            patch("web_core.search.runner._quick_health_check", new_callable=AsyncMock, return_value=True),
        ):
            url = await _start_docker_searxng(8888)
            assert url == "http://127.0.0.1:41592"
            assert mod._searxng_docker_container == "searxng-wet-41592"
            assert mod._is_owner is False

    async def test_spawn_new_container_success(self, tmp_config_dir):
        """Spawns a new container when none exists and it becomes healthy."""
        import web_core.search.runner as mod

        mock_res_info = MagicMock()
        mock_res_info.returncode = 0

        mock_res_ps = MagicMock()
        mock_res_ps.stdout = ""  # No container running

        mock_res_rm = MagicMock()

        mock_lock = MagicMock()

        mock_popen = MagicMock()
        mock_popen.wait = AsyncMock(return_value=0)
        mock_popen.returncode = 0

        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("subprocess.run", side_effect=[mock_res_info, mock_res_ps, mock_res_rm]),
            patch("web_core.search.runner._get_docker_lock", return_value=mock_lock),
            patch("web_core.search.runner._write_secure_text") as mock_write,
            patch("subprocess.Popen", return_value=mock_popen),
            patch("web_core.search.runner._wait_for_service", new_callable=AsyncMock, return_value=True),
            patch("web_core.search.runner._write_discovery", return_value=None),
        ):
            url = await _start_docker_searxng(8888)
            assert url == "http://127.0.0.1:41592"
            assert mod._searxng_docker_container == "searxng-wet-41592"
            assert mod._is_owner is True
            mock_write.assert_called_once()

    async def test_respawn_unhealthy_container(self, tmp_config_dir):
        """Respawns if container exists but is unhealthy."""
        import web_core.search.runner as mod

        mock_res_info = MagicMock()
        mock_res_info.returncode = 0

        mock_res_ps = MagicMock()
        mock_res_ps.stdout = "container_id_123"

        mock_res_rm = MagicMock()

        mock_lock = MagicMock()

        mock_popen = MagicMock()
        mock_popen.wait = AsyncMock(return_value=0)
        mock_popen.returncode = 0

        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("subprocess.run", side_effect=[mock_res_info, mock_res_ps, mock_res_rm]),
            patch("web_core.search.runner._get_docker_lock", return_value=mock_lock),
            patch("web_core.search.runner._quick_health_check", new_callable=AsyncMock, return_value=False),
            patch("web_core.search.runner._write_secure_text"),
            patch("subprocess.Popen", return_value=mock_popen),
            patch("web_core.search.runner._wait_for_service", new_callable=AsyncMock, return_value=True),
            patch("web_core.search.runner._write_discovery", return_value=None),
        ):
            url = await _start_docker_searxng(8888)
            assert url == "http://127.0.0.1:41592"
            assert mod._is_owner is True

    async def test_docker_run_failure(self, tmp_config_dir):
        """Returns None if docker run fails."""
        mock_res_info = MagicMock()
        mock_res_info.returncode = 0
        mock_res_ps = MagicMock()
        mock_res_ps.stdout = ""
        mock_res_rm = MagicMock()

        mock_lock = MagicMock()

        mock_popen = MagicMock()
        mock_popen.wait = AsyncMock(return_value=1)
        mock_popen.returncode = 1

        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("subprocess.run", side_effect=[mock_res_info, mock_res_ps, mock_res_rm]),
            patch("web_core.search.runner._get_docker_lock", return_value=mock_lock),
            patch("web_core.search.runner._write_secure_text"),
            patch("subprocess.Popen", return_value=mock_popen),
        ):
            url = await _start_docker_searxng(8888)
            assert url is None

    async def test_service_timeout_cleanup(self, tmp_config_dir):
        """Cleans up and returns None if service never becomes healthy."""
        mock_res_info = MagicMock()
        mock_res_info.returncode = 0
        mock_res_ps = MagicMock()
        mock_res_ps.stdout = ""
        mock_res_rm_init = MagicMock()
        mock_res_rm_cleanup = MagicMock()

        mock_lock = MagicMock()

        mock_popen = MagicMock()
        mock_popen.wait = AsyncMock(return_value=0)
        mock_popen.returncode = 0

        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch(
                "subprocess.run", side_effect=[mock_res_info, mock_res_ps, mock_res_rm_init, mock_res_rm_cleanup]
            ) as mock_run,
            patch("web_core.search.runner._get_docker_lock", return_value=mock_lock),
            patch("web_core.search.runner._write_secure_text"),
            patch("subprocess.Popen", return_value=mock_popen),
            patch("web_core.search.runner._wait_for_service", new_callable=AsyncMock, return_value=False),
        ):
            url = await _start_docker_searxng(8888)
            assert url is None
            # Verify cleanup rm was called
            assert mock_run.call_count == 4

    async def test_general_exception_handling(self):
        """Returns None and logs error on unexpected exceptions."""
        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("asyncio.to_thread", side_effect=Exception("unexpected")),
        ):
            url = await _start_docker_searxng(8888)
            assert url is None


class TestSettingsTemplate:
    def test_template_has_placeholders(self):
        """Template contains the expected format placeholders."""
        assert "{port}" in _SETTINGS_TEMPLATE
        assert "{secret_key}" in _SETTINGS_TEMPLATE
        assert "{enable_http2}" in _SETTINGS_TEMPLATE

    def test_template_renders_cleanly(self):
        """Template renders without errors."""
        rendered = _SETTINGS_TEMPLATE.format(
            port=18888,
            secret_key="test-key-123",
            enable_http2="true",
        )
        assert "port: 18888" in rendered
        assert 'secret_key: "test-key-123"' in rendered
        assert "enable_http2: true" in rendered


# ===========================================================================
# Module exports
# ===========================================================================


class TestModuleExports:
    def test_ensure_searxng_exported(self):
        """ensure_searxng is available from web_core.search."""
        from web_core.search import ensure_searxng as fn

        assert callable(fn)

    def test_shutdown_searxng_exported(self):
        """shutdown_searxng is available from web_core.search."""
        from web_core.search import shutdown_searxng as fn

        assert callable(fn)

    def test_all_contains_runner_exports(self):
        """__all__ includes runner exports."""
        from web_core.search import __all__ as all_exports

        assert "ensure_searxng" in all_exports
        assert "shutdown_searxng" in all_exports


# ===========================================================================
# _get_docker_lock
# ===========================================================================


class TestGetDockerLock:
    def test_returns_filelock(self, tmp_config_dir):
        """Returns a filelock.FileLock instance with correct path and timeout."""
        import filelock

        lock = _get_docker_lock()
        assert isinstance(lock, filelock.FileLock)
        assert Path(lock.lock_file).name == "docker_startup.lock"
        assert lock.timeout == 60.0

    def test_returns_same_lock(self, tmp_config_dir):
        """Returns the same lock on subsequent calls."""
        lock1 = _get_docker_lock()
        lock2 = _get_docker_lock()
        assert lock1 is lock2

    def test_creates_config_dir(self, tmp_path, monkeypatch):
        """Creates the config directory if it does not exist."""
        config_dir = tmp_path / "new-config-dir"
        monkeypatch.setattr("web_core.search.runner._CONFIG_DIR", config_dir)
        monkeypatch.setattr("web_core.search.runner._docker_lock", None)

        assert not config_dir.exists()
        _get_docker_lock()
        assert config_dir.exists()

    def test_get_config_dir_permissions(self, tmp_path, monkeypatch):
        """_get_config_dir sets correct permissions (0o700) on non-Windows."""
        import os
        import sys

        from web_core.search.runner import _get_config_dir

        config_dir = tmp_path / "perm-test-dir"
        monkeypatch.setattr("web_core.search.runner._CONFIG_DIR", config_dir)

        _get_config_dir()
        assert config_dir.exists()

        if sys.platform != "win32":
            mode = os.stat(config_dir).st_mode
            assert (mode & 0o777) == 0o700


# ===========================================================================
# _handle_restart_and_start
# ===========================================================================


class TestHandleRestartAndStart:
    @pytest.fixture(autouse=True)
    def _reset_state(self):
        import web_core.search.runner as mod

        mod._searxng_process = None
        mod._searxng_port = None
        mod._restart_count = 0
        mod._last_restart_time = 0.0
        mod._searxng_docker_container = None
        yield

    async def test_crash_detection_logging(self):
        """Verifies crashed process is logged and cleared."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = -1
        mock_proc.stderr.read.return_value = b"some error"
        mod._searxng_process = mock_proc

        with (
            patch("web_core.search.runner.logger") as mock_logger,
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value="http://ok"),
            patch("asyncio.to_thread", side_effect=lambda f, *args: f(*args)),
        ):
            await _handle_restart_and_start(start_port=8888)
            assert mod._searxng_process is None
            # Check warning call - first argument to warning
            warning_call = [call for call in mock_logger.warning.call_args_list if "crashed" in call.args[0]]
            assert len(warning_call) > 0

    async def test_crash_detection_stderr_read_failure(self):
        """Verifies crash detection handles stderr read failure gracefully."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = -1
        mock_proc.stderr.read.side_effect = Exception("read error")
        mod._searxng_process = mock_proc

        with (
            patch("web_core.search.runner.logger") as mock_logger,
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value="http://ok"),
            patch("asyncio.to_thread", side_effect=lambda f, *args: f(*args)),
        ):
            await _handle_restart_and_start(start_port=8888)
            assert mod._searxng_process is None
            warning_call = [call for call in mock_logger.warning.call_args_list if "crashed" in call.args[0]]
            assert len(warning_call) > 0
            # stderr should be empty in the log message
            assert "stderr: " in warning_call[0].args[0]

    async def test_restart_counter_reset(self):
        """Resets restart count if enough time passed."""
        import web_core.search.runner as mod

        mod._restart_count = 5
        mod._last_restart_time = time.time() - 301

        with patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value="http://ok"):
            await _handle_restart_and_start(start_port=8888)
            assert mod._restart_count == 0

    async def test_docker_fallback_success(self):
        """Returns Docker URL if successful."""
        import web_core.search.runner as mod

        with patch(
            "web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value="http://docker-url"
        ):
            url = await _handle_restart_and_start(start_port=8888)
            assert url == "http://docker-url"
            assert mod._restart_count == 0

    async def test_subprocess_success_after_docker_fail(self):
        """Falls back to subprocess if Docker fails."""
        import web_core.search.runner as mod

        with (
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=True),
            patch(
                "web_core.search.runner._start_searxng_subprocess",
                new_callable=AsyncMock,
                return_value="http://sub-url",
            ),
        ):
            url = await _handle_restart_and_start(start_port=8888)
            assert url == "http://sub-url"
            assert mod._restart_count == 0

    async def test_restart_limit_reached(self):
        """Raises RuntimeError if limit reached."""
        import web_core.search.runner as mod

        mod._restart_count = 3
        mod._last_restart_time = time.time()

        with pytest.raises(RuntimeError, match="restart limit reached"):
            await _handle_restart_and_start(start_port=8888)

    async def test_install_failure(self):
        """Raises RuntimeError if installation fails."""
        with (
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=False),
            patch("web_core.search.runner._install_searxng", return_value=False),
            pytest.raises(RuntimeError, match="installation failed"),
        ):
            await _handle_restart_and_start(start_port=8888)

    async def test_cooldown_applied(self):
        """Applies cooldown if restart count > 0."""
        import web_core.search.runner as mod

        mod._restart_count = 1
        mod._last_restart_time = time.time()

        with (
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=True),
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("web_core.search.runner._start_searxng_subprocess", new_callable=AsyncMock, return_value="http://ok"),
        ):
            await _handle_restart_and_start(start_port=8888)
            mock_sleep.assert_called_once_with(2.0)  # _RESTART_COOLDOWN * 1

    async def test_subprocess_failure_raises(self):
        """Raises RuntimeError if subprocess also fails."""
        with (
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=True),
            patch("web_core.search.runner._start_searxng_subprocess", new_callable=AsyncMock, return_value=None),
            pytest.raises(RuntimeError, match="start failed after all attempts"),
        ):
            await _handle_restart_and_start(start_port=8888)

    async def test_crash_detection_no_stderr(self):
        """Verifies crash detection handles missing stderr."""
        import web_core.search.runner as mod

        mock_proc = MagicMock()
        mock_proc.poll.return_value = -1
        mock_proc.stderr = None
        mod._searxng_process = mock_proc

        with (
            patch("web_core.search.runner.logger") as mock_logger,
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value="http://ok"),
        ):
            await _handle_restart_and_start(start_port=8888)
            assert mod._searxng_process is None
            warning_call = [call for call in mock_logger.warning.call_args_list if "crashed" in call.args[0]]
            assert len(warning_call) > 0

    async def test_install_required_and_success(self):
        """Verifies it proceeds if installation is required and succeeds."""

        with (
            patch("web_core.search.runner._start_docker_searxng", new_callable=AsyncMock, return_value=None),
            patch("web_core.search.runner._is_searxng_installed", return_value=False),
            patch("web_core.search.runner._install_searxng", return_value=True),
            patch(
                "web_core.search.runner._start_searxng_subprocess",
                new_callable=AsyncMock,
                return_value="http://sub-url",
            ),
        ):
            url = await _handle_restart_and_start(start_port=8888)
            assert url == "http://sub-url"
