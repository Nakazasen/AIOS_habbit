import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import LocalChunkIndex, SearchOptions
from aios_habit.rag_v2.semantic import (
    DeterministicEmbeddingBackend,
    SemanticBackendUnavailable,
    SemanticModelDescriptor,
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
