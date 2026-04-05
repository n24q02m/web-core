"""External API adapters with SSRF-safe HTTP, rate limiting, and typed models."""

from web_core.adapters.mangadex import ChapterImages, ChapterInfo, MangaDexClient, MangaInfo

__all__ = [
    "ChapterImages",
    "ChapterInfo",
    "MangaDexClient",
    "MangaInfo",
]
