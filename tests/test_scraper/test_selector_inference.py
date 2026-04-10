from __future__ import annotations

from web_core.scraper.selector_inference import DOMAIN_CONFIGS, get_domain_selectors, merge_selectors


def test_get_domain_selectors_exact_match():
    url = "https://ncode.syosetu.com/n1234ab/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == "#novel_honbun"
    assert "cookies" not in selectors


def test_get_domain_selectors_wildcard_match():
    url = "https://newtoki95.com/webtoon/1234"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert "content" in selectors
    assert selectors["title"] == ".toon-title"


def test_get_domain_selectors_case_insensitive():
    url = "HTTPS://KAKUYOMU.JP/works/123"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["content"] == ".widget-episodeBody"


def test_get_domain_selectors_no_match():
    url = "https://example.com"
    selectors = get_domain_selectors(url)
    assert selectors is None


def test_get_domain_selectors_with_cookies():
    url = "https://novel18.syosetu.com/n1234ab/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert selectors["cookies"] == {"over18": "yes"}
    assert selectors["content"] == "#novel_honbun"


def test_get_domain_selectors_returns_copy():
    url = "https://ncode.syosetu.com/n1234ab/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    selectors["content"] = "modified"
    assert DOMAIN_CONFIGS["ncode.syosetu.com"]["content"] == "#novel_honbun"


def test_merge_selectors():
    existing = {"content": "#main", "title": ""}
    inferred = {"content": "#content", "title": ".title", "next_chapter": "a.next"}

    merged = merge_selectors(existing, inferred)

    assert merged["content"] == "#main"  # Existing takes priority
    assert merged["title"] == ".title"  # Inferred takes priority because existing is empty
    assert merged["next_chapter"] == "a.next"


def test_merge_selectors_all_empty_existing():
    existing = {"content": "", "title": ""}
    inferred = {"content": "#content", "title": ".title"}

    merged = merge_selectors(existing, inferred)
    assert merged == inferred


def test_merge_selectors_no_inferred_overlap():
    existing = {"custom": "selector"}
    inferred = {"content": "#content"}

    merged = merge_selectors(existing, inferred)
    assert merged == {"custom": "selector", "content": "#content"}
