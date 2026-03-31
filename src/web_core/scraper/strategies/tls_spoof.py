"""TLS fingerprint spoofing strategy using curl-cffi."""

from __future__ import annotations

from typing import Any

from web_core.scraper.base import BaseStrategy, ScrapingResult


class TLSSpoofStrategy(BaseStrategy):
    """Bypass TLS fingerprinting with curl-cffi browser impersonation."""

    name: str = "tls_spoof"

    def __init__(
        self,
        impersonate: str = "chrome131",
        timeout: float = 30.0,
        session_factory: Any = None,
    ):
        self.impersonate = impersonate
        self.timeout = timeout
        self._session_factory = session_factory

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Fetch *url* using a TLS-spoofed session via curl-cffi."""
        if self._session_factory is not None:
            session = self._session_factory()
            response = await session.get(url, impersonate=self.impersonate, timeout=self.timeout)
        else:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                response = await session.get(url, impersonate=self.impersonate, timeout=self.timeout)

        return ScrapingResult(
            content=response.text,
            url=str(response.url),
            strategy=self.name,
            status_code=response.status_code,
            metadata={
                "impersonate": self.impersonate,
                "content_length": len(response.text),
            },
        )
