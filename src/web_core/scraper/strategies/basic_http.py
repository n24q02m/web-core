"""Basic HTTP strategy using httpx with SSRF protection."""

from __future__ import annotations

from typing import Any, ClassVar

from web_core.http.client import safe_httpx_client
from web_core.scraper.base import BaseStrategy, ScrapingResult


class BasicHTTPStrategy(BaseStrategy):
    """Fetch pages via httpx with browser-like headers and SSRF protection."""

    name: str = "basic_http"
    DEFAULT_HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    def __init__(
        self,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        http_client: Any = None,
    ):
        self.timeout = timeout
        self.headers = headers or self.DEFAULT_HEADERS.copy()
        self._http_client = http_client

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Fetch *url* via plain HTTP GET with browser-like headers."""
        if self._http_client is not None:
            response = await self._http_client.get(
                url, headers=self.headers, timeout=self.timeout, follow_redirects=True
            )
        else:
            async with safe_httpx_client(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)

        return ScrapingResult(
            content=response.text,
            url=str(response.url),
            strategy=self.name,
            status_code=response.status_code,
            metadata={
                "content_type": response.headers.get("content-type", ""),
                "content_length": len(response.text),
            },
        )
