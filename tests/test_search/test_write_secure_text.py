from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from web_core.search.runner import _write_secure_text


async def test_write_secure_text_creates_file(tmp_path: Path):
    """Verify that _write_secure_text creates a file with correct content."""
    test_file = tmp_path / "test.txt"
    content = "hello world"

    await _write_secure_text(test_file, content)

    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == content


async def test_write_secure_text_overwrites_file(tmp_path: Path):
    """Verify that _write_secure_text overwrites an existing file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("initial content that is longer than the next one", encoding="utf-8")

    content = "new content"
    await _write_secure_text(test_file, content)

    assert test_file.read_text(encoding="utf-8") == content


@pytest.mark.skipif(sys.platform == "win32", reason="0o600 permissions not applicable on Windows")
async def test_write_secure_text_permissions(tmp_path: Path):
    """Verify that _write_secure_text sets 0o600 permissions on non-Windows platforms."""
    test_file = tmp_path / "secure.txt"
    await _write_secure_text(test_file, "secret")

    mode = os.stat(test_file).st_mode
    # Extract only the permission bits
    assert oct(mode & 0o777) == "0o600"


async def test_write_secure_text_handles_utf8(tmp_path: Path):
    """Verify that _write_secure_text handles UTF-8 characters."""
    test_file = tmp_path / "utf8.txt"
    content = "🔒 secret content 🔑"

    await _write_secure_text(test_file, content)

    assert test_file.read_text(encoding="utf-8") == content
