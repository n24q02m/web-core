# web-core

**Shared web infrastructure for search, scraping, HTTP security, and stealth browsers -- powers wet-mcp and downstream apps.**

<!-- BEGIN: AUTO-GENERATED-CROSS-PROMO -->
<details>
  <summary><strong>Sister projects from n24q02m</strong> (click to expand)</summary>

| Project | Tagline | Tag |
|---|---|---|
| [better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) | Knowledge graph for token-efficient code reviews -- fixed search, configurabl... | MCP |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | IMAP/SMTP email server for AI agents -- 6 composite tools with multi-account ... | MCP |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Composite MCP server for Godot Engine -- 17 mega-tools for AI-assisted game d... | MCP |
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Markdown-first Notion API server for AI agents -- 10 composite tools replacin... | MCP |
| [better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) | MCP server for Telegram with dual-mode support: Bot API (httpx) for quick bot... | MCP |
| [claude-plugins](https://github.com/n24q02m/claude-plugins) | Full documentation: mcp.n24q02m.com — unified docs for all 8 servers + the mc... | Marketplace |
| [imagine-mcp](https://github.com/n24q02m/imagine-mcp) | Production-grade MCP server for image and video understanding + generation ac... | MCP |
| [jules-task-archiver](https://github.com/n24q02m/jules-task-archiver) | Chrome Extension for bulk operations on Jules tasks via batchexecute API -- a... | Tooling |
| [mcp-core](https://github.com/n24q02m/mcp-core) | Unified MCP Streamable HTTP 2025-11-25 transport, OAuth 2.1 Authorization Ser... | MCP |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search and embedded sync. Open, free, unlimi... | MCP |
| [qwen3-embed](https://github.com/n24q02m/qwen3-embed) | Lightweight Qwen3 text embedding and reranking via ONNX Runtime and GGUF | Library |
| [skret](https://github.com/n24q02m/skret) | Secrets without the server. | CLI |
| [web-core](https://github.com/n24q02m/web-core) | Shared web infrastructure package for search, scraping, HTTP security, and st... | Library |
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Open-source MCP Server for web search, content extraction, library docs & mul... | MCP |

</details>
<!-- END: AUTO-GENERATED-CROSS-PROMO -->

## Table of contents

- [Installation](#installation)
- [Quick Usage](#quick-usage)
- [Architecture](#architecture)
- [Development](#development)
- [License](#license)



Shared web infrastructure package: SearXNG search, multi-strategy scraping (basic, TLS spoof, Patchright stealth, Cloudflare CAPTCHA), SSRF-safe HTTP client, and stealth browser primitives. Used by [wet-mcp](https://github.com/n24q02m/wet-mcp) and downstream applications.

**Site-specific selectors moved to consumer applications.** This package provides generic infrastructure only. Consumers bring their own per-domain selectors via the `WEB_CORE_DOMAIN_COOKIES` env-var pattern documented below.

## Installation

```bash
# From PyPI
uv add n24q02m-web-core

# Or pin to v2.x (current stable line)
uv add "n24q02m-web-core>=2.0.0"
```

## Quick Usage

### SearXNG Search

```python
from web_core.search import ensure_searxng, shutdown_searxng
from web_core.search.client import search

# Start/reuse a SearXNG instance (cross-process singleton)
url = await ensure_searxng()

# Search with retry, deduplication, and domain filtering
results = await search(
    searxng_url=url,
    query="Python async patterns",
    max_results=10,
    include_domains=["docs.python.org"],
)

for r in results:
    print(f"{r.title}: {r.url}")

# Clean shutdown
await shutdown_searxng()
```

### Multi-Strategy Scraping

```python
from web_core.scraper import ScrapingAgent
from web_core.scraper.strategies import BasicHTTPStrategy, TLSSpoofStrategy

# Initialize agent with desired strategies
# Note: Some strategies (e.g., HeadlessStrategy, PatchrightStrategy)
# require optional dependencies like crawl4ai or patchright.
agent = ScrapingAgent(strategies={
    "basic": BasicHTTPStrategy(),
    "tls": TLSSpoofStrategy(),
})

# Scrape with automatic strategy escalation
content = await agent.scrape("https://example.com/article")
```

### SSRF-Safe HTTP Client

```python
from web_core.http import safe_httpx_client, is_safe_url

# Validate URL before use
assert is_safe_url("https://example.com")  # True
assert not is_safe_url("http://localhost")  # False (SSRF blocked)

# Create client with automatic SSRF protection + DNS pinning
async with safe_httpx_client() as client:
    resp = await client.get("https://example.com")
```

### URL Utilities

```python
from web_core.http import normalize_url, strip_tracking_params, is_valid_domain

# Normalize for deduplication (lowercase, strip www/tracking/fragment)
normalize_url("https://WWW.Example.COM/page?utm_source=x#section")
# => "https://example.com/page"

# Validate domain names (prevents search operator injection)
is_valid_domain("example.com")   # True
is_valid_domain("localhost")     # False
```

## Architecture

```
src/web_core/
  __init__.py              -- Public API re-exports
  py.typed                 -- PEP 561 type stub marker
  http/                    -- Layer 1: SSRF-safe HTTP primitives
    client.py              -- safe_httpx_client, DNS pinning, IP validation
    url.py                 -- normalize_url, strip_tracking_params, is_valid_domain
  search/                  -- Layer 2: SearXNG search engine
    client.py              -- search() with retry, dedup, domain filtering
    models.py              -- SearchResult, SearchError dataclasses
    runner.py              -- Cross-process SearXNG singleton manager
  scraper/                 -- Layer 2: Multi-strategy scraping agent
    agent.py               -- ScrapingAgent (LangGraph state machine)
    base.py                -- BaseStrategy ABC, ScrapingResult
    cache.py               -- StrategyCache (per-domain performance tracking)
    state.py               -- ScrapingState TypedDict, ScrapingError
    strategies/            -- Concrete strategy implementations
      api_direct.py        -- API endpoint detection and direct fetch
      basic_http.py        -- Simple httpx GET with SSRF protection
      captcha.py           -- CapSolver-backed captcha bypass
      headless.py          -- Crawl4AI headless browser rendering
      tls_spoof.py         -- curl_cffi TLS fingerprint spoofing
  browsers/                -- Layer 2: Stealth browser abstraction
    protocol.py            -- BrowserProvider Protocol (structural typing)
    patchright.py          -- Patchright (undetected Playwright) provider
```

### Key Design Decisions

- **SSRF protection**: All outbound HTTP goes through `safe_httpx_client` with DNS pinning to prevent DNS rebinding attacks.
- **Strategy escalation**: The scraping agent tries strategies in cache-recommended order, validates responses, and automatically escalates on failure.
- **Cross-process SearXNG**: A file-lock singleton ensures exactly one SearXNG instance runs across all Python processes.
- **Structural typing**: `BrowserProvider` uses `Protocol` so implementations don't need inheritance.

## Development

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- [mise](https://mise.jdx.dev/) (optional, for task shortcuts)

### Setup

```bash
git clone git@github.com:n24q02m/web-core.git
cd web-core
uv sync --all-extras
pre-commit install
```

### Commands

```bash
# Via mise
mise run setup     # uv sync --all-extras
mise run lint      # ruff check + ruff format --check
mise run test      # pytest with coverage
mise run fix       # auto-fix lint + format

# Direct
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
uv run pytest --cov -q
```

### Tests

- `asyncio_mode = "auto"` -- no `@pytest.mark.asyncio` needed
- Coverage threshold: 95% (enforced in pyproject.toml)
- Test files mirror source module structure under `tests/`

## License

[MIT](LICENSE)
