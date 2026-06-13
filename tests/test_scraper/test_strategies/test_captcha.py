from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.strategies.captcha import RECAPTCHA_V2_PROXYLESS, TURNSTILE_PROXYLESS, CaptchaStrategy


@pytest.mark.asyncio
class TestCaptchaStrategy:
    """Tests for CaptchaStrategy core logic."""

    async def test_solve_captcha_recaptcha(self):
        """solve_captcha calls CapSolver API for ReCaptcha."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"gRecaptchaResponse": "mock-token"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha(
            site_key="site-key",
            page_url="https://example.com",
            captcha_type=RECAPTCHA_V2_PROXYLESS,
        )

        assert token == "mock-token"
        mock_client.post.assert_called_once()
        payload = mock_client.post.call_args[1]["json"]
        assert payload["task"]["type"] == RECAPTCHA_V2_PROXYLESS
        assert payload["task"]["websiteKey"] == "site-key"

    async def test_solve_captcha_turnstile(self):
        """solve_captcha calls CapSolver API for Turnstile."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"token": "mock-turnstile-token"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha(
            site_key="0x4AAAA_key",
            page_url="https://example.com",
            captcha_type=TURNSTILE_PROXYLESS,
        )

        assert token == "mock-turnstile-token"
        payload = mock_client.post.call_args[1]["json"]
        assert payload["task"]["type"] == TURNSTILE_PROXYLESS

    async def test_solve_captcha_failure(self):
        """solve_captcha returns empty string on API failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"errorId": 1, "errorCode": "ERROR_KEY_INVALID"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="wrong", http_client=mock_client)
        token = await strategy.solve_captcha(site_key="sk", page_url="url")

        assert token == ""

    async def test_try_solve_turnstile_not_detected(self):
        """_try_solve_turnstile returns empty if CF not detected."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        with patch("web_core.scraper.strategies.captcha.detect_cloudflare_challenge", return_value=None):
            token = await strategy._try_solve_turnstile("https://ex.com", "<html>no challenge</html>")
            assert token == ""

    async def test_try_solve_turnstile_success(self):
        """_try_solve_turnstile detects and solves Turnstile."""
        strategy = CaptchaStrategy(capsolver_api_key="key")

        with (
            patch("web_core.scraper.strategies.captcha.detect_cloudflare_challenge", return_value="turnstile"),
            patch("web_core.scraper.strategies.captcha.extract_turnstile_sitekey", return_value="0x4AAAA_key"),
            patch.object(strategy, "solve_captcha", return_value="solved-token") as mock_solve,
        ):
            token = await strategy._try_solve_turnstile("https://ex.com", "<html>cf</html>")
            assert token == "solved-token"
            mock_solve.assert_called_once_with(
                site_key="0x4AAAA_key",
                page_url="https://ex.com",
                captcha_type=TURNSTILE_PROXYLESS,
            )


@pytest.mark.asyncio
class TestExtractTurnstileSitekey:
    """Tests for _extract_turnstile_sitekey (browser-level extraction)."""

    async def test_extract_from_data_attribute(self):
        """Extract sitekey from data-sitekey attribute."""
        mock_page = AsyncMock()
        mock_el = AsyncMock()
        mock_el.get_attribute = AsyncMock(return_value="0x4AAAA_static_key")
        mock_page.query_selector = AsyncMock(return_value=mock_el)

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result == "0x4AAAA_static_key"

    async def test_extract_from_iframe_src(self):
        """Extract sitekey from CF Turnstile iframe src URL."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)  # no data-sitekey element

        mock_iframe = AsyncMock()
        mock_iframe.get_attribute = AsyncMock(
            return_value="https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/0x4AAAAAAADnPIDROrmt1Wwj/light/normal"
        )

        mock_page.query_selector_all = AsyncMock(
            side_effect=[
                [mock_iframe],  # iframes
                [],  # scripts (won't be called if iframe matches)
            ]
        )

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

        mock_page.query_selector_all = AsyncMock(
            side_effect=[
                [mock_iframe],
                [],
            ]
        )

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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
class TestCaptchaCoverageEnhancement:
    """Additional tests to reach 100% coverage."""

    async def test_solve_captcha_no_http_client(self):
        """solve_captcha uses safe_httpx_client when no http_client is provided."""
        mock_response = MagicMock()
        # RECAPTCHA_V2_PROXYLESS expects "gRecaptchaResponse"
        mock_response.json.return_value = {"solution": {"gRecaptchaResponse": "default-client-token"}}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        strategy = CaptchaStrategy(capsolver_api_key="key")
        with patch("web_core.scraper.strategies.captcha.safe_httpx_client", return_value=mock_client):
            token = await strategy.solve_captcha(site_key="site-key", page_url="https://example.com")

        assert token == "default-client-token"
        mock_client.post.assert_called_once()

    async def test_extract_sitekey_iframe_no_regex_match(self):
        """_extract_turnstile_sitekey handles iframe src with /0x that doesn't match regex."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mock_iframe = AsyncMock()
        mock_iframe.get_attribute = AsyncMock(
            return_value="https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/0x/invalid"
        )

        mock_page.query_selector_all = AsyncMock(
            side_effect=[
                [mock_iframe],  # iframes
                [],  # scripts
            ]
        )

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result is None

    async def test_extract_sitekey_script_no_sitekey_keyword(self):
        """_extract_turnstile_sitekey skips scripts without sitekey keyword."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mock_script1 = AsyncMock()
        mock_script1.text_content = AsyncMock(return_value="console.log('hello');")
        mock_script2 = AsyncMock()
        mock_script2.text_content = AsyncMock(return_value="var x = 1;")

        mock_page.query_selector_all = AsyncMock(
            side_effect=[
                [],  # iframes
                [mock_script1, mock_script2],  # scripts
            ]
        )

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result is None

    async def test_extract_sitekey_script_regex_mismatch(self):
        """_extract_turnstile_sitekey handles script with sitekey keyword but no regex match."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mock_script = AsyncMock()
        mock_script.text_content = AsyncMock(return_value="var sitekey = 'too-short';")

        mock_page.query_selector_all = AsyncMock(
            side_effect=[
                [],  # iframes
                [mock_script],  # scripts
            ]
        )

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result is None

    async def test_solve_recaptcha_stub(self):
        """_solve_recaptcha stub returns False."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._solve_recaptcha(AsyncMock())
        assert result is False
