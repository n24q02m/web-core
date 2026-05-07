import signal

path = 'src/web_core/search/runner.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
# Add _SIGKILL definition after imports
added_sigkill = False
for line in lines:
    new_lines.append(line)
    if not added_sigkill and line.startswith("import signal"):
        new_lines.append("\n")
        new_lines.append("_SIGKILL = getattr(signal, \"SIGKILL\", signal.SIGTERM)\n")
        added_sigkill = True

# Replace all signal.SIGKILL with _SIGKILL
final_lines = []
for line in new_lines:
    # Special case: I added some if sys.platform blocks before, let's revert them to be cleaner
    if 'os.kill(pid, signal.SIGKILL)' in line or 'os.kill(pid, signal.SIGTERM)  # Windows fallback' in line:
        continue
    if 'if sys.platform != "win32":' in line and 'os.kill(pid, _SIGKILL)' not in line:
         # Keep it if it guards os.killpg
         final_lines.append(line)
    elif "signal.SIGKILL" in line:
        final_lines.append(line.replace("signal.SIGKILL", "_SIGKILL"))
    else:
        final_lines.append(line)

# Wait, I should just do a clean replacement.
# Let's read the file again and do it properly.
