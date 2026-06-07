import importlib
import json
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from web_core.scraper import selector_inference
from web_core.scraper.selector_inference import (
    _detect_provider_from_env,
    _resolve_provider_and_model,
    get_domain_selectors,
    infer_selectors_with_llm,
)


def test_get_domain_selectors_exact_match():
    # syosetu.com hardcoded config
    url = "https://ncode.syosetu.com/n1234abc/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == "#novel_honbun"


def test_get_domain_selectors_unknown_domain():
    assert get_domain_selectors("https://unknown.com") is None


def test_get_domain_selectors_case_insensitive():
    url = "HTTPS://NCODE.SYOSETU.COM/n1234abc/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == "#novel_honbun"


def test_get_domain_selectors_wildcard():
    # If we had any wildcards, they'd be tested here.
    # Currently none in DOMAIN_CONFIGS.
    pass


def test_get_domain_selectors_evil_subdomain_denied():
    # Only exact matches or allowed wildcards.
    # ncode.syosetu.com is a fixed domain.
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


def test_build_default_caller_invalid_provider_raises():
    from web_core.scraper.selector_inference import _build_default_caller

    with pytest.raises(ValueError, match="Unknown provider: bogus"):
        _build_default_caller(provider="bogus", model=None)


def test_load_domain_cookies_unexpected_error(monkeypatch):
    from web_core.scraper import selector_inference

    def boom(_):
        raise RuntimeError("fs error")

    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", '{"a": "b"}')
    monkeypatch.setattr("json.loads", boom)

    # Should log warning and return empty dict
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


@pytest.mark.asyncio
async def test_infer_dispatches_to_anthropic(monkeypatch):
    from web_core.scraper import selector_inference

    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")

    mock_call = AsyncMock(return_value=json.dumps({"content": "#c"}))
    monkeypatch.setattr(selector_inference, "_call_anthropic", mock_call)

    result = await infer_selectors_with_llm("https://example.com", "<html/>")
    assert result == {"content": "#c"}
    mock_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_anthropic_full(monkeypatch):
    from web_core.scraper import selector_inference

    mock_resp = MagicMock()
    mock_block = MagicMock()
    mock_block.text = '{"content": "#a"}'
    mock_resp.content = [mock_block]

    mock_client_instance = MagicMock()
    mock_client_instance.messages.create = AsyncMock(return_value=mock_resp)

    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client_instance

    sys.modules["anthropic"] = mock_anthropic

    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    res = await selector_inference._call_anthropic("prompt", "claude-3")
    assert res == '{"content": "#a"}'


@pytest.mark.asyncio
async def test_call_openai_compatible_full(monkeypatch):
    from web_core.scraper import selector_inference

    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"content": "#o"}'
    mock_resp.choices = [mock_choice]

    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_resp)

    mock_openai = MagicMock()
    mock_openai.AsyncOpenAI.return_value = mock_client_instance

    sys.modules["openai"] = mock_openai

    res = await selector_inference._call_openai_compatible("prompt", "gpt-4", base_url=None, api_key="dummy")
    assert res == '{"content": "#o"}'


@pytest.mark.asyncio
async def test_call_gemini_full(monkeypatch):
    from web_core.scraper import selector_inference

    mock_resp = MagicMock()
    mock_resp.text = '{"content": "#g"}'

    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_content = AsyncMock(return_value=mock_resp)

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client_instance

    mock_google = MagicMock()
    mock_google.genai = mock_genai

    sys.modules["google"] = mock_google
    sys.modules["google.genai"] = mock_genai

    # Test API key mode
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    res = await selector_inference._call_gemini("prompt", "gemini-pro")
    assert res == '{"content": "#g"}'

    # Test Vertex AI mode
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    res = await selector_inference._call_gemini("prompt", "gemini-pro")
    assert res == '{"content": "#g"}'
