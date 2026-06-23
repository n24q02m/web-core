from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock, call
import pytest

from web_core.search.runner import (
    _force_kill_process_sync,
    _force_kill_process,
    _sigterm_then_kill_sync,
    _sigterm_then_kill,
    _is_process_dead,
    _kill_stale_port_process,
)

# ---------------------------------------------------------------------------
# _is_process_dead
# ---------------------------------------------------------------------------

class TestIsProcessDead:
    def test_alive_process(self):
        # os.getpid() is always alive
        assert _is_process_dead(os.getpid()) is False

    def test_dead_process(self):
        # PID 999999 is likely dead
        with patch("os.kill", side_effect=ProcessLookupError):
            assert _is_process_dead(999999) is True

    def test_permission_error(self):
        with patch("os.kill", side_effect=PermissionError):
            assert _is_process_dead(1) is True

# ---------------------------------------------------------------------------
# _sigterm_then_kill_sync / _sigterm_then_kill
# ---------------------------------------------------------------------------

class TestSigtermThenKill:
    @patch("os.kill")
    @patch("web_core.search.runner._is_process_dead")
    def test_sigterm_success_sync(self, mock_dead, mock_kill):
        mock_dead.side_effect = [False, True]  # Alive then dead

        assert _sigterm_then_kill_sync(12345, "test") is True

        mock_kill.assert_any_call(12345, signal.SIGTERM)
        assert mock_dead.call_count >= 2

    @patch("os.kill")
    @patch("web_core.search.runner._is_process_dead")
    @patch("time.sleep")
    def test_sigterm_timeout_force_kill_sync(self, mock_sleep, mock_dead, mock_kill):
        mock_dead.return_value = False  # Always alive

        assert _sigterm_then_kill_sync(12345, "test") is True

        mock_kill.assert_any_call(12345, signal.SIGTERM)
        mock_kill.assert_any_call(12345, signal.SIGKILL)
        assert mock_dead.call_count == 30

    @patch("os.kill")
    @patch("web_core.search.runner._is_process_dead")
    async def test_sigterm_success_async(self, mock_dead, mock_kill):
        mock_dead.side_effect = [False, True]

        assert await _sigterm_then_kill(12345, "test") is True

        mock_kill.assert_any_call(12345, signal.SIGTERM)

    @patch("os.kill")
    @patch("web_core.search.runner._is_process_dead")
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_sigterm_timeout_force_kill_async(self, mock_sleep, mock_dead, mock_kill):
        mock_dead.return_value = False

        assert await _sigterm_then_kill(12345, "test") is True

        mock_kill.assert_any_call(12345, signal.SIGKILL)

    @patch("os.kill")
    def test_process_lookup_error(self, mock_kill):
        mock_kill.side_effect = ProcessLookupError
        assert _sigterm_then_kill_sync(12345) is True

    def test_sigterm_lookup_error_sync(self):
        with patch("os.kill", side_effect=ProcessLookupError):
            assert _sigterm_then_kill_sync(12345) is True

    def test_sigkill_lookup_error_sync(self):
        with patch("os.kill") as mock_kill:
            # First call (SIGTERM) succeeds, second (SIGKILL) fails
            mock_kill.side_effect = [None, ProcessLookupError]
            with patch("web_core.search.runner._is_process_dead", return_value=False):
                with patch("time.sleep"):
                    assert _sigterm_then_kill_sync(12345) is True

    @patch("os.kill")
    async def test_sigterm_lookup_error_async(self, mock_kill):
        mock_kill.side_effect = ProcessLookupError
        assert await _sigterm_then_kill(12345) is True

    @patch("os.kill")
    async def test_sigkill_lookup_error_async(self, mock_kill):
        mock_kill.side_effect = [None, ProcessLookupError]
        with patch("web_core.search.runner._is_process_dead", return_value=False):
            with patch("asyncio.sleep"):
                assert await _sigterm_then_kill(12345) is True

# ---------------------------------------------------------------------------
# _force_kill_process_sync
# ---------------------------------------------------------------------------

