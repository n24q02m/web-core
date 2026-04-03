"""Tests for SSRF-safe HTTP client."""

from __future__ import annotations

import socket
import time
from unittest.mock import patch

import httpx
import pytest

from web_core.http.client import (
    _DNS_CACHE_TTL,
    _check_ip_safe,
    _dns_cache,
    _dns_cache_lock,
    _pinned_getaddrinfo,
    _ssrf_event_hook,
    is_safe_url,
    safe_httpx_client,
)

# ---------------------------------------------------------------------------
# is_safe_url
# ---------------------------------------------------------------------------


class TestIsSafeUrl:
    """Test URL safety validation against SSRF attacks."""

    def test_allows_https(self):
        assert is_safe_url("https://example.com") is True

    def test_allows_http(self):
        assert is_safe_url("http://example.com") is True

    def test_blocks_file_scheme(self):
        assert is_safe_url("file:///etc/passwd") is False

    def test_blocks_ftp_scheme(self):
        assert is_safe_url("ftp://server") is False

    def test_blocks_localhost(self):
        assert is_safe_url("http://localhost") is False

    def test_blocks_localhost_localdomain(self):
        assert is_safe_url("http://localhost.localdomain") is False

    def test_blocks_127_0_0_1(self):
        assert is_safe_url("http://127.0.0.1") is False

    def test_blocks_ipv6_loopback(self):
        assert is_safe_url("http://[::1]") is False

    def test_blocks_private_10_range(self):
        """10.0.0.0/8 is private and must be blocked."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))],
        ):
            assert is_safe_url("http://internal.example.com") is False

    def test_blocks_private_192_168_range(self):
        """192.168.0.0/16 is private and must be blocked."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))],
        ):
            assert is_safe_url("http://internal.example.com") is False

    def test_blocks_private_172_16_range(self):
        """172.16.0.0/12 is private and must be blocked."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("172.16.0.1", 0))],
        ):
            assert is_safe_url("http://internal.example.com") is False

    def test_blocks_empty_string(self):
        assert is_safe_url("") is False

    def test_blocks_no_host_url(self):
        assert is_safe_url("http://") is False

    def test_blocks_dns_resolution_failure(self):
        """URLs that fail DNS resolution must be blocked."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            side_effect=socket.gaierror("Name resolution failed"),
        ):
            assert is_safe_url("http://nonexistent.invalid") is False

    def test_blocks_link_local_address(self):
        """169.254.0.0/16 link-local must be blocked."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0))],
        ):
            assert is_safe_url("http://metadata.example.com") is False

    def test_blocks_multicast_address(self):
        """224.0.0.0/4 multicast must be blocked."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("224.0.0.1", 0))],
        ):
            assert is_safe_url("http://multicast.example.com") is False

    def test_allows_public_ip(self):
        """Public IPs must be allowed."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
        ):
            assert is_safe_url("http://example.com") is True

    def test_caches_dns_results_for_pinned_getaddrinfo(self):
        """is_safe_url should populate the DNS cache for _pinned_getaddrinfo.

        The cache prevents DNS rebinding: is_safe_url resolves and validates,
        then the cached result is served by _pinned_getaddrinfo during the
        actual connection (via socket.getaddrinfo).
        """
        from web_core.http.client import _dns_cache, _dns_cache_lock

        hostname = "cache-pin-test.example.com"
        mock_results = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        # Clean up any prior cache entry
        with _dns_cache_lock:
            _dns_cache.pop(hostname, None)

        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=mock_results,
        ):
            assert is_safe_url(f"http://{hostname}") is True

        # Verify the hostname is now cached
        with _dns_cache_lock:
            assert hostname in _dns_cache
            cached_results, _cached_at = _dns_cache[hostname]
            assert cached_results == mock_results

    def test_blocks_unparseable_url(self):
        """Completely invalid URLs must be blocked."""
        assert is_safe_url("not-a-url") is False

    def test_blocks_urlparse_exception(self):
        """If urlparse raises a generic Exception, is_safe_url returns False."""
        with patch("web_core.http.client.urlparse", side_effect=Exception("parse error")):
            assert is_safe_url("http://example.com") is False

    def test_blocks_generic_dns_exception(self):
        """Generic exceptions during DNS resolution must be blocked (not just gaierror)."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            side_effect=RuntimeError("unexpected DNS error"),
        ):
            assert is_safe_url("http://dns-error.example.com") is False

    def test_blocks_malformed_url_value_error(self):
        """Trigger a real ValueError in urlparse."""
        assert is_safe_url("http://[") is False

    def test_blocks_url_with_none(self):
        """None is not a valid URL (some urlparse versions might handle it, some might raise)."""
        assert is_safe_url(None) is False  # type: ignore[arg-type]

    def test_blocks_url_with_int(self):
        """Integers are not valid URLs and trigger AttributeError in urlparse."""
        assert is_safe_url(123) is False  # type: ignore[arg-type]

    def test_blocks_unparseable_ip_from_dns(self):
        """If DNS returns an unparseable IP string, it must be blocked."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("not-an-ip", 0))],
        ):
            assert is_safe_url("http://bad-dns.example.com") is False
            assert is_safe_url("http://dns-error.example.com") is False


# ---------------------------------------------------------------------------
# _pinned_getaddrinfo
# ---------------------------------------------------------------------------


class TestPinnedGetaddrinfo:
    """Test the DNS pinning cache mechanism."""

    def test_returns_cached_results_when_fresh(self):
        """Cached DNS results should be returned when TTL has not expired."""
        hostname = "pinned-fresh-test.example.com"
        cached_results = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        with _dns_cache_lock:
            _dns_cache[hostname] = (cached_results, time.monotonic())

        try:
            result = _pinned_getaddrinfo(hostname, 443)
            assert len(result) == 1
            # Port should be replaced with the requested port
            assert result[0][4][1] == 443
            # IP should be preserved from cache
            assert result[0][4][0] == "93.184.216.34"
        finally:
            with _dns_cache_lock:
                _dns_cache.pop(hostname, None)

    def test_evicts_expired_cache_entry(self):
        """Expired cache entries should be evicted and fall through to real resolution."""
        hostname = "pinned-expired-test.example.com"
        cached_results = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        # Cache with a timestamp far in the past (expired)
        with _dns_cache_lock:
            _dns_cache[hostname] = (cached_results, time.monotonic() - _DNS_CACHE_TTL - 10)

        fresh_results = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 0))]

        try:
            with patch(
                "web_core.http.client._original_getaddrinfo",
                return_value=fresh_results,
            ):
                result = _pinned_getaddrinfo(hostname, 80)
                # Should get fresh results, not cached
                assert result == fresh_results

            # Expired entry should be removed from cache
            with _dns_cache_lock:
                assert hostname not in _dns_cache
        finally:
            with _dns_cache_lock:
                _dns_cache.pop(hostname, None)

    def test_falls_through_to_original_on_cache_miss(self):
        """When no cache entry exists, should call original getaddrinfo."""
        hostname = "pinned-miss-test.example.com"
        fresh_results = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("5.6.7.8", 0))]

        # Ensure no cache entry
        with _dns_cache_lock:
            _dns_cache.pop(hostname, None)

        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=fresh_results,
        ) as mock_gai:
            result = _pinned_getaddrinfo(hostname, 80)
            assert result == fresh_results
            mock_gai.assert_called_once_with(hostname, 80)

    def test_pinned_getaddrinfo_propagates_gaierror(self):
        """When original resolution fails, gaierror should propagate."""
        hostname = "pinned-fail-test.example.com"
        with _dns_cache_lock:
            _dns_cache.pop(hostname, None)

        with (
            patch(
                "web_core.http.client._original_getaddrinfo",
                side_effect=socket.gaierror("Name resolution failed"),
            ),
            pytest.raises(socket.gaierror),
        ):
            _pinned_getaddrinfo(hostname, 80)


# ---------------------------------------------------------------------------
# _check_ip_safe
# ---------------------------------------------------------------------------


class TestCheckIpSafe:
    """Test IP address safety checks."""

    def test_public_ip_safe(self):
        assert _check_ip_safe("93.184.216.34", "example.com") is True

    def test_private_ip_unsafe(self):
        assert _check_ip_safe("10.0.0.1", "internal") is False

    def test_loopback_unsafe(self):
        assert _check_ip_safe("127.0.0.1", "localhost") is False

    def test_link_local_unsafe(self):
        assert _check_ip_safe("169.254.169.254", "metadata") is False

    def test_multicast_unsafe(self):
        assert _check_ip_safe("224.0.0.1", "multicast") is False

    def test_reserved_unsafe(self):
        assert _check_ip_safe("240.0.0.1", "reserved") is False

    def test_ipv6_loopback_unsafe(self):
        assert _check_ip_safe("::1", "localhost") is False

    def test_ipv6_private_unsafe(self):
        assert _check_ip_safe("fd00::1", "private") is False

    def test_ipv6_public_safe(self):
        assert _check_ip_safe("2606:2800:220:1:248:1893:25c8:1946", "example.com") is True

    def test_zone_id_stripped(self):
        """IPv6 zone IDs (e.g., fe80::1%eth0) must be stripped before checking."""
        assert _check_ip_safe("fe80::1%eth0", "link-local") is False

    def test_unparseable_ip_blocked(self):
        assert _check_ip_safe("not-an-ip", "unknown") is False


# ---------------------------------------------------------------------------
# _ssrf_event_hook
# ---------------------------------------------------------------------------


class TestSsrfEventHook:
    """Test the httpx request event hook for SSRF prevention."""

    async def test_blocks_unsafe_url(self):
        request = httpx.Request("GET", "http://localhost/secret")
        with pytest.raises(httpx.RequestError, match="SSRF blocked"):
            await _ssrf_event_hook(request)

    async def test_allows_safe_url(self):
        """Safe URLs should pass through without raising."""
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
        ):
            request = httpx.Request("GET", "https://example.com/page")
            # Should not raise
            await _ssrf_event_hook(request)


# ---------------------------------------------------------------------------
# safe_httpx_client
# ---------------------------------------------------------------------------


class TestSafeHttpxClient:
    """Test the SSRF-protected httpx client factory."""

    def test_returns_async_client(self):
        client = safe_httpx_client()
        assert isinstance(client, httpx.AsyncClient)

    def test_has_ssrf_event_hook(self):
        client = safe_httpx_client()
        request_hooks = client.event_hooks.get("request", [])
        assert _ssrf_event_hook in request_hooks

    def test_ssrf_hook_is_first(self):
        """SSRF hook must be the first request hook to prevent bypass."""

        async def custom_hook(request):
            pass

        client = safe_httpx_client(event_hooks={"request": [custom_hook]})
        request_hooks = client.event_hooks["request"]
        assert request_hooks[0] is _ssrf_event_hook
        assert request_hooks[1] is custom_hook

    def test_preserves_other_kwargs(self):
        client = safe_httpx_client(timeout=30.0)
        assert client.timeout.connect == 30.0

    def test_preserves_response_hooks(self):
        async def response_hook(response):
            pass

        client = safe_httpx_client(event_hooks={"response": [response_hook]})
        response_hooks = client.event_hooks.get("response", [])
        assert response_hook in response_hooks
