"""Tests for scraper utility functions: CF challenge detection."""

from web_core.scraper.utils import (
    detect_cloudflare_challenge,
    extract_turnstile_sitekey,
    is_cloudflare_challenge,
    looks_under_rendered,
    visible_text,
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


def test_extract_sitekey_none_on_normal_page():
    assert extract_turnstile_sitekey(NORMAL_HTML) is None


def test_extract_sitekey_none_on_empty():
    assert extract_turnstile_sitekey("") is None


def test_extract_sitekey_from_javascript_config():
    html = 'window._cf_chl_opt = { turnstileSiteKey: "0x4CCCCCCtest_sitekey_7654321" };'
    assert extract_turnstile_sitekey(html) == "0x4CCCCCCtest_sitekey_7654321"


def test_extract_sitekey_variations():
    # Single quotes
    html = "data-sitekey='0x4DDDDDtest_sitekey_9876543'"
    assert extract_turnstile_sitekey(html) == "0x4DDDDDtest_sitekey_9876543"

    # turnstileSiteKey with different spacing/quotes
    html = 'turnstileSiteKey : "0x4EEEEEEtest_sitekey_1111111"'
    assert extract_turnstile_sitekey(html) == "0x4EEEEEEtest_sitekey_1111111"

    # sitekey in URL without query param syntax (unlikely but test regex)
    html = "sitekey=0x4FFFFFFtest_sitekey_2222222"
    assert extract_turnstile_sitekey(html) == "0x4FFFFFFtest_sitekey_2222222"


def test_extract_sitekey_fast_path_miss():
    """Test when 'sitekey' is present but doesn't match any pattern."""
    html = "This page has the word sitekey but no actual key pattern."
    assert extract_turnstile_sitekey(html) is None

    html = "This page has the word siteKey but no actual key pattern."
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


# ---------------------------------------------------------------------------
# visible_text
# ---------------------------------------------------------------------------


def test_visible_text_strips_scripts_styles_and_tags():
    html = (
        "<html><head><style>.a{color:red}</style></head>"
        "<body><h1>Title</h1><script>var x = 1;</script><p>Body&nbsp;text.</p></body></html>"
    )
    text = visible_text(html)
    assert "Title" in text
    assert "Body" in text and "text." in text
    # Script / style contents must not leak into visible text.
    assert "var x" not in text
    assert "color:red" not in text


def test_visible_text_strips_script_end_tag_with_whitespace():
    # End tags with whitespace before ">" (</script >, </style\n>) are valid HTML
    # and must still be stripped, otherwise script/style contents leak into the
    # visible-text length count (CodeQL py/bad-tag-filter).
    html = (
        "<html><head><style>.a{color:red}</style >\n</head>"
        "<body><script>var secret = 1;</script\n><p>Body text.</p></body></html>"
    )
    text = visible_text(html)
    assert "Body text." in text
    assert "var secret" not in text
    assert "color:red" not in text


def test_visible_text_empty():
    assert visible_text("") == ""


def test_visible_text_unescapes_entities():
    assert visible_text("<p>A &amp; B &lt;ok&gt;</p>") == "A & B <ok>"


# ---------------------------------------------------------------------------
# looks_under_rendered
# ---------------------------------------------------------------------------

# An SPA shell: empty mount root + scripts + a Loading marker, no real content.
UNDER_RENDERED_SPA = (
    "<html><head><title>App</title></head><body>"
    '<div id="root"></div>'
    '<script src="/static/app.js"></script>'
    "<script>window.__INIT__ = {};</script>"
    "<p>Loading…</p></body></html>"
)

# A rendered page that ALSO has a script + SPA root, but real visible content.
RENDERED_WITH_SCRIPTS = (
    "<html><head><title>Quotes</title></head><body><div id='root'>"
    "<blockquote>The world as we have created it is a process of our thinking. "
    "It cannot be changed without changing our thinking. - Albert Einstein</blockquote>"
    "</div><script src='/app.js'></script></body></html>"
)

# Short but complete, no scripts -> must NOT be flagged (false-escalation guard).
TINY_JSON_API = '{"id": 1, "name": "ok", "status": "active"}'
TINY_ARTICLE = "<html><body><p>Short but complete.</p></body></html>"


def test_under_rendered_flags_spa_shell():
    assert looks_under_rendered(UNDER_RENDERED_SPA) is True


def test_under_rendered_flags_loading_with_empty_app_root():
    html = "<html><body><div id='app'>Loading…</div><script>boot()</script></body></html>"
    assert looks_under_rendered(html) is True


def test_under_rendered_false_for_rendered_page_with_scripts():
    # Visible text is well over the threshold, so the script + #root are ignored.
    assert looks_under_rendered(RENDERED_WITH_SCRIPTS) is False


def test_under_rendered_false_for_short_json_no_script():
    # Short body but no JS-render evidence -> a complete API response, not a shell.
    assert looks_under_rendered(TINY_JSON_API) is False


def test_under_rendered_false_for_tiny_article_no_script():
    assert looks_under_rendered(TINY_ARTICLE) is False


def test_under_rendered_false_for_empty():
    assert looks_under_rendered("") is False


def test_under_rendered_script_only_shell_flagged():
    # Pure inline-script bootstrap with no visible body text.
    html = "<html><body><script>document.write('later')</script></body></html>"
    assert looks_under_rendered(html) is True


def test_under_rendered_respects_custom_threshold():
    html = "<html><body><div id='root'>Hello</div><script>x()</script></body></html>"
    # "Hello" (5 chars) is under a high threshold -> flagged.
    assert looks_under_rendered(html, min_visible_text=100) is True
    # ...but under a tiny threshold the visible text already qualifies.
    assert looks_under_rendered(html, min_visible_text=4) is False
