"""Tests for SearXNG search client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from web_core.search.client import (
    _MAX_PER_DOMAIN,
    _apply_domain_cap,
    _build_filtered_query,
    search,
)
from web_core.search.models import SearchError, SearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEARXNG_URL = "https://search.example.com"


def _make_searxng_response(results: list[dict], status_code: int = 200) -> MagicMock:
    """Build a mock httpx response mimicking SearXNG JSON output."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"results": results}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        http_error = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
        resp.raise_for_status.side_effect = http_error
    return resp


def _raw_result(url: str, title: str = "Title", content: str = "Snippet", engine: str = "google") -> dict:
    """Build a single raw SearXNG result dict."""
    return {"url": url, "title": title, "content": content, "engine": engine}


# ---------------------------------------------------------------------------
# _build_filtered_query
# ---------------------------------------------------------------------------


class TestBuildFilteredQuery:
    """Test query building with domain filters."""

    def test_no_filters_returns_original(self):
        assert _build_filtered_query("python tutorial") == "python tutorial"

    def test_include_domains_adds_site_operator(self):
        result = _build_filtered_query("test", include_domains=["example.com"])
        assert "site:example.com" in result
        assert "test" in result

    def test_include_multiple_domains_joined_with_or(self):
        result = _build_filtered_query("q", include_domains=["a.com", "b.org"])
        assert "site:a.com" in result
        assert "site:b.org" in result
        assert "OR" in result

    def test_include_domains_max_five(self):
        domains = [f"d{i}.com" for i in range(10)]
        result = _build_filtered_query("q", include_domains=domains)
        # Only the first 5 should appear
        for i in range(5):
            assert f"site:d{i}.com" in result
        for i in range(5, 10):
            assert f"site:d{i}.com" not in result

    def test_exclude_domains_adds_negative_site(self):
        result = _build_filtered_query("test", exclude_domains=["spam.com"])
        assert "-site:spam.com" in result

    def test_exclude_multiple_domains(self):
        result = _build_filtered_query("q", exclude_domains=["a.com", "b.com"])
        assert "-site:a.com" in result
        assert "-site:b.com" in result

    def test_exclude_domains_max_ten(self):
        domains = [f"d{i}.com" for i in range(15)]
        result = _build_filtered_query("q", exclude_domains=domains)
        for i in range(10):
            assert f"-site:d{i}.com" in result
        for i in range(10, 15):
            assert f"-site:d{i}.com" not in result

    def test_include_and_exclude_combined(self):
        result = _build_filtered_query("q", include_domains=["good.com"], exclude_domains=["bad.com"])
        assert "site:good.com" in result
        assert "-site:bad.com" in result

    def test_invalid_include_domain_rejected(self):
        result = _build_filtered_query("q", include_domains=["not valid!", "good.com"])
        assert "site:good.com" in result
        assert "not valid!" not in result

    def test_invalid_exclude_domain_rejected(self):
        result = _build_filtered_query("q", exclude_domains=["bad..domain", "spam.com"])
        assert "-site:spam.com" in result
        assert "bad..domain" not in result

    def test_all_include_domains_invalid_returns_plain_query(self):
        result = _build_filtered_query("test", include_domains=["!!!"])
        assert result == "test"


# ---------------------------------------------------------------------------
# _apply_domain_cap
# ---------------------------------------------------------------------------


