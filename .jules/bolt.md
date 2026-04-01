## 2023-10-27 - URL Normalization Bottleneck
**Learning:** `urllib.parse.urlparse` and query string operations are surprisingly slow in Python. Parsing queries using `parse_qs` when unnecessary causes significant overhead because standard URL normalization runs on *every* deduplicated link.
**Action:** Use fast path substring checks for query strings before performing full parses whenever possible to short-circuit expensive URL operations.
