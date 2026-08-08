import re
_STRIP_TAGS_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1[^>]*>|<[^>]+>",
    re.IGNORECASE | re.DOTALL
)

def visible_text_opt(html: str) -> str:
    if not html:
        return ""
    stripped = _STRIP_TAGS_RE.sub(" ", html)
    return stripped

html = "<script>var x = '</style>'; console.log(x);</script>"
print(visible_text_opt(html))