class TestApplyDomainCap:
    """Test per-domain result limiting."""

    def test_caps_at_max_per_domain(self):
        items = [{"url": f"https://example.com/page{i}"} for i in range(10)]
        result = _apply_domain_cap(items)
        assert len(result) == _MAX_PER_DOMAIN

    def test_different_domains_unaffected(self):
        items = [
            {"url": "https://a.com/1"},
            {"url": "https://b.com/1"},
            {"url": "https://c.com/1"},
            {"url": "https://d.com/1"},
        ]
        result = _apply_domain_cap(items)
        assert len(result) == 4

    def test_www_prefix_stripped_for_counting(self):
        """www.example.com and example.com count as the same domain."""
        items = [
            {"url": "https://www.example.com/1"},
            {"url": "https://example.com/2"},
            {"url": "https://www.example.com/3"},
            {"url": "https://example.com/4"},
        ]
        result = _apply_domain_cap(items)
        assert len(result) == _MAX_PER_DOMAIN

    def test_empty_list(self):
        assert _apply_domain_cap([]) == []

    def test_preserves_order(self):
        items = [
            {"url": "https://a.com/1"},
            {"url": "https://b.com/1"},
            {"url": "https://a.com/2"},
        ]
        result = _apply_domain_cap(items)
        assert [r["url"] for r in result] == [
            "https://a.com/1",
            "https://b.com/1",
            "https://a.com/2",
        ]

    def test_mixed_domains_with_cap(self):
        items = [
            {"url": "https://a.com/1"},
            {"url": "https://a.com/2"},
            {"url": "https://a.com/3"},
            {"url": "https://a.com/4"},  # capped
            {"url": "https://b.com/1"},
        ]
        result = _apply_domain_cap(items)
        assert len(result) == 4
        urls = [r["url"] for r in result]
        assert "https://a.com/4" not in urls
        assert "https://b.com/1" in urls

    def test_missing_url_key_treated_as_empty(self):
        """Items without a url key should not crash."""
        items = [{"title": "no url"}, {"url": "https://a.com/1"}]
        result = _apply_domain_cap(items)
        # Empty netloc is still a "domain" — should not crash
        assert len(result) == 2


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestSearch:
    """Test the main search function."""

    async def test_returns_search_results(self, mock_httpx_client):
        """Basic success case: SearXNG returns results, we get SearchResult objects."""
        raw_results = [
            _raw_result("https://example.com/1", "Title 1", "Snippet 1", "google"),
            _raw_result("https://example.com/2", "Title 2", "Snippet 2", "bing"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test query")

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].url == "https://example.com/1"
        assert results[0].title == "Title 1"
        assert results[0].snippet == "Snippet 1"
        assert results[0].source == "google"

    async def test_deduplicates_urls(self, mock_httpx_client):
        """Same URL from different engines should be merged into one result."""
        raw_results = [
            _raw_result("https://example.com/page", "Title", "Short", "google"),
            _raw_result("https://example.com/page", "Title", "Longer snippet here", "bing"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert len(results) == 1
        # Sources should be merged
        assert "google" in results[0].source
        assert "bing" in results[0].source
        # Longest snippet should be kept
        assert results[0].snippet == "Longer snippet here"

    async def test_dedup_keeps_longest_snippet(self, mock_httpx_client):
        """When deduplicating, the longest snippet wins."""
        raw_results = [
            _raw_result("https://example.com/p", "T1", "A very long snippet with details", "google"),
            _raw_result("https://example.com/p", "T2", "Short", "bing"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert results[0].snippet == "A very long snippet with details"

    async def test_dedup_does_not_duplicate_source(self, mock_httpx_client):
        """Duplicate source names should not be appended again."""
        raw_results = [
            _raw_result("https://example.com/p", "T", "S", "google"),
            _raw_result("https://example.com/p", "T", "S", "google"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert results[0].source == "google"
        assert results[0].source.count("google") == 1

    async def test_domain_cap_applied(self, mock_httpx_client):
        """No more than MAX_PER_DOMAIN results from a single domain."""
        raw_results = [_raw_result(f"https://example.com/page{i}", f"Title {i}", f"Snippet {i}") for i in range(10)]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert len(results) == _MAX_PER_DOMAIN

    async def test_respects_max_results(self, mock_httpx_client):
        """Results should be limited to max_results."""
        raw_results = [_raw_result(f"https://d{i}.com/page", f"Title {i}", f"Snippet {i}") for i in range(20)]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test", max_results=5)

        assert len(results) == 5

    async def test_empty_results_returns_empty_list(self, mock_httpx_client):
        """Empty SearXNG response should return empty list."""
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response([]))

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "obscure query")

        assert results == []

    async def test_retries_on_5xx(self, mock_httpx_client):
        """5xx errors should trigger retry, and succeed on subsequent attempt."""
        fail_resp = _make_searxng_response([], status_code=500)
        ok_resp = _make_searxng_response([_raw_result("https://example.com/1", "T", "S")])

        mock_httpx_client.get = AsyncMock(side_effect=[fail_resp, ok_resp])

        with (
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            results = await search(SEARXNG_URL, "test", max_retries=3)

        assert len(results) == 1
        assert mock_httpx_client.get.call_count == 2
        mock_sleep.assert_called_once()

    async def test_raises_search_error_on_4xx(self, mock_httpx_client):
        """4xx errors should raise SearchError immediately without retry."""
        fail_resp = _make_searxng_response([], status_code=429)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
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
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
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
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
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
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(SearchError) as exc_info,
        ):
            await search(SEARXNG_URL, "test", max_retries=2)

        assert "Connection refused" in exc_info.value.reason

    async def test_passes_time_range_param(self, mock_httpx_client):
        """time_range should be included in the SearXNG query params."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", time_range="week")

        call_kwargs = mock_httpx_client.get.call_args
        assert call_kwargs.kwargs["params"]["time_range"] == "week"

    async def test_invalid_time_range_ignored(self, mock_httpx_client):
        """Invalid time_range values should not be passed to SearXNG."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", time_range="invalid")

        call_kwargs = mock_httpx_client.get.call_args
        assert "time_range" not in call_kwargs.kwargs["params"]

    async def test_passes_language_param(self, mock_httpx_client):
        """language should be included in the SearXNG query params."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", language="en")

        call_kwargs = mock_httpx_client.get.call_args
        assert call_kwargs.kwargs["params"]["language"] == "en"

    async def test_passes_categories_param(self, mock_httpx_client):
        """categories should be included in the SearXNG query params."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", categories="news")

        call_kwargs = mock_httpx_client.get.call_args
        assert call_kwargs.kwargs["params"]["categories"] == "news"

    async def test_include_domains_forwarded_to_query(self, mock_httpx_client):
        """include_domains should appear as site: operators in the query."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", include_domains=["docs.python.org"])

        call_kwargs = mock_httpx_client.get.call_args
        assert "site:docs.python.org" in call_kwargs.kwargs["params"]["q"]

    async def test_exclude_domains_forwarded_to_query(self, mock_httpx_client):
        """exclude_domains should appear as -site: operators in the query."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", exclude_domains=["spam.com"])

        call_kwargs = mock_httpx_client.get.call_args
        assert "-site:spam.com" in call_kwargs.kwargs["params"]["q"]

    async def test_exponential_backoff_delays(self, mock_httpx_client):
        """Retry delays should follow exponential backoff: 1s, 2s."""
        fail_resp = _make_searxng_response([], status_code=500)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
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

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test")

        call_kwargs = mock_httpx_client.get.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["X-Real-IP"] == "127.0.0.1"
        assert headers["X-Forwarded-For"] == "127.0.0.1"

    async def test_requests_correct_url(self, mock_httpx_client):
        """The request should be sent to {searxng_url}/search."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test")

        call_args = mock_httpx_client.get.call_args
        assert call_args.args[0] == f"{SEARXNG_URL}/search"

    async def test_unexpected_exception_retries(self, mock_httpx_client):
        """Generic exceptions should also trigger retry."""
        ok_resp = _make_searxng_response([_raw_result("https://a.com/1", "T", "S")])
        mock_httpx_client.get = AsyncMock(side_effect=[ValueError("unexpected"), ok_resp])

        with (
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            results = await search(SEARXNG_URL, "test", max_retries=3)

        assert len(results) == 1

    async def test_max_retries_one_no_sleep(self, mock_httpx_client):
        """With max_retries=1, there should be no sleep (only 1 attempt)."""
        fail_resp = _make_searxng_response([], status_code=500)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client),
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

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert len(results) == 1

    async def test_uses_safe_httpx_client(self, mock_httpx_client):
        """Verify that safe_httpx_client is called (not raw httpx.AsyncClient)."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("web_core.search.client.httpx.AsyncClient", return_value=mock_httpx_client) as mock_factory:
            await search(SEARXNG_URL, "test")

        mock_factory.assert_called_once_with(timeout=15.0)
