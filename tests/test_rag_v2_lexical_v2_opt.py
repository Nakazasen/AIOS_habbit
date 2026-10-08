import os
import sqlite3
import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    _LEX_V2_MASTER_ENV,
    LocalChunkIndex,
    SearchOptions,
    _lexical_v2_flags,
    _identifier_literals,
    _VIETNAMESE_COMMON_STOPWORDS,
)
from aios_habit.rag_v2.query_planning import coerce_query_plan
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend


def make_chunk(
    chunk_id: str,
    document_id: str,
    text: str,
    *,
    labels=("allowed",),
    fingerprint="v1",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source_path=f"/workspace/{document_id}.txt",
        source_name=f"{document_id}.txt",
        file_type="txt",
        text=text,
        normalized_text=text.casefold(),
        element_ids=(f"element-{chunk_id}",),
        element_types=("text",),
        section_path=("section", chunk_id),
        privacy_labels=labels,
        source_fingerprint=fingerprint,
        checksum=f"checksum-{chunk_id}-{fingerprint}",
    )


@pytest.fixture
def test_index(tmp_path):
    db_file = tmp_path / "test_lexical.sqlite"
    embedding_backend = DeterministicEmbeddingBackend(dimension=8)
    idx = LocalChunkIndex(
        db_file,
        enable_fts5=True,
        embedding_backend=embedding_backend,
    )
    chunks = [
        make_chunk("c1", "doc1", "Bảo dưỡng khuôn 14/2 Magenta tỷ lệ lỗi C7620 tăng cao"),
        make_chunk("c2", "doc1", "Hiện tượng tại LSU Line xảy ra do bụi bẩn trên gương"),
        make_chunk("c3", "doc2", "Kiểm tra bằng tấm OHP cho kết quả đối sách đạt chuẩn"),
        make_chunk("c4", "doc3", "Unit 1 có liên quan đến Jig và thông số g1 g2"),
    ]
    idx.upsert_chunks(chunks)
    return idx


def test_lexical_v2_flags_default_enabled(monkeypatch):
    monkeypatch.delenv(_LEX_V2_MASTER_ENV, raising=False)
    flags = _lexical_v2_flags()
    assert flags is not None
    assert flags["SKIP_FULL_ELIGIBLE"] is True
    assert flags["NARROW_ELIGIBILITY"] is True
    assert flags["SELECTIVE_TERMS"] is True


def test_lexical_v2_flags_rollback(monkeypatch):
    monkeypatch.setenv(_LEX_V2_MASTER_ENV, "0")
    flags = _lexical_v2_flags()
    assert flags is None


def test_search_with_v2_enabled(test_index, monkeypatch):
    monkeypatch.setenv(_LEX_V2_MASTER_ENV, "1")
    plan = coerce_query_plan("Lỗi C7620 Magenta")
    resp = test_index.search_with_summary(plan, limit=10)
    assert len(resp.results) > 0
    assert resp.results[0].chunk_id == "c1"
    assert "C7620" in resp.results[0].text
    # Kiểm tra breakdown có ghi nhận
    bd_dict = dict(resp.summary.lexical_breakdown_ms)
    assert "fts_match_ms" in bd_dict


def test_search_with_v2_disabled_fallback(test_index, monkeypatch):
    monkeypatch.setenv(_LEX_V2_MASTER_ENV, "0")
    plan = coerce_query_plan("Lỗi C7620 Magenta")
    resp = test_index.search_with_summary(plan, limit=10)
    assert len(resp.results) > 0
    assert resp.results[0].chunk_id == "c1"


def test_fast_identifier_rescue(test_index, monkeypatch):
    monkeypatch.setenv(_LEX_V2_MASTER_ENV, "1")
    plan = coerce_query_plan("Hiện tượng tại LSU Line")
    resp = test_index.search_with_summary(plan, limit=10)
    assert len(resp.results) > 0
    top_ids = [r.chunk_id for r in resp.results]
    assert "c2" in top_ids


def test_identifier_literals_extraction():
    literals = _identifier_literals("Kiểm tra mã C7620 và g1 g2 tại LSU Line")
    assert "C7620" in literals or any("C7620" in lit for lit in literals)
    assert any("LSU" in lit or "Line" in lit for lit in literals)


def test_vietnamese_stopwords_coverage():
    assert "và" in _VIETNAMESE_COMMON_STOPWORDS
    assert "có" in _VIETNAMESE_COMMON_STOPWORDS
    assert "ngày" in _VIETNAMESE_COMMON_STOPWORDS
    assert "2" in _VIETNAMESE_COMMON_STOPWORDS
