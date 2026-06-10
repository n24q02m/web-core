import sys
import os

filepath = "src/web_core/search/client.py"
with open(filepath, "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "def _get_safe_domains" in line:
        skip = True
        new_lines.append("def _get_safe_domains(domains: Any, limit: int) -> list[str]:\n")
        new_lines.append("    \"\"\"Filter, normalize, and limit a list of domains.\n")
        new_lines.append("\n")
        new_lines.append("    - Silently skips invalid domains (per ``is_valid_domain``).\n")
        new_lines.append("    - Normalizes to lowercase.\n")
        new_lines.append("    - Deduplicates.\n")
        new_lines.append("    - Limits to ``limit`` items.\n")
        new_lines.append("    - Handles non-iterable input gracefully.\n")
        new_lines.append("    \"\"\"\n")
        new_lines.append("    if not isinstance(domains, Iterable) or isinstance(domains, (str, bytes)):\n")
        new_lines.append("        return []\n")
        new_lines.append("\n")
        new_lines.append("    seen = set()\n")
        new_lines.append("    safe = []\n")
        new_lines.append("    for d in domains:\n")
        new_lines.append("        if isinstance(d, str):\n")
        new_lines.append("            d_norm = d.strip().lower()\n")
        new_lines.append("            if d_norm and d_norm not in seen and is_valid_domain(d_norm):\n")
        new_lines.append("                seen.add(d_norm)\n")
        new_lines.append("                safe.append(d_norm)\n")
        new_lines.append("                if len(safe) >= limit:\n")
        new_lines.append("                    break\n")
        new_lines.append("    return safe\n")
        new_lines.append("\n\n")

        new_lines.append("def _build_filtered_query(\n")
        new_lines.append("    query: str,\n")
        new_lines.append("    include_domains: list[str] | None = None,\n")
        new_lines.append("    exclude_domains: list[str] | None = None,\n")
        new_lines.append(") -> str:\n")
        new_lines.append("    \"\"\"Build a SearXNG query with site: include/exclude operators.\n")
        new_lines.append("\n")
        new_lines.append("    - ``include_domains``: up to 5 unique domains joined with ``OR site:``\n")
        new_lines.append("    - ``exclude_domains``: up to 10 unique domains prepended with ``-site:``\n")
        new_lines.append("\n")
        new_lines.append("    Invalid domains (per ``is_valid_domain``) are silently skipped to\n")
        new_lines.append("    prevent search operator injection.\n")
        new_lines.append("    \"\"\"\n")
        new_lines.append("    # Robustness: ensure query is a string (handles None gracefully)\n")
        new_lines.append("    safe_query = str(query) if query is not None else \"\"\n")
        new_lines.append("    parts = [safe_query]\n")
        new_lines.append("\n")
        new_lines.append("    safe_include = _get_safe_domains(include_domains, 5)\n")
        new_lines.append("    if safe_include:\n")
        new_lines.append("        site_filter = \" OR \".join(f\"site:{d}\" for d in safe_include)\n")
        new_lines.append("        parts = [f\"({site_filter}) {safe_query}\"]\n")
        new_lines.append("\n")
        new_lines.append("    safe_exclude = _get_safe_domains(exclude_domains, 10)\n")
        new_lines.append("    for d in safe_exclude:\n")
        new_lines.append("        parts.append(f\"-site:{d}\")\n")
        new_lines.append("\n")
        new_lines.append("    return \" \".join(parts)\n")

    if "return \" \".join(parts)" in line and skip:
        skip = False
        continue

    if not skip:
        new_lines.append(line)

with open(filepath, "w") as f:
    f.writelines(new_lines)
