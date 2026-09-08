"""Patchright browser provider with optional Chrome persistent contexts."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)
_async_playwright_func: Callable | None = None


async def _get_async_playwright() -> Callable:
    """Import async_playwright in a thread and cache it."""
    global _async_playwright_func
    if _async_playwright_func is None:

        def _import():
            from patchright.async_api import async_playwright

            return async_playwright

        _async_playwright_func = await asyncio.to_thread(_import)
    return _async_playwright_func


class PatchrightProvider:
    """Patchright provider; persistent Chrome context is opt-in."""

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._playwright = None
        self._browser = None

    @property
    def name(self) -> str:
        return "patchright"

    @property
    def supports_arm64(self) -> bool:
        return True

    async def launch(self, config: dict[str, Any] | None = None) -> Any:
        """Launch a browser or an app-owned persistent Chrome context."""
        launch_config = dict(config or {})
        user_data_dir = launch_config.pop("user_data_dir", None)
        channel = launch_config.pop("channel", None)
        no_viewport = launch_config.pop("no_viewport", None)
        if any(value is not None for value in (channel, no_viewport)) and user_data_dir is None:
            raise ValueError("user_data_dir is required for persistent Patchright contexts")
        async_playwright = await _get_async_playwright()
        self._playwright = await async_playwright().start()
        launch_config.setdefault("headless", self._headless)
        if user_data_dir is not None:
            context_config = {"user_data_dir": user_data_dir, **launch_config}
            if channel is not None:
                context_config["channel"] = channel
            if no_viewport is not None:
                context_config["no_viewport"] = no_viewport
            self._browser = await self._playwright.chromium.launch_persistent_context(**context_config)
        else:
            self._browser = await self._playwright.chromium.launch(**launch_config)
        return self._browser

    async def close(self) -> None:
        """Close browser/context and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
