with open("src/web_core/http/client.py", "r") as f:
    content = f.read()

content = content.replace(
    "from typing import Any, Iterable",
    "from collections.abc import Iterable\nfrom typing import Any"
)

old_if = """    elif allow_private and not isinstance(allow_private, bool) and not isinstance(allow_private, str):
        if hostname.lower() in {h.lower() for h in allow_private}:
            is_private_allowed = True"""

new_if = """    elif allow_private and not isinstance(allow_private, bool) and not isinstance(allow_private, str) and hostname.lower() in {h.lower() for h in allow_private}:
        is_private_allowed = True"""

content = content.replace(old_if, new_if)

with open("src/web_core/http/client.py", "w") as f:
    f.write(content)

with open("tests/test_http/test_ssrf_whitelist.py", "r") as f:
    content = f.read()

content = content.replace("from typing import Iterable\n", "")
content = content.replace("import pytest\n", "")

with open("tests/test_http/test_ssrf_whitelist.py", "w") as f:
    f.write(content)
