import socket

import web_core.http.client
from web_core.http.client import _dns_cache, is_safe_url


def test_ssrf_granular_whitelist():
    _dns_cache.clear()
    original_getaddrinfo = web_core.http.client._original_getaddrinfo

    def mock_getaddrinfo(host, port, *args, **kwargs):
        if host in ("whitelisted.internal", "blocked.internal"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port))]
        return original_getaddrinfo(host, port, *args, **kwargs)

    try:
        web_core.http.client._original_getaddrinfo = mock_getaddrinfo

        # 1. Blocked by default (False)
        assert is_safe_url("http://whitelisted.internal", allow_private=False) is False

        # 2. Allowed by broad whitelist (True)
        assert is_safe_url("http://whitelisted.internal", allow_private=True) is True

        # 3. Allowed by granular whitelist
        assert is_safe_url("http://whitelisted.internal", allow_private=["whitelisted.internal"]) is True

        # 4. Blocked if not in granular whitelist
        assert is_safe_url("http://blocked.internal", allow_private=["whitelisted.internal"]) is False

        # 5. Case-insensitivity check
        assert is_safe_url("http://WHITELISTED.internal", allow_private=["whitelisted.internal"]) is True

    finally:
        web_core.http.client._original_getaddrinfo = original_getaddrinfo


def test_ssrf_localhost_whitelist():
    _dns_cache.clear()
    # Localhost aliases should be allowed only if whitelisted
    assert is_safe_url("http://localhost:8888", allow_private=["localhost"]) is True
    assert is_safe_url("http://127.0.0.1:8888", allow_private=["127.0.0.1"]) is True
    assert is_safe_url("http://localhost:8888", allow_private=False) is False
    assert is_safe_url("http://127.0.0.1:8888", allow_private=["localhost"]) is False
