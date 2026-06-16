1. **Security Vulnerability**:
   In `src/web_core/http/client.py`, `is_safe_url` implements DNS pinning to prevent DNS rebinding attacks. It checks `_is_dns_cached(hostname)` and returns `True` immediately if cached.
   However, `is_safe_url` can be called with `allow_private=True` (e.g., for local services like SearXNG) or `allow_private=False` (for external urls).
   If an attacker causes the application to fetch `http://internal.com` with `allow_private=True` (assuming they can control the URL for a local service call or similar), the DNS result (resolving to a private IP) gets cached.
   If the attacker then supplies `http://internal.com` to an external fetch that calls `is_safe_url` with `allow_private=False`, the fast path `_is_dns_cached(hostname)` will return `True` without checking if the cached IPs are actually public, bypassing the SSRF protection.

2. **Fix**:
   In `is_safe_url`, if `_is_dns_cached(hostname)` returns True, we still need to validate that the cached IPs are safe if `not allow_private`.
   We can retrieve the cached results and run the `_check_ip_safe` on them.
   Wait, `_is_dns_cached` only returns `bool`. We can modify `_get_cached_dns(hostname)` to return the results if valid, or we can just fetch it from `_dns_cache`.

   Let's check the implementation:
   ```python
    # Fast path: already resolved, validated, and pinned
    with _dns_cache_lock:
        entry = _dns_cache.get(hostname)
        if entry is not None:
            results, cached_at = entry
            if (time.monotonic() - cached_at) < _DNS_CACHE_TTL:
                if not allow_private:
                    for res in results:
                        ip_str = str(res[4][0])
                        if not _check_ip_safe(ip_str, hostname):
                            return False
                return True
    ```
   This will correctly re-validate the cached IPs against the `allow_private` flag.
