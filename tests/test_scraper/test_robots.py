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


class TestSharedClient:
    """Tests for the shared HTTP client lazy-init and caching."""

    async def test_get_shared_client_caching(self):
        """Re-initialization if already set but closed (shared client pattern)."""
        from unittest.mock import MagicMock, patch

        from web_core.scraper import robots as robots_mod
        from web_core.scraper.robots import _get_shared_client

        # Reset global state for testing
        old_client = robots_mod._shared_client
        robots_mod._shared_client = None

        try:
            with patch("web_core.scraper.robots.safe_httpx_client") as mock_factory:
                m1 = MagicMock()
                m1.is_closed = False
                m2 = MagicMock()
                m2.is_closed = False

                mock_factory.side_effect = [m1, m2]

                # 1. First call creates it
                c1 = _get_shared_client()
                assert c1 is m1
                mock_factory.assert_called_once_with(timeout=10.0)

                # 2. Second call reuses it
                c2 = _get_shared_client()
                assert c2 is c1
                assert mock_factory.call_count == 1

                # 3. If closed, creates new one
                m1.is_closed = True
                c3 = _get_shared_client()
                assert c3 is m2
                assert c3 is not c1
                assert mock_factory.call_count == 2
                mock_factory.assert_called_with(timeout=10.0)
        finally:
            robots_mod._shared_client = old_client

    async def test_fetch_robots_txt_success(self):
        """Success case for the real _fetch_robots_txt implementation."""
        from unittest.mock import MagicMock, patch

        from web_core.scraper.robots import RobotsCache

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "User-agent: *\nAllow: /"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        cache = RobotsCache()
        with patch("web_core.scraper.robots._get_shared_client", return_value=mock_client):
            content = await cache._fetch_robots_txt("https://example.com/robots.txt")
            assert content == "User-agent: *\nAllow: /"
            mock_client.get.assert_called_once_with("https://example.com/robots.txt", follow_redirects=True)

    async def test_fetch_robots_txt_error_status(self):
        """Non-200 status should return None."""
        from unittest.mock import MagicMock, patch

        from web_core.scraper.robots import RobotsCache

        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        cache = RobotsCache()
        with patch("web_core.scraper.robots._get_shared_client", return_value=mock_client):
            content = await cache._fetch_robots_txt("https://example.com/robots.txt")
            assert content is None

    async def test_fetch_robots_txt_exception(self):
        """Exception during fetch should return None."""
        from unittest.mock import MagicMock, patch

        from web_core.scraper.robots import RobotsCache

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))

        cache = RobotsCache()
        with patch("web_core.scraper.robots._get_shared_client", return_value=mock_client):
            content = await cache._fetch_robots_txt("https://example.com/robots.txt")
            assert content is None
