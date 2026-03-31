"""Strategy registry and factory."""

from __future__ import annotations

from typing import Any

from web_core.scraper.base import BaseStrategy


class StrategyRegistry:
    """Registry of named scraping strategies with a default-factory classmethod."""

    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}

    def register(self, strategy: BaseStrategy) -> None:
        """Register *strategy* under its ``name``."""
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> BaseStrategy | None:
        """Return the strategy registered as *name*, or ``None``."""
        return self._strategies.get(name)

    def list_strategies(self) -> list[str]:
        """Return names of all registered strategies."""
        return list(self._strategies.keys())

    @classmethod
    def create_default(cls, capsolver_api_key: str = "", **kwargs: Any) -> StrategyRegistry:
        """Build a registry pre-loaded with all available strategies.

        Headless is loaded only if ``crawl4ai`` is importable.
        Captcha is loaded only when *capsolver_api_key* is provided.
        """
        from web_core.scraper.strategies.api_direct import APIDirectStrategy
        from web_core.scraper.strategies.basic_http import BasicHTTPStrategy
        from web_core.scraper.strategies.tls_spoof import TLSSpoofStrategy

        reg = cls()
        reg.register(BasicHTTPStrategy())
        reg.register(TLSSpoofStrategy())
        reg.register(APIDirectStrategy())

        try:
            from web_core.scraper.strategies.headless import HeadlessStrategy

            reg.register(HeadlessStrategy())
        except ImportError:
            pass

        if capsolver_api_key:
            from web_core.scraper.strategies.captcha import CaptchaStrategy

            reg.register(CaptchaStrategy(capsolver_api_key=capsolver_api_key))

        return reg
