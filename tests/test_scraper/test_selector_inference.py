from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.selector_inference import get_domain_selectors, infer_selectors_with_llm, merge_selectors


def test_get_domain_selectors_exact_match():
    url = "https://ncode.syosetu.com/n1234ab/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == "#novel_honbun"
    assert selectors["title"] == ".novel_title, .novel_subtitle"
    assert "cookies" not in selectors


def test_get_domain_selectors_wildcard_match():
    url = "https://newtoki95.com/webtoon/1234"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["title"] == ".toon-title"
    assert selectors["next_chapter"] == "a.btn-next"


def test_get_domain_selectors_with_cookies():
    url = "https://novel18.syosetu.com/n1234ab/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == "#novel_honbun"
    assert selectors["cookies"] == {"over18": "yes"}


def test_get_domain_selectors_no_match():
    url = "https://example.com/"
    selectors = get_domain_selectors(url)
    assert selectors is None


def test_get_domain_selectors_case_insensitivity():
    url = "HTTPS://KAKUYOMU.JP/works/123"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == ".widget-episodeBody"


def test_merge_selectors_existing_priority():
    existing = {"content": "#main", "title": ""}
    inferred = {"content": ".article", "title": "h1", "next_chapter": "a.next"}
    merged = merge_selectors(existing, inferred)

    assert merged["content"] == "#main"  # Existing non-empty takes priority
    assert merged["title"] == "h1"  # Existing empty allowed inferred to take over
    assert merged["next_chapter"] == "a.next"


def test_merge_selectors_all_existing():
    existing = {"content": "#main", "title": "h1", "next_chapter": "a.next"}
    inferred = {"content": ".article", "title": "Header", "next_chapter": "link"}
    merged = merge_selectors(existing, inferred)

    assert merged == existing


def test_merge_selectors_all_inferred():
    existing: dict[str, str] = {}
    inferred = {"content": ".article", "title": "Header"}
    merged = merge_selectors(existing, inferred)

    assert merged == inferred


@pytest.mark.asyncio
async def test_infer_selectors_with_llm_success():
    url = "https://example.com"
    html_content = "<html><body><h1>Title</h1><div id='content'>Body</div></body></html>"

    mock_response = MagicMock()
    mock_response.text = '{"content": "#content", "title": "h1"}'

    # Mock the whole google.genai module structure
    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        import google.genai

        mock_client = MagicMock()
        google.genai.Client.return_value = mock_client
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        selectors = await infer_selectors_with_llm(url, html_content)

        assert selectors["content"] == "#content"
        assert selectors["title"] == "h1"
        assert "next_chapter" not in selectors


@pytest.mark.asyncio
async def test_infer_selectors_with_llm_import_error():
    url = "https://example.com"
    html_content = "some html"

    with patch.dict("sys.modules", {"google.genai": None}):
        selectors = await infer_selectors_with_llm(url, html_content)
        assert selectors == {}


@pytest.mark.asyncio
async def test_infer_selectors_with_llm_json_error():
    url = "https://example.com"
    html_content = "some html"

    mock_response = MagicMock()
    mock_response.text = "invalid json"

    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        import google.genai

        mock_client = MagicMock()
        google.genai.Client.return_value = mock_client
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        selectors = await infer_selectors_with_llm(url, html_content)
        assert selectors == {}


@pytest.mark.asyncio
async def test_infer_selectors_with_llm_general_exception():
    url = "https://example.com"
    html_content = "some html"

    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        import google.genai

        mock_client = MagicMock()
        google.genai.Client.return_value = mock_client
        mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API Error"))

        selectors = await infer_selectors_with_llm(url, html_content)
        assert selectors == {}


@pytest.mark.asyncio
async def test_infer_selectors_with_llm_non_dict_json():
    url = "https://example.com"
    html_content = "some html"

    mock_response = MagicMock()
    mock_response.text = '["not", "a", "dict"]'

    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        import google.genai

        mock_client = MagicMock()
        google.genai.Client.return_value = mock_client
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        selectors = await infer_selectors_with_llm(url, html_content)
        assert selectors == {}
