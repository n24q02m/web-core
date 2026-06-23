import httpx
import pytest

from web_core.http.client import is_safe_url, safe_httpx_client


def test_is_safe_url_allow_loopback():
    # Loopback addresses should be allowed with allow_loopback=True
    assert is_safe_url("http://127.0.0.1", allow_loopback=True) is True
    assert is_safe_url("http://localhost", allow_loopback=True) is True
    assert is_safe_url("http://[::1]", allow_loopback=True) is True

    # But still blocked with default settings
    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("http://localhost") is False
    assert is_safe_url("http://[::1]") is False


def test_is_safe_url_blocks_private_with_allow_loopback():
    # Private (non-loopback) addresses should still be blocked even with allow_loopback=True
    assert is_safe_url("http://10.0.0.1", allow_loopback=True) is False
    assert is_safe_url("http://192.168.1.1", allow_loopback=True) is False
    assert is_safe_url("http://169.254.169.254", allow_loopback=True) is False

    # They are allowed only with allow_private=True
    assert is_safe_url("http://10.0.0.1", allow_private=True) is True
    assert is_safe_url("http://192.168.1.1", allow_private=True) is True
    assert is_safe_url("http://169.254.169.254", allow_private=True) is True


async def test_safe_httpx_client_allow_loopback():
    # Test that the client follows the allow_loopback setting
    async with safe_httpx_client(allow_loopback=True) as client:
        # We don't actually need to make the request, just check if it raises SSRF blocked
        with pytest.raises(httpx.RequestError) as excinfo:
            await client.get("http://10.0.0.1")
        assert "SSRF blocked" in str(excinfo.value)

        # 127.0.0.1 should NOT raise SSRF blocked (it might raise ConnectError which is fine)
        try:
            await client.get("http://127.0.0.1:1")  # Use a port that likely fails
        except httpx.RequestError as e:
            assert "SSRF blocked" not in str(e)
        except Exception:
            pass
