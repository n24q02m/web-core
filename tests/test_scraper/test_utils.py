"""Tests for scraper utility functions: CF challenge detection."""

from web_core.scraper.utils import (
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


def test_detect_short():
    assert detect_cloudflare_challenge(SHORT_HTML) is None


def test_detect_cdn_cgi_challenge_platform():
    html = '<script src="/cdn-cgi/challenge-platform/scripts/main.js"></script>'
    assert detect_cloudflare_challenge(html) == "turnstile"


def test_detect_verifying_human():
    html = "<title>Verifying you are human</title><body>Please wait...</body>"
    assert detect_cloudflare_challenge(html) == "js_challenge"


def test_detect_jschl_answer():
    html = '<form id="challenge-form"><input name="jschl-answer" value=""></form>'
    assert detect_cloudflare_challenge(html) == "js_challenge"


def test_detect_newtoki_security_verification():
    """Newtoki-style CF managed challenge."""
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


def test_extract_sitekey_none_on_normal_page():
    assert extract_turnstile_sitekey(NORMAL_HTML) is None


def test_extract_sitekey_none_on_empty():
    assert extract_turnstile_sitekey("") is None


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
