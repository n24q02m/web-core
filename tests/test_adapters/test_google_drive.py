"""Tests for Google Drive adapter."""

from __future__ import annotations

from web_core.adapters.google_drive import (
    DriveChapter,
    DriveFile,
    _natural_sort_key,
    extract_file_id,
    extract_folder_id,
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
# list_folder_files & helpers
# ---------------------------------------------------------------------------

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_list_folder_via_gdown_success():
    """Test successful folder listing via gdown."""
    import web_core.adapters.google_drive
    import sys

    mock_item1 = MagicMock()
    mock_item1.id = "id1"
    mock_item1.path = "/folder/file.txt"

    mock_item2 = MagicMock()
    mock_item2.id = "id2"
    mock_item2.path = "/folder/image.png" # Should be filtered out

    mock_gdown = MagicMock()
    mock_gdown.download_folder.return_value = [mock_item1, mock_item2]

    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        files = await web_core.adapters.google_drive._list_folder_via_gdown("folder_id")
        assert len(files) == 1
        assert files[0].file_id == "id1"
        assert files[0].name == "file.txt"

@pytest.mark.asyncio
async def test_list_folder_via_gdown_empty():
    """Test gdown returning empty list."""
    import web_core.adapters.google_drive
    import sys
    mock_gdown = MagicMock()
    mock_gdown.download_folder.return_value = []
    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        files = await web_core.adapters.google_drive._list_folder_via_gdown("folder_id")
        assert len(files) == 0

@pytest.mark.asyncio
async def test_list_folder_via_html_success():
    """Test successful folder listing via HTML regex parsing."""
    import web_core.adapters.google_drive
    import sys
    html_content = 'some string "123456789012345678901234567890abc","document.txt" other string "223456789012345678901234567890def","story.epub"'

    mock_resp = MagicMock()
    mock_resp.text = html_content
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_httpx = MagicMock()
    mock_httpx.AsyncClient.return_value = mock_client

    with patch.dict(sys.modules, {"httpx": mock_httpx}):
        files = await web_core.adapters.google_drive._list_folder_via_html("folder_id")
        assert len(files) == 2
        assert files[0].file_id == "123456789012345678901234567890abc"
        assert files[0].name == "document.txt"
        assert files[1].file_id == "223456789012345678901234567890def"
        assert files[1].name == "story.epub"

@pytest.mark.asyncio
async def test_list_folder_fallback_flow():
    """Test list_folder_files falls back to HTML when gdown fails."""
    import web_core.adapters.google_drive
    # Mock _list_folder_via_gdown to raise an exception
    with patch("web_core.adapters.google_drive._list_folder_via_gdown", side_effect=Exception("gdown error")):
        with patch("web_core.adapters.google_drive._list_folder_via_html", return_value=[DriveFile("id", "fallback.txt")]) as mock_html:
            files = await web_core.adapters.google_drive.list_folder_files("folder_id")
            assert len(files) == 1
            assert files[0].name == "fallback.txt"
            mock_html.assert_called_once_with("folder_id")


# ---------------------------------------------------------------------------
# download_text_file
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_text_file_success(tmp_path):
    """Test successful file download via gdown."""
    import web_core.adapters.google_drive
    import sys
    test_content = "This is a test file."

    def mock_gdown_download(url, dest, **kwargs):
        with open(dest, "w", encoding="utf-8") as f:
            f.write(test_content)
        return dest

    mock_gdown = MagicMock()
    mock_gdown.download.side_effect = mock_gdown_download

    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        content = await web_core.adapters.google_drive.download_text_file("file_id")
        assert content == test_content

@pytest.mark.asyncio
async def test_download_text_file_failure():
    """Test file download failure via gdown."""
    import web_core.adapters.google_drive
    import sys

    mock_gdown = MagicMock()
    mock_gdown.download.return_value = None
    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        content = await web_core.adapters.google_drive.download_text_file("file_id")
        assert content == ""


# ---------------------------------------------------------------------------
# fetch_folder_chapters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_folder_chapters_success():
    """Test full flow of fetching chapters."""
    import web_core.adapters.google_drive
    mock_files = [
        DriveFile(file_id="id10", name="chapter-10.txt"),
        DriveFile(file_id="id2", name="chapter-2.txt"),
    ]

    with patch("web_core.adapters.google_drive.extract_folder_id", return_value="folder_id"):
        with patch("web_core.adapters.google_drive.list_folder_files", return_value=mock_files):
            # Mock download to return varying content based on ID
            async def mock_download(file_id):
                if file_id == "id2": return "Content 2"
                if file_id == "id10": return "Content 10"
                return ""

            with patch("web_core.adapters.google_drive.download_text_file", side_effect=mock_download):
                chapters = await web_core.adapters.google_drive.fetch_folder_chapters("https://drive.google.com/url")

                assert len(chapters) == 2
                # Check sorting
                assert chapters[0].title == "chapter-2"
                assert chapters[0].text == "Content 2"
                assert chapters[0].order == 1

                assert chapters[1].title == "chapter-10"
                assert chapters[1].text == "Content 10"
                assert chapters[1].order == 2

@pytest.mark.asyncio
async def test_fetch_folder_chapters_invalid_url():
    """Test error when folder ID cannot be extracted."""
    import web_core.adapters.google_drive
    with patch("web_core.adapters.google_drive.extract_folder_id", return_value=None):
        import pytest
        with pytest.raises(ValueError, match="Cannot extract folder ID"):
            await web_core.adapters.google_drive.fetch_folder_chapters("invalid_url")

@pytest.mark.asyncio
async def test_fetch_folder_chapters_empty_folder():
    """Test error when no text files are found."""
    import web_core.adapters.google_drive
    with patch("web_core.adapters.google_drive.extract_folder_id", return_value="folder_id"):
        with patch("web_core.adapters.google_drive.list_folder_files", return_value=[]):
            with pytest.raises(ValueError, match="No text files found"):
                await web_core.adapters.google_drive.fetch_folder_chapters("https://drive.google.com/url")
