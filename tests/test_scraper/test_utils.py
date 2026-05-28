"""Tests for scraper utility functions: CF challenge detection."""

import pytest

from web_core.scraper.utils import (
    _CF_JS_CHALLENGE_STRINGS,
    _CF_MANAGED_STRINGS,
    _CF_TURNSTILE_STRINGS,
    detect_cloudflare_challenge,
    extract_turnstile_sitekey,
    is_cloudflare_challenge,
)

# ---------------------------------------------------------------------------
# Sample HTML snippets for testing
# ---------------------------------------------------------------------------

CF_TURNSTILE_HTML = """
<html><head><title>Attention Required</title></head>
<body>
<div id="cf-turnstile-container">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<div class="cf-turnstile" data-sitekey="0x4AAAAAAAB1234567890abcdef"></div>
<input type="hidden" name="cf-turnstile-response" value="">
</div></body></html>
"""

CF_JS_CHALLENGE_HTML = """
<html><head><title>Just a moment...</title></head>
<body>
<div id="cf-browser-verification">
<noscript><h1>Checking your browser before accessing example.com</h1></noscript>
</div></body></html>
"""

CF_MANAGED_HTML = """
<html><head><title>Please wait</title></head>
<body>
<div id="cf-please-wait">
<p class="managed_checking_msg">Please stand by, while we are checking your browser...</p>
</div></body></html>
"""

NORMAL_HTML = """
<html><head><title>My Website</title></head>
<body><h1>Hello World</h1><p>Welcome to my website.</p></body></html>
"""

EMPTY_HTML = ""

SHORT_HTML = "<h1>Hi</h1>"


# ---------------------------------------------------------------------------
# detect_cloudflare_challenge
# ---------------------------------------------------------------------------


def test_detect_turnstile():
    assert detect_cloudflare_challenge(CF_TURNSTILE_HTML) == "turnstile"


def test_detect_js_challenge():
    assert detect_cloudflare_challenge(CF_JS_CHALLENGE_HTML) == "js_challenge"


def test_detect_managed():
    assert detect_cloudflare_challenge(CF_MANAGED_HTML) == "managed"


def test_detect_normal_page():
    assert detect_cloudflare_challenge(NORMAL_HTML) is None


def test_detect_empty():
    assert detect_cloudflare_challenge(EMPTY_HTML) is None
    assert detect_cloudflare_challenge(None) is None  # type: ignore


def test_detect_short():
    assert detect_cloudflare_challenge(SHORT_HTML) is None
    # Boundary check: length 49 vs 50
    assert detect_cloudflare_challenge("a" * 49) is None
    # Length 50 with a marker
    assert detect_cloudflare_challenge("a" * 40 + _CF_JS_CHALLENGE_STRINGS[0]) == "js_challenge"


@pytest.mark.parametrize("marker", _CF_TURNSTILE_STRINGS)
def test_detect_all_turnstile_markers(marker):
    html = f"<html><body>{'a' * 50} {marker}</body></html>"
    assert detect_cloudflare_challenge(html) == "turnstile"


@pytest.mark.parametrize("marker", _CF_MANAGED_STRINGS)
def test_detect_all_managed_markers(marker):
    html = f"<html><body>{'a' * 50} {marker}</body></html>"
    assert detect_cloudflare_challenge(html) == "managed"


@pytest.mark.parametrize("marker", _CF_JS_CHALLENGE_STRINGS)
def test_detect_all_js_challenge_markers(marker):
    html = f"<html><body>{'a' * 50} {marker}</body></html>"
    assert detect_cloudflare_challenge(html) == "js_challenge"


def test_detect_case_insensitivity():
    marker = _CF_TURNSTILE_STRINGS[0].upper()
    html = f"<html><body>{'a' * 50} {marker}</body></html>"
    assert detect_cloudflare_challenge(html) == "turnstile"


def test_detect_priority():
    # Turnstile has priority over others
    html = (
        f"<html><body>{'a' * 50} {_CF_TURNSTILE_STRINGS[0]} "
        f"{_CF_MANAGED_STRINGS[0]} {_CF_JS_CHALLENGE_STRINGS[0]}</body></html>"
    )
    assert detect_cloudflare_challenge(html) == "turnstile"

    # Managed has priority over JS Challenge
    html = f"<html><body>{'a' * 50} {_CF_MANAGED_STRINGS[0]} {_CF_JS_CHALLENGE_STRINGS[0]}</body></html>"
    assert detect_cloudflare_challenge(html) == "managed"


def test_detect_cdn_cgi_challenge_platform():
    html = '<script src="/cdn-cgi/challenge-platform/scripts/main.js"></script>'
    # This is 67 chars, so it should be detected
    assert detect_cloudflare_challenge(html) == "turnstile"


def test_detect_verifying_human():
    html = "<title>Verifying you are human</title><body>Please wait...</body>"
    assert detect_cloudflare_challenge(html) == "js_challenge"


def test_detect_jschl_answer():
    html = '<form id="challenge-form"><input name="jschl-answer" value=""></form>'
    assert detect_cloudflare_challenge(html) == "js_challenge"


def test_detect_cf_managed_security_verification():
    """Generic Cloudflare-managed challenge fingerprint detection."""
    html = """<html><body>
    <p>This website uses a security service to protect against malicious bots.</p>
    <p>This page is displayed while the website verifies you are not a bot.</p>
    <h2>Performing security verification</h2>
    </body></html>"""
    assert detect_cloudflare_challenge(html) == "managed"


# ---------------------------------------------------------------------------
# extract_turnstile_sitekey
# ---------------------------------------------------------------------------


def test_extract_sitekey_from_data_attribute():
    assert extract_turnstile_sitekey(CF_TURNSTILE_HTML) == "0x4AAAAAAAB1234567890abcdef"


def test_extract_sitekey_from_query_param():
    html = '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js?sitekey=0x4BBBBBtest_sitekey_1234567"></script>'
    assert extract_turnstile_sitekey(html) == "0x4BBBBBtest_sitekey_1234567"


def test_extract_sitekey_from_turnstile_sitekey_field():
    html = 'const options = { turnstileSiteKey: "0x4CCCCCCCtest_sitekey_8901234" };'
    assert extract_turnstile_sitekey(html) == "0x4CCCCCCCtest_sitekey_8901234"


def test_extract_sitekey_none_on_normal_page():
    assert extract_turnstile_sitekey(NORMAL_HTML) is None


def test_extract_sitekey_none_on_empty():
    assert extract_turnstile_sitekey("") is None


def test_extract_sitekey_keyword_present_but_no_match():
    # Sitekey is present in text but not in a format that matches patterns
    html = "<html><body>The sitekey is not here.</body></html>"
    assert extract_turnstile_sitekey(html) is None


# ---------------------------------------------------------------------------
# is_cloudflare_challenge
# ---------------------------------------------------------------------------


def test_is_cf_challenge_true():
    assert is_cloudflare_challenge(CF_TURNSTILE_HTML) is True
    assert is_cloudflare_challenge(CF_JS_CHALLENGE_HTML) is True
    assert is_cloudflare_challenge(CF_MANAGED_HTML) is True


def test_is_cf_challenge_false():
    assert is_cloudflare_challenge(NORMAL_HTML) is False
    assert is_cloudflare_challenge("") is False
