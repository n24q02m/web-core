"""Tests for BasicHTTPStrategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from web_core.scraper.strategies.basic_http import BasicHTTPStrategy

# ---------------------------------------------------------------------------
# BasicHTTPStrategy
# ---------------------------------------------------------------------------


class TestBasicHTTPStrategy:
    """Test basic HTTP scraping strategy."""

    def test_name(self):
        strategy = BasicHTTPStrategy()
        assert strategy.name == "basic_http"

    def test_default_timeout(self):
        strategy = BasicHTTPStrategy()
        assert strategy.timeout == 30.0

    def test_custom_timeout(self):
        strategy = BasicHTTPStrategy(timeout=10.0)
        assert strategy.timeout == 10.0

    def test_default_headers(self):
        strategy = BasicHTTPStrategy()
        assert "User-Agent" in strategy.headers
        assert "Chrome" in strategy.headers["User-Agent"]

    def test_custom_headers(self):
        custom = {"User-Agent": "CustomBot/1.0"}
        strategy = BasicHTTPStrategy(headers=custom)
        assert strategy.headers == custom

    async def test_fetch_success_with_injected_client(self, mock_httpx_client, mock_httpx_response):
        """fetch should return ScrapingResult with correct fields."""
        resp = mock_httpx_response(200, "<html>test content</html>", {"content-type": "text/html; charset=utf-8"})
        resp.url = "https://example.com"
        mock_httpx_client.get = AsyncMock(return_value=resp)

        strategy = BasicHTTPStrategy(http_client=mock_httpx_client)
        result = await strategy.fetch("https://example.com")

        assert result.content == "<html>test content</html>"
        assert result.url == "https://example.com"
        assert result.strategy == "basic_http"
        assert result.status_code == 200

    async def test_fetch_metadata(self, mock_httpx_client, mock_httpx_response):
        """Result metadata should include content_type and content_length."""
        resp = mock_httpx_response(200, "hello world", {"content-type": "text/plain"})
        resp.url = "https://example.com"
        mock_httpx_client.get = AsyncMock(return_value=resp)

        strategy = BasicHTTPStrategy(http_client=mock_httpx_client)
        result = await strategy.fetch("https://example.com")

        assert result.metadata["content_type"] == "text/plain"
        assert result.metadata["content_length"] == len("hello world")

    async def test_fetch_uses_safe_httpx_client_when_no_client(self, mock_httpx_response):
        """When no http_client is injected, fetch should use safe_httpx_client."""
        resp = mock_httpx_response(200, "<html>safe</html>")
        resp.url = "https://example.com"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        target = "web_core.scraper.strategies.basic_http.safe_httpx_client"
        with patch(target, return_value=mock_client) as mock_factory:
            strategy = BasicHTTPStrategy()
            result = await strategy.fetch("https://example.com")

            mock_factory.assert_called_once_with(timeout=30.0)
            assert result.content == "<html>safe</html>"

    async def test_fetch_passes_headers_and_timeout(self, mock_httpx_client, mock_httpx_response):
        """fetch should pass configured headers and timeout to the HTTP client."""
        resp = mock_httpx_response(200, "ok")
        resp.url = "https://example.com"
        mock_httpx_client.get = AsyncMock(return_value=resp)

        custom_headers = {"User-Agent": "TestBot"}
        strategy = BasicHTTPStrategy(timeout=15.0, headers=custom_headers, http_client=mock_httpx_client)
        await strategy.fetch("https://example.com")

        mock_httpx_client.get.assert_called_once_with(
            "https://example.com",
            headers=custom_headers,
            timeout=15.0,
            follow_redirects=True,
        )

    async def test_fetch_failure_propagates(self, mock_httpx_client):
        """HTTP errors should propagate to the caller."""
        mock_httpx_client.get = AsyncMock(side_effect=ConnectionError("refused"))

        strategy = BasicHTTPStrategy(http_client=mock_httpx_client)
        with pytest.raises(ConnectionError, match="refused"):
            await strategy.fetch("https://example.com")

    async def test_fetch_non_200_status(self, mock_httpx_client, mock_httpx_response):
        """Non-200 responses should still return a ScrapingResult."""
        resp = mock_httpx_response(403, "Forbidden")
        resp.url = "https://example.com"
        mock_httpx_client.get = AsyncMock(return_value=resp)

        strategy = BasicHTTPStrategy(http_client=mock_httpx_client)
        result = await strategy.fetch("https://example.com")

        assert result.status_code == 403
        assert result.content == "Forbidden"
