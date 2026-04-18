"""Patchright browser provider (current baseline)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Cache for the lazy-loaded async_playwright function
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
    """Patchright-based browser provider. Drop-in Playwright with CDP leak patches."""

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
        """Launch Patchright browser."""
        async_playwright = await _get_async_playwright()

        self._playwright = await async_playwright().start()
        launch_args: dict[str, Any] = {
            "headless": self._headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if config:
            launch_args.update(config)
        self._browser = await self._playwright.chromium.launch(**launch_args)
        return self._browser

    async def close(self) -> None:
        """Close browser and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
