"""Google Drive public folder adapter.

Cung cap kha nang tai file tu public Google Drive folder ma khong can OAuth.
Su dung gdown de list files va download content.

Use case: KnowledgePrism agent doc tieu thuyet/truyen tu folder chia se cong khai.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

FOLDER_URL_PATTERN = re.compile(
    r"drive\.google\.com/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]+)"
)
FILE_URL_PATTERN = re.compile(
    r"drive\.google\.com/(?:file/d/|open\?id=)([A-Za-z0-9_-]+)"
)
# MIME types considered as plain text content
_TEXT_MIME_TYPES = {
    "text/plain",
    "application/vnd.google-apps.document",
}


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
    """List all text files in a public Google Drive folder.

    Su dung gdown de lay danh sach file tu folder cong khai. Chi lay file text
    (khong lay folder con, file anh, v.v.).
    """
    try:
        import gdown
    except ImportError:
        raise RuntimeError("gdown not installed. Install web-core with gdown dependency.")

    url = f"https://drive.google.com/drive/folders/{folder_id}"

    # gdown.download_folder raises on private folders
    # We use its internal listing API via asyncio executor to avoid blocking
    loop = asyncio.get_running_loop()

    def _list_sync() -> list[dict]:
        # gdown does not have a public list API — use internal helper
        # gdrive_url_type returns metadata about the folder contents
        from gdown import download_folder
        import io
        import sys

        # Suppress gdown output
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        try:
            # Use dry_run to just get file list without downloading
            files_info = []
            try:
                result = download_folder(url, quiet=True, use_cookies=False, remaining_ok=True)  # type: ignore[call-arg]
                # result is None on dry_run, but may raise on failure
            except Exception:
                pass
        finally:
            sys.stdout = old_stdout

        return files_info

    # Since gdown.download_folder doesn't have a list-only mode in v5,
    # we use the raw Drive export endpoint to fetch folder HTML and parse it
    return await _list_folder_via_html(folder_id)


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

    # Drive embeds file data as JSON in script tags
    # Pattern: file ID appears as a 33-char alphanumeric string near file names
    # Extract pairs of (file_id, filename) from the embedded data
    files: list[DriveFile] = []
    seen: set[str] = set()

    # Google Drive HTML contains lines like: "1abc...xyz","filename.txt"
    # File IDs are 28-44 chars, alphanumeric + underscores + hyphens
    id_name_pattern = re.compile(
        r'"([A-Za-z0-9_-]{28,44})","([^"]+\.(txt|epub|pdf|md|html?|docx?))"'
    )
    for m in id_name_pattern.finditer(html):
        file_id, name = m.group(1), m.group(2)
        if file_id not in seen:
            seen.add(file_id)
            files.append(DriveFile(file_id=file_id, name=name))

    if not files:
        # Fallback: look for any file IDs with known extensions near them
        logger.warning("No files found via HTML pattern for folder %s. HTML may be JS-rendered.", folder_id)

    return files


async def download_text_file(file_id: str) -> str:
    """Download a text file from Google Drive by its file ID.

    Su dung gdown de download file text tu Google Drive.
    """
    try:
        import gdown
    except ImportError:
        raise RuntimeError("gdown not installed.")

    loop = asyncio.get_running_loop()

    def _download_sync() -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "file.txt")
            url = f"https://drive.google.com/uc?id={file_id}"
            result = gdown.download(url, dest, quiet=True, fuzzy=True)
            if result and os.path.exists(result):
                return Path(result).read_text(encoding="utf-8", errors="replace")
            return ""

    return await loop.run_in_executor(None, _download_sync)


async def fetch_folder_chapters(
    folder_url: str,
    max_chapters: int = 50,
) -> list[DriveChapter]:
    """Fetch all text files in a public Drive folder as ordered chapters.

    Tra ve list DriveChapter sorted theo ten file (so thu tu trong ten file).
    """
    folder_id = extract_folder_id(folder_url)
    if not folder_id:
        raise ValueError(f"Cannot extract folder ID from URL: {folder_url}")

    files = await list_folder_files(folder_id)
    if not files:
        raise ValueError(f"No text files found in Drive folder {folder_id}")

    # Sort by filename (chapter 01, 02, ... or natural sort)
    files.sort(key=lambda f: _natural_sort_key(f.name))
    files = files[:max_chapters]

    chapters: list[DriveChapter] = []
    for i, f in enumerate(files):
        try:
            text = await download_text_file(f.file_id)
            if text.strip():
                chapters.append(
                    DriveChapter(
                        title=Path(f.name).stem,
                        text=text,
                        order=i + 1,
                        file_id=f.file_id,
                    )
                )
        except Exception as e:
            logger.warning("Failed to download Drive file %s (%s): %s", f.name, f.file_id, e)

    return chapters


def _natural_sort_key(s: str) -> list[int | str]:
    """Natural sort: '2.txt' < '10.txt'."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", s)]
