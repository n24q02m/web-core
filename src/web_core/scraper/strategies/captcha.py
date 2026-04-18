"""Captcha strategy: CapSolver API integration (ReCaptcha + Turnstile)."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from web_core.http.client import safe_httpx_client
from web_core.scraper.base import BaseStrategy, ScrapingResult
from web_core.scraper.utils import detect_cloudflare_challenge, extract_turnstile_sitekey

logger = logging.getLogger(__name__)

# CapSolver task types
RECAPTCHA_V2_PROXYLESS = "ReCaptchaV2TaskProxyLess"
TURNSTILE_PROXYLESS = "AntiTurnstileTaskProxyLess"

# Token extraction keys per captcha type (CapSolver API response format)
_SOLUTION_KEYS: dict[str, str] = {
    RECAPTCHA_V2_PROXYLESS: "gRecaptchaResponse",
    "ReCaptchaV3TaskProxyLess": "gRecaptchaResponse",
    TURNSTILE_PROXYLESS: "token",
}


class CaptchaStrategy(BaseStrategy):
    """Solve CAPTCHAs via CapSolver before fetching protected pages.

    Supports:
    - ReCaptcha V2 (proxyless)
    - Cloudflare Turnstile (proxyless)

    If ``selectors`` contains ``site_key``, the strategy solves explicitly.
    Otherwise, if the fallback strategy returns CF challenge HTML, the strategy
    auto-detects Turnstile and solves it transparently.
    """

    name: str = "captcha"
    CAPSOLVER_URL: str = "https://api.capsolver.com/createTask"

    def __init__(
        self,
        capsolver_api_key: str = "",
        fallback_strategy: BaseStrategy | None = None,
        http_client: Any = None,
    ):
        self.capsolver_api_key = capsolver_api_key
        self.fallback_strategy = fallback_strategy
        self._http_client = http_client

    async def solve_captcha(
        self,
        site_key: str,
        page_url: str,
        captcha_type: str = RECAPTCHA_V2_PROXYLESS,
    ) -> str:
        """Submit a captcha task to CapSolver and return the solution token.

        Supports both ReCaptcha and Turnstile via the ``captcha_type`` parameter.
        """
        payload = {
            "clientKey": self.capsolver_api_key,
            "task": {
                "type": captcha_type,
                "websiteURL": page_url,
                "websiteKey": site_key,
            },
        }

        if self._http_client is not None:
            response = await self._http_client.post(self.CAPSOLVER_URL, json=payload)
        else:
            async with safe_httpx_client() as client:
                response = await client.post(self.CAPSOLVER_URL, json=payload)

        data = response.json()
        solution_key = _SOLUTION_KEYS.get(captcha_type, "token")
        token = data.get("solution", {}).get(solution_key, "")

        if token:
            logger.info("CapSolver solved %s for %s", captcha_type, page_url)
        else:
            logger.warning("CapSolver failed to solve %s for %s: %s", captcha_type, page_url, data)

        return token

    async def _try_solve_turnstile(self, url: str, html: str) -> str:
        """Auto-detect Turnstile in HTML and solve if found.

        Returns the Turnstile token, or empty string if not applicable.
        """
        challenge_type = detect_cloudflare_challenge(html)
        if challenge_type != "turnstile":
            return ""

        site_key = extract_turnstile_sitekey(html)
        if not site_key:
            logger.warning("Turnstile detected but site_key not found in HTML for %s", url)
            return ""

        return await self.solve_captcha(
            site_key=site_key,
            page_url=url,
            captcha_type=TURNSTILE_PROXYLESS,
        )

    async def _extract_turnstile_sitekey(self, page: Any) -> str | None:
        """Extract Turnstile sitekey from Patchright page.

        Uses Python-level query (not JS eval) to find the Turnstile iframe src
        since CF challenge iframes may not be accessible via document.querySelectorAll.
        """
        import contextlib
        import re

        # Wait for the Turnstile iframe to appear
        with contextlib.suppress(Exception):
            await page.wait_for_selector("iframe[src*='challenges.cloudflare.com']", timeout=8000)

        # Strategy 1: data-sitekey attribute (static Turnstile)
        el = await page.query_selector("[data-sitekey]")
        if el:
            return await el.get_attribute("data-sitekey")

        # Strategy 2: Extract 0x-prefix key from CF Turnstile iframe src
        # e.g. /cdn-cgi/.../0x4AAAAAAADnPIDROrmt1Wwj/light/...
        iframes = await page.query_selector_all("iframe")
        for f in iframes:
            src = await f.get_attribute("src") or ""
            m = re.search(r"/(0x[A-Za-z0-9]+)[/&]", src)
            if m:
                return m.group(1)
            m2 = re.search(r"/([A-Za-z0-9]{20,})/(?:light|dark|auto)", src)
            if m2:
                return m2.group(1)

        # Strategy 3: Inline script sitekey
        scripts = await page.query_selector_all("script")
        for s in scripts:
            text = await s.text_content() or ""
            m = re.search(r"""sitekey['"\s:=]+['"]([A-Za-z0-9_-]{10,})['"]""", text, re.IGNORECASE)
            if m:
                return m.group(1)

        return None

    async def _solve_cf_turnstile_via_patchright(self, url: str) -> ScrapingResult:
        """Use Patchright to load page, extract Turnstile sitekey via Python API,
        solve with CapSolver, inject token back, and return final content."""

        from web_core.browsers.patchright import PatchrightProvider

        provider = PatchrightProvider(headless=True)
        try:
            browser = await provider.launch()
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)

                sitekey = await self._extract_turnstile_sitekey(page)

                if not sitekey:
                    # Fallback: read content as-is
                    content = await page.content()
                    return ScrapingResult(
                        content=content,
                        url=page.url,
                        strategy=self.name,
                        status_code=200,
                        metadata={"captcha_solved": False, "error": "sitekey_not_found"},
                    )

                logger.info("Extracted Turnstile sitekey for %s: %s...", url, sitekey[:12])

                # Solve with CapSolver
                token = await self.solve_captcha(site_key=sitekey, page_url=url, captcha_type=TURNSTILE_PROXYLESS)

                if not token:
                    content = await page.content()
                    return ScrapingResult(
                        content=content,
                        url=page.url,
                        strategy=self.name,
                        status_code=200,
                        metadata={"captcha_solved": False, "error": "capsolver_no_token"},
                    )

                # Inject token and submit
                await page.evaluate(
                    """(token) => {
                    // Set CF Turnstile response token
                    const inputs = document.querySelectorAll('[name="cf-turnstile-response"]');
                    inputs.forEach(el => { el.value = token; });
                    // Try calling the turnstile callback if present
                    if (window.turnstile && window.turnstile.getResponse) {
                        const widgets = document.querySelectorAll('[id^="cf-turnstile"]');
                        widgets.forEach(w => {
                            try { window.turnstile.execute(w.id, { response: token }); } catch(e) {}
                        });
                    }
                    // Submit first form if present
                    const form = document.querySelector('form#challenge-form, form[action*="cdn-cgi"]');
                    if (form) form.submit();
                }""",
                    token,
                )

                # Wait for navigation to actual page
                with contextlib.suppress(Exception):
                    await page.wait_for_load_state("networkidle", timeout=15000)

                content = await page.content()
                final_url = page.url
                return ScrapingResult(
                    content=content,
                    url=final_url,
                    strategy=self.name,
                    status_code=200,
                    metadata={"captcha_solved": True, "captcha_type": TURNSTILE_PROXYLESS},
                )
            finally:
                await page.close()
        finally:
            await provider.close()

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Solve captcha if needed, then delegate to fallback strategy.

        Flow:
        1. If selectors has explicit site_key + captcha_type: solve with fallback strategy
        2. If capsolver_api_key set: use Patchright + CapSolver for CF Turnstile
        3. Fall back to fallback_strategy or return empty
        """
        captcha_type = (selectors or {}).get("captcha_type", RECAPTCHA_V2_PROXYLESS)

        # Explicit captcha solving (user-provided site_key) via fallback
        if selectors and "site_key" in selectors and self.fallback_strategy is not None:
            captcha_token = await self.solve_captcha(
                site_key=selectors["site_key"],
                page_url=url,
                captcha_type=captcha_type,
            )
            result = await self.fallback_strategy.fetch(url, selectors)
            return ScrapingResult(
                content=result.content,
                url=result.url,
                strategy=self.name,
                status_code=result.status_code,
                metadata={**result.metadata, "captcha_solved": bool(captcha_token)},
            )

        # CF Turnstile: use Patchright + CapSolver full browser flow
        if self.capsolver_api_key:
            return await self._solve_cf_turnstile_via_patchright(url)

        # Delegate to fallback strategy (no captcha solving)
        if self.fallback_strategy is not None:
            result = await self.fallback_strategy.fetch(url, selectors)
            return ScrapingResult(
                content=result.content,
                url=result.url,
                strategy=self.name,
                status_code=result.status_code,
                metadata={**result.metadata, "captcha_solved": False},
            )

        return ScrapingResult(
            content="",
            url=url,
            strategy=self.name,
            status_code=0,
            metadata={"captcha_solved": False, "error": "no_fallback_strategy"},
        )
