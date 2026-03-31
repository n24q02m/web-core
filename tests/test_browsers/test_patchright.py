"""Tests for Patchright browser provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from web_core.browsers.patchright import PatchrightProvider
from web_core.browsers.protocol import BrowserProvider


class TestPatchrightProvider:
    def test_name(self):
        p = PatchrightProvider()
        assert p.name == "patchright"

    def test_supports_arm64(self):
        p = PatchrightProvider()
        assert p.supports_arm64 is True

    def test_satisfies_protocol(self):
        assert isinstance(PatchrightProvider(), BrowserProvider)

    def test_default_headless(self):
        p = PatchrightProvider()
        assert p._headless is True

    def test_custom_headless(self):
        p = PatchrightProvider(headless=False)
        assert p._headless is False

    async def test_launch(self):
        mock_browser = MagicMock()
        mock_pw = MagicMock()
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_start = AsyncMock(return_value=mock_pw)
        mock_async_pw = MagicMock()
        mock_async_pw.start = mock_start

        with patch("patchright.async_api.async_playwright", return_value=mock_async_pw):
            p = PatchrightProvider()
            result = await p.launch()
            assert result is mock_browser
            assert p._playwright is mock_pw
            assert p._browser is mock_browser

    async def test_launch_with_config(self):
        mock_browser = MagicMock()
        mock_pw = MagicMock()
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_start = AsyncMock(return_value=mock_pw)
        mock_async_pw = MagicMock()
        mock_async_pw.start = mock_start

        with patch("patchright.async_api.async_playwright", return_value=mock_async_pw):
            p = PatchrightProvider()
            result = await p.launch(config={"slow_mo": 100})
            assert result is mock_browser
            call_kwargs = mock_pw.chromium.launch.call_args[1]
            assert call_kwargs["slow_mo"] == 100

    async def test_close(self):
        p = PatchrightProvider()
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        p._browser = mock_browser
        p._playwright = mock_playwright
        await p.close()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        assert p._browser is None
        assert p._playwright is None

    async def test_close_without_launch(self):
        p = PatchrightProvider()
        await p.close()  # Should not raise
