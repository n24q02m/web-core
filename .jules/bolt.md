## 2025-03-02 - Optimize sitekey extraction text.lower() call
**Learning:** Performing `text.lower()` on large strings (such as a full script tag's content) forces a new string allocation, which degrades performance significantly inside a loop.
**Action:** Replace `text.lower()` with exact substring checks (e.g., `"sitekey" not in text and "siteKey" not in text:`) to bypass script tags quickly without triggering costly string allocations.
## 2025-05-05 - Optimize parallel async downloads with Semaphore
**Learning:** Sequential await calls in loops (e.g. `await download()`) cause O(N) latency.
**Action:** Use `asyncio.gather` with an `asyncio.Semaphore` to parallelize downloads while avoiding rate limits. Ensure the `try...except` block is inside the helper async function so a single failure doesn't cancel the entire `gather` call.
