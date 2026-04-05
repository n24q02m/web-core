## 2025-05-15 - [SECURITY] Insecure temporary file creation
**Vulnerability:** Use of predictable filenames with `os.getpid()` in a shared directory without restricted permissions.
**Learning:** Standard file operations like `Path.write_text()` respect system umask, which might allow broader read access than intended for sensitive files (like those containing secrets).
**Prevention:** Use `tempfile.mkstemp()` to create files with randomized names and restricted (0o600) permissions by default. Use `os.fdopen()` with the returned file descriptor for writing.
