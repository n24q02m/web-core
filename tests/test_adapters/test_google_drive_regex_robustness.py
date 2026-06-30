import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.adapters.google_drive import _list_folder_via_html


@pytest.mark.asyncio
async def test_list_folder_via_html_boundary_ids():
    """Test _list_folder_via_html with ID lengths at boundaries (28-44)."""

    id27 = "A" * 27
    id28 = "B" * 28
    id44 = "C" * 44
    id45 = "D" * 45

    html = f'["{id27}","too_short.txt"],["{id28}","min.txt"],["{id44}","max.txt"],["{id45}","too_long.txt"]'

    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_html("test_folder_id")

    # Should match 28 and 44, skip 27 and 45
    assert len(result) == 2
    ids = [f.file_id for f in result]
    assert id28 in ids
    assert id44 in ids
    assert id27 not in ids
    assert id45 not in ids


@pytest.mark.asyncio
async def test_list_folder_via_html_all_extensions():
    """Test _list_folder_via_html with all supported extensions."""

    extensions = ["txt", "epub", "pdf", "md", "html", "htm", "docx", "doc"]
    id_base = "A" * 32

    html_parts = []
    for i, ext in enumerate(extensions):
        # Use different IDs to avoid deduplication
        file_id = id_base[:-2] + f"{i:02d}"
        html_parts.append(f'["{file_id}","file.{ext}"]')

    # Add an unsupported one
    html_parts.append(f'["{"E" * 32}","image.png"]')

    html = ",".join(html_parts)

    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_html("test_folder_id")

    assert len(result) == len(extensions)
    names = [f.name for f in result]
    for ext in extensions:
        assert f"file.{ext}" in names
    assert "image.png" not in names


@pytest.mark.asyncio
async def test_list_folder_via_html_complex_filenames():
    """Test _list_folder_via_html with complex filenames."""

    id1, id2, id3 = "1" * 32, "2" * 32, "3" * 32
    html = f'["{id1}","Chapter 1 - The Beginning.txt"],["{id2}","my.report.v2.pdf"],["{id3}","file(1).md"]'

    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_html("test_folder_id")

    assert len(result) == 3
    names = [f.name for f in result]
    assert "Chapter 1 - The Beginning.txt" in names
    assert "my.report.v2.pdf" in names
    assert "file(1).md" in names


@pytest.mark.asyncio
async def test_list_folder_via_html_deduplication():
    """Test _list_folder_via_html deduplicates by file_id."""

    id1, id2 = "A" * 32, "B" * 32
    html = f'["{id1}","file1.txt"],["{id1}","file1_duplicate.txt"],["{id2}","file2.txt"]'

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
    ids = [f.file_id for f in result]
    assert ids == [id1, id2]
    assert result[0].name == "file1.txt"


@pytest.mark.asyncio
async def test_list_folder_via_html_noisy_data():
    """Test _list_folder_via_html ignores noise."""

    valid_id = "V" * 32
    html = f"""
    Random text here
    "NOT_AN_ID","not_a_file.txt"
    "ID_WITH_INVALID_CHARS_!@#$%^&*()","invalid.txt"
    "VALID_ID_BUT_WRONG_EXTENSION_32","wrong.exe"
    ["{valid_id}",file_not_quoted.txt]
    ["{valid_id}","valid.txt"]
    """

    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("web_core.adapters.google_drive.safe_httpx_client", return_value=mock_client):
        result = await _list_folder_via_html("test_folder_id")

    assert len(result) == 1
    assert result[0].file_id == valid_id
    assert result[0].name == "valid.txt"


@pytest.mark.asyncio
async def test_get_gdown_import_error():
    """Test _get_gdown raises RuntimeError when gdown is not installed."""
    from web_core.adapters import google_drive

    original_import = importlib.import_module

    def mock_import(name, *args, **kwargs):
        if name == "gdown":
            raise ImportError("mock error")
        return original_import(name, *args, **kwargs)

    with (
        patch("importlib.import_module", side_effect=mock_import),
        patch("web_core.adapters.google_drive._gdown_mod", None),
        pytest.raises(RuntimeError, match="gdown not installed"),
    ):
        await google_drive._get_gdown()
