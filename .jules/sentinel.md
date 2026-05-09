## 2026-04-27 - [SSRF Bypass via Missing Carrier-Grade NAT (CGNAT) Blocking]
**Vulnerability:** The `_check_ip_safe` function relied on `ip.is_private` and other individual checks which missed non-publicly routable IPv4 addresses, specifically Carrier-Grade NAT (100.64.0.0/10). This could allow SSRF bypasses via these addresses.
**Learning:** Python's `ipaddress` module does not classify CGNAT addresses as `is_private`. The most robust way to ensure SSRF protection is to strictly require `ip.is_global` while also blocking `ip.is_multicast` (since multicast addresses can report as global).
**Prevention:** Always use `not ip.is_global or ip.is_multicast` for blocking SSRF and non-publicly routable IPs rather than manually chaining `is_private`, `is_loopback`, `is_link_local`, and manual subnets.

## 2026-04-28 - [Secret Leakage via Docker Command-Line Arguments]
**Vulnerability:** The application was passing a dynamically generated secret (for `SEARXNG_SECRET`) into a Docker container via the `-e` command-line argument in `subprocess.Popen` or `subprocess.run` calls.
**Learning:** Passing secrets through command-line arguments (e.g. `docker run -e SECRET=...`) makes them visible to all users on the host system via process inspection tools like `ps` or `top`. Since the secret was already safely injected via a template into a securely permissioned configuration file (`settings.yml`) that was mounted into the container, the `-e` argument was redundant and created a clear security risk.
**Prevention:** Never pass secrets via command-line arguments to Docker containers. Pass them using mounted configuration files or an `--env-file` instead.

## 2026-04-29 - [SSRF Bypass via Alternative HTTP Clients (curl_cffi)]
**Vulnerability:** The `TLSSpoofStrategy` utilized `curl_cffi` to perform network requests. While standard HTTP requests via `httpx` were protected by socket-level DNS pinning and `httpx` event hooks, `curl_cffi` bypasses Python's `socket.getaddrinfo` entirely because it delegates DNS resolution internally to `libcurl`. This exposed the strategy to SSRF vulnerabilities, allowing requests to arbitrary, non-validated IPs.
**Learning:** Security controls implemented by monkey-patching core Python libraries (like `socket.getaddrinfo`) or via library-specific hooks (like `httpx.AsyncClient` event hooks) will not protect components that wrap C-extensions or external binaries carrying their own networking stack.
**Prevention:** Always manually validate URLs using `is_safe_url` before executing requests via non-standard or external networking libraries like `curl_cffi`. Do not assume environment-level monkey patches cover all forms of outbound IO.
