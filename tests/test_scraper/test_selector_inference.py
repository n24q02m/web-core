"""Tests for LLM-based CSS selector inference utility functions."""

from web_core.scraper.selector_inference import merge_selectors


def test_merge_selectors_basic():
    """Test basic merge where inferred provides values for empty existing ones."""
    existing = {"title": ""}
    inferred = {"title": ".inferred-title", "content": "#content"}
    expected = {"title": ".inferred-title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_priority():
    """Test that existing non-empty values take priority over inferred ones."""
    existing = {"title": ".existing-title"}
    inferred = {"title": ".inferred-title", "content": "#content"}
    expected = {"title": ".existing-title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_empty_existing_values():
    """Test that empty existing strings are overridden by inferred values."""
    existing = {"title": "", "content": ""}
    inferred = {"title": ".inferred-title", "content": "#content"}
    expected = {"title": ".inferred-title", "content": "#content"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_new_keys_in_inferred():
    """Test that inferred keys not present in existing are added."""
    existing = {"title": ".title"}
    inferred = {"content": "#content", "next_chapter": ".next"}
    expected = {"title": ".title", "content": "#content", "next_chapter": ".next"}
    assert merge_selectors(existing, inferred) == expected


def test_merge_selectors_both_empty():
    """Test merging two empty dictionaries."""
    assert merge_selectors({}, {}) == {}


def test_merge_selectors_no_inferred():
    """Test merging with an empty inferred dictionary."""
    existing = {"title": ".title"}
    assert merge_selectors(existing, {}) == existing
