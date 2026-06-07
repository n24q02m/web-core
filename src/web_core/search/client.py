"""SearXNG search client with retry, deduplication, and domain filtering.

Adapted from wet-mcp's searxng.py with web-core conventions:
- SSRF-safe HTTP via ``safe_httpx_client``
- URL normalization and domain validation from ``web_core.http.url``
- Returns typed ``SearchResult`` objects instead of JSON strings
- Raises ``SearchError`` on failure instead of returning error payloads
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from web_core.http import safe_httpx_client
from web_core.http.url import is_valid_domain, normalize_url
from web_core.search.models import SearchError, SearchResult

logger = logging.getLogger(__name__)

_BASE_DELAY = 1.0
_MAX_PER_DOMAIN = 3

_shared_client: httpx.AsyncClient | None = None


def _get_shared_client() -> httpx.AsyncClient:
    """Lazy initialization of a shared httpx.AsyncClient.

    Performance Optimization: Reusing the client connection pool avoids the overhead
    of establishing new TCP/TLS connections for every search request.
    """
    global _shared_client
    if _shared_client is None or getattr(_shared_client, "is_closed", False):
        _shared_client = safe_httpx_client(allow_private=True, timeout=15.0)
    return _shared_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_domain_cap(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Limit results to at most ``_MAX_PER_DOMAIN`` per domain."""
    domain_counts: dict[str, int] = {}
    result: list[dict[str, Any]] = []
    for item in items:
        url = item.get("url") or ""
        # Fast path domain extraction (~3.5x faster than urlparse for hot loops)
        if url.startswith("//"):
            domain = url[2:].partition("/")[0].partition("?")[0].partition("#")[0]
        else:
            _, sep, rest = url.partition("://")
            domain_part = rest if sep else url
            domain = domain_part.partition("/")[0].partition("?")[0].partition("#")[0]

        if domain.startswith("www."):
            domain = domain[4:]
        count = domain_counts.get(domain, 0)
        if count < _MAX_PER_DOMAIN:
            result.append(item)
            domain_counts[domain] = count + 1
    return result


def _build_filtered_query(
    query: str,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> str:
    """Build a SearXNG query with site: include/exclude operators.

    - ``include_domains``: up to 5 unique domains joined with ``OR site:``
    - ``exclude_domains``: up to 10 unique domains prepended with ``-site:``

    Invalid domains (per ``is_valid_domain``) are silently skipped to
    prevent search operator injection.
    """
    parts = [query]

    if include_domains:
        seen_include = set()
        safe_include = []
        for d in include_domains:
            if d not in seen_include and is_valid_domain(d):
                seen_include.add(d)
                safe_include.append(d)
                if len(safe_include) >= 5:
                    break
        if safe_include:
            site_filter = " OR ".join(f"site:{d}" for d in safe_include)
            parts = [f"({site_filter}) {query}"]

    if exclude_domains:
        seen_exclude = set()
        count_exclude = 0
        for d in exclude_domains:
            if d not in seen_exclude and is_valid_domain(d):
                seen_exclude.add(d)
                parts.append(f"-site:{d}")
                count_exclude += 1
                if count_exclude >= 10:
                    break

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def search(
    searxng_url: str,
    query: str,
    *,
    categories: str = "general",
    max_results: int = 10,
    time_range: str | None = None,
    language: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    max_retries: int = 3,
) -> list[SearchResult]:
    """Search SearXNG and return deduplicated, domain-capped results.

    Parameters
    ----------
    searxng_url:
        Base URL of the SearXNG instance (e.g. ``http://localhost:8888``).
    query:
        The search query string.
    categories:
        SearXNG search categories (default ``"general"``).
    max_results:
        Maximum number of results to return after dedup and domain cap.
    time_range:
        Optional time range filter: ``"day"``, ``"week"``, ``"month"``, ``"year"``.
    language:
        Optional language code (e.g. ``"en"``).
    include_domains:
        Restrict results to these domains (max 5).
    exclude_domains:
        Exclude results from these domains (max 10).
    max_retries:
        Number of retry attempts on transient (5xx / connection) errors.

    Returns
    -------
    list[SearchResult]
        Deduplicated results capped at ``max_results``.

    Raises
    ------
    SearchError
        On 4xx (non-retryable) or after all retries are exhausted.
    """
    effective_query = _build_filtered_query(query, include_domains, exclude_domains)
    params: dict[str, str] = {
        "q": effective_query,
        "format": "json",
        "categories": categories,
    }
    if time_range and time_range in ("day", "week", "month", "year"):
        params["time_range"] = time_range
    if language:
        params["language"] = language

    last_error: str | None = None

    # SearXNG is a trusted local service — bypass SSRF protection.
    # SSRF-safe client blocks localhost/private IPs by design, but SearXNG
    # runs on localhost. External URL fetching still uses safe_httpx_client.
    client = _get_shared_client()
    for attempt in range(1, max_retries + 1):
        try:
            response = await client.get(
                f"{searxng_url}/search",
                params=params,
                headers={"X-Real-IP": "127.0.0.1", "X-Forwarded-For": "127.0.0.1"},
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])[: max_results * 2]

            # Deduplicate directly from raw results: merge sources, keep longest snippet
            # Performance Optimization: Combining extraction and deduplication loops
            # avoids creating an intermediate list of formatted dicts, saving ~25%
            # processing time for large result sets.
            seen: dict[str, dict[str, Any]] = {}
            for r in results:
                url = r.get("url", "")
                norm_url = normalize_url(url)

                source = r.get("engine", "")
                snippet = r.get("content", "")
                title = r.get("title", "")

                if norm_url in seen:
                    existing = seen[norm_url]
                    if source:
                        existing["source"].add(source)
                    if len(snippet) > len(existing["snippet"]):
                        existing["snippet"] = snippet
                        if title:
                            existing["title"] = title
                else:
                    seen[norm_url] = {
                        "url": url,
                        "title": title,
                        "snippet": snippet,
                        "source": {source} if source else set(),
                    }

            # Convert sets back to sorted strings
            for value in seen.values():
                value["source"] = ", ".join(sorted(value["source"]))

            # Domain cap + final limit
            capped = _apply_domain_cap(list(seen.values()))[:max_results]

            return [
                SearchResult(
                    url=r["url"],
                    title=r["title"],
                    snippet=r["snippet"],
                    source=r["source"],
                )
                for r in capped
            ]

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            last_error = f"HTTP {status}"
            if status < 500:
                # 4xx errors are non-retryable
                logger.warning("Non-retryable HTTP %d for query '%s'", status, query)
                raise SearchError(query, last_error) from e
            logger.warning(
                "Retryable HTTP %d for query '%s' (attempt %d/%d)",
                status,
                query,
                attempt,
                max_retries,
            )
        except httpx.RequestError as exc:
            exc_name = type(exc).__name__
            last_error = f"Request error: {exc_name}"
            logger.warning(
                "Request error for query '%s' (attempt %d/%d): %s",
                query,
                attempt,
                max_retries,
                exc_name,
            )
        except SearchError:
            raise
        except Exception as exc:
            exc_name = type(exc).__name__
            last_error = f"Unexpected error: {exc_name}"
            logger.warning(
                "Unexpected error for query '%s' (attempt %d/%d): %s",
                query,
                attempt,
                max_retries,
                exc_name,
            )

        if attempt < max_retries:
            delay = _BASE_DELAY * (2 ** (attempt - 1))
            await asyncio.sleep(delay)

    raise SearchError(query, last_error or "All attempts failed")
