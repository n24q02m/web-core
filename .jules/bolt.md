## 2026-05-01 - Parallelize Google Drive Chapter Downloads
**Learning:** Sequential network requests in loops (`for f in files: text = await download_text_file(f.file_id)`) create significant bottlenecks due to accumulated network latency, especially for remote APIs like Google Drive. Micro-benchmarks replacing URL parsing methods yield marginal gains compared to parallelizing IO-bound network calls.
**Action:** When fetching multiple independent resources from an adapter, use `asyncio.gather(*tasks)` to parallelize the requests, reducing total latency from O(n) to near-constant time.
