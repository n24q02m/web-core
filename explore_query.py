from web_core.search.client import _build_filtered_query

print(f"None query: {repr(_build_filtered_query(None)) if False else 'Crashes'}")
try:
    _build_filtered_query(None)
except Exception as e:
    print(f"None query error: {type(e).__name__}: {e}")

print(f"Mixed case domains: {_build_filtered_query('test', include_domains=['example.com', 'EXAMPLE.COM'])}")

print(f"Non-list iterable: {_build_filtered_query('test', include_domains={'a.com', 'b.com'})}")

def gen():
    yield "gen.com"
print(f"Generator: {_build_filtered_query('test', include_domains=gen())}")

print(f"Query with newline: {repr(_build_filtered_query('line1\nline2', include_domains=['a.com']))}")

print(f"Very long domain: {_build_filtered_query('test', include_domains=['a'*100 + '.com'])}")
