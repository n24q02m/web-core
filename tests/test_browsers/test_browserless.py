"""Tests for the self-host browserless /content client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from web_core.browsers.browserless import BrowserlessClient


def _resp(*, text="", raise_exc=None):
    resp = MagicMock()
    resp.text = text
    if raise_exc is not None:
        resp.raise_for_status.side_effect = raise_exc
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_requires_base_url():
    with pytest.raises(ValueError):
        BrowserlessClient("")


async def test_render_returns_raw_html_and_strips_trailing_slash():
    http = MagicMock()
    http.post = AsyncMock(return_value=_resp(text="<html>browserless</html>"))
    client = BrowserlessClient("https://browserless.example.com/", http_client=http)

    html = await client.render("https://spa.example.com")

    assert html == "<html>browserless</html>"
    endpoint, kwargs = http.post.call_args
    assert endpoint[0] == "https://browserless.example.com/content"
    assert kwargs["json"] == {"url": "https://spa.example.com", "gotoOptions": {"waitUntil": "networkidle0"}}
    # No token -> no query params.
    assert kwargs["params"] is None


async def test_render_passes_token_as_query_param():
    http = MagicMock()
    http.post = AsyncMock(return_value=_resp(text="<html/>"))
    client = BrowserlessClient("https://bl.example.com", token="secret-token", http_client=http)

    await client.render("https://example.com", wait_until="load")

    _, kwargs = http.post.call_args
    assert kwargs["params"] == {"token": "secret-token"}
    assert kwargs["json"]["gotoOptions"]["waitUntil"] == "load"


async def test_render_propagates_http_error_for_escalation():
    http = MagicMock()
    err = httpx.ConnectTimeout("timeout")
    http.post = AsyncMock(return_value=_resp(raise_exc=err))
    client = BrowserlessClient("https://bl.example.com", http_client=http)

    with pytest.raises(httpx.ConnectTimeout):
        await client.render("https://example.com")
