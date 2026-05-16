"""TLS fingerprint spoofing strategy using curl-cffi."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from web_core.http.client import is_safe_url
from web_core.scraper.base import BaseStrategy, ScrapingResult


class TLSSpoofStrategy(BaseStrategy):
    """Bypass TLS fingerprinting with curl-cffi browser impersonation."""

    name: str = "tls_spoof"
    MAX_REDIRECTS: int = 10

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
        current_url = url
        if not is_safe_url(current_url):
            raise ValueError(f"SSRF blocked: {current_url}")

        cookies: dict[str, str] = {}
        if selectors and isinstance(selectors.get("cookies"), dict):
            cookies = selectors["cookies"]

        req_cookies = cookies or None

        redirect_count = 0
        response = None

        if self._session_factory is not None:
            session = self._session_factory()

            while redirect_count <= self.MAX_REDIRECTS:
                response = await session.get(
                    current_url,
                    impersonate=self.impersonate,
                    timeout=self.timeout,
                    cookies=req_cookies,
                    allow_redirects=False,
                )

                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        break
                    current_url = urljoin(current_url, location)
                    if not is_safe_url(current_url):
                        raise ValueError(f"SSRF blocked on redirect: {current_url}")
                    redirect_count += 1
                else:
                    break
        else:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                while redirect_count <= self.MAX_REDIRECTS:
                    response = await session.get(
                        current_url,
                        impersonate=self.impersonate,
                        timeout=self.timeout,
                        cookies=req_cookies,
                        allow_redirects=False,
                    )

                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            break
                        current_url = urljoin(current_url, location)
                        if not is_safe_url(current_url):
                            raise ValueError(f"SSRF blocked on redirect: {current_url}")
                        redirect_count += 1
                    else:
                        break

        if redirect_count > self.MAX_REDIRECTS:
            raise Exception("Too many redirects")

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
