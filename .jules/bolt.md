## 2025-03-02 - Optimize sitekey extraction text.lower() call
**Learning:** Performing `text.lower()` on large strings (such as a full script tag's content) forces a new string allocation, which degrades performance significantly inside a loop.
**Action:** Replace `text.lower()` with exact substring checks (e.g., `"sitekey" not in text and "siteKey" not in text:`) to bypass script tags quickly without triggering costly string allocations.

## 2026-05-02 - Optimization rejection: avoid brittle string checks for case insensitivity
**Learning:** Replacing `text.lower()` with explicit exact-case substring checks (`'keyword' not in text`) as a fast-path optimization introduces functional regressions when facing unpredictable casing (e.g., Cloudflare challenges using 'CloudFlare' instead of 'Cloudflare'). Furthermore, enumerating numerous conditions severely degrades code readability.
**Action:** When optimizing case-insensitive text searching, prioritize deterministic operations or pre-compiled case-insensitive regular expressions if the text is small. Avoid large enumerations of exact-case checks for micro-optimizations that compromise correctness or readability.
