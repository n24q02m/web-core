# Sentinel Journal

## 2024-04-01 - Secure Configuration Files with Secrets
**Vulnerability:** A dynamically generated SearXNG settings file (`searxng_settings_{pid}.yml`) containing a `secret_key` (hex string) was being written using `Path.write_text()`. This used the default system umask, which on typical systems generates files readable by other users (e.g. `0o644` or `0o664`).
**Learning:** `Path.write_text()` doesn't allow setting explicit file permissions upon creation. Writing secrets to temporary or configuration files requires more explicit file descriptor handling to ensure proper access control and prevent secrets leakage on multi-user systems.
**Prevention:** Always construct sensitive files using `os.open` with a strict mode like `0o600` (`os.O_WRONLY | os.O_CREAT | os.O_TRUNC`) and secure the parent directory using `chmod(0o700)`. Use `os.fdopen` to wrap the resulting file descriptor into a standard Python file object to safely write contents.