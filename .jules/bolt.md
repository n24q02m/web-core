## 2025-05-14 - [Async DNS resolution in httpx event hook]
**Learning:** Synchronous operations like `socket.getaddrinfo` inside an async httpx event hook block the entire event loop, causing performance degradation in highly concurrent environments.
**Action:** Always wrap synchronous blocking calls in `asyncio.to_thread` when used within an async context if an async alternative is not readily available or preferred for simplicity/compatibility.
