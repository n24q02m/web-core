def _sigterm_then_kill_sync(pid: int, label: str = "") -> bool:  # pragma: no cover
    """Send SIGTERM to a PID, wait briefly, then SIGKILL if needed.

    Returns ``True`` if the process was successfully terminated.
    """
    tag = f" ({label})" if label else ""
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return True  # Already dead or inaccessible

    # Wait up to 3 seconds for graceful exit.
    for _ in range(30):
        try:
            os.kill(pid, 0)  # Check if alive
        except ProcessLookupError:
            logger.debug("Process PID=%d%s terminated gracefully", pid, tag)
            return True
        except PermissionError:
            return True
        time.sleep(0.1)

    # Force kill.
    try:
        os.kill(pid, signal.SIGKILL)
        logger.debug("Process PID=%d%s force-killed", pid, tag)
        return True
    except (ProcessLookupError, PermissionError):
        return True


async def _sigterm_then_kill(pid: int, label: str = "") -> bool:  # pragma: no cover
    """Send SIGTERM to a PID, wait briefly, then SIGKILL if needed (async).

    Returns ``True`` if the process was successfully terminated.
    """
    tag = f" ({label})" if label else ""
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return True  # Already dead or inaccessible

    # Wait up to 3 seconds for graceful exit.
    for _ in range(30):
        try:
            os.kill(pid, 0)  # Check if alive
        except ProcessLookupError:
            logger.debug("Process PID=%d%s terminated gracefully", pid, tag)
            return True
        except PermissionError:
            return True
        await asyncio.sleep(0.1)

    # Force kill.
    try:
        os.kill(pid, signal.SIGKILL)
        logger.debug("Process PID=%d%s force-killed", pid, tag)
        return True
    except (ProcessLookupError, PermissionError):
        return True


def _force_kill_process_sync(proc: subprocess.Popen) -> None:  # pragma: no cover
    """Force-kill a subprocess and all its children.

    Tries graceful SIGTERM first, then SIGKILL after a short timeout.
    On Unix, kills the entire process group to avoid orphaned children.
    """
    if proc.poll() is not None:
        return  # Already dead

    pid = proc.pid
    logger.debug("Force-killing SearXNG process (PID=%d)...", pid)

    try:
        if sys.platform != "win32":
            # Kill the entire process group on Unix.
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                proc.terminate()

            try:
                proc.wait(timeout=3)
                logger.debug("SearXNG process (PID=%d) terminated gracefully", pid)
                return
            except subprocess.TimeoutExpired:
                pass

            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()

            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                logger.warning("SearXNG process (PID=%d) could not be killed", pid)
        else:
            _sigterm_then_kill_sync(pid, "SearXNG")
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception as e:
        logger.debug("Error killing SearXNG process: %s", e)


async def _force_kill_process(proc: subprocess.Popen) -> None:  # pragma: no cover
    """Force-kill a subprocess and all its children (async).

    Tries graceful SIGTERM first, then SIGKILL after a short timeout.
    On Unix, kills the entire process group to avoid orphaned children.
    """
    if proc.poll() is not None:
        return  # Already dead

    pid = proc.pid
    logger.debug("Force-killing SearXNG process (PID=%d)...", pid)

    try:
        if sys.platform != "win32":
            # Kill the entire process group on Unix.
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                proc.terminate()

            try:
                await asyncio.to_thread(proc.wait, timeout=3)
                logger.debug("SearXNG process (PID=%d) terminated gracefully", pid)
                return
            except (subprocess.TimeoutExpired, asyncio.TimeoutError):
                pass

            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()

            try:
                await asyncio.to_thread(proc.wait, timeout=3)
            except (subprocess.TimeoutExpired, asyncio.TimeoutError):
                logger.warning("SearXNG process (PID=%d) could not be killed", pid)
        else:
            await _sigterm_then_kill(pid, "SearXNG")
            try:
                await asyncio.to_thread(proc.wait, timeout=3)
            except (subprocess.TimeoutExpired, asyncio.TimeoutError):
                proc.kill()
    except Exception as e:
        logger.debug("Error killing SearXNG process: %s", e)
