import socket
from web_core.http.client import is_safe_url, _dns_cache
import web_core.http.client

def test_ssrf_whitelist():
    _dns_cache.clear()

    original_getaddrinfo = web_core.http.client._original_getaddrinfo

    def mock_getaddrinfo(host, port, *args, **kwargs):
        if host == "localhost":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]
        if host == "private.local":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port))]
        return original_getaddrinfo(host, port, *args, **kwargs)

    try:
        web_core.http.client._original_getaddrinfo = mock_getaddrinfo

        # Without whitelist
        assert is_safe_url("http://localhost") is False
        assert is_safe_url("http://private.local") is False

        # Global bypass
        assert is_safe_url("http://localhost", allow_private=True) is True
        assert is_safe_url("http://private.local", allow_private=True) is True

        # Granular whitelist
        assert is_safe_url("http://localhost", allow_private=["localhost"]) is True
        assert is_safe_url("http://private.local", allow_private=["localhost"]) is False
        assert is_safe_url("http://localhost", allow_private=["private.local"]) is False
        assert is_safe_url("http://private.local", allow_private=["private.local"]) is True
        assert is_safe_url("http://localhost", allow_private=["localhost", "private.local"]) is True
        assert is_safe_url("http://private.local", allow_private=["localhost", "private.local"]) is True

    finally:
        web_core.http.client._original_getaddrinfo = original_getaddrinfo
