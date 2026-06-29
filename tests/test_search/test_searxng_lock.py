"""Regression: searxng Docker container reuse via pinned port + filelock.

Verifies that _start_docker_searxng:
1. Reuses an existing container when one is running on PINNED_SEARXNG_PORT.
2. Spawns exactly one new container (rm -f stale + docker run) when absent.

All Docker/network calls are mocked -- no real Docker daemon required.
These tests run on CI environments without Docker installed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.search.runner import PINNED_SEARXNG_PORT, _start_docker_searxng

# Fake docker binary path used across tests (avoids shutil.which("docker") returning None on CI).
_FAKE_DOCKER = "/usr/bin/docker"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class DockerMock:
    """Helper to mock Docker subprocess calls and track interactions."""

    def __init__(self) -> None:
        self.run_calls: list[list[str]] = []
        self.popen_calls: list[list[str]] = []
        self.container_running = False

    def fake_run(self, cmd: list[str], **_kwargs: Any) -> MagicMock:
        self.run_calls.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        # docker info succeeds
        if len(cmd) > 1 and cmd[1] == "info":
            result.stdout = "Server: Docker Desktop"
            return result
        # docker ps -q -f name=<container>
        if len(cmd) > 1 and cmd[1] == "ps" and any(f"searxng-wet-{PINNED_SEARXNG_PORT}" in str(a) for a in cmd):
            result.stdout = b"abc123\n" if self.container_running else b""
            return result
        result.stdout = b""
        return result

    def fake_popen(self, cmd: list[str], **_kwargs: Any) -> MagicMock:
        self.popen_calls.append(list(cmd))
        proc = MagicMock()
        proc.returncode = 0
        proc.wait.return_value = 0
        return proc


@pytest.fixture
def docker_mock():
    """Fixture to mock Docker subprocess.run and subprocess.Popen."""
    mock = DockerMock()
    with (
        patch("web_core.search.runner.subprocess.run", side_effect=mock.fake_run),
        patch("web_core.search.runner.subprocess.Popen", side_effect=mock.fake_popen),
    ):
        yield mock


@pytest.fixture(autouse=True)
def patch_runner_globals(monkeypatch):
    """Ensure runner globals are patched so we don't clobber the real system."""
    monkeypatch.setattr("web_core.search.runner.shutil.which", lambda x: _FAKE_DOCKER if x == "docker" else None)
    with (
        patch("web_core.search.runner._quick_health_check", new=AsyncMock(return_value=True)),
        patch("web_core.search.runner._wait_for_service", new=AsyncMock(return_value=True)),
        patch("web_core.search.runner._write_discovery"),
    ):
        yield


# ---------------------------------------------------------------------------
# Test: reuse existing container
# ---------------------------------------------------------------------------


async def test_spawn_docker_searxng_reuses_existing_container(tmp_config_dir, docker_mock):
    """When container searxng-wet-{PINNED_PORT} already running, do NOT docker run."""
    docker_mock.container_running = True

    url = await _start_docker_searxng(start_port=PINNED_SEARXNG_PORT)

    assert url == f"http://127.0.0.1:{PINNED_SEARXNG_PORT}"
    # Verify no "docker run" was issued
    docker_run_calls = [c for c in docker_mock.run_calls if len(c) > 1 and c[1] == "run"]
    assert len(docker_run_calls) == 0, f"Should not spawn new container; got: {docker_run_calls}"


# ---------------------------------------------------------------------------
# Test: spawn when absent
# ---------------------------------------------------------------------------


async def test_spawn_docker_searxng_creates_when_absent(tmp_config_dir, docker_mock):
    """When no container running on PINNED_PORT, rm stale + docker run must be called."""
    docker_mock.container_running = False

    url = await _start_docker_searxng(start_port=PINNED_SEARXNG_PORT)

    assert url == f"http://127.0.0.1:{PINNED_SEARXNG_PORT}"

    # rm -f stale container must be called via subprocess.run
    rm_calls = [c for c in docker_mock.run_calls if len(c) > 1 and c[1] == "rm"]
    assert len(rm_calls) >= 1, f"Expected docker rm call; got calls: {docker_mock.run_calls}"

    # docker run -d must be issued via Popen (detached container)
    assert len(docker_mock.popen_calls) > 0, "Expected subprocess.Popen to be called for docker run -d"
    popen_cmd = docker_mock.popen_calls[0]
    assert "-d" in popen_cmd, f"Expected -d flag in docker run; got: {popen_cmd}"
    assert f"searxng-wet-{PINNED_SEARXNG_PORT}" in popen_cmd
