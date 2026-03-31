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
        )

    async def test_fetch_failure_propagates(self):
        """Errors from the session should propagate to the caller."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=ConnectionError("TLS handshake failed"))

        strategy = TLSSpoofStrategy(session_factory=lambda: mock_session)
        with pytest.raises(ConnectionError, match="TLS handshake failed"):
            await strategy.fetch("https://example.com")

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
