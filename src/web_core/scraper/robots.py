"""Robots.txt compliance with per-domain caching.

Checks robots.txt before fetching any URL. Uses stdlib
``urllib.robotparser.RobotFileParser`` -- no new dependencies.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from web_core.http import safe_httpx_client

logger = logging.getLogger(__name__)


class RobotsDisallowedError(Exception):
    """Raised when robots.txt disallows crawling a URL."""

    def __init__(self, url: str, user_agent: str):
        self.url = url
        self.user_agent = user_agent
        super().__init__(f"robots.txt disallows {user_agent} from fetching {url}")


class RobotsCache:
    """Per-domain robots.txt cache with TTL-based expiry.

    Parameters
    ----------
    user_agent:
        The User-Agent string to check against robots.txt rules.
    ttl_seconds:
        How long to cache a parsed robots.txt before re-fetching.
    """

    def __init__(
        self,
        user_agent: str = "KlPrismBot/1.0",
        ttl_seconds: int = 3600,
    ):
        self.user_agent = user_agent
        self.ttl_seconds = ttl_seconds
        # domain -> (RobotFileParser, timestamp)
        self._cache: dict[str, tuple[RobotFileParser, float]] = {}

    async def is_allowed(self, url: str) -> bool:
        """Return True if ``user_agent`` may fetch *url* per robots.txt.

        Missing or unreachable robots.txt defaults to **allow** (per RFC 9309).
        """
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        parser = await self._get_parser(origin)
        return parser.can_fetch(self.user_agent, url)

    async def _get_parser(self, origin: str) -> RobotFileParser:
        """Return a cached or freshly-fetched ``RobotFileParser`` for *origin*."""
        cached = self._cache.get(origin)
        if cached is not None:
            parser, fetched_at = cached
            if time.monotonic() - fetched_at < self.ttl_seconds:
                return parser

        robots_url = f"{origin}/robots.txt"
        content = await self._fetch_robots_txt(robots_url)

        parser = RobotFileParser()
        if content is not None:
            parser.parse(content.splitlines())
        else:
            # Unreachable robots.txt -> allow everything (RFC 9309 sec 2.3)
            parser.allow_all = True

        self._cache[origin] = (parser, time.monotonic())
        return parser

    async def _fetch_robots_txt(self, url: str) -> str | None:
        """Fetch robots.txt content. Returns None on any error."""
        try:
            async with safe_httpx_client(timeout=10.0) as client:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    return resp.text
                return None
        except Exception:
            logger.debug("Failed to fetch %s, defaulting to allow", url, exc_info=True)
            return None
