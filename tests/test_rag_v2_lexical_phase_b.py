"""OPT-RAGV2-LEXICAL Phase B: V2 parity tests.

Gate for shipping B2: with AIOS_RAGV2_LEXICAL_V2=1 (every sub-toggle at its
default), the top-15 results must be IDENTICAL to the V2=0 baseline on
synthetic data -- especially for CJK queries. Any divergence -> do not ship.

Also verifies each sub-toggle can be flipped independently without breaking
parity, and that the opt-in CJK trigram path agrees with the LIKE prefilter
once OMP builds the chunks_fts_trigram table.
"""
import os
import shutil
import sqlite3

import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import LocalChunkIndex
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend

MASTER_ENV = "AIOS_RAGV2_LEXICAL_V2"
SUB_TOGGLES = [
    "TEMP_TXN",
    "SKIP_FULL_ELIGIBLE",
    "NARROW_ELIGIBILITY",
    "PRIVACY_LAZY",
    "SCORE_HOIST",
    "SCORE_CACHE",
    "CJK_TRIGRAM",
]

# FTS queries (incl. an identifier code -> rescue path) + CJK queries
# (LIKE prefilter path).
QUERIES = [
    "loi servo E302 qua tai truc X",
    "lap rap jig do cong venh",
    "bao tri bang tai dinh ky",
    "サーボモータ 過負荷エラー",
    "治具 組立手順",
]

VI_TOPICS = [
    "loi dong co servo truc X may cnc bao loi E302 qua tai",
    "huong dan lap rap jig do kiem tra do cong venh",
    "bao tri dinh ky bang tai chuyen phoi lieu",
    "do nhiet do dau thuy luc he thong ep nhua",
    "kiem tra cam bien tiep can cong doan han",
]
JP_TOPICS = [
    "サーボモータ過負荷エラー E302 対処方法",
    "治具組立手順 歪み検査方法",
    "ベルトコンベア定期メンテナンス",
]


def _make_chunk(i):
    if i % 7 == 0:
        text = JP_TOPICS[i % len(JP_TOPICS)] + f" 補足資料 {i}"
    else:
        text = VI_TOPICS[i % len(VI_TOPICS)] + f" chi tiet ma so {i}"
    text = (text + " ") * 6
    metadata = {}
    if i % 3 == 0:
        metadata = {"section_path": ["bao tri", "quy trinh"], "sheet_names": []}
    if i % 5 == 0:
        metadata = {"element_types": ["table"], "confidence": 0.9}
    return DocumentChunk(
        chunk_id=f"chunk-{i:06d}",
        document_id=f"doc-{i // 50:05d}",
        source_path=f"/data/source-{i // 50:05d}.txt",
        source_name=f"source-{i // 50:05d}.txt",
        file_type="txt",
        text=text,
        normalized_text=text.casefold(),
        element_ids=(f"element-{i}",),
        element_types=("text",),
        section_path=("section",),
        privacy_labels=("allowed",),
        source_fingerprint="v1",
        metadata=metadata,
    )


@pytest.fixture(scope="module")
def template_db_path(tmp_path_factory):
    """Build the 1500-chunk synthetic index once per module.

    Function fixtures below copy this file so each test gets an isolated
    DB without paying the ingest cost (and disk) 30 times.
    """
    db_path = tmp_path_factory.mktemp("lex_b_template") / "lex_b.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=16)
    with LocalChunkIndex(str(db_path), embedding_backend=backend) as index:
        index.upsert_chunks([_make_chunk(i) for i in range(1500)])
    return str(db_path)


@pytest.fixture()
def index_path(tmp_path, template_db_path):
    db_path = tmp_path / "lex_b.sqlite"
    shutil.copy(template_db_path, db_path)
    return str(db_path)


def _open_index(db_path):
    backend = DeterministicEmbeddingBackend(dimension=16)
    return LocalChunkIndex(db_path, embedding_backend=backend)


def _result_signature(response):
    return [(r.chunk_id, r.score) for r in response.results]


