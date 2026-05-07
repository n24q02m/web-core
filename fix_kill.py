import sys

path = 'src/web_core/search/runner.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "signal.SIGKILL" in line:
        # Check if we are inside if sys.platform != "win32" block or if it's the general case
        # For _sigterm_then_kill and _sigterm_then_kill_sync, they use os.kill(pid, signal.SIGKILL)
        # Windows doesn't have SIGKILL in signal module, but it has it in some environments?
        # Actually standard python on windows DOES NOT have SIGKILL.
        if "os.killpg" in line:
             new_lines.append(line)
        else:
             indent = line[:line.find("os.kill")]
             new_lines.append(f"{indent}if sys.platform != \"win32\":\n")
             new_lines.append(f"{indent}    os.kill(pid, signal.SIGKILL)\n")
             new_lines.append(f"{indent}else:\n")
             new_lines.append(f"{indent}    os.kill(pid, signal.SIGTERM)  # Windows fallback\n")
    else:
        new_lines.append(line)

with open(path, 'w') as f:
    f.writelines(new_lines)
