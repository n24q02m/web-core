path = 'src/web_core/search/runner.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == '_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)':
        continue
    new_lines.append(line)
    if line.startswith('logger = logging.getLogger'):
        new_lines.append('\n')
        new_lines.append('_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)\n')

with open(path, 'w') as f:
    f.writelines(new_lines)
