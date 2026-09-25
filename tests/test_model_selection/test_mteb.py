"""MTEB fetcher tests — fixture-based, no network in CI.

Cover: task_family taxonomy (exact + legacy + suffix fallback + exclusions),
parquet aggregation (split filter, per-task then per-family means, unknown
task names ignored), the shared per-process download memo, family fetchers
(keyed by raw model_name, weekly TTL), fail-open when the parquet listing
fails or no parquet reader is installed.
"""

from __future__ import annotations

import io
import itertools
import sys
from unittest.mock import patch

import pytest

import web_core.model_selection.sources as src
from web_core.model_selection.mteb_tasks import task_family
from web_core.model_selection.sources import (
    DAY,
    WEEK,
    MtebClassificationSource,
    MtebRerankingSource,
    MtebRetrievalSource,
    MtebStsSource,
    _aggregate_tables,
    _reset_mteb_memo,
    _shared_family_scores,
)

pa = pytest.importorskip("pyarrow")


@pytest.fixture(autouse=True)
def _fresh_memo():
    _reset_mteb_memo()
    yield
    _reset_mteb_memo()


def _table(rows: list[dict]) -> pa.Table:
    return pa.Table.from_pylist(
        rows,
        schema=pa.schema(
            [
                ("model_name", pa.large_string()),
                ("task_name", pa.large_string()),
                ("split", pa.large_string()),
                ("score", pa.float64()),
            ]
        ),
    )


# --- taxonomy -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("task_name", "want"),
    [
        ("Banking77Classification", "classification"),
        ("CovidDisinformationNLMultiLabelClassification", "classification"),
        ("MTOPIntent", "classification"),  # legacy alias (v1 name)
        ("MTOPIntentClassification", "classification"),  # exact (current name)
        ("ArguAna", "retrieval"),
        ("NQ", "retrieval"),
        ("MIRACLRetrievalHardNegatives", "retrieval"),  # suffix fallback
        ("FeverHardNegatives", "retrieval"),  # case-folded base resolution
        ("Touche2023", "retrieval"),  # legacy alias
        ("STS22", "sts"),  # exact carries STS22.v2; prefix fallback catches STS22
        ("STS22.v2", "sts"),
        ("BIOSSES", "sts"),
        ("SICK-R", "sts"),
        ("SemRel", "sts"),  # legacy alias (renamed SemRel24STS)
        ("AskUbuntuDupQuestions", "reranking"),
        ("SciDocsRR", "reranking"),
        ("NewBoardReranking", "reranking"),  # suffix fallback
        ("ArxivClusteringP2P", None),  # clustering is outside the four families
        ("FloresBitextMining", None),
        ("SICKNLPairClassification", None),  # pair classification, not classification
        ("SummarizationTask", None),
        ("TotallyUnknownBoard", None),
    ],
)
def test_task_family(task_name, want):
    assert task_family(task_name) == want


# --- aggregation ----------------------------------------------------------------


def test_aggregate_tables_means_per_task_then_family():
    tables = [
        _table(
            [
                # BIOSSES: mean over rows (test split only)
                {"model_name": "m/a", "task_name": "BIOSSES", "split": "test", "score": 0.80},
                {"model_name": "m/a", "task_name": "BIOSSES", "split": "test", "score": 0.60},
                # SICK-R: one row -> task mean 0.50
                {"model_name": "m/a", "task_name": "SICK-R", "split": "test", "score": 0.50},
                # non-test split ignored
                {"model_name": "m/a", "task_name": "BIOSSES", "split": "validation", "score": 0.99},
            ]
        ),
    ]
    agg = _aggregate_tables(tables)
    # family score = mean of task means: BIOSSES 0.70, SICK-R 0.50 -> 0.60
    assert agg["sts"]["m/a"] == pytest.approx(0.60)


def test_aggregate_tables_multiple_families_and_unknown_tasks():
    tables = [
        _table(
            [
                {"model_name": "m/a", "task_name": "Banking77Classification", "split": "test", "score": 0.90},
                {"model_name": "m/a", "task_name": "ArguAna", "split": "test", "score": 0.55},
                {"model_name": "m/a", "task_name": "ArxivClusteringP2P", "split": "test", "score": 0.70},  # ignored
                {"model_name": "", "task_name": "ArguAna", "split": "test", "score": 0.40},  # empty model ignored
                {"model_name": "m/a", "task_name": "ArguAna", "split": "test", "score": None},  # null mean ignored
            ]
        )
    ]
    agg = _aggregate_tables(tables)
    assert set(agg) == {"classification", "retrieval"}
    assert agg["classification"]["m/a"] == pytest.approx(0.90)
    assert agg["retrieval"]["m/a"] == pytest.approx(0.55)


def test_aggregate_tables_empty_input():
    assert _aggregate_tables([]) == {}


def test_read_mteb_table_roundtrip():
    table = _table([{"model_name": "m/a", "task_name": "ArguAna", "split": "test", "score": 0.5}])
    buf = io.BytesIO()
    import pyarrow.parquet as pq

    pq.write_table(table, buf)
    out = src._read_mteb_table(buf.getvalue())
    assert out.column_names == ["model_name", "task_name", "split", "score"]
    assert out.num_rows == 1


# --- shared scores + family fetchers ---------------------------------------------


