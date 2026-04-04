## 2024-04-05 - Enforce strict permissions for files with secrets
**Vulnerability:** SearXNG settings file (containing the secret_key) was written using `Path.write_text()`, which defaults to world-readable permissions (e.g., `0o644`) depending on the umask. This exposes the secret key to other users on the system.
**Learning:** For files that contain secrets or sensitive configuration, `Path.write_text()` should be avoided because it doesn't offer a direct way to enforce secure permissions at creation time.
**Prevention:** Always use `os.open` with flags `os.O_WRONLY | os.O_CREAT | os.O_TRUNC` and explicit `mode=0o600` when creating sensitive files, and enforce directory permissions using `mkdir(mode=0o700)` followed by `chmod(0o700)`.
