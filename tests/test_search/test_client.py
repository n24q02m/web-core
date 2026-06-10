"""Tests for SearXNG search client."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import httpx
import pytest

from web_core.search import client as client_mod
from web_core.search.client import (
    _apply_domain_cap,
    _build_filtered_query,
    _get_shared_client,
    search,
)
from web_core.search.models import SearchError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEARXNG_URL = "https://search.example.com"


@pytest.fixture(autouse=True)
def _reset_shared_client():
    """Reset the global _shared_client before each test."""
    old_client = client_mod._shared_client
    client_mod._shared_client = None
    yield
    client_mod._shared_client = old_client


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
# _get_shared_client
# ---------------------------------------------------------------------------


class TestSharedClient:
    """Tests for the shared httpx client caching logic."""

    async def test_get_shared_client_caching(self):
        """Verify that multiple calls return the same client instance."""
        with patch("web_core.search.client.safe_httpx_client") as mock_factory:
            m1 = MagicMock()
            m1.is_closed = False
            mock_factory.return_value = m1

            c1 = _get_shared_client()
            c2 = _get_shared_client()

            assert c1 is m1
            assert c2 is c1
            assert mock_factory.call_count == 1

    async def test_get_shared_client_reinit_when_closed(self):
        """Verify that a new client is created if the cached one is closed."""
        with patch("web_core.search.client.safe_httpx_client") as mock_factory:
            m1 = MagicMock()
            m1.is_closed = False
            m2 = MagicMock()
            m2.is_closed = False
            mock_factory.side_effect = [m1, m2]

            # 1. Create first client
            c1 = _get_shared_client()
            assert c1 is m1

            # 2. Close it and verify re-init
            m1.is_closed = True
            c2 = _get_shared_client()
            assert c2 is m2
            assert c2 is not c1
            assert mock_factory.call_count == 2


# ---------------------------------------------------------------------------
# _build_filtered_query
# ---------------------------------------------------------------------------


def test_build_filtered_query_basic():
    """Simple query without filters."""
    assert _build_filtered_query("hello") == "hello"


def test_build_filtered_query_include():
    """Query with site: include filters."""
    q = _build_filtered_query("hello", include_domains=["a.com", "b.com"])
    assert q == "(site:a.com OR site:b.com) hello"


def test_build_filtered_query_exclude():
    """Query with -site: exclude filters."""
    q = _build_filtered_query("hello", exclude_domains=["a.com", "b.com"])
    assert q == "hello -site:a.com -site:b.com"


def test_build_filtered_query_mixed():
    """Query with both include and exclude filters."""
    q = _build_filtered_query("hello", include_domains=["inc.com"], exclude_domains=["exc.com"])
    assert q == "(site:inc.com) hello -site:exc.com"


def test_build_filtered_query_caps():
    """Verify include (5) and exclude (10) limits."""
    includes = [f"{i}.com" for i in range(10)]
    excludes = [f"{i}.org" for i in range(20)]
    q = _build_filtered_query("hello", include_domains=includes, exclude_domains=excludes)

    assert q.count("site:") == 15  # 5 includes + 10 excludes
    assert q.count("OR") == 4


def test_build_filtered_query_invalid_domains():
    """Invalid domains should be silently skipped."""
    q = _build_filtered_query("hello", include_domains=["safe.com", "not a domain!!!", "127.0.0.1"])
    # 127.0.0.1 is technically valid per is_valid_domain but might be blocked elsewhere.
    # Actually is_valid_domain("127.0.0.1") is True.
    assert "not a domain!!!" not in q
    assert "site:safe.com" in q


def test_build_filtered_query_all_invalid_include():
    """Line 94 branch: safe_include is empty because all domains are invalid."""
    q = _build_filtered_query("hello", include_domains=["invalid domain", "not-a-domain"])
    assert q == "hello"


def test_build_filtered_query_exclude_invalid():
    """Line 102 branch: skip invalid domains in exclude list."""
    q = _build_filtered_query("hello", exclude_domains=["invalid domain", "safe.com"])
    assert q == "hello -site:safe.com"


# ---------------------------------------------------------------------------
# _apply_domain_cap
# ---------------------------------------------------------------------------


def test_apply_domain_cap():
    """Results should be limited per domain."""
    raw = [
        {"url": "https://a.com/1"},
        {"url": "https://a.com/2"},
        {"url": "https://a.com/3"},
        {"url": "https://a.com/4"},  # capped
        {"url": "https://b.com/1"},
    ]
    capped = _apply_domain_cap(raw)
    assert len(capped) == 4
    assert capped[-1]["url"] == "https://b.com/1"


def test_apply_domain_cap_www_normalization():
    """www. domains should be treated same as non-www."""
    raw = [
        {"url": "https://example.com/1"},
        {"url": "https://www.example.com/2"},
        {"url": "https://example.com/3"},
        {"url": "https://www.example.com/4"},  # capped
    ]
    capped = _apply_domain_cap(raw)
    assert len(capped) == 3


def test_apply_domain_cap_no_scheme():
    """Handle URLs without schemes or with relative paths."""
    raw = [
        {"url": "//a.com/1"},
        {"url": "//a.com/2"},
        {"url": "//a.com/3"},
        {"url": "//a.com/4"},  # capped
        {"url": "just-a-path/1"},  # domain becomes "just-a-path"
        {"url": "just-a-path/2"},
    ]
    capped = _apply_domain_cap(raw)
    assert len(capped) == 5


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestSearch:
    """Main search() function tests."""

    async def test_search_success(self, mock_httpx_client):
        """Basic search success path."""
        raw_results = [
            _raw_result("https://a.com/1", "Title 1", "Snippet 1", "google"),
            _raw_result("https://b.com/1", "Title 2", "Snippet 2", "bing"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test query")

        assert len(results) == 2
        assert results[0].url == "https://a.com/1"
        assert results[0].source == "google"
        assert results[1].source == "bing"

    async def test_search_dedup(self, mock_httpx_client):
        """Duplicate URLs should be merged."""
        raw_results = [
            _raw_result("https://a.com/1", "Short Title", "Snippet 1", "google"),
            _raw_result("https://a.com/1", "Much Longer Title", "Longer Snippet", "bing"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw_results))

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "test")

        assert len(results) == 1
        assert results[0].source == "bing, google"
        assert results[0].snippet == "Longer Snippet"
        assert results[0].title == "Much Longer Title"

    async def test_search_retry_on_500(self, mock_httpx_client):
        """Transient errors should trigger retries."""
        fail_resp = _make_searxng_response([], status_code=500)
        ok_resp = _make_searxng_response([_raw_result("https://a.com/1")])

        # Fail twice, then succeed
        mock_httpx_client.get = AsyncMock(side_effect=[fail_resp, fail_resp, ok_resp])

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            results = await search(SEARXNG_URL, "test", max_retries=3)

        assert len(results) == 1
        assert mock_httpx_client.get.call_count == 3
        assert mock_sleep.call_count == 2

    async def test_search_fail_on_400(self, mock_httpx_client):
        """4xx errors should not be retried."""
        fail_resp = _make_searxng_response([], status_code=400)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            pytest.raises(SearchError) as exc,
        ):
            await search(SEARXNG_URL, "test")

        assert "HTTP 400" in exc.value.reason
        assert mock_httpx_client.get.call_count == 1
        mock_sleep.assert_not_called()

    async def test_search_exhaust_retries(self, mock_httpx_client):
        """Failure after all retries are exhausted."""
        fail_resp = _make_searxng_response([], status_code=503)
        mock_httpx_client.get = AsyncMock(return_value=fail_resp)

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(SearchError) as exc,
        ):
            await search(SEARXNG_URL, "test", max_retries=2)

        assert "HTTP 503" in exc.value.reason
        assert mock_httpx_client.get.call_count == 2

    async def test_search_request_error(self, mock_httpx_client):
        """httpx.RequestError (e.g. DNS) should also trigger retry."""
        ok_resp = _make_searxng_response([_raw_result("https://a.com/1")])
        mock_httpx_client.get = AsyncMock(
            side_effect=[
                httpx.ConnectError("failed", request=MagicMock()),
                ok_resp,
            ]
        )

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            results = await search(SEARXNG_URL, "test")

        assert len(results) == 1
        assert mock_httpx_client.get.call_count == 2

    async def test_validates_time_range(self, mock_httpx_client):
        """Invalid time_range values should not be passed to SearXNG."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", time_range="invalid")

        call_kwargs = mock_httpx_client.get.call_args
        assert "time_range" not in call_kwargs.kwargs["params"]

    async def test_search_with_valid_time_range(self, mock_httpx_client):
        """Line 169: Pass a valid time_range."""
        ok_resp = _make_searxng_response([])
        mock_httpx_client.get = AsyncMock(return_value=ok_resp)
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await search(SEARXNG_URL, "test", time_range="day")
        call_kwargs = mock_httpx_client.get.call_args
        assert call_kwargs.kwargs["params"]["time_range"] == "day"

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

        mock_factory.assert_called_once_with(event_hooks=ANY, timeout=15.0)

    async def test_dedup_with_empty_source(self, mock_httpx_client):
        """Branch 204->206: Existing result, but new hit has no engine/source."""
        raw = [
            _raw_result("https://a.com", "T", "S", "google"),
            _raw_result("https://a.com", "T", "S", ""),  # empty engine
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw))
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "q")
        assert results[0].source == "google"

    async def test_dedup_with_empty_title(self, mock_httpx_client):
        """Branch 208->194: Existing result, new hit has longer snippet but empty title."""
        raw = [
            _raw_result("https://a.com", "Original Title", "Short", "google"),
            _raw_result("https://a.com", "", "Much Longer Snippet", "bing"),
        ]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw))
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await search(SEARXNG_URL, "q")
        assert results[0].snippet == "Much Longer Snippet"
        assert results[0].title == "Original Title"  # Should not have been overwritten by empty string

    async def test_catches_and_reraises_search_error(self, mock_httpx_client):
        """Line 260: Catch SearchError inside the loop and re-raise it."""
        raw = [_raw_result("https://a.com")]
        mock_httpx_client.get = AsyncMock(return_value=_make_searxng_response(raw))

        with (
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("web_core.search.client.normalize_url", side_effect=SearchError("q", "forced")),
        ):
            with pytest.raises(SearchError) as exc:
                await search(SEARXNG_URL, "q")
            assert exc.value.reason == "forced"
