"""Tests for scraping state and error types."""

from __future__ import annotations

from typing import get_type_hints

from web_core.scraper.state import ScrapingError, ScrapingState

# ---------------------------------------------------------------------------
# ScrapingError
# ---------------------------------------------------------------------------


class TestScrapingError:
    """Test ScrapingError exception."""

    def test_creation(self):
        err = ScrapingError(
            url="https://example.com",
            strategies_tried=["basic_http", "tls_spoof"],
            final_error="Connection refused",
        )
        assert err.url == "https://example.com"
        assert err.strategies_tried == ["basic_http", "tls_spoof"]
        assert err.final_error == "Connection refused"

    def test_str_representation(self):
        err = ScrapingError(
            url="https://example.com",
            strategies_tried=["basic_http"],
            final_error="timeout",
        )
        msg = str(err)
        assert "https://example.com" in msg
        assert "basic_http" in msg
        assert "timeout" in msg

    def test_is_exception(self):
        err = ScrapingError(url="u", strategies_tried=[], final_error="e")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self):
        try:
            raise ScrapingError(
                url="https://example.com",
                strategies_tried=["a", "b"],
                final_error="all failed",
            )
        except ScrapingError as e:
            assert e.url == "https://example.com"
            assert len(e.strategies_tried) == 2
        else:
            raise AssertionError("ScrapingError was not raised")

    def test_empty_strategies(self):
        err = ScrapingError(url="u", strategies_tried=[], final_error="no strategies")
        assert "[]" in str(err)


# ---------------------------------------------------------------------------
# ScrapingState
# ---------------------------------------------------------------------------


class TestScrapingState:
    """Test ScrapingState TypedDict."""

    def test_is_typed_dict(self):
        """ScrapingState should be usable as a TypedDict."""
        hints = get_type_hints(ScrapingState)
        assert "url" in hints
        assert "selectors" in hints
        assert "strategy_order" in hints
        assert "current_strategy_idx" in hints
        assert "content" in hints
        assert "status_code" in hints
        assert "success" in hints
        assert "strategies_tried" in hints
        assert "errors" in hints
        assert "metadata" in hints

    def test_creation_partial(self):
        """All keys are optional (total=False) so partial dicts are valid."""
        state: ScrapingState = {"url": "https://example.com"}
        assert state["url"] == "https://example.com"

    def test_creation_full(self):
        state: ScrapingState = {
            "url": "https://example.com",
            "selectors": {"title": "h1"},
            "strategy_order": ["basic_http", "tls_spoof"],
            "current_strategy_idx": 0,
            "content": "<html></html>",
            "status_code": 200,
            "success": True,
            "strategies_tried": ["basic_http"],
            "errors": [],
            "metadata": {"extra": "data"},
        }
        assert state["success"] is True
        assert len(state["strategy_order"]) == 2
