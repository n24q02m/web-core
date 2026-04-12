"""Tests for robots.txt compliance via RobotsCache."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from web_core.scraper.robots import RobotsCache, RobotsDisallowedError

ROBOTS_DISALLOW_ALL = """\
User-agent: *
Disallow: /
"""

ROBOTS_ALLOW_ROOT_ONLY = """\
User-agent: *
Disallow: /private/
Disallow: /admin/
Allow: /
"""

ROBOTS_BLOCK_KLPRISM = """\
User-agent: KlPrismBot
Disallow: /

User-agent: *
Allow: /
"""


def _patch_fetch(return_value: str | None):
    """Shortcut to mock ``_fetch_robots_txt``."""
    return patch.object(
        RobotsCache,
        "_fetch_robots_txt",
        new_callable=AsyncMock,
        return_value=return_value,
    )


class TestRobotsCache:
    """Core robots.txt cache behaviour."""

    async def test_allowed_when_no_robots_txt(self):
        """Missing robots.txt -> allow (RFC 9309)."""
        cache = RobotsCache()
        with _patch_fetch(None) as mock_fetch:
            result = await cache.is_allowed("https://example.com/page")
            assert result is True
            mock_fetch.assert_awaited_once()

    async def test_disallowed_path(self):
        """Explicit Disallow: / blocks everything."""
        cache = RobotsCache()
        with _patch_fetch(ROBOTS_DISALLOW_ALL):
            result = await cache.is_allowed("https://example.com/anything")
            assert result is False

    async def test_partial_disallow(self):
        """Only specific paths are blocked."""
        cache = RobotsCache()
        with _patch_fetch(ROBOTS_ALLOW_ROOT_ONLY):
            assert await cache.is_allowed("https://example.com/") is True
            assert await cache.is_allowed("https://example.com/public") is True
            assert await cache.is_allowed("https://example.com/private/secret") is False
            assert await cache.is_allowed("https://example.com/admin/panel") is False

    async def test_user_agent_specific_block(self):
        """Our bot is specifically blocked, others allowed."""
        cache = RobotsCache(user_agent="KlPrismBot/1.0")
        with _patch_fetch(ROBOTS_BLOCK_KLPRISM):
            assert await cache.is_allowed("https://example.com/page") is False

        # Different user-agent should be allowed
        cache2 = RobotsCache(user_agent="OtherBot/1.0")
        with _patch_fetch(ROBOTS_BLOCK_KLPRISM):
            assert await cache2.is_allowed("https://example.com/page") is True

    async def test_cache_hit_skips_refetch(self):
        """Second call for same domain uses cache, no re-fetch."""
        cache = RobotsCache()
        with _patch_fetch(ROBOTS_ALLOW_ROOT_ONLY) as mock_fetch:
            await cache.is_allowed("https://example.com/a")
            await cache.is_allowed("https://example.com/b")
            # Only one fetch for the same domain
            assert mock_fetch.await_count == 1

    async def test_different_domains_fetch_separately(self):
        """Each domain gets its own robots.txt fetch."""
        cache = RobotsCache()
        with _patch_fetch(None) as mock_fetch:
            await cache.is_allowed("https://alpha.com/page")
            await cache.is_allowed("https://beta.com/page")
            assert mock_fetch.await_count == 2

    async def test_cache_expires_after_ttl(self):
        """Expired cache entry triggers a re-fetch."""
        cache = RobotsCache(ttl_seconds=0)  # immediate expiry
        with _patch_fetch(None) as mock_fetch:
            await cache.is_allowed("https://example.com/a")
            await cache.is_allowed("https://example.com/b")
            # Both should fetch because TTL=0
            assert mock_fetch.await_count == 2


class TestRobotsDisallowedError:
    """Error type tests."""

    def test_error_message(self):
        err = RobotsDisallowedError("https://example.com/secret", "KlPrismBot/1.0")
        assert "KlPrismBot/1.0" in str(err)
        assert "https://example.com/secret" in str(err)
        assert err.url == "https://example.com/secret"
        assert err.user_agent == "KlPrismBot/1.0"

    def test_is_exception(self):
        assert issubclass(RobotsDisallowedError, Exception)
