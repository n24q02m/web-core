import sys
import os

filepath = "tests/test_search/test_build_filtered_query.py"
with open(filepath, "r") as f:
    content = f.read()

# Fix the test expectations as we now strip domains
content = content.replace(
    'def test_build_filtered_query_domain_whitespace():\n    """Domains with whitespace should be rejected (or handled) by is_valid_domain."""\n    result = _build_filtered_query("python", include_domains=["  ", "example.com "])\n    assert result == "python"',
    'def test_build_filtered_query_domain_whitespace():\n    """Domains with whitespace should be handled by stripping and validation."""\n    result = _build_filtered_query("python", include_domains=["  ", "example.com "])\n    assert result == "(site:example.com) python"'
)

with open(filepath, "w") as f:
    f.write(content)
