import sys
import subprocess
from unittest.mock import MagicMock, patch
import pytest
import web_core.search.runner as runner

def test_kill_stale_port_process_win32():
    with patch("web_core.search.runner.sys.platform", "win32"), \
         patch("web_core.search.runner.subprocess.run") as mock_run, \
         patch("web_core.search.runner._sigterm_then_kill") as mock_kill:

        # Mock netstat output
        mock_run.return_value = MagicMock(
            stdout="  TCP    127.0.0.1:18888        0.0.0.0:0              LISTENING       1234\n",
            returncode=0
        )

        runner._kill_stale_port_process(18888)

        mock_run.assert_called_once()
        assert "netstat" in mock_run.call_args[0][0]
        mock_kill.assert_called_once_with(1234, "stale port 18888")

def test_kill_stale_port_process_unix_lsof():
    with patch("web_core.search.runner.sys.platform", "linux"), \
         patch("web_core.search.runner.subprocess.run") as mock_run, \
         patch("web_core.search.runner._sigterm_then_kill") as mock_kill, \
         patch("web_core.search.runner.os.getpid", return_value=999):

        # Mock lsof output
        mock_run.return_value = MagicMock(
            stdout="1234\n",
            returncode=0
        )

        runner._kill_stale_port_process(18888)

        # subprocess.run should be called with lsof
        mock_run.assert_called_once()
        assert "lsof" in mock_run.call_args[0][0]
        mock_kill.assert_called_once_with(1234, "stale port 18888")

def test_kill_stale_port_process_unix_fuser_fallback():
    with patch("web_core.search.runner.sys.platform", "linux"), \
         patch("web_core.search.runner.subprocess.run") as mock_run, \
         patch("web_core.search.runner._sigterm_then_kill") as mock_kill, \
         patch("web_core.search.runner.os.getpid", return_value=999):

        # First call to lsof fails with FileNotFoundError
        mock_run.side_effect = [FileNotFoundError, MagicMock(returncode=0)]

        runner._kill_stale_port_process(18888)

        assert mock_run.call_count == 2
        assert "lsof" in mock_run.call_args_list[0][0][0]
        assert "fuser" in mock_run.call_args_list[1][0][0]

def test_kill_stale_port_process_invalid_port():
    with patch("web_core.search.runner.subprocess.run") as mock_run:
        runner._kill_stale_port_process(0)
        runner._kill_stale_port_process(65536)
        runner._kill_stale_port_process("invalid")
        mock_run.assert_not_called()
