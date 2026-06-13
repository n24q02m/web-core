import signal
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import web_core.search.runner as runner_mod
from web_core.search.runner import (
    _cleanup_process,
    _force_kill_process,
    _force_kill_process_sync,
    _is_pid_alive,
    _is_process_dead,
    _kill_stale_port_process,
    _sigterm_then_kill,
    _sigterm_then_kill_sync,
)


class TestProcessLiveness:
    def test_is_pid_alive_windows_success(self):
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32.OpenProcess.return_value = 0x123
        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch.dict("sys.modules", {"ctypes": mock_ctypes}),
        ):
            assert _is_pid_alive(1234) is True
            mock_ctypes.windll.kernel32.OpenProcess.assert_called_once()
            mock_ctypes.windll.kernel32.CloseHandle.assert_called_once()

    def test_is_pid_alive_windows_failure(self):
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32.OpenProcess.return_value = 0
        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch.dict("sys.modules", {"ctypes": mock_ctypes}),
        ):
            assert _is_pid_alive(1234) is False
            mock_ctypes.windll.kernel32.OpenProcess.assert_called_once()

    def test_is_pid_alive_linux_alive(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.kill", return_value=None),
            patch("web_core.search.runner.Path.exists", return_value=True),
            patch("web_core.search.runner.Path.read_text", return_value="Name: bash\nState: S (sleeping)\n"),
        ):
            assert _is_pid_alive(1234) is True

    def test_is_pid_alive_linux_no_proc_status(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.kill", return_value=None),
            patch("web_core.search.runner.Path.exists", return_value=False),
        ):
            assert _is_pid_alive(1234) is True

    def test_is_pid_alive_linux_oserror_reading_status(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.kill", return_value=None),
            patch("web_core.search.runner.Path.exists", return_value=True),
            patch("web_core.search.runner.Path.read_text", side_effect=OSError()),
        ):
            assert _is_pid_alive(1234) is True

    def test_is_pid_alive_linux_dead(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.kill", side_effect=ProcessLookupError()),
        ):
            assert _is_pid_alive(1234) is False

    def test_is_pid_alive_linux_zombie(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.kill", return_value=None),
            patch("web_core.search.runner.Path.exists", return_value=True),
            patch("web_core.search.runner.Path.read_text", return_value="Name: bash\nState: Z (zombie)\n"),
        ):
            assert _is_pid_alive(1234) is False

    def test_is_pid_alive_invalid_pid(self):
        assert _is_pid_alive(0) is False
        assert _is_pid_alive(-1) is False


