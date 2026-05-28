"""Tests for selector inference utility functions."""

import importlib
import json
import sys
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

    # Invalid matches (verify wildcard-bypass guards still hold)
    assert get_domain_selectors("https://testsite.com.evil.com") is None
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
async def test_infer_no_provider_warns_once(monkeypatch, caplog):
    _clear_llm_env(monkeypatch)
    monkeypatch.setattr(selector_inference, "_NO_PROVIDER_WARNED", False)

    with caplog.at_level("WARNING"):
        # First call should warn
        await infer_selectors_with_llm("https://example.com", "<html/>")
        assert "no LLM provider configured" in caplog.text

        caplog.clear()
        # Second call should not warn
        await infer_selectors_with_llm("https://example.com", "<html/>")
        assert "no LLM provider configured" not in caplog.text


@pytest.mark.asyncio
async def test_infer_llm_caller_returns_invalid_json(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        return "not-json"

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
        return 123  # Unexpected type

    result = await infer_selectors_with_llm(
        "https://example.com",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {}


@pytest.mark.asyncio
async def test_infer_domain_extraction_double_slash(monkeypatch):
    _clear_llm_env(monkeypatch)

    async def fake_caller(_prompt, _html):
        return {"content": "#c"}

    # Test domain extraction for // URL
    result = await infer_selectors_with_llm(
        "//example.com/path",
        "<html/>",
        llm_caller=fake_caller,
    )
    assert result == {"content": "#c"}


@pytest.mark.asyncio
async def test_call_gemini_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")

    mock_google = MagicMock()
    mock_genai = mock_google.genai
    monkeypatch.setitem(sys.modules, "google", mock_google)
    monkeypatch.setitem(sys.modules, "google.genai", mock_genai)

    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '{"content": "#g"}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    from web_core.scraper.selector_inference import _call_gemini

    result = await _call_gemini("prompt", "model")

    assert result == '{"content": "#g"}'
    mock_genai.Client.assert_called_once_with(api_key="dummy")


@pytest.mark.asyncio
async def test_call_gemini_vertex(monkeypatch):
    _clear_llm_env(monkeypatch)

    mock_google = MagicMock()
    mock_genai = mock_google.genai
    monkeypatch.setitem(sys.modules, "google", mock_google)
    monkeypatch.setitem(sys.modules, "google.genai", mock_genai)

    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '{"content": "#v"}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    from web_core.scraper.selector_inference import _call_gemini

    result = await _call_gemini("prompt", "model")

    assert result == '{"content": "#v"}'
    mock_genai.Client.assert_called_once_with(vertexai=True, project="klprism", location="global")


@pytest.mark.asyncio
async def test_call_openai_compatible(monkeypatch):
    mock_openai = MagicMock()
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    mock_client_instance = MagicMock()
    mock_openai.AsyncOpenAI.return_value = mock_client_instance

    mock_choice = MagicMock()
    mock_choice.message.content = '{"content": "#o"}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)

    from web_core.scraper.selector_inference import _call_openai_compatible

    result = await _call_openai_compatible("prompt", "model", base_url="https://api.o.com", api_key="key")

    assert result == '{"content": "#o"}'
    mock_openai.AsyncOpenAI.assert_called_once_with(api_key="key", base_url="https://api.o.com")


@pytest.mark.asyncio
async def test_call_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    mock_anthropic = MagicMock()
    monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

    mock_client_instance = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client_instance

    mock_block = MagicMock()
    mock_block.text = '{"content": "#a"}'
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client_instance.messages.create = AsyncMock(return_value=mock_response)

    from web_core.scraper.selector_inference import _call_anthropic

    result = await _call_anthropic("prompt", "model")

    assert result == '{"content": "#a"}'
    mock_anthropic.AsyncAnthropic.assert_called_once_with(api_key="dummy")

def test_load_domain_cookies_not_dict(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(["not", "a", "dict"]))
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


def test_load_domain_cookies_invalid_domain_value(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps({"example.com": "not-a-dict"}))
    importlib.reload(selector_inference)
    assert "example.com" not in selector_inference.DOMAIN_COOKIES


def test_get_domain_selectors_double_slash():
    # Test line 139
    url = "//ncode.syosetu.com/n1234abc/"
    selectors = selector_inference.get_domain_selectors(url)
    assert selectors is not None


def test_parse_selector_json_not_dict():
    # Test line 196->201 branch
    from web_core.scraper.selector_inference import _parse_selector_json
    assert _parse_selector_json(json.dumps(["not", "a", "dict"])) == {}


def test_resolve_provider_unknown_fallback(monkeypatch):
    # Test lines 233-239
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    # provider "unknown" should fallback to env detection which finds "openai"
    resolved = _resolve_provider_and_model("unknown", None)
    assert resolved == ("openai", selector_inference._PROVIDER_DEFAULT_MODEL["openai"])


def test_resolve_provider_unknown_fallback_fails(monkeypatch):
    # Test lines 233-239 where fallback also fails
    _clear_llm_env(monkeypatch)
    resolved = _resolve_provider_and_model("unknown", None)
    assert resolved is None


@pytest.mark.asyncio
async def test_call_openai_compatible_no_base_url(monkeypatch):
    # Test lines 281->283 branch (base_url=None)
    mock_openai = MagicMock()
    monkeypatch.setitem(sys.modules, "openai", mock_openai)
    mock_client = MagicMock()
    mock_openai.AsyncOpenAI.return_value = mock_client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "{}"
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    from web_core.scraper.selector_inference import _call_openai_compatible
    await _call_openai_compatible("p", "m", base_url=None, api_key="k")
    mock_openai.AsyncOpenAI.assert_called_once_with(api_key="k")


@pytest.mark.asyncio
async def test_call_anthropic_non_text_block(monkeypatch):
    # Test line 313->311 branch
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    mock_anthropic = MagicMock()
    monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)
    mock_client = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client

    mock_block = MagicMock(spec=[]) # No 'text' attribute
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    from web_core.scraper.selector_inference import _call_anthropic
    result = await _call_anthropic("p", "m")
    assert result == ""


@pytest.mark.asyncio
async def test_infer_dispatches_to_anthropic(monkeypatch):
    # Test lines 346-347 in _build_default_caller
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")

    mock_call = AsyncMock(return_value='{"content": "#a"}')
    monkeypatch.setattr(selector_inference, "_call_anthropic", mock_call)

    result = await infer_selectors_with_llm("https://example.com", "<html/>")
    assert result == {"content": "#a"}
    mock_call.assert_awaited_once()

def test_load_domain_cookies_unexpected_error(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "{}")
    # Mock json.loads to raise an unexpected error
    monkeypatch.setattr(json, "loads", MagicMock(side_effect=RuntimeError("boom")))
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}
