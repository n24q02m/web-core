"""Leaderboard data sources for model selection.

Each Source returns ``dict[join_key -> SourceRecord]``. Every fetcher is
FAIL-OPEN: network/parse/auth errors -> ``{}`` (warning logged), never raised
— a dead board only weakens the signal, it never crashes the pipeline.

Join key priority: OR ``canonical_slug`` -> OR ``id`` -> ``hugging_face_id`` ->
slug of display name (see ``normalize._alias_index``).

MTEB fetchers (``mteb_classification``, ``mteb_retrieval``, ``mteb_sts``,
``mteb_reranking``) aggregate the public CC0 ``mteb/results`` HF dataset (the
``mteb/leaderboard`` dataset is gated and NOT accessible without
credentials). The dataset ships as parquet shards (~300 MB total), read via
the optional ``pyarrow`` dependency (install extra ``web-core[mteb]``);
without a parquet reader the fetchers degrade to ``{}`` like every other
fail-open source. Scores are the mean over tasks of per-task mean scores on
the dataset's ``test`` split, keyed by the raw ``model_name`` (an HF repo id,
which joins into the OR backbone through the alias index).
"""

from __future__ import annotations

import csv
import io
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx

from web_core.model_selection.mteb_tasks import task_family

logger = logging.getLogger(__name__)

OR_MODELS_URL = "https://openrouter.ai/api/v1/models"
OR_ENDPOINTS_URL = "https://openrouter.ai/api/v1/models/{slug}/endpoints"
AA_MODELS_URL = "https://artificialanalysis.ai/api/v2/language/models"
LIVEBENCH_CSV_URL = "https://raw.githubusercontent.com/live-bench/LiveBench/main/livebench/data/stats.csv"
UGI_CSV_URL = "https://huggingface.co/datasets/DontPlanToEnd/UGI-Leaderboard/resolve/main/UGI_Leaderboard.csv"
ARENA_PARQUET_URL = "https://huggingface.co/spaces/lmarena-ai/arena-leaderboard/resolve/main/leaderboard_table.parquet"

MTEB_PARQUET_LIST_URL = "https://datasets-server.huggingface.co/parquet?dataset=mteb%2Fresults"

DEFAULT_TIMEOUT = 30.0
DAY = 24 * 3600
WEEK = 7 * DAY

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Normalize a model name to a slug: lowercase, keep [a-z0-9], '-' for other runs."""
    return _SLUG_RE.sub("-", text.lower()).strip("-")


@dataclass
class SourceRecord:
    """One score row from a leaderboard, before joining into the OR backbone."""

    key: str  # best join key the source has: slug / hf_id / raw name
    name: str = ""  # display name on the board
    score: float | None = None  # raw board score (not normalized)
    score_ci: float | None = None  # confidence interval +- when published
    board_version: str | None = None  # e.g. "v4.2" for AA index — drives version guard
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "score": self.score,
            "score_ci": self.score_ci,
            "board_version": self.board_version,
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceRecord:
        return cls(
            key=d["key"],
            name=d.get("name", ""),
            score=d.get("score"),
            score_ci=d.get("score_ci"),
            board_version=d.get("board_version"),
            raw=d.get("raw") or {},
        )


@runtime_checkable
class Source(Protocol):
    """Protocol for every leaderboard fetcher (including consumer-side plugins)."""

    name: str
    ttl_seconds: int

    def fetch(self) -> dict[str, SourceRecord]:
        """Returns {} on error — fail-open, never raises."""
        ...


def _get_json(url: str, *, headers: dict[str, str] | None = None, params: dict[str, str] | None = None) -> Any:
    resp = httpx.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()


def _get_bytes(url: str, *, headers: dict[str, str] | None = None) -> bytes:
    resp = httpx.get(url, headers=headers, timeout=DEFAULT_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_col(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    """Find a column by candidate names (case-insensitive)."""
    lowered = {f.lower().strip(): f for f in fieldnames}
    for cand in candidates:
        if cand in lowered:
            return lowered[cand]
    # fallback: column containing the substring
    for cand in candidates:
        for low, orig in lowered.items():
            if cand in low:
                return orig
    return None


def _parse_csv_records(
    text: str,
    *,
    name_cols: tuple[str, ...],
    score_cols: tuple[str, ...],
    ci_cols: tuple[str, ...] = (),
) -> dict[str, SourceRecord]:
    """Parse a defensive CSV leaderboard: auto-detect name + score columns."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {}
    name_col = _first_col(list(reader.fieldnames), name_cols)
    score_col = _first_col(list(reader.fieldnames), score_cols)
    ci_col = _first_col(list(reader.fieldnames), ci_cols) if ci_cols else None
    if not name_col or not score_col:
        logger.warning("model_selection csv: cannot detect columns: name_col=%s score_col=%s", name_col, score_col)
        return {}
    records: dict[str, SourceRecord] = {}
    for row in reader:
        name = (row.get(name_col) or "").strip()
        score = _float(row.get(score_col))
        if not name or score is None:
            continue
        rec = SourceRecord(
            key=slugify(name),
            name=name,
            score=score,
            score_ci=_float(row.get(ci_col)) if ci_col else None,
            raw=dict(row),
        )
        records[rec.key] = rec
    return records


