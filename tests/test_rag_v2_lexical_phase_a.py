"""Tests for OPT-RAGV2-LEXICAL Phase A (cache-token fix).

Phase A drops ``connection.total_changes`` from ``_index_cache_token()`` and
keeps only ``PRAGMA data_version`` of the main database. Writes to the TEMP
table ``rag_v2_eligible_chunks`` during the lexical FTS branch bump
``total_changes`` but never touch the main database's ``data_version``; with
the old ``(data_version, total_changes)`` token that mid-query TEMP write
invalidated the warm dense/sparse caches and forced a 100-260s matrix reload
inside the very query that caused it.

Tests:
1. TEMP writes (DELETE + INSERT into ``rag_v2_eligible_chunks``, same shape as
   the lexical branch) do NOT change the cache token — and ``total_changes``
   really does increase, proving the probe reproduces the old bug's trigger.
2. A seeded dense matrix cache survives the TEMP write: ``_dense_matrix_cache_for``
   returns the identical object without calling the loader again.
3. Same for the sparse inverted-index cache.
4. A genuine write to the main database (``upsert_chunks``) DOES change the
   token, so real index changes still invalidate the caches (safety assumption
   of Phase A: the worker never writes embedding tables mid-query; every merge
   restarts the app).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import NUMPY_DENSE_FLAG, LocalChunkIndex
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend

pytestmark = pytest.mark.slow


def make_chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        source_path="source.txt",
        source_name="source.txt",
        file_type="txt",
        text=text,
        normalized_text=text.casefold(),
        element_ids=(f"element-{chunk_id}",),
        element_types=("text",),
        section_path=("section", chunk_id),
        privacy_labels=("allowed",),
        source_fingerprint="v1",
        metadata={},
    )


def _phase_a_index(tmp_path: Path, count: int = 8) -> LocalChunkIndex:
    chunks = [
        make_chunk(f"chunk-{i:03d}", f"sample document text number {i} beam diameter")
        for i in range(count)
    ]
    backend = DeterministicEmbeddingBackend(dimension=16)
    index = LocalChunkIndex(tmp_path / "index.sqlite", embedding_backend=backend)
    index.upsert_chunks(chunks)
    index.ensure_embeddings()
    return index


def _simulate_lexical_temp_write(index: LocalChunkIndex, n: int = 500) -> int:
    """Reproduce the lexical FTS branch's TEMP-table write (index.py ~L3911).

    Returns the number of rows inserted.
    """
    conn = index._conn
    conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS rag_v2_eligible_chunks (chunk_id TEXT PRIMARY KEY)"
    )
    conn.execute("DELETE FROM rag_v2_eligible_chunks")
    conn.executemany(
        "INSERT INTO rag_v2_eligible_chunks(chunk_id) VALUES (?)",
        [(f"chunk-{i:03d}",) for i in range(n)],
    )
    return n


def test_temp_write_does_not_change_cache_token(tmp_path: Path) -> None:
    with _phase_a_index(tmp_path) as index:
        before = index._index_cache_token()
        changes_before = index._conn.total_changes
        _simulate_lexical_temp_write(index)
        # The probe really reproduces the old trigger: total_changes jumps ...
        assert index._conn.total_changes > changes_before
        # ... but the cache token (main DB data_version) does not.
        assert index._index_cache_token() == before


def test_dense_cache_survives_temp_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    np = pytest.importorskip("numpy")
    assert np is not None
    monkeypatch.setenv(NUMPY_DENSE_FLAG, "1")
    with _phase_a_index(tmp_path) as index:
        fingerprint = index._embedding_backend.descriptor.fingerprint
        seeded = index._dense_matrix_cache_for(fingerprint, 16)
        assert seeded is not None

        calls = 0
        real_loader = index._load_dense_matrix_cache

        def counting_loader(fp: str, dim: int):
            nonlocal calls
            calls += 1
            return real_loader(fp, dim)

        monkeypatch.setattr(index, "_load_dense_matrix_cache", counting_loader)
        _simulate_lexical_temp_write(index)
        again = index._dense_matrix_cache_for(fingerprint, 16)
        assert again is seeded
        assert calls == 0


def test_sparse_cache_survives_temp_write(tmp_path: Path) -> None:
    with _phase_a_index(tmp_path) as index:
        fingerprint = index._embedding_backend.descriptor.fingerprint
        seeded = index._sparse_vector_cache_for(fingerprint)
        assert seeded is not None

        calls = 0
        real_loader = index._load_sparse_vector_cache

        def counting_loader(fp: str):
            nonlocal calls
            calls += 1
            return real_loader(fp)

        # Instance-attribute patch: the accessor calls self._load_sparse_vector_cache.
        index._load_sparse_vector_cache = counting_loader  # type: ignore[method-assign]
        try:
            _simulate_lexical_temp_write(index)
            again = index._sparse_vector_cache_for(fingerprint)
        finally:
            index._load_sparse_vector_cache = real_loader  # type: ignore[method-assign]
        assert again is seeded
        assert calls == 0


def test_real_main_db_write_still_invalidates_cache(tmp_path: Path) -> None:
    with _phase_a_index(tmp_path) as index:
        fingerprint = index._embedding_backend.descriptor.fingerprint
        token_before = index._index_cache_token()
        sparse_before = index._sparse_vector_cache_for(fingerprint)
        assert sparse_before is not None
        index.upsert_chunks([make_chunk("chunk-new", "brand new chunk about beam")])
        assert index._index_cache_token() != token_before
        sparse_after = index._sparse_vector_cache_for(fingerprint)
        assert sparse_after is not None
        assert sparse_after is not sparse_before


def test_ensure_embeddings_without_pending_writes_keeps_cache(tmp_path: Path) -> None:
    # ensure_embeddings() with nothing pending must NOT invalidate the warm
    # cache (no spurious 100s+ reload on the warm query path).
    with _phase_a_index(tmp_path) as index:
        fingerprint = index._embedding_backend.descriptor.fingerprint
        assert index.ensure_embeddings() == 0
        seeded = index._sparse_vector_cache_for(fingerprint)
        assert seeded is not None
        assert index.ensure_embeddings() == 0
        assert index._sparse_vector_cache_for(fingerprint) is seeded
