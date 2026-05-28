from unittest.mock import ANY, AsyncMock, MagicMock, patch

import httpx
import pytest

from web_core.search.client import _client_cache, search
from web_core.search.models import SearchError, SearchResult

SEARXNG_URL = "http://localhost:8888"


def _raw_result(url: str, title: str, content: str, engine: str = "google") -> dict:
    return {"url": url, "title": title, "content": content, "engine": engine}


def _make_searxng_response(results: list[dict], status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = {"results": results}
    resp.raise_for_status.side_effect = (
        None if status_code < 400 else httpx.HTTPStatusError("Error", request=MagicMock(), response=resp)
    )
    return resp


@pytest.fixture(autouse=True)
def clear_client_cache():
    _client_cache.clear()
    yield
    _client_cache.clear()


@pytest.fixture
def mock_httpx_client():
    client = MagicMock(spec=httpx.AsyncClient)
    client.is_closed = False
    return client


class TestSearch:
    async def test_search_success(self, mock_httpx_client):
        """Standard successful search should return formatted results."""
        raw = [
            _raw_result("https://example.com/1", "Title 1", "Snippet 1"),
            _raw_result("https://example.com/2", "Title 2", "Snippet 2"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw))

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test query")

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].url == "https://example.com/1"
        assert results[0].title == "Title 1"
        assert "google" in results[0].source

    async def test_deduplication(self, mock_httpx_client):
        """Duplicate URLs should be merged, keeping the longest snippet."""
        raw = [
            _raw_result("https://a.com", "Title A", "Short"),
            _raw_result("https://a.com", "Title A Better", "Much longer snippet"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw))

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert len(results) == 1
        assert results[0].snippet == "Much longer snippet"
        assert results[0].title == "Title A Better"

    async def test_domain_capping(self, mock_httpx_client):
        """Results should be capped at 3 per domain."""
        raw = [_raw_result(f"https://site.com/{i}", f"T{i}", "S") for i in range(10)]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw))

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test", max_results=10)

        # 3 from site.com
        assert len(results) == 3

    async def test_raises_search_error_on_4xx(self, mock_httpx_client):
        """4xx errors should raise SearchError immediately (no retry)."""
        fail_resp = _make_searxng_response([], status_code=429)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            pytest.raises(SearchError) as exc_info,
        ):
            await search(SEARXNG_URL, "test", max_retries=3)

        assert exc_info.value.query == "test"
        assert "429" in exc_info.value.reason
        # Should NOT retry on 4xx
        assert mock_httpx_client.get.call_count == 1

    async def test_raises_search_error_after_all_retries(self, mock_httpx_client):
        """After exhausting all retries, SearchError should be raised."""
        fail_resp = _make_searxng_response([], status_code=503)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(SearchError) as exc_info,
        ):
            await search(SEARXNG_URL, "test", max_retries=2)

        assert exc_info.value.query == "test"
        assert "503" in exc_info.value.reason
        assert mock_httpx_client.get.call_count == 2

    async def test_retries_on_connection_error(self, mock_httpx_client):
        """Connection errors should trigger retry."""
        request = MagicMock()
        conn_error = httpx.ConnectError("Connection refused", request=request)
        ok_resp = _make_searxng_response([_raw_result("https://example.com/1", "T", "S")])

        mock_httpx_client.get = AsyncMock(side_effect=[conn_error, ok_resp])

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            results = await search(SEARXNG_URL, "test", max_retries=3)

        assert len(results) == 1
        assert mock_httpx_client.get.call_count == 2

    async def test_raises_after_connection_errors_exhausted(self, mock_httpx_client):
        """If all retries fail with connection errors, SearchError is raised."""
        request = MagicMock()
        conn_error = httpx.ConnectError("Connection refused", request=request)
        mock_httpx_client.get = AsyncMock(side_effect=[conn_error, conn_error])

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(SearchError) as exc_info,
        ):
            await search(SEARXNG_URL, "test", max_retries=2)

        assert "ConnectError" in exc_info.value.reason

    async def test_passes_time_range_param(self, mock_httpx_client):
        """time_range should be included in the SearXNG query params."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", time_range="week")

        call_kwargs = mock_httpx_client.get.call_args
        assert call_kwargs.kwargs["params"]["time_range"] == "week"

    async def test_invalid_time_range_ignored(self, mock_httpx_client):
        """Invalid time_range values should not be passed to SearXNG."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", time_range="invalid")

        call_kwargs = mock_httpx_client.get.call_args
        assert "time_range" not in call_kwargs.kwargs["params"]

    async def test_passes_language_param(self, mock_httpx_client):
        """language should be included in the SearXNG query params."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", language="en")

        call_kwargs = mock_httpx_client.get.call_args
        assert call_kwargs.kwargs["params"]["language"] == "en"

    async def test_passes_categories_param(self, mock_httpx_client):
        """categories should be included in the SearXNG query params."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", categories="news")

        call_kwargs = mock_httpx_client.get.call_args
        assert call_kwargs.kwargs["params"]["categories"] == "news"

    async def test_include_domains_forwarded_to_query(self, mock_httpx_client):
        """include_domains should appear as site: operators in the query."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", include_domains=["docs.python.org"])

        call_kwargs = mock_httpx_client.get.call_args
        assert "site:docs.python.org" in call_kwargs.kwargs["params"]["q"]

    async def test_exclude_domains_forwarded_to_query(self, mock_httpx_client):
        """exclude_domains should appear as -site: operators in the query."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", exclude_domains=["spam.com"])

        call_kwargs = mock_httpx_client.get.call_args
        assert "-site:spam.com" in call_kwargs.kwargs["params"]["q"]

    async def test_exponential_backoff_delays(self, mock_httpx_client):
        """Retry delays should follow exponential backoff: 1s, 2s."""
        fail_resp = _make_searxng_response([], status_code=500)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            pytest.raises(SearchError),
        ):
            await search(SEARXNG_URL, "test", max_retries=3)

        # Delays: attempt 1 -> sleep(1.0), attempt 2 -> sleep(2.0), attempt 3 -> no sleep
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    async def test_sends_correct_headers(self, mock_httpx_client):
        """SearXNG requests should include X-Real-IP and X-Forwarded-For headers."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test")

        call_kwargs = mock_httpx_client.get.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["X-Real-IP"] == "127.0.0.1"
        assert headers["X-Forwarded-For"] == "127.0.0.1"

    async def test_requests_correct_url(self, mock_httpx_client):
        """The request should be sent to {searxng_url}/search."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test")

        call_args = mock_httpx_client.get.call_args
        assert call_args.args[0] == f"{SEARXNG_URL}/search"

    async def test_unexpected_exception_retries(self, mock_httpx_client):
        """Generic exceptions should also trigger retry."""
        ok_resp = _make_searxng_response([_raw_result("https://a.com/1", "T", "S")])
        mock_httpx_client.get = AsyncMock(side_effect=[ValueError("unexpected"), ok_resp])

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            results = await search(SEARXNG_URL, "test", max_retries=3)

        assert len(results) == 1

    async def test_max_retries_one_no_sleep(self, mock_httpx_client):
        """With max_retries=1, there should be no sleep (only 1 attempt)."""
        fail_resp = _make_searxng_response([], status_code=500)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            pytest.raises(SearchError),
        ):
            await search(SEARXNG_URL, "test", max_retries=1)

        mock_sleep.assert_not_called()
        assert mock_httpx_client.get.call_count == 1

    async def test_dedup_with_tracking_params(self, mock_httpx_client):
        """URLs that normalize to the same value should be deduped."""
        raw_results = [
            _raw_result("https://example.com/page?utm_source=google", "T1", "Short", "google"),
            _raw_result("https://example.com/page", "T2", "Longer content here", "bing"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert len(results) == 1

    async def test_uses_safe_httpx_client(self, mock_httpx_client):
        """Verify that safe_httpx_client is called (not raw httpx.AsyncClient)."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client) as mock_factory:
            await search(SEARXNG_URL, "test")

        # Now expects event_hooks because safe_httpx_client is used
        mock_factory.assert_called_once_with(timeout=15.0, event_hooks=ANY)

    async def test_blocks_unauthorized_private_ip(self):
        """Searching against a non-whitelisted private IP should be blocked by SSRF hook."""
        # Use an internal IP that is NOT localhost
        evil_url = "http://10.0.0.1"

        with pytest.raises(SearchError) as exc_info:
            await search(evil_url, "test")

        assert "SSRF blocked" in str(exc_info.value)
