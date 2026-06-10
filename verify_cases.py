import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath("src"))

from web_core.search.client import _build_filtered_query

def test(name, result):
    print(f"{name}: {repr(result)}")

try:
    test("None query", _build_filtered_query(None))
except Exception as e:
    print(f"None query error: {type(e).__name__}: {e}")

test("Empty query + include", _build_filtered_query("", include_domains=["a.com"]))
test("Space query + include", _build_filtered_query(" ", include_domains=["a.com"]))
test("Empty query + exclude", _build_filtered_query("", exclude_domains=["b.com"]))
test("Mixed case domains", _build_filtered_query("q", include_domains=["example.com", "EXAMPLE.COM"]))
test("Trailing dot domain", _build_filtered_query("q", include_domains=["example.com."])) # regex says \. at the end is NOT allowed?
# _DOMAIN_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*\.[a-zA-Z]{2,}\Z")
# \.[a-zA-Z]{2,} expects at least 2 chars after the dot. So trailing dot fails.

test("Very long domain", _build_filtered_query("q", include_domains=["a"*256 + ".com"]))

try:
    test("Non-iterable include", _build_filtered_query("q", include_domains=123))
except Exception as e:
    print(f"Non-iterable include error: {type(e).__name__}: {e}")
