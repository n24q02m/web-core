# web-core

**Shared web infrastructure for search, scraping, HTTP security, and stealth browsers -- powers wet-mcp and downstream apps.**

<!-- BEGIN: AUTO-GENERATED-CROSS-PROMO -->
<details>
  <summary><strong>Sister projects from n24q02m</strong> (click to expand)</summary>

| Project | Tagline | Tag |
|---|---|---|
| [agent-chat-plugin](https://github.com/n24q02m/agent-chat-plugin) | Peer AI agents chat in a shared folder — no human relay, no orchestrator, wor... | Tooling |
| [better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) | Knowledge graph for token-efficient code reviews -- semantic search and call-... | MCP |
| [better-drive](https://github.com/n24q02m/better-drive) | 2-way Google Drive sync with .driveignore filter — rclone engine, Windows tray | Tooling |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | IMAP/SMTP email for AI agents -- read, send, organize folders, and manage att... | MCP |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Composite MCP server for Godot Engine -- 17 composite tools for AI-assisted g... | MCP |
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Markdown-first Notion for AI agents -- pages, databases, blocks, and comments... | MCP |
| [better-semantic-release](https://github.com/n24q02m/better-semantic-release) | Drop-in python-semantic-release fork with built-in release-safety guards (orp... | Tooling |
| [better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) | Telegram for AI agents -- messages, chats, media, and contacts across both bo... | MCP |
| [better-workspace-mcp](https://github.com/n24q02m/better-workspace-mcp) | Google Workspace MCP server (Docs/Drive/Calendar/Gmail/Sheets/Slides/Tasks/Ch... | MCP |
| [claude-plugins](https://github.com/n24q02m/claude-plugins) | Claude Code plugin marketplace for the n24q02m MCP servers -- install web sea... | Marketplace |
| [imagine-mcp](https://github.com/n24q02m/imagine-mcp) | Image and video understanding + generation for AI agents -- across Gemini, Op... | MCP |
| [jules-task-archiver](https://github.com/n24q02m/jules-task-archiver) | Chrome Extension for bulk operations on Jules tasks via batchexecute API -- a... | Tooling |
| [mcp-core](https://github.com/n24q02m/mcp-core) | Shared foundation for building MCP servers -- Streamable HTTP transport, OAut... | MCP |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search and embedded sync. Open, free, unlimi... | MCP |
| [qwen3-embed](https://github.com/n24q02m/qwen3-embed) | Lightweight Qwen3 text embedding and reranking via ONNX Runtime and GGUF | Library |
| [skret](https://github.com/n24q02m/skret) | Secrets without the server. | CLI |
| [tacet](https://github.com/n24q02m/tacet) | A self-distilling neuro-symbolic cascade that amortises LLM cost across knowl... | Tooling |
| [web-core](https://github.com/n24q02m/web-core) | Shared web infrastructure package for search, scraping, HTTP security, and st... | Library |
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Open-source MCP server for AI agents: web search, content extraction, and lib... | MCP |

</details>
<!-- END: AUTO-GENERATED-CROSS-PROMO -->

## Table of contents

- [Installation](#installation)
- [Quick Usage](#quick-usage)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Development](#development)
- [License](#license)

Shared web infrastructure package providing:

- **SearXNG search** -- cross-process singleton runner plus a retry/dedup/domain-filtering client.
- **Multi-strategy scraping** -- a LangGraph agent that escalates across API-direct, basic HTTP, TLS-fingerprint spoofing, headless rendering, remote rendering, and CAPTCHA-solving strategies.
- **SSRF-safe HTTP client** -- DNS-pinned `httpx` client plus URL normalization and domain validation helpers.
- **Stealth + remote browsers** -- a Patchright (undetected Playwright) provider, plus remote render clients (Cloudflare Browser Rendering, self-host browserless) for slim containers that offload JS rendering.
- **robots.txt compliance** -- per-domain cached `robots.txt` checks before fetching.
- **LLM selector inference** -- optional, env-key-gated CSS-selector inference when built-in selectors fail.
- **External API adapters** -- typed, SSRF-safe clients for Google Drive and MangaDex.

Used by [wet-mcp](https://github.com/n24q02m/wet-mcp) and downstream applications.

**Site-specific selectors live in consumer applications.** This package provides generic infrastructure only. Consumers supply per-domain cookies and selectors via the environment variables in the [Configuration](#configuration) section.

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

# Initialize the agent with the strategies you want, in escalation order.
# All scraping dependencies (crawl4ai, patchright, curl-cffi, capsolver)
# ship as core dependencies, so every built-in strategy is importable.
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

## Configuration

All configuration is read from environment variables. Every variable is optional;
omitting one disables the feature it controls (no variable is required to import or
use the package).

### Search

| Variable | Used by | Purpose |
|---|---|---|
| `SEARXNG_URL` | `search.runner` | Use an already-running SearXNG instance instead of starting a managed one. |
| `SEARXNG_USER` | `search.runner` | User the managed SearXNG container runs as (default `nobody`). |

### Scraping

| Variable | Used by | Purpose |
|---|---|---|
| `WEB_CORE_DOMAIN_COOKIES` | `scraper.selector_inference` | JSON object `{"domain": {"cookie": "value"}}` of per-domain cookies (e.g. age-gate tokens). Keeps secrets out of source. |

### LLM selector inference (optional)

When built-in selectors fail to extract content, the scraper can ask an LLM to infer
CSS selectors. A provider is auto-detected from whichever key is present; if none is
set, inference is skipped silently. Consumers may also inject a custom `llm_caller`.

| Variable | Provider |
|---|---|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google Gemini |
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `XAI_API_KEY` | xAI |
| `WEB_CORE_LLM_MODEL` | Override the per-provider default model. |
| `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` | Route Gemini through Vertex AI instead of the public API. |

### Remote render backends (optional)

Credentials are passed as constructor arguments to the render clients; consumers
typically source them from their own config/env:

- `CFBrowserRenderingClient(account_id, api_token)` -- Cloudflare Browser Rendering.
- `BrowserlessClient(base_url, token=...)` -- a self-hosted browserless `/content` endpoint.

## Architecture

```
src/web_core/
  __init__.py              -- Public API re-exports
  py.typed                 -- PEP 561 type stub marker
  http/                    -- Layer 1: SSRF-safe HTTP primitives
    client.py              -- safe_httpx_client, DNS pinning, IP validation, browser SSRF setup
    url.py                 -- normalize_url, strip_tracking_params, is_valid_domain, extract_domain
  search/                  -- Layer 2: SearXNG search engine
    client.py              -- search() with retry, dedup, domain filtering
    models.py              -- SearchResult, SearchError dataclasses
    runner.py              -- Cross-process SearXNG singleton manager
  scraper/                 -- Layer 2: Multi-strategy scraping agent
    agent.py               -- ScrapingAgent (LangGraph state machine)
    base.py                -- BaseStrategy ABC, ScrapingResult
    cache.py               -- StrategyCache (per-domain performance tracking)
    robots.py              -- RobotsCache (per-domain robots.txt compliance)
    selector_inference.py  -- LLM-based CSS selector inference + domain cookie loading
    state.py               -- ScrapingState TypedDict, ScrapingError
    utils.py               -- Shared scraping helpers
    strategies/            -- Concrete strategy implementations
      api_direct.py        -- API endpoint detection and direct fetch
      basic_http.py        -- Simple httpx GET with SSRF protection
      captcha.py           -- CapSolver-backed captcha bypass
      headless.py          -- Crawl4AI headless browser rendering
      patchright_browser.py -- Patchright stealth-browser rendering
      remote_render.py     -- RemoteRenderStrategy over a RenderClient (CF / browserless)
      tls_spoof.py         -- curl_cffi TLS fingerprint spoofing
  browsers/                -- Layer 2: Browser + remote render clients
    protocol.py            -- BrowserProvider Protocol (structural typing)
    patchright.py          -- Patchright (undetected Playwright) provider
    browserless.py         -- BrowserlessClient (self-host /content render client)
    cf_rendering.py        -- CFBrowserRenderingClient (Cloudflare Browser Rendering)
  adapters/                -- Layer 2: External API adapters (typed, SSRF-safe)
    google_drive.py        -- Google Drive folder/file fetch
    mangadex.py            -- MangaDex client (manga, chapters, images)
```

### Key Design Decisions

- **SSRF protection**: All outbound HTTP goes through `safe_httpx_client` with DNS pinning to prevent DNS rebinding attacks.
- **Strategy escalation**: The scraping agent tries strategies in cache-recommended order, validates responses, and automatically escalates on failure (including past under-rendered JS shells to a render backend).
- **Cross-process SearXNG**: A file-lock singleton ensures exactly one SearXNG instance runs across all Python processes.
- **Structural typing**: `BrowserProvider` and `RenderClient` use `Protocol` so implementations don't need inheritance.

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
