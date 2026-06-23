with open("src/web_core/http/client.py", "r") as f:
    content = f.read()

old_if = """    if allow_private is True or (allow_private and not isinstance(allow_private, bool) and not isinstance(allow_private, str) and hostname.lower() in {h.lower() for h in allow_private}):
        is_private_allowed = True"""

new_if = """    if allow_private is True or (
        allow_private
        and not isinstance(allow_private, bool)
        and not isinstance(allow_private, str)
        and hostname.lower() in {h.lower() for h in allow_private}
    ):
        is_private_allowed = True"""

content = content.replace(old_if, new_if)

with open("src/web_core/http/client.py", "w") as f:
    f.write(content)
