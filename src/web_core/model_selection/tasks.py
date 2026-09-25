"""TaskProfile registry: map an application's task -> preferred sources + constraints.

Source order (per the 22/09 directive): specialized per-task boards FIRST,
aggregate boards SECOND, OpenRouter as the constraint/tiebreak layer. Source
names without a fetcher in ``SOURCE_REGISTRY`` are skipped fail-open — the
registry may point at fetchers a consumer supplies as plugin sources (e.g.
``ugi``, ``eqbench_creative_v3``, ``aa_healthcare_index``).

Ported from knowledge_core.model_selection.tasks. The ``embedding`` and
``rerank`` profiles intentionally have empty ``aggregate_sources``: embedders
and rerankers mostly do not route through OpenRouter, so the backbone is
expected to be thin/empty there (see ``web_core.model_selection`` docs for the
auto-promotion policy).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Constraints:
    """Hard prefilter before pareto."""

    min_context: int = 0  # minimum context_length
    required_input_modality: str | None = None  # e.g. "image" for vision/manga
    require_tools: bool = False  # OR supported_parameters contains "tools"
    require_structured_outputs: bool = False  # OR supported_parameters contains "structured_outputs"
    require_zdr: bool = False  # needs an endpoint tagged zdr (fail-closed: unknown = drop)
    min_uptime_1d: float | None = None  # SLO uptime; None = do not filter
    max_cost_1m: float | None = None  # USD / 1M blended tokens


@dataclass(frozen=True)
class TaskProfile:
    """A task's profile: preferred sources + constraints + measured token mix."""

    name: str
    specialized_sources: tuple[str, ...] = ()  # tried first, higher weight
    aggregate_sources: tuple[str, ...] = ()  # merge/fallback layer
    constraints: Constraints = field(default_factory=Constraints)
    quality_weight: float = 0.7  # w_spec when specialized covers >=80% of candidates; else 0.5
    # Token mix (input, output, cache_read) measured on the app — do NOT hardcode
    # a generic one: KP ingestion is input-heavy, Aiora chat is ~ AA 7:2:1
    # (cache:input:output).
    token_mix: tuple[float, float, float] = (0.2, 0.1, 0.7)
    expected_prompt_tokens: int = 0  # to apply OR pricing.overrides by min_prompt_tokens


# --- Registry ----------------------------------------------------------------

TASKS: dict[str, TaskProfile] = {
    "translation": TaskProfile(
        name="translation",
        specialized_sources=("wmt24pp", "flores_speakleash"),
        aggregate_sources=("arena", "artificial_analysis"),
        constraints=Constraints(min_context=8_192),
        token_mix=(0.7, 0.3, 0.0),  # ingestion input-heavy
    ),
    "story-gen": TaskProfile(
        name="story-gen",
        specialized_sources=("eqbench_creative_v3", "eqbench_longform", "eqbench4"),
        aggregate_sources=("arena", "artificial_analysis"),
        constraints=Constraints(min_context=32_768),
        token_mix=(0.4, 0.6, 0.0),
    ),
    "embedding": TaskProfile(
        name="embedding",
        specialized_sources=("mteb_classification", "mteb_retrieval", "mteb_sts"),
        # Embedders do not route through OpenRouter -> the OR backbone returns
        # thin/empty for now; the profile stays so consumers can supply their
        # own sources + join keys via a ``sources`` override.
        aggregate_sources=(),
        constraints=Constraints(),
    ),
    "rerank": TaskProfile(
        name="rerank",
        specialized_sources=("mteb_reranking",),
        aggregate_sources=(),
        constraints=Constraints(),
    ),
    "manga-text": TaskProfile(
        name="manga-text",
        specialized_sources=("manga109_v2026", "mangavqa"),
        aggregate_sources=("arena", "ocrbench"),
        constraints=Constraints(min_context=16_384, required_input_modality="image"),
        token_mix=(0.6, 0.4, 0.0),
    ),
    "healthcare-advice": TaskProfile(
        name="healthcare-advice",
        specialized_sources=("aa_healthcare_index", "healthbench"),
        aggregate_sources=("artificial_analysis", "medhelm", "medarena", "vals_medscribe"),
        constraints=Constraints(min_context=32_768, min_uptime_1d=99.0),
        token_mix=(0.2, 0.1, 0.7),  # chat ~ AA 7:2:1 cache:input:output
    ),
    "aqi-advice": TaskProfile(
        name="aqi-advice",
        # GAP: no dedicated AQI board -> proxied by healthcare; backlog =
        # in-house eval on synthetic AQI readings.
        specialized_sources=("aa_healthcare_index", "healthbench"),
        aggregate_sources=("arena", "artificial_analysis"),
        constraints=Constraints(min_context=16_384),
    ),
    "classification": TaskProfile(
        name="classification",
        specialized_sources=("mteb_classification", "aiora_triage_eval"),
        aggregate_sources=("artificial_analysis", "arena"),
        constraints=Constraints(require_structured_outputs=True),
        token_mix=(0.8, 0.2, 0.0),
    ),
    "agentic": TaskProfile(
        name="agentic",
        specialized_sources=("tau2_bench_or", "bfcl"),
        aggregate_sources=("artificial_analysis", "gaia"),
        constraints=Constraints(min_context=32_768, require_tools=True, min_uptime_1d=99.0),
        token_mix=(0.5, 0.4, 0.1),
    ),
    "vision": TaskProfile(
        name="vision",
        specialized_sources=("ocrbench",),
        aggregate_sources=("arena", "artificial_analysis"),
        constraints=Constraints(required_input_modality="image"),
    ),
}


def get_task(task: TaskProfile | str) -> TaskProfile:
    """Resolve a TaskProfile from the registry by name; KeyError if unregistered."""
    if isinstance(task, TaskProfile):
        return task
    return TASKS[task]
