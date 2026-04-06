"""Captcha strategy: CapSolver API integration (ReCaptcha + Turnstile)."""

from __future__ import annotations

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

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Solve captcha if needed, then delegate to fallback strategy.

        Flow:
        1. If selectors has explicit site_key + captcha_type: solve directly
        2. Run fallback strategy to get initial page
        3. If fallback returns CF Turnstile HTML: auto-detect and solve
        4. Return result with captcha metadata
        """
        captcha_token = ""
        captcha_type = (selectors or {}).get("captcha_type", RECAPTCHA_V2_PROXYLESS)

        # Explicit captcha solving (user-provided site_key)
        if selectors and "site_key" in selectors:
            captcha_token = await self.solve_captcha(
                site_key=selectors["site_key"],
                page_url=url,
                captcha_type=captcha_type,
            )

        # Delegate to fallback strategy
        if self.fallback_strategy is not None:
            result = await self.fallback_strategy.fetch(url, selectors)

            # Auto-detect Turnstile if no explicit captcha and fallback got challenge HTML
            if not captcha_token and self.capsolver_api_key:
                captcha_token = await self._try_solve_turnstile(url, result.content)

            return ScrapingResult(
                content=result.content,
                url=result.url,
                strategy=self.name,
                status_code=result.status_code,
                metadata={
                    **result.metadata,
                    "captcha_solved": bool(captcha_token),
                    "captcha_type": captcha_type if captcha_token else None,
                },
            )

        return ScrapingResult(
            content="",
            url=url,
            strategy=self.name,
            status_code=0,
            metadata={
                "captcha_solved": bool(captcha_token),
                "error": "no_fallback_strategy",
            },
        )
