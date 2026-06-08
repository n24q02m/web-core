"""Tests for selector inference utility functions."""

import importlib
import json
from unittest.mock import AsyncMock

import pytest

from web_core.scraper import selector_inference
from web_core.scraper.selector_inference import (
    _build_default_caller,
    _detect_provider_from_env,
    _resolve_provider_and_model,
    infer_selectors_with_llm,
    merge_selectors,
)


def test_merge_selectors_disjoint():
    existing = {"title": ".title"}
    inferred = {"content": "#content"}
    result = merge_selectors(existing, inferred)
    assert result == {"title": ".title", "content": "#content"}


def test_merge_selectors_prefer_existing():
    existing = {"title": ".title"}
    inferred = {"title": "#llm-title", "content": "#content"}
    result = merge_selectors(existing, inferred)
    assert result == {"title": ".title", "content": "#content"}


def test_merge_selectors_empty_existing():
    existing = {"title": "", "content": ".main"}
    inferred = {"title": "#llm-title"}
    result = merge_selectors(existing, inferred)
    assert result == {"title": "#llm-title", "content": ".main"}


def test_parse_selector_json_valid():
    raw = '{"content": "#c", "title": ".t", "next_chapter": "a"}'
    res = selector_inference._parse_selector_json(raw)
    assert res == {"content": "#c", "title": ".t", "next_chapter": "a"}


def test_parse_selector_json_extra_keys():
    raw = '{"content": "#c", "garbage": "data"}'
    res = selector_inference._parse_selector_json(raw)
    assert res == {"content": "#c"}


def test_parse_selector_json_non_string():
    raw = '{"content": 123}'
    res = selector_inference._parse_selector_json(raw)
    assert res == {}


def test_parse_selector_json_malformed():
    with pytest.raises(json.JSONDecodeError):
        selector_inference._parse_selector_json("not json")


def test_parse_selector_json_empty():
    with pytest.raises(json.JSONDecodeError):
        selector_inference._parse_selector_json("")


def test_get_domain_selectors_ncode():
    url = "https://ncode.syosetu.com/n1234abc/"
    selectors = selector_inference.get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == "#novel_honbun"


def test_get_domain_selectors_wildcard():
    # Test wildcard matching (kakuyomu.jp is mapped via wildcard kakuyomu.jp)
    url = "https://kakuyomu.jp/works/123"
    selectors = selector_inference.get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == ".widget-episodeBody"


def test_get_domain_selectors_miss():
    assert selector_inference.get_domain_selectors("https://unknown.com") is None


def test_get_domain_selectors_boundary_matches():
    from web_core.scraper.selector_inference import get_domain_selectors

    # Tests for _extract_domain and pattern matching
    assert get_domain_selectors("https://eviltestsite.com") is None
    assert get_domain_selectors("https://testsite.com.co") is None

    # Non-wildcard exact matches via existing config (ncode.syosetu.com general novels)
    assert get_domain_selectors("https://ncode.syosetu.com") is not None
    assert get_domain_selectors("https://ncode.syosetu.com.evil.com") is None


def test_load_domain_cookies_from_env(monkeypatch):
    # Mock environment variable
    custom_cookies = {"test.com": {"cookie_name": "cookie_value"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))

    # Reload module to re-initialize DOMAIN_COOKIES
    importlib.reload(selector_inference)

    assert selector_inference.DOMAIN_COOKIES["test.com"] == {"cookie_name": "cookie_value"}
    assert "other.example.com" not in selector_inference.DOMAIN_COOKIES


def test_load_domain_cookies_empty_env(monkeypatch):
    # Mock empty/missing environment variable
    monkeypatch.delenv("WEB_CORE_DOMAIN_COOKIES", raising=False)

    # Reload module
    importlib.reload(selector_inference)

    # It should be empty if we remove the hardcoded ones
    assert selector_inference.DOMAIN_COOKIES == {}


def test_get_domain_selectors_injects_cookies(monkeypatch):
    custom_cookies = {"ncode.syosetu.com": {"session": "abc123"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))
    importlib.reload(selector_inference)

    url = "https://ncode.syosetu.com/n1234abc/"
    selectors = selector_inference.get_domain_selectors(url)

    assert selectors is not None
    assert selectors["cookies"] == {"session": "abc123"}


def test_load_domain_cookies_invalid_json(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "invalid-json")
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


def test_load_domain_cookies_not_dict(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "[1, 2, 3]")
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


def test_load_domain_cookies_domain_not_dict(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", '{"example.com": "not a dict"}')
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


# -----------------------------------------------------------------------------
# Multi-provider auto-detection (issue #177)
# -----------------------------------------------------------------------------


def _clear_llm_env(monkeypatch):
    for var in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "WEB_CORE_LLM_MODEL",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
    ):
        monkeypatch.delenv(var, raising=False)


