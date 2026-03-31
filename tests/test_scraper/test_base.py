"""Tests for scraper base types."""

from __future__ import annotations

import pytest

from web_core.scraper.base import BaseStrategy, ScrapingResult

# ---------------------------------------------------------------------------
# ScrapingResult
# ---------------------------------------------------------------------------


class TestScrapingResult:
    """Test ScrapingResult dataclass."""

    def test_creation_minimal(self):
        result = ScrapingResult(
            content="<html>hello</html>",
            url="https://example.com",
            strategy="basic_http",
            status_code=200,
        )
        assert result.content == "<html>hello</html>"
        assert result.url == "https://example.com"
        assert result.strategy == "basic_http"
        assert result.status_code == 200
        assert result.metadata == {}

    def test_creation_with_metadata(self):
        meta = {"content_type": "text/html", "content_length": 42}
        result = ScrapingResult(
            content="<html>hello</html>",
            url="https://example.com",
            strategy="tls_spoof",
            status_code=200,
            metadata=meta,
        )
        assert result.metadata == {"content_type": "text/html", "content_length": 42}

    def test_metadata_default_is_independent(self):
        """Each instance should get its own metadata dict."""
        a = ScrapingResult(content="", url="", strategy="a", status_code=200)
        b = ScrapingResult(content="", url="", strategy="b", status_code=200)
        a.metadata["key"] = "value"
        assert "key" not in b.metadata

    def test_equality(self):
        kwargs = {"content": "x", "url": "u", "strategy": "s", "status_code": 200}
        assert ScrapingResult(**kwargs) == ScrapingResult(**kwargs)

    def test_inequality_different_status(self):
        base = {"content": "x", "url": "u", "strategy": "s"}
        assert ScrapingResult(**base, status_code=200) != ScrapingResult(**base, status_code=404)


# ---------------------------------------------------------------------------
# BaseStrategy
# ---------------------------------------------------------------------------


class TestBaseStrategy:
    """Test BaseStrategy abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseStrategy()  # type: ignore[abstract]

    def test_subclass_without_fetch_raises_type_error(self):
        """A concrete subclass that does not implement fetch cannot be instantiated."""

        class Incomplete(BaseStrategy):
            name = "incomplete"

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        """A subclass that implements fetch can be instantiated."""

        class Concrete(BaseStrategy):
            name = "concrete"

            async def fetch(self, url, selectors=None):
                return ScrapingResult(content="ok", url=url, strategy=self.name, status_code=200)

        strategy = Concrete()
        assert strategy.name == "concrete"

    async def test_concrete_subclass_fetch(self):
        """Verify that a concrete subclass's fetch actually works."""

        class Concrete(BaseStrategy):
            name = "concrete"

            async def fetch(self, url, selectors=None):
                return ScrapingResult(content="ok", url=url, strategy=self.name, status_code=200)

        strategy = Concrete()
        result = await strategy.fetch("https://example.com")
        assert result.content == "ok"
        assert result.strategy == "concrete"
