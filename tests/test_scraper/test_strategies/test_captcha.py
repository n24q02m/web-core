"""Tests for CaptchaStrategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from web_core.scraper.base import BaseStrategy, ScrapingResult
from web_core.scraper.strategies.captcha import CaptchaStrategy


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
            metadata={"from_fallback": True},
        )


class TestCaptchaStrategy:
    """Test CapSolver CAPTCHA strategy."""

    def test_name(self):
        strategy = CaptchaStrategy()
        assert strategy.name == "captcha"

    def test_default_capsolver_api_key(self):
        strategy = CaptchaStrategy()
        assert strategy.capsolver_api_key == ""

    def test_custom_capsolver_api_key(self):
        strategy = CaptchaStrategy(capsolver_api_key="test-key-123")
        assert strategy.capsolver_api_key == "test-key-123"

    def test_default_fallback_strategy(self):
        strategy = CaptchaStrategy()
        assert strategy.fallback_strategy is None

    def test_capsolver_url(self):
        strategy = CaptchaStrategy()
        assert strategy.CAPSOLVER_URL == "https://api.capsolver.com/createTask"

    # ------------------------------------------------------------------
    # solve_captcha
    # ------------------------------------------------------------------

    async def test_solve_captcha_sends_correct_payload(self):
        """solve_captcha should POST correct payload to CapSolver."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"gRecaptchaResponse": "captcha-token-xyz"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="my-api-key", http_client=mock_client)
        token = await strategy.solve_captcha(site_key="6Le-site-key", page_url="https://example.com")

        assert token == "captcha-token-xyz"
        mock_client.post.assert_called_once_with(
            "https://api.capsolver.com/createTask",
            json={
                "clientKey": "my-api-key",
                "task": {
                    "type": "ReCaptchaV2TaskProxyLess",
                    "websiteURL": "https://example.com",
                    "websiteKey": "6Le-site-key",
                },
            },
        )

    async def test_solve_captcha_custom_type(self):
        """solve_captcha should support custom captcha types."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"gRecaptchaResponse": "token-v3"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha(
            site_key="site-key",
            page_url="https://example.com",
            captcha_type="ReCaptchaV3TaskProxyLess",
        )

        assert token == "token-v3"
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["task"]["type"] == "ReCaptchaV3TaskProxyLess"

    async def test_solve_captcha_empty_solution(self):
        """solve_captcha should return empty string when solution is missing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"errorId": 1, "errorCode": "ERROR_CAPTCHA_UNSOLVABLE"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha(site_key="key", page_url="https://example.com")

        assert token == ""

    async def test_solve_captcha_uses_safe_httpx_when_no_client(self):
        """When no http_client is injected, solve_captcha should use safe_httpx_client."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"gRecaptchaResponse": "safe-token"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        target = "web_core.scraper.strategies.captcha.safe_httpx_client"
        with patch(target, return_value=mock_client) as mock_factory:
            strategy = CaptchaStrategy(capsolver_api_key="key")
            token = await strategy.solve_captcha(site_key="sk", page_url="https://example.com")

            mock_factory.assert_called_once()
            assert token == "safe-token"

    # ------------------------------------------------------------------
    # fetch
    # ------------------------------------------------------------------

    async def test_fetch_with_site_key_solves_captcha_and_delegates(self):
        """fetch with site_key should solve captcha then delegate to fallback."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"gRecaptchaResponse": "solved-token"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        fallback = MockFallbackStrategy()
        strategy = CaptchaStrategy(
            capsolver_api_key="key",
            fallback_strategy=fallback,
            http_client=mock_client,
        )
        result = await strategy.fetch(
            "https://example.com",
            selectors={"site_key": "6Le-key"},
        )

        assert result.strategy == "captcha"
        assert result.content == "<html>fallback</html>"
        assert result.status_code == 200
        assert result.metadata["captcha_solved"] is True
        assert result.metadata["from_fallback"] is True

    async def test_fetch_without_site_key_uses_patchright_flow(self):
        """fetch with capsolver_api_key but no site_key uses Patchright+CapSolver flow."""
        mock_client = AsyncMock()

        strategy = CaptchaStrategy(
            capsolver_api_key="key",
            http_client=mock_client,
        )
        # Mock _solve_cf_turnstile_via_patchright to avoid real browser
        mock_result = ScrapingResult(
            content="<html>solved</html>",
            url="https://example.com",
            strategy="captcha",
            status_code=200,
            metadata={"captcha_solved": True},
        )
        with patch.object(strategy, "_solve_cf_turnstile_via_patchright", return_value=mock_result):
            result = await strategy.fetch("https://example.com", selectors={"other": "value"})

        assert result.metadata["captcha_solved"] is True
        assert result.content == "<html>solved</html>"

    async def test_fetch_with_none_selectors_skips_solving(self):
        """fetch with selectors=None and capsolver_api_key goes to patchright flow."""
        mock_client = AsyncMock()

        fallback = MockFallbackStrategy()
        strategy = CaptchaStrategy(
            capsolver_api_key="key",
            fallback_strategy=fallback,
            http_client=mock_client,
        )
        mock_result = ScrapingResult(
            content="<html>patchright</html>",
            url="https://example.com",
            strategy="captcha",
            status_code=200,
            metadata={"captcha_solved": False, "error": "sitekey_not_found"},
        )
        with patch.object(strategy, "_solve_cf_turnstile_via_patchright", return_value=mock_result):
            result = await strategy.fetch("https://example.com")

        mock_client.post.assert_not_called()
        assert result.metadata["captcha_solved"] is False

    async def test_fetch_without_fallback_with_site_key_skips_captcha(self):
        """fetch without fallback but WITH site_key: explicit flow but no fallback -> patchright flow."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        mock_result = ScrapingResult(
            content="",
            url="https://example.com",
            strategy="captcha",
            status_code=0,
            metadata={"captcha_solved": False, "error": "capsolver_no_token"},
        )
        with patch.object(strategy, "_solve_cf_turnstile_via_patchright", return_value=mock_result):
            result = await strategy.fetch(
                "https://example.com",
                selectors={"site_key": "6Le-key"},
            )
        # With site_key + fallback=None: goes to patchright flow (capsolver_api_key is set)
        assert result.strategy == "captcha"

    async def test_fetch_no_capsolver_no_fallback_returns_empty(self):
        """fetch without capsolver_api_key AND without fallback returns empty."""
        strategy = CaptchaStrategy()
        result = await strategy.fetch("https://example.com")

        assert result.content == ""
        assert result.status_code == 0
        assert result.metadata["captcha_solved"] is False
        assert result.metadata["error"] == "no_fallback_strategy"
