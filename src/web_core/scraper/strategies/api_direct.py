"""API endpoint discovery and direct fetching strategy."""

from __future__ import annotations

import re
from typing import Any, ClassVar
from urllib.parse import urljoin

from web_core.http.client import safe_httpx_client
from web_core.scraper.base import BaseStrategy, ScrapingResult


class APIDirectStrategy(BaseStrategy):
    """Discover API endpoints in page source and fetch data directly."""

    name: str = "api_direct"
    API_PATTERNS: ClassVar[list[str]] = [
        r'"(https?://[^"]*api[^"]*)"',
        r"'(https?://[^']*api[^']*)'",
        r'"(/api/[^"]*)"',
        r"fetch\(['\"]([^'\"]+)['\"]\)",
        r"axios\.\w+\(['\"]([^'\"]+)['\"]\)",
    ]
    _API_PATTERNS_COMPILED: ClassVar[list[re.Pattern[str]]] = [re.compile(p) for p in API_PATTERNS]

    def __init__(self, timeout: float = 30.0, http_client: Any = None):
        self.timeout = timeout
        self._http_client = http_client

    def discover_apis(self, html: str) -> list[str]:
        """Extract unique API endpoint URLs from *html* source."""
        apis: list[str] = []
        for pattern in self._API_PATTERNS_COMPILED:
            apis.extend(pattern.findall(html))
        return list(dict.fromkeys(apis))

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Discover and fetch from an API endpoint, or fall back to page source."""
        api_url = selectors.get("api_url") if selectors else None
        client = self._http_client if self._http_client is not None else safe_httpx_client(timeout=self.timeout)
        should_close = self._http_client is None

        try:
            if api_url is None:
                page_response = await client.get(url, follow_redirects=True)
                discovered = self.discover_apis(page_response.text)
                if not discovered:
                    return ScrapingResult(
                        content=page_response.text,
                        url=url,
                        strategy=self.name,
                        status_code=page_response.status_code,
                        metadata={"apis_found": 0, "fallback": "page_source"},
                    )
                api_url = discovered[0]
                if api_url.startswith("/"):
                    api_url = urljoin(url, api_url)

            api_response = await client.get(api_url, headers={"Accept": "application/json"}, follow_redirects=True)
            return ScrapingResult(
                content=api_response.text,
                url=api_url,
                strategy=self.name,
                status_code=api_response.status_code,
                metadata={
                    "api_url": api_url,
                    "content_type": api_response.headers.get("content-type", ""),
                },
            )
        finally:
            if should_close:
                await client.aclose()
