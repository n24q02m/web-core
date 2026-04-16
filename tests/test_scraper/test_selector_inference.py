"""Tests for selector inference utility functions."""

import importlib
import json
import sys
from unittest.mock import MagicMock

from web_core.scraper import selector_inference
from web_core.scraper.selector_inference import merge_selectors


def test_merge_selectors_disjoint():
    existing = {"title": ".title"}
    inferred = {"content": "#content"}
    expected = {"title": ".title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_existing_priority():
    existing = {"title": ".existing-title"}
    inferred = {"title": ".inferred-title", "content": "#content"}
    expected = {"title": ".existing-title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_empty_existing_uses_inferred():
    existing = {"title": ""}
    inferred = {"title": ".inferred-title", "content": "#content"}
    expected = {"title": ".inferred-title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_missing_existing_uses_inferred():
    existing = {"content": "#content"}
    inferred = {"title": ".inferred-title"}
    expected = {"content": "#content", "title": ".inferred-title"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_all_empty():
    assert merge_selectors({}, {}) == {}


def test_merge_selectors_no_inferred():
    existing = {"title": ".title"}
    assert merge_selectors(existing, {}) == {"title": ".title"}


def test_merge_selectors_no_existing():
    inferred = {"title": ".title"}
    assert merge_selectors({}, inferred) == {"title": ".title"}


def test_get_domain_selectors_wildcard():
    # Mock heavy dependencies imported at module level in src/web_core/__init__.py
    sys.modules["httpx"] = MagicMock()
    sys.modules["langgraph"] = MagicMock()
    sys.modules["langgraph.graph"] = MagicMock()
    sys.modules["google.genai"] = MagicMock()

    from web_core.scraper.selector_inference import get_domain_selectors

    # Valid matches
    assert get_domain_selectors("https://newtoki123.com") is not None
    assert get_domain_selectors("https://newtoki.com") is not None

    # Invalid matches (fixed wildcard-bypass vulnerabilities)
    assert get_domain_selectors("https://newtoki.com.evil.com") is None
    assert get_domain_selectors("https://evilnewtoki.com") is None
    assert get_domain_selectors("https://newtoki.com.co") is None

    # Non-wildcard exact matches
    assert get_domain_selectors("https://ncode.syosetu.com") is not None
    assert get_domain_selectors("https://ncode.syosetu.com.evil.com") is None


def test_load_domain_cookies_from_env(monkeypatch):
    # Mock environment variable
    custom_cookies = {"test.com": {"cookie_name": "cookie_value"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))

    # Reload module to re-initialize DOMAIN_COOKIES
    importlib.reload(selector_inference)

    assert selector_inference.DOMAIN_COOKIES["test.com"] == {"cookie_name": "cookie_value"}
    assert "novel18.syosetu.com" not in selector_inference.DOMAIN_COOKIES


def test_load_domain_cookies_empty_env(monkeypatch):
    # Mock empty/missing environment variable
    monkeypatch.delenv("WEB_CORE_DOMAIN_COOKIES", raising=False)

    # Reload module
    importlib.reload(selector_inference)

    # It should be empty if we remove the hardcoded ones
    assert selector_inference.DOMAIN_COOKIES == {}


def test_get_domain_selectors_injects_cookies(monkeypatch):
    custom_cookies = {"novel18.syosetu.com": {"over18": "yes"}}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))
    importlib.reload(selector_inference)

    url = "https://novel18.syosetu.com/n1234abc/"
    selectors = selector_inference.get_domain_selectors(url)

    assert selectors is not None
    assert selectors["cookies"] == {"over18": "yes"}


def test_load_domain_cookies_invalid_json(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "invalid-json")

    # Should log an error and fallback to empty dict
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}
