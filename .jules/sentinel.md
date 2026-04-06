
## 2025-02-23 - [SSRF Bypass via Unspecified IP Addresses (0.0.0.0 / ::)]
**Vulnerability:** The SSRF filter checking if an IP is safe did not check for `ip.is_unspecified`. This allowed connection attempts to `0.0.0.0` or `::`, which could act as a local loopback on some UNIX-like operating systems.
**Learning:** Checking for private/loopback/link-local/multicast is insufficient. Unspecified IP addresses can bypass these checks and be routed locally by the OS.
**Prevention:** Use `ip.is_unspecified` as an explicit check in SSRF filters to block `0.0.0.0` and `::`.
