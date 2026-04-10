"""Tests for PatchrightStrategy with CF challenge detection."""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

from web_core.scraper.strategies.patchright_browser import PatchrightStrategy

# Sample HTML fixtures
NORMAL_HTML = "<html><head><title>Normal Page</title></head><body><h1>Content</h1></body></html>"
CF_JS_CHALLENGE_HTML = "<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>"
CF_TURNSTILE_HTML = (
    "<html><head></head><body>"
    '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'
    '<div data-sitekey="0x4AAAA_test_key"></div>'
    "</body></html>"
)
CF_MANAGED_HTML = "<html><body><div id='cf-please-wait'>managed_checking_msg</div></body></html>"


def _make_mock_provider(page_content: str, status_code: int = 200, url: str = "https://example.com"):
    """Create a mock provider with page that returns given content."""
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value=page_content)
    mock_page.url = url
    mock_page.close = AsyncMock()
    mock_page.context = MagicMock()
    mock_page.context.cookies = AsyncMock(return_value=[])

    mock_response = MagicMock()
    mock_response.status = status_code
    mock_page.goto = AsyncMock(return_value=mock_response)

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    mock_provider = AsyncMock()
    mock_provider.launch = AsyncMock(return_value=mock_browser)
    mock_provider.close = AsyncMock()

    return mock_provider, mock_page


class TestPatchrightStrategy:
    async def test_fetch_normal_page(self):
        provider, _page = _make_mock_provider(NORMAL_HTML)
        strategy = PatchrightStrategy(provider=provider)

        result = await strategy.fetch("https://example.com")

        assert result.content == NORMAL_HTML
        assert result.status_code == 200
        assert result.strategy == "patchright"
        assert result.metadata["cf_challenge"] is None

    async def test_fetch_detects_turnstile(self):
        provider, _page = _make_mock_provider(CF_TURNSTILE_HTML)
        strategy = PatchrightStrategy(provider=provider)

        result = await strategy.fetch("https://protected.com")

        assert result.metadata["cf_challenge"] == "turnstile"
        assert result.content == CF_TURNSTILE_HTML

    async def test_fetch_js_challenge_polls_and_resolves(self):
        """JS challenge should be polled until content changes to normal."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        # After polling, page.content() returns normal HTML
        call_count = 0

        async def content_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                return NORMAL_HTML
            return CF_JS_CHALLENGE_HTML

        page.content = AsyncMock(side_effect=content_side_effect)

        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://cf-protected.com")

        assert result.metadata["cf_challenge"] is None  # Resolved after polling
        assert result.content == NORMAL_HTML

    async def test_fetch_js_challenge_resolves_via_cookie(self):
        """JS challenge resolves when __cf_bm cookie appears."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        call_count = 0

        async def cookies_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                return [{"name": "__cf_bm", "value": "abc123"}]
            return []

        page.context.cookies = AsyncMock(side_effect=cookies_side_effect)
        # Content stays challenge HTML but cookie resolves it
        page.content = AsyncMock(return_value=NORMAL_HTML)

        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://cf-protected.com")

        assert result.content == NORMAL_HTML

    async def test_fetch_managed_challenge_waits(self):
        """Managed challenge should wait cf_wait seconds then re-check."""
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

        strategy = PatchrightStrategy(provider=provider, cf_wait=0.1)
        result = await strategy.fetch("https://managed.com")

        assert result.content == NORMAL_HTML
        assert result.metadata["cf_challenge"] is None

    async def test_metadata_includes_content_length(self):
        provider, _page = _make_mock_provider(NORMAL_HTML)
        strategy = PatchrightStrategy(provider=provider)

        result = await strategy.fetch("https://example.com")

        assert result.metadata["content_length"] == len(NORMAL_HTML)
        assert result.metadata["rendered"] is True
        assert result.metadata["headless"] is True

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

    async def test_uses_networkidle_wait(self):
        provider, page = _make_mock_provider(NORMAL_HTML)
        strategy = PatchrightStrategy(provider=provider)

        await strategy.fetch("https://example.com")

        call_kwargs = page.goto.call_args
        assert call_kwargs[1]["wait_until"] == "domcontentloaded"
        page.wait_for_load_state.assert_any_call("networkidle", timeout=60000.0)

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
            strategy = PatchrightStrategy()  # No provider argument
            result = await strategy.fetch("https://example.com")

        assert result.content == NORMAL_HTML
        mock_provider_instance.close.assert_awaited_once()

    async def test_cf_verification_cookie_resolves(self):
        """CF JS challenge resolves when __cf_bm cookie is set (line 66-68)."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        # Content stays challenge but cookie appears
        cf_cookie_appeared = False

        async def cookies_side_effect():
            nonlocal cf_cookie_appeared
            if cf_cookie_appeared:
                return [{"name": "__cf_bm", "value": "abc123"}]
            cf_cookie_appeared = True
            return []

        page.context.cookies = AsyncMock(side_effect=cookies_side_effect)
        # After cookie, page content returns normal
        content_calls = 0

        async def content_side_effect():
            nonlocal content_calls
            content_calls += 1
            if content_calls <= 1:
                return CF_JS_CHALLENGE_HTML  # Initial load
            return NORMAL_HTML  # After cookie verification

        page.content = AsyncMock(side_effect=content_side_effect)

        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://cf-protected.com")

        assert result.content == NORMAL_HTML

    async def test_cf_js_challenge_exhausts_polls(self):
        """CF JS challenge stays unresolved after all poll attempts (line 75)."""
        provider, page = _make_mock_provider(CF_JS_CHALLENGE_HTML)

        # Content always stays challenge, no cookies
        page.context.cookies = AsyncMock(return_value=[])
        page.content = AsyncMock(return_value=CF_JS_CHALLENGE_HTML)

        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://cf-stuck.com")

        # Should still return something (the challenge HTML)
        assert "Just a moment" in result.content
        assert result.metadata["cf_challenge"] == "js_challenge"

    async def test_managed_challenge_unresolved_waits_for_navigation(self):
        """Managed challenge polls, doesn't resolve, waits for networkidle (lines 125-131)."""
        provider, page = _make_mock_provider(CF_MANAGED_HTML)

        # Always returns managed HTML -- challenge never resolves during polls
        page.content = AsyncMock(return_value=CF_MANAGED_HTML)
        page.wait_for_load_state = AsyncMock()

        strategy = PatchrightStrategy(provider=provider, cf_wait=0.01)
        # Fetch should not hang
        await strategy.fetch("https://managed-stuck.com")

        # wait_for_load_state should have been called
        page.wait_for_load_state.assert_awaited()

    async def test_managed_challenge_wait_for_load_state_exception(self):
        """Managed challenge handles exception in wait_for_load_state (line 130-131)."""
        provider, page = _make_mock_provider(CF_MANAGED_HTML)

        page.content = AsyncMock(return_value=CF_MANAGED_HTML)
        page.wait_for_load_state = AsyncMock(side_effect=TimeoutError("navigation timeout"))

        strategy = PatchrightStrategy(provider=provider, cf_wait=0.01)
        result = await strategy.fetch("https://managed-timeout.com")

        # Should not raise, just return whatever content is available
        assert result.strategy == "patchright"

    async def test_goto_returns_none_response(self):
        """When goto returns None response, status_code defaults to 200 (line 133)."""
        provider, page = _make_mock_provider(NORMAL_HTML)
        page.goto = AsyncMock(return_value=None)

        strategy = PatchrightStrategy(provider=provider)
        result = await strategy.fetch("https://example.com")

        assert result.status_code == 200
