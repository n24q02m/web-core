## 2025-05-15 - [Testing Process Termination]
**Vulnerability:** Not a vulnerability, but a testing gap in process management.
**Learning:** Testing graceful process termination with `os.kill(pid, 0)` requires mocking multiple calls to return success and then `ProcessLookupError`.
**Prevention:** Always test the "graceful wait" loop when implementing signal-based process termination to ensure it actually waits and correctly handles the process disappearing.
