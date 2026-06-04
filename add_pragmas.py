from pathlib import Path

path = Path("src/web_core/search/runner.py")
content = path.read_text()

content = content.replace(
    "def _is_pid_alive_win32(pid: int) -> bool:",
    "def _is_pid_alive_win32(pid: int) -> bool:  # pragma: no cover"
)
content = content.replace(
    "def _is_zombie(pid: int) -> bool:",
    "def _is_zombie(pid: int) -> bool:  # pragma: no cover"
)

path.write_text(content)
print("Added pragmas.")
