"""LLM-based CSS selector inference for autonomous content extraction.

When the scraping agent gets valid HTML but existing selectors fail to extract
meaningful content, this module uses an LLM to analyze the page structure and
infer correct CSS selectors for content, title, and navigation elements.

Supports multiple LLM providers via env-var auto-detection:
    - GEMINI_API_KEY / GOOGLE_API_KEY -> Gemini (google-genai SDK)
    - OPENAI_API_KEY                  -> OpenAI (openai SDK)
    - ANTHROPIC_API_KEY               -> Anthropic (anthropic SDK)
    - XAI_API_KEY                     -> xAI (openai SDK with base_url)

Consumers may also inject a custom ``llm_caller`` callable. See
``infer_selectors_with_llm`` for priority rules.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

LLMCaller = Callable[[str, str], Awaitable[dict[str, str]]]
"""Signature: async (prompt, html_content) -> selector dict."""

# Default model per provider (overridable via WEB_CORE_LLM_MODEL env or model kwarg).
_PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "xai": "grok-3-mini",
}

# Track whether we have already logged the "no provider" warning so we do not spam.
_NO_PROVIDER_WARNED = False


def _load_domain_cookies() -> dict[str, dict[str, str]]:
    """Load domain-specific cookies from WEB_CORE_DOMAIN_COOKIES environment variable.

    Expected format: {"domain": {"cookie_name": "value"}, ...}
    """
    cookies: dict[str, dict[str, str]] = {}

    # Load from environment variable to allow configuration of tokens/secrets
    raw = os.environ.get("WEB_CORE_DOMAIN_COOKIES")
    if raw:
        try:
            env_cookies = json.loads(raw)
            if isinstance(env_cookies, dict):
                for domain, domain_cookies in env_cookies.items():
                    if isinstance(domain_cookies, dict):
                        cookies[domain] = domain_cookies
            else:
                logger.warning("WEB_CORE_DOMAIN_COOKIES is not a JSON object")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse WEB_CORE_DOMAIN_COOKIES: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error loading WEB_CORE_DOMAIN_COOKIES: {e}")

    return cookies


# Domain cookies for sites requiring specific cookies (e.g., age verification)
# Loaded from environment to avoid hardcoding secrets in the source code.
DOMAIN_COOKIES: dict[str, dict[str, str]] = _load_domain_cookies()

# Built-in domain configs for known sites — saves LLM calls
DOMAIN_CONFIGS: dict[str, dict[str, str]] = {
    "ncode.syosetu.com": {
        "content": "#novel_honbun",
        "title": ".novel_title, .novel_subtitle",
        "next_chapter": "a.novelview_pager-next",
    },
    "novel18.syosetu.com": {
        "content": "#novel_honbun",
        "title": ".novel_title, .novel_subtitle",
        "next_chapter": "a.novelview_pager-next",
    },
    "kakuyomu.jp": {
        "content": ".widget-episodeBody",
        "title": ".widget-episodeTitle",
        "next_chapter": "a[rel='next']",
    },
    "www.pixiv.net": {
        "content": ".novel-content",
        "title": ".work-info__title",
    },
    "newtoki*.com": {
        "content": "#manga-reading-nav-head + div img, .view-content img",
        "title": ".toon-title",
        "next_chapter": "a.btn-next",
    },
    "mangadex.org": {
        "content": ".md-chapter-page img",
        "title": ".manga-title",
    },
}

# Pre-compile wildcard patterns for fast lookup
_WILDCARD_CONFIGS: list[tuple[re.Pattern[str], dict[str, str]]] = [
    (re.compile(re.escape(pattern).replace(r"\*", r"[^.]*") + r"\Z"), config)
    for pattern, config in DOMAIN_CONFIGS.items()
    if "*" in pattern
]

# Prompt cho LLM infer selectors tu HTML
_INFER_SELECTORS_PROMPT = """\
You are a CSS selector expert. Analyze this HTML and extract the best CSS selectors.

URL: {url}
HTML (truncated to first 5000 chars):
```html
{html_snippet}
```

Return JSON with CSS selectors for:
- "content": the main content area (article body, novel text, manga images)
- "title": the page/chapter title
- "next_chapter": link to next chapter (if pagination exists)

