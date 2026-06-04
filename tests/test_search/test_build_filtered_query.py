from web_core.search.client import _build_filtered_query


def test_build_filtered_query_basic():
    """Simple query without domain filters."""
    assert _build_filtered_query("python") == "python"


def test_build_filtered_query_special_chars():
    """Query with special characters."""
    query = "python & (search | query) -stuff"
    assert _build_filtered_query(query) == query


def test_build_filtered_query_long_query():
    """Extremely long query string."""
    query = "a" * 1000
    assert _build_filtered_query(query) == query


def test_build_filtered_query_include_domains_basic():
    """Include domains are joined with OR site:."""
    result = _build_filtered_query("python", include_domains=["example.com", "test.org"])
    assert result == "(site:example.com OR site:test.org) python"


def test_build_filtered_query_include_domains_cap():
    """Include domains are capped at 5."""
    domains = [f"d{i}.com" for i in range(10)]
    result = _build_filtered_query("python", include_domains=domains)
    assert result == "(site:d0.com OR site:d1.com OR site:d2.com OR site:d3.com OR site:d4.com) python"


def test_build_filtered_query_include_domains_dedup():
    """Include domains are deduplicated."""
    result = _build_filtered_query("python", include_domains=["a.com", "a.com", "b.com"])
    assert result == "(site:a.com OR site:b.com) python"


def test_build_filtered_query_include_domains_invalid():
    """Invalid include domains are skipped."""
    result = _build_filtered_query("python", include_domains=["valid.com", "invalid", "also..invalid.com"])
    assert result == "(site:valid.com) python"


def test_build_filtered_query_include_domains_only_invalid():
    """If all include domains are invalid, no site filter is added."""
    result = _build_filtered_query("python", include_domains=["invalid", "bad..domain"])
    assert result == "python"


def test_build_filtered_query_exclude_domains_basic():
    """Exclude domains are prepended with -site:."""
    result = _build_filtered_query("python", exclude_domains=["spam.com", "junk.org"])
    assert result == "python -site:spam.com -site:junk.org"


def test_build_filtered_query_exclude_domains_cap():
    """Exclude domains are capped at 10."""
    domains = [f"e{i}.com" for i in range(15)]
    result = _build_filtered_query("python", exclude_domains=domains)
    expected = "python"
    for i in range(10):
        expected += f" -site:e{i}.com"
    assert result == expected


def test_build_filtered_query_exclude_domains_dedup():
    """Exclude domains are deduplicated."""
    result = _build_filtered_query("python", exclude_domains=["x.com", "x.com", "y.com"])
    assert result == "python -site:x.com -site:y.com"


def test_build_filtered_query_exclude_domains_invalid():
    """Invalid exclude domains are skipped."""
    result = _build_filtered_query("python", exclude_domains=["valid.com", "invalid"])
    assert result == "python -site:valid.com"


def test_build_filtered_query_exclude_domains_only_invalid():
    """If all exclude domains are invalid, nothing is added."""
    result = _build_filtered_query("python", exclude_domains=["invalid"])
    assert result == "python"


def test_build_filtered_query_combined():
    """Include and exclude domains combined."""
    result = _build_filtered_query("python", include_domains=["inc.com"], exclude_domains=["exc.com"])
    assert result == "(site:inc.com) python -site:exc.com"


def test_build_filtered_query_none_lists():
    """Lists being None should be handled correctly."""
    assert _build_filtered_query("python", include_domains=None, exclude_domains=None) == "python"


def test_build_filtered_query_empty_query():
    """Empty query string."""
    assert _build_filtered_query("") == ""


def test_build_filtered_query_whitespace_query():
    """Whitespace query string."""
    assert _build_filtered_query("   ") == "   "
