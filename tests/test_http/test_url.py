from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from web_core.http.url import (
    _TRACKING_PARAMS,
    extract_domain,
    is_valid_domain,
    normalize_url,
    strip_tracking_params,
)


class TestNormalizeUrl:
    """Test URL normalization logic."""

    def test_lowercases_host_and_scheme(self):
        result = normalize_url("HTTPS://EXAMPLE.COM/Path")
        assert result == "https://example.com/Path"

    def test_strips_www_prefix(self):
        result = normalize_url("https://www.example.com/path")
        assert result == "https://example.com/path"

    def test_strips_trailing_slash(self):
        result = normalize_url("https://example.com/path/")
        assert result == "https://example.com/path"

    def test_strips_fragment(self):
        result = normalize_url("https://example.com/path#section")
        assert result == "https://example.com/path"

    def test_strips_utm_source(self):
        result = normalize_url("https://example.com/?utm_source=twitter&title=hello")
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

    def test_urlsplit_exception_returns_original(self):
        """If urlsplit raises, the original URL string is returned unchanged."""
        raw = "https://example.com/page"
        with patch("web_core.http.url.urlsplit", side_effect=Exception("parse fail")):
            assert normalize_url(raw) == raw

    def test_preserves_port(self):
        result = normalize_url("https://example.com:8080/path")
        assert result == "https://example.com:8080/path"

    def test_duplicate_tracking_params(self):
        result = normalize_url("https://example.com/?utm_source=a&utm_source=b")
        assert "?" not in result

    def test_preserves_order_of_duplicate_non_tracking_params(self):
        url = "https://example.com/?tag=first&other=value&tag=second&utm_source=ignored"
        assert normalize_url(url) == "https://example.com?tag=first&other=value&tag=second"

    def test_preserves_blank_non_tracking_values(self):
        url = "https://example.com/?keep=&utm_source=ignored"
        assert normalize_url(url) == "https://example.com?keep="

    def test_empty_tracking_param_value(self):
        result = normalize_url("https://example.com/?utm_source=")
        assert "?" not in result

    def test_no_value_tracking_param(self):
        result = normalize_url("https://example.com/?utm_source")
        assert "?" not in result

    def test_near_tracking_param_match(self):
        url = "https://example.com/?not_utm_source=a"
        assert normalize_url(url) == "https://example.com?not_utm_source=a"

    def test_www_in_middle_of_domain(self):
        url = "https://mywwwsite.com"
        assert normalize_url(url) == url

    def test_www_start_of_subdomain(self):
        url = "https://sub.www.example.com"
        assert normalize_url(url) == url

    def test_multiple_trailing_slashes(self):
        result = normalize_url("https://example.com/path///")
        assert result == "https://example.com/path"

    def test_short_tracking_params(self):
        result = normalize_url("https://example.com/?s=1&ref=2&ref_src=3")
        assert "?" not in result

    def test_encoded_path(self):
        url = "https://example.com/path%20with%20space"
        assert normalize_url(url) == url

    def test_preserves_params_section(self):
        """Test that the rarely used 'params' section (after ;) is preserved."""
        url = "https://example.com/path;matrix=1?q=test"
        result = normalize_url(url)
        assert ";matrix=1" in result
        assert "q=test" in result

    def test_multiple_trailing_slashes_root(self):
        result = normalize_url("https://example.com///")
        assert result == "https://example.com"


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

    @pytest.mark.parametrize("param", sorted(_TRACKING_PARAMS))
    def test_strips_all_tracking_params(self, param):
        """Verify every parameter in the tracking set is correctly stripped."""
        url = f"https://example.com/page?{param}=value&keep=me"
        result = strip_tracking_params(url)
        parsed = urlparse(result)
        params = parse_qs(parsed.query)
        assert param not in params
        assert params["keep"] == ["me"]

    def test_full_normalization_applied(self):
        """Verify that full normalization is applied as documented."""
        url = "HTTPS://WWW.Example.com/Path/#fragment?utm_source=track"
        # normalize_url strips fragment, trailing slash, www, and lowercases
        expected = "https://example.com/Path"
        assert strip_tracking_params(url) == expected

    def test_complex_url_mixed_params(self):
        """Test a complex URL with multiple tracking and legitimate parameters."""
        url = (
            "https://example.com/search?q=python&utm_source=google&page=1&fbclid=abc123&utm_campaign=winter&ref=sidebar"
        )
        result = strip_tracking_params(url)
        assert "q=python" in result
        assert "page=1" in result
        assert "utm_source" not in result
        assert "fbclid" not in result
        assert "utm_campaign" not in result
        assert "ref" not in result

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
# extract_domain
# ---------------------------------------------------------------------------


class TestExtractDomain:
    """Test domain extraction from various URL formats."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com/path", "example.com"),
            ("http://sub.example.com/path?q=1", "sub.example.com"),
            ("//example.com/path", "example.com"),
            ("example.com/path", "example.com"),
            ("https://example.com:8080/path", "example.com:8080"),
            ("https://example.com#fragment", "example.com"),
            ("https://example.com?query", "example.com"),
            ("https://user:pass@example.com", "user:pass@example.com"),
            ("", ""),
            ("/", ""),
            ("//", ""),
            ("http://", ""),
        ],
    )
    def test_extract_domain(self, url, expected):
        assert extract_domain(url) == expected


# ---------------------------------------------------------------------------
# is_valid_domain
# ---------------------------------------------------------------------------


class TestIsValidDomain:
    """Test domain name validation."""

    @pytest.mark.parametrize(
        "domain,expected",
        [
            # Valid cases
            ("example.com", True),
            ("sub.example.com", True),
            ("a.b.c.example.com", True),
            ("my-site.example.com", True),
            ("site.london", True),
            ("my_site.com", True),
            # Invalid cases
            ("", False),
            ("localhost", False),
            ("com", False),
            ("192.168.1.1", False),
            ("exam!ple.com", False),
            ("example..com", False),
            (".example.com", False),
            ("-example.com", False),
            ("example .com", False),
            ("exampl\u00e9.com", False),
            ("site:evil.com", False),
            ("example.com\n", False),
            ("example.c", False),
            ("example.123", False),
            ("example.", False),
            ("example.-com", False),
            ("example.com-", False),
        ],
    )
    def test_is_valid_domain(self, domain, expected):
        assert is_valid_domain(domain) is expected
