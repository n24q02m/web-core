"""Search result and error models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single search result."""

    url: str
    title: str
    snippet: str
    source: str = ""


class SearchError(Exception):
    """Raised when a search operation fails after all retries."""

    def __init__(self, query: str, reason: str):
        self.query = query
        self.reason = reason
        super().__init__(f"Search failed for '{query}': {reason}")
