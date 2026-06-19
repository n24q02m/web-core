"""Cloudflare Browser Rendering REST client (``/content`` endpoint).

Offloads JS rendering to Cloudflare's managed browser fleet: POST a URL, get
back fully-rendered HTML. Used as a cloud headless backend so a slim container
(e.g. on CF Workers/Containers) need not bundle chromium. The free tier
(3 concurrent / 1 per 10s) covers low single-page volume.

Docs: https://developers.cloudflare.com/browser-rendering/rest-api/content-endpoint/
"""

from __future__ import annotations

from typing import Any

from web_core.http.client import safe_httpx_client

_CF_CONTENT_API = "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/content"


class CFBrowserRenderingError(RuntimeError):
    """Cloudflare Browser Rendering returned an error or an unusable response."""


class CFBrowserRenderingClient:
    """Render a URL to HTML via Cloudflare Browser Rendering ``/content``.

    Credentials: a Cloudflare ``account_id`` and an API token with the
    "Browser Rendering" permission (``CF_ACCOUNT_ID`` / ``CF_BROWSER_RENDERING_TOKEN``
    in the consumer's config). The outbound request targets the public
    ``api.cloudflare.com`` host; the target page URL is rendered on Cloudflare's
    side (callers should still SSRF-validate the target before calling).
    """

    name = "cf-browser-rendering"

    def __init__(
        self,
        account_id: str,
        api_token: str,
        *,
        timeout: float = 60.0,
        http_client: Any = None,
    ):
        if not account_id or not api_token:
            raise ValueError("CFBrowserRenderingClient requires both account_id and api_token")
        self._account_id = account_id
        self._api_token = api_token
        self._timeout = timeout
        self._http_client = http_client

    async def render(self, url: str, *, wait_until: str = "networkidle0", timeout: float | None = None) -> str:
        """Return the fully-rendered HTML of *url*.

        ``wait_until`` is forwarded as ``gotoOptions.waitUntil`` — ``networkidle0``
        suits SPAs (wait until the network is quiet so client-side content has
        rendered). Raises :class:`CFBrowserRenderingError` on an API-level
        failure and propagates ``httpx`` errors (5xx/timeout) so the agent's
        escalation chain can fall back to the next backend.
        """
        endpoint = _CF_CONTENT_API.format(account_id=self._account_id)
        payload = {"url": url, "gotoOptions": {"waitUntil": wait_until}}
        headers = {"Authorization": f"Bearer {self._api_token}", "Content-Type": "application/json"}

        if self._http_client is not None:
            response = await self._http_client.post(endpoint, json=payload, headers=headers)
        else:
            async with safe_httpx_client(timeout=timeout or self._timeout) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        if not data.get("success", False):
            raise CFBrowserRenderingError(f"Cloudflare Browser Rendering failed: {data.get('errors')}")
        result = data.get("result")
        if not isinstance(result, str) or not result:
            raise CFBrowserRenderingError("Cloudflare Browser Rendering returned no HTML content")
        return result
