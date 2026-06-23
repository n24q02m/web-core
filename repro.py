import asyncio
from unittest.mock import MagicMock, patch

async def _kill_stale_port_process(port):
    import sys
    import asyncio
    import logging
    logger = logging.getLogger("test")
    if sys.platform == "win32":
        try:
            await asyncio.to_thread(lambda: None)
        except Exception as e:
            logger.debug("Error finding processes on port %d using netstat: %s", port, e)

async def test():
    mock_logger = MagicMock()
    with patch("sys.platform", "win32"):
        with patch("asyncio.to_thread", side_effect=Exception("netstat failed")):
            with patch("logging.getLogger", return_value=mock_logger):
                await _kill_stale_port_process(8888)

    print(f"Debug called: {mock_logger.debug.called}")
    for i, call in enumerate(mock_logger.debug.call_args_list):
        print(f"Call {i} args: {call.args}")

asyncio.run(test())
