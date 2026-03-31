"""SearXNG search client, models, and runner."""

from web_core.search.client import search
from web_core.search.models import SearchError, SearchResult
from web_core.search.runner import ensure_searxng, shutdown_searxng

__all__ = ["SearchError", "SearchResult", "ensure_searxng", "search", "shutdown_searxng"]
