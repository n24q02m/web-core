"""Base strategy interface and result type for scraping."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ScrapingResult:
    """Result from a single scraping strategy execution."""

    content: str
    url: str
    strategy: str
    status_code: int
    metadata: dict[str, object] = field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract base class for scraping strategies."""

    name: str = "base"

    @abstractmethod
    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        """Fetch content from a URL using this strategy."""
        ...
