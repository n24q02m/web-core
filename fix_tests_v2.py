import signal

path = 'tests/test_search/test_runner.py'
with open(path, 'r') as f:
    content = f.read()

# For TestSigtermThenKillSync.test_force_kill and TestSigtermThenKill.test_graceful_exit_async
# they run on host platform in mocks if not patched.
# Actually I should patch sys.platform to linux for these tests to ensure SIGKILL path is tested.

content = content.replace(
    'def test_force_kill(self):',
    'def test_force_kill(self):\n        with patch("sys.platform", "linux"):',
)

content = content.replace(
    'async def test_graceful_exit_async(self):',
    'async def test_graceful_exit_async(self):\n        with patch("sys.platform", "linux"):',
)

with open(path, 'w') as f:
    f.write(content)
