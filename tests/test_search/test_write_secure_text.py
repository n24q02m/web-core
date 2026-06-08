import sys

from web_core.search.runner import _write_secure_text


def test_write_secure_text_basic(tmp_path):
    """Test that _write_secure_text correctly writes content."""
    test_file = tmp_path / "test.txt"
    content = "hello world"
    _write_secure_text(test_file, content)

    assert test_file.read_text(encoding="utf-8") == content

    if sys.platform != "win32":
        # Check permissions (0o600)
        assert (test_file.stat().st_mode & 0o777) == 0o600


def test_write_secure_text_overwrites(tmp_path):
    """Test that _write_secure_text overwrites existing content."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("old content")

    new_content = "new content"
    _write_secure_text(test_file, new_content)

    assert test_file.read_text(encoding="utf-8") == new_content


def test_write_secure_text_unicode(tmp_path):
    """Test that _write_secure_text handles unicode content."""
    test_file = tmp_path / "test.txt"
    content = "🔥 unicode test 🔥"
    _write_secure_text(test_file, content)

    assert test_file.read_text(encoding="utf-8") == content
