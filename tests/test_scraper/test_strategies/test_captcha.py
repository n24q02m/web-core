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

    async def test_fetch_no_capsolver_with_fallback_delegates(self):
        """fetch without capsolver_api_key but with fallback delegates to fallback."""
        fallback = MockFallbackStrategy(content="<html>from fallback</html>")
        strategy = CaptchaStrategy(fallback_strategy=fallback)
        result = await strategy.fetch("https://example.com")

        assert result.content == "<html>from fallback</html>"
        assert result.metadata["captcha_solved"] is False
        assert result.metadata["from_fallback"] is True


class TestTrySolveTurnstile:
    """Tests for _try_solve_turnstile method."""

    async def test_non_turnstile_returns_empty(self):
        """_try_solve_turnstile returns empty for non-turnstile HTML."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._try_solve_turnstile(
            "https://example.com",
            "<html><body>Normal page</body></html>",
        )
        assert result == ""

    async def test_turnstile_no_sitekey_returns_empty(self):
        """_try_solve_turnstile returns empty when sitekey not found."""
        html = (
            "<html><head></head><body>"
            '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'
            "</body></html>"
        )
        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._try_solve_turnstile("https://example.com", html)
        assert result == ""

    async def test_turnstile_with_sitekey_solves(self):
        """_try_solve_turnstile extracts sitekey and solves."""
        html = (
            "<html><head></head><body>"
            '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'
            '<div data-sitekey="0x4AAAAAAADnPIDROrmt1Wwj"></div>'
            "</body></html>"
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"token": "turnstile-token-123"},
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        result = await strategy._try_solve_turnstile("https://example.com", html)
        assert result == "turnstile-token-123"


class TestExtractTurnstileSitekey:
    """Tests for _extract_turnstile_sitekey method (Patchright page extraction)."""

    async def test_extract_from_data_sitekey_attribute(self):
        """Extract sitekey from data-sitekey attribute on page element."""
        mock_el = AsyncMock()
        mock_el.get_attribute = AsyncMock(return_value="0x4AAAA_data_key")

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_el)

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result == "0x4AAAA_data_key"

    async def test_extract_from_iframe_src(self):
        """Extract sitekey from CF Turnstile iframe src URL."""
        mock_el = AsyncMock()
        mock_el.get_attribute = AsyncMock(return_value=None)  # no data-sitekey

        mock_iframe = AsyncMock()
        mock_iframe.get_attribute = AsyncMock(
            return_value="https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/0x4AAAAAAADnPIDROrmt1Wwj/light/normal"
        )

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)  # no data-sitekey element
        mock_page.query_selector_all = AsyncMock(return_value=[mock_iframe])

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result == "0x4AAAAAAADnPIDROrmt1Wwj"

    async def test_extract_from_inline_script(self):
        """Extract sitekey from inline script."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mock_iframe = AsyncMock()
        mock_iframe.get_attribute = AsyncMock(return_value="https://example.com/no-sitekey")

        mock_script = AsyncMock()
        mock_script.text_content = AsyncMock(return_value="turnstile.render({sitekey: '0x4AAAA_script_key'})")

        mock_page.query_selector_all = AsyncMock(
            side_effect=[
                [mock_iframe],  # iframes
                [mock_script],  # scripts
            ]
        )

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result == "0x4AAAA_script_key"

    async def test_extract_returns_none_when_not_found(self):
        """Returns None when no sitekey found anywhere."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("timeout"))
        mock_page.query_selector = AsyncMock(return_value=None)

        mock_iframe = AsyncMock()
        mock_iframe.get_attribute = AsyncMock(return_value="")

        mock_script = AsyncMock()
        mock_script.text_content = AsyncMock(return_value="var x = 1;")

        mock_page.query_selector_all = AsyncMock(
            side_effect=[
                [mock_iframe],  # iframes
                [mock_script],  # scripts
            ]
        )

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result is None

    async def test_extract_iframe_fallback_pattern(self):
        """Extract sitekey using fallback pattern from iframe src (light/dark/auto)."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mock_iframe = AsyncMock()
        mock_iframe.get_attribute = AsyncMock(
            return_value="https://challenges.cloudflare.com/LongAlphanumericString12/light/normal"
        )

        mock_page.query_selector_all = AsyncMock(return_value=[mock_iframe])

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result == "LongAlphanumericString12"


def _make_mock_patchright(page_content="<html>challenge</html>", page_url="https://example.com"):
    """Create mock PatchrightProvider and page for captcha tests."""
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value=page_content)
    mock_page.url = page_url
    mock_page.close = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.evaluate = AsyncMock()
    mock_page.wait_for_load_state = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    mock_provider = AsyncMock()
    mock_provider.launch = AsyncMock(return_value=mock_browser)
    mock_provider.close = AsyncMock()

    # Create a callable class that returns mock_provider when instantiated
    mock_cls = MagicMock(return_value=mock_provider)

    return mock_cls, mock_provider, mock_page


class TestSolveCfTurnstileViaPatchright:
    """Tests for _solve_cf_turnstile_via_patchright."""

    async def test_sitekey_not_found_returns_fallback(self):
        """When sitekey cannot be extracted, returns fallback result."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        mock_cls, _, _ = _make_mock_patchright()

        with (
            patch("web_core.browsers.patchright.PatchrightProvider", mock_cls),
            patch.object(strategy, "_extract_turnstile_sitekey", return_value=None),
        ):
            result = await strategy._solve_cf_turnstile_via_patchright("https://example.com")

        assert result.metadata["captcha_solved"] is False
        assert result.metadata["error"] == "sitekey_not_found"

    async def test_capsolver_no_token_returns_fallback(self):
        """When CapSolver returns no token, returns fallback result."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"errorId": 1}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        mock_cls, _, _ = _make_mock_patchright()

        with (
            patch("web_core.browsers.patchright.PatchrightProvider", mock_cls),
            patch.object(strategy, "_extract_turnstile_sitekey", return_value="0x4AAAA_key"),
        ):
            result = await strategy._solve_cf_turnstile_via_patchright("https://example.com")

        assert result.metadata["captcha_solved"] is False
        assert result.metadata["error"] == "capsolver_no_token"

    async def test_successful_solve_returns_content(self):
        """When CapSolver solves successfully, injects token and returns content."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"token": "solved-turnstile-token"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        mock_cls, _, mock_page = _make_mock_patchright(
            page_content="<html>real content after solve</html>",
            page_url="https://example.com/real",
        )

        with (
            patch("web_core.browsers.patchright.PatchrightProvider", mock_cls),
            patch.object(strategy, "_extract_turnstile_sitekey", return_value="0x4AAAA_key"),
        ):
            result = await strategy._solve_cf_turnstile_via_patchright("https://example.com")

        assert result.metadata["captcha_solved"] is True
        assert result.content == "<html>real content after solve</html>"
        mock_page.evaluate.assert_called_once()
