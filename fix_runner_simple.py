import os
import signal

path = 'src/web_core/search/runner.py'
with open(path, 'r') as f:
    content = f.read()

# Add _SIGKILL
content = content.replace('import signal', 'import signal\n\n_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)')

# Replace all signal.SIGKILL
content = content.replace('signal.SIGKILL', '_SIGKILL')

# Remove pragmas I already removed but just to be sure if I reverted
content = content.replace('  # pragma: no cover', '')

with open(path, 'w') as f:
    f.write(content)
