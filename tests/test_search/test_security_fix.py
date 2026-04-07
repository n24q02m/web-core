import stat

import pytest

import web_core.search.runner as runner
from web_core.search.runner import _cleanup_process, _get_settings_path, _write_discovery


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Use a temporary config directory."""
    config_dir = tmp_path / ".web-core"
    # Don't create it here, let the code create it to test permissions
    monkeypatch.setattr(runner, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(runner, "_DISCOVERY_FILE", config_dir / "searxng_instance.json")
    return config_dir


def test_config_dir_permissions(tmp_config_dir):
    """Verify that _CONFIG_DIR is created with 0o700 permissions."""
    _get_settings_path(18888)
    assert tmp_config_dir.exists()
    mode = tmp_config_dir.stat().st_mode
    assert stat.S_IMODE(mode) == 0o700


def test_settings_file_permissions(tmp_config_dir):
    """Verify that settings file is created with 0o600 permissions."""
    path = _get_settings_path(18888)
    assert path.exists()
    mode = path.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600


def test_settings_file_uniqueness(tmp_config_dir):
    """Verify that subsequent calls create different files."""
    path1 = _get_settings_path(18888)
    path2 = _get_settings_path(18889)
    assert path1 != path2
    assert path1.exists()
    assert path2.exists()


def test_discovery_file_permissions(tmp_config_dir):
    """Verify that discovery file is created with 0o600 permissions."""
    _write_discovery(18888, 12345)
    discovery_file = runner._DISCOVERY_FILE
    assert discovery_file.exists()
    mode = discovery_file.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600


def test_cleanup_removes_secure_settings(tmp_config_dir):
    """Verify that _cleanup_process removes the secure settings file."""
    path = _get_settings_path(18888)
    assert path.exists()

    _cleanup_process()
    assert not path.exists()

def test_discovery_file_exception_handling(tmp_config_dir, monkeypatch):
    """Verify exception handling in _write_discovery."""
    import os
    original_open = os.open
    def mock_open(*args, **kwargs):
        raise OSError("Mock error")

    monkeypatch.setattr(os, "open", mock_open)
    # Should not raise exception but log it
    _write_discovery(18888, 12345)

def test_get_settings_path_exception_handling(tmp_config_dir, monkeypatch):
    """Verify exception handling in _get_settings_path."""
    import os
    def mock_fdopen(*args, **kwargs):
        raise OSError("Mock error")

    monkeypatch.setattr(os, "fdopen", mock_fdopen)
    # Should raise exception because it's fatal for startup
    with pytest.raises(OSError, match="Mock error"):
        _get_settings_path(18888)
