import importlib
import json

from web_core.scraper import selector_inference


def test_load_domain_cookies_from_env(monkeypatch):
    # Mock environment variable
    custom_cookies = {"test.com": {"cookie_name": "cookie_value"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))

    # Reload module to re-initialize DOMAIN_COOKIES
    importlib.reload(selector_inference)

    # Should contain BOTH default and custom cookies
    assert "novel18.syosetu.com" in selector_inference.DOMAIN_COOKIES
    assert selector_inference.DOMAIN_COOKIES["test.com"] == {"cookie_name": "cookie_value"}


def test_load_domain_cookies_override_default(monkeypatch):
    # Mock environment variable overriding default
    custom_cookies = {"novel18.syosetu.com": {"over18": "no"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))

    # Reload module
    importlib.reload(selector_inference)

    assert selector_inference.DOMAIN_COOKIES["novel18.syosetu.com"] == {"over18": "no"}


def test_load_domain_cookies_empty_env(monkeypatch):
    # Mock empty/missing environment variable
    monkeypatch.delenv("WEB_CORE_DOMAIN_COOKIES", raising=False)

    # Reload module
    importlib.reload(selector_inference)

    # It should still have the default ones
    assert selector_inference.DOMAIN_COOKIES == {"novel18.syosetu.com": {"over18": "yes"}}


def test_get_domain_selectors_injects_cookies(monkeypatch):
    custom_cookies = {"ncode.syosetu.com": {"test": "val"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))
    importlib.reload(selector_inference)

    url = "https://ncode.syosetu.com/n1234abc/"
    selectors = selector_inference.get_domain_selectors(url)

    assert selectors is not None
    assert selectors["cookies"] == {"test": "val"}


def test_load_domain_cookies_invalid_json(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "invalid-json")

    # Should log an error and fallback to default dict
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {"novel18.syosetu.com": {"over18": "yes"}}