class TestForceKillProcessSync:
    def test_already_dead(self):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = 0
        _force_kill_process_sync(proc)
        proc.wait.assert_not_called()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("os.getpgid")
    @patch("os.killpg")
    def test_unix_graceful_success(self, mock_killpg, mock_getpgid):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345
        mock_getpgid.return_value = 5555

        _force_kill_process_sync(proc)

        mock_killpg.assert_any_call(5555, signal.SIGTERM)
        proc.wait.assert_called_with(timeout=3)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("os.getpgid")
    @patch("os.killpg")
    def test_unix_force_kill_after_timeout(self, mock_killpg, mock_getpgid):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345
        mock_getpgid.return_value = 5555
        proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="", timeout=3), None]

        _force_kill_process_sync(proc)

        mock_killpg.assert_any_call(5555, signal.SIGTERM)
        mock_killpg.assert_any_call(5555, signal.SIGKILL)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("os.getpgid")
    @patch("os.killpg")
    def test_unix_killpg_error_fallback(self, mock_killpg, mock_getpgid):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345
        mock_getpgid.return_value = 5555
        mock_killpg.side_effect = ProcessLookupError

        _force_kill_process_sync(proc)

        proc.terminate.assert_called_once()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("os.getpgid")
    @patch("os.killpg")
    def test_unix_killpg_sigkill_error_fallback(self, mock_killpg, mock_getpgid):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345
        mock_getpgid.return_value = 5555
        # SIGTERM succeeds, wait timeouts, SIGKILL fails
        proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="", timeout=3), None]
        mock_killpg.side_effect = [None, ProcessLookupError]

        _force_kill_process_sync(proc)

        proc.kill.assert_called_once()

    @patch("web_core.search.runner.sys")
    @patch("web_core.search.runner._sigterm_then_kill_sync")
    def test_windows_branch(self, mock_sigterm, mock_sys):
        mock_sys.platform = "win32"
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345

        _force_kill_process_sync(proc)

        mock_sigterm.assert_called_once_with(12345, "SearXNG")
        proc.wait.assert_called_once()

    @patch("web_core.search.runner.logger")
    def test_exception_handling(self, mock_logger):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345

        with patch("web_core.search.runner.sys") as mock_sys:
            mock_sys.platform = "unix"
            with patch("os.getpgid", side_effect=Exception("boom")):
                _force_kill_process_sync(proc)

        # Should not raise, but log
        assert mock_logger.debug.called

# ---------------------------------------------------------------------------
# _force_kill_process (async)
# ---------------------------------------------------------------------------

class TestForceKillProcessAsync:
    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("os.getpgid")
    @patch("os.killpg")
    @patch("asyncio.to_thread")
    async def test_unix_graceful_success(self, mock_to_thread, mock_killpg, mock_getpgid):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345
        mock_getpgid.return_value = 5555
        mock_to_thread.return_value = None

        await _force_kill_process(proc)

        mock_killpg.assert_any_call(5555, signal.SIGTERM)
        mock_to_thread.assert_called_with(proc.wait, timeout=3)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("os.getpgid")
    @patch("os.killpg")
    @patch("asyncio.to_thread")
    async def test_unix_killpg_sigkill_error_fallback(self, mock_to_thread, mock_killpg, mock_getpgid):
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345
        mock_getpgid.return_value = 5555
        # SIGTERM succeeds, wait timeouts, SIGKILL fails
        mock_to_thread.side_effect = [subprocess.TimeoutExpired(cmd="", timeout=3), None]
        mock_killpg.side_effect = [None, ProcessLookupError]

        await _force_kill_process(proc)

        proc.kill.assert_called_once()

    @patch("web_core.search.runner.sys")
    @patch("web_core.search.runner._sigterm_then_kill")
    @patch("asyncio.to_thread")
    async def test_windows_branch(self, mock_to_thread, mock_sigterm, mock_sys):
        mock_sys.platform = "win32"
        proc = MagicMock(spec=subprocess.Popen)
        proc.poll.return_value = None
        proc.pid = 12345
        mock_sigterm.return_value = True

        await _force_kill_process(proc)

        mock_sigterm.assert_called_once_with(12345, "SearXNG")
        mock_to_thread.assert_called_with(proc.wait, timeout=3)

# ---------------------------------------------------------------------------
# _kill_stale_port_process
# ---------------------------------------------------------------------------

class TestKillStalePortProcess:
    async def test_invalid_port(self):
        # Should return immediately
        await _kill_stale_port_process(0)
        await _kill_stale_port_process(70000)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("asyncio.to_thread")
    @patch("web_core.search.runner._sigterm_then_kill")
    async def test_unix_lsof_success(self, mock_sigterm, mock_to_thread):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "12345\n"
        mock_to_thread.return_value = mock_result

        await _kill_stale_port_process(8888)

        mock_to_thread.assert_called()
        mock_sigterm.assert_called_with(12345, "stale port 8888")

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix branch test")
    @patch("asyncio.to_thread")
    @patch("web_core.search.runner._sigterm_then_kill")
    async def test_unix_fuser_fallback(self, mock_sigterm, mock_to_thread):
        # lsof fails with FileNotFoundError (simulated by lsof not found in result)
        mock_lsof_result = MagicMock()
        mock_lsof_result.returncode = 1

        # We need to simulate FileNotFoundError on the first call to to_thread
        mock_to_thread.side_effect = [FileNotFoundError, MagicMock(returncode=0)]

        await _kill_stale_port_process(8888)

        assert mock_to_thread.call_count == 2
        # fuser -k handles killing, so sigterm should NOT be called by us
        mock_sigterm.assert_not_called()

    @patch("web_core.search.runner.sys")
    @patch("asyncio.to_thread")
    @patch("web_core.search.runner._sigterm_then_kill")
    async def test_windows_netstat_success(self, mock_sigterm, mock_to_thread, mock_sys):
        mock_sys.platform = "win32"
        mock_result = MagicMock()
        mock_result.stdout = "  TCP    127.0.0.1:8888         0.0.0.0:0              LISTENING       12345\n"
        mock_to_thread.return_value = mock_result

        await _kill_stale_port_process(8888)

        mock_sigterm.assert_called_with(12345, "stale port 8888")
