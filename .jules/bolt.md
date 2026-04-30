
## 2025-05-01 - [Google Drive Adapter Concurrent Download]
**Learning:** Sequential network I/O calls (like `download_text_file` inside a `for` loop in `fetch_folder_chapters`) create a linear architectural bottleneck when fetching multiple external assets, negating the benefits of Python's async event loop.
**Action:** When a function fetches independent items from a remote API, use the `asyncio.gather` pattern to retrieve them concurrently. This change reduces expected latency from O(n) to near-constant time.
