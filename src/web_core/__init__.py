"""web-core: Shared web infrastructure for search, scraping, HTTP security, and browsers."""

from web_core.browsers import BrowserProvider
from web_core.http import is_safe_url, is_valid_domain, normalize_url, safe_httpx_client, strip_tracking_params
from web_core.scraper import ScrapingAgent, StrategyCache, StrategyRegistry
from web_core.search import SearchResult, ensure_searxng, shutdown_searxng

__all__ = [
    "BrowserProvider",
    "ScrapingAgent",
    "SearchResult",
    "StrategyCache",
    "StrategyRegistry",
    "ensure_searxng",
    "is_safe_url",
    "is_valid_domain",
    "normalize_url",
    "safe_httpx_client",
    "shutdown_searxng",
    "strip_tracking_params",
]
