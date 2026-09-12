"""Headless strategy: Crawl4AI wrapper for JS-rendered pages with stealth mode."""

from __future__ import annotations

from typing import Any

from web_core.fingerprint import FingerprintProfile
from web_core.http.client import is_safe_url
from web_core.http.url import extract_domain
from web_core.scraper.base import BaseStrategy, ScrapingResult


class HeadlessStrategy(BaseStrategy):
    """Use Crawl4AI headless browser with a stable optional profile."""

    name: str = "headless"

    def __init__(
        self,
        timeout: float = 60.0,
        wait_for: str | None = None,
        stealth: bool = True,
        proxy: str | None = None,
        crawler_factory: Any = None,
        profile: FingerprintProfile | None = None,
    ):
        self.timeout = timeout
        self.wait_for = wait_for
        self.stealth = stealth
        self.proxy = proxy
        self.profile = profile
        self._crawler_factory = crawler_factory

    def _build_browser_config(self) -> Any:
        """Build a Crawl4AI BrowserConfig with profile and proxy settings."""
        from crawl4ai import BrowserConfig

        config: dict[str, Any] = {
            "headless": True,
            "browser_type": "chromium",
            "enable_stealth": self.stealth,
            "verbose": False,
        }
        if self.profile is not None:
            config.update(
                user_agent=self.profile.user_agent,
                viewport_width=self.profile.viewport_width,
                viewport_height=self.profile.viewport_height,
            )
        browser_config = BrowserConfig(**config)
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
        if not is_safe_url(url):
            raise ValueError(f"SSRF blocked: {url}")
        if self.profile is None:
            self.profile = FingerprintProfile.for_domain(extract_domain(url))
        crawler_run_config = self._build_crawler_run_config()
        if self._crawler_factory is not None:
            crawler = self._crawler_factory()
            result = await crawler.arun(url=url, config=crawler_run_config)
        else:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler(config=self._build_browser_config()) as crawler:
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
