"""Tests for MangaDex API adapter -- models, URL construction, and mocked HTTP."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from web_core.adapters.mangadex import (
    ChapterImages,
    ChapterInfo,
    MangaDexClient,
    MangaInfo,
    _extract_cover_url,
    build_page_url,
)

# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


class TestMangaInfo:
    """Test MangaInfo model validation and defaults."""

    def test_minimal_fields(self):
        m = MangaInfo(id="abc-123", title="Test Manga")
        assert m.id == "abc-123"
        assert m.title == "Test Manga"
        assert m.alt_titles == []
        assert m.description == ""
        assert m.cover_url is None
        assert m.status == ""
        assert m.year is None

    def test_all_fields(self):
        m = MangaInfo(
            id="abc-123",
            title="One Piece",
            alt_titles=["OP", "Wan Piisu"],
            description="Pirates adventure",
            cover_url="https://uploads.mangadex.org/covers/abc-123/cover.jpg",
            status="ongoing",
            year=1997,
        )
        assert m.title == "One Piece"
        assert len(m.alt_titles) == 2
        assert m.year == 1997
        assert m.cover_url is not None

    def test_serialization_roundtrip(self):
        original = MangaInfo(id="x", title="T", alt_titles=["A"], year=2020)
        data = original.model_dump()
        restored = MangaInfo.model_validate(data)
        assert restored == original


class TestChapterInfo:
    """Test ChapterInfo model validation and defaults."""

    def test_minimal_fields(self):
        c = ChapterInfo(id="ch-1")
        assert c.id == "ch-1"
        assert c.chapter is None
        assert c.title is None
        assert c.volume is None
        assert c.language == ""
        assert c.pages == 0

    def test_all_fields(self):
        c = ChapterInfo(
            id="ch-1",
            chapter="42",
            title="The Answer",
            volume="5",
            language="en",
            pages=18,
        )
        assert c.chapter == "42"
        assert c.pages == 18


class TestChapterImages:
    """Test ChapterImages model validation."""

    def test_construction(self):
        ci = ChapterImages(
            base_url="https://example.com",
            hash="abc123",
            data=["page1.png", "page2.png"],
            data_saver=["page1.jpg", "page2.jpg"],
        )
        assert ci.base_url == "https://example.com"
        assert ci.hash == "abc123"
        assert len(ci.data) == 2
        assert len(ci.data_saver) == 2

    def test_empty_lists(self):
        ci = ChapterImages(base_url="", hash="", data=[], data_saver=[])
        assert ci.data == []
        assert ci.data_saver == []


# ---------------------------------------------------------------------------
# URL construction helpers
# ---------------------------------------------------------------------------


class TestBuildPageUrl:
    """Test build_page_url helper."""

    def test_full_quality(self):
        url = build_page_url("https://server.example.com", "abc123", "page1.png")
        assert url == "https://server.example.com/data/abc123/page1.png"

    def test_data_saver(self):
        url = build_page_url("https://server.example.com", "abc123", "page1.jpg", saver=True)
        assert url == "https://server.example.com/data-saver/abc123/page1.jpg"

    def test_preserves_base_url_without_trailing_slash(self):
        url = build_page_url("https://s.example.com", "h", "f.png")
        assert url.startswith("https://s.example.com/data/")

    def test_no_double_slash(self):
        """Base URL should not have a trailing slash in practice,
        but the function concatenates with / so no double slash."""
        url = build_page_url("https://s.example.com", "h", "f.png")
        assert "//" not in url.replace("https://", "")


class TestExtractCoverUrl:
    """Test _extract_cover_url helper."""

    def test_extracts_from_relationships(self):
        item = {
            "id": "manga-uuid",
            "relationships": [
                {"type": "author", "id": "auth-1"},
                {
                    "type": "cover_art",
                    "id": "cover-1",
                    "attributes": {"fileName": "cover.jpg"},
                },
            ],
        }
        url = _extract_cover_url(item)
        assert url == "https://uploads.mangadex.org/covers/manga-uuid/cover.jpg"

    def test_returns_none_when_no_cover_art(self):
        item = {
            "id": "manga-uuid",
            "relationships": [{"type": "author", "id": "auth-1"}],
        }
        assert _extract_cover_url(item) is None

    def test_returns_none_when_no_relationships(self):
        item = {"id": "manga-uuid", "relationships": []}
        assert _extract_cover_url(item) is None

    def test_returns_none_when_empty_filename(self):
        item = {
            "id": "manga-uuid",
            "relationships": [
                {
                    "type": "cover_art",
                    "id": "cover-1",
                    "attributes": {"fileName": ""},
                },
            ],
        }
        assert _extract_cover_url(item) is None

    def test_returns_none_when_no_attributes(self):
        item = {
            "id": "manga-uuid",
            "relationships": [{"type": "cover_art", "id": "cover-1"}],
        }
        assert _extract_cover_url(item) is None


# ---------------------------------------------------------------------------
# MangaDexClient -- construction and config
# ---------------------------------------------------------------------------


class TestMangaDexClientConfig:
    """Test client construction and configuration."""

    def test_default_user_agent(self):
        client = MangaDexClient()
        assert client._user_agent == "KnowledgePrism/1.0"

    def test_custom_user_agent(self):
        client = MangaDexClient(user_agent="TestAgent/2.0")
        assert client._user_agent == "TestAgent/2.0"

    def test_base_url(self):
        assert MangaDexClient.BASE_URL == "https://api.mangadex.org"

    def test_rate_limit_default(self):
        assert MangaDexClient.RATE_LIMIT_RPS == 4

    def test_initial_last_request_time(self):
        client = MangaDexClient()
        assert client._last_request_time == 0.0


# ---------------------------------------------------------------------------
# MangaDexClient -- mocked HTTP calls
# ---------------------------------------------------------------------------

# Fixture data mocking the MangaDex API responses


def _mock_search_response() -> dict:
    return {
        "result": "ok",
        "data": [
            {
                "id": "manga-001",
                "type": "manga",
                "attributes": {
                    "title": {"en": "One Piece"},
                    "altTitles": [{"ja": "Wan Piisu"}, {"ko": "Won Piseu"}],
                    "description": {"en": "A pirate adventure."},
                    "status": "ongoing",
                    "year": 1997,
                },
                "relationships": [
                    {
                        "type": "cover_art",
                        "id": "cover-001",
                        "attributes": {"fileName": "one-piece-cover.jpg"},
                    },
                ],
            },
            {
                "id": "manga-002",
                "type": "manga",
                "attributes": {
                    "title": {"ja": "Naruto"},
                    "altTitles": [],
                    "description": {},
                    "status": "completed",
                    "year": 1999,
                },
                "relationships": [],
            },
        ],
        "total": 2,
    }


def _mock_feed_response(offset: int = 0) -> dict:
    """Simulate a single page of chapter feed."""
    return {
        "result": "ok",
        "data": [
            {
                "id": f"ch-{offset + 1}",
                "type": "chapter",
                "attributes": {
                    "chapter": str(offset + 1),
                    "title": f"Chapter {offset + 1}",
                    "volume": "1",
                    "translatedLanguage": "en",
                    "pages": 20,
                },
            },
            {
                "id": f"ch-{offset + 2}",
                "type": "chapter",
                "attributes": {
                    "chapter": str(offset + 2),
                    "title": f"Chapter {offset + 2}",
                    "volume": "1",
                    "translatedLanguage": "en",
                    "pages": 18,
                },
            },
        ],
        "total": 2,
    }


def _mock_at_home_response() -> dict:
    return {
        "result": "ok",
        "baseUrl": "https://cmdxd98sb0x3yprd.mangadex.network",
        "chapter": {
            "hash": "abcdef123456",
            "data": ["p1-full.png", "p2-full.png", "p3-full.png"],
            "dataSaver": ["p1-saver.jpg", "p2-saver.jpg", "p3-saver.jpg"],
        },
    }


def _make_mock_response(json_data: dict | None = None, content: bytes = b"") -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data or {})
    resp.content = content
    return resp


class TestSearchManga:
    """Test search_manga with mocked HTTP."""

    async def test_returns_parsed_results(self):
        mock_resp = _make_mock_response(_mock_search_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            results = await client.search_manga("One Piece")

        assert len(results) == 2
        assert results[0].id == "manga-001"
        assert results[0].title == "One Piece"
        assert results[0].alt_titles == ["Wan Piisu", "Won Piseu"]
        assert results[0].description == "A pirate adventure."
        assert results[0].status == "ongoing"
        assert results[0].year == 1997
        assert results[0].cover_url == "https://uploads.mangadex.org/covers/manga-001/one-piece-cover.jpg"

    async def test_manga_without_cover(self):
        mock_resp = _make_mock_response(_mock_search_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            results = await client.search_manga("Naruto")

        # manga-002 has no cover_art relationship
        assert results[1].cover_url is None
        assert results[1].description == ""

    async def test_empty_search_results(self):
        mock_resp = _make_mock_response({"result": "ok", "data": [], "total": 0})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            results = await client.search_manga("NonexistentManga12345")

        assert results == []

    async def test_passes_correct_params(self):
        mock_resp = _make_mock_response({"data": [], "total": 0})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient(user_agent="TestBot/1.0")
            await client.search_manga("test", limit=5)

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args.args[0] == "https://api.mangadex.org/manga"
        assert call_args.kwargs["params"]["title"] == "test"
        assert call_args.kwargs["params"]["limit"] == 5
        assert call_args.kwargs["params"]["includes[]"] == "cover_art"
        assert call_args.kwargs["headers"]["User-Agent"] == "TestBot/1.0"

    async def test_raises_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock())
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            with pytest.raises(httpx.HTTPStatusError):
                await client.search_manga("error")


class TestGetChapterFeed:
    """Test get_chapter_feed with mocked HTTP."""

    async def test_returns_parsed_chapters(self):
        mock_resp = _make_mock_response(_mock_feed_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            chapters = await client.get_chapter_feed("manga-001")

        assert len(chapters) == 2
        assert chapters[0].id == "ch-1"
        assert chapters[0].chapter == "1"
        assert chapters[0].title == "Chapter 1"
        assert chapters[0].volume == "1"
        assert chapters[0].language == "en"
        assert chapters[0].pages == 20

    async def test_passes_language_param(self):
        mock_resp = _make_mock_response({"data": [], "total": 0})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            await client.get_chapter_feed("manga-001", language="vi")

        call_args = mock_client.get.call_args
        assert call_args.kwargs["params"]["translatedLanguage[]"] == "vi"
        assert call_args.kwargs["params"]["order[chapter]"] == "asc"

    async def test_pagination_stops_at_total(self):
        """When offset >= total, pagination must stop."""
        mock_resp = _make_mock_response(_mock_feed_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            chapters = await client.get_chapter_feed("manga-001", limit=500)

        # total=2, so only one page fetched
        assert mock_client.get.call_count == 1
        assert len(chapters) == 2

    async def test_pagination_respects_limit(self):
        """When limit < batch size, only request that many."""
        mock_resp = _make_mock_response(_mock_feed_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            await client.get_chapter_feed("manga-001", limit=1)

        call_args = mock_client.get.call_args
        assert call_args.kwargs["params"]["limit"] == 1

    async def test_pagination_handles_multiple_pages(self):
        """Verify the client fetches multiple pages when total > batch size."""
        # Page 1: 2 items, total=4
        page1 = {
            "data": [
                {"id": "ch-1", "attributes": {"chapter": "1", "translatedLanguage": "en", "pages": 10}},
                {"id": "ch-2", "attributes": {"chapter": "2", "translatedLanguage": "en", "pages": 12}},
            ],
            "total": 4,
        }
        # Page 2: 2 items, total=4
        page2 = {
            "data": [
                {"id": "ch-3", "attributes": {"chapter": "3", "translatedLanguage": "en", "pages": 14}},
                {"id": "ch-4", "attributes": {"chapter": "4", "translatedLanguage": "en", "pages": 16}},
            ],
            "total": 4,
        }

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = _make_mock_response(page1 if call_count == 1 else page2)
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            chapters = await client.get_chapter_feed("manga-001", limit=500)

        assert len(chapters) == 4
        assert call_count == 2
        assert chapters[2].id == "ch-3"


class TestGetChapterImages:
    """Test get_chapter_images with mocked HTTP."""

    async def test_returns_parsed_images(self):
        mock_resp = _make_mock_response(_mock_at_home_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            images = await client.get_chapter_images("ch-1")

        assert images.base_url == "https://cmdxd98sb0x3yprd.mangadex.network"
        assert images.hash == "abcdef123456"
        assert len(images.data) == 3
        assert len(images.data_saver) == 3
        assert images.data[0] == "p1-full.png"
        assert images.data_saver[0] == "p1-saver.jpg"

    async def test_calls_correct_endpoint(self):
        mock_resp = _make_mock_response(_mock_at_home_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            await client.get_chapter_images("chapter-uuid-xyz")

        call_args = mock_client.get.call_args
        assert call_args.args[0] == "https://api.mangadex.org/at-home/server/chapter-uuid-xyz"


class TestDownloadImage:
    """Test download_image with mocked HTTP."""

    async def test_downloads_full_quality(self):
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_resp = _make_mock_response(content=image_bytes)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            result = await client.download_image(
                "https://server.example.com",
                "abcdef",
                "page1.png",
            )

        assert result == image_bytes
        call_args = mock_client.get.call_args
        assert call_args.args[0] == "https://server.example.com/data/abcdef/page1.png"

    async def test_downloads_saver_quality(self):
        mock_resp = _make_mock_response(content=b"jpeg-data")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client):
            client = MangaDexClient()
            await client.download_image(
                "https://server.example.com",
                "abcdef",
                "page1.jpg",
                saver=True,
            )

        call_args = mock_client.get.call_args
        assert call_args.args[0] == "https://server.example.com/data-saver/abcdef/page1.jpg"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimit:
    """Test rate limiting behavior."""

    async def test_rate_limit_delays_when_too_fast(self):
        """Verify _rate_limit introduces a delay when called rapidly."""
        client = MangaDexClient()
        # Simulate a very recent request
        import time

        client._last_request_time = time.monotonic()

        with patch("web_core.adapters.mangadex.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._rate_limit()
            # Should have slept since we just set _last_request_time to now
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args.args[0]
            assert 0 < sleep_duration <= 1.0 / client.RATE_LIMIT_RPS

    async def test_rate_limit_no_delay_when_enough_time_passed(self):
        """No delay needed when enough time has passed since last request."""
        client = MangaDexClient()
        # _last_request_time is 0.0 (epoch), so plenty of time has passed
        with patch("web_core.adapters.mangadex.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._rate_limit()
            mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# SSRF safety -- verify safe_httpx_client is used
# ---------------------------------------------------------------------------


class TestSsrfSafety:
    """Verify the adapter uses safe_httpx_client, not raw httpx.AsyncClient."""

    async def test_get_uses_safe_client(self):
        """The internal _get method must call safe_httpx_client."""
        mock_resp = _make_mock_response({"data": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client) as mock_factory:
            client = MangaDexClient()
            await client._get("/test")
            mock_factory.assert_called_once_with(timeout=30.0)

    async def test_download_uses_safe_client(self):
        """download_image must also use safe_httpx_client."""
        mock_resp = _make_mock_response(content=b"img")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("web_core.adapters.mangadex.safe_httpx_client", return_value=mock_client) as mock_factory:
            client = MangaDexClient()
            await client.download_image("https://s.example.com", "h", "f.png")
            mock_factory.assert_called_once_with(timeout=60.0)