class _BaseSource:
    """Fail-open boilerplate: ``fetch`` wraps ``_fetch``, any exception -> {}."""

    name: str = "base"
    ttl_seconds: int = DAY

    def fetch(self) -> dict[str, SourceRecord]:
        try:
            return self._fetch()
        except Exception as exc:
            logger.warning("model_selection source failed: source=%s error=%s", self.name, exc)
            return {}

    def _fetch(self) -> dict[str, SourceRecord]:
        raise NotImplementedError


class OpenRouterModelsSource(_BaseSource):
    """Mandatory backbone: GET /api/v1/models (no auth).

    Each record keeps the raw JSON row in ``raw`` — pricing (USD/token,
    including tiered ``overrides`` by ``min_prompt_tokens``),
    ``context_length``, ``architecture.modality``, ``supported_parameters``,
    plus AA scores embedded in ``benchmarks.artificial_analysis.*`` (present
    only on some rows; absent = missing, not 0).
    """

    name = "openrouter_models"
    ttl_seconds = DAY

    def _fetch(self) -> dict[str, SourceRecord]:
        data = _get_json(OR_MODELS_URL)
        rows = data.get("data") if isinstance(data, dict) else data
        records: dict[str, SourceRecord] = {}
        for row in rows or []:
            slug = row.get("id")
            if not slug:
                continue
            records[slug] = SourceRecord(key=slug, name=row.get("name") or slug, raw=row)
        return records


class ArtificialAnalysisSource(_BaseSource):
    """AA Data API: GET /api/v2/language/models, header ``x-api-key``.

    Key is OPTIONAL (only raises rate limits): read from ``AA_API_KEY`` at
    fetch time; without a key -> {} (fail-open, nothing to scrape instead).
    ``board_version`` = major version of the AA index for the version guard.
    """

    name = "artificial_analysis"
    ttl_seconds = DAY

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def _fetch(self) -> dict[str, SourceRecord]:
        api_key = self._api_key or os.environ.get("AA_API_KEY")
        if not api_key:
            logger.info("model_selection: AA_API_KEY absent, skip artificial_analysis")
            return {}
        data = _get_json(AA_MODELS_URL, headers={"x-api-key": api_key})
        rows = data.get("data") if isinstance(data, dict) else data
        records: dict[str, SourceRecord] = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            name = row.get("name") or row.get("model") or row.get("slug") or ""
            slug = row.get("slug") or slugify(name)
            if not slug:
                continue
            evals = row.get("evaluations") if isinstance(row.get("evaluations"), dict) else row
            score = _float(
                evals.get("artificial_analysis_intelligence_index")
                or evals.get("intelligence_index")
                or evals.get("smart_index")
            )
            version = evals.get("artificial_analysis_index_version") or evals.get("index_version")
            records[slug] = SourceRecord(
                key=slugify(slug),
                name=name or slug,
                score=score,
                board_version=str(version) if version else None,
                raw=row,
            )
        return records


class LiveBenchSource(_BaseSource):
    """LiveBench (contamination hedge) via the CSV release on GitHub live-bench/LiveBench."""

    name = "livebench"
    ttl_seconds = WEEK

    def _fetch(self) -> dict[str, SourceRecord]:
        text = _get_bytes(LIVEBENCH_CSV_URL).decode("utf-8", errors="replace")
        return _parse_csv_records(
            text,
            name_cols=("model", "model_name", "name"),
            score_cols=("global_average", "score", "average", "avg"),
            ci_cols=("ci", "confidence_interval", "stderr"),
        )


