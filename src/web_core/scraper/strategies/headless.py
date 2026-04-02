"""Headless strategy: Crawl4AI wrapper for JS-rendered pages."""

from __future__ import annotations

from typing import Any

from web_core.scraper.base import BaseStrategy, ScrapingResult


class HeadlessStrategy(BaseStrategy):
    """Use Crawl4AI headless browser to render JS-heavy pages."""

    name: str = "headless"

    def __init__(
        self,
        timeout: float = 60.0,
        wait_for: str | None = None,
        crawler_factory: Any = None,
        **kwargs: Any,
    ):
        self.timeout = timeout
        self.wait_for = wait_for
        self._crawler_factory = crawler_factory
        # Store extra kwargs as attributes for flexibility
        for k, v in kwargs.items():
            setattr(self, k, v)

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Fetch *url* via Crawl4AI headless browser rendering."""
        if self._crawler_factory is not None:
            crawler = self._crawler_factory()
            result = await crawler.arun(url=url, timeout=self.timeout, wait_for=self.wait_for)
        else:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url, timeout=self.timeout, wait_for=self.wait_for)

        content = getattr(result, "markdown", "") or getattr(result, "html", "") or ""
        status = getattr(result, "status_code", 200)
        return ScrapingResult(
            content=content,
            url=url,
            strategy=self.name,
            status_code=status,
            metadata={
                "rendered": True,
                "content_length": len(content),
                "wait_for": self.wait_for,
            },
        )
