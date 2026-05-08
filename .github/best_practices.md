# Style Guide - n24q02m-web-core

## Architecture
Shared web infrastructure: search, scraping, HTTP security, browsers

## Python
- Runtime: Python 3.13.* (pinned via `.mise.toml` + `pyproject.toml [project] requires-python`)
- Package manager: `uv` (lockfile committed)
- Lint: `ruff` (config in pyproject.toml or `.ruff.toml`); line length 88; rules E/F/W/I/UP/B/C4
- Format: `ruff format` (drop-in `black` replacement)
- Type check: `ty` (preferred) or `mypy` (strict mode)
- Tests: `pytest` with `pytest-asyncio` (asyncio_mode=auto), default timeout 30s
- Coverage target: ≥ 95% on `src/<package>/`

## Code Patterns
- Pydantic Settings for config (singleton via lru_cache)
- Async-first (`asyncio.to_thread()` for sync wrapping)
- Errors: tools return error strings (`return "Error: ..."`), don't raise
- Lazy imports for heavy deps + circular avoidance
- `match action:` for tool action dispatch

## CI/CD
- CI: ruff check + format-check + ty + pytest (`mise run lint && mise run test`)
- CD: workflow_dispatch trigger, PSR v10 → uv publish PyPI + Docker multi-arch + MCP Registry (if MCP server)

## Pre-commit
- ruff (`--fix --target-version=py313`)
- ruff format
- ty type check
- pytest (`--tb=short -q --timeout=30`)
- commit-msg: enforce `feat:` / `fix:` prefix
