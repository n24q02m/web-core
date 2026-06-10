"""HTTP security module: SSRF-safe client and URL utilities."""

from web_core.http.client import is_safe_url, safe_httpx_client, setup_browser_ssrf_protection
from web_core.http.url import is_valid_domain, normalize_url, strip_tracking_params

__all__ = [
    "is_safe_url",
    "is_valid_domain",
    "normalize_url",
    "safe_httpx_client",
    "setup_browser_ssrf_protection",
    "strip_tracking_params",
]
