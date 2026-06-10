"""Tests for robots.txt compliance via RobotsCache."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper import robots as robots_mod
from web_core.scraper.robots import RobotsCache, RobotsDisallowedError, _get_shared_client

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


@pytest.fixture(autouse=True)
def _reset_shared_client():
    """Reset the global _shared_client before each test."""
    old_client = robots_mod._shared_client
    robots_mod._shared_client = None
    yield
    robots_mod._shared_client = old_client


def _patch_fetch(return_value: str | None):
    """Shortcut to mock ``_fetch_robots_txt``."""
    return patch.object(
        RobotsCache,
        "_fetch_robots_txt",
        new_callable=AsyncMock,
        return_value=return_value,
    )


class TestSharedClient:
    """Tests for the shared httpx client caching logic."""

    async def test_get_shared_client_caching(self):
        """Verify that multiple calls return the same client instance."""
        with patch("web_core.scraper.robots.safe_httpx_client") as mock_factory:
            m1 = MagicMock()
            m1.is_closed = False
            mock_factory.return_value = m1

            c1 = _get_shared_client()
            c2 = _get_shared_client()

            assert c1 is m1
            assert c2 is c1
            assert mock_factory.call_count == 1

    async def test_get_shared_client_reinit_when_closed(self):
        """Verify that a new client is created if the cached one is closed."""
        with patch("web_core.scraper.robots.safe_httpx_client") as mock_factory:
            m1 = MagicMock()
            m1.is_closed = False
            m2 = MagicMock()
            m2.is_closed = False
            mock_factory.side_effect = [m1, m2]

            # 1. Create first client
            c1 = _get_shared_client()
            assert c1 is m1

            # 2. Close it and verify re-init
            m1.is_closed = True
            c2 = _get_shared_client()
            assert c2 is m2
            assert c2 is not c1
            assert mock_factory.call_count == 2


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
        cache = RobotsCache(user_agent="web-core-bot/1.0")
        with _patch_fetch(ROBOTS_BLOCK_OUR_BOT):
            assert await cache.is_allowed("https://example.com/page") is False

        # Different user-agent should be allowed
        cache2 = RobotsCache(user_agent="OtherBot/1.0")
        with _patch_fetch(ROBOTS_BLOCK_OUR_BOT):
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

    async def test_fetch_robots_txt_uses_shared_client(self):
        """Verify that _fetch_robots_txt actually calls the shared client."""
        cache = RobotsCache()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "User-agent: *\nAllow: /"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("web_core.scraper.robots._get_shared_client", return_value=mock_client):
            content = await cache._fetch_robots_txt("https://example.com/robots.txt")
            assert content == "User-agent: *\nAllow: /"
            mock_client.get.assert_called_once_with("https://example.com/robots.txt", follow_redirects=True)

    async def test_fetch_robots_txt_handles_error(self):
        """Verify that _fetch_robots_txt handles exceptions gracefully."""
        cache = RobotsCache()
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("network error")

        with patch("web_core.scraper.robots._get_shared_client", return_value=mock_client):
            content = await cache._fetch_robots_txt("https://example.com/robots.txt")
            assert content is None

    async def test_fetch_robots_txt_non_200(self):
        """Verify that _fetch_robots_txt returns None for non-200 responses."""
        cache = RobotsCache()
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("web_core.scraper.robots._get_shared_client", return_value=mock_client):
            content = await cache._fetch_robots_txt("https://example.com/robots.txt")
            assert content is None


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
