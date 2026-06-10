"""Tests for PatchrightStrategy."""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.strategies.patchright_browser import PatchrightConfig, PatchrightStrategy

NORMAL_HTML = "<html><body><h1>Hello World</h1></body></html>"
CF_JS_CHALLENGE_HTML = "<html><body><div class='cf-browser-verification'>just a moment...</div></body></html>"
CF_MANAGED_HTML = "<html><body><div id='managed_checking_msg'>managed challenge</div></body></html>"


def _make_mock_provider(html: str, url: str = "https://example.com", status: int = 200):
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value=html)
    mock_page.url = url
    mock_page.close = AsyncMock()
    mock_page.context = MagicMock()
    mock_page.context.cookies = AsyncMock(return_value=[])

    mock_response = MagicMock()
    mock_response.status = status
    mock_page.goto = AsyncMock(return_value=mock_response)

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    mock_provider = AsyncMock()
    mock_provider.launch = AsyncMock(return_value=mock_browser)
    mock_provider.close = AsyncMock()

    return mock_provider, mock_page


class TestPatchrightStrategy:
    @pytest.fixture(autouse=True)
    def mock_safe_url(self):
        with patch("web_core.scraper.strategies.patchright_browser.is_safe_url", return_value=True):
            yield

    async def test_fetch_success(self):
        provider, _page = _make_mock_provider(NORMAL_HTML)
        strategy = PatchrightStrategy(provider=provider)

        result = await strategy.fetch("https://example.com")

        assert result.content == NORMAL_HTML
        assert result.url == "https://example.com"
        assert result.strategy == "patchright"
        assert result.status_code == 200
        assert result.metadata["rendered"] is True
        assert result.metadata["cf_challenge"] is None

    async def test_fetch_js_challenge_resolves(self):
        """CF JS challenge should wait and poll."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        # After wait, content changes to normal
        content_calls = 0

        async def content_side_effect():
            nonlocal content_calls
            content_calls += 1
            if content_calls >= 2:
                return NORMAL_HTML
            return CF_JS_CHALLENGE_HTML

        page.content = AsyncMock(side_effect=content_side_effect)

        strategy = PatchrightStrategy(provider=provider)
        with patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01):
            result = await strategy.fetch("https://cf-protected.com")

        assert result.metadata["cf_challenge"] is None  # Resolved after polling
        assert result.content == NORMAL_HTML

    async def test_cf_verification_cookie_resolves(self):
        """CF JS challenge resolves when __cf_bm cookie is set (line 67-68)."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        # Initially no cookie, then cookie appears
        cookie_calls = 0

        async def cookies_side_effect():
            nonlocal cookie_calls
            cookie_calls += 1
            if cookie_calls >= 2:
                return [{"name": "__cf_bm", "value": "abc123"}]
            return []

        page.context.cookies = AsyncMock(side_effect=cookies_side_effect)

        # Content stays challenge HTML during wait, then returns normal HTML in final call
        content_calls = 0

        async def content_side_effect():
            nonlocal content_calls
            content_calls += 1
            if content_calls >= 3:
                return NORMAL_HTML
            return CF_JS_CHALLENGE_HTML

        page.content = AsyncMock(side_effect=content_side_effect)

        strategy = PatchrightStrategy(provider=provider)
        with patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01):
            result = await strategy.fetch("https://cf-protected.com")

        assert result.content == NORMAL_HTML

    async def test_fetch_js_challenge_exhausts_polls(self):
        """CF JS challenge stays unresolved after all poll attempts (line 75)."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        # Content always stays challenge, no cookies
        page.context.cookies = AsyncMock(return_value=[])
        page.content = AsyncMock(return_value=CF_JS_CHALLENGE_HTML)

        strategy = PatchrightStrategy(provider=provider)
        with (
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_MAX_CHECKS", 2),
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01),
        ):
            result = await strategy.fetch("https://cf-stuck.com")

        assert "just a moment..." in result.content.lower()
        assert result.metadata["cf_challenge"] == "js_challenge"

    async def test_fetch_managed_challenge_waits(self):
        """Managed challenge should wait and poll."""
        provider, page = _make_mock_provider(CF_MANAGED_HTML)

        # After wait, content changes to normal
        content_calls = 0

        async def content_side_effect():
            nonlocal content_calls
            content_calls += 1
            if content_calls >= 2:
                return NORMAL_HTML
            return CF_MANAGED_HTML

        page.content = AsyncMock(side_effect=content_side_effect)

        strategy = PatchrightStrategy(provider=provider)
        with (
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_MAX_CHECKS", 5),
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01),
        ):
            result = await strategy.fetch("https://managed.com")

        assert result.content == NORMAL_HTML
        assert result.metadata["cf_challenge"] is None

    async def test_browser_cleanup_on_success(self):
        provider, page = _make_mock_provider(NORMAL_HTML)
        strategy = PatchrightStrategy(provider=provider)

        await strategy.fetch("https://example.com")

        page.close.assert_awaited_once()
        provider.close.assert_awaited_once()

    async def test_browser_cleanup_on_error(self):
        provider, page = _make_mock_provider(NORMAL_HTML)
        page.goto = AsyncMock(side_effect=TimeoutError("Navigation timeout"))
        strategy = PatchrightStrategy(provider=provider)

        with contextlib.suppress(TimeoutError):
            await strategy.fetch("https://timeout.com")

        page.close.assert_awaited_once()
        provider.close.assert_awaited_once()

    async def test_custom_timeout(self):
        provider, page = _make_mock_provider(NORMAL_HTML)
        strategy = PatchrightStrategy(provider=provider, timeout=30.0)

        await strategy.fetch("https://example.com")

        page.goto.assert_awaited_once()
        call_kwargs = page.goto.call_args
        assert call_kwargs[1]["timeout"] == 30000.0

    async def test_fetch_uses_patchright_provider_when_no_provider(self):
        """When no provider injected, instantiates PatchrightProvider."""
        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value=NORMAL_HTML)
        mock_page.url = "https://example.com"
        mock_page.close = AsyncMock()
        mock_page.context = MagicMock()
        mock_page.context.cookies = AsyncMock(return_value=[])

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        mock_provider_instance = AsyncMock()
        mock_provider_instance.launch = AsyncMock(return_value=mock_browser)
        mock_provider_instance.close = AsyncMock()

        with patch(
            "web_core.browsers.patchright.PatchrightProvider",
            return_value=mock_provider_instance,
        ):
            strategy = PatchrightStrategy()
            result = await strategy.fetch("https://example.com")

        assert result.content == NORMAL_HTML
        mock_provider_instance.close.assert_awaited_once()

    async def test_goto_returns_none_response(self):
        provider, page = _make_mock_provider(NORMAL_HTML)
        page.goto = AsyncMock(return_value=None)

        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://example.com")

        assert result.status_code == 200

    async def test_fetch_initial_networkidle_timeout(self):
        """Cover lines 113-115: Initial networkidle timeout."""
        provider, page = _make_mock_provider(NORMAL_HTML)
        page.wait_for_load_state = AsyncMock(side_effect=TimeoutError("networkidle timeout"))

        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://example.com")

        assert result.content == NORMAL_HTML
        assert result.metadata["cf_challenge"] is None

    async def test_fetch_js_resolution_networkidle_timeout(self):
        """Cover lines 127-128: networkidle timeout after JS resolution."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        content_calls = 0

        async def content_side_effect():
            nonlocal content_calls
            content_calls += 1
            if content_calls >= 2:
                return NORMAL_HTML
            return CF_JS_CHALLENGE_HTML

        page.content = AsyncMock(side_effect=content_side_effect)
        page.wait_for_load_state = AsyncMock(side_effect=TimeoutError("networkidle timeout"))

        strategy = PatchrightStrategy(provider=provider)
        with patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01):
            result = await strategy.fetch("https://cf-resolve-timeout.com")

        assert result.content == NORMAL_HTML

    async def test_fetch_managed_resolution_networkidle_timeout(self):
        """Cover lines 155-156: networkidle timeout after managed resolution."""
        provider, page = _make_mock_provider(CF_MANAGED_HTML)

        content_calls = 0

        async def content_side_effect():
            nonlocal content_calls
            content_calls += 1
            if content_calls >= 2:
                return NORMAL_HTML
            return CF_MANAGED_HTML

        page.content = AsyncMock(side_effect=content_side_effect)
        page.wait_for_load_state = AsyncMock(side_effect=TimeoutError("networkidle timeout"))

        strategy = PatchrightStrategy(provider=provider, cf_wait=0.01)
        with patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01):
            result = await strategy.fetch("https://managed-resolve-timeout.com")

        assert result.content == NORMAL_HTML

    async def test_managed_challenge_unresolved_hits_navigation_and_content(self):
        """Cover lines 146-147: Managed challenge unresolved, hits domcontentloaded then content."""
        provider, page = _make_mock_provider(CF_MANAGED_HTML)

        # Content stays managed
        page.content = AsyncMock(return_value=CF_MANAGED_HTML)

        strategy = PatchrightStrategy(provider=provider)
        with (
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_MAX_CHECKS", 1),
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01),
        ):
            result = await strategy.fetch("https://managed-stuck.com")

        assert result.metadata["cf_challenge"] == "managed"
        # Verify domcontentloaded was awaited
        page.wait_for_load_state.assert_awaited_with("domcontentloaded", timeout=15000)

    async def test_managed_challenge_wait_for_load_state_exception(self):
        """Managed challenge handles exception in wait_for_load_state (line 148-149)."""
        provider, page = _make_mock_provider(CF_MANAGED_HTML)

        page.content = AsyncMock(return_value=CF_MANAGED_HTML)

        # Mock wait_for_load_state to timeout for "domcontentloaded"
        async def wait_side_effect(state, timeout=None):
            if state == "domcontentloaded":
                raise TimeoutError("domcontentloaded timeout")
            return None

        page.wait_for_load_state = AsyncMock(side_effect=wait_side_effect)

        strategy = PatchrightStrategy(provider=provider)
        with (
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_MAX_CHECKS", 1),
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01),
        ):
            result = await strategy.fetch("https://managed-timeout.com")

        assert result.strategy == "patchright"

    async def test_config_object_init(self):
        """Verify initialization with PatchrightConfig object."""
        provider, page = _make_mock_provider(NORMAL_HTML)
        config = PatchrightConfig(timeout=45.0, headless=False)
        strategy = PatchrightStrategy(config=config, provider=provider)

        assert strategy.config.timeout == 45.0
        assert strategy.config.headless is False

        await strategy.fetch("https://example.com")
        page.goto.assert_awaited_once()
        call_kwargs = page.goto.call_args
        assert call_kwargs[1]["timeout"] == 45000.0

    async def test_lazy_provider_init(self):
        """Verify PatchrightProvider is lazily initialized when not provided."""
        mock_provider_instance = AsyncMock()
        mock_provider_instance.launch = AsyncMock()
        mock_provider_instance.close = AsyncMock()

        with patch("web_core.browsers.patchright.PatchrightProvider", return_value=mock_provider_instance):
            strategy = PatchrightStrategy()
            # Suppress all exceptions because we only care about the instantiation
            with contextlib.suppress(Exception):
                await strategy.fetch("https://example.com")

        assert mock_provider_instance.launch.called

    async def test_ssrf_protection_triggered(self):
        """Cover line 103: SSRF protection."""
        strategy = PatchrightStrategy()
        with (
            patch("web_core.scraper.strategies.patchright_browser.is_safe_url", return_value=False),
            pytest.raises(ValueError, match="SSRF blocked"),
        ):
            await strategy.fetch("http://169.254.169.254")

    async def test_managed_challenge_recheck_resolves(self):
        """Cover line 146: managed challenge resolved after domcontentloaded."""
        provider, page = _make_mock_provider(CF_MANAGED_HTML)

        # Initial content is challenge, then it resolves after domcontentloaded
        content_calls = 0

        async def content_side_effect():
            nonlocal content_calls
            content_calls += 1
            if content_calls >= 3:  # 1 for detect, 1 for loop (exhausted), 1 for re-check
                return NORMAL_HTML
            return CF_MANAGED_HTML

        page.content = AsyncMock(side_effect=content_side_effect)

        strategy = PatchrightStrategy(provider=provider)
        with (
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_MAX_CHECKS", 1),
            patch("web_core.scraper.strategies.patchright_browser._CF_POLL_INTERVAL", 0.01),
        ):
            result = await strategy.fetch("https://managed-resolve-late.com")

        assert result.metadata["cf_challenge"] is None
        assert result.content == NORMAL_HTML

    async def test_turnstile_detected(self):
        """Cover line 146: turnstile detected."""
        provider, _page = _make_mock_provider("<html><body><div class='cf-turnstile-response'></div></body></html>")
        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://turnstile.com")
        assert result.metadata["cf_challenge"] == "turnstile"
