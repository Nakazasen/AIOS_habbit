import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    HybridRankingConfig,
    LocalChunkIndex,
    SearchOptions,
    SearchResponse,
    SearchResult,
    SearchSummary,
    fuse_ranked_channels,
)
from aios_habit.rag_v2.retrieval_backends import BgeM3Backend
from aios_habit.rag_v2.semantic import (
    DeterministicEmbeddingBackend,
    DeterministicRerankerBackend,
    FastEmbedRerankerBackend,
    MultiVectorDescriptor,
    SemanticBackendError,
    SemanticBackendUnavailable,
    SemanticModelDescriptor,
    late_interaction_maxsim,
    normalize_vector,
    unavailable_embedding_backend,
)


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
        section_path=(),
        privacy_labels=labels,
        source_fingerprint=fingerprint,
        checksum=f"checksum-{chunk_id}-{fingerprint}",
    )


def test_context_only_parent_is_never_embedded_or_dense_ranked(tmp_path):
    child = make_chunk("child", "doc", "semantic target child")
    parent = DocumentChunk(
        chunk_id="parent",
        document_id="doc",
        source_path=child.source_path,
        source_name=child.source_name,
        file_type=child.file_type,
        text="semantic target child plus the complete raw parent context",
        normalized_text="semantic target child plus the complete raw parent context",
        element_ids=("element-parent",),
        element_types=("text",),
        privacy_labels=child.privacy_labels,
        source_fingerprint=child.source_fingerprint,
        checksum="checksum-parent",
        retrievable=False,
        metadata={"representation_role": "parent", "retrievable": False},
    )
    backend = DeterministicEmbeddingBackend(dimension=8)

    with LocalChunkIndex(tmp_path / "parent.sqlite", embedding_backend=backend) as index:
        assert index.upsert_chunks([child, parent]) == 1
        candidates = index.dense_candidates("semantic target", limit=10)
        status = index.embedding_status()

        assert index._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 2
        assert index._conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 1

    assert backend.embedded_document_count == 1
    assert status["embedded_chunk_count"] == 1
    assert [candidate.chunk_id for candidate in candidates] == ["child"]


def test_embedding_cache_persists_and_skips_unchanged_chunks_after_reopen(tmp_path):
    db_path = tmp_path / "index.sqlite"
    chunk = make_chunk("stable", "doc", "semantic cache survives reopen")
    first_backend = DeterministicEmbeddingBackend(dimension=8)

    with LocalChunkIndex(db_path, embedding_backend=first_backend) as index:
        assert index.upsert_chunks([chunk]) == 1
        assert first_backend.embedded_document_count == 1
        assert index.embedding_status()["embedded_chunk_count"] == 1

    second_backend = DeterministicEmbeddingBackend(dimension=8)
    with LocalChunkIndex(db_path, embedding_backend=second_backend) as index:
        assert second_backend.embedded_document_count == 0
        assert index.replace_document_chunks("doc", [chunk]) == 1
        assert second_backend.embedded_document_count == 0
        status = index.embedding_status()

    assert status["embedded_chunk_count"] == 1
    assert status["model"]["fingerprint"] == second_backend.descriptor.fingerprint


def test_embedding_status_supports_legacy_read_only_index_without_multivector_table(tmp_path):
    db_path = tmp_path / "legacy.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=8)

    with LocalChunkIndex(db_path, embedding_backend=backend):
        pass
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE chunk_multivector_embeddings")

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        ensure_embeddings_on_open=False,
        read_only=True,
    ) as index:
        status = index.embedding_status()

    assert status["embedded_chunk_count"] == 0
    assert status["sparse_embedded_chunk_count"] == 0
    assert status["multivector_embedded_chunk_count"] == 0
    assert status["multivector_ready"] is False


def test_embedding_cache_invalidates_changed_content_and_isolates_models(tmp_path):
    db_path = tmp_path / "index.sqlite"
    old = make_chunk("stable", "doc", "old semantic content")
    changed = make_chunk("stable", "doc", "changed semantic content", fingerprint="v2")
    first_backend = DeterministicEmbeddingBackend(dimension=8, model_id="test/model-a")

    with LocalChunkIndex(db_path, embedding_backend=first_backend) as index:
        index.upsert_chunks([old])
        index.replace_document_chunks("doc", [changed])
        assert first_backend.embedded_document_count == 2
        assert index._conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 1

    second_backend = DeterministicEmbeddingBackend(dimension=8, model_id="test/model-b")
    with LocalChunkIndex(db_path, embedding_backend=second_backend) as index:
        assert second_backend.embedded_document_count == 1
        rows = index._conn.execute(
            "SELECT model_fingerprint FROM chunk_embeddings ORDER BY model_fingerprint"
        ).fetchall()
        assert {row[0] for row in rows} == {
            first_backend.descriptor.fingerprint,
            second_backend.descriptor.fingerprint,
        }