class TestSigtermThenKill:
    def test_sigterm_then_kill_sync_graceful(self):
        with (
            patch("os.kill") as mock_kill,
            patch("web_core.search.runner._is_process_dead", side_effect=[False, True]),
            patch("time.sleep"),
        ):
            assert _sigterm_then_kill_sync(1234, "test") is True
            mock_kill.assert_called_once_with(1234, signal.SIGTERM)

    def test_sigterm_then_kill_sync_force(self):
        with (
            patch("os.kill") as mock_kill,
            patch("web_core.search.runner._is_process_dead", return_value=False),
            patch("time.sleep"),
        ):
            assert _sigterm_then_kill_sync(1234, "test") is True
            assert mock_kill.call_count == 2
            mock_kill.assert_any_call(1234, signal.SIGTERM)
            mock_kill.assert_any_call(1234, signal.SIGKILL)

    def test_sigterm_then_kill_sync_force_exception(self):
        with (
            patch("os.kill", side_effect=[None, ProcessLookupError()]),
            patch("web_core.search.runner._is_process_dead", return_value=False),
            patch("time.sleep"),
        ):
            assert _sigterm_then_kill_sync(1234, "test") is True

    def test_sigterm_then_kill_sync_already_dead(self):
        with patch("os.kill", side_effect=ProcessLookupError()):
            assert _sigterm_then_kill_sync(1234, "test") is True

    @pytest.mark.asyncio
    async def test_sigterm_then_kill_async_graceful(self):
        with (
            patch("os.kill") as mock_kill,
            patch("web_core.search.runner._is_process_dead", side_effect=[False, True]),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            assert await _sigterm_then_kill(1234, "test") is True
            mock_kill.assert_called_once_with(1234, signal.SIGTERM)

    @pytest.mark.asyncio
    async def test_sigterm_then_kill_async_sigterm_exception(self):
        with patch("os.kill", side_effect=ProcessLookupError()):
            assert await _sigterm_then_kill(1234, "test") is True

    @pytest.mark.asyncio
    async def test_sigterm_then_kill_async_force(self):
        with (
            patch("os.kill") as mock_kill,
            patch("web_core.search.runner._is_process_dead", return_value=False),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            assert await _sigterm_then_kill(1234, "test") is True
            assert mock_kill.call_count == 2
            mock_kill.assert_any_call(1234, signal.SIGTERM)
            mock_kill.assert_any_call(1234, signal.SIGKILL)

    @pytest.mark.asyncio
    async def test_sigterm_then_kill_async_force_exception(self):
        with (
            patch("os.kill", side_effect=[None, ProcessLookupError()]),
            patch("web_core.search.runner._is_process_dead", return_value=False),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            assert await _sigterm_then_kill(1234, "test") is True


class TestForceKillProcess:
    def test_force_kill_process_sync_windows_success(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("web_core.search.runner._sigterm_then_kill_sync") as mock_sigterm,
        ):
            _force_kill_process_sync(mock_proc)
            mock_sigterm.assert_called_once_with(1234, "SearXNG")
            mock_proc.wait.assert_called_once()

    def test_force_kill_process_sync_windows_timeout(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234
        mock_proc.wait.side_effect = subprocess.TimeoutExpired(["cmd"], 3)

        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("web_core.search.runner._sigterm_then_kill_sync") as mock_sigterm,
        ):
            _force_kill_process_sync(mock_proc)
            mock_sigterm.assert_called_once_with(1234, "SearXNG")
            mock_proc.kill.assert_called_once()

    def test_force_kill_process_sync_exception(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("web_core.search.runner._sigterm_then_kill_sync", side_effect=Exception("oops")),
        ):
            # Should catch and log
            _force_kill_process_sync(mock_proc)

    def test_force_kill_process_sync_linux_graceful(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg") as mock_killpg,
        ):
            _force_kill_process_sync(mock_proc)
            mock_killpg.assert_called_once_with(5678, signal.SIGTERM)
            mock_proc.wait.assert_called_once()

    def test_force_kill_process_sync_linux_killpg_error(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired(["cmd"], 3), None]

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg", side_effect=[ProcessLookupError(), ProcessLookupError()]),
        ):
            _force_kill_process_sync(mock_proc)
            mock_proc.terminate.assert_called_once()
            mock_proc.kill.assert_called_once()

    def test_force_kill_process_sync_linux_force(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired(["cmd"], 3), 0]

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg") as mock_killpg,
        ):
            _force_kill_process_sync(mock_proc)
            assert mock_killpg.call_count == 2
            mock_killpg.assert_any_call(5678, signal.SIGTERM)
            mock_killpg.assert_any_call(5678, signal.SIGKILL)

    def test_force_kill_process_sync_linux_force_timeout_warn(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired(["cmd"], 3), subprocess.TimeoutExpired(["cmd"], 3)]

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg") as mock_killpg,
        ):
            _force_kill_process_sync(mock_proc)
            assert mock_killpg.call_count == 2

    @pytest.mark.asyncio
    async def test_force_kill_process_async_already_dead(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = 0
        await _force_kill_process(mock_proc)
        mock_proc.wait.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_kill_process_async_windows_success(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_sigterm,
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            await _force_kill_process(mock_proc)
            mock_sigterm.assert_called_once_with(1234, "SearXNG")
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_kill_process_async_windows_timeout(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_sigterm,
            patch("asyncio.to_thread", side_effect=subprocess.TimeoutExpired(["cmd"], 3)),
        ):
            await _force_kill_process(mock_proc)
            mock_sigterm.assert_called_once_with(1234, "SearXNG")
            mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_kill_process_async_exception(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("web_core.search.runner._sigterm_then_kill", side_effect=Exception("oops")),
        ):
            await _force_kill_process(mock_proc)

    @pytest.mark.asyncio
    async def test_force_kill_process_async_linux_graceful(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg") as mock_killpg,
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            await _force_kill_process(mock_proc)
            mock_killpg.assert_called_once_with(5678, signal.SIGTERM)
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_kill_process_async_linux_force(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg") as mock_killpg,
            patch("asyncio.to_thread", side_effect=[subprocess.TimeoutExpired(["cmd"], 3), None]),
        ):
            await _force_kill_process(mock_proc)
            assert mock_killpg.call_count == 2
            mock_killpg.assert_any_call(5678, signal.SIGTERM)
            mock_killpg.assert_any_call(5678, signal.SIGKILL)

    @pytest.mark.asyncio
    async def test_force_kill_process_async_linux_killpg_error(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg", side_effect=[ProcessLookupError(), ProcessLookupError()]),
            patch("asyncio.to_thread", side_effect=[subprocess.TimeoutExpired(["cmd"], 3), None]),
        ):
            await _force_kill_process(mock_proc)
            mock_proc.terminate.assert_called_once()
            mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_kill_process_async_linux_force_timeout_warn(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.pid = 1234

        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("os.getpgid", return_value=5678),
            patch("os.killpg") as mock_killpg,
            patch("asyncio.to_thread", side_effect=[subprocess.TimeoutExpired(["cmd"], 3)] * 2),
        ):
            await _force_kill_process(mock_proc)
            assert mock_killpg.call_count == 2

    def test_force_kill_process_sync_already_terminated(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = 0

        _force_kill_process_sync(mock_proc)
        mock_proc.wait.assert_not_called()


class TestIsProcessDead:
    def test_is_process_dead_true(self):
        with patch("os.kill", side_effect=ProcessLookupError()):
            assert _is_process_dead(1234) is True

    def test_is_process_dead_false(self):
        with patch("os.kill", return_value=None):
            assert _is_process_dead(1234) is False

    def test_is_process_dead_permission_error(self):
        with patch("os.kill", side_effect=PermissionError()):
            assert _is_process_dead(1234) is True


class TestKillStalePortProcess:
    @pytest.mark.asyncio
    async def test_kill_stale_port_process_invalid_port(self):
        assert await _kill_stale_port_process(0) is None
        assert await _kill_stale_port_process(65536) is None

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_windows_success(self):
        mock_res = MagicMock()
        mock_res.stdout = "  TCP    127.0.0.1:8888         0.0.0.0:0              LISTENING       1234\n"
        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("asyncio.to_thread", return_value=mock_res),
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_kill,
        ):
            await _kill_stale_port_process(8888)
            mock_kill.assert_called_once_with(1234, "stale port 8888")

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_windows_no_str_stdout(self):
        mock_res = MagicMock()
        mock_res.stdout = b"  TCP    127.0.0.1:8888         0.0.0.0:0              LISTENING       1234\n"
        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("asyncio.to_thread", return_value=mock_res),
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_kill,
        ):
            await _kill_stale_port_process(8888)
            mock_kill.assert_called_once_with(1234, "stale port 8888")

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_windows_kill_exception(self):
        mock_res = MagicMock()
        mock_res.stdout = "  TCP    127.0.0.1:8888         0.0.0.0:0              LISTENING       1234\n"
        with (
            patch("web_core.search.runner.sys.platform", "win32"),
            patch("asyncio.to_thread", return_value=mock_res),
            patch("web_core.search.runner._sigterm_then_kill", side_effect=PermissionError()),
        ):
            # Should catch and log
            await _kill_stale_port_process(8888)

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_linux_lsof_success(self):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "1234\n5678\n"
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("asyncio.to_thread", return_value=mock_res),
            patch("os.getpid", return_value=9999),
            patch("web_core.search.runner._sigterm_then_kill", new_callable=AsyncMock) as mock_kill,
        ):
            await _kill_stale_port_process(8888)
            assert mock_kill.call_count == 2
            mock_kill.assert_any_call(1234, "stale port 8888")
            mock_kill.assert_any_call(5678, "stale port 8888")

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_linux_lsof_kill_exception(self):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "1234\n"
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("asyncio.to_thread", return_value=mock_res),
            patch("os.getpid", return_value=9999),
            patch("web_core.search.runner._sigterm_then_kill", side_effect=PermissionError()),
        ):
            await _kill_stale_port_process(8888)

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_linux_fuser_fallback(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("asyncio.to_thread", side_effect=[FileNotFoundError(), MagicMock()]),
        ):
            await _kill_stale_port_process(8888)

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_linux_fuser_fallback_fail(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("asyncio.to_thread", side_effect=[FileNotFoundError(), FileNotFoundError()]),
        ):
            await _kill_stale_port_process(8888)

    @pytest.mark.asyncio
    async def test_kill_stale_port_process_linux_exception(self):
        with (
            patch("web_core.search.runner.sys.platform", "linux"),
            patch("asyncio.to_thread", side_effect=Exception("oops")),
        ):
            await _kill_stale_port_process(8888)


