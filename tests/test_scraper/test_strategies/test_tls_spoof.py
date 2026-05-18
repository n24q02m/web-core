"""Tests for TLSSpoofStrategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.strategies.tls_spoof import TLSSpoofStrategy

# ---------------------------------------------------------------------------
# TLSSpoofStrategy
# ---------------------------------------------------------------------------


class TestTLSSpoofStrategy:
    """Test TLS fingerprint spoofing strategy."""

    def test_name(self):
        strategy = TLSSpoofStrategy()
        assert strategy.name == "tls_spoof"

    def test_default_impersonate(self):
        strategy = TLSSpoofStrategy()
        assert strategy.impersonate == "chrome131"

    def test_custom_impersonate(self):
        strategy = TLSSpoofStrategy(impersonate="firefox120")
        assert strategy.impersonate == "firefox120"

    def test_default_timeout(self):
        strategy = TLSSpoofStrategy()
        assert strategy.timeout == 30.0

    def test_custom_timeout(self):
        strategy = TLSSpoofStrategy(timeout=60.0)
        assert strategy.timeout == 60.0

    async def test_fetch_success_with_session_factory(self):
        """fetch with injected session_factory should use it and return correct result."""
        mock_response = MagicMock()
        mock_response.text = "<html>spoofed</html>"
        mock_response.url = "https://example.com"
        mock_response.status_code = 200

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        strategy = TLSSpoofStrategy(session_factory=lambda: mock_session)
        result = await strategy.fetch("https://example.com")

        assert result.content == "<html>spoofed</html>"
        assert result.url == "https://example.com"
        assert result.strategy == "tls_spoof"
        assert result.status_code == 200

    async def test_fetch_metadata(self):
        """Result metadata should include impersonate and content_length."""
        mock_response = MagicMock()
        mock_response.text = "hello"
        mock_response.url = "https://example.com"
        mock_response.status_code = 200

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        strategy = TLSSpoofStrategy(impersonate="chrome131", session_factory=lambda: mock_session)
        result = await strategy.fetch("https://example.com")

        assert result.metadata["impersonate"] == "chrome131"
        assert result.metadata["content_length"] == 5

    async def test_fetch_passes_impersonate_and_timeout(self):
        """fetch should pass impersonate and timeout to session.get."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_response.url = "https://example.com"
        mock_response.status_code = 200

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        strategy = TLSSpoofStrategy(impersonate="firefox120", timeout=15.0, session_factory=lambda: mock_session)
        await strategy.fetch("https://example.com")

        mock_session.get.assert_called_once_with(
            "https://example.com",
            impersonate="firefox120",
            timeout=15.0,
            cookies=None,
            allow_redirects=False,
        )

    async def test_fetch_failure_propagates(self):
        """Errors from the session should propagate to the caller."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=ConnectionError("TLS handshake failed"))

        strategy = TLSSpoofStrategy(session_factory=lambda: mock_session)
        with pytest.raises(ConnectionError, match="TLS handshake failed"):
            await strategy.fetch("https://example.com")

    async def test_fetch_blocks_ssrf(self):
        """fetch should block SSRF attempts by raising ValueError for unsafe URLs."""
        strategy = TLSSpoofStrategy()

        with (
            patch("web_core.scraper.strategies.tls_spoof.is_safe_url", return_value=False),
            pytest.raises(ValueError, match=r"SSRF blocked: http://169\.254\.169\.254/latest/meta-data/"),
        ):
            await strategy.fetch("http://169.254.169.254/latest/meta-data/")

    async def test_fetch_uses_curl_cffi_when_no_factory(self):
        """When no session_factory is provided, fetch should import and use curl-cffi."""
        mock_response = MagicMock()
        mock_response.text = "<html>cffi</html>"
        mock_response.url = "https://example.com"
        mock_response.status_code = 200

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Patch at the source module so the lazy `from curl_cffi.requests import AsyncSession`
        # picks up our mock.
        with patch("curl_cffi.requests.AsyncSession", return_value=mock_session) as mock_cls:
            strategy = TLSSpoofStrategy()
            result = await strategy.fetch("https://example.com")

            mock_cls.assert_called_once()
            assert result.content == "<html>cffi</html>"

    async def test_fetch_follows_redirects_and_retains_cookies(self):
        """Test that redirects are followed up to 10 times and initial cookies are sent only on the first request."""
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 302
        mock_resp1.headers = {"Location": "/path2"}
        mock_resp1.url = "https://example.com/path1"

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 301
        mock_resp2.headers = {"Location": "https://other.com/final"}
        mock_resp2.url = "https://example.com/path2"

        mock_resp3 = MagicMock()
        mock_resp3.status_code = 200
        mock_resp3.text = "final content"
        mock_resp3.url = "https://other.com/final"
        mock_resp3.headers = {}

        mock_session = AsyncMock()
        mock_session.get.side_effect = [mock_resp1, mock_resp2, mock_resp3]

        strategy = TLSSpoofStrategy(session_factory=lambda: mock_session)
        result = await strategy.fetch("https://example.com/path1", selectors={"cookies": {"auth": "123"}})

        assert result.content == "final content"
        assert result.url == "https://other.com/final"

        # Check call arguments for cookie retention
        calls = mock_session.get.call_args_list
        assert len(calls) == 3
        # First call has initial cookies
        assert calls[0].args[0] == "https://example.com/path1"
        assert calls[0].kwargs["cookies"] == {"auth": "123"}
        assert calls[0].kwargs["allow_redirects"] is False

        # Second call does not have manual cookies
        assert calls[1].args[0] == "https://example.com/path2"
        assert calls[1].kwargs["cookies"] is None
        assert calls[1].kwargs["allow_redirects"] is False

        # Third call
        assert calls[2].args[0] == "https://other.com/final"
        assert calls[2].kwargs["cookies"] is None
        assert calls[2].kwargs["allow_redirects"] is False

    async def test_fetch_blocks_ssrf_on_redirect(self):
        """Test that SSRF protection applies to redirect URLs as well."""
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 302
        mock_resp1.headers = {"Location": "http://127.0.0.1/admin"}
        mock_resp1.url = "https://example.com/path1"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_resp1

        strategy = TLSSpoofStrategy(session_factory=lambda: mock_session)

        # Patch is_safe_url to simulate SSRF block on redirect target
        with (
            patch(
                "web_core.scraper.strategies.tls_spoof.is_safe_url",
                side_effect=lambda url: url == "https://example.com/path1",
            ),
            pytest.raises(ValueError, match=r"SSRF blocked: http://127\.0\.0\.1/admin"),
        ):
            await strategy.fetch("https://example.com/path1")

    async def test_fetch_too_many_redirects(self):
        """Test that a RuntimeError is raised after 10 redirects."""
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.headers = {"Location": "/loop"}
        mock_resp.url = "https://example.com/loop"

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_resp

        strategy = TLSSpoofStrategy(session_factory=lambda: mock_session)

        with pytest.raises(RuntimeError, match="Too many redirects"):
            await strategy.fetch("https://example.com/loop")
