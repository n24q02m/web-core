import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.adapters.google_drive import (
    DriveChapter,
    DriveFile,
    _list_folder_via_gdown,
    _list_folder_via_html,
    download_text_file,
    fetch_folder_chapters,
    list_folder_files,
)

# ---------------------------------------------------------------------------
# DriveFile / DriveChapter dataclasses
# ---------------------------------------------------------------------------


def test_drive_file_defaults():
    f = DriveFile(file_id="abc123", name="chapter-01.txt")
    assert f.mime_type == "text/plain"


def test_drive_chapter_fields():
    ch = DriveChapter(title="Chapter 1", text="Hello world", order=1, file_id="abc")
    assert ch.order == 1
    assert ch.text == "Hello world"


# ---------------------------------------------------------------------------
# Async tests (mocked I/O)


@pytest.fixture(autouse=True)
def reset_gdown_cache():
    """Reset the lazy-loaded gdown module cache before each test."""
    import web_core.adapters.google_drive as gd

    gd._gdown_mod = None
    yield
    gd._gdown_mod = None


async def test_list_folder_via_gdown_success():
    """list_folder_via_gdown returns DriveFile list from mocked embedded view."""
    html = """<html>
    <a href="https://drive.google.com/file/d/1Dm3nwjlzMB0166LwVO0vQhsGRArecuWd/view">chapter-1.txt</a>
    <a href="https://drive.google.com/file/d/2XyZ_AbcDefGhiJklMnOpQrStUvWxYz01/view">chapter-2.epub</a>
    <a href="https://drive.google.com/file/d/3Image_AbcDefGhiJklMnOpQrStUvWxYz01/view">image.png</a>
    </html>"""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_gdown("test_folder_id")

    assert len(result) == 2
    assert result[0].file_id == "1Dm3nwjlzMB0166LwVO0vQhsGRArecuWd"
    assert result[0].name == "chapter-1.txt"
    assert result[1].file_id == "2XyZ_AbcDefGhiJklMnOpQrStUvWxYz01"


async def test_list_folder_via_gdown_empty():
    """list_folder_via_gdown returns empty list when response is not 200."""
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_gdown("empty_folder")

    assert result == []


async def test_list_folder_via_html_parses_ids():
    """list_folder_via_html extracts file IDs from HTML."""
    html = """<html>
    <script>
    data = [
        ["1Dm3nwjlzMB0166LwVO0vQhsGRArecuWd","chapter-1.txt"],
        ["2XyZ_AbcDefGhiJklMnOpQrStUvWxYz01","chapter-2.epub"]
    ]
    </script>
    </html>"""

    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_html("test_folder_id")

    assert len(result) == 2
    assert result[0].name == "chapter-1.txt"


async def test_list_folder_via_html_no_files(caplog):
    """list_folder_via_html logs warning when no files found."""
    mock_response = MagicMock()
    mock_response.text = "<html><body>Empty</body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_html("empty_folder")

    assert result == []


async def test_list_folder_files_fallback_to_html():
    """list_folder_files falls back to HTML parsing when gdown fails."""
    with (
        patch(
            "web_core.adapters.google_drive._list_folder_via_gdown",
            side_effect=RuntimeError("gdown failed"),
        ),
        patch(
            "web_core.adapters.google_drive._list_folder_via_html",
            return_value=[DriveFile(file_id="f1", name="ch1.txt")],
        ) as mock_html,
    ):
        result = await list_folder_files("folder_id")

    mock_html.assert_called_once_with("folder_id")
    assert len(result) == 1


async def test_download_text_file_success():
    """download_text_file returns file content via gdown."""

    # Create a temp file to simulate gdown download
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Chapter 1 content here")
        temp_path = f.name

    try:
        mock_gdown = MagicMock()
        mock_gdown.download.return_value = temp_path

        with patch.dict("sys.modules", {"gdown": mock_gdown}):
            result = await download_text_file("test_file_id")

        assert "Chapter 1 content" in result
    finally:
        os.unlink(temp_path)


async def test_download_text_file_returns_empty_on_failure():
    """download_text_file returns empty string when gdown fails."""
    mock_gdown = MagicMock()
    mock_gdown.download.return_value = None

    with patch.dict("sys.modules", {"gdown": mock_gdown}):
        result = await download_text_file("bad_file_id")

    assert result == ""


async def test_fetch_folder_chapters_success():
    """fetch_folder_chapters returns sorted chapters."""
    files = [
        DriveFile(file_id="f2", name="chapter-2.txt"),
        DriveFile(file_id="f1", name="chapter-1.txt"),
    ]

    with (
        patch("web_core.adapters.google_drive.list_folder_files", return_value=files),
        patch(
            "web_core.adapters.google_drive.download_text_file",
            side_effect=["Content of chapter 1", "Content of chapter 2"],
        ),
    ):
        chapters = await fetch_folder_chapters("https://drive.google.com/drive/folders/1Abc123XYZ")

    assert len(chapters) == 2
    assert chapters[0].title == "chapter-1"
    assert chapters[0].order == 1
    assert chapters[1].title == "chapter-2"
    assert chapters[1].order == 2


