"""web_core.model_selection — leaderboard-driven model picker, publicly reusable.

Usage::

    from web_core.model_selection import candidates, pick, TASKS

    cands = candidates("healthcare-advice")   # ranked, pareto frontier first
    best = pick("healthcare-advice", strategy="knee")

Pipeline: fetch the OR backbone -> fetch each source (fail-open) -> join by
alias -> version guard -> min-max normalize -> blend quality -> blended cost ->
constraint prefilter -> pareto rank. The module does not run evals — consumers
eval and promote from the ranked candidate list.

OpenRouter auto-promotion constraint (2026-09-25 directive)
-----------------------------------------------------------

Only models listed on the OpenRouter catalog can be auto-promoted (rank-0) by
this module:

- Every candidate is joined into the OR ``/api/v1/models`` backbone; records
  that do not match the catalog are dropped at join time and can never reach
  rank-0.
- Embedding/rerank tasks (``embedding``, ``rerank`` profiles) normally find a
  thin/empty OR backbone, because embedders and rerankers mostly do not route
  through OpenRouter. In that case ``candidates()`` returns ``[]`` and logs
  ``or_backbone_empty`` — it does NOT promote non-OR models. Only a caller
  that passes a ``sources`` override whose ``openrouter_models`` entry
  actually lists (joinable) OR-catalog entries gets a non-empty candidate
  list.
- Cost signal: pricing comes from the OR catalog. Entries without OR pricing
  get ``cost_1m_blended=None`` and are excluded from the pareto frontier —
  no cost means the model cannot be a best-value pick. OR's ``-1`` sentinel
  price (internal routes such as ``openrouter/auto``) counts as no cost
  signal; genuinely free (0-priced) models keep cost ``0.0``.

Ported from knowledge_core.model_selection (kept there during migration);
adapted to web_core conventions: stdlib logging, no structlog, and the
``mteb_*`` fetchers implemented on the public ``mteb/results`` dataset.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from typing import Literal

from web_core.model_selection.cache import FileCache
from web_core.model_selection.normalize import (
    ModelCandidate,
    blend_quality,
    blended_cost_1m,
    join_sources,
    minmax_normalize,
    passes_constraints,
    version_guard,
)
from web_core.model_selection.pareto import assign_pareto_ranks
from web_core.model_selection.pareto import pick as _pick
from web_core.model_selection.sources import (
    SOURCE_REGISTRY,
    Source,
    SourceRecord,
    fetch_endpoint_stats,
)
from web_core.model_selection.tasks import TASKS, Constraints, TaskProfile, get_task

logger = logging.getLogger(__name__)

__all__ = [
    "SOURCE_REGISTRY",
    "TASKS",
    "Constraints",
    "FileCache",
    "ModelCandidate",
    "Source",
    "SourceRecord",
    "TaskProfile",
    "candidates",
    "enrich_uptime",
    "get_task",
    "pick",
]


def _fetch_source(source: Source, cache: FileCache | None, refresh: bool) -> dict[str, SourceRecord]:
    """Fetch one source through the cache; empty/failed fetch -> try stale snapshot."""
    if cache is not None and not refresh:
        cached = cache.get(source.name, source.ttl_seconds)
        if cached is not None:
            return {k: SourceRecord.from_dict(v) for k, v in cached.items()}
    try:
        records = source.fetch()
    except Exception as exc:  # plugin sources that do not inherit _BaseSource
        logger.warning("model_selection source raised: source=%s error=%s", source.name, exc)
        records = {}
    if records:
        if cache is not None:
            cache.set(source.name, {k: r.to_dict() for k, r in records.items()})
        return records
    if cache is not None:
        stale = cache.get(source.name, float("inf"), allow_stale=True)
        if stale:
            logger.info("model_selection using stale cache: source=%s", source.name)
            return {k: SourceRecord.from_dict(v) for k, v in stale.items()}
    return records


def candidates(
    task: TaskProfile | str,
    *,
    refresh: bool = False,
    cache: FileCache | None = None,
    sources: Mapping[str, Source] | None = None,
) -> list[ModelCandidate]:
    """Ranked candidate list for a task, frontier first, dominated after.

    ``sources`` overrides the registry (tests/plugins); defaults to
    ``SOURCE_REGISTRY``. Names in the TaskProfile without an entry in the map
    are skipped fail-open.

    Returns ``[]`` when the OpenRouter backbone is missing or empty
    (``or_backbone_empty`` is logged): without catalog rows there is nothing
    the module is allowed to auto-promote.
    """
    profile = get_task(task)
    registry = sources if sources is not None else SOURCE_REGISTRY
    use_cache = cache if sources is None else None  # fixtures/plugins do not write cache

    or_source = registry.get("openrouter_models")
    if or_source is None:
        logger.warning("model_selection: missing openrouter_models backbone")
        return []
    or_records = _fetch_source(or_source, use_cache, refresh)
    if not or_records:
        logger.warning(
            "model_selection or_backbone_empty: task=%s — no OpenRouter-listed models to "
            "auto-promote; pass a sources override with joinable OR-catalog entries to proceed",
            profile.name,
        )
        return []

    source_records: dict[str, dict[str, SourceRecord]] = {}
    for name in (*profile.specialized_sources, *profile.aggregate_sources):
        source = registry.get(name)
        if source is None:
            continue  # fetcher not written / consumer plugin — fail-open
        source_records[name] = _fetch_source(source, use_cache, refresh)

    cands = join_sources(or_records, source_records, task=profile)
    version_guard(cands)
    minmax_normalize(cands)
    blend_quality(cands, profile)
    for cand in cands:
        cand.cost_1m_blended = blended_cost_1m(cand, profile)
    cands = [c for c in cands if passes_constraints(c, profile.constraints)]
    assign_pareto_ranks(cands)
    # Sentinel inf instead of len(cands): while list.sort() runs, the list is
    # detached and len() returns 0 — dominated members would be pushed to the
    # front. None-cost candidates keep rank None -> also sort to the back.
    cands.sort(key=lambda c: (c.pareto_rank if c.pareto_rank is not None else math.inf, -c.quality))
    return cands


def pick(
    task: TaskProfile | str,
    *,
    strategy: Literal["knee", "quadrant", "cheapest"] = "knee",
    refresh: bool = False,
    cache: FileCache | None = None,
    sources: Mapping[str, Source] | None = None,
) -> ModelCandidate | None:
    """Pick one model per strategy; ``None`` when no candidate survives."""
    return _pick(candidates(task, refresh=refresh, cache=cache, sources=sources), strategy)


def enrich_uptime(cands: list[ModelCandidate], *, limit: int = 20) -> list[ModelCandidate]:
    """Fetch uptime_1d + zdr_available from OR /endpoints for the top-N candidates.

    Call AFTER shortlisting (1 request/model). Constraint ``min_uptime_1d``
    only filters when the field has data; ``require_zdr`` is fail-closed on
    this data.
    """
    for cand in cands[:limit]:
        stats = fetch_endpoint_stats(cand.or_slug)
        if not stats:
            continue
        cand.uptime_1d = stats.get("uptime_1d")
        cand.zdr_available = stats.get("zdr_available")
    return cands
