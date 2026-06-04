with open('src/web_core/adapters/mangadex.py', 'r') as f:
    lines = f.readlines()

# Line 190 (index 189) is '    # -- public API ---------------------------------------------------------'
# Let's insert a newline before it if it's too close or just ensure it's on its own line.
# Currently it looks like it's immediately after the return.

if '    # -- public API' in lines[189]:
    lines.insert(189, '\n')

with open('src/web_core/adapters/mangadex.py', 'w') as f:
    f.writelines(lines)
