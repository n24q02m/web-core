"""TLS fingerprint spoofing strategy using curl-cffi."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

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

        cookies: dict[str, str] = {}
        if selectors and isinstance(selectors.get("cookies"), dict):
            cookies = selectors["cookies"]

        req_cookies = cookies or None
        current_url = url
        max_redirects = 5
        redirects = 0

        async def _do_fetch(session: Any) -> Any:
            nonlocal current_url, redirects
            while redirects <= max_redirects:
                resp = await session.get(
                    current_url,
                    impersonate=self.impersonate,
                    timeout=self.timeout,
                    cookies=req_cookies,
                    allow_redirects=False,
                )
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        return resp

                    next_url = urljoin(current_url, location)
                    if not is_safe_url(next_url):
                        raise ValueError(f"SSRF blocked: {next_url}")

                    current_url = next_url
                    redirects += 1
                else:
                    return resp
            raise ValueError(f"Too many redirects: {url}")

        if self._session_factory is not None:
            session = self._session_factory()
            response = await _do_fetch(session)
        else:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                response = await _do_fetch(session)

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
