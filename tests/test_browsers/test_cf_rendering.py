"""Tests for the Cloudflare Browser Rendering /content client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from web_core.browsers.cf_rendering import CFBrowserRenderingClient, CFBrowserRenderingError


def _resp(*, json_data=None, raise_exc=None, text=""):
    resp = MagicMock()
    resp.json.return_value = json_data or {}
    resp.text = text
    if raise_exc is not None:
        resp.raise_for_status.side_effect = raise_exc
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_requires_account_id_and_token():
    with pytest.raises(ValueError):
        CFBrowserRenderingClient("", "token")
    with pytest.raises(ValueError):
        CFBrowserRenderingClient("acct", "")


@patch("web_core.browsers.cf_rendering.is_safe_url", return_value=True)
async def test_render_returns_html_and_sends_correct_request(mock_is_safe_url):
    http = MagicMock()
    http.post = AsyncMock(return_value=_resp(json_data={"success": True, "result": "<html>rendered</html>"}))
    client = CFBrowserRenderingClient("acct123", "tok456", http_client=http)

    html = await client.render("https://spa.example.com", wait_until="networkidle0")

    assert html == "<html>rendered</html>"
    endpoint, kwargs = http.post.call_args
    assert endpoint[0] == "https://api.cloudflare.com/client/v4/accounts/acct123/browser-rendering/content"
    assert kwargs["json"] == {"url": "https://spa.example.com", "gotoOptions": {"waitUntil": "networkidle0"}}
    assert kwargs["headers"]["Authorization"] == "Bearer tok456"
    assert kwargs["headers"]["Content-Type"] == "application/json"


@patch("web_core.browsers.cf_rendering.is_safe_url", return_value=True)
async def test_render_raises_on_api_failure(mock_is_safe_url):
    http = MagicMock()
    http.post = AsyncMock(return_value=_resp(json_data={"success": False, "errors": [{"message": "quota"}]}))
    client = CFBrowserRenderingClient("acct", "tok", http_client=http)

    with pytest.raises(CFBrowserRenderingError, match="quota"):
        await client.render("https://example.com")


@patch("web_core.browsers.cf_rendering.is_safe_url", return_value=True)
async def test_render_raises_on_empty_result(mock_is_safe_url):
    http = MagicMock()
    http.post = AsyncMock(return_value=_resp(json_data={"success": True, "result": ""}))
    client = CFBrowserRenderingClient("acct", "tok", http_client=http)

    with pytest.raises(CFBrowserRenderingError):
        await client.render("https://example.com")


@patch("web_core.browsers.cf_rendering.is_safe_url", return_value=True)
async def test_render_propagates_http_error_for_escalation(mock_is_safe_url):
    http = MagicMock()
    err = httpx.HTTPStatusError("503", request=MagicMock(), response=MagicMock())
    http.post = AsyncMock(return_value=_resp(raise_exc=err))
    client = CFBrowserRenderingClient("acct", "tok", http_client=http)

    with pytest.raises(httpx.HTTPStatusError):
        await client.render("https://example.com")


@patch("web_core.browsers.cf_rendering.is_safe_url", return_value=False)
async def test_render_blocks_unsafe_url_ssrf(mock_is_safe_url):
    http = MagicMock()
    http.post = AsyncMock(return_value=_resp(json_data={"success": True, "result": "<html/>"}))
    client = CFBrowserRenderingClient("acct", "tok", http_client=http)

    with pytest.raises(ValueError, match="SSRF blocked"):
        await client.render("http://169.254.169.254/latest/meta-data")

    http.post.assert_not_called()
