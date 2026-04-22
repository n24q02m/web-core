
## 2024-05-18 - SSRF protection gap using `ipaddress`
**Vulnerability:** The `ipaddress` module explicitly considers CGNAT (`100.64.0.0/10`) and unspecified (`0.0.0.0`) addresses as NOT private (i.e. `ip.is_private` is `False`). Because the custom SSRF protection block logic relied on checking `is_private`, `is_loopback`, `is_link_local`, `is_reserved`, and `is_multicast`, it failed to block those IPs. This could lead to SSRF vulnerabilities inside AWS and other cloud providers leveraging Carrier Grade NAT or `0.0.0.0` for local routing.
**Learning:** `ip.is_private` is surprisingly strict. `ip.is_global` returns `False` for CGNAT, unspecified, private, loopback, link_local, and reserved IP ranges.
**Prevention:** Instead of explicitly listing every non-public IP type via `is_private`, `is_loopback` etc., rely on `not ip.is_global or ip.is_multicast` to correctly ensure an IP is both globally routable and strictly non-multicast.
