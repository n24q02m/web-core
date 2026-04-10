from unittest.mock import MagicMock, patch

import pytest

from web_core.search.runner import _SEARXNG_INSTALL_URL, _install_searxng


@pytest.mark.asyncio
async def test_install_searxng_validates_url():
    """Verify that _install_searxng validates the URL and uses the pinned one."""
    with (
        patch("web_core.search.runner.subprocess.run") as mock_run,
        patch("web_core.search.runner._get_pip_command", return_value=["pip", "install"]),
    ):
        # Mock successful build deps install
        mock_deps_result = MagicMock()
        mock_deps_result.returncode = 0

        # Mock successful searxng install
        mock_install_result = MagicMock()
        mock_install_result.returncode = 0

        mock_run.side_effect = [mock_deps_result, mock_install_result]

        # Should succeed with the pinned URL
        assert _install_searxng() is True

        # Verify the second call to subprocess.run used the pinned URL
        args, _ = mock_run.call_args_list[1]
        cmd = args[0]
        assert _SEARXNG_INSTALL_URL in cmd
        assert "#sha256=" in _SEARXNG_INSTALL_URL
        assert "https://github.com/searxng/searxng/archive/" in _SEARXNG_INSTALL_URL


def test_install_searxng_fails_on_invalid_url(monkeypatch):
    """Verify that _install_searxng fails if the URL is tampered with."""
    # Tamper with the URL
    monkeypatch.setattr("web_core.search.runner._SEARXNG_INSTALL_URL", "https://malicious.com/payload.zip")

    with (
        patch("web_core.search.runner._get_pip_command", return_value=["pip", "install"]),
        patch("web_core.search.runner.subprocess.run") as mock_run,
    ):
        # Mock successful build deps install
        mock_deps_result = MagicMock()
        mock_deps_result.returncode = 0
        mock_run.return_value = mock_deps_result

        # Should fail due to validation
        assert _install_searxng() is False

        # Should not have attempted the second subprocess.run (the actual install)
        assert mock_run.call_count == 1
