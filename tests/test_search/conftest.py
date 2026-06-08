"""Shared fixtures for search tests."""

from __future__ import annotations

import pytest


def _reset_module_state():
    """Reset module-level state between tests."""
    import web_core.search.runner as mod

    mod._searxng_process = None
    mod._searxng_port = None
    mod._searxng_docker_container = None
    mod._searxng_settings_path = None
    mod._restart_count = 0
    mod._last_restart_time = 0.0
    mod._is_owner = False
    mod._startup_lock = None
    mod._DOCKER_LOCK = None


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset module state before and after each test."""
    _reset_module_state()
    yield
    _reset_module_state()


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Use a temporary config directory."""
    import web_core.search.runner as mod

    config_dir = tmp_path / ".web-core"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(mod, "_DISCOVERY_FILE", config_dir / "searxng_instance.json")
    return config_dir


@pytest.fixture
def tmp_discovery(tmp_path, monkeypatch):
    """Use a temporary discovery file."""
    import web_core.search.runner as mod

    discovery = tmp_path / "searxng_instance.json"
    monkeypatch.setattr(mod, "_DISCOVERY_FILE", discovery)
    return discovery
