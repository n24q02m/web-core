"""Join sources into the OpenRouter backbone + normalize/blend scores + prefilter.

Backbone = OR ``/api/v1/models``: a model that does not route through
OpenRouter never becomes a candidate (self-hosted embedders/rerankers need a
different backbone — see ``tasks.py`` embedding/rerank profiles and the
package docstring for the auto-promotion policy). Join key priority:
canonical_slug -> id -> hugging_face_id -> slug of display name.

Cost semantics: ``ModelCandidate.cost_1m_blended`` is ``None`` when no OR
pricing can be parsed (unlisted / free / unknown). ``None``-cost candidates
are excluded from the pareto frontier — without a cost signal a model cannot
be a best-value pick (it also cannot be beaten on price, which would make the
frontier meaningless).
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any

from web_core.model_selection.sources import SourceRecord, slugify
from web_core.model_selection.tasks import Constraints, TaskProfile

logger = logging.getLogger(__name__)

# AA scores embedded in OR /api/v1/models rows -> aggregate source names.
# Missing on a row = missing, NOT 0.
_EMBEDDED_AA_SCORES = {
    "intelligence_index": "artificial_analysis",
    "coding_index": "aa_coding_index",
    "agentic_index": "aa_agentic_index",
}

_COST_UNKNOWN = math.inf


@dataclass
class ModelCandidate:
    """An OR-routable model after join + normalize + pareto."""

    or_slug: str
    name: str = ""
    hf_id: str | None = None
    litellm_id: str | None = None
    canonical_slug: str | None = None
    scores: dict[str, float] = field(default_factory=dict)  # per-source, normalized 0-100
    score_cis: dict[str, float] = field(default_factory=dict)
    board_versions: dict[str, str] = field(default_factory=dict)
    quality: float = 0.0  # blended 0-100
    quality_ci: float | None = None
    cost_1m_blended: float | None = None  # USD / 1M tokens per task token_mix; None = unknown cost
    context: int = 0
    modalities: tuple[str, ...] = ()
    supported_parameters: tuple[str, ...] = ()
    uptime_1d: float | None = None
    zdr_available: bool | None = None
    or_task_spend_share: float | None = None
    pareto_rank: int | None = None  # 0..k-1 on the frontier; None = dominated or unknown cost
    evidence: tuple[str, ...] = ()  # boards that contributed a score
    weak_evidence: bool = False  # only OR usage/pricing, no board score
    raw: dict[str, Any] = field(default_factory=dict)


def _alias_index(or_records: dict[str, SourceRecord]) -> dict[str, str]:
    """Alias -> or_slug index: id, canonical_slug, hugging_face_id, slug(name)."""
    index: dict[str, str] = {}
    for slug, rec in or_records.items():
        row = rec.raw
        keys = {slug, slugify(slug)}
        canonical = row.get("canonical_slug")
        if canonical:
            keys.add(canonical)
            keys.add(slugify(canonical))
        hf = row.get("hugging_face_id")
        if hf:
            keys.add(hf)
            keys.add(slugify(hf))
        name = rec.name or row.get("name")
        if name:
            keys.add(slugify(name))
        for k in keys:
            index.setdefault(k, slug)
    return index


def _match_key(rec: SourceRecord, alias_index: dict[str, str]) -> str | None:
    for cand in (rec.key, slugify(rec.key), slugify(rec.name) if rec.name else None):
        if cand and cand in alias_index:
            return alias_index[cand]
    return None


def join_sources(
    or_records: dict[str, SourceRecord],
    source_records: dict[str, dict[str, SourceRecord]],
    *,
    task: TaskProfile | None = None,
) -> list[ModelCandidate]:
    """Join every source into the OR backbone. Unmatched records are dropped.

    ``task`` is required to use the embedded AA fallback: scores are only
    filled for sources listed in the task's ``specialized_sources`` /
    ``aggregate_sources``.
    """
    alias_index = _alias_index(or_records)
    candidates: dict[str, ModelCandidate] = {}
    for slug, rec in or_records.items():
        row = rec.raw
        modality = str(row.get("architecture", {}).get("modality") or "")
        inputs = tuple(m.strip() for m in modality.split("->")[0].split("+") if m.strip())
        candidates[slug] = ModelCandidate(
            or_slug=slug,
            name=rec.name,
            hf_id=row.get("hugging_face_id"),
            litellm_id=f"openrouter/{slug}",
            canonical_slug=row.get("canonical_slug"),
            context=int(row.get("context_length") or 0),
            modalities=inputs,
            supported_parameters=tuple(row.get("supported_parameters") or ()),
            raw=row,
        )

    wanted = set()
    if task is not None:
        wanted = set(task.specialized_sources) | set(task.aggregate_sources)

    for source_name, records in source_records.items():
        if source_name == "openrouter_models":
            continue
        for rec in records.values():
            slug = _match_key(rec, alias_index)
            if slug is None:
                continue
            cand = candidates[slug]
            if rec.score is not None:
                cand.scores[source_name] = rec.score
            if rec.score_ci is not None:
                cand.score_cis[source_name] = rec.score_ci
            if rec.board_version:
                cand.board_versions[source_name] = rec.board_version

    # Embedded AA fallback: OR rows already carry intelligence/coding/agentic
    # indexes; MTEB scores land via the same path once a backbone lists them.
    for cand in candidates.values():
        aa = cand.raw.get("benchmarks", {}).get("artificial_analysis")
        if not isinstance(aa, dict):
            continue
        for field_name, source_name in _EMBEDDED_AA_SCORES.items():
            if wanted and source_name not in wanted:
                continue
            if source_name in cand.scores:
                continue
            val = aa.get(field_name)
            if isinstance(val, (int, float)):
                cand.scores[source_name] = float(val)
    return list(candidates.values())


def version_guard(candidates: list[ModelCandidate]) -> None:
    """Drop scores from stale board versions when one source has many majors.

    AA re-baselines its index between major versions (e.g. v3 -> v4):
    cross-version comparison is wrong. Keep only the newest major version per
    source, drop the rest.
    """
    newest: dict[str, int] = {}
    for cand in candidates:
        for source, ver in cand.board_versions.items():
            m = re.match(r"v?(\d+)", ver)
            if m:
                newest[source] = max(newest.get(source, 0), int(m.group(1)))
    for cand in candidates:
        for source, ver in list(cand.board_versions.items()):
            m = re.match(r"v?(\d+)", ver)
            if m and int(m.group(1)) < newest[source]:
                logger.warning(
                    "model_selection version guard drop: source=%s model=%s version=%s newest=v%d",
                    source,
                    cand.or_slug,
                    ver,
                    newest[source],
                )
                cand.scores.pop(source, None)
                cand.score_cis.pop(source, None)


def minmax_normalize(candidates: list[ModelCandidate]) -> None:
    """Min-max normalize each board to 0-100 IN-PLACE before blending.

    A board with a single value (or all values equal) gives 100.0 to every
    scored model: nothing to differentiate on, let cost decide.
    """
    sources = {s for c in candidates for s in c.scores}
    for source in sources:
        vals = [c.scores[source] for c in candidates if source in c.scores]
        lo, hi = min(vals), max(vals)
        for cand in candidates:
            if source not in cand.scores:
                continue
            cand.scores[source] = 100.0 if hi == lo else (cand.scores[source] - lo) / (hi - lo) * 100.0


def blend_quality(candidates: list[ModelCandidate], task: TaskProfile) -> None:
    """q = w_spec * q_specialized + (1 - w_spec) * q_aggregate.

    w_spec = task.quality_weight when specialized covers >=80% of scored
    candidates, else 0.5. A model with only one layer of scores uses that
    layer (not a 0).
    """
    spec = set(task.specialized_sources)
    agg = set(task.aggregate_sources)
    scored = [c for c in candidates if c.scores]
    covered = sum(1 for c in scored if spec & set(c.scores))
    w_spec = task.quality_weight if scored and covered / len(scored) >= 0.8 else min(task.quality_weight, 0.5)
    for cand in candidates:
        spec_vals = [v for s, v in cand.scores.items() if s in spec]
        agg_vals = [v for s, v in cand.scores.items() if s in agg]
        if spec_vals and agg_vals:
            cand.quality = w_spec * (sum(spec_vals) / len(spec_vals)) + (1 - w_spec) * (sum(agg_vals) / len(agg_vals))
        elif spec_vals:
            cand.quality = sum(spec_vals) / len(spec_vals)
        elif agg_vals:
            cand.quality = sum(agg_vals) / len(agg_vals)
        else:
            cand.quality = 0.0
            cand.weak_evidence = True
        cand.evidence = tuple(sorted(cand.scores))
        cis = [cand.score_cis[s] for s in cand.scores if s in cand.score_cis]
        cand.quality_ci = max(cis) if cis else None


def _tiered_price(pricing: dict[str, Any], expected_prompt_tokens: int) -> dict[str, Any]:
    """Apply OR ``pricing.overrides`` when the expected prompt exceeds ``min_prompt_tokens``."""
    if not expected_prompt_tokens:
        return pricing
    best: dict[str, Any] | None = None
    best_min = -1
    for ov in pricing.get("overrides") or []:
        if not isinstance(ov, dict):
            continue
        sub = ov.get("pricing") if isinstance(ov.get("pricing"), dict) else ov
        try:
            min_tokens = int(ov.get("min_prompt_tokens") or 0)
        except (TypeError, ValueError):
            continue
        if min_tokens > best_min and expected_prompt_tokens >= min_tokens:
            best, best_min = sub, min_tokens
    return best or pricing


def blended_cost_1m(cand: ModelCandidate, task: TaskProfile) -> float | None:
    """c = in_share*p_in + out_share*p_out + cache_share*p_cache_read (USD/1M).

    OR prices are USD/token -> x1e6. Unparseable price (unlisted / free /
    unknown) -> ``None``: unknown-cost candidates are excluded from the pareto
    frontier instead of silently ranking as free or infinitely expensive.
    """
    pricing = cand.raw.get("pricing")
    if not isinstance(pricing, dict):
        return None
    pricing = _tiered_price(pricing, task.expected_prompt_tokens)

    def _price(key: str) -> float | None:
        try:
            return float(pricing[key])
        except (KeyError, TypeError, ValueError):
            return None

    p_in = _price("prompt")
    p_out = _price("completion")
    p_cache = _price("input_cache_read")
    if p_in is None or p_out is None:
        return None
    if p_cache is None:
        p_cache = p_in
    in_share, out_share, cache_share = task.token_mix
    blended = (in_share * p_in + out_share * p_out + cache_share * p_cache) * 1e6
    # OR uses ``-1`` as a sentinel price on internal routes (e.g.
    # ``openrouter/auto``): a negative blended cost is a missing signal, not a
    # bargain — treat it as unknown so it cannot dominate the frontier.
    if blended < 0:
        return None
    return blended


def passes_constraints(cand: ModelCandidate, constraints: Constraints) -> bool:
    """Hard prefilter before pareto. ZDR fail-closed (unknown = drop); uptime
    only filters when data exists (before ``enrich_uptime`` nothing drops)."""
    if cand.context < constraints.min_context:
        return False
    if constraints.required_input_modality and constraints.required_input_modality not in cand.modalities:
        return False
    params = set(cand.supported_parameters)
    if constraints.require_tools and "tools" not in params:
        return False
    if constraints.require_structured_outputs and "structured_outputs" not in params:
        return False
    if constraints.require_zdr and cand.zdr_available is not True:
        return False
    if (
        constraints.min_uptime_1d is not None
        and cand.uptime_1d is not None
        and cand.uptime_1d < constraints.min_uptime_1d
    ):
        return False
    if constraints.max_cost_1m is None:
        return True
    return cand.cost_1m_blended is not None and cand.cost_1m_blended <= constraints.max_cost_1m


def effective_cost(cand: ModelCandidate) -> float:
    """Sort/compare helper: ``None`` (unknown) cost behaves as +inf."""
    return cand.cost_1m_blended if cand.cost_1m_blended is not None else _COST_UNKNOWN
