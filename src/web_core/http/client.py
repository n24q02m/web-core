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

import ipaddress
import logging
import socket
import threading
import time
from typing import Any
from urllib.parse import urlparse

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
                pinned = []
                for family, stype, proto, canonname, sockaddr in cached_results:
                    pinned_addr = (sockaddr[0], port, *sockaddr[2:])
                    pinned.append((family, stype, proto, canonname, pinned_addr))
                return pinned
            del _dns_cache[host]

    return _original_getaddrinfo(host, port, *args, **kwargs)


# Monkey-patch socket.getaddrinfo at import time
socket.getaddrinfo = _pinned_getaddrinfo  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# IP safety check
# ---------------------------------------------------------------------------


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
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
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


def is_safe_url(url: str) -> bool:
    """Validate that *url* is safe to fetch (no SSRF).

    Checks:
    1. Scheme must be ``http`` or ``https``
    2. Hostname must exist and not be a known localhost alias
    3. All resolved IPs must be publicly routable
    4. Results are cached to pin DNS and prevent rebinding
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return False

    try:
        results = _original_getaddrinfo(hostname, None)
        for res in results:
            ip_str = str(res[4][0])
            if not _check_ip_safe(ip_str, hostname):
                return False
        # Pin the DNS result
        with _dns_cache_lock:
            _dns_cache[hostname] = (results, time.monotonic())
    except socket.gaierror:
        return False
    except ValueError:
        return False
    except Exception:
        return False

    return True


# ---------------------------------------------------------------------------
# SSRF event hook + client factory
# ---------------------------------------------------------------------------


async def _ssrf_event_hook(request: httpx.Request) -> None:
    """httpx request event hook that blocks SSRF attempts."""
    url_str = str(request.url)
    if not is_safe_url(url_str):
        raise httpx.RequestError(f"SSRF blocked: {url_str}", request=request)


def safe_httpx_client(**kwargs: Any) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with SSRF protection.

    The SSRF event hook is always inserted as the *first* request hook so
    it cannot be bypassed by earlier hooks.  Any additional ``event_hooks``
    passed via *kwargs* are preserved.

    Usage::

        async with safe_httpx_client() as client:
            resp = await client.get("https://example.com")
    """
    hooks = kwargs.pop("event_hooks", {})
    request_hooks = list(hooks.get("request", []))
    request_hooks.insert(0, _ssrf_event_hook)
    hooks["request"] = request_hooks
    return httpx.AsyncClient(event_hooks=hooks, **kwargs)
