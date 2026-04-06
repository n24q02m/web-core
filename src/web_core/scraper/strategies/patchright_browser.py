"""Patchright browser strategy with Cloudflare challenge detection."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from web_core.scraper.base import BaseStrategy, ScrapingResult
from web_core.scraper.utils import detect_cloudflare_challenge

logger = logging.getLogger(__name__)

# Thoi gian cho mac dinh cho CF challenge (giay)
_CF_CHALLENGE_WAIT: float = 3.0
# So lan toi da kiem tra CF challenge da resolve chua
_CF_POLL_MAX_CHECKS: int = 20
# Khoang thoi gian giua cac lan kiem tra (giay)
_CF_POLL_INTERVAL: float = 0.5


class PatchrightStrategy(BaseStrategy):
    """Direct Patchright browser for sites where Crawl4AI stealth fails.

    Uses undetected Playwright (patchright) to bypass Cloudflare JS challenges.
    After page load, detects CF challenge type and waits for resolution:

    - **JS challenge**: Polls page content until challenge HTML disappears
      or ``__cf_bm`` cookie is set (up to 10s).
    - **Turnstile**: Detected but NOT solved here — CaptchaStrategy handles
      Turnstile solving. This strategy escalates to let captcha strategy solve.
    - **No challenge**: Returns immediately after networkidle.
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

    async def _wait_for_cf_resolution(self, page: Any) -> str:
        """Wait for Cloudflare JS challenge to auto-resolve.

        Polls page content up to ``_CF_POLL_MAX_CHECKS`` times, checking
        whether the challenge HTML has disappeared. Also checks for
        ``__cf_bm`` cookie as a signal that CF has verified the browser.

        Returns the final page content.
        """
        for _ in range(_CF_POLL_MAX_CHECKS):
            await asyncio.sleep(_CF_POLL_INTERVAL)

            # Check if CF set verification cookie
            cookies = await page.context.cookies()
            cf_cookies = [c for c in cookies if c.get("name", "").startswith("__cf")]
            if cf_cookies:
                logger.debug("CF verification cookie detected, challenge resolved")
                break

            content = await page.content()
            if detect_cloudflare_challenge(content) is None:
                logger.debug("CF challenge HTML no longer present")
                return content

        return await page.content()

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Fetch *url* via Patchright undetected browser.

        Quy trinh:
        1. Launch browser + navigate voi networkidle wait
        2. Kiem tra CF challenge trong HTML
        3. Neu JS challenge: poll cho den khi resolve (toi da 10s)
        4. Neu Turnstile/managed: tra ve challenge HTML (de CaptchaStrategy xu ly)
        5. Neu khong co challenge: tra ve content ngay
        """
        if self._provider is not None:
            provider = self._provider
        else:
            from web_core.browsers.patchright import PatchrightProvider

            provider = PatchrightProvider(headless=self.headless)

        cf_challenge_type = None

        try:
            browser = await provider.launch(config=self.launch_config)
            page = await browser.new_page()

            try:
                response = await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)

                content = await page.content()
                cf_challenge_type = detect_cloudflare_challenge(content)

                if cf_challenge_type == "js_challenge":
                    logger.info("CF JS challenge detected for %s, polling for resolution", url)
                    content = await self._wait_for_cf_resolution(page)
                    # Re-check after wait
                    cf_challenge_type = detect_cloudflare_challenge(content)
                elif cf_challenge_type == "turnstile":
                    logger.info("CF Turnstile detected for %s, cannot solve here", url)
                    # Return the challenge HTML — CaptchaStrategy will handle
                elif cf_challenge_type == "managed":
                    logger.info("CF managed challenge for %s, polling for resolution", url)
                    # Poll until challenge resolves (redirect to real page)
                    for _ in range(_CF_POLL_MAX_CHECKS):
                        await asyncio.sleep(_CF_POLL_INTERVAL)
                        content = await page.content()
                        cf_challenge_type = detect_cloudflare_challenge(content)
                        if cf_challenge_type is None:
                            logger.debug("CF managed challenge resolved for %s", url)
                            break
                    # If still challenged after polls, wait for navigation
                    if cf_challenge_type is not None:
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                            content = await page.content()
                            cf_challenge_type = detect_cloudflare_challenge(content)
                        except Exception:
                            pass

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
                "cf_challenge": cf_challenge_type,
            },
        )
