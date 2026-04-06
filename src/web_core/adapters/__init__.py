"""External API adapters with SSRF-safe HTTP, rate limiting, and typed models."""

from web_core.adapters.google_drive import DriveChapter, DriveFile, fetch_folder_chapters
from web_core.adapters.mangadex import ChapterImages, ChapterInfo, MangaDexClient, MangaInfo

__all__ = [
    "ChapterImages",
    "ChapterInfo",
    "DriveChapter",
    "DriveFile",
    "MangaDexClient",
    "MangaInfo",
    "fetch_folder_chapters",
]
