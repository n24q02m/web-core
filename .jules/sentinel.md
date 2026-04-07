## 2025-05-22 - [PERF] Synchronous I/O in async context (time.sleep)
**Vulnerability:** Blocking the event loop with synchronous I/O (time.sleep, blocking proc.wait) in an asynchronous context.
**Learning:** Functions that perform I/O or waiting should provide both sync and async versions if they are called from both contexts (e.g., normal async flow vs. atexit handlers).
**Prevention:** Use `asyncio.sleep` in async functions and `asyncio.to_thread` for blocking calls like `subprocess.Popen.wait`. Provide `_sync` suffixed versions for synchronous entry points.