async def test_fetch_folder_chapters_invalid_url():
    """fetch_folder_chapters raises ValueError for non-Drive URL."""

    with pytest.raises(ValueError, match="Cannot extract folder ID"):
        await fetch_folder_chapters("https://example.com/not-a-drive-url")


async def test_fetch_folder_chapters_no_files():
    """fetch_folder_chapters raises ValueError when folder is empty."""

    with (
        patch("web_core.adapters.google_drive.list_folder_files", return_value=[]),
        pytest.raises(ValueError, match="No text files found"),
    ):
        await fetch_folder_chapters("https://drive.google.com/drive/folders/1Abc123XYZ")


async def test_fetch_folder_chapters_skips_empty_content():
    """fetch_folder_chapters skips files with empty content."""
    files = [DriveFile(file_id="f1", name="ch1.txt"), DriveFile(file_id="f2", name="ch2.txt")]

    with (
        patch("web_core.adapters.google_drive.list_folder_files", return_value=files),
        patch(
            "web_core.adapters.google_drive.download_text_file",
            side_effect=["Content here", "   "],
        ),
    ):
        chapters = await fetch_folder_chapters("https://drive.google.com/drive/folders/1Abc123XYZ")

    assert len(chapters) == 1


async def test_fetch_folder_chapters_handles_download_error():
    """fetch_folder_chapters handles download errors gracefully."""
    files = [DriveFile(file_id="f1", name="ch1.txt"), DriveFile(file_id="f2", name="ch2.txt")]

    with (
        patch("web_core.adapters.google_drive.list_folder_files", return_value=files),
        patch(
            "web_core.adapters.google_drive.download_text_file",
            side_effect=[RuntimeError("network error"), "Valid content"],
        ),
    ):
        chapters = await fetch_folder_chapters("https://drive.google.com/drive/folders/1Abc123XYZ")

    assert len(chapters) == 1
    assert chapters[0].title == "ch2"


async def test_fetch_folder_chapters_max_chapters():
    """fetch_folder_chapters respects max_chapters limit."""
    files = [DriveFile(file_id=f"f{i}", name=f"ch{i}.txt") for i in range(10)]

    with (
        patch("web_core.adapters.google_drive.list_folder_files", return_value=files),
        patch(
            "web_core.adapters.google_drive.download_text_file",
            return_value="Content",
        ),
    ):
        chapters = await fetch_folder_chapters(
            "https://drive.google.com/drive/folders/1Abc123XYZ",
            max_chapters=3,
        )

    assert len(chapters) == 3


async def test_fetch_folder_chapters_is_concurrent():
    """Verify that fetch_folder_chapters downloads files concurrently."""

    files = [
        DriveFile(file_id="f1", name="ch1.txt"),
        DriveFile(file_id="f2", name="ch2.txt"),
        DriveFile(file_id="f3", name="ch3.txt"),
    ]

    async def slow_download(file_id):
        await asyncio.sleep(0.1)
        return f"Content of {file_id}"

    with (
        patch("web_core.adapters.google_drive.list_folder_files", return_value=files),
        patch("web_core.adapters.google_drive.download_text_file", side_effect=slow_download),
    ):
        start_time = asyncio.get_event_loop().time()
        chapters = await fetch_folder_chapters("https://drive.google.com/drive/folders/1Abc123XYZ")
        end_time = asyncio.get_event_loop().time()

    duration = end_time - start_time
    assert len(chapters) == 3
    # If sequential, it would take at least 0.3s. If concurrent, ~0.1s.
    assert duration < 0.2


async def test_list_folder_recursive_with_subfolders():
    """Verify that _list_folder_recursive correctly handles subfolders."""
    from web_core.adapters.google_drive import _list_folder_recursive

    # Root folder HTML with one file and one subfolder
    root_html = """<html>
    <a href="https://drive.google.com/file/d/file_root_AbcDefGhiJklMnOpQrStUvWxYz01/view">root.txt</a>
    <a href="https://drive.google.com/drive/folders/subfolder_id_AbcDefGhiJklMnOpQrStUvWxYz01">Subfolder</a>
    </html>"""

    # Subfolder HTML with one file
    sub_html = """<html>
    <a href="https://drive.google.com/file/d/file_sub_AbcDefGhiJklMnOpQrStUvWxYz01/view">sub.txt</a>
    </html>"""

    mock_resp_root = MagicMock()
    mock_resp_root.status_code = 200
    mock_resp_root.text = root_html

    mock_resp_sub = MagicMock()
    mock_resp_sub.status_code = 200
    mock_resp_sub.text = sub_html

    mock_client = AsyncMock()
    # First call for root, second for subfolder
    mock_client.get = AsyncMock(side_effect=[mock_resp_root, mock_resp_sub])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    sem = asyncio.Semaphore(1)
    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_recursive("root_id_AbcDefGhiJklMnOpQrStUvWxYz01", sem)

    assert len(result) == 2
    ids = [f.file_id for f in result]
    assert "file_root_AbcDefGhiJklMnOpQrStUvWxYz01" in ids
    assert "file_sub_AbcDefGhiJklMnOpQrStUvWxYz01" in ids
    names = [f.name for f in result]
    assert "root.txt" in names
    assert "sub.txt" in names
