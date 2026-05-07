path = 'tests/test_search/test_runner.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "signal.SIGKILL" in line:
        if "assert_any_call" in line and "mock_killpg" not in line:
             # This is for _sigterm_then_kill tests which are run under default platform (linux in my local mock, but might be windows in CI)
             # Wait, the tests mock sys.platform = "linux" or "win32" sometimes, but not always.
             # Let's check the context.
             new_lines.append(line)
        else:
             new_lines.append(line)
    else:
        new_lines.append(line)

# Actually, I'll just use sed to conditionally check SIGKILL only if it exists
# But the issue is signal.SIGKILL does not EXIST on windows.
# So I should use getattr(signal, "SIGKILL", signal.SIGTERM) in tests too if I want them to be platform-agnostic,
# OR ensure I'm mocking sys.platform.

with open(path, 'w') as f:
    for line in lines:
        f.write(line.replace('signal.SIGKILL', 'getattr(signal, "SIGKILL", signal.SIGTERM)'))
