"""URL normalization, tracking parameter stripping, and domain validation.

Provides utilities for cleaning and deduplicating URLs before storage or
comparison, and for validating domain names to prevent injection attacks.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# ---------------------------------------------------------------------------
# Tracking parameters to strip
# ---------------------------------------------------------------------------

_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "utm_cid",
        "fbclid",
        "gclid",
        "gclsrc",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "yclid",
        "twclid",
        "igshid",
        "s",
        "ref",
        "ref_src",
    }
)

# ---------------------------------------------------------------------------
# Domain validation regex
# ---------------------------------------------------------------------------

_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*\.[a-zA-Z]{2,}$")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_url_info(url: str) -> tuple[str, str]:
    """Get normalized URL and domain from a URL string.

    Returns a tuple of (normalized_url, domain).
    The domain is lowercased and has the 'www.' prefix removed.

    Returns (url, "") if parsing fails.
    Returns ("", "") for empty input.
    """
    if not url:
        return "", ""

    try:
        parsed = urlparse(url)
    except Exception:
        return url, ""

    scheme = (parsed.scheme or "").lower()
    netloc = (parsed.netloc or "").lower()

    if netloc.startswith("www."):
        netloc = netloc[4:]

    domain = netloc
    path = parsed.path.rstrip("/") or ""

    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        cleaned = {k: v for k, v in params.items() if k not in _TRACKING_PARAMS}
        query = urlencode(cleaned, doseq=True)
    else:
        query = ""

    # Fragment is always stripped (empty string)
    normalized = urlunparse((scheme, netloc, path, parsed.params, query, ""))
    return normalized, domain


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    Transformations applied:
    - Lowercase scheme and netloc
    - Strip ``www.`` prefix from netloc
    - Strip trailing slashes from path
    - Remove tracking query parameters (UTM, click IDs, etc.)
    - Remove fragment (``#section``)

    Returns the original string unchanged if parsing fails.
    Returns empty string for empty input.
    """
    normalized, _ = get_url_info(url)
    return normalized


def strip_tracking_params(url: str) -> str:
    """Remove tracking parameters from a URL.

    This is an alias for :func:`normalize_url` -- the full normalization
    (lowercasing, www stripping, etc.) is always applied.
    """
    return normalize_url(url)


def is_valid_domain(domain: str) -> bool:
    """Validate a domain name to prevent search operator injection.

    Returns True only for well-formed domain names matching
    ``[a-zA-Z0-9][a-zA-Z0-9._-]*\\.[a-zA-Z]{2,}`` with no consecutive dots.
    IP addresses, special characters, and unicode are rejected.
    """
    return bool(_DOMAIN_RE.match(domain)) and ".." not in domain