class TestCleanupProcess:
    @pytest.fixture(autouse=True)
    def reset_mod_state(self):
        old_container = runner_mod._searxng_docker_container
        old_is_owner = runner_mod._is_owner
        old_process = runner_mod._searxng_process
        old_settings = runner_mod._searxng_settings_path
        yield
        runner_mod._searxng_docker_container = old_container
        runner_mod._is_owner = old_is_owner
        runner_mod._searxng_process = old_process
        runner_mod._searxng_settings_path = old_settings

    def test_cleanup_process_owner_docker(self):
        runner_mod._searxng_docker_container = "test-container"
        runner_mod._is_owner = True

        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("subprocess.run") as mock_run,
            patch("web_core.search.runner._remove_discovery") as mock_remove,
        ):
            _cleanup_process()
            mock_run.assert_called_once()
            assert "rm" in mock_run.call_args[0][0]
            mock_remove.assert_called_once()
            assert runner_mod._searxng_docker_container is None

    def test_cleanup_process_owner_docker_no_bin(self):
        runner_mod._searxng_docker_container = "test-container"
        runner_mod._is_owner = True

        with (
            patch("shutil.which", return_value=None),
            patch("web_core.search.runner._remove_discovery") as mock_remove,
        ):
            _cleanup_process()
            mock_remove.assert_called_once()
            assert runner_mod._searxng_docker_container is None

    def test_cleanup_process_owner_subprocess(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        runner_mod._searxng_process = mock_proc
        runner_mod._is_owner = True

        with (
            patch("web_core.search.runner._force_kill_process_sync") as mock_kill,
            patch("web_core.search.runner._remove_discovery") as mock_remove,
        ):
            _cleanup_process()
            mock_kill.assert_called_once_with(mock_proc)
            mock_remove.assert_called_once()
            assert runner_mod._searxng_process is None

    def test_cleanup_process_owner_subprocess_exception(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        runner_mod._searxng_process = mock_proc
        runner_mod._is_owner = True

        with (
            patch("web_core.search.runner._force_kill_process_sync", side_effect=Exception("oops")),
            patch("web_core.search.runner._remove_discovery"),
        ):
            _cleanup_process()
            assert runner_mod._searxng_process is None

    def test_cleanup_process_non_owner(self):
        runner_mod._searxng_docker_container = "test-container"
        runner_mod._is_owner = False
        runner_mod._searxng_process = MagicMock()

        _cleanup_process()
        assert runner_mod._searxng_docker_container is None
        assert runner_mod._searxng_process is None
        assert runner_mod._is_owner is False

    def test_cleanup_process_settings_file(self):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        runner_mod._searxng_settings_path = mock_path

        _cleanup_process()
        mock_path.unlink.assert_called_once()

    def test_cleanup_process_settings_file_exception(self):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.unlink.side_effect = Exception("oops")
        runner_mod._searxng_settings_path = mock_path

        _cleanup_process()
        mock_path.unlink.assert_called_once()
