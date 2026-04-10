"""Scraping utilities: Cloudflare challenge detection, content validation."""

from __future__ import annotations

import re

# Cloudflare challenge detection patterns
# Using lowercase substring checks is significantly faster than regex search
_CF_TURNSTILE_STRINGS = [
    "challenges.cloudflare.com/turnstile",
    "cf-turnstile-response",
    "/cdn-cgi/challenge-platform/",
]

_CF_JS_CHALLENGE_STRINGS = [
    "just a moment...",
    "checking your browser",
    "verifying you are human",
    "cf-browser-verification",
    "jschl-answer",
]

_CF_MANAGED_STRINGS = [
    "managed_checking_msg",
    "cf-please-wait",
    "performing security verification",
    "security service to protect",
    "verifies you are not a bot",
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

    html_lower = html.lower()

    for s in _CF_TURNSTILE_STRINGS:
        if s in html_lower:
            return "turnstile"

    for s in _CF_MANAGED_STRINGS:
        if s in html_lower:
            return "managed"

    for s in _CF_JS_CHALLENGE_STRINGS:
        if s in html_lower:
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
