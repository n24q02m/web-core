"""Google Drive public folder adapter.

Cung cap kha nang tai file tu public Google Drive folder ma khong can OAuth.
Su dung gdown de download file, httpx de list folder contents.

Use case: KnowledgePrism agent doc tieu thuyet/truyen tu folder chia se cong khai.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bs4

from web_core.http import safe_httpx_client

_gdown_mod: Any = None
_gdown_lock: asyncio.Lock | None = None


async def _get_gdown() -> Any:
    """Lazy load gdown module with thread offloading."""
    global _gdown_mod, _gdown_lock
    if _gdown_lock is None:
        _gdown_lock = asyncio.Lock()

    async with _gdown_lock:
        if _gdown_mod is None:
            try:
                import importlib

                _gdown_mod = await asyncio.to_thread(importlib.import_module, "gdown")
            except ImportError as e:
                raise RuntimeError("gdown not installed.") from e
    return _gdown_mod


logger = logging.getLogger(__name__)

FOLDER_URL_PATTERN = re.compile(r"drive\.google\.com/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]+)")
_ID_NAME_RE = re.compile(r'"([A-Za-z0-9_-]{28,44})","([^"]+\.(txt|epub|pdf|md|html?|docx?))"')
_NATURAL_SORT_RE = re.compile(r"(\d+)")
_SUPPORTED_EXTS = {".txt", ".epub", ".pdf", ".md", ".html", ".htm", ".docx"}


@dataclass
class DriveFile:
    """Metadata for a single file in a Google Drive folder."""

    file_id: str
    name: str
    mime_type: str = "text/plain"


@dataclass
class DriveChapter:
    """A downloaded Drive file as a chapter."""

    title: str
    text: str
    order: int
    file_id: str = ""


def extract_folder_id(url: str) -> str | None:
    """Extract folder ID from a Google Drive folder URL."""
    match = FOLDER_URL_PATTERN.search(url)
    return match.group(1) if match else None


async def list_folder_files(folder_id: str) -> list[DriveFile]:
    """List all text/document files in a public Google Drive folder.

    Su dung async embedded view de list files,
    fallback sang HTML parsing neu that bai.
    """
    try:
        return await _list_folder_via_gdown(folder_id)
    except Exception as e:
        logger.debug("Async folder list failed, falling back to HTML: %s", e)
        return await _list_folder_via_html(folder_id)


async def _list_folder_via_gdown(folder_id: str) -> list[DriveFile]:
    """Use Google Drive embedded view to list folder files recursively.

    This replaces the previous implementation that used gdown.download_folder
    in a thread executor, providing a more efficient async alternative.
    """
    sem = asyncio.Semaphore(5)  # Limit concurrent subfolder fetches
    return await _list_folder_recursive(folder_id, sem)


async def _list_folder_recursive(folder_id: str, semaphore: asyncio.Semaphore) -> list[DriveFile]:
    """Recursively list files in a Google Drive folder using the embedded view."""
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with semaphore, safe_httpx_client(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return []
        html = resp.text

    soup = bs4.BeautifulSoup(html, "html.parser")
    files: list[DriveFile] = []
    subfolder_ids: list[str] = []

    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "")
        if not isinstance(href, str) or not href:
            continue

        # File links
        file_match = re.search(r"drive\.google\.com/file/d/([-\w]{25,})", href)
        if file_match:
            file_id = file_match.group(1)
            name = a_tag.get_text(strip=True)
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in _SUPPORTED_EXTS:
                files.append(DriveFile(file_id=file_id, name=name))
            continue

        # Doc links (Google native)
        docs_match = re.search(r"docs\.google\.com/\w+/d/([-\w]{25,})", href)
        if docs_match:
            file_id = docs_match.group(1)
            name = a_tag.get_text(strip=True)
            files.append(DriveFile(file_id=file_id, name=name))
            continue

        # Subfolder links
        folder_match = re.search(r"drive\.google\.com/drive/folders/([-\w]{25,})", href)
        if folder_match:
            subfolder_ids.append(folder_match.group(1))

    if subfolder_ids:
        # Deduplicate subfolder IDs to avoid infinite loops or redundant work
        subfolder_ids = list(dict.fromkeys(subfolder_ids))
        tasks = [_list_folder_recursive(fid, semaphore) for fid in subfolder_ids]
        subfolder_results = await asyncio.gather(*tasks)
        for res in subfolder_results:
            files.extend(res)

    return files


async def _list_folder_via_html(folder_id: str) -> list[DriveFile]:
    """Parse public Drive folder HTML to extract file metadata."""

    url = f"https://drive.google.com/drive/folders/{folder_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with safe_httpx_client(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()

    html = resp.text

    # Google Drive HTML contains file IDs and names embedded in script data.
    # Pattern: file ID (28-44 alphanumeric chars) followed by filename with extension.
    files: list[DriveFile] = []
    seen: set[str] = set()

    for m in _ID_NAME_RE.finditer(html):
        file_id, name = m.group(1), m.group(2)
        if file_id not in seen:
            seen.add(file_id)
            files.append(DriveFile(file_id=file_id, name=name))

    if not files:
        logger.warning(
            "No files found via HTML pattern for folder %s. Page may require JavaScript rendering.",
            folder_id,
        )

    return files


async def download_text_file(file_id: str) -> str:
    """Download a text file from Google Drive by its file ID.

    Su dung gdown de download file text tu Google Drive public.
    """
    gdown_mod = await _get_gdown()

    loop = asyncio.get_running_loop()

    def _download_sync() -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "file.txt")
            dl_url = f"https://drive.google.com/uc?id={file_id}"
            result = gdown_mod.download(dl_url, dest, quiet=True)
            if result and os.path.exists(result):
                return Path(result).read_text(encoding="utf-8", errors="replace")
            return ""

    return await loop.run_in_executor(None, _download_sync)


async def fetch_folder_chapters(
    folder_url: str,
    max_chapters: int = 50,
) -> list[DriveChapter]:
    """Fetch all text files in a public Drive folder as ordered chapters.

    Tra ve list DriveChapter sorted theo ten file (natural sort theo so).
    """
    folder_id = extract_folder_id(folder_url)
    if not folder_id:
        raise ValueError(f"Cannot extract folder ID from URL: {folder_url}")

    files = await list_folder_files(folder_id)
    if not files:
        raise ValueError(f"No text files found in Drive folder {folder_id}")

    # Sort by filename using natural sort (chapter-2 < chapter-10)
    files.sort(key=lambda f: _natural_sort_key(f.name))
    files = files[:max_chapters]

    # Performance Optimization: Parallelize chapter downloads
    # By using a semaphore and asyncio.TaskGroup, we reduce latency from O(N) to roughly O(1)
    # for typical folder sizes, without triggering rate limits from concurrent connections.
    sem = asyncio.Semaphore(10)
    results: list[DriveChapter | None] = [None] * len(files)

    async def _download_chapter(i: int, f: DriveFile) -> None:
        async with sem:
            try:
                text = await download_text_file(f.file_id)
                if text.strip():
                    results[i] = DriveChapter(
                        title=Path(f.name).stem,
                        text=text,
                        order=i + 1,
                        file_id=f.file_id,
                    )
            except Exception as e:
                # Security: Sanitize log by using type(e).__name__ to avoid leaking sensitive data
                logger.warning(
                    "Failed to download Drive file %s (%s): %s",
                    f.name,
                    f.file_id,
                    type(e).__name__,
                )

    async with asyncio.TaskGroup() as tg:
        for i, f in enumerate(files):
            tg.create_task(_download_chapter(i, f))

    return [res for res in results if res is not None]


def _natural_sort_key(s: str) -> list[int | str]:
    """Natural sort key: '2.txt' sorts before '10.txt'."""
    return [int(c) if c.isdigit() else c.lower() for c in _NATURAL_SORT_RE.split(s)]
