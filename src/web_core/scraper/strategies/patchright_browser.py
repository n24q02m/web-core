"""Patchright browser strategy for sites where Crawl4AI stealth fails."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from web_core.scraper.base import BaseStrategy, ScrapingResult

logger = logging.getLogger(__name__)

# Thoi gian cho mac dinh cho CF challenge (giay)
_CF_CHALLENGE_WAIT: float = 3.0


class PatchrightStrategy(BaseStrategy):
    """Direct Patchright browser for sites where Crawl4AI stealth fails.

    Uses undetected Playwright (patchright) to bypass Cloudflare JS challenges
    and other anti-bot protections that fingerprint standard Playwright/Puppeteer.
    """

    name: str = "patchright"

    def __init__(
        self,
        timeout: float = 60.0,
        headless: bool = True,
        cf_wait: float = _CF_CHALLENGE_WAIT,
        launch_config: dict[str, Any] | None = None,
        provider: Any = None,
    ):
        self.timeout = timeout
        self.headless = headless
        self.cf_wait = cf_wait
        self.launch_config = launch_config
        self._provider = provider

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Fetch *url* via Patchright undetected browser.

        Quy trinh:
        1. Khoi tao PatchrightProvider (hoac dung provider duoc inject)
        2. Launch browser va tao page moi
        3. Navigate toi URL voi networkidle wait
        4. Cho CF challenge resolve (mac dinh 3 giay)
        5. Lay noi dung trang
        6. Dong browser
        7. Tra ve ScrapingResult
        """
        if self._provider is not None:
            provider = self._provider
        else:
            from web_core.browsers.patchright import PatchrightProvider

            provider = PatchrightProvider(headless=self.headless)

        try:
            browser = await provider.launch(config=self.launch_config)
            page = await browser.new_page()

            try:
                response = await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)

                # Cho CF JS challenge resolve
                await asyncio.sleep(self.cf_wait)

                content = await page.content()
                status_code = response.status if response else 200
                final_url = page.url

            finally:
                await page.close()
        finally:
            await provider.close()

        return ScrapingResult(
            content=content,
            url=final_url,
            strategy=self.name,
            status_code=status_code,
            metadata={
                "rendered": True,
                "content_length": len(content),
                "headless": self.headless,
                "cf_wait": self.cf_wait,
            },
        )
