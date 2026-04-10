"""Tests for Google Drive adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from web_core.adapters.google_drive import (
    DriveChapter,
    DriveFile,
    _list_folder_via_gdown,
    _list_folder_via_html,
    _natural_sort_key,
    download_text_file,
    extract_file_id,
    extract_folder_id,
    fetch_folder_chapters,
    list_folder_files,
)

# ---------------------------------------------------------------------------
# extract_folder_id
# ---------------------------------------------------------------------------


def test_extract_folder_id_standard():
    url = "https://drive.google.com/drive/folders/1Dm3nwjlzMB0166LwVO0vQhsGRArecuWd"
    assert extract_folder_id(url) == "1Dm3nwjlzMB0166LwVO0vQhsGRArecuWd"


def test_extract_folder_id_with_user():
    url = "https://drive.google.com/drive/u/0/folders/1Abc123XYZ"
    assert extract_folder_id(url) == "1Abc123XYZ"


def test_extract_folder_id_none_for_non_drive():
    assert extract_folder_id("https://docs.google.com/document/d/abc") is None


def test_extract_folder_id_none_for_file():
    assert extract_folder_id("https://drive.google.com/file/d/1abc/view") is None


# ---------------------------------------------------------------------------
# extract_file_id
# ---------------------------------------------------------------------------


def test_extract_file_id_standard():
    url = "https://drive.google.com/file/d/1XYZabcDEF/view"
    assert extract_file_id(url) == "1XYZabcDEF"


def test_extract_file_id_open():
    url = "https://drive.google.com/open?id=1XYZabcDEF"
    assert extract_file_id(url) == "1XYZabcDEF"


def test_extract_file_id_none_for_folder():
    assert extract_file_id("https://drive.google.com/drive/folders/1abc") is None


# ---------------------------------------------------------------------------
# _natural_sort_key
# ---------------------------------------------------------------------------


def test_natural_sort_numeric():
    files = ["chapter-10.txt", "chapter-2.txt", "chapter-1.txt"]
    sorted_files = sorted(files, key=_natural_sort_key)
    assert sorted_files == ["chapter-1.txt", "chapter-2.txt", "chapter-10.txt"]


def test_natural_sort_mixed():
    files = ["Chap 3.txt", "Chap 10.txt", "Chap 1.txt"]
    sorted_files = sorted(files, key=_natural_sort_key)
    assert sorted_files == ["Chap 1.txt", "Chap 3.txt", "Chap 10.txt"]


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
async def test_list_folder_via_gdown_success():
    """list_folder_via_gdown returns DriveFile list from gdown output."""
    mock_item_1 = MagicMock()
    mock_item_1.id = "file_id_1"
    mock_item_1.path = "folder/chapter-1.txt"

    mock_item_2 = MagicMock()
    mock_item_2.id = "file_id_2"
    mock_item_2.path = "folder/chapter-2.epub"

    mock_item_3 = MagicMock()
    mock_item_3.id = "file_id_3"
    mock_item_3.path = "folder/image.png"  # Unsupported ext

    mock_gdown = MagicMock()
    mock_gdown.download_folder.return_value = [mock_item_1, mock_item_2, mock_item_3]

    with patch("web_core.adapters.google_drive.gdown", mock_gdown):
        result = await _list_folder_via_gdown("test_folder_id")

    assert len(result) == 2  # .png filtered out
    assert result[0].file_id == "file_id_1"
    assert result[0].name == "chapter-1.txt"
    assert result[1].file_id == "file_id_2"


async def test_list_folder_via_gdown_empty():
    """list_folder_via_gdown returns empty list when gdown returns None."""
    mock_gdown = MagicMock()
    mock_gdown.download_folder.return_value = None

    with patch("web_core.adapters.google_drive.gdown", mock_gdown):
        result = await _list_folder_via_gdown("empty_folder")

    assert result == []


async def test_list_folder_via_gdown_no_path():
    """list_folder_via_gdown handles items without path attribute."""
    mock_item = MagicMock()
    mock_item.id = "file_id"
    mock_item.path = ""

    mock_gdown = MagicMock()
    mock_gdown.download_folder.return_value = [mock_item]

    with patch("web_core.adapters.google_drive.gdown", mock_gdown):
        result = await _list_folder_via_gdown("test_folder")

    assert result == []  # Empty name, no extension match


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
    import os
    import tempfile

    # Create a temp file to simulate gdown download
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Chapter 1 content here")
        temp_path = f.name

    try:
        mock_gdown = MagicMock()
        mock_gdown.download.return_value = temp_path

        with patch("web_core.adapters.google_drive.gdown", mock_gdown):
            result = await download_text_file("test_file_id")

        assert "Chapter 1 content" in result
    finally:
        os.unlink(temp_path)


async def test_download_text_file_returns_empty_on_failure():
    """download_text_file returns empty string when gdown fails."""
    mock_gdown = MagicMock()
    mock_gdown.download.return_value = None

    with patch("web_core.adapters.google_drive.gdown", mock_gdown):
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
    import pytest

    with pytest.raises(ValueError, match="Cannot extract folder ID"):
        await fetch_folder_chapters("https://example.com/not-a-drive-url")


async def test_fetch_folder_chapters_no_files():
    """fetch_folder_chapters raises ValueError when folder is empty."""
    import pytest

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
