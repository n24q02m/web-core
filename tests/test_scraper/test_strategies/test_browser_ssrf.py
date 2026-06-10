import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web_core.http.client import setup_browser_ssrf_protection
from web_core.scraper.strategies.captcha import CaptchaStrategy
from web_core.scraper.strategies.patchright_browser import PatchrightStrategy

@pytest.mark.asyncio
async def test_setup_browser_ssrf_protection_aborts_unsafe():
    mock_page = AsyncMock()
    mock_route = AsyncMock()
    mock_route.request.url = "http://127.0.0.1/private"

    # Capture the handler passed to page.route
    await setup_browser_ssrf_protection(mock_page)
    mock_page.route.assert_called_once()
    args, kwargs = mock_page.route.call_args
    assert args[0] == "**/*"
    handler = args[1]

    with patch("web_core.http.client.is_safe_url", return_value=False):
        await handler(mock_route)

    mock_route.abort.assert_called_once_with("blockedbyclient")
    mock_route.continue_.assert_not_called()

@pytest.mark.asyncio
async def test_setup_browser_ssrf_protection_allows_safe():
    mock_page = AsyncMock()
    mock_route = AsyncMock()
    mock_route.request.url = "https://example.com"

    await setup_browser_ssrf_protection(mock_page)
    handler = mock_page.route.call_args[0][1]

    with patch("web_core.http.client.is_safe_url", return_value=True):
        await handler(mock_route)

    mock_route.continue_.assert_called_once()
    mock_route.abort.assert_not_called()

@pytest.mark.asyncio
async def test_setup_browser_ssrf_protection_allows_special_schemes():
    mock_page = AsyncMock()
    mock_route = AsyncMock()

    await setup_browser_ssrf_protection(mock_page)
    handler = mock_page.route.call_args[0][1]

    for url in ["data:image/png;base64,xxx", "blob:https://example.com/uuid", "about:blank"]:
        mock_route.request.url = url
        mock_route.continue_ = AsyncMock()
        await handler(mock_route)
        mock_route.continue_.assert_called_once()

def _make_mock_patchright_for_ssrf():
    mock_page = AsyncMock()
    mock_page.close = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html></html>")

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    mock_provider = AsyncMock()
    mock_provider.launch = AsyncMock(return_value=mock_browser)
    mock_provider.close = AsyncMock()

    mock_cls = MagicMock(return_value=mock_provider)
    return mock_cls, mock_page

@pytest.mark.asyncio
async def test_captcha_strategy_calls_setup_ssrf():
    strategy = CaptchaStrategy(capsolver_api_key="key")
    mock_cls, mock_page = _make_mock_patchright_for_ssrf()

    with (
        patch("web_core.browsers.patchright.PatchrightProvider", mock_cls),
        patch("web_core.scraper.strategies.captcha.is_safe_url", return_value=True),
        patch("web_core.scraper.strategies.captcha.setup_browser_ssrf_protection", AsyncMock()) as mock_setup
    ):
        # We need to mock _extract_turnstile_sitekey to avoid further calls
        with patch.object(strategy, "_extract_turnstile_sitekey", return_value=None):
            await strategy.fetch("https://example.com")

    mock_setup.assert_called_once_with(mock_page)

@pytest.mark.asyncio
async def test_patchright_strategy_calls_setup_ssrf():
    strategy = PatchrightStrategy()
    mock_cls, mock_page = _make_mock_patchright_for_ssrf()

    # PatchrightStrategy might use internal _provider or launch its own
    with (
        patch("web_core.browsers.patchright.PatchrightProvider", mock_cls),
        patch("web_core.scraper.strategies.patchright_browser.is_safe_url", return_value=True),
        patch("web_core.scraper.strategies.patchright_browser.setup_browser_ssrf_protection", AsyncMock()) as mock_setup,
        patch("web_core.scraper.strategies.patchright_browser.detect_cloudflare_challenge", return_value=None)
    ):
        await strategy.fetch("https://example.com")

    mock_setup.assert_called_once_with(mock_page)
