import asyncio
from unittest.mock import MagicMock

async def main():
    mock = MagicMock()
    mock.return_value = None
    try:
        await mock()
        print("Success??")
    except TypeError as e:
        print(f"Caught error: {e}")

asyncio.run(main())
