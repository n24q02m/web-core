## 2025-03-02 - Optimize sitekey extraction text.lower() call
**Learning:** Performing `text.lower()` on large strings (such as a full script tag's content) forces a new string allocation, which degrades performance significantly inside a loop.
**Action:** Replace `text.lower()` with exact substring checks (e.g., `"sitekey" not in text and "siteKey" not in text:`) to bypass script tags quickly without triggering costly string allocations.
## 2025-05-05 - Optimize parallel async downloads with Semaphore
**Learning:** Sequential await calls in loops (e.g. `await download()`) cause O(N) latency.
**Action:** Use `asyncio.gather` with an `asyncio.Semaphore` to parallelize downloads while avoiding rate limits. Ensure the `try...except` block is inside the helper async function so a single failure doesn't cancel the entire `gather` call.
## 2025-05-08 - Optimize Playwright IPC latency with page.evaluate batching
**Learning:** Calling `page.query_selector_all()` and subsequently awaiting properties like `await el.get_attribute()` or `await el.text_content()` sequentially inside a loop creates O(N) IPC (Inter-Process Communication) round-trips to the Playwright browser context, causing multi-second latency for large numbers of elements (e.g. hundreds of scripts or iframes).
**Action:** Replace sequential element property extractions with batch execution via `page.evaluate()`, mapping over elements directly inside the browser context (e.g. `await page.evaluate("() => Array.from(document.querySelectorAll('script')).map(s => s.textContent || '')")`). This executes in a single O(1) IPC round-trip.
## 2025-05-08 - Fast Path Domain Extraction
**Learning:** `urllib.parse.urlparse` is slow for simple domain extraction due to regex usage and tuple allocations. Using string partitioning (`partition`) on the URL string is roughly 3.5x faster in micro-benchmarks. This optimization is especially valuable in hot loops like iterating over search results or caching operations, but also provides a measurable speedup for simple selector inference.
**Action:** When only the domain (netloc) is needed from a URL and RFC strictness for edge cases (like non-standard schemas) is not critical, use `str.partition` instead of `urlparse`.
