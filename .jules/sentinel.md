## 2026-04-08 - [SSRF Bypass Fix]
**Vulnerability:** `_list_folder_via_html` in `google_drive.py` instantiated `httpx.AsyncClient` directly instead of using `safe_httpx_client`.
**Learning:** Incomplete adoption of central security wrapper components.
**Prevention:** Must enforce usage of `safe_httpx_client` for all external network requests to prevent Server-Side Request Forgery vulnerabilities.
