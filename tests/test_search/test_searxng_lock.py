"""Regression: searxng Docker container reuse via pinned port + filelock.

Verifies that _start_docker_searxng:
1. Reuses an existing container when one is running on PINNED_SEARXNG_PORT.
2. Spawns exactly one new container (rm -f stale + docker run) when absent.

All Docker/network calls are mocked -- no real Docker daemon required.
These tests run on CI environments without Docker installed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.search.runner import PINNED_SEARXNG_PORT, _start_docker_searxng

# Fake docker binary path used across tests (avoids shutil.which("docker") returning None on CI).
_FAKE_DOCKER = "/usr/bin/docker"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_docker_state():
    """Reset module-level Docker state before and after each test."""
    import web_core.search.runner as mod

    mod._searxng_docker_container = None
    mod._searxng_port = None
    mod._is_owner = False
    mod._DOCKER_LOCK = None  # Reset lazy filelock so tmp_path dir is used
    yield
    mod._searxng_docker_container = None
    mod._searxng_port = None
    mod._is_owner = False
    mod._DOCKER_LOCK = None


# ---------------------------------------------------------------------------
# Test: reuse existing container
# ---------------------------------------------------------------------------


async def test_spawn_docker_searxng_reuses_existing_container(tmp_path, monkeypatch):
    """When container searxng-wet-{PINNED_PORT} already running, do NOT docker run."""
    import web_core.search.runner as mod

    config_dir = tmp_path / ".web-core"
    config_dir.mkdir()
    monkeypatch.setattr(mod, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(mod, "_DISCOVERY_FILE", config_dir / "searxng_instance.json")

    container_name = f"searxng-wet-{PINNED_SEARXNG_PORT}"

    call_args_list: list = []

    def fake_run(cmd, **kwargs):
        call_args_list.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        # docker info succeeds
        if cmd[1] == "info":
            result.stdout = "Server: Docker Desktop"
            return result
        # docker ps -q -f name=<container> -> returns container id (running)
        if cmd[1] == "ps" and any(container_name in str(a) for a in cmd):
            result.stdout = b"abc123\n"
            return result
        result.stdout = b""
        return result

    with (
        patch("web_core.search.runner.shutil.which", return_value=_FAKE_DOCKER),
        patch("web_core.search.runner.subprocess.run", side_effect=fake_run),
        patch("web_core.search.runner._quick_health_check", new=AsyncMock(return_value=True)),
        patch("web_core.search.runner._write_discovery"),
    ):
        url = await _start_docker_searxng(start_port=PINNED_SEARXNG_PORT)

    assert url == f"http://127.0.0.1:{PINNED_SEARXNG_PORT}"
    # Verify no "docker run" was issued
    docker_run_calls = [c for c in call_args_list if len(c) > 1 and c[1] == "run"]
    assert len(docker_run_calls) == 0, f"Should not spawn new container; got: {docker_run_calls}"


# ---------------------------------------------------------------------------
# Test: spawn when absent
# ---------------------------------------------------------------------------


async def test_spawn_docker_searxng_creates_when_absent(tmp_path, monkeypatch):
    """When no container running on PINNED_PORT, rm stale + docker run must be called."""
    import web_core.search.runner as mod

    config_dir = tmp_path / ".web-core"
    config_dir.mkdir()
    monkeypatch.setattr(mod, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(mod, "_DISCOVERY_FILE", config_dir / "searxng_instance.json")

    container_name = f"searxng-wet-{PINNED_SEARXNG_PORT}"

    call_args_list: list = []

    def fake_run(cmd, **kwargs):
        call_args_list.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        # docker info succeeds
        if cmd[1] == "info":
            result.stdout = "Server: Docker Desktop"
            return result
        # docker ps -q -f name=<container> -> returns empty (not running)
        if cmd[1] == "ps" and any(container_name in str(a) for a in cmd):
            result.stdout = b""
            return result
        result.stdout = b""
        return result

    fake_popen = MagicMock()
    fake_popen.returncode = 0
    fake_popen.wait.return_value = 0

    mock_popen = MagicMock(return_value=fake_popen)

    with (
        patch("web_core.search.runner.shutil.which", return_value=_FAKE_DOCKER),
        patch("web_core.search.runner.subprocess.run", side_effect=fake_run),
        patch("web_core.search.runner.subprocess.Popen", mock_popen),
        patch("web_core.search.runner._wait_for_service", new=AsyncMock(return_value=True)),
        patch("web_core.search.runner._write_discovery"),
    ):
        url = await _start_docker_searxng(start_port=PINNED_SEARXNG_PORT)

    assert url == f"http://127.0.0.1:{PINNED_SEARXNG_PORT}"

    # rm -f stale container must be called via subprocess.run
    rm_calls = [c for c in call_args_list if len(c) > 1 and c[1] == "rm"]
    assert len(rm_calls) >= 1, f"Expected docker rm call; got calls: {call_args_list}"

    # docker run -d must be issued via Popen (detached container)
    assert mock_popen.called, "Expected subprocess.Popen to be called for docker run -d"
    popen_cmd = mock_popen.call_args[0][0]
    assert "-d" in popen_cmd, f"Expected -d flag in docker run; got: {popen_cmd}"
    assert container_name in popen_cmd, f"Expected container name {container_name}; got: {popen_cmd}"
