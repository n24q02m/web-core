"""Tests for selector inference utility functions."""

import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from web_core.scraper import selector_inference
from web_core.scraper.selector_inference import (
    _detect_provider_from_env,
    _parse_selector_json,
    _resolve_provider_and_model,
    infer_selectors_with_llm,
    merge_selectors,
)


def test_merge_selectors_disjoint():
    existing = {"title": ".title"}
    inferred = {"content": "#content"}
    expected = {"title": ".title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_existing_priority():
    existing = {"title": ".existing-title"}
    inferred = {"title": ".inferred-title", "content": "#content"}
    expected = {"title": ".existing-title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_empty_existing_uses_inferred():
    existing = {"title": ""}
    inferred = {"title": ".inferred-title", "content": "#content"}
    expected = {"title": ".inferred-title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_missing_existing_uses_inferred():
    existing = {"content": "#content"}
    inferred = {"title": ".inferred-title"}
    expected = {"content": "#content", "title": ".inferred-title"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_all_empty():
    assert merge_selectors({}, {}) == {}


def test_parse_selector_json_valid():
    text = json.dumps({"content": "#c", "title": ".t", "next_chapter": "a"})
    assert _parse_selector_json(text) == {"content": "#c", "title": ".t", "next_chapter": "a"}


def test_parse_selector_json_partial():
    text = json.dumps({"content": "#c"})
    assert _parse_selector_json(text) == {"content": "#c"}


def test_parse_selector_json_unexpected_keys():
    text = json.dumps({"content": "#c", "bogus": "val"})
    assert _parse_selector_json(text) == {"content": "#c"}


def test_parse_selector_json_non_string_values():
    text = json.dumps({"content": 123, "title": None})
    assert _parse_selector_json(text) == {}


def test_parse_selector_json_malformed():
    assert _parse_selector_json("invalid { json") == {}


def test_parse_selector_json_empty():
    assert _parse_selector_json("") == {}
    assert _parse_selector_json(None) == {}  # type: ignore[arg-type]


def test_parse_selector_json_non_dict():
    assert _parse_selector_json(json.dumps([1, 2, 3])) == {}
    assert _parse_selector_json(json.dumps("not a dict")) == {}


def test_parse_selector_json_valid():
    text = json.dumps({"content": "#c", "title": ".t", "next_chapter": "a"})
    assert _parse_selector_json(text) == {"content": "#c", "title": ".t", "next_chapter": "a"}


def test_parse_selector_json_partial():
    text = json.dumps({"content": "#c"})
    assert _parse_selector_json(text) == {"content": "#c"}


def test_parse_selector_json_unexpected_keys():
    text = json.dumps({"content": "#c", "bogus": "val"})
    assert _parse_selector_json(text) == {"content": "#c"}


def test_parse_selector_json_non_string_values():
    text = json.dumps({"content": 123, "title": None})
    assert _parse_selector_json(text) == {}


def test_parse_selector_json_malformed():
    assert _parse_selector_json("invalid { json") == {}


def test_parse_selector_json_empty():
    assert _parse_selector_json("") == {}
    assert _parse_selector_json(None) == {}  # type: ignore[arg-type]


def test_parse_selector_json_non_dict():
    assert _parse_selector_json(json.dumps([1, 2, 3])) == {}
    assert _parse_selector_json(json.dumps("not a dict")) == {}


def test_parse_selector_json_valid():
    text = json.dumps({"content": "#c", "title": ".t", "next_chapter": "a"})
    assert _parse_selector_json(text) == {"content": "#c", "title": ".t", "next_chapter": "a"}


def test_parse_selector_json_partial():
    text = json.dumps({"content": "#c"})
    assert _parse_selector_json(text) == {"content": "#c"}


def test_parse_selector_json_unexpected_keys():
    text = json.dumps({"content": "#c", "bogus": "val"})
    assert _parse_selector_json(text) == {"content": "#c"}


def test_parse_selector_json_non_string_values():
    text = json.dumps({"content": 123, "title": None})
    assert _parse_selector_json(text) == {}


def test_parse_selector_json_malformed():
    assert _parse_selector_json("invalid { json") == {}


def test_parse_selector_json_empty():
    assert _parse_selector_json("") == {}
    assert _parse_selector_json(None) == {}  # type: ignore[arg-type]


def test_parse_selector_json_non_dict():
    assert _parse_selector_json(json.dumps([1, 2, 3])) == {}
    assert _parse_selector_json(json.dumps("not a dict")) == {}


def _clear_llm_env(monkeypatch):
    for key in [
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "WEB_CORE_LLM_MODEL",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.asyncio
async def test_infer_no_provider_returns_empty(monkeypatch):
    _clear_llm_env(monkeypatch)
    # Mocking logger to avoid actual warning in output if desired, but not strictly needed.
    result = await infer_selectors_with_llm("https://example.com", "<html/>")
    assert result == {}


@pytest.mark.asyncio
async def test_infer_llm_caller_exception_returns_empty(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def boom(_prompt, _html):
        raise RuntimeError("LLM error")

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
    # Model resolved from _PROVIDER_DEFAULT_MODEL
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
        return [1, 2, 3]  # Unexpected type

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

    # Test with // protocol-less URL
    result = await infer_selectors_with_llm(
        "//example.com/path",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {"content": "#c"}


def _inject_fake_genai(monkeypatch, *, text, capture):
    async def generate_content(**kwargs):
        capture["gen_kwargs"] = kwargs
        return SimpleNamespace(text=text)

    class FakeClient:
        def __init__(self, **kwargs):
            capture["client_kwargs"] = kwargs
            self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    mod = ModuleType("google.genai")
    mod.Client = FakeClient
    mod.types = SimpleNamespace(GenerateContentConfig=lambda **kw: SimpleNamespace(**kw))
    fake_google = ModuleType("google")
    fake_google.genai = mod
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", mod)
    return capture


@pytest.mark.asyncio
async def test_call_gemini_api_key_mode(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k-123")
    capture = _inject_fake_genai(monkeypatch, text='{"content": "#x"}', capture={})

    out = await selector_inference._call_gemini("prompt", "gemini-2.5-flash")

    assert out == '{"content": "#x"}'
    assert capture["client_kwargs"] == {"api_key": "k-123"}
    assert capture["gen_kwargs"]["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_call_gemini_vertex_mode(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    capture = _inject_fake_genai(monkeypatch, text="", capture={})

    out = await selector_inference._call_gemini("prompt", "gemini-2.5-flash")

    assert out == ""
    assert capture["client_kwargs"] == {
        "vertexai": True,
        "project": "my-project",
        "location": "us-central1",
    }


@pytest.mark.asyncio
async def test_call_gemini_vertex_missing_project_raises(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    _inject_fake_genai(monkeypatch, text="{}", capture={})

    with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT"):
        await selector_inference._call_gemini("prompt", "gemini-2.5-flash")


@pytest.mark.asyncio
async def test_call_openai_compatible_passes_base_url(monkeypatch):
    capture: dict = {}

    async def create(**kwargs):
        capture["create_kwargs"] = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"content": "#c"}'))])

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            capture["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    mod = ModuleType("openai")
    mod.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)

    out = await selector_inference._call_openai_compatible(
        "prompt", "grok-3-mini", base_url="https://api.x.ai/v1", api_key="xai-key"
    )

    assert out == '{"content": "#c"}'
    assert capture["client_kwargs"] == {"api_key": "xai-key", "base_url": "https://api.x.ai/v1"}
    assert capture["create_kwargs"]["model"] == "grok-3-mini"


@pytest.mark.asyncio
async def test_call_openai_compatible_none_content(monkeypatch):
    async def create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))])

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    mod = ModuleType("openai")
    mod.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)

    out = await selector_inference._call_openai_compatible("prompt", "gpt-4o-mini", base_url=None, api_key="k")

    assert out == ""


@pytest.mark.asyncio
async def test_call_anthropic_joins_text_blocks(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
    capture: dict = {}

    async def create(**kwargs):
        capture["create_kwargs"] = kwargs
        return SimpleNamespace(
            content=[
                SimpleNamespace(text='{"content"'),
                SimpleNamespace(text=': "#a"}'),
                object(),
            ]
        )

    class FakeAsyncAnthropic:
        def __init__(self, **kwargs):
            capture["client_kwargs"] = kwargs
            self.messages = SimpleNamespace(create=create)

    mod = ModuleType("anthropic")
    mod.AsyncAnthropic = FakeAsyncAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)

    out = await selector_inference._call_anthropic("prompt", "claude-haiku-4-5-20251001")

    assert out == '{"content": "#a"}'
    assert capture["client_kwargs"] == {"api_key": "ant-key"}


def test_resolve_provider_unknown_falls_back_to_env(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    resolved = _resolve_provider_and_model("bogus-provider", None)
    assert resolved == ("openai", selector_inference._PROVIDER_DEFAULT_MODEL["openai"])


def test_resolve_provider_unknown_no_env_returns_none(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert _resolve_provider_and_model("bogus-provider", None) is None


@pytest.mark.asyncio
async def test_infer_dispatches_to_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")

    mock_call = AsyncMock(return_value=json.dumps({"content": "#a"}))
    monkeypatch.setattr(selector_inference, "_call_anthropic", mock_call)

    result = await infer_selectors_with_llm("https://example.com", "<html/>")
    assert result == {"content": "#a"}
    mock_call.assert_awaited_once()
