## 2025-03-02 - Optimize sitekey extraction text.lower() call
**Learning:** Performing `text.lower()` on large strings (such as a full script tag's content) forces a new string allocation, which degrades performance significantly inside a loop.
**Action:** Replace `text.lower()` with exact substring checks (e.g., `"sitekey" not in text and "siteKey" not in text:`) to bypass script tags quickly without triggering costly string allocations.
## 2025-05-04 - Safely parallelizing bounded async network calls
**Learning:** When fetching multiple items over the network (e.g., downloading chapters from Google Drive), running them sequentially inside a `for` loop results in linear latency.
**Action:** Use `asyncio.gather` for bounded parallelization to reduce latency to ~O(1) relative to network round-trips. Always wrap individual operations in a safe `try...except` helper function returning `None` on failure so that a single error doesn't cancel the entire `gather` call, while still ensuring the order of returned results matches the input list.
