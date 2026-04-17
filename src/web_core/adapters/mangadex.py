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


class ChapterImages(BaseModel):
    """Image file list for a chapter from the at-home delivery server."""

    base_url: str
    hash: str
    data: list[str]
    data_saver: list[str]


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

        client = MangaDexClient()
        results = await client.search_manga("One Piece")
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

    # -- internal helpers ---------------------------------------------------

    async def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
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
        async with safe_httpx_client(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}{path}",
                params=params,
                headers={"User-Agent": self._user_agent},
            )
            resp.raise_for_status()
            return resp.json()

    # -- public API ---------------------------------------------------------

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
            attrs = item.get("attributes", {})
            titles = attrs.get("title", {})
            main_title = next(iter(titles.values()), "")
            alt = [next(iter(t.values()), "") for t in attrs.get("altTitles", [])]

            cover_url = _extract_cover_url(item)

            results.append(
                MangaInfo(
                    id=item["id"],
                    title=main_title,
                    alt_titles=alt,
                    description=next(iter(attrs.get("description", {}).values()), ""),
                    cover_url=cover_url,
                    status=attrs.get("status", ""),
                    year=attrs.get("year"),
                )
            )
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
        chapters: list[ChapterInfo] = []
        offset = 0
        pages_fetched = 0

        while pages_fetched < _MAX_FEED_PAGES:
            batch_limit = min(limit - len(chapters), 100)
            if batch_limit <= 0:
                break

            data = await self._get(
                f"/manga/{manga_id}/feed",
                params={
                    "translatedLanguage[]": language,
                    "order[chapter]": "asc",
                    "limit": batch_limit,
                    "offset": offset,
                },
            )
            batch = data.get("data", [])
            for item in batch:
                attrs = item.get("attributes", {})
                chapters.append(
                    ChapterInfo(
                        id=item["id"],
                        chapter=attrs.get("chapter"),
                        title=attrs.get("title"),
                        volume=attrs.get("volume"),
                        language=attrs.get("translatedLanguage", ""),
                        pages=attrs.get("pages", 0),
                    )
                )

            total = data.get("total", 0)
            offset += len(batch)
            pages_fetched += 1

            if offset >= total or len(chapters) >= limit or not batch:
                break

        return chapters

    async def get_chapter_images(self, chapter_id: str) -> ChapterImages:
        """Get image delivery info for a chapter via the MangaDex@Home network."""
        # at-home/server has stricter rate limit than main API
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
