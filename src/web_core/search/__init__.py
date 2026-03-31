"""SearXNG search client and models."""

from web_core.search.client import search
from web_core.search.models import SearchError, SearchResult

__all__ = ["SearchError", "SearchResult", "search"]