def test_detect_provider_gemini(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    assert _detect_provider_from_env() == "gemini"


def test_detect_provider_google_fallback(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    assert _detect_provider_from_env() == "gemini"


def test_detect_provider_openai(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    assert _detect_provider_from_env() == "openai"


def test_detect_provider_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    assert _detect_provider_from_env() == "anthropic"


def test_detect_provider_xai(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("XAI_API_KEY", "dummy")
    assert _detect_provider_from_env() == "xai"


def test_detect_provider_priority(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    assert _detect_provider_from_env() == "gemini"


def test_detect_provider_none(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert _detect_provider_from_env() is None


def test_resolve_provider_env_model_alias(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("WEB_CORE_LLM_MODEL", "gpt-4o")
    resolved = _resolve_provider_and_model(None, None)
    assert resolved == ("openai", "gpt-4o")


def test_resolve_provider_explicit_overrides_env(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    resolved = _resolve_provider_and_model("openai", "gpt-4o-2024")
    assert resolved == ("openai", "gpt-4o-2024")


def test_resolve_provider_default_model(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    resolved = _resolve_provider_and_model(None, None)
    assert resolved is not None
    provider, model = resolved
    assert provider == "anthropic"
    assert model == selector_inference._PROVIDER_DEFAULT_MODEL["anthropic"]


def test_resolve_provider_returns_none_when_unset(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert _resolve_provider_and_model(None, None) is None


@pytest.mark.asyncio
async def test_infer_explicit_llm_caller_used(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        return {"content": "#custom", "title": ".t", "next_chapter": "a.n"}

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {"content": "#custom", "title": ".t", "next_chapter": "a.n"}


@pytest.mark.asyncio
async def test_infer_llm_caller_returns_json_string(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        return json.dumps({"content": "#x", "title": ".y", "unrelated": "ignored"})

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {"content": "#x", "title": ".y"}


@pytest.mark.asyncio
async def test_infer_no_provider_graceful_degradation(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setattr(selector_inference, "_NO_PROVIDER_WARNED", False)
    result = await infer_selectors_with_llm("https://example.com", "<html/>")
    assert result == {}


@pytest.mark.asyncio
async def test_infer_llm_caller_exception_returns_empty(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def boom(_prompt, _html):
        raise RuntimeError("provider down")

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=boom,
    )
    assert result == {}


@pytest.mark.asyncio
async def test_infer_llm_caller_import_error_returns_empty(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def missing_sdk(_prompt, _html):
        raise ImportError("openai not installed")

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=missing_sdk,
    )
    assert result == {}


@pytest.mark.asyncio
async def test_infer_dispatches_to_provider_via_env(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    mock_call = AsyncMock(return_value=json.dumps({"content": "#c", "title": ".t", "next_chapter": "a"}))
    monkeypatch.setattr(selector_inference, "_call_openai_compatible", mock_call)

    result = await infer_selectors_with_llm("https://example.com", "<html/>")
    assert result == {"content": "#c", "title": ".t", "next_chapter": "a"}
    mock_call.assert_awaited_once()
    kwargs = mock_call.await_args.kwargs
    assert kwargs["api_key"] == "dummy"
    assert kwargs["base_url"] is None
    args = mock_call.await_args.args
    assert args[1] == selector_inference._PROVIDER_DEFAULT_MODEL["openai"]


@pytest.mark.asyncio
async def test_infer_dispatches_to_xai_with_base_url(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("XAI_API_KEY", "dummy")

    mock_call = AsyncMock(return_value=json.dumps({"content": "#c"}))
    monkeypatch.setattr(selector_inference, "_call_openai_compatible", mock_call)

    result = await infer_selectors_with_llm("https://example.com", "<html/>")
    assert result == {"content": "#c"}
    kwargs = mock_call.await_args.kwargs
    assert kwargs["base_url"] == "https://api.x.ai/v1"


@pytest.mark.asyncio
async def test_infer_model_param_overrides_default(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")

    mock_call = AsyncMock(return_value=json.dumps({"content": "#c"}))
    monkeypatch.setattr(selector_inference, "_call_gemini", mock_call)

    await infer_selectors_with_llm("https://example.com", "<html/>", model="gemini-2.5-pro")
    args = mock_call.await_args.args
    assert args[1] == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_infer_llm_caller_returns_invalid_json(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        return "invalid { json"

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {}


@pytest.mark.asyncio
async def test_infer_llm_caller_returns_unexpected_type(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        return [1, 2, 3]

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {}


@pytest.mark.asyncio
async def test_infer_domain_extraction_protocol_less(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        return {"content": "#c"}

    result = await infer_selectors_with_llm(
        "//example.com/path",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {"content": "#c"}


def test_build_default_caller_invalid_provider():
    with pytest.raises(ValueError, match="Unknown provider: invalid"):
        _build_default_caller(provider="invalid", model="gpt-4")


@pytest.mark.asyncio
async def test_infer_selectors_dispatches_to_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    mock_call = AsyncMock(return_value='{"content": "#a"}')
    monkeypatch.setattr(selector_inference, "_call_anthropic", mock_call)

    res = await infer_selectors_with_llm("http://test.com", "<html></html>", provider="anthropic")
    assert res == {"content": "#a"}
    mock_call.assert_awaited_once()


def test_resolve_provider_unknown_but_env_detected(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    res = _resolve_provider_and_model("unknown", None)
    assert res == ("openai", selector_inference._PROVIDER_DEFAULT_MODEL["openai"])
