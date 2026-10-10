"""SSRF-safe HTTP client with DNS pinning to prevent DNS rebinding attacks.

Provides ``safe_httpx_client()`` factory that creates httpx.AsyncClient instances
with automatic SSRF protection via request event hooks. All outbound HTTP in
web-core MUST go through this client.

Key protections:
- Blocks requests to private, loopback, link-local, reserved, and multicast IPs
- DNS pinning cache prevents TOCTOU / DNS rebinding attacks
- Blocks non-HTTP(S) schemes (file://, ftp://, etc.)
- Blocks well-known localhost aliases
"""

from __future__ import annotations

import functools
import ipaddress
import logging
import socket
import threading
import time
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DNS pinning cache — prevents DNS rebinding (TOCTOU) attacks
# ---------------------------------------------------------------------------

_DNS_CACHE_TTL = 30  # seconds
_dns_cache: dict[str, tuple[list, float]] = {}
_dns_cache_lock = threading.Lock()
_original_getaddrinfo = socket.getaddrinfo


def _pinned_getaddrinfo(host: str, port: int | str | None, *args: Any, **kwargs: Any) -> list:
    """Patched getaddrinfo that returns cached (pinned) DNS results.

    After ``is_safe_url`` resolves and validates a hostname, the result is
    cached.  Subsequent ``socket.getaddrinfo`` calls (e.g. from httpx) will
    receive the *same* IPs, preventing an attacker from changing DNS between
    the safety check and the actual connection.
    """
    with _dns_cache_lock:
        entry = _dns_cache.get(host)
        if entry is not None:
            cached_results, cached_at = entry
            if time.monotonic() - cached_at < _DNS_CACHE_TTL:
                return [
                    (family, stype, proto, canonname, (sockaddr[0], port, *sockaddr[2:]))
                    for family, stype, proto, canonname, sockaddr in cached_results
                ]
            del _dns_cache[host]

    return _original_getaddrinfo(host, port, *args, **kwargs)


# Monkey-patch socket.getaddrinfo at import time
socket.getaddrinfo = _pinned_getaddrinfo  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# IP safety check
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1024)
def _check_ip_safe(ip_str: str, hostname: str) -> bool:
    """Return True if *ip_str* is a publicly-routable address.

    Blocks private (RFC 1918), loopback, link-local (169.254/16),
    reserved, and multicast addresses.
    """
    try:
        # Strip IPv6 zone ID (e.g. fe80::1%eth0)
        if "%" in ip_str:
            ip_str = ip_str.split("%")[0]
        ip = ipaddress.ip_address(ip_str)
        if not ip.is_global or ip.is_multicast:
            logger.warning("Blocked private/unsafe IP: %s for host %s", ip, hostname)
            return False
    except ValueError:
        logger.warning("Unparseable IP '%s' for host %s, blocking", ip_str, hostname)
        return False
    return True


# ---------------------------------------------------------------------------
# URL safety validation
# ---------------------------------------------------------------------------

_BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain", "127.0.0.1", "::1"})


def is_safe_url(url: str, *, allow_private: bool | Iterable[str] = False) -> bool:
    """Validate that *url* is safe to fetch (no SSRF).

    Checks:
    1. Scheme must be ``http`` or ``https``
    2. Hostname must exist
    3. Hostname must not be a known localhost alias (unless ``allow_private=True``)
    4. All resolved IPs must be publicly routable (unless ``allow_private=True``)
    5. Results are cached to pin DNS and prevent rebinding
    """
    try:
        # Performance Optimization: Using urlsplit instead of urlparse avoids regex execution and is ~7x faster
        parsed = urlsplit(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False

    hostname = parsed.hostname
    is_host_allowed = allow_private if isinstance(allow_private, bool) else (hostname in allow_private)
    if not is_host_allowed and hostname.lower() in _BLOCKED_HOSTNAMES:
        return False

    # Fast path: already resolved, validated, and pinned
    with _dns_cache_lock:
        entry = _dns_cache.get(hostname)
        if entry is not None:
            results, cached_at = entry
            if (time.monotonic() - cached_at) < _DNS_CACHE_TTL:
                if not is_host_allowed:
                    for res in results:
                        ip_str = str(res[4][0])
                        if not _check_ip_safe(ip_str, hostname):
                            return False
                return True

    try:
        results = _original_getaddrinfo(hostname, None)
    except (socket.gaierror, Exception):
        return False

    if not is_host_allowed:
        for res in results:
            ip_str = str(res[4][0])
            if not _check_ip_safe(ip_str, hostname):
                return False

    # Pin the DNS result
    with _dns_cache_lock:
        _dns_cache[hostname] = (results, time.monotonic())

    return True


# ---------------------------------------------------------------------------
# SSRF event hook + client factory
# ---------------------------------------------------------------------------


def _ssrf_event_hook_factory(allow_private: bool | Iterable[str]) -> Any:
    """Create an SSRF event hook with specific settings."""
    # Performance Optimization: Convert iterable to frozenset once to ensure O(1)
    # lookups during frequent SSRF checks, preventing O(N) list scans on every HTTP request.
    if isinstance(allow_private, Iterable) and not isinstance(allow_private, (str, bytes)):
        allow_private = frozenset(allow_private)

    async def _ssrf_event_hook(request: httpx.Request) -> None:
        """httpx request event hook that blocks SSRF attempts."""
        url_str = str(request.url)
        if not is_safe_url(url_str, allow_private=allow_private):
            raise httpx.RequestError(f"SSRF blocked: {url_str}", request=request)

    return _ssrf_event_hook


def safe_httpx_client(**kwargs: Any) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with SSRF protection.

    The SSRF event hook is always inserted as the *first* request hook so
    it cannot be bypassed by earlier hooks.  Any additional ``event_hooks``
    passed via *kwargs* are preserved.

    Optional Parameter:
    - ``allow_private``: If ``True``, allows requests to loopback and private IPs.
      Defaults to ``False``.

    Usage::

        async with safe_httpx_client() as client:
            resp = await client.get("https://example.com")
    """
    allow_private = kwargs.pop("allow_private", False)
    hooks = kwargs.pop("event_hooks", {})
    request_hooks = list(hooks.get("request", []))
    request_hooks.insert(0, _ssrf_event_hook_factory(allow_private))
    hooks["request"] = request_hooks
    return httpx.AsyncClient(event_hooks=hooks, **kwargs)


# ---------------------------------------------------------------------------
# Browser SSRF protection
# ---------------------------------------------------------------------------


async def setup_browser_ssrf_protection(page: Any, *, allow_private: bool | Iterable[str] = False) -> None:
    """Setup SSRF protection for a Playwright/Patchright page.

    Uses page.route to intercept all requests (including redirects and
    sub-resources) and validates them using is_safe_url.

    Args:
        page: The Playwright/Patchright Page object.
        allow_private: If True or an iterable of hostnames, allows requests to private/loopback IPs for those hosts.
    """
    # Performance Optimization: Convert iterable to frozenset once to ensure O(1)
    # lookups during frequent browser request intercepts (dozens to hundreds per page).
    if isinstance(allow_private, Iterable) and not isinstance(allow_private, (str, bytes)):
        allow_private = frozenset(allow_private)

    async def _route_handler(route: Any) -> None:
        url = route.request.url
        # Allow safe local schemes
        if url.startswith(("data:", "blob:", "about:")):
            await route.continue_()
            return

        if not is_safe_url(url, allow_private=allow_private):
            logger.warning("SSRF blocked browser request: %s", url)
            await route.abort("blockedbyclient")
            return

        await route.continue_()

    await page.route("**/*", _route_handler)
