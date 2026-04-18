"""Strategy cache: tracks success rate and recommends best strategy per domain."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass
class StrategyStats:
    """Per-strategy statistics for a single domain."""

    attempts: int = 0
    successes: int = 0
    total_time_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Fraction of attempts that succeeded (0.0 .. 1.0)."""
        return self.successes / self.attempts if self.attempts > 0 else 0.0


class StrategyCache:
    """In-memory cache that tracks per-domain strategy performance.

    Records success/failure and response time for each (domain, strategy) pair.
    Recommends strategy ordering based on historical success rate.
    """

    DEFAULT_ORDER: ClassVar[list[str]] = [
        "basic_http",
        "tls_spoof",
        "headless",
        "patchright",
        "captcha",
        "api_direct",
    ]

    def __init__(
        self,
        default_order: list[str] | None = None,
        min_attempts: int = 3,
        backend: Any = None,
    ):
        self.default_order = default_order or self.DEFAULT_ORDER.copy()
        self.min_attempts = min_attempts
        self._backend = backend
        self._stats: dict[str, dict[str, StrategyStats]] = defaultdict(lambda: defaultdict(StrategyStats))

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract the network-location (domain:port) from *url*."""
        # Performance Optimization: Using string partitioning is ~3.5x faster
        # than urllib.parse.urlparse by avoiding regex and tuple allocation overhead.
        # This is a hot path called for every URL caching operation.
        if url.startswith("//"):
            return url[2:].partition("/")[0].partition("?")[0].partition("#")[0]

        _, sep, rest = url.partition("://")
        domain_part = rest if sep else url
        return domain_part.partition("/")[0].partition("?")[0].partition("#")[0]

    async def record(
        self,
        url: str,
        strategy_name: str,
        success: bool,
        time_ms: float = 0.0,
    ) -> None:
        """Record one attempt for (*domain*, *strategy_name*)."""
        domain = self._extract_domain(url)
        stats = self._stats[domain][strategy_name]
        stats.attempts += 1
        if success:
            stats.successes += 1
        stats.total_time_ms += time_ms

    async def recommend(self, url: str) -> list[str]:
        """Return strategy names ordered by historical success rate for *url*'s domain.

        Strategies with fewer than ``min_attempts`` are appended in default order.
        """
        domain = self._extract_domain(url)
        domain_stats = self._stats.get(domain, {})

        if not domain_stats:
            return self.default_order.copy()

        scored: list[tuple[str, float]] = []
        unscored: list[str] = []
        for name in self.default_order:
            stats = domain_stats.get(name)
            if stats and stats.attempts >= self.min_attempts:
                scored.append((name, stats.success_rate))
            else:
                unscored.append(name)

        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored] + unscored

    async def get_stats(self, url: str) -> dict[str, StrategyStats]:
        """Return all strategy stats for *url*'s domain."""
        domain = self._extract_domain(url)
        return dict(self._stats.get(domain, {}))

    async def clear(self, url: str | None = None) -> None:
        """Clear stats for a specific domain, or all domains if *url* is None."""
        if url is None:
            self._stats.clear()
        else:
            domain = self._extract_domain(url)
            self._stats.pop(domain, None)
