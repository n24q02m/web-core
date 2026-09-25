"""Pareto frontier over (cost up, quality down) + pick strategies.

- ``frontier``: the non-dominated set — i dominates j iff q_i >= q_j (within
  CI) and c_i <= c_j, strictly better in at least one dimension.
- ``knee``: the point with the largest perpendicular distance to the chord
  joining the cheapest and the best-quality point — the default pick.
- ``quadrant``: median-split; Q-attractive = {q >= q_med, c < c_med}, ranked
  by q/c then OR task-spend share.

Cost-unknown candidates (``cost_1m_blended is None``) are excluded from the
frontier and from every strategy: with no cost signal a model can be neither
a best-value pick nor a meaningful price comparison point. They keep
``pareto_rank=None`` and sort to the back of the candidate list.
"""

from __future__ import annotations

import math
from typing import Literal

from web_core.model_selection.normalize import ModelCandidate, effective_cost

Strategy = Literal["knee", "quadrant", "cheapest"]


def _dominates(a: ModelCandidate, b: ModelCandidate) -> bool:
    """a dominates b: cheaper-or-equal, and no worse in quality (within CI).

    CI overlap counts as a quality tie -> the cheaper one dominates
    (within-CI = tie -> prefer cheaper).
    """
    tol = max(a.quality_ci or 0.0, b.quality_ci or 0.0)
    if effective_cost(a) > effective_cost(b):
        return False
    if a.quality < b.quality - tol:
        return False
    return a.quality > b.quality + tol or effective_cost(a) < effective_cost(b)


def frontier(candidates: list[ModelCandidate]) -> list[ModelCandidate]:
    """Non-dominated set among cost-known candidates, sorted by cost ascending."""
    known = [c for c in candidates if c.cost_1m_blended is not None]
    result = [c for c in known if not any(_dominates(other, c) for other in known if other is not c)]
    return sorted(result, key=lambda c: (c.cost_1m_blended, -c.quality))


def assign_pareto_ranks(candidates: list[ModelCandidate]) -> None:
    """Assign ``pareto_rank`` 0..k-1 to frontier members (cost ascending).

    Cost-unknown candidates keep ``pareto_rank=None`` — no cost, no rank-0.
    """
    front = frontier(candidates)
    for rank, cand in enumerate(front):
        cand.pareto_rank = rank


def knee_point(front: list[ModelCandidate]) -> ModelCandidate | None:
    """Max perpendicular distance to the chord (cheapest <-> best quality).

    Frontier < 3 points: 1 point -> itself; 2 points -> the cheaper one (knee
    is undefined, default to thrift).
    """
    if not front:
        return None
    if len(front) <= 2:
        return front[0]
    cheapest = min(front, key=effective_cost)
    best = max(front, key=lambda c: c.quality)
    if cheapest is best:
        return cheapest
    x0, y0 = effective_cost(cheapest), cheapest.quality
    x1, y1 = effective_cost(best), best.quality
    dx, dy = x1 - x0, y1 - y0
    norm = math.hypot(dx, dy)
    if norm == 0:
        return cheapest

    def _dist(c: ModelCandidate) -> float:
        # perpendicular distance from the point to the line through (x0,y0)-(x1,y1)
        return abs(dy * (effective_cost(c) - x0) - dx * (c.quality - y0)) / norm

    return max(front, key=_dist)


def quadrants(candidates: list[ModelCandidate]) -> dict[str, list[ModelCandidate]]:
    """Median-split into 4 quadrants. ``attractive`` = q >= median, c < median."""
    if not candidates:
        return {"attractive": [], "premium": [], "budget": [], "avoid": []}
    qs = sorted(c.quality for c in candidates)
    cs = sorted(effective_cost(c) for c in candidates)
    q_med, c_med = qs[len(qs) // 2], cs[len(cs) // 2]
    out: dict[str, list[ModelCandidate]] = {"attractive": [], "premium": [], "budget": [], "avoid": []}
    for c in candidates:
        cost = effective_cost(c)
        if c.quality >= q_med:
            out["attractive" if cost < c_med else "premium"].append(c)
        else:
            out["budget" if cost < c_med else "avoid"].append(c)
    return out


def _rank_q_over_cost(cands: list[ModelCandidate]) -> list[ModelCandidate]:
    """Rank by q/c, tiebreak on OR task-spend share."""
    return sorted(
        cands,
        key=lambda c: (
            -(c.quality / c.cost_1m_blended if c.cost_1m_blended is not None and c.cost_1m_blended > 0 else math.inf),
            -(c.or_task_spend_share or 0.0),
        ),
    )


def pick(candidates: list[ModelCandidate], strategy: Strategy = "knee") -> ModelCandidate | None:
    """Pick one candidate per strategy. ``None`` when nobody survives prefilter."""
    if not candidates:
        return None
    if strategy == "cheapest":
        known = [c for c in candidates if c.cost_1m_blended is not None]
        if not known:
            return None
        return min(known, key=lambda c: (c.cost_1m_blended, -c.quality))
    front = frontier(candidates)
    if not front:
        return None
    if strategy == "quadrant":
        quads = quadrants(front)
        # attractive within the (median boundary) -> premium (still above
        # median quality) -> whole frontier; rank by q/c then OR spend share.
        pool = quads["attractive"] or quads["premium"] or front
        ranked = _rank_q_over_cost(pool)
        return ranked[0] if ranked else None
    return knee_point(front)
