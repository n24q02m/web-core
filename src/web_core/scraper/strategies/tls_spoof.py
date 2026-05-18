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

        cookies: dict[str, str] = {}
        if selectors and isinstance(selectors.get("cookies"), dict):
            cookies = selectors["cookies"]

        from urllib.parse import urljoin

        req_cookies = cookies or None

        async def _run_request(session: Any) -> Any:
            current_url = url
            send_cookies = req_cookies
            for _ in range(10):  # Max 10 redirects
                response = await session.get(
                    current_url,
                    impersonate=self.impersonate,
                    timeout=self.timeout,
                    cookies=send_cookies,
                    allow_redirects=False,
                )
                if response.status_code in (301, 302, 303, 307, 308) and "Location" in response.headers:
                    next_url = urljoin(current_url, response.headers["Location"])
                    if not is_safe_url(next_url):
                        raise ValueError(f"SSRF blocked: {next_url}")
                    current_url = next_url
                    send_cookies = None  # Subsequent requests use session cookies
                else:
                    return response
            raise RuntimeError("Too many redirects")

        if self._session_factory is not None:
            session = self._session_factory()
            response = await _run_request(session)
        else:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                response = await _run_request(session)

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
