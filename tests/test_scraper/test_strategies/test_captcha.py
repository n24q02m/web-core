"""Tests for CaptchaStrategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.base import BaseStrategy, ScrapingResult
from web_core.scraper.strategies.captcha import CaptchaStrategy


@pytest.fixture(autouse=True)
def mock_is_safe_url():
    with patch("web_core.scraper.strategies.captcha.is_safe_url", return_value=True):
        yield


class MockFallbackStrategy(BaseStrategy):
    """Minimal fallback strategy for testing."""

    name: str = "mock_fallback"

    def __init__(self, content: str = "<html>fallback</html>", status_code: int = 200):
        self._content = content
        self._status_code = status_code

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        return ScrapingResult(
            content=self._content,
            url=url,
            strategy=self.name,
            status_code=self._status_code,
        )


class TestCaptchaStrategy:
    """Test CAPTCHA solving and strategy delegation."""

    def test_name(self):
        strategy = CaptchaStrategy()
        assert strategy.name == "captcha"

    @pytest.mark.asyncio
    async def test_fetch_delegates_to_fallback(self):
        fallback = MockFallbackStrategy()
        strategy = CaptchaStrategy(fallback_strategy=fallback)

        result = await strategy.fetch("https://example.com")

        assert result.content == "<html>fallback</html>"
        assert result.strategy == "captcha"
        assert result.metadata["captcha_solved"] is False

    @pytest.mark.asyncio
    async def test_fetch_no_fallback_error(self):
        strategy = CaptchaStrategy()
        result = await strategy.fetch("https://example.com")

        assert result.status_code == 0
        assert result.metadata["error"] == "no_fallback_strategy"

    @pytest.mark.asyncio
    async def test_solve_captcha_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"solution": {"gRecaptchaResponse": "token123"}}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha("sitekey", "https://example.com")

        assert token == "token123"

    @pytest.mark.asyncio
    async def test_solve_captcha_with_safe_client(self):
        """Test solve_captcha when it instantiates safe_httpx_client (lines 74-75)."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"solution": {"gRecaptchaResponse": "token123"}}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_resp

        with patch("web_core.scraper.strategies.captcha.safe_httpx_client") as mock_factory:
            mock_factory.return_value.__aenter__.return_value = mock_client_instance

            strategy = CaptchaStrategy(capsolver_api_key="key")
            token = await strategy.solve_captcha("sitekey", "https://example.com")

        assert token == "token123"
        mock_client_instance.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_solve_captcha_failure(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errorId": 1, "errorCode": "ERROR_KEY"}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha("sitekey", "https://example.com")

        assert token == ""

    @pytest.mark.asyncio
    async def test_fetch_explicit_captcha_solve(self):
        """Explicitly solve captcha when site_key provided in selectors (lines 247-260)."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"solution": {"gRecaptchaResponse": "token123"}}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        fallback = MockFallbackStrategy()
        strategy = CaptchaStrategy(capsolver_api_key="key", fallback_strategy=fallback, http_client=mock_client)

        result = await strategy.fetch("https://protected.com", {"site_key": "123"})

        assert result.metadata["captcha_solved"] is True
        assert result.content == "<html>fallback</html>"

    @pytest.mark.asyncio
    async def test_try_solve_turnstile_auto_detect(self):
        """Auto-detect and solve Turnstile (lines 89-106)."""
        html = '<html><div class="cf-turnstile-response" data-sitekey="0x4AAAAAAADnPIDROrmt1Wwj"></div></html>'
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"solution": {"token": "turnstile_token"}}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy._try_solve_turnstile("https://cf.com", html)

        assert token == "turnstile_token"

    @pytest.mark.asyncio
    async def test_try_solve_turnstile_no_challenge(self):
        """No challenge detected (lines 94-95)."""
        strategy = CaptchaStrategy()
        token = await strategy._try_solve_turnstile("https://normal.com", "<html>safe</html>")
        assert token == ""

    @pytest.mark.asyncio
    async def test_try_solve_turnstile_no_sitekey(self):
        """Turnstile detected but sitekey missing (lines 98-100)."""
        html = '<html><div class="cf-turnstile-response"></div></html>'
        strategy = CaptchaStrategy()
        token = await strategy._try_solve_turnstile("https://cf.com", html)
        assert token == ""

    @pytest.mark.asyncio
    async def test_extract_turnstile_sitekey_strategies(self):
        """Test multiple sitekey extraction strategies (lines 125-155)."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        # Mock Strategy 1: query_selector
        mock_el = AsyncMock()
        mock_el.get_attribute.return_value = "0x4AAAAAAADnPIDROrmt1Wwj"
        mock_page.query_selector.return_value = mock_el

        strategy = CaptchaStrategy()
        res1 = await strategy._extract_turnstile_sitekey(mock_page)
        assert res1 == "0x4AAAAAAADnPIDROrmt1Wwj"

        # Mock Strategy 2: iframe src
        mock_page.query_selector.return_value = None
        mock_page.evaluate.side_effect = [
            ["https://challenges.cloudflare.com/0x4AAAAAAADnPIDROrmt1Wwj/light/"],  # evaluate(iframe src)
            ["sitekey: '0x4AAAAAAADnPIDROrmt1Wwj'"],  # evaluate(script texts)
        ]

        res2 = await strategy._extract_turnstile_sitekey(mock_page)
        assert res2 == "0x4AAAAAAADnPIDROrmt1Wwj"

        # Mock Strategy 3: inline script
        mock_page.evaluate.side_effect = [
            [],  # no iframes
            ["sitekey: '0x4AAAAAAADnPIDROrmt1Wwj'"],  # evaluate(script texts)
        ]

        res3 = await strategy._extract_turnstile_sitekey(mock_page)
        assert res3 == "0x4AAAAAAADnPIDROrmt1Wwj"

    @pytest.mark.asyncio
    async def test_extract_turnstile_sitekey_not_found(self):
        """Cover line 155 return None."""
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None
        mock_page.evaluate.return_value = []

        strategy = CaptchaStrategy()
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result is None
