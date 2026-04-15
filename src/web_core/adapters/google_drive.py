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

logger = logging.getLogger(__name__)

FOLDER_URL_PATTERN = re.compile(r"drive\.google\.com/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]+)")
FILE_URL_PATTERN = re.compile(r"drive\.google\.com/(?:file/d/|open\?id=)([A-Za-z0-9_-]+)")


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


def extract_file_id(url: str) -> str | None:
    """Extract file ID from a Google Drive file URL."""
    match = FILE_URL_PATTERN.search(url)
    return match.group(1) if match else None


async def list_folder_files(folder_id: str) -> list[DriveFile]:
    """List all text/document files in a public Google Drive folder.

    Su dung gdown skip_download=True de list files ma khong download,
    fallback sang HTML parsing neu gdown that bai.
    """
    try:
        return await _list_folder_via_gdown(folder_id)
    except Exception:
        return await _list_folder_via_html(folder_id)


async def _list_folder_via_gdown(folder_id: str) -> list[DriveFile]:
    """Use gdown skip_download=True to list folder files without downloading."""
    try:
        import gdown as gdown_mod
    except ImportError as e:
        raise RuntimeError("gdown not installed.") from e

    url = f"https://drive.google.com/drive/folders/{folder_id}"
    loop = asyncio.get_running_loop()

    _SUPPORTED_EXTS = {".txt", ".epub", ".pdf", ".md", ".html", ".htm", ".docx"}

    def _list_sync() -> list[DriveFile]:
        items = gdown_mod.download_folder(url, skip_download=True, quiet=True, use_cookies=False)
        if not items:
            return []
        files = []
        for item in items:
            # GoogleDriveFileToDownload has .id and .path attributes
            name = item.path.split("/")[-1] if hasattr(item, "path") and item.path else ""
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in _SUPPORTED_EXTS:
                files.append(DriveFile(file_id=item.id, name=name))
        return files

    return await loop.run_in_executor(None, _list_sync)


async def _list_folder_via_html(folder_id: str) -> list[DriveFile]:
    """Parse public Drive folder HTML to extract file metadata."""
    import httpx

    url = f"https://drive.google.com/drive/folders/{folder_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()

    html = resp.text

    # Google Drive HTML contains file IDs and names embedded in script data.
    # Pattern: file ID (28-44 alphanumeric chars) followed by filename with extension.
    files: list[DriveFile] = []
    seen: set[str] = set()

    id_name_pattern = re.compile(r'"([A-Za-z0-9_-]{28,44})","([^"]+\.(txt|epub|pdf|md|html?|docx?))"')
    for m in id_name_pattern.finditer(html):
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
    try:
        import gdown as gdown_mod
    except ImportError as e:
        raise RuntimeError("gdown not installed.") from e

    loop = asyncio.get_running_loop()

    def _download_sync() -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "file.txt")
            dl_url = f"https://drive.google.com/uc?id={file_id}"
            result = gdown_mod.download(dl_url, dest, quiet=True, fuzzy=True)
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

    chapters: list[DriveChapter] = []
    sem = asyncio.Semaphore(5)

    async def _download_with_semaphore(f: DriveFile, idx: int) -> DriveChapter | None:
        async with sem:
            try:
                text = await download_text_file(f.file_id)
                if text.strip():
                    return DriveChapter(
                        title=Path(f.name).stem,
                        text=text,
                        order=idx + 1,
                        file_id=f.file_id,
                    )
            except Exception as e:
                logger.warning("Failed to download Drive file %s (%s): %s", f.name, f.file_id, e)
            return None

    # Bolt: ⚡ Optimize N+1 sequential downloads by running them concurrently with a semaphore bound
    tasks = [_download_with_semaphore(f, i) for i, f in enumerate(files)]
    results = await asyncio.gather(*tasks)

    for res in results:
        if res is not None:
            chapters.append(res)

    return chapters


def _natural_sort_key(s: str) -> list[int | str]:
    """Natural sort key: '2.txt' sorts before '10.txt'."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", s)]
