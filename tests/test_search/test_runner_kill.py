import subprocess
from unittest.mock import ANY, MagicMock, patch

from web_core.search.runner import _force_kill_process


def test_force_kill_process_exception_handling_unix():
    """Test that _force_kill_process handles unexpected exceptions on Unix."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.poll.return_value = None  # Process is alive
    mock_proc.pid = 12345

    # We patch sys.platform to 'linux' and os.getpgid to raise an unexpected Exception.
    with (
        patch("web_core.search.runner.sys.platform", "linux"),
        patch("web_core.search.runner.os.getpgid", side_effect=RuntimeError("Unexpected Unix error")),
        patch("web_core.search.runner.logger") as mock_logger,
    ):
        _force_kill_process(mock_proc)

        mock_logger.debug.assert_any_call("Error killing SearXNG process: %s", ANY)


def test_force_kill_process_exception_handling_windows():
    """Test that _force_kill_process handles unexpected exceptions on Windows."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.poll.return_value = None  # Process is alive
    mock_proc.pid = 12345

    with (
        patch("web_core.search.runner.sys.platform", "win32"),
        patch("web_core.search.runner._sigterm_then_kill", side_effect=RuntimeError("Unexpected Windows error")),
        patch("web_core.search.runner.logger") as mock_logger,
    ):
        _force_kill_process(mock_proc)

        mock_logger.debug.assert_any_call("Error killing SearXNG process: %s", ANY)


def test_force_kill_process_already_dead():
    """Test that _force_kill_process returns early if process is already dead."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.poll.return_value = 0  # Already dead

    _force_kill_process(mock_proc)

    assert mock_proc.poll.called


def test_force_kill_process_unix_timeout_expired():
    """Test Unix path where wait times out."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.poll.return_value = None
    mock_proc.pid = 12345
    mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3)

    with (
        patch("web_core.search.runner.sys.platform", "linux"),
        patch("web_core.search.runner.os.getpgid", return_value=12345),
        patch("web_core.search.runner.os.killpg") as mock_killpg,
        patch("web_core.search.runner.logger") as mock_logger,
    ):
        _force_kill_process(mock_proc)

        assert mock_killpg.call_count == 2
        mock_logger.warning.assert_any_call("SearXNG process (PID=%d) could not be killed", 12345)


def test_force_kill_process_unix_os_killpg_error():
    """Test Unix path where os.killpg raises ProcessLookupError."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.poll.return_value = None
    mock_proc.pid = 12345
    mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3)

    with (
        patch("web_core.search.runner.sys.platform", "linux"),
        patch("web_core.search.runner.os.getpgid", return_value=12345),
        patch("web_core.search.runner.os.killpg", side_effect=ProcessLookupError),
        patch("web_core.search.runner.logger"),
    ):
        _force_kill_process(mock_proc)

        assert mock_proc.terminate.called
        assert mock_proc.kill.called


def test_force_kill_process_windows_timeout_expired():
    """Test Windows path where wait times out."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.poll.return_value = None
    mock_proc.pid = 12345
    mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3)

    with (
        patch("web_core.search.runner.sys.platform", "win32"),
        patch("web_core.search.runner._sigterm_then_kill") as mock_sigterm,
    ):
        _force_kill_process(mock_proc)

        assert mock_sigterm.called
        assert mock_proc.kill.called
