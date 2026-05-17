"""TLS fingerprint spoofing strategy using curl-cffi."""

from __future__ import annotations

import urllib.parse
from typing import Any

from web_core.http.client import is_safe_url
from web_core.scraper.base import BaseStrategy, ScrapingResult

_MAX_REDIRECTS = 10


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

        async def _fetch_with_session(sess: Any) -> ScrapingResult:
            current_url = url
            for _ in range(_MAX_REDIRECTS):
                if not is_safe_url(current_url):
                    raise ValueError(f"SSRF blocked: {current_url}")

                resp = await sess.get(
                    current_url,
                    impersonate=self.impersonate,
                    timeout=self.timeout,
                    cookies=req_cookies,
                    allow_redirects=False,
                )

                if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                    next_url = urllib.parse.urljoin(current_url, resp.headers["Location"])
                    current_url = next_url
                    continue

                return ScrapingResult(
                    content=resp.text,
                    url=str(resp.url),
                    strategy=self.name,
                    status_code=resp.status_code,
                    metadata={
                        "impersonate": self.impersonate,
                        "content_length": len(resp.text),
                    },
                )
            raise ValueError(f"Too many redirects: {url}")

        if self._session_factory is not None:
            session = self._session_factory()
            return await _fetch_with_session(session)
        else:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                return await _fetch_with_session(session)
