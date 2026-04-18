# web-core

Shared web infrastructure Python package (PUBLIC, PyPI). Cung cap SearXNG search, multi-strategy scraping, SSRF-safe HTTP client, va stealth browsers cho knowledge-core va cac downstream apps.

## Architecture

```
src/web_core/
  __init__.py              -- Public API re-exports
  py.typed                 -- PEP 561 marker
  http/                    -- Layer 1: SSRF-safe HTTP primitives
    client.py              -- safe_httpx_client(), DNS pinning, IP validation
    url.py                 -- normalize_url(), strip_tracking_params(), is_valid_domain()
  search/                  -- Layer 2: SearXNG search engine
    client.py              -- search() voi retry, dedup, domain filtering
    models.py              -- SearchResult, SearchError
    runner.py              -- Cross-process SearXNG singleton (file-lock, auto-restart)
  scraper/                 -- Layer 2: Multi-strategy scraping agent
    agent.py               -- ScrapingAgent (LangGraph state machine)
    base.py                -- BaseStrategy ABC, ScrapingResult
    cache.py               -- StrategyCache (per-domain performance tracking)
    state.py               -- ScrapingState TypedDict, ScrapingError
    strategies/            -- Concrete implementations
      api_direct.py        -- API endpoint detection
      basic_http.py        -- Simple httpx GET
      captcha.py           -- CapSolver captcha bypass
      headless.py          -- Crawl4AI headless browser
      tls_spoof.py         -- curl_cffi TLS fingerprint spoofing
  browsers/                -- Layer 2: Stealth browser abstraction
    protocol.py            -- BrowserProvider Protocol (structural typing)
    patchright.py          -- Patchright (undetected Playwright) provider
tests/                     -- Mirror cau truc source modules
```

## Build Commands

```bash
# Cai dat dependencies
uv sync --all-extras

# Chay tests
uv run pytest --cov -q
uv run pytest --cov --cov-report=term-missing

# Lint + type check
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/

# Auto-fix
uv run ruff check --fix --unsafe-fixes src/ tests/
uv run ruff format src/ tests/

# Mise shortcuts
mise run setup     # uv sync --all-extras
mise run lint      # ruff check + ruff format --check
mise run test      # pytest --cov -q
mise run fix       # ruff check --fix + ruff format
```

## Cau hinh quan trong

- **Python 3.13 bat buoc** -- `requires-python = ">=3.13,<3.14"`
- Ruff: line-length 120, target py313, rules E/F/W/I/UP/B/SIM/RUF
- ty: lenient (`unresolved-import`, `unresolved-attribute` = "ignore")
- Coverage: >= 95%, branch = true

## Pytest

- `asyncio_mode = "auto"` -- KHONG can `@pytest.mark.asyncio`
- Default timeout: 30 seconds per test
- Integration/live tests excluded by default
- `addopts = "-m 'not integration and not live' --timeout=30"`

## Pre-commit Hooks

1. gitleaks (secret detection -- MUST be first)
2. Ruff lint (`--fix`) + format
3. ty type check
4. pytest (`-x -q --timeout=30`)
5. trailing-whitespace, merge-conflicts, JSON/YAML/TOML check, end-of-file-fixer
6. Commit message: enforce Conventional Commits prefix

## Release & Deploy

- **PyPI**: `web-core` (OIDC Trusted Publishing, `uv publish`)
- Conventional Commits. Tag format: `v{version}`
- CD: workflow_dispatch, chon beta/stable
- Pipeline: PSR v10 -> PyPI (uv publish) -> GitHub Release + Tag
- SAST: **CodeQL** (public repo). KHONG dung Semgrep.
- Consumers: `pip install web-core` hoac `"web-core>=0.1.0"` trong pyproject.toml

## Conventions

- **Pydantic** cho config classes, **dataclass** cho simple data models
- **Async-first**: tat ca I/O operations la async
- **stdlib logging** (KHONG dung structlog -- day la library, khong phai app)
- **TDD**: Viet test truoc, coverage >= 95%
- **Naming**: snake_case cho modules/functions, PascalCase cho classes
- **Imports**: Absolute imports tu `web_core.*`. Lazy imports cho heavy deps (crawl4ai, patchright)
- **SSRF**: TAT CA outbound HTTP PHAI qua `safe_httpx_client()`
- **Error handling**: Custom exception classes per module, KHONG return error strings

## Ngon ngu

| Ngu canh          | Ngon ngu                    |
|-------------------|-----------------------------|
| Code, Variables   | English                     |
| Commits           | English (Conventional Commits) |
| Docs, Comments    | Tieng Viet                  |

## Infisical

- Project: `790b3d1e-188f-4ead-bfcc-da5dca110d50`

## Security

- KHONG BAO GIO commit credentials thuc (API keys, tokens, passwords)
- Luon dung placeholders hoac environment variables
- Secrets quan ly qua Infisical
- TAT CA GitHub Actions pinned to SHA
