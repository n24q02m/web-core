"""Optional persistent strategy cache with success and latency ranking."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, ClassVar

from web_core.http.url import extract_domain


@dataclass
class StrategyStats:
    """Per-strategy statistics for a single domain."""

    attempts: int = 0
    successes: int = 0
    total_time_ms: float = 0.0
    latency_samples_ms: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Fraction of attempts that succeeded (0.0 .. 1.0)."""
        return self.successes / self.attempts if self.attempts > 0 else 0.0

    @property
    def p50_time_ms(self) -> float:
        """Median observed latency, or zero when no sample exists."""
        if not self.latency_samples_ms:
            return 0.0
        values = sorted(self.latency_samples_ms)
        middle = len(values) // 2
        return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


class StrategyCache:
    """Track strategy performance, optionally backed by a mapping-like store."""

    DEFAULT_ORDER: ClassVar[list[str]] = ["basic_http", "tls_spoof", "headless", "patchright", "captcha", "api_direct"]

    def __init__(self, default_order: list[str] | None = None, min_attempts: int = 1, backend: Any = None):
        self.default_order = default_order or self.DEFAULT_ORDER.copy()
        self.min_attempts = min_attempts
        self._backend = backend
        self._stats: dict[str, dict[str, StrategyStats]] = defaultdict(lambda: defaultdict(StrategyStats))

    def _load_domain(self, domain: str) -> dict[str, StrategyStats]:
        if domain in self._stats or self._backend is None:
            return self._stats[domain]
        stored = self._backend.get(f"strategy-cache:{domain}")
        if stored:
            self._stats[domain] = defaultdict(
                StrategyStats, {name: StrategyStats(**values) for name, values in stored.items()}
            )
        return self._stats[domain]

    def _persist_domain(self, domain: str) -> None:
        if self._backend is None:
            return
        payload = {
            name: {
                "attempts": stats.attempts,
                "successes": stats.successes,
                "total_time_ms": stats.total_time_ms,
                "latency_samples_ms": stats.latency_samples_ms,
            }
            for name, stats in self._stats[domain].items()
        }
        key = f"strategy-cache:{domain}"
        if hasattr(self._backend, "set"):
            self._backend.set(key, payload)
        else:
            self._backend[key] = payload

    async def record(self, url: str, strategy_name: str, success: bool, time_ms: float = 0.0) -> None:
        """Record one attempt and persist it when a backend is configured."""
        domain = extract_domain(url)
        stats = self._load_domain(domain)[strategy_name]
        stats.attempts += 1
        stats.successes += int(success)
        stats.total_time_ms += time_ms
        stats.latency_samples_ms.append(time_ms)
        self._persist_domain(domain)

    async def recommend(self, url: str) -> list[str]:
        """Rank strategies by ``success_rate / (1 + p50_seconds / 10)``."""
        domain_stats = self._load_domain(extract_domain(url))
        if not domain_stats:
            return self.default_order.copy()
        scored: list[tuple[str, float]] = []
        unscored: list[str] = []
        for name in self.default_order:
            stats = domain_stats.get(name)
            if stats and stats.attempts >= self.min_attempts:
                scored.append((name, stats.success_rate / (1 + stats.p50_time_ms / 10000)))
            else:
                unscored.append(name)
        scored.sort(key=lambda item: item[1], reverse=True)
        return [name for name, _ in scored] + unscored

    async def get_stats(self, url: str) -> dict[str, StrategyStats]:
        """Return all strategy stats for *url*'s domain."""
        return dict(self._load_domain(extract_domain(url)))

    async def clear(self, url: str | None = None) -> None:
        """Clear stats for a domain, or all cache-owned domains."""
        if url is None:
            self._stats.clear()
            if self._backend is not None:
                for key in list(self._backend):
                    if isinstance(key, str) and key.startswith("strategy-cache:"):
                        self._backend.pop(key, None)
            return
        domain = extract_domain(url)
        self._stats.pop(domain, None)
        if self._backend is not None:
            self._backend.pop(f"strategy-cache:{domain}", None)
