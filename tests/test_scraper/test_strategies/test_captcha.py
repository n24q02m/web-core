from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.base import ScrapingResult
from web_core.scraper.strategies.captcha import (
    TURNSTILE_PROXYLESS,
    CaptchaStrategy,
)


class TestCaptchaStrategy:
    """Tests for CaptchaStrategy."""

    async def test_solve_captcha_success(self):
        """solve_captcha returns token from CapSolver."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"token": "solved-token"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha(
            site_key="site-key",
            page_url="https://example.com",
            captcha_type=TURNSTILE_PROXYLESS,
        )

        assert token == "solved-token"
        mock_client.post.assert_called_once()

    async def test_solve_captcha_failure(self):
        """solve_captcha returns empty string if CapSolver fails."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"errorId": 1}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        token = await strategy.solve_captcha(site_key="site-key", page_url="https://example.com")

        assert token == ""

    async def test_try_solve_turnstile_not_turnstile(self):
        """_try_solve_turnstile returns empty if not a turnstile challenge."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        with patch("web_core.scraper.strategies.captcha.detect_cloudflare_challenge", return_value="none"):
            token = await strategy._try_solve_turnstile("https://example.com", "<html></html>")
            assert token == ""

    async def test_try_solve_turnstile_no_sitekey(self):
        """_try_solve_turnstile returns empty if sitekey not found."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        with (
            patch("web_core.scraper.strategies.captcha.detect_cloudflare_challenge", return_value="turnstile"),
            patch("web_core.scraper.strategies.captcha.extract_turnstile_sitekey", return_value=None),
        ):
            token = await strategy._try_solve_turnstile("https://example.com", "<html></html>")
            assert token == ""

    async def test_try_solve_turnstile_success(self):
        """_try_solve_turnstile calls solve_captcha and returns token."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        with (
            patch("web_core.scraper.strategies.captcha.detect_cloudflare_challenge", return_value="turnstile"),
            patch("web_core.scraper.strategies.captcha.extract_turnstile_sitekey", return_value="0x4AAAA_key"),
            patch.object(strategy, "solve_captcha", return_value="solved-token") as mock_solve,
        ):
            token = await strategy._try_solve_turnstile("https://example.com", "<html></html>")
            assert token == "solved-token"
            mock_solve.assert_called_once_with(
                site_key="0x4AAAA_key",
                page_url="https://example.com",
                captcha_type=TURNSTILE_PROXYLESS,
            )

    async def test_extract_from_data_sitekey(self):
        """Extract sitekey from data-sitekey attribute."""
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
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)  # no data-sitekey element

        mock_page.evaluate = AsyncMock(
            side_effect=[
                [
                    "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/0x4AAAAAAADnPIDROrmt1Wwj/light/normal"
                ],
                [],
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

        mock_page.evaluate = AsyncMock(
            side_effect=[
                ["https://example.com/no-sitekey"],  # iframes
                ["turnstile.render({sitekey: '0x4AAAA_script_key'})"],  # scripts
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

        mock_page.evaluate = AsyncMock(
            side_effect=[
                ["https://challenges.cloudflare.com/LongAlphanumericString12/light/normal"],
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
        mock_cls, _, _mock_page = _make_mock_patchright(
            page_content="<html>real content after solve</html>",
            page_url="https://example.com/real",
        )

        with (
            patch("web_core.browsers.patchright.PatchrightProvider", mock_cls),
            patch.object(strategy, "_extract_turnstile_sitekey", return_value="0x4AAAA_key"),
            patch.object(strategy, "_inject_turnstile_token", return_value=True) as mock_inject,
        ):
            result = await strategy._solve_cf_turnstile_via_patchright("https://example.com")

        assert result.metadata["captcha_solved"] is True
        assert result.content == "<html>real content after solve</html>"
        mock_inject.assert_called_once()

    async def test_token_injection_failure_returns_fallback(self):
        """When token injection fails, returns fallback result."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "solution": {"token": "solved-turnstile-token"},
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        strategy = CaptchaStrategy(capsolver_api_key="key", http_client=mock_client)
        mock_cls, _, _mock_page = _make_mock_patchright(
            page_content="<html>challenge content</html>",
            page_url="https://example.com/challenge",
        )

        with (
            patch("web_core.browsers.patchright.PatchrightProvider", mock_cls),
            patch.object(strategy, "_extract_turnstile_sitekey", return_value="0x4AAAA_key"),
            patch.object(strategy, "_inject_turnstile_token", return_value=False),
        ):
            result = await strategy._solve_cf_turnstile_via_patchright("https://example.com")

        assert result.metadata["captcha_solved"] is False
        assert result.metadata["error"] == "token_injection_failed"
        assert result.content == "<html>challenge content</html>"


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

        # Strategy 2: /0x is present but it's not followed by hex chars as expected by _RE_CF_IFRAME_0X
        mock_page.evaluate = AsyncMock(
            side_effect=[
                ["https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/0x/invalid"],  # iframes
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

        mock_page.evaluate = AsyncMock(
            side_effect=[
                [],  # iframes
                ["console.log('hello');", "var x = 1;"],  # scripts
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

        # "sitekey" is present (triggers the continue check) but doesn't match _RE_SCRIPT_SITEKEY
        mock_page.evaluate = AsyncMock(
            side_effect=[
                [],  # iframes
                ["var sitekey = 'too-short';"],  # scripts
            ]
        )

        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._extract_turnstile_sitekey(mock_page)
        assert result is None

    async def test_inject_turnstile_token_failure(self):
        """_inject_turnstile_token returns False if page.evaluate raises."""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=Exception("eval failed"))
        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._inject_turnstile_token(mock_page, "token")
        assert result is False

    async def test_solve_cf_turnstile_ssrf_blocked(self):
        """_solve_cf_turnstile_via_patchright raises ValueError if SSRF blocked."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        with (
            patch("web_core.scraper.strategies.captcha.is_safe_url", return_value=False),
            pytest.raises(ValueError, match="SSRF blocked"),
        ):
            await strategy._solve_cf_turnstile_via_patchright("http://unsafe.com")

    async def test_fetch_ssrf_blocked(self):
        """fetch raises ValueError if SSRF blocked."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        with (
            patch("web_core.scraper.strategies.captcha.is_safe_url", return_value=False),
            pytest.raises(ValueError, match="SSRF blocked"),
        ):
            await strategy.fetch("http://unsafe.com")

    async def test_fetch_explicit_captcha(self):
        """fetch solves captcha via fallback strategy if explicit site_key provided."""
        mock_fallback = AsyncMock()
        mock_fallback.fetch = AsyncMock(
            return_value=ScrapingResult(
                content="fallback content",
                url="https://example.com",
                strategy="fallback",
                status_code=200,
                metadata={},
            )
        )

        strategy = CaptchaStrategy(capsolver_api_key="key", fallback_strategy=mock_fallback)
        with patch.object(strategy, "solve_captcha", return_value="token") as mock_solve:
            result = await strategy.fetch("https://example.com", {"site_key": "explicit-key", "captcha_type": "type"})
            assert result.metadata["captcha_solved"] is True
            assert result.content == "fallback content"
            mock_solve.assert_called_once()
            mock_fallback.fetch.assert_called_once()

    async def test_fetch_capsolver_key_only(self):
        """fetch calls _solve_cf_turnstile_via_patchright if capsolver_api_key set."""
        strategy = CaptchaStrategy(capsolver_api_key="key")
        with patch.object(
            strategy,
            "_solve_cf_turnstile_via_patchright",
            return_value=ScrapingResult(
                content="solved", url="https://example.com", strategy="captcha", status_code=200
            ),
        ) as mock_solve:
            result = await strategy.fetch("https://example.com")
            assert result.content == "solved"
            mock_solve.assert_called_once()

    async def test_fetch_fallback_only(self):
        """fetch delegates to fallback strategy if no captcha solving configured."""
        mock_fallback = AsyncMock()
        mock_fallback.fetch = AsyncMock(
            return_value=ScrapingResult(
                content="fallback only",
                url="https://example.com",
                strategy="fallback",
                status_code=200,
                metadata={},
            )
        )

        strategy = CaptchaStrategy(fallback_strategy=mock_fallback)
        result = await strategy.fetch("https://example.com")
        assert result.content == "fallback only"
        assert result.metadata["captcha_solved"] is False
        mock_fallback.fetch.assert_called_once()

    async def test_fetch_no_config(self):
        """fetch returns error if no captcha or fallback configured."""
        strategy = CaptchaStrategy()
        result = await strategy.fetch("https://example.com")
        assert result.metadata["error"] == "no_fallback_strategy"

    async def test_inject_turnstile_token_success(self):
        """_inject_turnstile_token returns True if page.evaluate succeeds."""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock()
        strategy = CaptchaStrategy(capsolver_api_key="key")
        result = await strategy._inject_turnstile_token(mock_page, "token")
        assert result is True
