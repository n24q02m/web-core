import socket
from unittest.mock import patch

import httpx
import pytest

from web_core.http.client import _dns_cache, is_safe_url, safe_httpx_client


@pytest.fixture(autouse=True)
def clean_dns_cache():
    _dns_cache.clear()
    yield
    _dns_cache.clear()


def test_iterable_whitelist_allows_specific_hosts_while_blocking_others():
    """Test that allow_private=[hostname] allows the whitelisted host while blocking others."""

    mock_results = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))]

    with patch("web_core.http.client._original_getaddrinfo", return_value=mock_results):
        # Explicitly whitelisted hostname is allowed
        assert is_safe_url("http://internal.example.com", allow_private=["internal.example.com"]) is True

        # Not whitelisted hostname is blocked (because IP is private)
        assert is_safe_url("http://other.example.com", allow_private=["internal.example.com"]) is False

        # Empty whitelist blocks everything private
        assert is_safe_url("http://internal.example.com", allow_private=[]) is False


def test_iterable_whitelist_with_localhost_alias():
    """Test that allow_private=[hostname] handles well-known localhost aliases correctly."""

    # localhost is blocked by default
    assert is_safe_url("http://localhost", allow_private=False) is False

    # localhost is blocked if not in the whitelist
    assert is_safe_url("http://localhost", allow_private=["internal.example.com"]) is False

    # localhost is allowed if explicitly in the whitelist
    assert is_safe_url("http://localhost", allow_private=["localhost"]) is True


async def test_safe_httpx_client_with_iterable_whitelist():
    """Test that safe_httpx_client respects iterable allow_private."""

    async with safe_httpx_client(allow_private=["allowed.local"]) as client:
        mock_results = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.100", 80))]

        # Safe public URL
        transport_public = httpx.MockTransport(lambda request: httpx.Response(200, content=b"public"))
        client._transport = transport_public
        with patch(
            "web_core.http.client._original_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 80))],
        ):
            resp = await client.get("http://public.com")
            assert resp.status_code == 200

        # Allowed private URL
        transport_allowed = httpx.MockTransport(lambda request: httpx.Response(200, content=b"allowed"))
        client._transport = transport_allowed
        with patch("web_core.http.client._original_getaddrinfo", return_value=mock_results):
            resp = await client.get("http://allowed.local")
            assert resp.status_code == 200

        # Blocked private URL
        with (
            patch("web_core.http.client._original_getaddrinfo", return_value=mock_results),
            pytest.raises(httpx.RequestError, match="SSRF blocked"),
        ):
            await client.get("http://blocked.local")
