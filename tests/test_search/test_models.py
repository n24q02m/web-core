"""Tests for search result and error models."""

from web_core.search.models import SearchError, SearchResult

# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_creation_minimal(self):
        result = SearchResult(url="https://example.com", title="Example", snippet="A snippet")
        assert result.url == "https://example.com"
        assert result.title == "Example"
        assert result.snippet == "A snippet"
        assert result.source == ""

    def test_creation_full(self):
        result = SearchResult(
            url="https://example.com",
            title="Example",
            snippet="A snippet",
            source="google",
        )
        assert result.url == "https://example.com"
        assert result.title == "Example"
        assert result.snippet == "A snippet"
        assert result.source == "google"

    def test_equality(self):
        a = SearchResult(url="https://example.com", title="T", snippet="S", source="g")
        b = SearchResult(url="https://example.com", title="T", snippet="S", source="g")
        assert a == b

    def test_inequality_different_url(self):
        a = SearchResult(url="https://a.com", title="T", snippet="S")
        b = SearchResult(url="https://b.com", title="T", snippet="S")
        assert a != b

    def test_empty_fields(self):
        result = SearchResult(url="", title="", snippet="")
        assert result.url == ""
        assert result.title == ""
        assert result.snippet == ""
        assert result.source == ""

    def test_to_dict(self):
        result = SearchResult(
            url="https://example.com",
            title="T",
            snippet="S",
            source="google",
        )
        assert result.to_dict() == {
            "url": "https://example.com",
            "title": "T",
            "snippet": "S",
            "source": "google",
        }


# ---------------------------------------------------------------------------
# SearchError
# ---------------------------------------------------------------------------


class TestSearchError:
    """Test SearchError exception."""

    def test_creation(self):
        err = SearchError("python tutorial", "HTTP 429")
        assert err.query == "python tutorial"
        assert err.reason == "HTTP 429"

    def test_str_representation(self):
        err = SearchError("python tutorial", "HTTP 429")
        assert str(err) == "Search failed for 'python tutorial': HTTP 429"

    def test_is_exception(self):
        err = SearchError("q", "reason")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self):
        try:
            raise SearchError("test query", "timeout")
        except SearchError as e:
            assert e.query == "test query"
            assert e.reason == "timeout"
        else:
            raise AssertionError("SearchError was not raised")

    def test_message_includes_query_and_reason(self):
        err = SearchError("complex query with spaces", "connection refused")
        msg = str(err)
        assert "complex query with spaces" in msg
        assert "connection refused" in msg
