"""Tests for URL normalization and domain validation."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from web_core.http.url import (
    _TRACKING_PARAMS,
    is_valid_domain,
    normalize_url,
    strip_tracking_params,
)

# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------


class TestNormalizeUrl:
    """Test URL normalization for deduplication."""

    def test_strips_fragment(self):
        result = normalize_url("https://example.com/page#section")
        assert "#" not in result
        assert result == "https://example.com/page"

    def test_strips_trailing_slash(self):
        result = normalize_url("https://example.com/page/")
        assert result == "https://example.com/page"

    def test_lowercases_scheme(self):
        result = normalize_url("HTTPS://example.com/page")
        assert result.startswith("https://")

    def test_lowercases_host(self):
        result = normalize_url("https://EXAMPLE.COM/page")
        assert "example.com" in result

    def test_strips_www_prefix(self):
        result = normalize_url("https://www.example.com/page")
        assert "www." not in result
        assert result == "https://example.com/page"

    def test_strips_utm_source(self):
        result = normalize_url("https://example.com/page?utm_source=twitter&title=hello")
        assert "utm_source" not in result
        assert "title=hello" in result

    def test_strips_utm_medium(self):
        result = normalize_url("https://example.com/?utm_medium=social")
        assert "utm_medium" not in result

    def test_strips_utm_campaign(self):
        result = normalize_url("https://example.com/?utm_campaign=launch")
        assert "utm_campaign" not in result

    def test_strips_fbclid(self):
        result = normalize_url("https://example.com/post?fbclid=abc123")
        assert "fbclid" not in result

    def test_strips_gclid(self):
        result = normalize_url("https://example.com/ad?gclid=xyz789")
        assert "gclid" not in result

    def test_strips_msclkid(self):
        result = normalize_url("https://example.com/?msclkid=ms123")
        assert "msclkid" not in result

    def test_preserves_non_tracking_params(self):
        result = normalize_url("https://example.com/search?q=python&page=2")
        assert "q=python" in result
        assert "page=2" in result

    def test_empty_string_returns_empty(self):
        assert normalize_url("") == ""

    def test_no_query_params(self):
        result = normalize_url("https://example.com/page")
        assert result == "https://example.com/page"

    def test_all_tracking_params_stripped(self):
        """When all params are tracking, query string should be empty."""
        result = normalize_url("https://example.com/?utm_source=x&fbclid=y&gclid=z")
        assert "?" not in result or result.endswith("?")
        # Verify none of the tracking params remain
        assert "utm_source" not in result
        assert "fbclid" not in result
        assert "gclid" not in result

    def test_preserves_path_case(self):
        """Path should preserve case (unlike host)."""
        result = normalize_url("https://example.com/CaseSensitive")
        assert "/CaseSensitive" in result

    def test_root_path_normalization(self):
        """Root path (just slash) should normalize to empty path."""
        result = normalize_url("https://example.com/")
        assert result == "https://example.com"

    def test_mixed_tracking_and_normal_params(self):
        url = "https://example.com/page?q=search&utm_source=google&page=1&fbclid=abc"
        result = normalize_url(url)
        assert "q=search" in result
        assert "page=1" in result
        assert "utm_source" not in result
        assert "fbclid" not in result

    def test_urlparse_exception_returns_original(self):
        """If urlparse raises, the original URL string is returned unchanged."""
        raw = "https://example.com/page"
        with patch("web_core.http.url.urlparse", side_effect=Exception("parse fail")):
            assert normalize_url(raw) == raw


class TestTrackingParams:
    """Verify the tracking params set is comprehensive."""

    @pytest.mark.parametrize(
        "param",
        [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "utm_id",
            "utm_cid",
            "fbclid",
            "gclid",
            "gclsrc",
            "msclkid",
            "mc_cid",
            "mc_eid",
            "yclid",
            "twclid",
            "igshid",
            "s",
            "ref",
            "ref_src",
        ],
    )
    def test_tracking_param_in_set(self, param):
        assert param in _TRACKING_PARAMS


# ---------------------------------------------------------------------------
# strip_tracking_params
# ---------------------------------------------------------------------------


class TestStripTrackingParams:
    """Test tracking param stripping (alias for normalize_url)."""

    def test_strips_utm_params(self):
        result = strip_tracking_params("https://example.com/?utm_source=x&utm_medium=y")
        assert "utm_source" not in result
        assert "utm_medium" not in result

    def test_strips_fbclid(self):
        result = strip_tracking_params("https://example.com/?fbclid=abc")
        assert "fbclid" not in result

    def test_strips_gclid(self):
        result = strip_tracking_params("https://example.com/?gclid=def")
        assert "gclid" not in result

    def test_no_params_unchanged(self):
        result = strip_tracking_params("https://example.com/page")
        assert result == "https://example.com/page"

    def test_preserves_legitimate_params(self):
        result = strip_tracking_params("https://example.com/?q=test&utm_source=x")
        assert "q=test" in result
        assert "utm_source" not in result


# ---------------------------------------------------------------------------
# is_valid_domain
# ---------------------------------------------------------------------------


class TestIsValidDomain:
    """Test domain name validation."""

    def test_valid_domain(self):
        assert is_valid_domain("example.com") is True

    def test_valid_subdomain(self):
        assert is_valid_domain("sub.example.com") is True

    def test_valid_deep_subdomain(self):
        assert is_valid_domain("a.b.c.example.com") is True

    def test_valid_hyphenated_domain(self):
        assert is_valid_domain("my-site.example.com") is True

    def test_empty_returns_false(self):
        assert is_valid_domain("") is False

    def test_ip_address_returns_false(self):
        assert is_valid_domain("192.168.1.1") is False

    def test_special_chars_returns_false(self):
        assert is_valid_domain("exam!ple.com") is False

    def test_double_dots_returns_false(self):
        assert is_valid_domain("example..com") is False

    def test_no_tld_returns_false(self):
        """Single label without TLD is not a valid domain."""
        assert is_valid_domain("localhost") is False

    def test_starts_with_dot_returns_false(self):
        assert is_valid_domain(".example.com") is False

    def test_starts_with_hyphen_returns_false(self):
        assert is_valid_domain("-example.com") is False

    def test_space_in_domain_returns_false(self):
        assert is_valid_domain("example .com") is False

    def test_unicode_domain_returns_false(self):
        """Punycode should be used for international domains."""
        assert is_valid_domain("exampl\u00e9.com") is False

    def test_search_operator_injection_blocked(self):
        """Domains with operators like site:evil.com should be rejected."""
        assert is_valid_domain("site:evil.com") is False

    def test_trailing_newline_returns_false(self):
        """Trailing newlines should be rejected to prevent bypasses."""
        assert is_valid_domain("example.com\n") is False