class UGISource(_BaseSource):
    """UGI leaderboard (HF CSV) — PLUGIN SOURCE, not part of the shared TaskProfiles.

    Register via ``candidates(..., sources={..., "ugi": UGISource()})`` or
    provide an in-house Source; the default registry does not wire UGI into
    any task.
    """

    name = "ugi"
    ttl_seconds = WEEK

    def _fetch(self) -> dict[str, SourceRecord]:
        text = _get_bytes(UGI_CSV_URL).decode("utf-8", errors="replace")
        return _parse_csv_records(
            text,
            name_cols=("model", "model_name", "name"),
            score_cols=("ugi", "ugi_score", "score"),
        )


class ArenaSource(_BaseSource):
    """LMArena via a parquet mirror on an HF space — BEST-EFFORT.

    No official API; parquet needs ``pandas`` or ``pyarrow`` (optional, not a
    web-core dependency) -> missing parser or schema change = {}.
    """

    name = "arena"
    ttl_seconds = WEEK

    def _fetch(self) -> dict[str, SourceRecord]:
        blob = _get_bytes(ARENA_PARQUET_URL)
        rows = self._read_parquet(blob)
        records: dict[str, SourceRecord] = {}
        for row in rows:
            name = str(row.get("model") or row.get("Model") or row.get("name") or "").strip()
            score = _float(
                row.get("arena_score")
                or row.get("Arena Score")
                or row.get("rating")
                or row.get("elo")
                or row.get("score")
            )
            if not name or score is None:
                continue
            ci = _float(row.get("ci") or row.get("CI") or row.get("confidence_interval"))
            rec = SourceRecord(key=slugify(name), name=name, score=score, score_ci=ci, raw=dict(row))
            records[rec.key] = rec
        return records

    @staticmethod
    def _read_parquet(blob: bytes) -> list[dict[str, Any]]:
        try:
            import pandas as pd
        except ImportError:
            pd = None
        if pd is not None:
            return pd.read_parquet(io.BytesIO(blob)).to_dict("records")
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("arena parquet needs pandas or pyarrow") from exc
        table = pq.read_table(io.BytesIO(blob))
        return table.to_pylist()


# --- MTEB fetchers ------------------------------------------------------------
#
# All four families share one expensive step (list + download + aggregate the
# ``mteb/results`` parquet shards), memoized per process and per family result
# so e.g. ``candidates("embedding")`` pays for one download across
# mteb_classification / mteb_retrieval / mteb_sts.


def _mteb_parquet_urls() -> list[str]:
    """List parquet shard URLs for ``mteb/results`` via the datasets-server API."""
    data = _get_json(MTEB_PARQUET_LIST_URL)
    files = data.get("parquet_files") if isinstance(data, dict) else data
    urls = []
    for f in files or []:
        if isinstance(f, dict) and f.get("url"):
            urls.append(f["url"])
    return urls


def _read_mteb_table(blob: bytes) -> Any:
    """Read one parquet shard into a pyarrow Table (ImportError -> fail-open upstream)."""
    import pyarrow.parquet as pq

    return pq.read_table(
        io.BytesIO(blob),
        columns=["model_name", "task_name", "split", "score"],
    )


def _aggregate_tables(tables: list[Any]) -> dict[str, dict[str, float]]:
    """Aggregate pyarrow Tables into ``{family: {model_name: mean score}}``.

    Rows on splits other than ``test`` are ignored; scores are averaged per
    (model, task) first, then per family across tasks (mean of task means), so
    a task with many subset rows does not dominate its family. Task names that
    do not classify into one of the four families are ignored (fail-open).
    """
    import pyarrow.compute as pc

    sums: dict[str, dict[str, float]] = {}
    counts: dict[str, dict[str, int]] = {}
    for table in tables:
        filtered = table.filter(pc.equal(table.column("split"), "test"))
        grouped = filtered.group_by(["model_name", "task_name"]).aggregate([("score", "mean")])
        models = grouped.column("model_name").to_pylist()
        tasks = grouped.column("task_name").to_pylist()
        means = grouped.column("score_mean").to_pylist()
        for model, task_name, mean in zip(models, tasks, means, strict=True):
            family = task_family(task_name)
            if family is None or mean is None or not model:
                continue
            fam_sums = sums.setdefault(family, {})
            fam_counts = counts.setdefault(family, {})
            fam_sums[model] = fam_sums.get(model, 0.0) + float(mean)
            fam_counts[model] = fam_counts.get(model, 0) + 1
    return {
        family: {model: total / counts[family][model] for model, total in models.items()}
        for family, models in sums.items()
    }


