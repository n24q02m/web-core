path = 'tests/test_search/test_runner.py'
with open(path, 'r') as f:
    content = f.read()

# I messed up big time with string replaces. Let's just rewrite the whole TestSigtermThenKillSync and TestSigtermThenKill classes correctly.

import re

# Find and replace TestSigtermThenKillSync
new_sync_class = """class TestSigtermThenKillSync:
    def test_immediate_dead(self):
        with patch("os.kill") as mock_kill:
            mock_kill.side_effect = ProcessLookupError()
            assert _sigterm_then_kill_sync(123) is True
            mock_kill.assert_called_once_with(123, signal.SIGTERM)

    def test_graceful_exit(self):
        with (
            patch("os.kill") as mock_kill,
            patch("web_core.search.runner._is_process_dead") as mock_dead,
            patch("time.sleep"),
        ):
            mock_dead.side_effect = [False, False, True]
            assert _sigterm_then_kill_sync(123) is True
            assert mock_kill.call_count == 1
            mock_kill.assert_called_with(123, signal.SIGTERM)
            assert mock_dead.call_count == 3

    def test_force_kill(self):
        with (
            patch("sys.platform", "linux"),
            patch("os.kill") as mock_kill,
            patch("web_core.search.runner._is_process_dead") as mock_dead,
            patch("time.sleep"),
        ):
            mock_dead.return_value = False
            assert _sigterm_then_kill_sync(123) is True
            assert mock_kill.call_count == 2
            mock_kill.assert_any_call(123, signal.SIGTERM)
            mock_kill.assert_any_call(123, getattr(signal, "SIGKILL", signal.SIGTERM))
            assert mock_dead.call_count == 30"""

content = re.sub(r'class TestSigtermThenKillSync:.*?assert mock_dead.call_count == 30', new_sync_class, content, flags=re.DOTALL)

# Find and replace TestSigtermThenKill
new_async_class = """class TestSigtermThenKill:
    @pytest.mark.asyncio
    async def test_graceful_exit_async(self):
        with (
            patch("sys.platform", "linux"),
            patch("os.kill") as mock_kill,
            patch("web_core.search.runner._is_process_dead") as mock_dead,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_dead.side_effect = [False, True]
            assert await _sigterm_then_kill(123) is True
            mock_kill.assert_called_once_with(123, signal.SIGTERM)"""

content = re.sub(r'class TestSigtermThenKill:.*?mock_kill.assert_called_once_with\(123, signal.SIGTERM\)', new_async_class, content, flags=re.DOTALL)

with open(path, 'w') as f:
    f.write(content)
