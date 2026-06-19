"""Remote headless rendering strategy.

Adapts a remote render client (Cloudflare Browser Rendering, self-host
browserless) to the scraper ``BaseStrategy`` so its rendered HTML enters the
agent's escalation chain like any other strategy. This is the cloud/remote
headless leg used in place of the in-process chromium (``HeadlessStrategy``) —
e.g. on a slim container that offloads rendering instead of bundling ~1GB of
chromium. Runtime fallback between backends is provided for free by the agent's
existing escalate-on-validation-failure machinery (a 5xx/timeout raises here,
the agent advances to the next strategy).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from web_core.http.client import is_safe_url
from web_core.scraper.base import BaseStrategy, ScrapingResult


@runtime_checkable
class RenderClient(Protocol):
    """A remote service that renders a URL to fully-loaded HTML."""

    @property
    def name(self) -> str: ...

    async def render(self, url: str, *, wait_until: str = "networkidle0", timeout: float | None = None) -> str: ...


class RemoteRenderStrategy(BaseStrategy):
    """Render JS-heavy pages via a remote :class:`RenderClient` (CF / browserless)."""

    def __init__(self, client: RenderClient, *, name: str | None = None, wait_until: str = "networkidle0"):
        self._client = client
        self.name = name or client.name
        self._wait_until = wait_until

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        if not is_safe_url(url):
            raise ValueError(f"SSRF blocked: {url}")
        html = await self._client.render(url, wait_until=self._wait_until)
        return ScrapingResult(
            content=html,
            url=url,
            strategy=self.name,
            status_code=200,
            metadata={"rendered": True, "backend": self.name},
        )