_SHARED_FAMILY_SCORES: dict[str, dict[str, float]] | None = None


def _reset_mteb_memo() -> None:
    global _SHARED_FAMILY_SCORES
    _SHARED_FAMILY_SCORES = None


def _shared_family_scores(*, refresh: bool = False) -> dict[str, dict[str, float]]:
    """Family-level scores shared by all MTEB fetchers (one download per process)."""
    global _SHARED_FAMILY_SCORES
    if _SHARED_FAMILY_SCORES is not None and not refresh:
        return _SHARED_FAMILY_SCORES
    tables = [_read_mteb_table(_get_bytes(url)) for url in _mteb_parquet_urls()]
    _SHARED_FAMILY_SCORES = _aggregate_tables(tables)
    return _SHARED_FAMILY_SCORES


class _MtebFamilySource(_BaseSource):
    """Base for the four MTEB family fetchers; subclasses pick their family."""

    family = ""
    ttl_seconds = WEEK

    def _fetch(self) -> dict[str, SourceRecord]:
        scores = _shared_family_scores().get(self.family, {})
        return {
            model: SourceRecord(key=model, name=model, score=score)
            for model, score in scores.items()
            if score is not None
        }


class MtebClassificationSource(_MtebFamilySource):
    """Mean MTEB classification score per model (mteb/results, test split)."""

    name = "mteb_classification"
    family = "classification"


class MtebRetrievalSource(_MtebFamilySource):
    """Mean MTEB retrieval score per model (mteb/results, test split)."""

    name = "mteb_retrieval"
    family = "retrieval"


class MtebStsSource(_MtebFamilySource):
    """Mean MTEB STS score per model (mteb/results, test split)."""

    name = "mteb_sts"
    family = "sts"


class MtebRerankingSource(_MtebFamilySource):
    """Mean MTEB reranking score per model (mteb/results, test split)."""

    name = "mteb_reranking"
    family = "reranking"


def fetch_endpoint_stats(or_slug: str) -> dict[str, Any]:
    """GET /api/v1/models/{slug}/endpoints — uptime/latency/zdr per provider.

    Used by ``enrich_uptime`` after shortlisting (1 request/model instead of a
    full sweep). Fail-open: error -> {}.
    """
    try:
        data = _get_json(OR_ENDPOINTS_URL.format(slug=or_slug))
    except Exception as exc:
        logger.warning("model_selection endpoints failed: slug=%s error=%s", or_slug, exc)
        return {}
    rows = data.get("data") if isinstance(data, dict) else data
    uptimes: list[float] = []
    zdr = False
    latency: float | None = None
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        u = _float(row.get("uptime_last_1d"))
        if u is not None:
            uptimes.append(u)
        tag = str(row.get("tag") or "")
        if "zdr" in tag.lower():
            zdr = True
        lat = _float(row.get("latency_last_30m"))
        if lat is not None:
            latency = lat if latency is None else min(latency, lat)
    return {
        "uptime_1d": max(uptimes) if uptimes else None,
        "zdr_available": zdr,
        "latency_30m": latency,
    }


# Default registry. Source names in a TaskProfile without an entry here are
# skipped (fail-open) — the registry may point at fetchers not yet written or
# supplied by the consumer as plugins (e.g. "eqbench_creative_v3", "ugi").
SOURCE_REGISTRY: dict[str, Source] = {
    "openrouter_models": OpenRouterModelsSource(),
    "artificial_analysis": ArtificialAnalysisSource(),
    "livebench": LiveBenchSource(),
    "arena": ArenaSource(),
    "ugi": UGISource(),
    "mteb_classification": MtebClassificationSource(),
    "mteb_retrieval": MtebRetrievalSource(),
    "mteb_sts": MtebStsSource(),
    "mteb_reranking": MtebRerankingSource(),
}
