path = 'tests/test_search/test_runner.py'
with open(path, 'r') as f:
    content = f.read()

content = content.replace(
    'with patch("sys.platform", "linux"), (',
    'with patch("sys.platform", "linux"),',
)

with open(path, 'w') as f:
    f.write(content)
