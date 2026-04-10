import json

from web_core.scraper.selector_inference import get_domain_selectors


def test_get_domain_selectors_syosetu_cookies_via_env(monkeypatch):
    # Set environment variable
    cookies_json = json.dumps({"novel18.syosetu.com": {"over18": "yes"}})
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", cookies_json)

    url = "https://novel18.syosetu.com/n1234abc/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert "cookies" in selectors
    assert selectors["cookies"].get("over18") == "yes"


def test_get_domain_selectors_no_env_no_cookies():
    # Ensure no environment variable is set (should be the case by default in tests)
    url = "https://novel18.syosetu.com/n1234abc/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert "cookies" not in selectors


def test_get_domain_selectors_invalid_json_logs_warning(monkeypatch, caplog):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "{invalid json}")
    url = "https://novel18.syosetu.com/n1234abc/"
    selectors = get_domain_selectors(url)
    assert selectors is not None
    assert "cookies" not in selectors
    assert "Failed to parse WEB_CORE_DOMAIN_COOKIES" in caplog.text


def test_get_domain_selectors_multiple_domains_via_env(monkeypatch):
    cookies_json = json.dumps({"novel18.syosetu.com": {"over18": "yes"}, "example.com": {"foo": "bar"}})
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", cookies_json)

    # Test syosetu
    selectors = get_domain_selectors("https://novel18.syosetu.com/n1234abc/")
    assert selectors["cookies"]["over18"] == "yes"

    # Example.com is not in DOMAIN_CONFIGS, so get_domain_selectors should return None
    # unless we add it or test a domain that IS in DOMAIN_CONFIGS.
    # Let's check kakuyomu.jp which IS in DOMAIN_CONFIGS.

    cookies_json = json.dumps({"kakuyomu.jp": {"session": "abc"}})
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", cookies_json)
    selectors = get_domain_selectors("https://kakuyomu.jp/works/123")
    assert selectors["cookies"]["session"] == "abc"