Rules:
- Prefer ID selectors (#id) over class selectors (.class)
- Avoid generic selectors like "div", "p", "span" alone
- For manga/image pages, select the image container
- Return ONLY valid JSON, no explanation

Example response:
{{"content": "#novel_honbun", "title": ".novel_title", "next_chapter": "a.next"}}"""


def get_domain_selectors(url: str) -> dict[str, str] | None:
    """Return built-in selectors for a known domain, or None.

    Also injects domain-specific cookies into selectors["cookies"]
    if the domain requires them (e.g., Syosetu R18 age verification).

    Logs domain usage for analytics — enabling the Tiered Scraping
    feedback loop (track unknown domains → hardcode popular ones).
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    selectors: dict[str, str] | None = None

    # Exact match
    if domain in DOMAIN_CONFIGS:
        selectors = DOMAIN_CONFIGS[domain].copy()
        logger.info(
            "domain_selector_hit",
            extra={"domain": domain, "tier": "hardcoded", "url": url},
        )
    else:
        # Wildcard match (e.g. newtoki*.com)
        for pattern_re, config in _WILDCARD_CONFIGS:
            if pattern_re.match(domain):
                selectors = config.copy()
                logger.info(
                    "domain_selector_hit",
                    extra={
                        "domain": domain,
                        "tier": "hardcoded_wildcard",
                        "pattern": pattern_re.pattern,
                        "url": url,
                    },
                )
                break

    # Log unknown domain — candidate for future hardcoding
    if selectors is None:
        logger.info(
            "domain_selector_miss",
            extra={"domain": domain, "tier": "unknown", "url": url},
        )

    # Inject domain-specific cookies
    if selectors is not None:
        cookies = DOMAIN_COOKIES.get(domain)
        if cookies:
            selectors["cookies"] = cookies  # type: ignore[assignment]

    return selectors


def _build_prompt(url: str, html_content: str) -> str:
    """Build the selector-inference prompt, truncating HTML to first 5000 chars."""
    html_snippet = html_content[:5000]
    return _INFER_SELECTORS_PROMPT.format(url=url, html_snippet=html_snippet)


def _parse_selector_json(text: str) -> dict[str, str]:
    """Parse a JSON response into a whitelisted selector dict."""
    result = json.loads(text or "")
    selectors: dict[str, str] = {}
    if isinstance(result, dict):
        for key in ("content", "title", "next_chapter"):
            value = result.get(key)
            if isinstance(value, str):
                selectors[key] = value
    return selectors


def _detect_provider_from_env() -> str | None:
    """Detect LLM provider from presence of API keys in env. Returns provider name or None."""
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("XAI_API_KEY"):
        return "xai"
    return None


def _resolve_provider_and_model(
    provider: str | None,
    model: str | None,
) -> tuple[str, str] | None:
    """Resolve (provider, model) from explicit params + env vars. None if no provider."""
    env_model = os.environ.get("WEB_CORE_LLM_MODEL")
    if model is None and env_model:
        model = env_model

    if provider is None:
        provider = _detect_provider_from_env()

    if provider is None:
        return None

    if provider not in _PROVIDER_DEFAULT_MODEL:
        logger.warning(
            "selector_inference: unknown provider %r, falling back to env detection",
            provider,
        )
        provider = _detect_provider_from_env()
        if provider is None:
            return None

    resolved_model = model or _PROVIDER_DEFAULT_MODEL[provider]
    return provider, resolved_model


async def _call_gemini(prompt: str, model: str) -> str:
    """Call Gemini via google-genai SDK (Vertex AI or API key mode)."""
    import google.genai as genai

    # Prefer API key mode when GEMINI_API_KEY / GOOGLE_API_KEY is set; otherwise Vertex.
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "klprism"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        )
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


async def _call_openai_compatible(
    prompt: str,
    model: str,
    *,
    base_url: str | None,
    api_key: str,
) -> str:
    """Call an OpenAI-compatible endpoint (OpenAI proper or xAI)."""
    from openai import AsyncOpenAI

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    choice = response.choices[0]
    return choice.message.content or ""