def test_embedding_rows_cascade_with_chunk_lifecycle(tmp_path):
    backend = DeterministicEmbeddingBackend(dimension=8)
    with LocalChunkIndex(tmp_path / "index.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks([make_chunk("one", "doc", "one semantic record")])
        assert index._conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 1
        assert index.delete_document("doc") == 1
        assert index._conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 0


def test_dense_candidates_apply_source_privacy_and_staleness_filters(tmp_path):
    backend = DeterministicEmbeddingBackend(dimension=16)
    chunks = [
        make_chunk("allowed", "safe", "semantic target", labels=("allowed",)),
        make_chunk("private", "blocked", "semantic target", labels=("restricted",)),
        make_chunk("stale", "old", "semantic target", labels=("allowed",), fingerprint="old"),
    ]
    options = SearchOptions(
        allowed_privacy_labels=("allowed",),
        allowed_document_ids=("safe", "old"),
        expected_source_fingerprints={"old": "current"},
    )

    with LocalChunkIndex(tmp_path / "index.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks(chunks)
        first = index.dense_candidates("semantic target", options=options)
        second = index.dense_candidates("semantic target", options=options)

    assert [result.chunk_id for result in first] == ["allowed"]
    assert first == second
    assert first[0].ranking_signals["dense_cosine"] == pytest.approx(1.0)
    assert "dense_multi_variant_rrf" in first[0].ranking_signals


def test_unavailable_semantic_backend_is_explicit_and_never_fakes_dense_scores(tmp_path):
    backend = unavailable_embedding_backend(
        "missing/model",
        dimension=8,
        reason="model is not cached locally",
    )
    with LocalChunkIndex(tmp_path / "index.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks([make_chunk("one", "doc", "semantic text")])
        status = index.embedding_status()
        lexical = index.search("semantic")
        with pytest.raises(SemanticBackendUnavailable, match="not cached"):
            index.dense_candidates("semantic")

    assert status["configured"] is True
    assert status["available"] is False
    assert status["embedded_chunk_count"] == 0
    assert [result.chunk_id for result in lexical] == ["one"]


def test_model_descriptor_fingerprint_changes_with_vector_contract():
    baseline = SemanticModelDescriptor(model_id="model", dimension=8, revision="v1")
    changed_revision = SemanticModelDescriptor(model_id="model", dimension=8, revision="v2")
    changed_dimension = SemanticModelDescriptor(model_id="model", dimension=16, revision="v1")

    assert baseline.fingerprint != changed_revision.fingerprint
    assert baseline.fingerprint != changed_dimension.fingerprint
    assert baseline.to_safe_dict()["cache_identity"] == baseline.fingerprint


def test_embedding_failure_rolls_back_chunk_and_vector_mutation(tmp_path):
    class FailingBackend(DeterministicEmbeddingBackend):
        def embed_documents(self, texts):
            del texts
            raise RuntimeError("synthetic embedding failure")

    backend = FailingBackend(dimension=8)
    with LocalChunkIndex(tmp_path / "index.sqlite", embedding_backend=backend) as index:
        with pytest.raises(RuntimeError, match="synthetic embedding failure"):
            index.upsert_chunks([make_chunk("one", "doc", "must rollback")])

        assert index.count() == 0
        assert index._conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 0


def test_bge_m3_pending_sparse_cache_supports_duplicate_document_texts():
    class FakeBgeM3Model:
        def __init__(self):
            self.calls = []

        def encode(
            self, texts, *, batch_size, max_length,
            return_dense, return_sparse, return_colbert_vecs,
        ):
            self.calls.append((tuple(texts), return_dense, return_sparse))
            assert batch_size == 3
            assert max_length == 128
            assert return_colbert_vecs is False
            output = {}
            if return_dense:
                output["dense_vecs"] = [(1.0, 0.0) for _ in texts]
            if return_sparse:
                output["lexical_weights"] = [{"7": 1.0} for _ in texts]
            return output

    model = FakeBgeM3Model()
    backend = object.__new__(BgeM3Backend)
    backend._model = model
    backend._batch_size = 3
    backend._max_length = 128
    backend._descriptor = SemanticModelDescriptor(
        model_id="test/bge-m3", revision="pinned", dimension=2,
    )
    backend._pending_sparse = {}
    texts = ("duplicate chunk", "duplicate chunk", "unique chunk")

    dense = backend.embed_documents(texts)
    sparse = backend.sparse_documents(texts)

    assert len(dense) == len(texts)
    assert sparse == ({"7": 1.0}, {"7": 1.0}, {"7": 1.0})
    assert model.calls == [(texts, True, True)]
    assert backend._pending_sparse == {}


def test_bge_m3_multivector_reuses_one_encode_pass_for_all_representations():
    class FakeBgeM3Model:
        def __init__(self):
            self.calls = []

        def encode(
            self, texts, *, batch_size, max_length,
            return_dense, return_sparse, return_colbert_vecs,
        ):
            self.calls.append((tuple(texts), return_colbert_vecs))
            return {
                "dense_vecs": [(1.0, 0.0) for _ in texts],
                "lexical_weights": [{"11": 1.0} for _ in texts],
                "colbert_vecs": [[(1.0, 0.0), (0.0, 1.0)] for _ in texts],
            }

    model = FakeBgeM3Model()
    backend = object.__new__(BgeM3Backend)
    backend._model = model
    backend._batch_size = 2
    backend._max_length = 16
    backend._enable_multivector = True
    backend._descriptor = SemanticModelDescriptor(
        model_id="test/bge-m3", revision="pinned", dimension=2,
    )
    backend._multivector_descriptor = MultiVectorDescriptor(
        model_fingerprint=backend._descriptor.fingerprint,
        dimension=2,
        max_tokens=16,
    )
    backend._pending_sparse = {}
    backend._pending_multivector = {}
    backend._pending_queries = {}
    texts = ("first chunk", "second chunk")

    dense = backend.embed_documents(texts)
    sparse = backend.sparse_documents(texts)
    multivectors = backend.multivector_documents(texts)
    query_dense = backend.embed_query("query")
    query_sparse = backend.sparse_query("query")
    query_multivector = backend.multivector_query("query")

    assert len(dense) == len(sparse) == len(multivectors) == 2
    assert query_dense == (1.0, 0.0)
    assert query_sparse == {"11": 1.0}
    assert len(query_multivector) == 2
    assert model.calls == [(texts, True), (("query",), True)]
    assert backend._pending_sparse == {}
    assert backend._pending_multivector == {}


def test_late_interaction_maxsim_matches_mean_query_token_reference():
    query = ((1.0, 0.0), (0.0, 1.0))
    document = ((0.8, 0.2), (0.1, 0.9))

    assert late_interaction_maxsim(query, document, dimension=2) == pytest.approx(0.85)


def _ranked_result(chunk_id, text, raw_score, *, labels=("allowed",)):
    return SearchResult(
        chunk_id=chunk_id,
        score=raw_score,
        text=text,
        document_id=f"doc-{chunk_id}",
        source_path=f"/workspace/{chunk_id}.txt",
        source_name=f"{chunk_id}.txt",
        file_type="txt",
        metadata={"source_fingerprint": "v1"},
        privacy_labels=labels,
        matched_terms=tuple(text.casefold().split()),
        term_coverage=1.0,
        matched_query_variants=("alpha beta",),
        matched_query_variant_ids=("query_original",),
        matched_query_facets=("query",),
    )


def _lexical_response(results):
    return SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query="alpha beta",
            indexed_chunk_count=len(results),
            eligible_chunk_count=len(results),
            candidate_count=len(results),
            returned_count=len(results),
        ),
    )


def test_cross_channel_rrf_is_rank_based_not_raw_score_scaled():
    low_scale = _lexical_response([
        _ranked_result("a", "alpha", 0.01),
        _ranked_result("b", "beta", 0.001),
    ])
    high_scale = _lexical_response([
        _ranked_result("a", "alpha", 10**12),
        _ranked_result("b", "beta", -(10**12)),
    ])
    dense = [
        _ranked_result("b", "beta", -99999.0),
        _ranked_result("a", "alpha", 99999.0),
    ]
    options = SearchOptions(per_document_limit=2)

    first = fuse_ranked_channels("alpha beta", low_scale, dense, limit=2, options=options)
    second = fuse_ranked_channels("alpha beta", high_scale, dense, limit=2, options=options)

    assert [item.chunk_id for item in first.results] == ["a", "b"]
    assert [item.chunk_id for item in second.results] == ["a", "b"]
    assert [item.ranking_signals["fused_rrf"] for item in first.results] == [
        item.ranking_signals["fused_rrf"] for item in second.results
    ]
    assert first.results[0].ranking_signals["lexical_channel_rank"] == 1.0
    assert first.results[0].ranking_signals["dense_channel_rank"] == 2.0
    assert [item.ranking_signals["final_rank"] for item in first.results] == [1.0, 2.0]


def test_dense_channel_rescues_paraphrase_when_lexical_channel_misses(tmp_path):
    class ParaphraseEmbeddingBackend(DeterministicEmbeddingBackend):
        def _embed(self, text):
            lowered = text.casefold()
            if ("automobile" in lowered and "maintenance" in lowered) or (
                "car" in lowered and "service" in lowered
            ):
                return normalize_vector((1.0, 0.0, 0.0, 0.0), dimension=4)
            return normalize_vector((0.0, 1.0, 0.0, 0.0), dimension=4)

    backend = ParaphraseEmbeddingBackend(dimension=4)
    chunk = make_chunk(
        "semantic",
        "manual",
        "The automobile maintenance schedule is published quarterly.",
    )
    with LocalChunkIndex(tmp_path / "index.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks([chunk])
        lexical = index.search_with_summary("car service timetable")
        hybrid = index.hybrid_search_with_summary("car service timetable", limit=1)

    assert lexical.results == ()
    assert [item.chunk_id for item in hybrid.results] == ["semantic"]
    assert hybrid.summary.candidate_backend == "hybrid_rrf"
    assert hybrid.results[0].ranking_signals["lexical_channel_rank"] == 0.0
    assert hybrid.results[0].ranking_signals["dense_channel_rank"] == 1.0


def test_multivector_score_is_primary_over_lexical_rrf_authority():
    lexical = _lexical_response([
        _ranked_result("lexical", "alpha alpha alpha procedural checklist", 1000.0),
        _ranked_result("semantic", "alpha production completion evidence", 1.0),
    ])
    dense = [
        _ranked_result("lexical", "alpha alpha alpha procedural checklist", 0.99),
        _ranked_result("semantic", "alpha production completion evidence", 0.50),
    ]

    response = fuse_ranked_channels(
        "alpha production completion",
        lexical,
        dense,
        limit=2,
        options=SearchOptions(per_document_limit=2),
        multivector_scores={"lexical": 0.10, "semantic": 0.92},
    )

    assert [item.chunk_id for item in response.results] == ["semantic", "lexical"]
    assert response.summary.candidate_backend == "hybrid_rrf_multivector"
    assert response.results[0].ranking_signals["multivector_score"] == pytest.approx(0.92)
    assert response.results[0].ranking_signals["multivector_rank"] == 1.0
    assert response.results[0].ranking_signals["fused_rrf"] < response.results[1].ranking_signals["fused_rrf"]


def test_balanced_multivector_window_cannot_be_monopolized_by_lexical_results():
    lexical = [_ranked_result(f"lex-{index}", "alpha", 1.0) for index in range(4)]
    dense = [_ranked_result("semantic", "semantic alpha", 1.0)]
    sparse = [_ranked_result("sparse", "sparse alpha", 1.0)]

    window = LocalChunkIndex._balanced_multivector_window(lexical, dense, sparse, limit=3)

    assert window == ("semantic", "sparse", "lex-0")


def test_cross_encoder_reranks_fused_window_and_preserves_trace():
    lexical = _lexical_response([
        _ranked_result("partial", "alpha", 1000.0),
        _ranked_result("complete", "alpha beta", 1.0),
    ])
    dense = [
        _ranked_result("partial", "alpha", 0.99),
        _ranked_result("complete", "alpha beta", 0.5),
    ]

    response = fuse_ranked_channels(
        "alpha beta",
        lexical,
        dense,
        limit=2,
        options=SearchOptions(per_document_limit=2),
        config=HybridRankingConfig(rerank_limit=2),
        reranker=DeterministicRerankerBackend(),
    )

    assert [item.chunk_id for item in response.results] == ["complete", "partial"]
    assert response.summary.candidate_backend == "hybrid_rrf_rerank"
    assert response.results[0].ranking_signals["reranker_score"] == 1.0
    assert response.results[1].ranking_signals["reranker_score"] == 0.5
    assert all("fused_rrf" in item.ranking_signals for item in response.results)


def test_fusion_rechecks_privacy_before_accepting_dense_only_candidate():
    lexical = _lexical_response([_ranked_result("safe", "alpha beta", 1.0)])
    dense = [
        _ranked_result("blocked", "alpha beta", 1.0, labels=("restricted",)),
        _ranked_result("safe", "alpha beta", 0.5),
    ]

    response = fuse_ranked_channels(
        "alpha beta",
        lexical,
        dense,
        limit=2,
        options=SearchOptions(allowed_privacy_labels=("allowed",), per_document_limit=2),
    )

    assert [item.chunk_id for item in response.results] == ["safe"]
    assert all(item.privacy_labels == ("allowed",) for item in response.results)


def test_fastembed_reranker_normalizes_vendor_runtime_failure():
    class FailingModel:
        def rerank(self, query, documents):
            del query, documents
            raise RuntimeError("synthetic ONNX failure")

    backend = object.__new__(FastEmbedRerankerBackend)
    backend._model = FailingModel()

    with pytest.raises(SemanticBackendError, match="inference failed"):
        backend.score_pairs((("alpha", "alpha evidence"),))
