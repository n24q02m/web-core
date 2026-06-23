import asyncio
from unittest.mock import MagicMock, patch

async def _kill_stale_port_process(port):
    import sys
    import asyncio
    from web_core.search.runner import logger
    if sys.platform == "win32":
        try:
            await asyncio.to_thread(lambda: None)
        except Exception as e:
            logger.debug("Error finding processes on port %d using netstat: %s", port, e)

async def test():
    with patch("sys.platform", "win32"):
        with patch("asyncio.to_thread", side_effect=Exception("netstat failed")):
            with patch("web_core.search.runner.logger") as mock_logger:
                await _kill_stale_port_process(8888)
                print(f"Debug calls: {mock_logger.debug.call_args_list}")

asyncio.run(test())
