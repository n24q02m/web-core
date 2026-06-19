"""Self-host browserless ``/content`` REST client (generic VM/self-host).

POST a URL to a self-hosted browserless instance, get back fully-rendered HTML.
The client knows ONLY a base URL (any reverse-proxied browserless — e.g. behind
Caddy + a tunnel, the same exposure pattern as the self-host SearXNG) and an
optional token; it is deliberately NOT tied to any infra vendor. Used as the
self-host headless leg: a dedicated egress IP hedges a cloud renderer's
shared-IP bot-flagging on hard targets.

Docs: https://docs.browserless.io/rest-apis/content
"""

from __future__ import annotations

from typing import Any

from web_core.http.client import safe_httpx_client


class BrowserlessClient:
    """Render a URL to HTML via a self-host browserless ``/content`` endpoint.

    ``base_url`` is the public reverse-proxied browserless root (basic-auth may
    be embedded as userinfo, ``https://user:pass@host`` — ``httpx`` extracts it,
    identical to the self-host SearXNG setup). ``token`` is browserless's native
    ``?token=`` auth, used when the instance is token-gated instead.
    """

    name = "browserless"

    def __init__(
        self,
        base_url: str,
        *,
        token: str = "",
        timeout: float = 60.0,
        http_client: Any = None,
    ):
        if not base_url:
            raise ValueError("BrowserlessClient requires a base_url")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._http_client = http_client

    async def render(self, url: str, *, wait_until: str = "networkidle0", timeout: float | None = None) -> str:
        """Return the fully-rendered HTML of *url*.

        browserless ``/content`` responds with ``text/html`` (the raw rendered
        markup, not a JSON wrapper). Propagates ``httpx`` errors (5xx/timeout)
        so the agent's escalation chain can fall back to the next backend.
        """
        endpoint = f"{self._base_url}/content"
        params = {"token": self._token} if self._token else None
        payload = {"url": url, "gotoOptions": {"waitUntil": wait_until}}

        if self._http_client is not None:
            response = await self._http_client.post(endpoint, json=payload, params=params)
        else:
            async with safe_httpx_client(timeout=timeout or self._timeout) as client:
                response = await client.post(endpoint, json=payload, params=params)
        response.raise_for_status()
        return response.text
