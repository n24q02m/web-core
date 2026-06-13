"""Shared test fixtures for web_core.search."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_runner_state():
    """Reset module-level state in web_core.search.runner between tests."""
    import web_core.search.runner as mod

    def _reset():
        mod._searxng_process = None
        mod._searxng_port = None
        mod._searxng_docker_container = None
        mod._searxng_settings_path = None
        mod._restart_count = 0
        mod._last_restart_time = 0.0
        mod._is_owner = False
        mod._startup_lock = None
        mod._docker_lock = None

    _reset()
    yield
    _reset()


@pytest.fixture(autouse=True)
def _clean_client_state():
    """Reset module-level state in web_core.search.client between tests."""
    import web_core.search.client as mod

    def _reset():
        if mod._shared_client is not None:
            # We don't necessarily want to close it here as it might be in use,
            # but for test isolation it's safer to reset the reference.
            # test_client.py usually handles the actual client lifecycle if needed,
            # but resetting to None forces re-init.
            mod._shared_client = None

    _reset()
    yield
    _reset()


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Use a temporary config directory for SearchRunner."""
    import web_core.search.runner as mod

    config_dir = tmp_path / ".web-core"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(mod, "_DISCOVERY_FILE", config_dir / "searxng_instance.json")
    return config_dir


@pytest.fixture
def tmp_discovery(tmp_path, monkeypatch):
    """Use a temporary discovery file for SearchRunner."""
    import web_core.search.runner as mod

    discovery = tmp_path / "searxng_instance.json"
    monkeypatch.setattr(mod, "_DISCOVERY_FILE", discovery)
    return discovery
