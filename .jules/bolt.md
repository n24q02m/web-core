## 2025-03-02 - Optimize sitekey extraction text.lower() call
**Learning:** Performing `text.lower()` on large strings (such as a full script tag's content) forces a new string allocation, which degrades performance significantly inside a loop.
**Action:** Replace `text.lower()` with exact substring checks (e.g., `"sitekey" not in text and "siteKey" not in text:`) to bypass script tags quickly without triggering costly string allocations.
