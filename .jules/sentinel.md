## $(date +%Y-%m-%d) - Secure Temporary File Creation for Settings
**Vulnerability:** Predictable temporary file path creation with insecure default permissions via `Path.write_text()`.
**Learning:** Using predictable paths (e.g., `f"searxng_settings_{os.getpid()}.yml"`) in world-accessible or user-accessible configuration directories (even with directory chmod) creates vectors for symlink attacks and configuration tampering. `Path.write_text()` does not enforce strict file permissions during creation, which can leak locally generated secrets if the umask allows world-read.
**Prevention:** Always use `tempfile.mkstemp()` (with appropriate `prefix`, `suffix`, and `dir`) to generate cryptographically random filenames and automatically enforce strict `0o600` permissions. Handle the resulting file descriptor securely using `os.fdopen()` and `try...finally` (or `contextlib.suppress`) cleanup logic to avoid resource leaks.

## 2026-04-13 - [Regex Domain Matching]
**Learning:** Using manual string replacement (e.g., .replace('.', '\.')) for regex generation is error-prone and can lead to substring bypasses if not anchored.
**Action:** Always use re.escape() for escaping literal segments and ensure start (^) and end ($) anchors are used for strict domain/URL matching. Use [^.]* instead of .* for wildcards in domains to prevent segment-crossing matches.
