import sys
import os

file_path = "src/web_core/http/client.py"
with open(file_path, "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "def is_safe_url" in line:
        # Add helpers before is_safe_url
        new_lines.append("def _is_dns_pinned(hostname: str) -> bool:\n")
        new_lines.append("    \"\"\"Return True if the hostname is already resolved and pinned.\"\"\"\n")
        new_lines.append("    with _dns_cache_lock:\n")
        new_lines.append("        entry = _dns_cache.get(hostname)\n")
        new_lines.append("        if entry is None:\n")
        new_lines.append("            return False\n")
        new_lines.append("\n")
        new_lines.append("        _, cached_at = entry\n")
        new_lines.append("        return time.monotonic() - cached_at < _DNS_CACHE_TTL\n")
        new_lines.append("\n")
        new_lines.append("\n")
        new_lines.append("def _are_resolved_ips_safe(results: list, hostname: str) -> bool:\n")
        new_lines.append("    \"\"\"Return True if all resolved IPs are publicly routable.\"\"\"\n")
        new_lines.append("    for res in results:\n")
        new_lines.append("        ip_str = str(res[4][0])\n")
        new_lines.append("        if not _check_ip_safe(ip_str, hostname):\n")
        new_lines.append("            return False\n")
        new_lines.append("    return True\n")
        new_lines.append("\n")
        new_lines.append("\n")

        new_lines.append(line)
        skip = True
        continue

    if skip:
        if line.startswith("# ---") or line.startswith("def _ssrf_event_hook"):
            skip = False
            new_lines.append("\n")
            new_lines.append(line)
        continue

    new_lines.append(line)

# Now define the new is_safe_url content
is_safe_url_body = """    \"\"\"Validate that *url* is safe to fetch (no SSRF).

    Checks:
    1. Scheme must be ``http`` or ``https``
    2. Hostname must exist
    3. Hostname must not be a known localhost alias (unless ``allow_private=True``)
    4. All resolved IPs must be publicly routable (unless ``allow_private=True``)
    5. Results are cached to pin DNS and prevent rebinding
    \"\"\"
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    if not allow_private and hostname.lower() in _BLOCKED_HOSTNAMES:
        return False

    # Fast path: already resolved, validated, and pinned
    if _is_dns_pinned(hostname):
        return True

    try:
        results = _original_getaddrinfo(hostname, None)
        if not allow_private and not _are_resolved_ips_safe(results, hostname):
            return False

        # Pin the DNS result
        with _dns_cache_lock:
            _dns_cache[hostname] = (results, time.monotonic())
        return True
    except (socket.gaierror, Exception):
        return False
"""

# Find where is_safe_url starts and replace its body
final_lines = []
in_body = False
for line in new_lines:
    if "def is_safe_url" in line:
        final_lines.append(line)
        final_lines.append(is_safe_url_body)
        in_body = True
        continue
    if in_body:
        if line.strip() == "" or line.startswith("    "):
            continue
        else:
            in_body = False
    final_lines.append(line)

with open(file_path, "w") as f:
    f.writelines(final_lines)
