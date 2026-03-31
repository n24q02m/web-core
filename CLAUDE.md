# web-core

Shared web infrastructure package (PUBLIC, PyPI).

## Architecture
- `http/` — SSRF-safe HTTP client, URL normalization
- `search/` — SearXNG client (retry, dedup, filtering) + singleton runner
- `scraper/` — Multi-strategy scraping agent (LangGraph orchestration)
- `browsers/` — Stealth browser provider Protocol

## Commands
- `uv run pytest --cov -q` — run tests
- `uv run ruff check src/ tests/` — lint
- `uv run ruff format src/ tests/` — format

## Conventions
- Python 3.13, async-first
- All HTTP through safe_httpx_client (SSRF protection)
- Tests: pytest-asyncio, asyncio_mode = "auto"
- Coverage >= 95%
