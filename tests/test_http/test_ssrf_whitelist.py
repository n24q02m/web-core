import socket

import web_core.http.client
from web_core.http.client import _dns_cache, is_safe_url


def test_ssrf_whitelist():
    _dns_cache.clear()

    original_getaddrinfo = web_core.http.client._original_getaddrinfo

    def mock_getaddrinfo(host, port, *args, **kwargs):
        if host == "allowed.local":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port))]
        elif host == "blocked.local":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.2", port))]
        return original_getaddrinfo(host, port, *args, **kwargs)

    try:
        web_core.http.client._original_getaddrinfo = mock_getaddrinfo

        # allowed.local is in whitelist, so it should be allowed despite pointing to 10.0.0.1
        assert is_safe_url("http://allowed.local", allow_private=["allowed.local"]) is True

        # blocked.local is not in whitelist, so it should be blocked since it points to 10.0.0.2
        assert is_safe_url("http://blocked.local", allow_private=["allowed.local"]) is False

        # if allow_private=True, both should be allowed
        assert is_safe_url("http://allowed.local", allow_private=True) is True
        assert is_safe_url("http://blocked.local", allow_private=True) is True

        # if allow_private=False, both should be blocked
        assert is_safe_url("http://allowed.local", allow_private=False) is False
        assert is_safe_url("http://blocked.local", allow_private=False) is False

    finally:
        web_core.http.client._original_getaddrinfo = original_getaddrinfo
