"""Captcha strategy: CapSolver API integration."""

from __future__ import annotations

from typing import Any

from web_core.http.client import safe_httpx_client
from web_core.scraper.base import BaseStrategy, ScrapingResult


class CaptchaStrategy(BaseStrategy):
    """Solve CAPTCHAs via CapSolver before fetching protected pages."""

    name: str = "captcha"
    CAPSOLVER_URL: str = "https://api.capsolver.com/createTask"

    def __init__(
        self,
        capsolver_api_key: str = "",
        fallback_strategy: BaseStrategy | None = None,
        http_client: Any = None,
        **kwargs: Any,
    ):
        self.capsolver_api_key = capsolver_api_key
        self.fallback_strategy = fallback_strategy
        self._http_client = http_client
        # Store extra kwargs as attributes for flexibility
        for k, v in kwargs.items():
            setattr(self, k, v)

    async def solve_captcha(
        self,
        site_key: str,
        page_url: str,
        captcha_type: str = "ReCaptchaV2TaskProxyLess",
    ) -> str:
        """Submit a captcha task to CapSolver and return the solution token."""
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
        return data.get("solution", {}).get("gRecaptchaResponse", "")

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Optionally solve a captcha, then delegate to fallback strategy."""
        captcha_token = ""
        if selectors and "site_key" in selectors:
            captcha_token = await self.solve_captcha(
                site_key=selectors["site_key"],
                page_url=url,
            )

        if self.fallback_strategy is not None:
            result = await self.fallback_strategy.fetch(url, selectors)
            return ScrapingResult(
                content=result.content,
                url=result.url,
                strategy=self.name,
                status_code=result.status_code,
                metadata={**result.metadata, "captcha_solved": bool(captcha_token)},
            )
        return ScrapingResult(
            content="",
            url=url,
            strategy=self.name,
            status_code=0,
            metadata={"captcha_solved": bool(captcha_token), "error": "no_fallback_strategy"},
        )
