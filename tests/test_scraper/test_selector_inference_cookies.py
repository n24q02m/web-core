from __future__ import annotations

import importlib
import json

from web_core.scraper import selector_inference


def test_load_domain_cookies_not_a_dict(monkeypatch):
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(["not", "a", "dict"]))
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}


def test_load_domain_cookies_skips_non_dict_values(monkeypatch):
    custom_cookies = {"valid.com": {"a": "b"}, "invalid.com": "not-a-dict"}
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", json.dumps(custom_cookies))
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {"valid.com": {"a": "b"}}


def test_load_domain_cookies_unexpected_error(monkeypatch):
    # Mock json.loads to raise a generic Exception
    monkeypatch.setattr("json.loads", lambda x: exec("raise Exception('boom')"))
    monkeypatch.setenv("WEB_CORE_DOMAIN_COOKIES", "{}")
    importlib.reload(selector_inference)
    assert selector_inference.DOMAIN_COOKIES == {}
