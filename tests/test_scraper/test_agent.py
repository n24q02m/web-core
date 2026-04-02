"""Tests for ScrapingAgent."""

from __future__ import annotations

import pytest

from web_core.scraper.agent import ScrapingAgent
from web_core.scraper.base import BaseStrategy, ScrapingResult
from web_core.scraper.cache import StrategyCache
from web_core.scraper.state import ScrapingError

# ---------------------------------------------------------------------------
# Mock strategies
# ---------------------------------------------------------------------------


class MockStrategy(BaseStrategy):
    """Configurable mock strategy for testing."""

    def __init__(
        self,
        name: str = "mock",
        should_fail: bool = False,
        content: str = "<html>mock content that is long enough for validation</html>" + "x" * 100,
        status_code: int = 200,
    ):
        self.name = name
        self._should_fail = should_fail
        self._content = content
        self._status_code = status_code
        self.call_count = 0

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        self.call_count += 1
        if self._should_fail:
            raise RuntimeError(f"Mock failure from {self.name}")
        return ScrapingResult(
            content=self._content,
            url=url,
            strategy=self.name,
            status_code=self._status_code,
        )


class TestScrapingAgent:
    """Test ScrapingAgent LangGraph workflow."""

    # ------------------------------------------------------------------
    # scrape success
    # ------------------------------------------------------------------

    async def test_scrape_success_first_strategy(self):
        """Agent should succeed with the first strategy when it works."""
        strategy = MockStrategy(name="fast")
        agent = ScrapingAgent(strategies={"fast": strategy})

        content = await agent.scrape("https://example.com")

        assert "mock content" in content
        assert strategy.call_count == 1

    async def test_scrape_returns_content(self):
        """scrape should return the page content on success."""
        strategy = MockStrategy(name="basic", content="A" * 200)
        agent = ScrapingAgent(strategies={"basic": strategy}, min_content_length=50)

        result = await agent.scrape("https://example.com")

        assert result == "A" * 200

    async def test_scrape_with_selectors(self):
        """scrape should pass selectors through to the strategy."""
        strategy = MockStrategy(name="sel")
        agent = ScrapingAgent(strategies={"sel": strategy})

        await agent.scrape("https://example.com", selectors={"key": "value"})

        assert strategy.call_count == 1

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    async def test_scrape_escalates_on_failure(self):
        """Agent should try the next strategy when the first fails."""
        failing = MockStrategy(name="failing", should_fail=True)
        working = MockStrategy(name="working")
        agent = ScrapingAgent(strategies={"failing": failing, "working": working})

        content = await agent.scrape("https://example.com")

        assert "mock content" in content
        assert failing.call_count == 1
        assert working.call_count == 1

    async def test_scrape_escalates_on_short_content(self):
        """Agent should escalate when content is shorter than min_content_length."""
        short = MockStrategy(name="short", content="hi")
        long = MockStrategy(name="long", content="x" * 200)
        agent = ScrapingAgent(
            strategies={"short": short, "long": long},
            min_content_length=100,
        )

        content = await agent.scrape("https://example.com")

        assert content == "x" * 200
        assert short.call_count == 1
        assert long.call_count == 1

    async def test_scrape_escalates_on_error_status(self):
        """Agent should escalate when status code is not 2xx/3xx."""
        bad = MockStrategy(name="bad", content="x" * 200, status_code=403)
        good = MockStrategy(name="good", content="y" * 200)
        agent = ScrapingAgent(
            strategies={"bad": bad, "good": good},
            min_content_length=50,
        )

        content = await agent.scrape("https://example.com")

        assert content == "y" * 200

    # ------------------------------------------------------------------
    # All fail -> ScrapingError
    # ------------------------------------------------------------------

    async def test_scrape_raises_scraping_error_all_fail(self):
        """Agent should raise ScrapingError when all strategies fail."""
        s1 = MockStrategy(name="s1", should_fail=True)
        s2 = MockStrategy(name="s2", should_fail=True)
        agent = ScrapingAgent(strategies={"s1": s1, "s2": s2})

        with pytest.raises(ScrapingError) as exc_info:
            await agent.scrape("https://example.com")

        assert exc_info.value.url == "https://example.com"
        assert "s1" in exc_info.value.strategies_tried
        assert "s2" in exc_info.value.strategies_tried

    async def test_scrape_error_includes_last_error(self):
        """ScrapingError should include the last error message."""
        s1 = MockStrategy(name="s1", should_fail=True)
        agent = ScrapingAgent(strategies={"s1": s1})

        with pytest.raises(ScrapingError) as exc_info:
            await agent.scrape("https://example.com")

        assert "Mock failure" in exc_info.value.final_error

    async def test_scrape_no_strategies_raises_error(self):
        """Agent with no strategies should raise ScrapingError."""
        agent = ScrapingAgent(strategies={})

        with pytest.raises(ScrapingError) as exc_info:
            await agent.scrape("https://example.com")

        assert "No strategies available" in exc_info.value.final_error

    # ------------------------------------------------------------------
    # max_retries
    # ------------------------------------------------------------------

    async def test_max_retries_limits_attempts(self):
        """Agent should not try more strategies than max_retries."""
        strategies = {f"s{i}": MockStrategy(name=f"s{i}", should_fail=True) for i in range(10)}
        agent = ScrapingAgent(strategies=strategies, max_retries=3)

        with pytest.raises(ScrapingError) as exc_info:
            await agent.scrape("https://example.com")

        assert len(exc_info.value.strategies_tried) <= 3

    # ------------------------------------------------------------------
    # Cache interaction
    # ------------------------------------------------------------------

    async def test_update_cache_records_results(self):
        """Agent should record outcomes to the strategy cache."""
        cache = StrategyCache()
        strategy = MockStrategy(name="basic_http")
        agent = ScrapingAgent(strategies={"basic_http": strategy}, strategy_cache=cache)

        await agent.scrape("https://example.com")

        stats = await cache.get_stats("https://example.com")
        assert "basic_http" in stats
        assert stats["basic_http"].attempts == 1
        assert stats["basic_http"].successes == 1

    async def test_cache_records_failure(self):
        """Failed strategies should be recorded as failures in the cache."""
        cache = StrategyCache()
        failing = MockStrategy(name="failing", should_fail=True)
        working = MockStrategy(name="working")
        agent = ScrapingAgent(
            strategies={"failing": failing, "working": working},
            strategy_cache=cache,
        )

        await agent.scrape("https://example.com")

        stats = await cache.get_stats("https://example.com")
        assert stats["failing"].attempts == 1
        assert stats["failing"].successes == 0
        assert stats["working"].attempts == 1
        assert stats["working"].successes == 1

    async def test_cache_all_fail_records_all_as_failure(self):
        """When all strategies fail, all should be recorded as failures."""
        cache = StrategyCache()
        s1 = MockStrategy(name="s1", should_fail=True)
        s2 = MockStrategy(name="s2", should_fail=True)
        agent = ScrapingAgent(
            strategies={"s1": s1, "s2": s2},
            strategy_cache=cache,
        )

        with pytest.raises(ScrapingError):
            await agent.scrape("https://example.com")

        stats = await cache.get_stats("https://example.com")
        for name in ["s1", "s2"]:
            assert stats[name].successes == 0

    async def test_cache_recommendation_affects_order(self):
        """The cache recommendation should influence strategy order."""
        cache = StrategyCache(min_attempts=1)
        # Record that tls_spoof works well for this domain
        await cache.record("https://example.com", "tls_spoof", success=True)

        tls = MockStrategy(name="tls_spoof")
        basic = MockStrategy(name="basic_http", should_fail=True)
        agent = ScrapingAgent(
            strategies={"basic_http": basic, "tls_spoof": tls},
            strategy_cache=cache,
        )

        await agent.scrape("https://example.com")

        # tls_spoof should have been tried (and succeeded)
        assert tls.call_count == 1

    # ------------------------------------------------------------------
    # Validate content
    # ------------------------------------------------------------------

    async def test_min_content_length_default(self):
        """Default min_content_length should be 100."""
        agent = ScrapingAgent()
        assert agent.min_content_length == 100

    async def test_custom_min_content_length(self):
        agent = ScrapingAgent(min_content_length=50)
        assert agent.min_content_length == 50

    async def test_validate_accepts_3xx_status(self):
        """Status codes in 200-399 range should be considered valid."""
        strategy = MockStrategy(name="redirect", content="x" * 200, status_code=301)
        agent = ScrapingAgent(strategies={"redirect": strategy}, min_content_length=50)

        content = await agent.scrape("https://example.com")

        assert content == "x" * 200

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    async def test_scrape_strategy_disappears_at_runtime(self):
        """Test handling of a strategy that disappears from the dict during execution."""

        class SaboteurStrategy(MockStrategy):
            def __init__(self, agent, target_name):
                super().__init__(name="saboteur", content="too short")
                self.agent = agent
                self.target_name = target_name

            async def fetch(self, url, selectors=None):
                if self.target_name in self.agent.strategies:
                    del self.agent.strategies[self.target_name]
                return await super().fetch(url, selectors)

        agent = ScrapingAgent(min_content_length=100)
        s1 = SaboteurStrategy(agent, "s2")
        s2 = MockStrategy(name="s2")
        agent.strategies = {"s1": s1, "s2": s2}

        with pytest.raises(ScrapingError) as exc_info:
            await agent.scrape("https://example.com")

        assert "Strategy 's2' not found" in exc_info.value.final_error
        assert "s1" in exc_info.value.strategies_tried
        assert "s2" in exc_info.value.strategies_tried

    async def test_scrape_handles_missing_success_in_result(self, monkeypatch):
        """scrape should handle a result missing the 'success' key gracefully."""
        agent = ScrapingAgent()

        # Mock ainvoke to return a dict without 'success'
        async def mock_ainvoke(state):
            return {"errors": ["unexpected failure"], "strategies_tried": ["mock"]}

        monkeypatch.setattr(agent._graph, "ainvoke", mock_ainvoke)

        with pytest.raises(ScrapingError) as exc_info:
            await agent.scrape("https://example.com")

        assert "unexpected failure" in exc_info.value.final_error