def _build_trigram_table(db_path):
    """Build the OMP-owned trigram table the CJK_TRIGRAM path reads."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts_trigram"
        " USING fts5(chunk_id UNINDEXED, text, tokenize='trigram')"
    )
    rows = conn.execute(
        "SELECT chunk_id,"
        " COALESCE(normalized_text,'') || ' ' || COALESCE(source_name,'')"
        " || ' ' || COALESCE(source_path,'')"
        " || ' ' || COALESCE(metadata_json,'')"
        " FROM chunks WHERE retrievable = 1"
    ).fetchall()
    conn.executemany(
        "INSERT INTO chunks_fts_trigram(chunk_id, text) VALUES (?, ?)", rows
    )
    conn.commit()
    conn.close()


@pytest.mark.parametrize("query", QUERIES)
def test_v2_default_parity_top15(index_path, query, monkeypatch):
    """V2=1 at defaults must reproduce V2=0 top-15 exactly (ids + scores)."""
    monkeypatch.delenv(MASTER_ENV, raising=False)
    with _open_index(index_path) as index:
        baseline = _result_signature(index.search_with_summary(query, limit=15))
    monkeypatch.setenv(MASTER_ENV, "1")
    with _open_index(index_path) as index:
        optimized = _result_signature(index.search_with_summary(query, limit=15))
        breakdown = index.search_with_summary(query, limit=15).summary.lexical_breakdown_ms
    assert [chunk_id for chunk_id, _ in optimized] == [
        chunk_id for chunk_id, _ in baseline
    ]
    assert [score for _, score in optimized] == [score for _, score in baseline]
    assert len(optimized) == len(baseline) > 0
    assert dict(breakdown).get("eligible_rows") == 1500.0


@pytest.mark.parametrize("toggle", SUB_TOGGLES)
@pytest.mark.parametrize("query", QUERIES[:3])
def test_v2_each_toggle_independent_parity(index_path, query, toggle, monkeypatch):
    """Flipping any single sub-toggle off must not break V2=0 parity."""
    monkeypatch.delenv(MASTER_ENV, raising=False)
    with _open_index(index_path) as index:
        baseline = _result_signature(index.search_with_summary(query, limit=15))
    monkeypatch.setenv(MASTER_ENV, "1")
    monkeypatch.setenv(f"AIOS_RAGV2_LEX_V2_{toggle}", "0")
    with _open_index(index_path) as index:
        optimized = _result_signature(index.search_with_summary(query, limit=15))
    assert [chunk_id for chunk_id, _ in optimized] == [
        chunk_id for chunk_id, _ in baseline
    ]
    assert [score for _, score in optimized] == [score for _, score in baseline]


@pytest.mark.parametrize("query", [q for q in QUERIES if any(ord(c) > 127 for c in q)])
def test_v2_trigram_agrees_with_like_prefilter(index_path, query, monkeypatch):
    """With the trigram table present, CJK_TRIGRAM=1 must match the LIKE path."""
    _build_trigram_table(index_path)
    monkeypatch.setenv(MASTER_ENV, "1")
    monkeypatch.setenv("AIOS_RAGV2_LEX_V2_CJK_TRIGRAM", "0")
    with _open_index(index_path) as index:
        like_path = _result_signature(index.search_with_summary(query, limit=15))
    monkeypatch.setenv("AIOS_RAGV2_LEX_V2_CJK_TRIGRAM", "1")
    with _open_index(index_path) as index:
        trigram_path = _result_signature(index.search_with_summary(query, limit=15))
        breakdown = dict(
            index.search_with_summary(query, limit=15).summary.lexical_breakdown_ms
        )
    assert [chunk_id for chunk_id, _ in trigram_path] == [
        chunk_id for chunk_id, _ in like_path
    ]
    assert [score for _, score in trigram_path] == [score for _, score in like_path]
    assert breakdown.get("trigram_match_ms", 0.0) > 0.0


def test_v2_trigram_missing_table_falls_back_to_like(index_path, monkeypatch):
    """CJK_TRIGRAM=1 without the table must silently use the LIKE path."""
    monkeypatch.setenv(MASTER_ENV, "1")
    monkeypatch.setenv("AIOS_RAGV2_LEX_V2_CJK_TRIGRAM", "1")
    with _open_index(index_path) as index:
        response = index.search_with_summary("サーボモータ 過負荷エラー", limit=15)
    breakdown = dict(response.summary.lexical_breakdown_ms)
    assert len(response.results) > 0
    assert breakdown.get("like_prefilter_ms", 0.0) > 0.0
    assert "trigram_match_ms" not in breakdown


def test_v2_skip_full_eligible_records_skip(index_path, monkeypatch):
    """Unfiltered search should take the SKIP_FULL_ELIGIBLE fast path."""
    monkeypatch.setenv(MASTER_ENV, "1")
    with _open_index(index_path) as index:
        response = index.search_with_summary("lap rap jig do cong venh", limit=15)
    breakdown = dict(response.summary.lexical_breakdown_ms)
    assert breakdown.get("temp_build_skipped", 0.0) >= 1.0
    assert "temp_build_ms" not in breakdown
