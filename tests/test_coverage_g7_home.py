"""Tests for G7 coverage & document fingerprint cache by _index_cache_token() (ARCH-15).

Ticket: DESKTOP-SPEED-FIX-G7-COVERAGE-HOME
Covers:
1. Missing embeddings fail-closed control test (verify_selected_document_coverage & RagV2DevPipeline.query).
2. Complete index exact dict equivalence against legacy SHA-256 content_hash scan.
3. LSU structured lane exemption (STRUCTURED_LANE_DOCUMENT_IDS) preservation in read_only=True/False.
4. Token-keyed caching (0 SQL queries on warm repeat turn, invalidation on _index_cache_token() change).
5. Safe 500-item SQL IN (...) batching for >1,000 document/chunk IDs.
6. coverage_verify_ms propagation to SearchSummary, RagV2QueryResult, worker IPC, and [RETRIEVAL_MICRO_TIMING].
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Mapping, Sequence
from unittest.mock import MagicMock

import pytest

from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus
from aios_habit.rag_v2.bge_subprocess_worker import _serialize_query_result
from aios_habit.rag_v2.chunking import StructureAwareChunker
from aios_habit.rag_v2.index import (
    LocalChunkIndex,
    STRUCTURED_LANE_DOCUMENT_IDS,
    _embedding_content_hash,
)
from aios_habit.rag_v2.pipeline import (
    RagV2DevConfig,
    RagV2DevPipeline,
    SourceSpec,
)
from aios_habit.rag_v2.semantic import (
    DeterministicEmbeddingBackend,
    MultiVectorDescriptor,
    SemanticBackendUnavailable,
    SemanticCapability,
)


class _MultiVectorTestBackend(DeterministicEmbeddingBackend):
    @property
    def multivector_capability(self) -> SemanticCapability:
        return SemanticCapability(
            capability="multivector_embedding",
            available=True,
            backend="deterministic-test",
            model=self.descriptor,
        )

    @property
    def multivector_descriptor(self) -> MultiVectorDescriptor:
        return MultiVectorDescriptor(
            model_fingerprint=self.descriptor.fingerprint,
            dimension=self.descriptor.dimension,
            max_tokens=8,
        )

    def multivector_documents(self, texts: Sequence[str]):
        return tuple((self._embed(text),) for text in texts)

    def multivector_query(self, text: str):
        return (self._embed(text),)


def _legacy_verify_selected_document_coverage(
    index: LocalChunkIndex,
    document_ids: Sequence[str],
    *,
    expected_document_fingerprints: Mapping[str, str] | None = None,
    sparse_required: bool = False,
    multivector_required: bool = False,
) -> Dict[str, Any]:
    """Reference implementation of pre-G7 verify_selected_document_coverage for equivalence testing."""
    selected = tuple(
        dict.fromkeys(
            str(document_id).strip()
            for document_id in document_ids
            if str(document_id).strip()
        )
    )
    expected = (
        {str(key): str(value) for key, value in expected_document_fingerprints.items()}
        if expected_document_fingerprints is not None
        else {}
    )
    if not selected:
        return {
            "valid": False,
            "reason": "no_selected_documents",
            "document_count": 0,
            "retrievable_chunk_count": 0,
            "dense_embedding_count": 0,
            "sparse_embedding_count": 0,
            "multivector_embedding_count": 0,
            "dense_complete": False,
            "sparse_complete": not sparse_required,
            "multivector_complete": not multivector_required,
            "documents_complete": False,
        }
    placeholders = ",".join("?" for _ in selected)
    rows = index._conn.execute(
        f"""
        SELECT document_id,
               MIN(source_fingerprint) AS min_fingerprint,
               MAX(source_fingerprint) AS max_fingerprint,
               COUNT(*) AS chunk_count
        FROM chunks
        WHERE retrievable = 1 AND document_id IN ({placeholders})
        GROUP BY document_id
        """,
        selected,
    ).fetchall()
    actual_fingerprints = {
        str(row["document_id"]): (
            str(row["min_fingerprint"])
            if row["min_fingerprint"] is not None
            and row["min_fingerprint"] == row["max_fingerprint"]
            else ""
        )
        for row in rows
    }
    missing_document_ids = tuple(sorted(set(selected) - set(actual_fingerprints)))
    fingerprint_mismatch_document_ids = tuple(
        sorted(
            document_id
            for document_id, fingerprint in expected.items()
            if document_id in set(selected)
            and fingerprint != ""
            and actual_fingerprints.get(document_id) != fingerprint
        )
    )
    documents_complete = not missing_document_ids and not fingerprint_mismatch_document_ids
    retrievable_chunk_count = sum(int(row["chunk_count"]) for row in rows)
    backend = index._embedding_backend
    assert backend is not None
    descriptor = backend.descriptor
    dense_rows = index._conn.execute(
        f"""
        SELECT c.document_id, c.text, e.content_hash
        FROM chunks AS c
        JOIN chunk_embeddings AS e ON e.chunk_id = c.chunk_id
        WHERE c.retrievable = 1
          AND c.document_id IN ({placeholders})
          AND e.model_fingerprint = ?
        """,
        (*selected, descriptor.fingerprint),
    ).fetchall()
    dense_embedding_count = sum(
        str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
        for row in dense_rows
    )
    sparse_embedding_count = 0
    sparse_rows = []
    if sparse_required:
        sparse_rows = index._conn.execute(
            f"""
            SELECT c.document_id, c.text, s.content_hash
            FROM chunks AS c
            JOIN chunk_sparse_embeddings AS s ON s.chunk_id = c.chunk_id
            WHERE c.retrievable = 1
              AND c.document_id IN ({placeholders})
              AND s.model_fingerprint = ?
            """,
            (*selected, descriptor.fingerprint),
        ).fetchall()
        sparse_embedding_count = sum(
            str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
            for row in sparse_rows
        )
    multivector_embedding_count = 0
    if multivector_required:
        multivector_backend = index._multivector_backend
        multivector_descriptor = (
            multivector_backend.multivector_descriptor
            if multivector_backend is not None
            and multivector_backend.multivector_capability.available
            else None
        )
        if multivector_descriptor is not None:
            multivector_rows = index._conn.execute(
                f"""
                SELECT c.document_id, c.text, m.content_hash, m.representation_fingerprint
                FROM chunks AS c
                JOIN chunk_multivector_embeddings AS m ON m.chunk_id = c.chunk_id
                WHERE c.retrievable = 1
                  AND c.document_id IN ({placeholders})
                  AND m.model_fingerprint = ?
                """,
                (*selected, descriptor.fingerprint),
            ).fetchall()
            multivector_embedding_count = sum(
                str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
                and str(row["representation_fingerprint"])
                == multivector_descriptor.fingerprint
                for row in multivector_rows
            )
    semantic_required_chunk_count = sum(
        int(row["chunk_count"])
        for row in rows
        if str(row["document_id"]) not in STRUCTURED_LANE_DOCUMENT_IDS
    )
    semantic_dense_count = sum(
        str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
        for row in dense_rows
        if str(row["document_id"]) not in STRUCTURED_LANE_DOCUMENT_IDS
    )
    dense_complete = (
        semantic_dense_count == semantic_required_chunk_count
        if semantic_required_chunk_count > 0
        else True
    )
    if sparse_required:
        semantic_sparse_count = sum(
            str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
            for row in sparse_rows
            if str(row["document_id"]) not in STRUCTURED_LANE_DOCUMENT_IDS
        )
        sparse_complete = (
            semantic_sparse_count == semantic_required_chunk_count
            if semantic_required_chunk_count > 0
            else True
        )
    else:
        sparse_complete = True
    multivector_complete = (
        not multivector_required
        or multivector_embedding_count == retrievable_chunk_count
    )
    return {
        "valid": bool(
            documents_complete
            and retrievable_chunk_count > 0
            and dense_complete
            and sparse_complete
            and multivector_complete
        ),
        "reason": "" if documents_complete else "document_identity_mismatch",
        "document_count": len(actual_fingerprints),
        "retrievable_chunk_count": retrievable_chunk_count,
        "missing_document_ids": missing_document_ids,
        "fingerprint_mismatch_document_ids": fingerprint_mismatch_document_ids,
        "documents_complete": documents_complete,
        "model_fingerprint": descriptor.fingerprint,
        "dense_embedding_count": dense_embedding_count,
        "sparse_embedding_count": sparse_embedding_count,
        "multivector_embedding_count": multivector_embedding_count,
        "dense_complete": dense_complete,
        "sparse_complete": sparse_complete,
        "multivector_complete": multivector_complete,
    }


def _make_chunk(doc_id: str, idx: int, text: str, fp: str = "fp-01"):
    chunker = StructureAwareChunker(max_chars=300)
    el = DocumentElement(
        element_id=f"el-{doc_id}-{idx}",
        document_id=doc_id,
        source_path=f"C:/docs/{doc_id}.txt",
        source_name=f"{doc_id}.txt",
        file_type="txt",
        extractor="unit",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text=text,
        privacy_labels=("local_only",),
        source_fingerprint=fp,
        page=1,
    )
    return chunker.chunk_elements([el])[0]


def test_g7_complete_index_exact_equivalence_and_missing_embeddings_fail_closed(tmp_path: Path):
    """Control test: complete index matches legacy coverage dict 100%; missing dense/sparse fails closed."""
    db_path = tmp_path / "library.sqlite"
    backend = _MultiVectorTestBackend(dimension=8)
    doc_ids = ["doc-alpha", "doc-beta", "doc-gamma"]
    exempt_doc_id = next(iter(STRUCTURED_LANE_DOCUMENT_IDS))

    chunks = [
        _make_chunk("doc-alpha", 1, "Alpha chunk one content for testing", "fp-alpha"),
        _make_chunk("doc-alpha", 2, "Alpha chunk two content for testing", "fp-alpha"),
        _make_chunk("doc-beta", 1, "Beta chunk one content for testing", "fp-beta"),
        _make_chunk("doc-gamma", 1, "Gamma chunk one content for testing", "fp-gamma"),
        _make_chunk(exempt_doc_id, 1, "Exempt structured CSV row content", "fp-exempt"),
    ]

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
        multivector_backend=backend,
    ) as writable_index:
        writable_index.upsert_chunks(chunks)
        # Remove embeddings for exempt structured doc to verify exemption equivalence
        writable_index._conn.execute(
            "DELETE FROM chunk_embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE document_id = ?)",
            (exempt_doc_id,),
        )
        writable_index._conn.execute(
            "DELETE FROM chunk_sparse_embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE document_id = ?)",
            (exempt_doc_id,),
        )
        writable_index._conn.commit()

    all_selected = [*doc_ids, exempt_doc_id]
    expected_fps = {
        "doc-alpha": "fp-alpha",
        "doc-beta": "fp-beta",
        "doc-gamma": "fp-gamma",
        exempt_doc_id: "fp-exempt",
    }

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
        multivector_backend=backend,
        read_only=True,
        ensure_embeddings_on_open=False,
    ) as ro_index:
        actual = ro_index.verify_selected_document_coverage(
            all_selected,
            expected_document_fingerprints=expected_fps,
            sparse_required=True,
            multivector_required=False,
        )
        legacy = _legacy_verify_selected_document_coverage(
            ro_index,
            all_selected,
            expected_document_fingerprints=expected_fps,
            sparse_required=True,
            multivector_required=False,
        )
        assert actual == legacy
        assert actual["valid"] is True
        assert actual["dense_complete"] is True
        assert actual["sparse_complete"] is True

        # Also verify multivector_required=True on non-exempt docs matches legacy
        actual_mv = ro_index.verify_selected_document_coverage(
            doc_ids,
            expected_document_fingerprints={k: expected_fps[k] for k in doc_ids},
            sparse_required=True,
            multivector_required=True,
        )
        legacy_mv = _legacy_verify_selected_document_coverage(
            ro_index,
            doc_ids,
            expected_document_fingerprints={k: expected_fps[k] for k in doc_ids},
            sparse_required=True,
            multivector_required=True,
        )
        assert actual_mv == legacy_mv
        assert actual_mv["valid"] is True
        assert actual_mv["multivector_complete"] is True

        # Fingerprint mismatch check matches legacy
        bad_fps = {**expected_fps, "doc-beta": "fp-wrong"}
        actual_mismatch = ro_index.verify_selected_document_coverage(
            all_selected,
            expected_document_fingerprints=bad_fps,
            sparse_required=True,
        )
        legacy_mismatch = _legacy_verify_selected_document_coverage(
            ro_index,
            all_selected,
            expected_document_fingerprints=bad_fps,
            sparse_required=True,
        )
        assert actual_mismatch == legacy_mismatch
        assert actual_mismatch["valid"] is False
        assert actual_mismatch["fingerprint_mismatch_document_ids"] == ("doc-beta",)

        # Missing document check matches legacy
        with_missing = [*all_selected, "doc-nonexistent"]
        actual_missing_doc = ro_index.verify_selected_document_coverage(
            with_missing,
            expected_document_fingerprints=expected_fps,
            sparse_required=True,
        )
        legacy_missing_doc = _legacy_verify_selected_document_coverage(
            ro_index,
            with_missing,
            expected_document_fingerprints=expected_fps,
            sparse_required=True,
        )
        assert actual_missing_doc == legacy_missing_doc
        assert actual_missing_doc["valid"] is False
        assert actual_missing_doc["missing_document_ids"] == ("doc-nonexistent",)

    # Now delete one sparse embedding from a non-exempt doc -> must fail sparse_complete
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "DELETE FROM chunk_sparse_embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE document_id = 'doc-gamma')"
    )
    conn.commit()
    conn.close()

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
        read_only=True,
        ensure_embeddings_on_open=False,
    ) as ro_index_incomplete_sparse:
        cov_sparse = ro_index_incomplete_sparse.verify_selected_document_coverage(
            all_selected,
            expected_document_fingerprints=expected_fps,
            sparse_required=True,
        )
        legacy_sparse = _legacy_verify_selected_document_coverage(
            ro_index_incomplete_sparse,
            all_selected,
            expected_document_fingerprints=expected_fps,
            sparse_required=True,
        )
        assert cov_sparse == legacy_sparse
        assert cov_sparse["valid"] is False
        assert cov_sparse["dense_complete"] is True
        assert cov_sparse["sparse_complete"] is False

    # Now delete one dense embedding from doc-alpha -> must fail dense_complete and raise in pipeline.query
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "DELETE FROM chunk_embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE document_id = 'doc-alpha' LIMIT 1)"
    )
    conn.commit()
    conn.close()

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
        read_only=True,
        ensure_embeddings_on_open=False,
    ) as ro_index_incomplete_dense:
        cov_dense = ro_index_incomplete_dense.verify_selected_document_coverage(
            all_selected,
            expected_document_fingerprints=expected_fps,
            sparse_required=False,
        )
        legacy_dense = _legacy_verify_selected_document_coverage(
            ro_index_incomplete_dense,
            all_selected,
            expected_document_fingerprints=expected_fps,
            sparse_required=False,
        )
        assert cov_dense == legacy_dense
        assert cov_dense["valid"] is False
        assert cov_dense["dense_complete"] is False


def test_g7_warm_cache_zero_sql_queries_and_invalidation_on_token_change(tmp_path: Path):
    """Verify 0 SQL queries on warm repeat turn and immediate invalidation when _index_cache_token() changes."""
    source_paths = []
    sources = []
    for i in range(12):
        p = tmp_path / f"doc_{i}.txt"
        p.write_text(f"Document {i} operational manual procedure step {i} for Matecon.", encoding="utf-8")
        source_paths.append(p)
        sources.append(SourceSpec(p, document_id=f"doc-{i:03d}"))

    runtime_root = tmp_path / "runtime"
    embedding = DeterministicEmbeddingBackend(dimension=8)
    writable_cfg = RagV2DevConfig(
        runtime_root=runtime_root,
        retrieval_profile="bge_m3_hybrid",
        strict_semantic=True,
    )
    with RagV2DevPipeline(writable_cfg, embedding_backend=embedding) as writable_pipe:
        writable_pipe.ingest(sources)

    ro_cfg = RagV2DevConfig(
        runtime_root=runtime_root,
        retrieval_profile="bge_m3_hybrid",
        strict_semantic=True,
        index_read_only=True,
        ensure_embeddings_on_open=False,
    )
    with RagV2DevPipeline(ro_cfg, embedding_backend=embedding) as ro_pipe:
        doc_ids = [s.document_id for s in sources]
        # Turn 1: cold populate
        fps_1 = ro_pipe.index.get_document_fingerprints(doc_ids)
        cov_1 = ro_pipe.index.verify_selected_document_coverage(
            doc_ids,
            expected_document_fingerprints={k: v or "" for k, v in fps_1.items()},
            sparse_required=True,
        )
        assert cov_1["valid"] is True

        # Trace SQL statements on Turn 2 (excluding PRAGMA data_version in _index_cache_token)
        sql_statements: list[str] = []
        ro_pipe.index._conn.set_trace_callback(sql_statements.append)
        try:
            t0 = perf_counter()
            fps_2 = ro_pipe.index.get_document_fingerprints(doc_ids)
            cov_2 = ro_pipe.index.verify_selected_document_coverage(
                doc_ids,
                expected_document_fingerprints={k: v or "" for k, v in fps_2.items()},
                sparse_required=True,
            )
            # Also verify a subset of documents uses cached per-document counts without SQL
            cov_subset = ro_pipe.index.verify_selected_document_coverage(
                doc_ids[:4],
                expected_document_fingerprints={k: fps_2[k] or "" for k in doc_ids[:4]},
                sparse_required=True,
            )
            warm_ms = (perf_counter() - t0) * 1000.0
        finally:
            ro_pipe.index._conn.set_trace_callback(None)

        non_pragma_sql = [
            stmt for stmt in sql_statements if "PRAGMA data_version" not in stmt
        ]
        assert non_pragma_sql == [], f"Expected 0 non-PRAGMA SQL queries on warm turn, got: {non_pragma_sql}"
        assert fps_2 == fps_1
        assert cov_2 == cov_1
        assert cov_subset["valid"] is True
        assert cov_subset["document_count"] == 4
        assert warm_ms < 5.0

        # Simulate external process write that bumps PRAGMA data_version
        ext_conn = sqlite3.connect(str(ro_pipe.config.index_path))
        ext_conn.execute(
            "DELETE FROM chunk_embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE document_id = 'doc-000')"
        )
        ext_conn.commit()
        ext_conn.close()

        # Next coverage verification must detect the token change, invalidate cache, and fail closed
        cov_after_write = ro_pipe.index.verify_selected_document_coverage(
            doc_ids,
            expected_document_fingerprints={k: v or "" for k, v in fps_1.items()},
            sparse_required=True,
        )
        assert cov_after_write["valid"] is False
        assert cov_after_write["dense_complete"] is False

        with pytest.raises(SemanticBackendUnavailable, match="semantic_index_coverage_incomplete"):
            ro_pipe.query("operational manual procedure", sources)


def test_g7_batching_over_1200_documents_and_chunks(tmp_path: Path):
    """Verify >1,200 documents/chunks are safely batched in 500-placeholder chunks."""
    db_path = tmp_path / "large_batch.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=8)
    chunks = [
        _make_chunk(f"doc-{i:04d}", 1, f"Content for document number {i}", f"fp-{i:04d}")
        for i in range(1205)
    ]
    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
    ) as writable_index:
        writable_index.upsert_chunks(chunks)

    doc_ids = [f"doc-{i:04d}" for i in range(1205)]
    chunk_ids = [c.chunk_id for c in chunks]

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
        read_only=True,
        ensure_embeddings_on_open=False,
    ) as ro_index:
        fps = ro_index.get_document_fingerprints(doc_ids)
        assert len(fps) == 1205
        assert fps["doc-0000"] == "fp-0000"
        assert fps["doc-1204"] == "fp-1204"

        cov = ro_index.verify_selected_document_coverage(
            doc_ids,
            expected_document_fingerprints={k: v or "" for k, v in fps.items()},
            sparse_required=True,
        )
        assert cov["valid"] is True
        assert cov["document_count"] == 1205
        assert cov["retrievable_chunk_count"] == 1205
        assert cov["dense_embedding_count"] == 1205
        assert cov["sparse_embedding_count"] == 1205

        rows_by_id = ro_index._chunk_rows_by_id(chunk_ids)
        assert len(rows_by_id) == 1205


def test_g7_coverage_verify_ms_propagates_to_summary_worker_and_micro_timing(monkeypatch, tmp_path: Path):
    """Verify coverage_verify_ms is recorded on SearchSummary, serialized by worker, and emitted in [RETRIEVAL_MICRO_TIMING]."""
    p = tmp_path / "manual.txt"
    p.write_text("Manual Matecon procedure uses ctrlMode one before startup.", encoding="utf-8")
    source = SourceSpec(p, document_id="matecon-doc")
    runtime_root = tmp_path / "runtime"
    embedding = DeterministicEmbeddingBackend(dimension=8)

    writable_cfg = RagV2DevConfig(
        runtime_root=runtime_root,
        retrieval_profile="bge_m3_hybrid",
        strict_semantic=True,
    )
    with RagV2DevPipeline(writable_cfg, embedding_backend=embedding) as writable_pipe:
        writable_pipe.ingest([source])

    ro_cfg = RagV2DevConfig(
        runtime_root=runtime_root,
        retrieval_profile="bge_m3_hybrid",
        strict_semantic=True,
        index_read_only=True,
        ensure_embeddings_on_open=False,
    )
    with RagV2DevPipeline(ro_cfg, embedding_backend=embedding) as ro_pipe:
        res1 = ro_pipe.query("How does Manual Matecon work?", [source])
        res2 = ro_pipe.query("How does Manual Matecon work?", [source])
        assert res1.coverage_verify_ms >= 0.0
        assert res1.search_response.summary.coverage_verify_ms == pytest.approx(res1.coverage_verify_ms)
        assert res2.coverage_verify_ms >= 0.0
        serialized = _serialize_query_result(res1)
        assert "coverage_verify_ms" in serialized["summary"]
        assert serialized["summary"]["coverage_verify_ms"] == pytest.approx(res1.coverage_verify_ms)

    # Also verify adapter _run_profile emits coverage_verify_ms in [RETRIEVAL_MICRO_TIMING]
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
    from aios_habit.workspace_chat_rag_v2_adapter import (
        WorkspaceChatRagV2CanaryConfig,
        _PREPARATION_READY_STATE,
        _SUBPROCESS_CLIENT,
        _run_profile,
    )

    printed_markers: list[str] = []
    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter._safe_print_streaming_marker",
        printed_markers.append,
    )
    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.get_workspace_chat_source_preparation_status",
        lambda sources, config=None: {f"{s.source_scope}:{s.source_id}": _PREPARATION_READY_STATE for s in sources},
    )
    monkeypatch.setattr(_SUBPROCESS_CLIENT, "_persistent_applies", lambda cfg: True)
    monkeypatch.setattr(_SUBPROCESS_CLIENT, "is_ready", lambda cfg: True)
    monkeypatch.setattr(
        _SUBPROCESS_CLIENT,
        "query_ready",
        lambda *args, **kwargs: {
            "summary": {
                "candidate_count": 3,
                "returned_count": 1,
                "filtered_as_stale_count": 0,
                "indexed_chunk_count": 10,
                "pipe_wait_ms": 0.42,
                "coverage_verify_ms": 0.18,
                "embed_latency_ms": 210.0,
                "embed_wait_ms": 0.0,
                "embed_compute_ms": 210.0,
                "dense_latency_ms": 12.5,
                "sparse_latency_ms": 8.0,
                "fusion_latency_ms": 3.2,
                "dense_resident": True,
                "dense_load_latency_ms": 0.0,
            },
            "items": [
                {
                    "document_id": "wsc-doc-1",
                    "text": "Sample evidence text",
                    "score": 0.95,
                    "citation_id": "cit-1",
                    "evidence_id": "ev-1",
                }
            ],
            "insufficiency_reasons": [],
            "routing": {"effective_path": "hybrid"},
            "synthesis": {"answer": "Ans", "citation_ids": ["cit-1"], "grounded": True, "abstained": False},
        },
    )

    model_dir = tmp_path / "model"
    model_dir.mkdir(exist_ok=True)
    cfg = WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        requested_profile="bge_m3_hybrid",
        runtime_root=tmp_path / "adapter_runtime",
        bge_m3_model_path=model_dir,
        bge_m3_model_revision="rev1",
        bge_m3_model_checksum="chk1",
    )
    ctx_source = WorkspaceAIContextSource(
        source_id="src-1",
        source_scope="notebook",
        source_type="plain_text",
        title="Doc 1",
        privacy_label="local_only",
        text="Sample evidence text",
        included_chars=20,
        truncated=False,
    )
    mapped = _run_profile(
        question="Test coverage_verify_ms marker",
        sources=(ctx_source,),
        config=cfg,
        profile="bge_m3_hybrid",
        fallback_reason="",
        pipeline_factory=MagicMock(),
        domain_collection_id="lsu",
    )
    assert mapped["rag_v2_canary"]["coverage_verify_ms"] == pytest.approx(0.18)
    micro_markers = [m for m in printed_markers if "[RETRIEVAL_MICRO_TIMING]" in m]
    assert len(micro_markers) == 1
    assert "coverage_verify_ms=0.18" in micro_markers[0]
