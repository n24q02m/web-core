"""Tests for robots.txt compliance via RobotsTxtChecker."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from web_core.scraper.robots import RobotsTxtChecker, RobotsDisallowedError

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

ROBOTS_BLOCK_OUR_BOT = """\
User-agent: web-core-bot
Disallow: /

User-agent: *
Allow: /
"""


def _patch_fetch(return_value: str | None):
    """Shortcut to mock ``_fetch_robots_txt``."""
    return patch.object(
        RobotsTxtChecker,
        "_fetch_robots_txt",
        new_callable=AsyncMock,
        return_value=return_value,
    )


class TestRobotsTxtChecker:
    """Core robots.txt checker behaviour."""

    async def test_allowed_when_no_robots_txt(self):
        """Missing robots.txt -> allow (RFC 9309)."""
        checker = RobotsTxtChecker()
        with _patch_fetch(None) as mock_fetch:
            result = await checker.is_allowed("https://example.com/page")
            assert result is True
            mock_fetch.assert_awaited_once()

    async def test_disallowed_path(self):
        """Explicit Disallow: / blocks everything."""
        checker = RobotsTxtChecker()
        with _patch_fetch(ROBOTS_DISALLOW_ALL):
            result = await checker.is_allowed("https://example.com/anything")
            assert result is False

    async def test_partial_disallow(self):
        """Only specific paths are blocked."""
        checker = RobotsTxtChecker()
        with _patch_fetch(ROBOTS_ALLOW_ROOT_ONLY):
            assert await checker.is_allowed("https://example.com/") is True
            assert await checker.is_allowed("https://example.com/public") is True
            assert await checker.is_allowed("https://example.com/private/secret") is False
            assert await checker.is_allowed("https://example.com/admin/panel") is False

    async def test_user_agent_specific_block(self):
        """Our bot is specifically blocked, others allowed."""
        checker = RobotsTxtChecker(user_agent="web-core-bot/1.0")
        with _patch_fetch(ROBOTS_BLOCK_OUR_BOT):
            assert await checker.is_allowed("https://example.com/page") is False

        # Different user-agent should be allowed
        checker2 = RobotsTxtChecker(user_agent="OtherBot/1.0")
        with _patch_fetch(ROBOTS_BLOCK_OUR_BOT):
            assert await checker2.is_allowed("https://example.com/page") is True

    async def test_cache_hit_skips_refetch(self):
        """Second call for same domain uses checker, no re-fetch."""
        checker = RobotsTxtChecker()
        with _patch_fetch(ROBOTS_ALLOW_ROOT_ONLY) as mock_fetch:
            await checker.is_allowed("https://example.com/a")
            await checker.is_allowed("https://example.com/b")
            # Only one fetch for the same domain
            assert mock_fetch.await_count == 1

    async def test_cache_hit_cross_scheme(self):
        """http and https on same domain share cache via extract_domain."""
        checker = RobotsTxtChecker()
        with _patch_fetch(ROBOTS_ALLOW_ROOT_ONLY) as mock_fetch:
            await checker.is_allowed("http://example.com/a")
            await checker.is_allowed("https://example.com/b")
            # Only one fetch because extract_domain ignores scheme
            assert mock_fetch.await_count == 1

    async def test_different_domains_fetch_separately(self):
        """Each domain gets its own robots.txt fetch."""
        checker = RobotsTxtChecker()
        with _patch_fetch(None) as mock_fetch:
            await checker.is_allowed("https://alpha.com/page")
            await checker.is_allowed("https://beta.com/page")
            assert mock_fetch.await_count == 2

    async def test_cache_expires_after_ttl(self):
        """Expired checker entry triggers a re-fetch."""
        checker = RobotsTxtChecker(ttl_seconds=0)  # immediate expiry
        with _patch_fetch(None) as mock_fetch:
            await checker.is_allowed("https://example.com/a")
            await checker.is_allowed("https://example.com/b")
            # Both should fetch because TTL=0
            assert mock_fetch.await_count == 2


class TestRobotsDisallowedError:
    """Error type tests."""

    def test_error_message(self):
        err = RobotsDisallowedError("https://example.com/secret", "web-core-bot/1.0")
        assert "web-core-bot/1.0" in str(err)
        assert "https://example.com/secret" in str(err)
        assert err.url == "https://example.com/secret"
        assert err.user_agent == "web-core-bot/1.0"

    def test_is_exception(self):
        assert issubclass(RobotsDisallowedError, Exception)
