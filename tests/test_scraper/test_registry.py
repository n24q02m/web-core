"""Tests for StrategyRegistry."""

from __future__ import annotations

from web_core.scraper.base import BaseStrategy, ScrapingResult
from web_core.scraper.registry import StrategyRegistry


class StubStrategy(BaseStrategy):
    """Minimal strategy for testing registry operations."""

    name: str = "stub"

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        return ScrapingResult(content="stub", url=url, strategy=self.name, status_code=200)


class AnotherStubStrategy(BaseStrategy):
    """Second stub strategy with a different name."""

    name: str = "another_stub"

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        return ScrapingResult(content="another", url=url, strategy=self.name, status_code=200)


class TestStrategyRegistry:
    """Test StrategyRegistry."""

    def test_register_and_get(self):
        reg = StrategyRegistry()
        strategy = StubStrategy()
        reg.register(strategy)
        assert reg.get("stub") is strategy

    def test_get_unknown_returns_none(self):
        reg = StrategyRegistry()
        assert reg.get("nonexistent") is None

    def test_register_overwrites(self):
        """Registering a strategy with the same name should overwrite the old one."""
        reg = StrategyRegistry()
        first = StubStrategy()
        second = StubStrategy()
        reg.register(first)
        reg.register(second)
        assert reg.get("stub") is second

    def test_list_strategies_empty(self):
        reg = StrategyRegistry()
        assert reg.list_strategies() == []

    def test_list_strategies_single(self):
        reg = StrategyRegistry()
        reg.register(StubStrategy())
        assert reg.list_strategies() == ["stub"]

    def test_list_strategies_multiple(self):
        reg = StrategyRegistry()
        reg.register(StubStrategy())
        reg.register(AnotherStubStrategy())
        names = reg.list_strategies()
        assert "stub" in names
        assert "another_stub" in names
        assert len(names) == 2

    # ------------------------------------------------------------------
    # create_default
    # ------------------------------------------------------------------

    def test_create_default_includes_core_strategies(self):
        """create_default should include basic_http, tls_spoof, api_direct."""
        reg = StrategyRegistry.create_default()
        names = reg.list_strategies()
        assert "basic_http" in names
        assert "tls_spoof" in names
        assert "api_direct" in names

    def test_create_default_includes_headless(self):
        """create_default should include headless when crawl4ai is available."""
        reg = StrategyRegistry.create_default()
        assert "headless" in reg.list_strategies()

    def test_create_default_no_headless_when_import_fails(self):
        """create_default should gracefully skip headless when crawl4ai is unavailable."""
        # The import happens inside create_default, so we patch at the module level
        # by making the strategies.headless module raise ImportError
        import sys

        # Temporarily remove cached module and block the import
        saved = sys.modules.pop("web_core.scraper.strategies.headless", None)
        sys.modules["web_core.scraper.strategies.headless"] = None  # type: ignore[assignment]
        try:
            reg = StrategyRegistry.create_default()
            assert "headless" not in reg.list_strategies()
        finally:
            del sys.modules["web_core.scraper.strategies.headless"]
            if saved is not None:
                sys.modules["web_core.scraper.strategies.headless"] = saved

    def test_create_default_no_captcha_without_key(self):
        """create_default without capsolver_api_key should not include captcha."""
        reg = StrategyRegistry.create_default()
        assert "captcha" not in reg.list_strategies()

    def test_create_default_includes_captcha_with_key(self):
        """create_default with capsolver_api_key should include captcha."""
        reg = StrategyRegistry.create_default(capsolver_api_key="test-key")
        assert "captcha" in reg.list_strategies()

    def test_create_default_returns_registry_instance(self):
        reg = StrategyRegistry.create_default()
        assert isinstance(reg, StrategyRegistry)

    def test_create_default_strategies_are_correct_types(self):
        """All strategies from create_default should be BaseStrategy subclasses."""
        reg = StrategyRegistry.create_default()
        for name in reg.list_strategies():
            strategy = reg.get(name)
            assert isinstance(strategy, BaseStrategy)
