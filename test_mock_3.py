import asyncio
from unittest.mock import AsyncMock

async def main():
    mock = AsyncMock()
    await mock()
    print("Success")

asyncio.run(main())
