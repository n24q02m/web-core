"""Tests for Google Drive adapter."""

from __future__ import annotations

import pytest

from web_core.adapters.google_drive import (
    DriveChapter,
    DriveFile,
    extract_file_id,
    extract_folder_id,
    _natural_sort_key,
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
