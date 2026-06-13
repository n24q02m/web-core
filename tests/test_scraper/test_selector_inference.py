"""Tests for selector inference utility functions."""

import importlib
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from web_core.scraper import selector_inference
from web_core.scraper.selector_inference import (
    _detect_provider_from_env,
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


def test_merge_selectors_no_inferred():
    existing = {"title": ".title"}
    assert merge_selectors(existing, {}) == {"title": ".title"}


def test_merge_selectors_no_existing():
    inferred = {"title": ".title"}
    assert merge_selectors({}, inferred) == {"title": ".title"}


def test_merge_selectors_no_existing_full():
    inferred = {"title": ".title", "content": "#content", "next_chapter": ".next"}
    assert merge_selectors({}, inferred) == inferred


def test_get_domain_selectors_wildcard(monkeypatch):
    # Verify wildcard-pattern matching infrastructure works correctly + does not
    # leak via subdomain-bypass (e.g. attacker spoofs `attacker.com.<wildcard>.evil.com`).
    # Uses a generic test-fixture wildcard pattern injected via monkeypatch — the
    # built-in DOMAIN_CONFIGS no longer ships site-specific wildcard configs.
    monkeypatch.setitem(sys.modules, "httpx", MagicMock())
    monkeypatch.setitem(sys.modules, "langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "langgraph.graph", MagicMock())
    monkeypatch.setitem(sys.modules, "google.genai", MagicMock())

    import re as _re

    from web_core.scraper import selector_inference

    fixture_pattern = "testsite*.com"
    fixture_config = {"content": "#main", "title": ".title"}
    monkeypatch.setitem(selector_inference.DOMAIN_CONFIGS, fixture_pattern, fixture_config)
    monkeypatch.setattr(
        selector_inference,
        "_WILDCARD_CONFIGS",
        [
            (
                _re.compile(_re.escape(fixture_pattern).replace(r"\*", r"[^.]*") + r"\Z"),
                fixture_config,
            )
        ],
    )

    from web_core.scraper.selector_inference import get_domain_selectors

    # Valid matches against the generic wildcard
    assert get_domain_selectors("https://testsite123.com") is not None
    assert get_domain_selectors("https://testsite.com") is not None

    # Exact match works along with wildcard
    monkeypatch.setitem(selector_inference.DOMAIN_CONFIGS, "testsite.com", fixture_config)
    assert get_domain_selectors("https://testsite.com") is not None

    # Invalid matches (verify wildcard-bypass guards still hold)
    assert get_domain_selectors("https://testsite.com.evil.com") is None
    assert get_domain_selectors("https://eviltestsite.com") is None
    assert get_domain_selectors("https://testsite.com.co") is None


def test_load_domain_cookies_from_env(monkeypatch):
    # Test demonstrates generic env-var injection API: any domain can supply
    # cookies via WEB_CORE_DOMAIN_COOKIES.
    custom_cookies = {"example.com": {"session": "123"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))

    # Force re-load of the module-level DOMAIN_COOKIES
    importlib.reload(selector_inference)

    assert "example.com" in selector_inference.DOMAIN_COOKIES
    assert selector_inference.DOMAIN_COOKIES["example.com"] == {"session": "123"}


def test_load_domain_cookies_empty_env(monkeypatch):
    monkeypatch.delenv("WEB_CORE_DOMAIN_COOKIES", raising=False)

    # Reload module
    importlib.reload(selector_inference)

    # It should be empty if we remove the hardcoded ones
    assert selector_inference.DOMAIN_COOKIES == {}


def test_get_domain_selectors_injects_cookies(monkeypatch):
    # Test demonstrates generic env-var injection API: any domain can supply
    # cookies via WEB_CORE_DOMAIN_COOKIES. Caller is responsible for obtaining
    # user consent before passing R-18 / age-gated cookies.
    custom_cookies = {"ncode.syosetu.com": {"session": "abc123"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))
    importlib.reload(selector_inference)

    url = "https://ncode.syosetu.com/n1234abc/"
    selectors = selector_inference.get_domain_selectors(url)

    assert selectors is not None
    assert selectors["cookies"] == {"session": "abc123"}


def test_load_domain_cookies_invalid_json(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "invalid-json")

    # Should log an error and fallback to empty dict
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


def test_load_domain_cookies_not_a_dict(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(["not", "a", "dict"]))
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


def test_load_domain_cookies_unexpected_error(monkeypatch):
    # Mock json.loads to raise an unexpected Exception
    monkeypatch.setattr(json, "loads", MagicMock(side_effect=RuntimeError("boom")))
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "{}")
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
    # GEMINI wins when multiple keys present (docs order)
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
    # Reset the one-shot warning flag
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


# ---------------------------------------------------------------------------
# Provider-call bodies (_call_gemini / _call_openai_compatible / _call_anthropic).
# These exercise the real SDK-dispatch code by injecting fake SDK modules into
# sys.modules so the lazy in-function imports resolve to the fakes.
# ---------------------------------------------------------------------------


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
    # google-genai isn't installed in the test env, so the lazy
    # `import google.genai` needs both the parent package and the submodule.
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

    # response.text is "" -> function returns "" (the `or ""` branch)
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
    # Inject a fake so an accidental client build would not hit the real SDK.
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
                object(),  # block without a .text attribute -> skipped
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


@pytest.mark.asyncio
async def test_infer_gemini_vertex_missing_project_logs_warning(monkeypatch, caplog):
    _clear_llm_env(monkeypatch)
    # Inject fake genai so it doesn't try to import real one if it was missing
    _inject_fake_genai(monkeypatch, text="{}", capture={})

    # Explicitly request gemini provider but without any credentials/project
    result = await infer_selectors_with_llm("https://example.com", "<html></html>", provider="gemini")

    assert result == {}
    assert "GOOGLE_CLOUD_PROJECT" in caplog.text
    assert "LLM selector inference failed" in caplog.text


def test_detect_provider_missing_xai_key(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert _detect_provider_from_env() is None


def test_infer_no_provider_second_call_no_warning(monkeypatch, caplog):
    _clear_llm_env(monkeypatch)
    # Ensure warning flag is True
    monkeypatch.setattr(selector_inference, "_NO_PROVIDER_WARNED", True)

    caplog.clear()
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(infer_selectors_with_llm("https://example.com", "<html/>"))

    assert result == {}
    assert "no LLM provider configured" not in caplog.text


def test_parse_selector_json_not_dict():
    # Covers line 196 (if isinstance(result, dict) is False)
    assert selector_inference._parse_selector_json("[]") == {}


def test_parse_selector_json_values_not_strings():
    # Covers line 199's false branch
    data = {"content": 123, "title": None, "next_chapter": ["abc"]}
    assert selector_inference._parse_selector_json(json.dumps(data)) == {}


@pytest.mark.asyncio
async def test_infer_llm_caller_returns_raw_json_string(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        # Explicitly return a JSON string to exercise the 'if isinstance(raw, str):' branch
        return '{"content": "#raw", "title": ".raw"}'

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {"content": "#raw", "title": ".raw"}


def test_get_domain_selectors_completely_unknown_miss(monkeypatch):
    # Covers line 139
    # Ensure we don't match any existing hardcoded domains or wildcards
    monkeypatch.setattr(selector_inference, "DOMAIN_CONFIGS", {})
    monkeypatch.setattr(selector_inference, "_WILDCARD_CONFIGS", [])

    url = "https://unknown.com"
    assert selector_inference.get_domain_selectors(url) is None
