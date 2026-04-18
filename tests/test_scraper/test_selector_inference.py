"""Tests for selector inference utility functions."""

import sys
from unittest.mock import MagicMock

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
