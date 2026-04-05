"""Headless strategy: Crawl4AI wrapper for JS-rendered pages with stealth mode."""

from __future__ import annotations

from typing import Any

from web_core.scraper.base import BaseStrategy, ScrapingResult


class HeadlessStrategy(BaseStrategy):
    """Use Crawl4AI headless browser to render JS-heavy pages.

    Supports stealth mode (enabled by default) to bypass bot detection,
    random user-agent rotation, and optional proxy configuration.
    """

    name: str = "headless"

    def __init__(
        self,
        timeout: float = 60.0,
        wait_for: str | None = None,
        stealth: bool = True,
        proxy: str | None = None,
        crawler_factory: Any = None,
    ):
        self.timeout = timeout
        self.wait_for = wait_for
        self.stealth = stealth
        self.proxy = proxy
        self._crawler_factory = crawler_factory

    def _build_browser_config(self) -> Any:
        """Build a Crawl4AI BrowserConfig with stealth and proxy settings."""
        from crawl4ai import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            browser_type="chromium",
            enable_stealth=self.stealth,
            user_agent_mode="random",
            verbose=False,
        )
        if self.proxy is not None:
            browser_config.proxy_config = {"server": self.proxy}
        return browser_config

    def _build_crawler_run_config(self) -> Any:
        """Build a Crawl4AI CrawlerRunConfig with wait and delay settings."""
        from crawl4ai import CrawlerRunConfig

        return CrawlerRunConfig(
            wait_for=self.wait_for or "css:body",
            delay_before_return_html=2.0,
            page_timeout=int(self.timeout * 1000),
            verbose=False,
        )

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Fetch *url* via Crawl4AI headless browser rendering."""
        crawler_run_config = self._build_crawler_run_config()

        if self._crawler_factory is not None:
            crawler = self._crawler_factory()
            result = await crawler.arun(url=url, config=crawler_run_config)
        else:
            from crawl4ai import AsyncWebCrawler

            browser_config = self._build_browser_config()
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_run_config)

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
                "stealth": self.stealth,
                "proxy": self.proxy is not None,
            },
        )
