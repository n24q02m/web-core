path = 'src/web_core/search/runner.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
imports_done = False
for line in lines:
    if line.strip() == '_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)':
        continue
    new_lines.append(line)
    if not imports_done and line.startswith('import time'):
        new_lines.append('\n')
        new_lines.append('_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)\n')
        imports_done = True

with open(path, 'w') as f:
    f.writelines(new_lines)
