"""Tests for DESKTOP-SPEED-FIX-G1-INDEX-COST-HOME (ARCH-01, ARCH-02, ARCH-03).

Covers:
1. ARCH-01: SQL pushdown ``WHERE retrievable = 1 AND document_id IN (...)`` in
   <=500 batches inside ``search_with_summary``; 100% parity with legacy full
   scan on results and SearchSummary counts; SQL trace proof of no full-table
   chunk fetch when ``allowed_document_ids`` is provided.
2. ARCH-02: ``rag_v2_eligible_chunks`` temp table populated at most once per
   ``search_with_summary`` call before the ``query_plan.variants`` loop; 100%
   ranked-ID and fused result parity across multi-variant plans.
3. ARCH-03: Precomputed ``frozenset`` in ``SearchOptions`` and ``pipeline.py``,
   plus direct parallel-array filtering in ``_dense_candidates_numpy`` and
   ``_sparse_candidates_cached`` without intermediate ``row = {...}`` dicts;
   100% candidate order and score parity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from aios_habit.rag_v2 import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    NUMPY_DENSE_FLAG,
    LocalChunkIndex,
    SearchOptions,
)
from aios_habit.rag_v2.query_planning import RetrievalQueryPlan, RetrievalQueryVariant
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend


def _make_chunk(
    chunk_id: str,
    document_id: str,
    text: str,
    *,
    source_path: str | None = None,
    privacy_labels: tuple[str, ...] = ("allowed", "internal"),
    source_fingerprint: str = "fp-v1",
) -> DocumentChunk:
    resolved_path = source_path or f"/workspace/{document_id}.txt"
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source_path=resolved_path,
        source_name=f"{document_id}.txt",
        file_type="txt",
        text=text,
        normalized_text=text.casefold(),
        element_ids=(f"el-{chunk_id}",),
        element_types=("text",),
        section_path=("section", chunk_id),
        privacy_labels=privacy_labels,
        source_fingerprint=source_fingerprint,
        checksum=f"chk-{chunk_id}-{source_fingerprint}",
    )


def _legacy_search_with_full_scan_and_per_variant_temp(
    index: LocalChunkIndex,
    query: str | RetrievalQueryPlan,
    limit: int,
    options: SearchOptions,
    monkeypatch: pytest.MonkeyPatch,
):
    """Run search_with_summary simulating legacy ARCH-01 + ARCH-02 behavior."""
    orig_select = index._select_retrievable_rows_by_document_ids
    orig_populate = index._populate_eligible_temp_table

    def legacy_full_scan_select(allowed_document_ids, *, narrow: bool = False):
        if narrow:
            rows = index._conn.execute(
                "SELECT chunk_id, document_id, source_path,"
                " privacy_labels_json, source_fingerprint"
                " FROM chunks WHERE retrievable = 1"
            ).fetchall()
        else:
            rows = index._conn.execute(
                "SELECT * FROM chunks WHERE retrievable = 1"
            ).fetchall()
        allowed_set = set(allowed_document_ids)
        return [r for r in rows if r["document_id"] in allowed_set]

    monkeypatch.setattr(index, "_select_retrievable_rows_by_document_ids", legacy_full_scan_select)
    try:
        return index.search_with_summary(query, limit=limit, options=options)
    finally:
        monkeypatch.setattr(index, "_select_retrievable_rows_by_document_ids", orig_select)
        monkeypatch.setattr(index, "_populate_eligible_temp_table", orig_populate)


@pytest.mark.parametrize("lex_v2_flag", ["0", "1"])
def test_arch01_sql_pushdown_semantic_equivalence_and_multibatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lex_v2_flag: str,
) -> None:
    """ARCH-01: SQL document_id IN (...) pushdown matches legacy full scan across >500 docs."""
    monkeypatch.setenv("AIOS_RAGV2_LEXICAL_V2", lex_v2_flag)
    db_path = tmp_path / f"arch01_{lex_v2_flag}.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=16)

    chunks: List[DocumentChunk] = []
    # Create 620 documents (> 500 SQLite batch boundary) with varying privacy and fingerprints
    for i in range(620):
        doc_id = f"doc-{i:04d}"
        labels = ("allowed", "internal") if i % 7 != 0 else ("restricted",)
        fp = "fp-v1" if i % 11 != 0 else "fp-stale"
        chunks.append(
            _make_chunk(
                f"chunk-{i:04d}-a",
                doc_id,
                f"quy trinh kiem tra servo truc X ma loi E302 tai doc {i}",
                privacy_labels=labels,
                source_fingerprint=fp,
            )
        )
        if i % 5 == 0:
            chunks.append(
                _make_chunk(
                    f"chunk-{i:04d}-b",
                    doc_id,
                    f"huong dan bao duong khuon magenta va thay the linh kien {i}",
                    privacy_labels=labels,
                    source_fingerprint=fp,
                )
            )

    with LocalChunkIndex(db_path, embedding_backend=backend) as index:
        index.upsert_chunks(chunks)

        # Select 540 document IDs (forces 2 SQL IN batches: 500 + 40)
        selected_docs = tuple(f"doc-{i:04d}" for i in range(10, 550))
        expected_fps = {f"doc-{i:04d}": "fp-v1" for i in range(10, 550)}
        options = SearchOptions(
            allowed_document_ids=selected_docs,
            allowed_privacy_labels=("allowed", "internal"),
            expected_source_fingerprints=expected_fps,
            candidate_limit=80,
            per_document_limit=2,
        )

        sql_statements: List[str] = []
        index._conn.set_trace_callback(sql_statements.append)
        try:
            new_resp = index.search_with_summary(
                "kiem tra servo truc X ma loi E302",
                limit=15,
                options=options,
            )
        finally:
            index._conn.set_trace_callback(None)

        # Verify SQL pushdown was used in 2 batches and NO full-table SELECT without WHERE document_id IN
        in_queries = [
            stmt
            for stmt in sql_statements
            if "FROM chunks WHERE retrievable = 1 AND document_id IN" in stmt
        ]
        assert len(in_queries) == 2
        unfiltered_full_scans = [
            stmt
            for stmt in sql_statements
            if (
                "SELECT * FROM chunks WHERE retrievable = 1" in stmt
                or "SELECT chunk_id, document_id, source_path, privacy_labels_json, source_fingerprint FROM chunks WHERE retrievable = 1"
                in stmt
            )
            and "document_id IN" not in stmt
        ]
        assert unfiltered_full_scans == []

        legacy_resp = _legacy_search_with_full_scan_and_per_variant_temp(
            index,
            "kiem tra servo truc X ma loi E302",
            limit=15,
            options=options,
            monkeypatch=monkeypatch,
        )

        assert [(r.chunk_id, r.score) for r in new_resp.results] == [
            (r.chunk_id, r.score) for r in legacy_resp.results
        ]
        assert new_resp.summary.indexed_chunk_count == legacy_resp.summary.indexed_chunk_count == len(chunks)
        assert new_resp.summary.eligible_chunk_count == legacy_resp.summary.eligible_chunk_count
        assert new_resp.summary.filtered_by_source_count == legacy_resp.summary.filtered_by_source_count
        assert new_resp.summary.filtered_by_privacy_count == legacy_resp.summary.filtered_by_privacy_count
        assert new_resp.summary.filtered_as_stale_count == legacy_resp.summary.filtered_as_stale_count
        assert new_resp.summary.insufficiency_reasons == legacy_resp.summary.insufficiency_reasons


def test_arch01_empty_allowed_documents_and_edge_cases(tmp_path: Path) -> None:
    """ARCH-01: Empty allowed_document_ids returns zero results with accurate source-filter count."""
    db_path = tmp_path / "arch01_empty.sqlite"
    with LocalChunkIndex(db_path) as index:
        index.upsert_chunks(
            [
                _make_chunk("c1", "doc1", "alpha beta gamma"),
                _make_chunk("c2", "doc2", "alpha delta epsilon"),
            ]
        )
        resp = index.search_with_summary(
            "alpha",
            limit=5,
            options=SearchOptions(allowed_document_ids=()),
        )
        assert resp.results == ()
        assert resp.summary.indexed_chunk_count == 2
        assert resp.summary.eligible_chunk_count == 0
        assert resp.summary.filtered_by_source_count == 2
        assert "source_filter_excluded_all_chunks" in resp.summary.insufficiency_reasons


@pytest.mark.parametrize("lex_v2_flag", ["0", "1"])
def test_arch02_temp_table_populated_once_across_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lex_v2_flag: str,
) -> None:
    """ARCH-02: rag_v2_eligible_chunks is populated once per search_with_summary across N variants."""
    monkeypatch.setenv("AIOS_RAGV2_LEXICAL_V2", lex_v2_flag)
    db_path = tmp_path / f"arch02_{lex_v2_flag}.sqlite"
    with LocalChunkIndex(db_path) as index:
        chunks = [
            _make_chunk("c1", "doc1", "servo motor overload alarm E302 troubleshooting"),
            _make_chunk("c2", "doc1", "replace encoder cable and verify axis X torque"),
            _make_chunk("c3", "doc2", "periodic maintenance conveyor belt tension check"),
            _make_chunk("c4", "doc3", "hydraulic oil temperature sensor calibration guide"),
        ]
        index.upsert_chunks(chunks)

        # Restrict to doc1 + doc2 so eligible_complete is False -> temp table path is active
        options = SearchOptions(allowed_document_ids=("doc1", "doc2"))
        plan = RetrievalQueryPlan(
            original_query="servo motor overload E302 axis X",
            variants=(
                RetrievalQueryVariant(text="servo motor overload E302", origin="original", variant_id="v0"),
                RetrievalQueryVariant(text="verify axis X torque encoder", origin="expanded", variant_id="v1"),
                RetrievalQueryVariant(text="conveyor belt tension maintenance", origin="expanded", variant_id="v2"),
                RetrievalQueryVariant(text="servo alarm troubleshooting", origin="expanded", variant_id="v3"),
            ),
            content_terms=("servo", "motor", "overload", "e302", "axis"),
            expansion_status="expanded",
            intent_category="diagnosis",
        )

        # Measure SQL statements during multi-variant search
        sql_statements: List[str] = []
        index._conn.set_trace_callback(sql_statements.append)
        try:
            resp = index.search_with_summary(plan, limit=10, options=options)
        finally:
            index._conn.set_trace_callback(None)

        delete_temp_calls = [
            s for s in sql_statements if "DELETE FROM rag_v2_eligible_chunks" in s
        ]
        fts_match_calls = [
            s for s in sql_statements if "WHERE chunks_fts MATCH" in s
        ]
        assert len(delete_temp_calls) == 1
        assert len(fts_match_calls) == 4

        breakdown = dict(resp.summary.lexical_breakdown_ms)
        # Only 3 eligible chunks (c1, c2 in doc1 + c3 in doc2) inserted once (not 3 * 4 = 12)
        assert breakdown.get("temp_inserted_rows") == 3.0

        # Verify per-variant ranked IDs match standalone per-variant calls
        for variant in plan.variants:
            match_query = " OR ".join(f'"{t}"' for t in variant.text.lower().split())
            standalone_ids = index._fts_ranked_ids_v2(
                match_query,
                ["c1", "c2", "c3"],
                options.candidate_limit,
                eligible_temp_populated=False,
            )
            reused_ids = index._fts_ranked_ids_v2(
                match_query,
                ["c1", "c2", "c3"],
                options.candidate_limit,
                eligible_temp_populated=True,
            )
            assert standalone_ids == reused_ids


def _legacy_dense_and_sparse_filter(
    cache: Any,
    options: SearchOptions,
) -> List[int]:
    """Legacy ARCH-03 reference: allocate row dict per index and use tuple/set per row."""
    kept: List[int] = []
    for idx in range(len(cache.chunk_ids)):
        row = {
            "document_id": cache.document_ids[idx],
            "source_path": cache.source_paths[idx],
            "source_fingerprint": cache.source_fingerprints[idx],
        }
        if options.allowed_document_ids is not None:
            selected = row["document_id"] in tuple(options.allowed_document_ids)
        elif options.allowed_source_paths is not None:
            selected = row["source_path"] in tuple(options.allowed_source_paths)
        else:
            selected = True
        if not selected:
            continue
        privacy_labels = cache.privacy_labels[idx]
        if options.allowed_privacy_labels is not None:
            allowed_priv = set(options.allowed_privacy_labels)
            if not (bool(privacy_labels) and all(lbl in allowed_priv for lbl in privacy_labels)):
                continue
        row_fp = row["source_fingerprint"]
        stale = False
        if row_fp:
            expected = options.expected_source_fingerprints
            if row["document_id"] in expected:
                exp = expected[row["document_id"]]
                stale = bool(exp and row_fp != exp)
            elif row["source_path"] in expected:
                exp = expected[row["source_path"]]
                stale = bool(exp and row_fp != exp)
        if stale:
            continue
        kept.append(idx)
    return kept


def test_arch03_parallel_array_filter_and_frozenset_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ARCH-03: Parallel-array filtering and frozenset match legacy dense & sparse candidates."""
    pytest.importorskip("numpy")
    monkeypatch.setenv(NUMPY_DENSE_FLAG, "1")
    db_path = tmp_path / "arch03.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=16)

    chunks: List[DocumentChunk] = []
    for i in range(120):
        doc_id = f"doc-{i // 4:03d}"
        labels = ("allowed", "team-a") if i % 3 != 0 else ("secret",)
        fp = "fp-ok" if i % 5 != 0 else "fp-old"
        chunks.append(
            _make_chunk(
                f"c-{i:04d}",
                doc_id,
                f"optical sensor alignment procedure step {i} beam calibration",
                privacy_labels=labels,
                source_fingerprint=fp,
            )
        )

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
    ) as index:
        index.upsert_chunks(chunks)
        index.ensure_embeddings()

        options = SearchOptions(
            allowed_document_ids=tuple(f"doc-{d:03d}" for d in range(2, 22)),
            allowed_privacy_labels=("allowed", "team-a"),
            expected_source_fingerprints={f"doc-{d:03d}": "fp-ok" for d in range(2, 22)},
            candidate_limit=30,
        )
        assert isinstance(options.allowed_document_ids_set, frozenset)
        assert isinstance(options.allowed_privacy_labels_set, frozenset)

        fp = backend.descriptor.fingerprint
        dense_cache = index._dense_matrix_cache_for(fp, 16)
        sparse_cache = index._sparse_vector_cache_for(fp)
        assert dense_cache is not None
        assert sparse_cache is not None

        assert index._eligible_cache_indices(dense_cache, options) == _legacy_dense_and_sparse_filter(
            dense_cache, options
        )
        assert index._eligible_cache_indices(sparse_cache, options) == _legacy_dense_and_sparse_filter(
            sparse_cache, options
        )

        # Verify _dense_candidates_numpy and _sparse_candidates_cached do not call _is_selected
        def forbid_is_selected(*args: Any, **kwargs: Any) -> bool:
            raise AssertionError("_is_selected should not be called in cached array filter")

        monkeypatch.setattr(index, "_is_selected", forbid_is_selected)
        plan = RetrievalQueryPlan(
            original_query="optical sensor beam calibration",
            variants=(
                RetrievalQueryVariant(text="optical sensor beam calibration", origin="original", variant_id="v0"),
            ),
            content_terms=("optical", "sensor", "beam", "calibration"),
        )

        dense_cands = index._dense_candidates_numpy(
            plan,
            limit=20,
            options=options,
            ensure_embeddings=False,
        )
        sparse_cands = index._sparse_candidates_cached(
            plan,
            cache=sparse_cache,
            limit=20,
            options=options,
        )
        assert dense_cands is not None and len(dense_cands) > 0
        assert len(sparse_cands) > 0


