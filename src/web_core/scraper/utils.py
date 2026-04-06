"""Scraping utilities: Cloudflare challenge detection, content validation."""

from __future__ import annotations

import re

# Cloudflare challenge detection patterns
_CF_TURNSTILE_PATTERNS = [
    re.compile(r"challenges\.cloudflare\.com/turnstile", re.IGNORECASE),
    re.compile(r"cf-turnstile-response", re.IGNORECASE),
    re.compile(r"/cdn-cgi/challenge-platform/", re.IGNORECASE),
]

_CF_JS_CHALLENGE_PATTERNS = [
    re.compile(r"Just a moment\.\.\.", re.IGNORECASE),
    re.compile(r"Checking your browser", re.IGNORECASE),
    re.compile(r"Verifying you are human", re.IGNORECASE),
    re.compile(r"cf-browser-verification", re.IGNORECASE),
    re.compile(r"jschl-answer", re.IGNORECASE),
]

_CF_MANAGED_PATTERNS = [
    re.compile(r"managed_checking_msg", re.IGNORECASE),
    re.compile(r"cf-please-wait", re.IGNORECASE),
]

_CF_SITEKEY_PATTERNS = [
    re.compile(r'data-sitekey=["\']([0-9a-zA-Z_-]{20,})["\']'),
    re.compile(r"sitekey=([0-9a-zA-Z_-]{20,})"),
    re.compile(r'turnstileSiteKey["\s:]+["\']([0-9a-zA-Z_-]{20,})["\']'),
]


def detect_cloudflare_challenge(html: str) -> str | None:
    """Detect Cloudflare challenge type from HTML content.

    Returns:
        "turnstile" — Cloudflare Turnstile CAPTCHA (requires solving)
        "js_challenge" — CF JS challenge (auto-resolves with browser wait)
        "managed" — CF managed challenge (intermediate, may auto-resolve)
        None — not a CF challenge page
    """
    if not html or len(html) < 50:
        return None

    for pattern in _CF_TURNSTILE_PATTERNS:
        if pattern.search(html):
            return "turnstile"

    for pattern in _CF_MANAGED_PATTERNS:
        if pattern.search(html):
            return "managed"

    for pattern in _CF_JS_CHALLENGE_PATTERNS:
        if pattern.search(html):
            return "js_challenge"

    return None


def extract_turnstile_sitekey(html: str) -> str | None:
    """Extract Cloudflare Turnstile site key from HTML.

    Returns the site key string, or None if not found.
    """
    for pattern in _CF_SITEKEY_PATTERNS:
        match = pattern.search(html)
        if match:
            return match.group(1)
    return None


def is_cloudflare_challenge(html: str) -> bool:
    """Quick check: is this HTML a Cloudflare challenge page?"""
    return detect_cloudflare_challenge(html) is not None
