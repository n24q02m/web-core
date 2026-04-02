"""Tests for StrategyCache."""

from __future__ import annotations

import pytest

from web_core.scraper.cache import StrategyCache, StrategyStats


class TestStrategyStats:
    """Test StrategyStats dataclass."""

    def test_default_values(self):
        stats = StrategyStats()
        assert stats.attempts == 0
        assert stats.successes == 0
        assert stats.total_time_ms == 0.0

    def test_success_rate_zero_attempts(self):
        stats = StrategyStats()
        assert stats.success_rate == 0.0

    def test_success_rate_with_data(self):
        stats = StrategyStats(attempts=10, successes=7)
        assert stats.success_rate == pytest.approx(0.7)

    def test_success_rate_all_success(self):
        stats = StrategyStats(attempts=5, successes=5)
        assert stats.success_rate == pytest.approx(1.0)

    def test_success_rate_all_failure(self):
        stats = StrategyStats(attempts=5, successes=0)
        assert stats.success_rate == pytest.approx(0.0)

    def test_avg_time_ms_zero_attempts(self):
        stats = StrategyStats()
        assert stats.avg_time_ms == 0.0

    def test_avg_time_ms_with_data(self):
        stats = StrategyStats(attempts=4, total_time_ms=1000.0)
        assert stats.avg_time_ms == pytest.approx(250.0)


