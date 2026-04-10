# AGENTS.md - web-core

Shared web infrastructure package: SearXNG search, multi-strategy scraping, SSRF-safe HTTP, stealth browsers. Python 3.13, uv, src layout.

## Build / Lint / Test Commands

```bash
uv sync --all-extras                # Install dependencies
uv build                            # Build package (hatchling)
uv run ruff check src/ tests/       # Lint
uv run ruff format --check src/ tests/  # Format check
uv run ruff format src/ tests/      # Format fix
uv run ruff check --fix src/ tests/ # Lint fix
uv run ty check src/                # Type check (Astral ty)
uv run pytest                       # Run all tests
uv run pytest --cov -q              # Run tests with coverage

# Run a single test file
uv run pytest tests/test_http/test_client.py

# Run a single test function
uv run pytest tests/test_http/test_client.py::test_function_name -v

# Mise shortcuts
mise run setup     # Full dev environment setup
mise run lint      # ruff check + ruff format --check
mise run test      # pytest with coverage
mise run fix       # ruff check --fix --unsafe-fixes + ruff format
```

### Pytest Configuration

- `asyncio_mode = "auto"` -- no `@pytest.mark.asyncio` needed
- Default timeout: 30 seconds per test
- Integration tests excluded by default (`-m 'not integration and not live'`)
- Test files: `test_*.py` mirroring source module structure
- Coverage threshold: 95% (enforced in CI and pyproject.toml)

## Code Style

### Formatting (Ruff)

- **Line length**: 120
- **Quotes**: Double quotes
- **Indent**: 4 spaces (Python), 2 spaces (JSON/YAML/TOML)
- **Line endings**: LF
- **Target**: Python 3.13

### Ruff Rules

`select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]`

- `I` = isort, `UP` = pyupgrade, `B` = bugbear, `SIM` = simplify, `RUF` = Ruff-specific

### Type Checker (ty)

Lenient: `unresolved-import`, `unresolved-attribute` as `"ignore"` (third-party stubs missing).

### Import Ordering (isort via Ruff)

1. Standard library (`import asyncio`, `import logging`, `import socket`)
2. Third-party (`import httpx`, `from langgraph.graph import StateGraph`)
3. Local (`from web_core.http.client import safe_httpx_client`)

Lazy imports inside functions for heavy deps (crawl4ai, patchright) to avoid import-time overhead.

### Type Hints

- Full type hints on all signatures: parameters and return types
- Modern syntax: `str | None`, `list[float]`, `dict[str, object]`
- `from __future__ import annotations` used in all modules
- `py.typed` marker file present

### Naming Conventions

| Element            | Convention       | Example                                     |
|--------------------|------------------|---------------------------------------------|
| Functions/methods  | snake_case       | `is_safe_url`, `normalize_url`              |
| Private            | Leading `_`      | `_check_ip_safe`, `_pinned_getaddrinfo`     |
| Classes            | PascalCase       | `ScrapingAgent`, `StrategyCache`            |
| Constants          | UPPER_SNAKE_CASE | `_DNS_CACHE_TTL`, `_BLOCKED_HOSTNAMES`      |
| Modules            | snake_case       | `client.py`, `runner.py`                    |

### Error Handling

- Custom exception classes per module (`SearchError`, `ScrapingError`)
- try/except with `logger.warning()` for non-fatal failures
- Graceful fallback chains in scraping agent (strategy escalation)
- Retry with exponential backoff on transient HTTP errors

### File Organization

```
src/web_core/
  __init__.py              # Public API re-exports
  py.typed                 # PEP 561 marker
  http/                    # SSRF-safe HTTP client, URL normalization
    client.py              # safe_httpx_client, DNS pinning, IP validation
    url.py                 # normalize_url, strip_tracking_params, is_valid_domain
  search/                  # SearXNG search engine
    client.py              # search() with retry, dedup, domain filtering
    models.py              # SearchResult, SearchError dataclasses
    runner.py              # Cross-process SearXNG singleton manager
  scraper/                 # Multi-strategy scraping agent
    agent.py               # ScrapingAgent (LangGraph state machine)
    base.py                # BaseStrategy ABC, ScrapingResult
    cache.py               # StrategyCache (per-domain performance tracking)
    state.py               # ScrapingState TypedDict, ScrapingError
    strategies/            # Concrete strategy implementations
      api_direct.py        # API endpoint detection
      basic_http.py        # Simple httpx fetch
      captcha.py           # CapSolver-backed captcha bypass
      headless.py          # Crawl4AI headless browser
      tls_spoof.py         # curl_cffi TLS fingerprint spoofing
  browsers/                # Stealth browser abstraction
    protocol.py            # BrowserProvider Protocol
    patchright.py          # Patchright (undetected Playwright) implementation
```

### Documentation

- Module-level docstrings on every file
- Google-style docstrings with `Args:`/`Returns:` sections
- Section separators: `# ---------------------------------------------------------------------------`

### Commits

Conventional Commits: `type(scope): message`. Automated semantic release.

### Pre-commit Hooks

1. gitleaks (secret detection)
2. Ruff lint (`--fix`) + format
3. ty type check
4. pytest (`--timeout=30 -x -q`)
5. trailing-whitespace, merge-conflicts, JSON/YAML/TOML check, end-of-file-fixer
6. Commit message: enforce `feat`/`fix` prefix
