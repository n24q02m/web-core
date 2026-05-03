## 2026-04-27 - [SSRF Bypass via Missing Carrier-Grade NAT (CGNAT) Blocking]
**Vulnerability:** The `_check_ip_safe` function relied on `ip.is_private` and other individual checks which missed non-publicly routable IPv4 addresses, specifically Carrier-Grade NAT (100.64.0.0/10). This could allow SSRF bypasses via these addresses.
**Learning:** Python's `ipaddress` module does not classify CGNAT addresses as `is_private`. The most robust way to ensure SSRF protection is to strictly require `ip.is_global` while also blocking `ip.is_multicast` (since multicast addresses can report as global).
**Prevention:** Always use `not ip.is_global or ip.is_multicast` for blocking SSRF and non-publicly routable IPs rather than manually chaining `is_private`, `is_loopback`, `is_link_local`, and manual subnets.

## 2024-05-27 - [Secret Leakage via Docker Command Line Arguments]
**Vulnerability:** In `src/web_core/search/runner.py`, a dynamically generated secret key was passed to the SearXNG Docker container using the `-e SEARXNG_SECRET=...` command-line argument. This exposes the secret to all users on the host system, as process arguments are visible via utilities like `ps aux` or reading `/proc/<pid>/cmdline`.
**Learning:** Command-line arguments of long-running processes (like Docker containers) are globally readable on most operating systems. Passing secrets (API keys, passwords, generated tokens) via `-e` or `--env` on the command line is an inherent vulnerability.
**Prevention:** Always provide secrets to processes and containers using secure methods, such as an environment variable file (`--env-file`) or mounted configuration files (e.g., `settings.yml`) with restrictive file permissions.