def _patch_pipeline(tables, urls=None):
    # each shard decodes to the next fixture table, cycling so extra calls never starve
    shards = itertools.cycle(tables)
    return (
        patch.object(src, "_mteb_parquet_urls", return_value=urls or ["u1", "u2"]),
        patch.object(src, "_get_bytes", side_effect=lambda url: url.encode()),
        patch.object(src, "_read_mteb_table", side_effect=lambda _blob: next(shards)),
    )


def test_shared_family_scores_one_download_shared_across_fetchers():
    tables = [
        _table([{"model_name": "m/a", "task_name": "ArguAna", "split": "test", "score": 0.50}]),
        _table([{"model_name": "m/a", "task_name": "BIOSSES", "split": "test", "score": 0.70}]),
    ]
    p1, p2, p3 = _patch_pipeline(tables)
    with p1 as urls_mock, p2 as bytes_mock, p3 as read_mock:
        scores = _shared_family_scores()
        scores_again = _shared_family_scores()
    assert scores is scores_again  # memoized
    assert urls_mock.call_count == 1  # one listing call total
    assert bytes_mock.call_count == 2  # one download per shard, paid once
    assert read_mock.call_count == 2
    assert scores["retrieval"] == {"m/a": pytest.approx(0.50)}
    assert scores["sts"] == {"m/a": pytest.approx(0.70)}


def test_shared_family_scores_refresh_bypasses_memo():
    tables = [_table([{"model_name": "m/a", "task_name": "ArguAna", "split": "test", "score": 0.50}])]
    p1, p2, p3 = _patch_pipeline(tables)
    with p1 as urls_mock, p2, p3:
        _shared_family_scores()
        _shared_family_scores(refresh=True)
    assert urls_mock.call_count == 2


@pytest.mark.parametrize(
    ("cls", "family"),
    [
        (MtebClassificationSource, "classification"),
        (MtebRetrievalSource, "retrieval"),
        (MtebStsSource, "sts"),
        (MtebRerankingSource, "reranking"),
    ],
)
def test_family_fetcher_returns_records_keyed_by_model_name(cls, family):
    tables = [
        _table(
            [
                {"model_name": f"org/model-{family}", "task_name": "ArguAna", "split": "test", "score": 0.55},
                {"model_name": f"org/model-{family}", "task_name": "SICK-R", "split": "test", "score": 0.65},
            ]
        )
    ]
    if family == "reranking":
        tables = [
            _table(
                [
                    {
                        "model_name": f"org/model-{family}",
                        "task_name": "AskUbuntuDupQuestions",
                        "split": "test",
                        "score": 0.6,
                    }
                ]
            )
        ]
    if family == "classification":
        tables = [
            _table(
                [
                    {
                        "model_name": f"org/model-{family}",
                        "task_name": "Banking77Classification",
                        "split": "test",
                        "score": 0.9,
                    }
                ]
            )
        ]
    p1, p2, p3 = _patch_pipeline(tables)
    with p1, p2, p3:
        recs = cls().fetch()
    assert cls.name in {
        "mteb_classification",
        "mteb_retrieval",
        "mteb_sts",
        "mteb_reranking",
    }
    assert cls.ttl_seconds == WEEK  # weekly TTL: the aggregate is cache-friendly
    assert set(recs) == {f"org/model-{family}"}
    rec = recs[f"org/model-{family}"]
    assert rec.key == f"org/model-{family}"  # raw HF id: joins via the alias index
    expected = {"classification": 0.9, "retrieval": 0.55, "sts": 0.65, "reranking": 0.6}[family]
    assert rec.score == pytest.approx(expected)


def test_family_fetcher_empty_family_returns_empty():
    tables = [_table([{"model_name": "m/a", "task_name": "ArxivClusteringP2P", "split": "test", "score": 0.5}])]
    p1, p2, p3 = _patch_pipeline(tables)
    with p1, p2, p3:
        assert MtebRerankingSource().fetch() == {}


def test_family_fetcher_fail_open_on_listing_error():
    with patch.object(src, "_mteb_parquet_urls", side_effect=ConnectionError("hf down")):
        assert MtebStsSource().fetch() == {}


def test_family_fetcher_fail_open_without_parquet_reader(monkeypatch):
    # both patch targets make "import pyarrow.parquet" raise ImportError
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", None)
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with (
        patch.object(src, "_mteb_parquet_urls", return_value=["u1"]),
        patch.object(src, "_get_bytes", return_value=b"parquet-bytes"),
    ):
        assert MtebRetrievalSource().fetch() == {}


def test_mteb_parquet_urls_parses_listing():
    payload = {
        "parquet_files": [
            {"url": "https://example.test/0000.parquet", "size": 1},
            {"url": None},  # skipped
            "junk",  # skipped
        ]
    }
    with patch.object(src, "_get_json", return_value=payload):
        assert src._mteb_parquet_urls() == ["https://example.test/0000.parquet"]


def test_mteb_sources_not_daily():
    """Guard against accidentally tying MTEB aggregates to the daily TTL."""
    for cls in (MtebClassificationSource, MtebRetrievalSource, MtebStsSource, MtebRerankingSource):
        assert cls.ttl_seconds == WEEK
        assert cls.ttl_seconds != DAY
