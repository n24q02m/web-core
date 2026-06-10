"""TLS fingerprint spoofing strategy using curl-cffi."""

from __future__ import annotations

from typing import Any

from web_core.http.client import is_safe_url
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
        """Fetch *url* using a TLS-spoofed session via curl-cffi.

        Supports optional cookies via selectors["cookies"] (dict[str, str]).
        """
        if not is_safe_url(url):
            raise ValueError(f"SSRF blocked: {url}")

        cookies = self._extract_cookies(selectors)

        if self._session_factory is not None:
            session = self._session_factory()
            response = await self._perform_request(session, url, cookies)
        else:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                response = await self._perform_request(session, url, cookies)

        return self._build_result(response)

    def _extract_cookies(self, selectors: dict[str, Any] | None) -> dict[str, str] | None:
        """Extract cookies from selectors dictionary."""
        if selectors and isinstance(selectors.get("cookies"), dict):
            return selectors["cookies"]
        return None

    async def _perform_request(self, session: Any, url: str, cookies: dict[str, str] | None) -> Any:
        """Perform the HTTP request(s) with manual redirect handling."""
        from urllib.parse import urljoin

        max_redirects = 10
        current_url = url
        current_cookies = cookies

        for _ in range(max_redirects):
            if not is_safe_url(current_url):
                raise ValueError(f"SSRF blocked: {current_url}")

            resp = await session.get(
                current_url,
                impersonate=self.impersonate,
                timeout=self.timeout,
                cookies=current_cookies,
                allow_redirects=False,
            )
            current_cookies = None  # Only send initial cookies on the first request

            if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                current_url = urljoin(current_url, resp.headers["Location"])
                continue

            return resp

        raise ValueError(f"Too many redirects: {url}")

    def _build_result(self, response: Any) -> ScrapingResult:
        """Build ScrapingResult from the response."""
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