class TestStrategyCache:
    """Test StrategyCache."""

    def test_default_order(self):
        cache = StrategyCache()
        assert cache.default_order == ["basic_http", "tls_spoof", "api_direct", "headless", "captcha"]

    def test_custom_default_order(self):
        order = ["headless", "basic_http"]
        cache = StrategyCache(default_order=order)
        assert cache.default_order == ["headless", "basic_http"]

    def test_default_order_is_copy(self):
        """Modifying default_order should not affect DEFAULT_ORDER class var."""
        cache = StrategyCache()
        cache.default_order.append("custom")
        assert "custom" not in StrategyCache.DEFAULT_ORDER

    def test_default_min_attempts(self):
        cache = StrategyCache()
        assert cache.min_attempts == 3

    def test_custom_min_attempts(self):
        cache = StrategyCache(min_attempts=5)
        assert cache.min_attempts == 5

    # ------------------------------------------------------------------
    # _extract_domain
    # ------------------------------------------------------------------

    def test_extract_domain_full_url(self):
        assert StrategyCache._extract_domain("https://example.com/page") == "example.com"

    def test_extract_domain_with_port(self):
        assert StrategyCache._extract_domain("https://example.com:8080/page") == "example.com:8080"

    def test_extract_domain_http(self):
        assert StrategyCache._extract_domain("http://test.org") == "test.org"

    def test_extract_domain_no_scheme(self):
        # Without scheme, urlparse puts it all in path
        result = StrategyCache._extract_domain("example.com/page")
        assert result == "example.com"

    def test_extract_domain_subdomain(self):
        assert StrategyCache._extract_domain("https://sub.example.com/path") == "sub.example.com"

    # ------------------------------------------------------------------
    # record + get_stats
    # ------------------------------------------------------------------

    async def test_record_success(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True, time_ms=150.0)

        stats = await cache.get_stats("https://example.com")
        assert "basic_http" in stats
        assert stats["basic_http"].attempts == 1
        assert stats["basic_http"].successes == 1
        assert stats["basic_http"].total_time_ms == 150.0

    async def test_record_failure(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=False, time_ms=50.0)

        stats = await cache.get_stats("https://example.com")
        assert stats["basic_http"].attempts == 1
        assert stats["basic_http"].successes == 0
        assert stats["basic_http"].total_time_ms == 50.0

    async def test_record_multiple(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True, time_ms=100.0)
        await cache.record("https://example.com", "basic_http", success=True, time_ms=200.0)
        await cache.record("https://example.com", "basic_http", success=False, time_ms=300.0)

        stats = await cache.get_stats("https://example.com")
        assert stats["basic_http"].attempts == 3
        assert stats["basic_http"].successes == 2
        assert stats["basic_http"].total_time_ms == 600.0
        assert stats["basic_http"].success_rate == pytest.approx(2 / 3)
        assert stats["basic_http"].avg_time_ms == pytest.approx(200.0)

    async def test_record_different_strategies(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True)
        await cache.record("https://example.com", "tls_spoof", success=False)

        stats = await cache.get_stats("https://example.com")
        assert "basic_http" in stats
        assert "tls_spoof" in stats
        assert stats["basic_http"].successes == 1
        assert stats["tls_spoof"].successes == 0

    async def test_record_different_domains(self):
        cache = StrategyCache()
        await cache.record("https://example.com/page1", "basic_http", success=True)
        await cache.record("https://other.com/page1", "basic_http", success=False)

        stats_ex = await cache.get_stats("https://example.com")
        stats_ot = await cache.get_stats("https://other.com")
        assert stats_ex["basic_http"].successes == 1
        assert stats_ot["basic_http"].successes == 0

    # ------------------------------------------------------------------
    # recommend
    # ------------------------------------------------------------------

    async def test_recommend_no_history(self):
        cache = StrategyCache()
        order = await cache.recommend("https://example.com")
        assert order == ["basic_http", "tls_spoof", "api_direct", "headless", "captcha"]

    async def test_recommend_reorders_after_min_attempts(self):
        cache = StrategyCache(min_attempts=2)

        # tls_spoof: 2 attempts, 100% success
        await cache.record("https://example.com", "tls_spoof", success=True)
        await cache.record("https://example.com", "tls_spoof", success=True)

        # basic_http: 2 attempts, 0% success
        await cache.record("https://example.com", "basic_http", success=False)
        await cache.record("https://example.com", "basic_http", success=False)

        order = await cache.recommend("https://example.com")
        # tls_spoof (100%) should come before basic_http (0%)
        assert order.index("tls_spoof") < order.index("basic_http")

    async def test_recommend_unscored_appended(self):
        """Strategies with fewer than min_attempts should be appended after scored ones."""
        cache = StrategyCache(min_attempts=3)

        # Only basic_http has enough attempts
        for _ in range(3):
            await cache.record("https://example.com", "basic_http", success=True)

        # tls_spoof has 1 attempt (below min_attempts=3)
        await cache.record("https://example.com", "tls_spoof", success=True)

        order = await cache.recommend("https://example.com")
        # basic_http scored first, then unscored in default order
        assert order[0] == "basic_http"
        # tls_spoof should be in unscored section
        assert "tls_spoof" in order

    async def test_recommend_preserves_default_for_unknown_domain(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True)

        order = await cache.recommend("https://unknown.com")
        assert order == cache.default_order

    # ------------------------------------------------------------------
    # get_stats
    # ------------------------------------------------------------------

    async def test_get_stats_empty(self):
        cache = StrategyCache()
        stats = await cache.get_stats("https://example.com")
        assert stats == {}

    async def test_get_stats_returns_dict_copy(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True)

        stats = await cache.get_stats("https://example.com")
        assert isinstance(stats, dict)
        assert "basic_http" in stats

    async def test_get_stats_returns_independent_objects(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True)

        stats = await cache.get_stats("https://example.com")
        stats["basic_http"].attempts = 999

        new_stats = await cache.get_stats("https://example.com")
        assert new_stats["basic_http"].attempts == 1

    # ------------------------------------------------------------------
    # clear
    # ------------------------------------------------------------------

    async def test_clear_all(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True)
        await cache.record("https://other.com", "tls_spoof", success=True)

        await cache.clear()

        assert await cache.get_stats("https://example.com") == {}
        assert await cache.get_stats("https://other.com") == {}

    async def test_clear_specific_domain(self):
        cache = StrategyCache()
        await cache.record("https://example.com", "basic_http", success=True)
        await cache.record("https://other.com", "tls_spoof", success=True)

        await cache.clear("https://example.com")

        assert await cache.get_stats("https://example.com") == {}
        stats_other = await cache.get_stats("https://other.com")
        assert "tls_spoof" in stats_other

    async def test_clear_nonexistent_domain(self):
        """Clearing a domain with no stats should not raise."""
        cache = StrategyCache()
        await cache.clear("https://nonexistent.com")  # no error
