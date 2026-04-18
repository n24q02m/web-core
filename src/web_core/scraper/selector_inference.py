"""LLM-based CSS selector inference for autonomous content extraction.

When the scraping agent gets valid HTML but existing selectors fail to extract
meaningful content, this module uses an LLM to analyze the page structure and
infer correct CSS selectors for content, title, and navigation elements.
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# Built-in domain cookies for sites requiring specific cookies
# (e.g., age verification bypass, session persistence)
DOMAIN_COOKIES: dict[str, dict[str, str]] = {
    "novel18.syosetu.com": {
        "over18": "yes",  # Syosetu R18 age verification bypass
    },
}

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
    (re.compile(pattern.replace(".", r"\.").replace("*", ".*")), config)
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


async def infer_selectors_with_llm(
    url: str,
    html_content: str,
    *,
    model: str = "gemini-2.5-flash",
) -> dict[str, str]:
    """Use LLM to infer CSS selectors from HTML structure.

    Falls back to empty dict on any error — the agent should not
    crash just because selector inference fails.
    """
    try:
        import google.genai as genai

        # Truncate HTML to avoid token limits
        html_snippet = html_content[:5000]

        prompt = _INFER_SELECTORS_PROMPT.format(url=url, html_snippet=html_snippet)

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

        text = response.text or ""
        # Parse JSON from response
        result = json.loads(text)
        if isinstance(result, dict):
            selectors = {}
            for key in ("content", "title", "next_chapter"):
                if key in result and isinstance(result[key], str):
                    selectors[key] = result[key]

            from urllib.parse import urlparse

            domain = urlparse(url).netloc.lower()
            logger.info(
                "domain_selector_inferred",
                extra={
                    "domain": domain,
                    "tier": "llm_inferred",
                    "url": url,
                    "selectors": selectors,
                    "model": model,
                },
            )
            return selectors

    except ImportError:
        logger.debug("google-genai not available, skipping LLM selector inference")
    except json.JSONDecodeError as e:
        logger.warning(f"LLM selector inference returned invalid JSON: {e}")
    except Exception as e:
        logger.warning(f"LLM selector inference failed: {e}")

    return {}


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
