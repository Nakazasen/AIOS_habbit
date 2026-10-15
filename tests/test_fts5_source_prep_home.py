"""Unit tests for DESKTOP-SPEED-FTS5-SOURCE-PREP-HOME.

Covers:
1. Preloading and caching of lexical structures (`preload_lexical_structures`, `_LexicalStructureCache`).
2. 100% lexical result equivalence before/after `_LexicalStructureCache` across FTS5 BM25,
   subset eligibility filtering, CJK prefilter, identifier rescue, and summary search.
3. Zero temp-table rebuilds (`rag_v2_eligible_chunks`) and zero `chunks` eligibility scans
   on preloaded/read-only queries.
4. Automatic cache invalidation when `_note_main_db_write` occurs.
5. `hybrid_search_with_summary` latency accumulation and query-vector cache reuse across `thin_retry=True`.
6. Adapter `_maybe_expand_latin_query_for_cjk_corpus` immediate skip when `AIOS_AI_BACKEND=local`.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Sequence
from unittest.mock import patch

import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    LocalChunkIndex,
    SearchOptions,
    clear_process_lexical_structure_cache,
)
from aios_habit.rag_v2.semantic import (
    DeterministicEmbeddingBackend,
    SemanticCapability,
    SparseVector,
)
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceAIContextSource,
    _maybe_expand_latin_query_for_cjk_corpus,
)


class _CountingHybridBackend(DeterministicEmbeddingBackend):
    def __init__(self) -> None:
        super().__init__()
        self.embed_query_calls = 0
        self.sparse_query_calls = 0

    @property
    def sparse_capability(self) -> SemanticCapability:
        return SemanticCapability(
            capability="sparse_embedding",
            available=True,
            backend="deterministic-test",
            model=self.descriptor,
        )

    def embed_query(self, text: str) -> tuple[float, ...]:
        self.embed_query_calls += 1
        return super().embed_query(text)

    def sparse_documents(self, texts: Sequence[str]) -> tuple[SparseVector, ...]:
        out: list[SparseVector] = []
        for t in texts:
            words = [w.lower() for w in t.split() if len(w) >= 2]
            out.append({w: 1.0 for w in words[:8]} or {"default": 1.0})
        return tuple(out)

    def sparse_query(self, text: str) -> SparseVector:
        self.sparse_query_calls += 1
        words = [w.lower() for w in text.split() if len(w) >= 2]
        return {w: 1.0 for w in words[:8]} or {"default": 1.0}


def _sample_chunks() -> tuple[DocumentChunk, ...]:
    return (
        DocumentChunk(
            chunk_id="chk-lsu-01",
            document_id="doc-lsu-tonly",
            source_path="/corpus/lsu/tonly_dtm.pdf",
            source_name="tonly_dtm.pdf",
            file_type="document_summary",
            text="Báo cáo ĐTM Nhà máy thông minh Tonly Việt Nam quy định hệ thống xử lý khí thải than hoạt tính và bể lắng nước thải sinh hoạt.",
            normalized_text="Báo cáo ĐTM Nhà máy thông minh Tonly Việt Nam quy định hệ thống xử lý khí thải than hoạt tính và bể lắng nước thải sinh hoạt.",
            element_ids=("el-1",),
            element_types=("paragraph",),
            section_path=("Chương 4", "Biện pháp giảm thiểu"),
            metadata={"is_document_summary": True, "section_path": ["Chương 4", "Biện pháp giảm thiểu"]},
            privacy_labels=("local_only",),
            source_fingerprint="fp-tonly-1",
            checksum="cs-tonly-1",
        ),
        DocumentChunk(
            chunk_id="chk-lsu-02",
            document_id="doc-lsu-mitutoyo",
            source_path="/corpus/lsu/mitutoyo_500_181_30.pdf",
            source_name="mitutoyo_500_181_30.pdf",
            file_type="pdf",
            text="Chứng chỉ kiểm tra Mitutoyo cho thước cặp hiện số ABS Digimatic Caliper 500-181-30 có dải đo 0-150 mm và độ chia 0.01 mm.",
            normalized_text="Chứng chỉ kiểm tra Mitutoyo cho thước cặp hiện số ABS Digimatic Caliper 500-181-30 có dải đo 0-150 mm và độ chia 0.01 mm.",
            element_ids=("el-2",),
            element_types=("paragraph",),
            section_path=("Spec",),
            metadata={"section_path": ["Spec"]},
            privacy_labels=("local_only",),
            source_fingerprint="fp-mitutoyo-1",
            checksum="cs-mitutoyo-1",
        ),
        DocumentChunk(
            chunk_id="chk-cjk-01",
            document_id="doc-cjk-sanyo",
            source_path="/corpus/lsu/sanyo_9GA0412P3J01.pdf",
            source_name="sanyo_9GA0412P3J01.pdf",
            file_type="pdf",
            text="山洋電気 冷却ファン San Ace 40 9GA0412P3J01 定格電圧 12V 定格電流 0.60A 定格回転速度 16000 min-1",
            normalized_text="山洋電気 冷却ファン San Ace 40 9GA0412P3J01 定格電圧 12V 定格電流 0.60A 定格回転速度 16000 min-1",
            element_ids=("el-3",),
            element_types=("paragraph",),
            section_path=("仕様",),
            metadata={"section_path": ["仕様"]},
            privacy_labels=("local_only",),
            source_fingerprint="fp-sanyo-1",
            checksum="cs-sanyo-1",
        ),
        DocumentChunk(
            chunk_id="chk-dtl-01",
            document_id="doc-dtl-molding",
            source_path="/corpus/dtl/bao_cao_loi_duc.xlsx",
            source_name="bao_cao_loi_duc.xlsx",
            file_type="xlsx",
            text="Báo cáo điều tra lỗi đúc nhựa: lỗi bavia (burr) và thiếu nhựa (short shot) do áp suất bảo áp thấp và mòn mặt phân khuôn.",
            normalized_text="Báo cáo điều tra lỗi đúc nhựa: lỗi bavia (burr) và thiếu nhựa (short shot) do áp suất bảo áp thấp và mòn mặt phân khuôn.",
            element_ids=("el-4",),
            element_types=("table",),
            section_path=("Sheet1",),
            metadata={"sheet_names": ["Sheet1"]},
            privacy_labels=("public",),
            source_fingerprint="fp-dtl-1",
            checksum="cs-dtl-1",
        ),
    )


def test_preload_lexical_structures_and_exact_equivalence(tmp_path: Path) -> None:
    clear_process_lexical_structure_cache()
    db_path = tmp_path / "library.sqlite"
    writer = LocalChunkIndex(db_path)
    writer.upsert_chunks(_sample_chunks())
    writer.close()

    # 1. Baseline without lexical structure cache
    orig_active = LocalChunkIndex._active_lexical_structure_cache
    LocalChunkIndex._active_lexical_structure_cache = lambda self, auto_load_read_only=True: None  # type: ignore[method-assign]
    try:
        idx_base = LocalChunkIndex(db_path, read_only=True)
        opts_subset = SearchOptions(
            candidate_limit=10,
            allowed_document_ids=frozenset({"doc-lsu-tonly", "doc-lsu-mitutoyo", "doc-cjk-sanyo"}),
            expected_source_fingerprints={
                "doc-lsu-tonly": "fp-tonly-1",
                "doc-lsu-mitutoyo": "fp-mitutoyo-1",
                "doc-cjk-sanyo": "fp-sanyo-1",
            },
        )
        opts_all = SearchOptions(candidate_limit=10)
        q_fts = "Báo cáo ĐTM Nhà máy Tonly Việt Nam xử lý khí thải"
        q_id = "Thước cặp 500-181-30 Mitutoyo dải đo bao nhiêu"
        q_cjk = "冷却ファン 9GA0412P3J01 定格電圧"

        base_fts = idx_base.search_with_summary(q_fts, limit=5, options=opts_subset)
        base_id = idx_base.search_with_summary(q_id, limit=5, options=opts_subset)
        base_cjk = idx_base.search_with_summary(q_cjk, limit=5, options=opts_subset)
        base_all = idx_base.search_with_summary(q_fts, limit=5, options=opts_all)
        base_sum = idx_base.search_summaries_with_summary(q_fts, limit=5, options=opts_subset)
        idx_base.close()
    finally:
        LocalChunkIndex._active_lexical_structure_cache = orig_active  # type: ignore[method-assign]

    # 2. Preloaded index
    clear_process_lexical_structure_cache()
    idx_fast = LocalChunkIndex(db_path, read_only=True)
    chunk_count, preload_ms = idx_fast.preload_lexical_structures()
    assert chunk_count == 4
    assert preload_ms >= 0.0

    sql_statements: list[str] = []
    idx_fast._conn.set_trace_callback(sql_statements.append)
    fast_fts = idx_fast.search_with_summary(q_fts, limit=5, options=opts_subset)
    fast_id = idx_fast.search_with_summary(q_id, limit=5, options=opts_subset)
    fast_cjk = idx_fast.search_with_summary(q_cjk, limit=5, options=opts_subset)
    fast_all = idx_fast.search_with_summary(q_fts, limit=5, options=opts_all)
    fast_sum = idx_fast.search_summaries_with_summary(q_fts, limit=5, options=opts_subset)
    idx_fast._conn.set_trace_callback(None)

    for base_resp, fast_resp in (
        (base_fts, fast_fts),
        (base_id, fast_id),
        (base_cjk, fast_cjk),
        (base_all, fast_all),
        (base_sum, fast_sum),
    ):
        assert [r.chunk_id for r in fast_resp.results] == [r.chunk_id for r in base_resp.results]
        assert [r.score for r in fast_resp.results] == pytest.approx([r.score for r in base_resp.results])
        assert fast_resp.summary.indexed_chunk_count == base_resp.summary.indexed_chunk_count
        assert fast_resp.summary.eligible_chunk_count == base_resp.summary.eligible_chunk_count
        assert fast_resp.summary.filtered_by_source_count == base_resp.summary.filtered_by_source_count
        assert fast_resp.summary.filtered_by_privacy_count == base_resp.summary.filtered_by_privacy_count
        assert fast_resp.summary.filtered_as_stale_count == base_resp.summary.filtered_as_stale_count

    # Ensure zero temp-table creation or inserts and zero `chunks` eligibility scans
    upper_sql = [s.upper() for s in sql_statements]
    assert not any("RAG_V2_ELIGIBLE_CHUNKS" in s for s in upper_sql)
    assert not any("WHERE RETRIEVABLE = 1 AND DOCUMENT_ID IN" in s for s in upper_sql)
    idx_fast.close()


def test_lexical_cache_invalidates_on_write(tmp_path: Path) -> None:
    clear_process_lexical_structure_cache()
    db_path = tmp_path / "library_write.sqlite"
    idx = LocalChunkIndex(db_path)
    idx.upsert_chunks(_sample_chunks()[:2])
    cnt1, _ = idx.preload_lexical_structures()
    assert cnt1 == 2
    assert idx.count() == 2

    # Upsert remaining chunks -> _note_main_db_write increments write_seq -> reloads cache
    idx.upsert_chunks(_sample_chunks()[2:])
    assert idx.count() == 4
    cnt2, _ = idx.preload_lexical_structures()
    assert cnt2 == 4
    idx.close()


def test_hybrid_thin_retry_accumulates_latencies_and_caches_query_vectors(tmp_path: Path) -> None:
    clear_process_lexical_structure_cache()
    db_path = tmp_path / "library_hybrid.sqlite"
    backend = _CountingHybridBackend()
    idx = LocalChunkIndex(db_path, embedding_backend=backend, sparse_backend=backend)
    idx.upsert_chunks(_sample_chunks())
    idx.preload_dense_matrix_cache()
    idx.preload_sparse_vector_cache()
    idx.preload_lexical_structures()

    # Force thin retry by using a query with multiple uncommon terms so coverage < 0.75 on pass 1
    query = "Tonly xylophoneqz999 unikorn777"
    resp = idx.hybrid_search_with_summary(
        query,
        limit=4,
        options=SearchOptions(candidate_limit=4, per_document_limit=1),
    )
    assert resp.summary.lexical_latency_ms > 0.0
    # Even if thin_retry ran a second pass over the same variants, query vectors are cached per variant text
    variant_count = resp.summary.query_variant_count
    assert backend.embed_query_calls == variant_count
    assert backend.sparse_query_calls == variant_count
    idx.close()


def test_cjk_query_expansion_skips_immediately_in_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIOS_AI_BACKEND", "local")
    sources = (
        WorkspaceAIContextSource(
            source_id="src-1",
            source_scope="notebook",
            source_type="plain_text",
            title="山洋電気 仕様書.pdf",
            privacy_label="local_only",
            text="定格電圧 12V 定格電流 0.60A 冷却ファン",
            included_chars=25,
            truncated=False,
        ),
    )
    with patch("aios_habit.antigravity_bridge.get_antigravity_bridge_health") as mock_health:
        result = _maybe_expand_latin_query_for_cjk_corpus(
            "Thong so quat lam mat Sanyo Denki la gi?",
            sources,
        )
        assert result is None
        mock_health.assert_not_called()


def test_coverage_verify_and_expand_context_use_preloaded_cache(tmp_path: Path) -> None:
    clear_process_lexical_structure_cache()
    db_path = tmp_path / "library_cov.sqlite"
    backend = _CountingHybridBackend()
    idx = LocalChunkIndex(db_path, embedding_backend=backend, sparse_backend=backend)
    chunks = list(_sample_chunks())
    # Add a structured lane document with 2 chunks where only 1 chunk has dense/sparse embeddings
    structured_doc_id = "wsc-8eb2a5d21b75fa88307223b1"
    chunks.extend(
        [
            DocumentChunk(
                chunk_id="chk-struct-01",
                document_id=structured_doc_id,
                source_path="/corpus/lsu/2026_08_Error_BowOverAdjust.csv",
                source_name="2026_08_Error_BowOverAdjust.csv",
                file_type="csv",
                text="Row 1 BowOverAdjust error value 0.12",
                normalized_text="Row 1 BowOverAdjust error value 0.12",
                element_ids=("el-s1",),
                element_types=("table",),
                section_path=("CSV",),
                metadata={"section_path": ["CSV"]},
                privacy_labels=("local_only",),
                source_fingerprint="fp-struct-1",
                checksum="cs-struct-1",
            ),
            DocumentChunk(
                chunk_id="chk-struct-02",
                document_id=structured_doc_id,
                source_path="/corpus/lsu/2026_08_Error_BowOverAdjust.csv",
                source_name="2026_08_Error_BowOverAdjust.csv",
                file_type="csv",
                text="Row 2 BowOverAdjust error value 0.15",
                normalized_text="Row 2 BowOverAdjust error value 0.15",
                element_ids=("el-s1",),
                element_types=("table",),
                section_path=("CSV",),
                metadata={"section_path": ["CSV"]},
                privacy_labels=("local_only",),
                source_fingerprint="fp-struct-1",
                checksum="cs-struct-2",
            ),
        ]
    )
    idx.upsert_chunks(tuple(chunks))
    # Delete one embedding row for the structured lane doc to simulate partial embedding coverage (like 6155 / 22054 in LSU)
    idx._conn.execute("DELETE FROM chunk_embeddings WHERE chunk_id = 'chk-struct-02'")
    idx._conn.execute("DELETE FROM chunk_sparse_embeddings WHERE chunk_id = 'chk-struct-02'")
    idx._conn.commit()
    idx.close()

    clear_process_lexical_structure_cache()
    ro_idx = LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
        read_only=True,
    )
    ro_idx.preload_dense_matrix_cache()
    ro_idx.preload_sparse_vector_cache()
    ro_idx.preload_lexical_structures()

    sql_traced: list[str] = []
    ro_idx._conn.set_trace_callback(sql_traced.append)
    fps = ro_idx.get_document_fingerprints(["doc-lsu-tonly", structured_doc_id])
    cov = ro_idx.verify_selected_document_coverage(
        ["doc-lsu-tonly", structured_doc_id],
        expected_document_fingerprints={
            "doc-lsu-tonly": "fp-tonly-1",
            structured_doc_id: "fp-struct-1",
        },
        sparse_required=True,
    )
    ro_idx._conn.set_trace_callback(None)

    assert fps == {"doc-lsu-tonly": "fp-tonly-1", structured_doc_id: "fp-struct-1"}
    assert cov["valid"] is True
    assert cov["documents_complete"] is True
    assert cov["dense_complete"] is True
    assert cov["sparse_complete"] is True
    # Zero table scans on chunks / chunk_embeddings / chunk_sparse_embeddings when preloaded!
    assert not any("FROM CHUNKS" in s.upper() for s in sql_traced)
    assert not any("CHUNK_EMBEDDINGS" in s.upper() for s in sql_traced)
    assert not any("CHUNK_SPARSE_EMBEDDINGS" in s.upper() for s in sql_traced)

    # Verify expand_context equivalence and caching
    resp = ro_idx.search_with_summary("BowOverAdjust error value", limit=2)
    expanded1 = ro_idx.expand_context(resp, neighbor_window=1, parent_limit=1)
    sql_expand2: list[str] = []
    ro_idx._conn.set_trace_callback(sql_expand2.append)
    expanded2 = ro_idx.expand_context(resp, neighbor_window=1, parent_limit=1)
    ro_idx._conn.set_trace_callback(None)
    assert [r.chunk_id for r in expanded1.results] == [r.chunk_id for r in expanded2.results]
    assert [r.text for r in expanded1.results] == [r.text for r in expanded2.results]
    assert not any("FROM CHUNKS" in s.upper() for s in sql_expand2)
    ro_idx.close()


def test_structured_excel_evidence_bounds_many_workbooks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When >3 managed workbooks exist in a notebook, _try_structured_excel_evidence must not scan unrelated workbooks."""
    from aios_habit.workspace_chat_rag_v2_adapter import _try_structured_excel_evidence

    inspected: list[str] = []
    sources: list[WorkspaceAIContextSource] = []
    for i in range(10):
        wb_path = tmp_path / f"wb_{i}.xlsx"
        wb_path.write_bytes(b"fake-xlsx")
        sources.append(
            WorkspaceAIContextSource(
                source_id=f"src-{i}",
                source_scope="notebook",
                source_type="spreadsheet",
                title=f"Unrelated_Workbook_{i}.xlsx",
                privacy_label="local_only",
                text=f"Dữ liệu báo cáo kho {i}",
                included_chars=25,
                truncated=False,
                managed_path=str(wb_path),
            )
        )

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter._managed_workbook_path",
        lambda src: Path(src.managed_path),
    )

    def _fake_inspect(path: Path, *, document_id: str = "") -> tuple:
        inspected.append(Path(path).name)
        return ()

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.inspect_excel_schemas",
        _fake_inspect,
    )

    res = _try_structured_excel_evidence(
        "Theo báo cáo điều tra lỗi WASE TONNER BOX IS NOT INSTALL.xlsx trên dòng máy Iris2024, dòng 3 là gì?",
        tuple(sources),
    )
    assert res is None
    assert inspected == []

