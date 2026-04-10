from __future__ import annotations

from web_core.scraper.selector_inference import get_domain_selectors


def test_get_domain_selectors_exact_match():
    selectors = get_domain_selectors("https://kakuyomu.jp/works/123")
    assert selectors is not None
    assert selectors["content"] == ".widget-episodeBody"
    assert selectors["title"] == ".widget-episodeTitle"


def test_get_domain_selectors_wildcard_match():
    # Should match newtoki*.com
    selectors = get_domain_selectors("https://newtoki123.com/webtoon/123")
    assert selectors is not None
    assert selectors["title"] == ".toon-title"

    selectors = get_domain_selectors("https://newtoki.com/webtoon/123")
    assert selectors is not None
    assert selectors["title"] == ".toon-title"


def test_get_domain_selectors_no_match():
    selectors = get_domain_selectors("https://unknown.com")
    assert selectors is None


def test_get_domain_selectors_wildcard_vulnerability():
    # This currently matches but SHOULD NOT
    # because the regex is missing the end anchor '$'
    selectors = get_domain_selectors("https://newtoki123.com.evil.com/phish")

    # In the vulnerable state, this will be NOT None
    # After the fix, this should be None
    assert selectors is None


def test_get_domain_selectors_case_insensitivity():
    selectors = get_domain_selectors("https://KAKUYOMU.jp/works/123")
    assert selectors is not None
    assert selectors["content"] == ".widget-episodeBody"