async def _call_anthropic(prompt: str, model: str) -> str:
    """Call Anthropic via anthropic SDK."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.1,
        messages=[
            {
                "role": "user",
                "content": (
                    prompt
                    + "\n\nRespond ONLY with a raw JSON object, no prose, no code fence."
                ),
            }
        ],
    )
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


def _build_default_caller(
    *,
    provider: str | None,
    model: str | None,
) -> LLMCaller | None:
    """Build a default LLM caller from explicit params + env vars. None if no provider."""
    resolved = _resolve_provider_and_model(provider, model)
    if resolved is None:
        return None
    prov, resolved_model = resolved

    async def caller(prompt: str, _html_content: str) -> dict[str, str]:
        if prov == "gemini":
            text = await _call_gemini(prompt, resolved_model)
        elif prov == "openai":
            text = await _call_openai_compatible(
                prompt,
                resolved_model,
                base_url=None,
                api_key=os.environ["OPENAI_API_KEY"],
            )
        elif prov == "xai":
            text = await _call_openai_compatible(
                prompt,
                resolved_model,
                base_url="https://api.x.ai/v1",
                api_key=os.environ["XAI_API_KEY"],
            )
        elif prov == "anthropic":
            text = await _call_anthropic(prompt, resolved_model)
        else:  # pragma: no cover - guarded by _resolve_provider_and_model
            return {}
        return _parse_selector_json(text)

    caller.__web_core_provider__ = prov  # type: ignore[attr-defined]
    caller.__web_core_model__ = resolved_model  # type: ignore[attr-defined]
    return caller


async def infer_selectors_with_llm(
    url: str,
    html_content: str,
    *,
    llm_caller: LLMCaller | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, str]:
    """Use LLM to infer CSS selectors from HTML structure.

    Priority:
        1. Explicit ``llm_caller`` (custom) - used directly.
        2. Explicit ``provider`` + ``model`` params - dispatch via built-in providers.
        3. Env-detected: ``WEB_CORE_LLM_MODEL`` + provider auto-detect from env vars
           (GEMINI_API_KEY / GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
           XAI_API_KEY).
        4. No provider configured -> log warning once and return ``{}``.

    Never raises: on any provider error we log and return ``{}`` so that the
    ``ScrapingAgent`` can continue with domain-config and empty selectors.
    """
    global _NO_PROVIDER_WARNED

    if llm_caller is None:
        llm_caller = _build_default_caller(provider=provider, model=model)

    if llm_caller is None:
        if not _NO_PROVIDER_WARNED:
            logger.warning(
                "selector_inference: no LLM provider configured "
                "(set GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY / XAI_API_KEY, "
                "or pass an llm_caller); skipping inference"
            )
            _NO_PROVIDER_WARNED = True
        return {}

    prompt = _build_prompt(url, html_content)

    try:
        raw = await llm_caller(prompt, html_content)
    except ImportError as e:
        logger.debug(
            "selector_inference: provider SDK not installed (%s), skipping", e
        )
        return {}
    except Exception as e:
        logger.warning("LLM selector inference failed: %s", e)
        return {}

    # llm_caller may return a dict directly (already parsed) or raw JSON text.
    if isinstance(raw, str):
        try:
            selectors = _parse_selector_json(raw)
        except json.JSONDecodeError as e:
            logger.warning("LLM selector inference returned invalid JSON: %s", e)
            return {}
    elif isinstance(raw, dict):
        selectors = {
            k: v
            for k, v in raw.items()
            if k in {"content", "title", "next_chapter"} and isinstance(v, str)
        }
    else:
        logger.warning(
            "LLM selector inference returned unexpected type: %s", type(raw)
        )
        return {}

    from urllib.parse import urlparse

    domain = urlparse(url).netloc.lower()
    provider_name = getattr(llm_caller, "__web_core_provider__", provider or "custom")
    resolved_model = getattr(llm_caller, "__web_core_model__", model)
    logger.info(
        "domain_selector_inferred",
        extra={
            "domain": domain,
            "tier": "llm_inferred",
            "url": url,
            "selectors": selectors,
            "provider": provider_name,
            "model": resolved_model,
        },
    )
    return selectors


def merge_selectors(
    existing: dict[str, str],
    inferred: dict[str, str],
) -> dict[str, str]:
    """Merge selectors, preferring existing non-empty values."""
    merged = {**inferred}
    for key, value in existing.items():
        if value:  # Existing non-empty takes priority
            merged[key] = value
    return merged
