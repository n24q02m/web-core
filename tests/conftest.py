"""Shared test fixtures for web-core."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_httpx_response():
    """Factory for mock httpx responses."""

    def _make(status_code: int = 200, text: str = "", headers: dict | None = None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        resp.headers = headers or {"content-type": "text/html"}
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        return resp

    return _make


@pytest.fixture
def mock_httpx_client(mock_httpx_response):
    """Mock httpx.AsyncClient."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=mock_httpx_response(200, "<html>test</html>"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client
