## 2025-05-14 - Redundant URL parsing optimization
**Learning:** Extracting multiple components from a URL (e.g., normalized URL and domain) in a single pass using a combined utility function significantly reduces redundant parsing costs in heavy processing loops like search result deduplication and filtering.
**Action:** Use `get_url_info` when both normalized URL and domain are needed. Avoid repeated `urlparse` calls on the same string within the same scope.
