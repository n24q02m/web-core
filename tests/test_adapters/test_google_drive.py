"""Tests for Google Drive adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
# fetch_folder_chapters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_folder_chapters_invalid_url():
    from web_core.adapters.google_drive import fetch_folder_chapters

    with pytest.raises(ValueError, match="Cannot extract folder ID from URL"):
        await fetch_folder_chapters("https://example.com/not-drive")


@pytest.mark.asyncio
async def test_fetch_folder_chapters_no_files():
    from web_core.adapters.google_drive import fetch_folder_chapters

    with patch("web_core.adapters.google_drive.list_folder_files", return_value=[]), \
         pytest.raises(ValueError, match="No text files found"):
        await fetch_folder_chapters("https://drive.google.com/drive/folders/123")


@pytest.mark.asyncio
async def test_fetch_folder_chapters_success():
    from web_core.adapters.google_drive import DriveFile, fetch_folder_chapters

    files = [DriveFile(file_id="id1", name="chap2.txt"), DriveFile(file_id="id2", name="chap1.txt")]
    with patch("web_core.adapters.google_drive.list_folder_files", return_value=files), \
         patch("web_core.adapters.google_drive.download_text_file", side_effect=["content1", "content2"]):
        chapters = await fetch_folder_chapters("https://drive.google.com/drive/folders/123")

        assert len(chapters) == 2
        # Should be sorted: chap1 then chap2
        assert chapters[0].title == "chap1"
        assert chapters[0].text == "content1"
        assert chapters[0].file_id == "id2"

        assert chapters[1].title == "chap2"
        assert chapters[1].text == "content2"
        assert chapters[1].file_id == "id1"


@pytest.mark.asyncio
async def test_fetch_folder_chapters_download_failure():
    from web_core.adapters.google_drive import DriveFile, fetch_folder_chapters

    files = [DriveFile(file_id="id1", name="chap1.txt")]
    with patch("web_core.adapters.google_drive.list_folder_files", return_value=files), \
         patch("web_core.adapters.google_drive.download_text_file", side_effect=Exception("Download failed")):
        chapters = await fetch_folder_chapters("https://drive.google.com/drive/folders/123")
        assert len(chapters) == 0


# ---------------------------------------------------------------------------
# list_folder_files & _list_folder_via_gdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_folder_files_gdown_success():
    from web_core.adapters.google_drive import list_folder_files

    with patch("web_core.adapters.google_drive._list_folder_via_gdown", return_value=["file1"]):
        res = await list_folder_files("folder123")
        assert res == ["file1"]


@pytest.mark.asyncio
async def test_list_folder_files_gdown_fallback_to_html():
    from web_core.adapters.google_drive import list_folder_files

    with patch("web_core.adapters.google_drive._list_folder_via_gdown", side_effect=Exception("gdown fail")), \
         patch("web_core.adapters.google_drive._list_folder_via_html", return_value=["file2"]):
        res = await list_folder_files("folder123")
        assert res == ["file2"]


@pytest.mark.asyncio
async def test_list_folder_via_gdown_success():
    import sys

    from web_core.adapters.google_drive import _list_folder_via_gdown

    mock_gdown = MagicMock()
    mock_item1 = MagicMock()
    mock_item1.path = "folder/file1.txt"
    mock_item1.id = "id1"

    mock_item2 = MagicMock()
    mock_item2.path = "folder/file2.png"  # not supported ext
    mock_item2.id = "id2"

    mock_gdown.download_folder.return_value = [mock_item1, mock_item2]

    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        files = await _list_folder_via_gdown("123")
        assert len(files) == 1
        assert files[0].file_id == "id1"
        assert files[0].name == "file1.txt"


@pytest.mark.asyncio
async def test_list_folder_via_gdown_empty():
    import sys

    from web_core.adapters.google_drive import _list_folder_via_gdown

    mock_gdown = MagicMock()
    mock_gdown.download_folder.return_value = []

    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        files = await _list_folder_via_gdown("123")
        assert files == []


@pytest.mark.asyncio
async def test_list_folder_via_gdown_import_error():
    import builtins

    from web_core.adapters.google_drive import _list_folder_via_gdown

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "gdown":
            raise ImportError("No module named gdown")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import), \
         pytest.raises(RuntimeError, match="gdown not installed"):
        await _list_folder_via_gdown("123")


# ---------------------------------------------------------------------------
# _list_folder_via_html
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_folder_via_html_success():
    from web_core.adapters.google_drive import _list_folder_via_html

    mock_html = (
        '{"id":"1XYZabcDEF1XYZabcDEF1XYZabcDEF","name":"chapter1.txt"}, "1XYZabcDEF1XYZabcDEF1XYZabcDEF","chapter1.txt"'
    )
    mock_resp = MagicMock()
    mock_resp.text = mock_html
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        files = await _list_folder_via_html("123")
        assert len(files) == 1
        assert files[0].file_id == "1XYZabcDEF1XYZabcDEF1XYZabcDEF"
        assert files[0].name == "chapter1.txt"


@pytest.mark.asyncio
async def test_list_folder_via_html_empty():
    from web_core.adapters.google_drive import _list_folder_via_html

    mock_resp = MagicMock()
    mock_resp.text = "<html>No files here</html>"

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        files = await _list_folder_via_html("123")
        assert len(files) == 0


# ---------------------------------------------------------------------------
# download_text_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_text_file_success(tmp_path):
    import sys

    from web_core.adapters.google_drive import download_text_file

    mock_gdown = MagicMock()

    def mock_download(url, dest, **kwargs):
        with open(dest, "w") as f:
            f.write("test content")
        return dest

    mock_gdown.download.side_effect = mock_download

    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        content = await download_text_file("123")
        assert content == "test content"


@pytest.mark.asyncio
async def test_download_text_file_fail_no_result():
    import sys

    from web_core.adapters.google_drive import download_text_file

    mock_gdown = MagicMock()
    mock_gdown.download.return_value = None

    with patch.dict(sys.modules, {"gdown": mock_gdown}):
        content = await download_text_file("123")
        assert content == ""


@pytest.mark.asyncio
async def test_download_text_file_import_error():
    import builtins

    from web_core.adapters.google_drive import download_text_file

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "gdown":
            raise ImportError("No module named gdown")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import), \
         pytest.raises(RuntimeError, match="gdown not installed"):
        await download_text_file("123")