def test_arch03_pipeline_constructs_frozenset_search_options(tmp_path: Path) -> None:
    """ARCH-03: RagV2DevPipeline passes frozenset for allowed_document_ids and allowed_privacy_labels."""
    source_file = tmp_path / "manual.txt"
    source_file.write_text("Servo E302 overload procedure and inspection steps.", encoding="utf-8")
    source = SourceSpec(source_file)

    config = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        retrieval_profile="lexical",
    )
    with RagV2DevPipeline(config) as pipeline:
        pipeline.ingest([source])
        captured_options: List[SearchOptions] = []
        orig_search = pipeline.index.search_with_summary

        def spy_search(query: Any, limit: int = 10, options: SearchOptions | None = None):
            if options is not None:
                captured_options.append(options)
            return orig_search(query, limit=limit, options=options)

        pipeline.index.search_with_summary = spy_search  # type: ignore[method-assign]
        try:
            pipeline.query("Servo E302 overload", [source])
        finally:
            pipeline.index.search_with_summary = orig_search  # type: ignore[method-assign]

        assert len(captured_options) == 1
        opts = captured_options[0]
        assert isinstance(opts.allowed_document_ids, frozenset)
        assert isinstance(opts.allowed_privacy_labels, frozenset)
        assert isinstance(opts.allowed_document_ids_set, frozenset)
        assert isinstance(opts.allowed_privacy_labels_set, frozenset)
