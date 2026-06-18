"""Typed client for MangaDex API v5 with rate limiting and SSRF protection.

MangaDex API docs: https://api.mangadex.org/docs/

All HTTP requests go through ``safe_httpx_client()`` to enforce SSRF safety
(DNS pinning, private IP blocking). Rate limiting is enforced at 4 RPS per
the MangaDex API guidelines.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx
from pydantic import BaseModel

from web_core.http import safe_httpx_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class MangaInfo(BaseModel):
    """Manga metadata from a search or detail lookup."""

    id: str
    title: str
    alt_titles: list[str] = []
    description: str = ""
    cover_url: str | None = None
    status: str = ""
    year: int | None = None


class ChapterInfo(BaseModel):
    """Single chapter entry from a manga feed."""

    id: str
    chapter: str | None = None
    title: str | None = None
    volume: str | None = None
    language: str = ""
    pages: int = 0


class ChapterPage(BaseModel):
    """Single page image info with full URL."""

    url: str
    filename: str


class ChapterImages(BaseModel):
    """Image file list for a chapter from the at-home delivery server."""

    base_url: str
    hash: str
    data: list[str]
    data_saver: list[str]

    @property
    def images(self) -> list[ChapterPage]:
        """Get list of full image URLs for standard quality."""
        return [ChapterPage(url=f"{self.base_url}/data/{self.hash}/{fn}", filename=fn) for fn in self.data]

    @property
    def images_saver(self) -> list[ChapterPage]:
        """Get list of full image URLs for data-saver quality."""
        return [ChapterPage(url=f"{self.base_url}/data-saver/{self.hash}/{fn}", filename=fn) for fn in self.data_saver]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# Gioi han so trang tai xuong toi da trong mot lan goi ``get_chapter_feed``
# de tranh vong lap vo han khi API tra ve du lieu bat thuong.
_MAX_FEED_PAGES = 50


class MangaDexClient:
    """Typed async client for the MangaDex API v5.

    Features:
    - SSRF-safe HTTP via ``safe_httpx_client()``
    - Token-bucket rate limiting (default 4 RPS)
    - Typed Pydantic response models
    - Automatic pagination for chapter feeds

    Usage::

        # Standalone usage (creates a new HTTP connection per request)
        client = MangaDexClient()
        results = await client.search_manga("One Piece")

        # Context manager usage (reuses HTTP connections, recommended for bulk operations)
        async with MangaDexClient() as client:
            chapters = await client.get_chapter_feed(results[0].id)
            images = await client.get_chapter_images(chapters[0].id)
    """

    BASE_URL = "https://api.mangadex.org"
    COVERS_CDN = "https://uploads.mangadex.org/covers"
    RATE_LIMIT_RPS = 4
    # at-home/server endpoint has stricter limit: ~40 req/min = 0.67 RPS
    AT_HOME_RATE_LIMIT_RPS = 0.5

    def __init__(self, user_agent: str = "KnowledgePrism/1.0") -> None:
        self._user_agent = user_agent
        self._last_request_time = 0.0
        self._last_at_home_time = 0.0
        self._lock = asyncio.Lock()
        self._at_home_lock = asyncio.Lock()
        self._client_count = 0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> MangaDexClient:
        self._client_count += 1
        if self._client is None:
            # We use 60.0 here since download_image needs 60.0, and sharing client means sharing the timeout
            self._client = safe_httpx_client(timeout=60.0)
            await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self._client_count -= 1
        if self._client_count <= 0 and self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    # -- internal helpers ---------------------------------------------------

    async def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        async with self._lock:
            now = time.monotonic()
            min_interval = 1.0 / self.RATE_LIMIT_RPS
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request_time = time.monotonic()

    async def _get(self, path: str, params: dict[str, object] | None = None) -> dict:
        """Send a GET request to the MangaDex API.

        Raises ``httpx.HTTPStatusError`` on 4xx/5xx responses.
        """
        await self._rate_limit()

        # Performance Optimization: Reuse HTTP client if available
        if self._client is not None:
            resp = await self._client.get(
                f"{self.BASE_URL}{path}",
                params=params,
                headers={"User-Agent": self._user_agent},
            )
            resp.raise_for_status()
            return resp.json()

        async with safe_httpx_client(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}{path}",
                params=params,
                headers={"User-Agent": self._user_agent},
            )
            resp.raise_for_status()
            return resp.json()

    def _parse_manga_item(self, item: dict) -> MangaInfo:
        """Parse a single manga item from the API response."""
        attrs = item.get("attributes", {})
        titles = attrs.get("title", {})
        main_title = next(iter(titles.values()), "")
        alt = [next(iter(t.values()), "") for t in attrs.get("altTitles", [])]

        cover_url = _extract_cover_url(item)

        return MangaInfo(
            id=item.get("id", ""),
            title=main_title,
            alt_titles=alt,
            description=next(iter(attrs.get("description", {}).values()), ""),
            cover_url=cover_url,
            status=attrs.get("status", ""),
            year=attrs.get("year"),
        )

    def _parse_chapter_item(self, item: dict) -> ChapterInfo:
        """Parse a single chapter item from the API response."""
        attrs = item.get("attributes", {})
        return ChapterInfo(
            id=item.get("id", ""),
            chapter=attrs.get("chapter"),
            title=attrs.get("title"),
            volume=attrs.get("volume"),
            language=attrs.get("translatedLanguage", ""),
            pages=attrs.get("pages", 0),
        )

    # -- public API ---------------------------------------------------------

    async def get_manga(self, manga_id: str) -> MangaInfo:
        """Get manga metadata by UUID.

        Includes ``cover_art`` relationship.
        """
        data = await self._get(f"/manga/{manga_id}", params={"includes[]": "cover_art"})
        return self._parse_manga_item(data.get("data", {}))

    async def get_chapter(self, chapter_id: str) -> ChapterInfo:
        """Get chapter metadata by UUID."""
        data = await self._get(f"/chapter/{chapter_id}")
        return self._parse_chapter_item(data.get("data", {}))

    async def search_manga(self, title: str, limit: int = 10) -> list[MangaInfo]:
        """Search manga by title.

        Includes ``cover_art`` relationship so cover URLs can be extracted
        without a second request.
        """
        data = await self._get(
            "/manga",
            params={
                "title": title,
                "limit": limit,
                "includes[]": "cover_art",
            },
        )
        results: list[MangaInfo] = []
        for item in data.get("data", []):
            results.append(self._parse_manga_item(item))
        return results

    async def get_chapter_feed(
        self,
        manga_id: str,
        language: str = "en",
        limit: int = 100,
    ) -> list[ChapterInfo]:
        """Get chapters for a manga, handling pagination automatically.

        Parameters
        ----------
        manga_id:
            UUID of the manga.
        language:
            Translated language filter (ISO 639-1).
        limit:
            Maximum number of chapters to return.
        """

        def _parse_batch(items: list[dict]) -> list[ChapterInfo]:
            return [self._parse_chapter_item(item) for item in items]

        async with self:
            # Fetch first page to get total (MangaDex supports limit up to 500 for feeds)
            first_batch_limit = min(limit, 500)
            data = await self._get(
                f"/manga/{manga_id}/feed",
                params={
                    "translatedLanguage[]": language,
                    "order[chapter]": "asc",
                    "limit": first_batch_limit,
                    "offset": 0,
                },
            )

            total = data.get("total", 0)
            first_batch = data.get("data", [])
            chapters = _parse_batch(first_batch)

            # Calculate remaining pages
            effective_limit = min(limit, total)
            if len(chapters) >= effective_limit or not first_batch:
                return chapters[:limit]

            # Prepare offsets for remaining pages
            offsets = []
            curr_offset = len(chapters)
            pages_to_fetch = 1  # We already fetched one page
            while curr_offset < effective_limit and pages_to_fetch < _MAX_FEED_PAGES:
                next_batch_limit = min(limit - curr_offset, 500)
                offsets.append((curr_offset, next_batch_limit))
                curr_offset += next_batch_limit
                pages_to_fetch += 1

            if not offsets:
                return chapters[:limit]

            async def fetch_page(offset: int, b_limit: int) -> list[ChapterInfo]:
                page_data = await self._get(
                    f"/manga/{manga_id}/feed",
                    params={
                        "translatedLanguage[]": language,
                        "order[chapter]": "asc",
                        "limit": b_limit,
                        "offset": offset,
                    },
                )
                return _parse_batch(page_data.get("data", []))

            results = await asyncio.gather(*(fetch_page(o, limit_) for o, limit_ in offsets))
            for batch_chapters in results:
                chapters.extend(batch_chapters)

            return chapters[:limit]

    async def get_chapter_images(self, chapter_id: str) -> ChapterImages:
        """Get image delivery info for a chapter via the MangaDex@Home network."""
        # at-home/server has stricter rate limit than main API
        async with self._at_home_lock:
            now = time.monotonic()
            min_interval = 1.0 / self.AT_HOME_RATE_LIMIT_RPS
            elapsed = now - self._last_at_home_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_at_home_time = time.monotonic()

        data = await self._get(f"/at-home/server/{chapter_id}")
        ch = data.get("chapter", {})
        return ChapterImages(
            base_url=data.get("baseUrl", ""),
            hash=ch.get("hash", ""),
            data=ch.get("data", []),
            data_saver=ch.get("dataSaver", []),
        )

    async def download_image(
        self,
        base_url: str,
        hash: str,
        filename: str,
        *,
        saver: bool = False,
    ) -> bytes:
        """Download a single chapter page image.

        Parameters
        ----------
        base_url:
            Base URL from ``ChapterImages.base_url``.
        hash:
            Chapter hash from ``ChapterImages.hash``.
        filename:
            Filename from ``ChapterImages.data`` or ``ChapterImages.data_saver``.
        saver:
            If True, use data-saver (compressed) quality.

        Returns
        -------
        bytes
            Raw image content.
        """
        quality = "data-saver" if saver else "data"
        url = f"{base_url}/{quality}/{hash}/{filename}"
        await self._rate_limit()

        # Performance Optimization: Reuse HTTP client if available
        if self._client is not None:
            resp = await self._client.get(url, headers={"User-Agent": self._user_agent})
            resp.raise_for_status()
            return resp.content

        async with safe_httpx_client(timeout=60.0) as client:
            resp = await client.get(url, headers={"User-Agent": self._user_agent})
            resp.raise_for_status()
            return resp.content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_cover_url(manga_item: dict) -> str | None:
    """Extract the full cover image URL from an included ``cover_art`` relationship."""
    manga_id = manga_item.get("id", "")
    for rel in manga_item.get("relationships", []):
        if rel.get("type") == "cover_art":
            cover_fn = rel.get("attributes", {}).get("fileName", "")
            if cover_fn:
                return f"{MangaDexClient.COVERS_CDN}/{manga_id}/{cover_fn}"
    return None
