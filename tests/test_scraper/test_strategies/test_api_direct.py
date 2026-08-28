"""Tests for APIDirectStrategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.strategies.api_direct import APIDirectStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status_code: int = 200, text: str = "", headers: dict | None = None, url: str = ""):
    """Create a mock HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {"content-type": "text/html"}
    resp.url = url
    return resp


def _make_client(*responses):
    """Create a mock async client that returns responses in order."""
    client = AsyncMock()
    client.get = AsyncMock(side_effect=list(responses))
    client.aclose = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# APIDirectStrategy
# ---------------------------------------------------------------------------


class TestAPIDirectStrategy:
    """Test API endpoint discovery and direct fetching strategy."""

    def test_name(self):
        strategy = APIDirectStrategy()
        assert strategy.name == "api_direct"

    def test_default_timeout(self):
        strategy = APIDirectStrategy()
        assert strategy.timeout == 30.0

    # -- discover_apis -------------------------------------------------------

    def test_discover_apis_fetch_pattern(self):
        html = """<script>fetch("/api/data")</script>"""
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert "/api/data" in apis

    def test_discover_apis_axios_pattern(self):
        html = """<script>axios.get("/api/users")</script>"""
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert "/api/users" in apis

    def test_discover_apis_absolute_url(self):
        html = """<script>var url = "https://api.example.com/v1/data";</script>"""
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert "https://api.example.com/v1/data" in apis

    def test_discover_apis_single_quoted_url(self):
        html = """<script>var url = 'https://api.example.com/v2/items';</script>"""
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert "https://api.example.com/v2/items" in apis

    def test_discover_apis_relative_api_path(self):
        html = """<script>var endpoint = "/api/v1/products";</script>"""
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert "/api/v1/products" in apis

    def test_discover_apis_deduplicates(self):
        html = """
        <script>
            fetch("/api/data");
            fetch("/api/data");
        </script>
        """
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert apis.count("/api/data") == 1

    def test_discover_apis_preserves_order(self):
        html = """
        <script>
            fetch("/api/first");
            fetch("/api/second");
        </script>
        """
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert apis.index("/api/first") < apis.index("/api/second")

    def test_discover_apis_preserves_pattern_priority(self):
        html = 'var absolute = "https://api.example.com/first"; fetch("/api/second")'
        strategy = APIDirectStrategy()
        assert strategy.discover_apis(html)[:2] == [
            "https://api.example.com/first",
            "/api/second",
        ]

    def test_discover_apis_empty_html(self):
        strategy = APIDirectStrategy()
        assert strategy.discover_apis("") == []

    def test_discover_apis_no_patterns(self):
        strategy = APIDirectStrategy()
        assert strategy.discover_apis("<html><body>Hello</body></html>") == []

    def test_discover_apis_multiple_pattern_types(self):
        html = """
        <script>
            fetch("/api/items");
            axios.post("/api/orders");
            var url = "https://api.example.com/data";
        </script>
        """
        strategy = APIDirectStrategy()
        apis = strategy.discover_apis(html)
        assert len(apis) >= 3

    # -- fetch ---------------------------------------------------------------

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_blocks_unsafe_url(self, mock_is_safe_url):
        """fetch should raise ValueError when URL is unsafe."""
        mock_is_safe_url.return_value = False
        client = AsyncMock()
        strategy = APIDirectStrategy(http_client=client)
        with pytest.raises(ValueError, match="SSRF blocked: http://localhost"):
            await strategy.fetch("http://localhost")

        client.get.assert_not_called()

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_blocks_unsafe_api_url(self, mock_is_safe_url):
        """fetch should raise ValueError when discovered API URL is unsafe."""
        # Allow the page URL but block the API URL
        mock_is_safe_url.side_effect = [True, False]
        page_html = '<script>fetch("http://localhost/admin")</script>'
        page_resp = _make_response(200, page_html, url="https://example.com")
        client = _make_client(page_resp)

        strategy = APIDirectStrategy(http_client=client)
        with pytest.raises(ValueError, match="SSRF blocked: http://localhost/admin"):
            await strategy.fetch("https://example.com")

        assert client.get.call_count == 1  # Only page was fetched

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_with_api_discovery(self, mock_is_safe_url):
        """When page source contains API URLs, fetch the first discovered API."""
        mock_is_safe_url.return_value = True
        page_html = '<script>fetch("https://api.example.com/data")</script>'
        page_resp = _make_response(200, page_html, url="https://example.com")
        api_resp = _make_response(
            200,
            '{"items": []}',
            headers={"content-type": "application/json"},
            url="https://api.example.com/data",
        )
        client = _make_client(page_resp, api_resp)

        strategy = APIDirectStrategy(http_client=client)
        result = await strategy.fetch("https://example.com")

        assert result.content == '{"items": []}'
        assert result.strategy == "api_direct"
        assert result.status_code == 200
        assert result.metadata["api_url"] == "https://api.example.com/data"

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_no_apis_found_falls_back(self, mock_is_safe_url):
        """When no API endpoints are discovered, return the page source as fallback."""
        mock_is_safe_url.return_value = True
        page_html = "<html><body>No APIs here</body></html>"
        page_resp = _make_response(200, page_html, url="https://example.com")
        client = _make_client(page_resp)

        strategy = APIDirectStrategy(http_client=client)
        result = await strategy.fetch("https://example.com")

        assert result.content == page_html
        assert result.metadata["apis_found"] == 0
        assert result.metadata["fallback"] == "page_source"

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_with_explicit_api_url(self, mock_is_safe_url):
        """When selectors include api_url, skip discovery and fetch directly."""
        mock_is_safe_url.return_value = True
        api_resp = _make_response(
            200,
            '{"result": true}',
            headers={"content-type": "application/json"},
            url="https://api.example.com/direct",
        )
        client = _make_client(api_resp)

        strategy = APIDirectStrategy(http_client=client)
        result = await strategy.fetch(
            "https://example.com",
            selectors={"api_url": "https://api.example.com/direct"},
        )

        assert result.content == '{"result": true}'
        assert result.url == "https://api.example.com/direct"
        # Only one call — no page fetch
        assert client.get.call_count == 1

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_relative_api_url_resolved(self, mock_is_safe_url):
        """Relative API paths should be resolved against the page URL."""
        mock_is_safe_url.return_value = True
        page_html = '<script>fetch("/api/v1/data")</script>'
        page_resp = _make_response(200, page_html, url="https://example.com/page")
        api_resp = _make_response(
            200,
            '{"data": []}',
            headers={"content-type": "application/json"},
            url="https://example.com/api/v1/data",
        )
        client = _make_client(page_resp, api_resp)

        strategy = APIDirectStrategy(http_client=client)
        await strategy.fetch("https://example.com/page")

        # The second call should be to the resolved absolute URL
        second_call = client.get.call_args_list[1]
        assert second_call.args[0] == "https://example.com/api/v1/data"

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_failure_propagates(self, mock_is_safe_url):
        """HTTP errors should propagate."""
        mock_is_safe_url.return_value = True
        client = AsyncMock()
        client.get = AsyncMock(side_effect=ConnectionError("connection refused"))
        client.aclose = AsyncMock()

        strategy = APIDirectStrategy(http_client=client)
        with pytest.raises(ConnectionError, match="connection refused"):
            await strategy.fetch("https://example.com")

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_closes_client_when_no_injected_client(self, mock_is_safe_url, mock_httpx_response):
        """When using safe_httpx_client (no injected client), aclose should be called."""
        mock_is_safe_url.return_value = True
        from unittest.mock import patch

        page_resp = mock_httpx_response(200, "<html>no api</html>")
        page_resp.url = "https://example.com"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=page_resp)
        mock_client.aclose = AsyncMock()

        with patch("web_core.scraper.strategies.api_direct.safe_httpx_client", return_value=mock_client):
            strategy = APIDirectStrategy()
            await strategy.fetch("https://example.com")

            mock_client.aclose.assert_called_once()

    @patch("web_core.scraper.strategies.api_direct.is_safe_url")
    async def test_fetch_does_not_close_injected_client(self, mock_is_safe_url):
        """An injected http_client should NOT be closed by fetch."""
        mock_is_safe_url.return_value = True
        page_resp = _make_response(200, "<html>no api</html>", url="https://example.com")
        client = _make_client(page_resp)

        strategy = APIDirectStrategy(http_client=client)
        await strategy.fetch("https://example.com")

        client.aclose.assert_not_called()
