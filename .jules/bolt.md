## 2024-07-22 - Fast-path URL normalizer with f-strings
**Learning:** In highly frequent core utility functions like `normalize_url` in `src/web_core/http/url.py`, relying on robust standard library functions like `urlunsplit` introduces measurable overhead from tuple allocation and complex conditionals. `urlsplit` already guarantees that the path is either empty or starts with a `/`.
**Action:** When both `scheme` and `netloc` are known, and `path` is correctly formatted, string interpolation (`f"{scheme}://{netloc}{path}?{query}"`) is completely safe and ~2x faster than `urlunsplit`. Always look for safe string formatting opportunities to bypass standard library builder methods in hot paths.

## 2024-07-22 - Regex Combination Optimization
**Learning:** Checking a large string (like HTML pages) against multiple `re.compile()` patterns sequentially is extremely costly because the regex engine runs multiple full passes over the document, especially for non-matching cases.
**Action:** Combine independent regex patterns into a single compiled pattern using alternations (`|`) and check `match.groups()` instead. This performs a single scan, significantly reducing CPU overhead without any loss in functionality.
