"""Pareto frontier + pick strategy tests — fixture-based, no network.

Ported from knowledge_core tests, plus cost-unknown semantics: candidates
with ``cost_1m_blended=None`` are excluded from the frontier and every pick
strategy (no cost -> no best-value rank).
"""

from __future__ import annotations

import pytest

from web_core.model_selection.normalize import ModelCandidate
from web_core.model_selection.pareto import frontier, knee_point, quadrants
from web_core.model_selection.pareto import pick as pareto_pick


def _cand(slug: str, q: float, cost: float | None, ci: float | None = None) -> ModelCandidate:
    return ModelCandidate(or_slug=slug, quality=q, cost_1m_blended=cost, quality_ci=ci)


def test_frontier_drops_dominated():
    """A model both worse and pricier is dominated and leaves the frontier."""
    good_cheap = _cand("a", q=90, cost=1.0)
    bad_expensive = _cand("b", q=80, cost=2.0)  # dominated by a
    good_expensive = _cand("c", q=95, cost=3.0)  # on frontier (highest quality)
    cheap_bad = _cand("d", q=50, cost=0.5)  # on frontier (cheapest)

    front = frontier([good_cheap, bad_expensive, good_expensive, cheap_bad])
    slugs = [c.or_slug for c in front]
    assert "b" not in slugs
    assert slugs == ["d", "a", "c"]  # cost ascending


def test_frontier_ci_tie_prefers_cheaper():
    """Two models within each other's CI -> the cheaper dominates the pricier."""
    cheap = _cand("cheap", q=90, cost=1.0, ci=5.0)
    pricey = _cand("pricey", q=92, cost=3.0, ci=5.0)  # |92-90| <= CI 5
    front = frontier([cheap, pricey])
    assert [c.or_slug for c in front] == ["cheap"]


def test_frontier_excludes_unknown_cost():
    """cost=None candidates never enter the frontier (no cost = no best-value)."""
    known = _cand("known", q=80, cost=1.0)
    unknown = _cand("unknown", q=99, cost=None)
    front = frontier([known, unknown])
    assert [c.or_slug for c in front] == ["known"]


def test_frontier_all_unknown_cost_is_empty():
    assert frontier([_cand("a", q=90, cost=None), _cand("b", q=50, cost=None)]) == []


def test_knee_picks_max_distance_point():
    """Knee = the most bent frontier point (max perpendicular distance to chord)."""
    # Chord joins (cost=1,q=50) and (cost=10,q=100); point (cost=2,q=95) is clearly bent.
    cands = [
        _cand("cheap-bad", q=50, cost=1.0),
        _cand("knee", q=95, cost=2.0),
        _cand("best-pricey", q=100, cost=10.0),
    ]
    front = frontier(cands)
    knee = knee_point(front)
    assert knee is not None and knee.or_slug == "knee"


def test_knee_two_points_picks_cheaper():
    front = frontier([_cand("cheap", q=80, cost=1.0), _cand("best", q=95, cost=5.0)])
    knee = knee_point(front)
    assert knee is not None and knee.or_slug == "cheap"


def test_knee_empty_and_degenerate():
    assert knee_point([]) is None
    only = frontier([_cand("a", q=90, cost=2.0)])
    assert knee_point(only) is not None and knee_point(only).or_slug == "a"
    # identical points: chord norm 0 -> cheapest returned
    same = frontier([_cand("a", q=90, cost=2.0), _cand("b", q=90, cost=2.0)])
    assert knee_point(same).or_slug == "a"


def test_quadrant_median_split():
    """Median-split: attractive = q >= median & c < median."""
    cands = [
        _cand("attractive", q=90, cost=1.0),
        _cand("premium", q=99, cost=9.0),
        _cand("budget", q=40, cost=0.5),
        _cand("avoid", q=30, cost=8.0),
    ]
    quads = quadrants(cands)
    assert [c.or_slug for c in quads["attractive"]] == ["attractive"]
    assert [c.or_slug for c in quads["premium"]] == ["premium"]
    assert [c.or_slug for c in quads["budget"]] == ["budget"]
    assert [c.or_slug for c in quads["avoid"]] == ["avoid"]


def test_quadrant_median_split_ignores_unknown_cost():
    """Unknown-cost candidates bucket with the expensive side (inf sentinel)."""
    cands = [
        _cand("attractive", q=90, cost=1.0),
        _cand("premium", q=99, cost=9.0),
        _cand("budget", q=40, cost=0.5),
        _cand("avoid", q=30, cost=8.0),
        _cand("mystery", q=80, cost=None),
    ]
    quads = quadrants(cands)
    names = {q_.or_slug for key in quads for q_ in quads[key]}
    assert names == {"attractive", "premium", "budget", "avoid", "mystery"}
    # inf sentinel: the unknown-cost model cannot land in the cheap half
    assert quads["attractive"][0].or_slug == "attractive"
    assert all(q_.or_slug != "mystery" for q_ in quads["attractive"] + quads["budget"])


def test_quadrant_pick_prefers_high_q_over_cost():
    """pick(quadrant) chooses the frontier member with the best q/c in attractive."""
    cands = [
        _cand("cheap", q=60, cost=0.5),
        _cand("sweet", q=90, cost=1.0),
        _cand("pricey", q=95, cost=8.0),
    ]
    picked = pareto_pick(cands, "quadrant")
    assert picked is not None and picked.or_slug == "sweet"


def test_quadrant_pick_falls_through_to_frontier():
    """Attractive+premium empty -> whole frontier pool, free model first."""
    cands = [_cand("free", q=70, cost=0.0), _cand("cheap", q=60, cost=0.5)]
    picked = pareto_pick(cands, "quadrant")
    assert picked is not None and picked.or_slug == "free"


def test_pick_cheapest_skips_unknown_cost():
    cands = [_cand("unknown", q=99, cost=None), _cand("cheap", q=60, cost=0.5)]
    picked = pareto_pick(cands, "cheapest")
    assert picked is not None and picked.or_slug == "cheap"


def test_pick_cheapest_all_unknown_cost_returns_none():
    assert pareto_pick([_cand("a", q=99, cost=None)], "cheapest") is None


@pytest.mark.parametrize(
    ("strategy", "want"),
    [("knee", "known"), ("quadrant", "known"), ("cheapest", "known")],
)
def test_pick_never_returns_unknown_cost(strategy, want):
    """Rank-0-style strategies cannot promote a cost-unknown model."""
    cands = [_cand("unknown", q=99, cost=None), _cand(want, q=60, cost=1.0)]
    picked = pareto_pick(cands, strategy)  # type: ignore[arg-type]
    assert picked is not None and picked.or_slug == want


def test_pick_empty_candidates_returns_none():
    assert pareto_pick([], "knee") is None
