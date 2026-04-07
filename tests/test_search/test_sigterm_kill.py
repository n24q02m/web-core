import signal
from unittest.mock import call, patch

from web_core.search.runner import _sigterm_then_kill


def test_sigterm_then_kill_process_lookup_error_on_sigterm():
    """Returns True if os.kill raises ProcessLookupError on SIGTERM."""
    with patch("os.kill", side_effect=ProcessLookupError):
        assert _sigterm_then_kill(1234, "test") is True


def test_sigterm_then_kill_permission_error_on_sigterm():
    """Returns True if os.kill raises PermissionError on SIGTERM."""
    with patch("os.kill", side_effect=PermissionError):
        assert _sigterm_then_kill(1234, "test") is True


def test_sigterm_then_kill_graceful_exit():
    """Returns True if process terminates gracefully during the wait loop."""
    # First call to os.kill(pid, signal.SIGTERM) succeeds (None)
    # Second call to os.kill(pid, 0) (check if alive) raises ProcessLookupError (terminated)
    with patch("os.kill", side_effect=[None, ProcessLookupError]) as mock_kill, patch("time.sleep") as mock_sleep:
        assert _sigterm_then_kill(1234, "test") is True
        mock_kill.assert_has_calls([call(1234, signal.SIGTERM), call(1234, 0)])
        mock_sleep.assert_not_called()


def test_sigterm_then_kill_graceful_exit_after_some_retries():
    """Returns True if process terminates gracefully after a few checks."""
    # os.kill calls:
    # 1. os.kill(1234, signal.SIGTERM) -> returns None
    # 2. os.kill(1234, 0) (loop 0) -> returns None (still alive)
    # 3. os.kill(1234, 0) (loop 1) -> returns None (still alive)
    # 4. os.kill(1234, 0) (loop 2) -> returns None (still alive)
    # 5. os.kill(1234, 0) (loop 3) -> raises ProcessLookupError (graceful exit!)

    # Logic in _sigterm_then_kill:
    # try: os.kill(pid, 0)
    # except ProcessLookupError: return True
    # time.sleep(0.1)

    # Loop 0: kill(pid, 0) succeeds -> calls sleep(0.1)
    # Loop 1: kill(pid, 0) succeeds -> calls sleep(0.1)
    # Loop 2: kill(pid, 0) succeeds -> calls sleep(0.1)
    # Loop 3: kill(pid, 0) raises ProcessLookupError -> returns True (no more sleep)

    with (
        patch("os.kill", side_effect=[None, None, None, None, ProcessLookupError]) as mock_kill,
        patch("time.sleep") as mock_sleep,
    ):
        assert _sigterm_then_kill(1234, "test") is True
        assert mock_kill.call_count == 5
        assert mock_sleep.call_count == 3


def test_sigterm_then_kill_permission_error_in_loop():
    """Returns True if os.kill(pid, 0) raises PermissionError in loop."""
    with patch("os.kill", side_effect=[None, PermissionError]), patch("time.sleep"):
        assert _sigterm_then_kill(1234, "test") is True


def test_sigterm_then_kill_force_kill():
    """Returns True if process is force-killed after 30 retries."""
    # SIGTERM succeeds
    # 30 alive checks succeed
    # SIGKILL succeeds
    side_effects = [None] + ([None] * 30) + [None]
    with patch("os.kill", side_effect=side_effects) as mock_kill, patch("time.sleep") as mock_sleep:
        assert _sigterm_then_kill(1234, "test") is True
        # calls: SIGTERM (1), alive checks (30), SIGKILL (1) = 32
        assert mock_kill.call_count == 32
        assert mock_sleep.call_count == 30


def test_sigterm_then_kill_force_kill_lookup_error():
    """Returns True if SIGKILL raises ProcessLookupError."""
    # SIGTERM succeeds
    # 30 alive checks succeed
    # SIGKILL raises ProcessLookupError
    side_effects = [None] + ([None] * 30) + [ProcessLookupError]
    with patch("os.kill", side_effect=side_effects), patch("time.sleep"):
        assert _sigterm_then_kill(1234, "test") is True


def test_sigterm_then_kill_no_label():
    """Works correctly without a label."""
    with patch("os.kill", side_effect=ProcessLookupError):
        assert _sigterm_then_kill(1234) is True
