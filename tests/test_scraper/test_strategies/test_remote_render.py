"""Tests for RemoteRenderStrategy (adapts a render client to the agent chain)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from web_core.scraper.strategies.remote_render import RemoteRenderStrategy, RenderClient


class _StubClient:
    name = "stub-render"

    def __init__(self, html="<html>ok</html>", exc=None):
        self._html = html
        self._exc = exc
        self.calls: list[tuple[str, str]] = []

    async def render(self, url, *, wait_until="networkidle0", timeout=None):
        self.calls.append((url, wait_until))
        if self._exc is not None:
            raise self._exc
        return self._html


def test_stub_client_satisfies_protocol():
    assert isinstance(_StubClient(), RenderClient)


async def test_fetch_returns_scraping_result_with_backend_metadata():
    client = _StubClient(html="<html>rendered body</html>")
    strategy = RemoteRenderStrategy(client)

    result = await strategy.fetch("https://example.com")

    assert result.content == "<html>rendered body</html>"
    assert result.status_code == 200
    assert result.strategy == "stub-render"
    assert result.metadata["rendered"] is True
    assert result.metadata["backend"] == "stub-render"
    assert client.calls == [("https://example.com", "networkidle0")]


async def test_name_override_and_wait_until_forwarded():
    client = _StubClient()
    strategy = RemoteRenderStrategy(client, name="cf-browser-rendering", wait_until="load")

    result = await strategy.fetch("https://example.com")

    assert result.strategy == "cf-browser-rendering"
    assert client.calls == [("https://example.com", "load")]


async def test_fetch_blocks_unsafe_url():
    strategy = RemoteRenderStrategy(_StubClient())
    with (
        patch("web_core.scraper.strategies.remote_render.is_safe_url", return_value=False),
        pytest.raises(ValueError, match="SSRF blocked"),
    ):
        await strategy.fetch("http://169.254.169.254/")


async def test_fetch_propagates_client_error_for_escalation():
    client = _StubClient(exc=RuntimeError("backend down"))
    strategy = RemoteRenderStrategy(client)
    with pytest.raises(RuntimeError, match="backend down"):
        await strategy.fetch("https://example.com")
