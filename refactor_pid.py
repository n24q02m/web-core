import sys
from pathlib import Path

path = Path("src/web_core/search/runner.py")
content = path.read_text()

old_code = """def _is_pid_alive(pid: int) -> bool:  # pragma: no cover
    \"\"\"Check if a process with the given PID is alive (not zombie).

    On Windows, uses ctypes ``OpenProcess`` since ``os.kill(pid, 0)`` does
    not work for non-child processes.  On Linux, additionally checks
    ``/proc/{pid}/status`` for zombie state.
    \"\"\"
    if pid <= 0:
        return False

    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
            return True
        return False

    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False

    # On Linux, check /proc/{pid}/status for zombie state.
    # os.kill(pid, 0) succeeds for zombie processes (PID still in table),
    # but they are defunct and cannot serve requests.
    try:
        status_path = Path(f"/proc/{pid}/status")
        if status_path.exists():
            for line in status_path.read_text().splitlines():
                if line.startswith("State:"):
                    if "Z" in line.split(":")[1]:
                        logger.debug("PID %d is a zombie process", pid)
                        return False
                    break
    except OSError:
        pass

    return True"""

new_code = """def _is_pid_alive_win32(pid: int) -> bool:
    \"\"\"Windows-specific PID liveness check using ctypes OpenProcess.\"\"\"
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid
    )
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        return True
    return False


def _is_zombie(pid: int) -> bool:
    \"\"\"Check if a Linux process is in a zombie state.\"\"\"
    try:
        status_path = Path(f"/proc/{pid}/status")
        if not status_path.exists():
            return False

        for line in status_path.read_text().splitlines():
            if line.startswith("State:"):
                state_info = line.split(":")[1]
                if "Z" in state_info:
                    logger.debug("PID %d is a zombie process", pid)
                    return True
                break
    except OSError:
        pass
    return False


def _is_pid_alive(pid: int) -> bool:  # pragma: no cover
    \"\"\"Check if a process with the given PID is alive (not zombie).

    On Windows, uses ctypes ``OpenProcess`` since ``os.kill(pid, 0)`` does
    not work for non-child processes.  On Linux, additionally checks
    ``/proc/{pid}/status`` for zombie state.
    \"\"\"
    if pid <= 0:
        return False

    if sys.platform == "win32":
        return _is_pid_alive_win32(pid)

    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False

    # On Linux, check /proc/{pid}/status for zombie state.
    # os.kill(pid, 0) succeeds for zombie processes (PID still in table),
    # but they are defunct and cannot serve requests.
    if _is_zombie(pid):
        return False

    return True"""

if old_code in content:
    new_content = content.replace(old_code, new_code)
    path.write_text(new_content)
    print("Successfully refactored.")
else:
    print("Could not find the exact old_code block.")
    sys.exit(1)
