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
from urllib.parse import urlparse

import httpx

from web_core.http.client import safe_httpx_client
from web_core.http.url import is_valid_domain, normalize_url
from web_core.search.models import SearchError, SearchResult

logger = logging.getLogger(__name__)

_BASE_DELAY = 1.0
_MAX_PER_DOMAIN = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_domain_cap(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Limit results to at most ``_MAX_PER_DOMAIN`` per domain."""
    domain_counts: dict[str, int] = {}
    result: list[dict[str, str]] = []
    for item in items:
        parsed = urlparse(item.get("url", ""))
        domain = parsed.netloc
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

    - ``include_domains``: up to 5 domains joined with ``OR site:``
    - ``exclude_domains``: up to 10 domains prepended with ``-site:``

    Invalid domains (per ``is_valid_domain``) are silently skipped to
    prevent search operator injection.
    """
    parts = [query]
    if include_domains:
        safe = [d for d in include_domains[:5] if is_valid_domain(d)]
        if safe:
            site_filter = " OR ".join(f"site:{d}" for d in safe)
            parts = [f"({site_filter}) {query}"]
    if exclude_domains:
        for domain in exclude_domains[:10]:
            if is_valid_domain(domain):
                parts.append(f"-site:{domain}")
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

    async with safe_httpx_client(timeout=15.0) as client:
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

                # Format raw results into dicts
                formatted = [
                    {
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "snippet": r.get("content", ""),
                        "source": r.get("engine", ""),
                    }
                    for r in results
                ]

                # Deduplicate: merge sources, keep longest snippet
                seen: dict[str, dict[str, str]] = {}
                for item in formatted:
                    norm_url = normalize_url(item["url"])
                    if norm_url in seen:
                        existing = seen[norm_url]
                        if item["source"] and item["source"] not in existing["source"]:
                            existing["source"] += f", {item['source']}"
                        if len(item.get("snippet", "")) > len(existing.get("snippet", "")):
                            existing["snippet"] = item["snippet"]
                            existing["title"] = item["title"] or existing["title"]
                    else:
                        seen[norm_url] = item

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
                last_error = f"Request error: {exc}"
                logger.warning(
                    "Request error for query '%s' (attempt %d/%d): %s",
                    query,
                    attempt,
                    max_retries,
                    exc,
                )
            except SearchError:
                raise
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Unexpected error for query '%s' (attempt %d/%d): %s",
                    query,
                    attempt,
                    max_retries,
                    exc,
                )

            if attempt < max_retries:
                delay = _BASE_DELAY * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

    raise SearchError(query, last_error or "All attempts failed")
