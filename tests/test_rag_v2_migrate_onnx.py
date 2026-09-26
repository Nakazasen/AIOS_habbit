"""Offline migration of stored vectors to the ONNX fingerprint."""
from __future__ import annotations

import sqlite3

import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import LocalChunkIndex
from scripts import migrate_vectors_to_onnx as migrate


class _FakeDescriptor:
    def __init__(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        self.model_id = "test/onnx"
        self.revision = "v1"
        self.runtime = "onnxruntime-int8"
        self.runtime_version = "1"
        self.dimension = 4
        self.normalized = True


class _FakeCapability:
    def __init__(self, available: bool = True) -> None:
        self.available = available

    def require(self) -> None:
        if not self.available:
            raise AssertionError("sparse unavailable")


class _FakeBackend:
    def __init__(self, fingerprint: str = "onnx-fp") -> None:
        self.descriptor = _FakeDescriptor(fingerprint)
        self.sparse_capability = _FakeCapability()
        self.calls = 0
        self._pending: dict[tuple[str, ...], tuple[dict, ...]] = {}

    def embed_documents(self, texts):
        self.calls += 1
        vectors = tuple((1.0, 0.0, 0.0, 0.0) for _ in texts)
        self._pending[tuple(texts)] = tuple({str(i): 1.0} for i in range(len(texts)))
        return vectors

    def sparse_documents(self, texts):
        cached = self._pending.pop(tuple(texts), None)
        if cached is not None:
            return cached
        return tuple({str(i): 1.0} for i in range(len(texts)))


def _chunk(chunk_id: str, text: str = "migration target") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="doc-m",
        source_path="m.txt",
        source_name="m.txt",
        file_type="txt",
        text=text,
        normalized_text=text.lower(),
        element_ids=("e1",),
        element_types=("text",),
        privacy_labels=("cloud_safe",),
        source_fingerprint="fp",
        metadata={},
    )


def _seed(path, backend):
    with LocalChunkIndex(path, embedding_backend=backend) as index:
        index.upsert_chunks([_chunk("c1"), _chunk("c2", "second target")])
    return path


def test_plan_counts_pending_without_writing(tmp_path, monkeypatch):
    import hashlib

    from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend

    old_backend = DeterministicEmbeddingBackend(dimension=4, model_id="test/old")
    path = _seed(tmp_path / "plan.sqlite", old_backend)
    fake = _FakeBackend()
    monkeypatch.setattr(migrate, "_open_backend", lambda: fake)
    before = path.stat().st_mtime_ns
    before_bytes = path.read_bytes()
    plan = migrate.plan_migration(path)
    assert plan.retrievable_chunks == 2
    assert plan.already_onnx == 0
    assert len(plan.pending) == 2
    assert plan.pytorch_fingerprint == old_backend.descriptor.fingerprint
    assert path.stat().st_mtime_ns == before
    assert hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(
        before_bytes
    ).hexdigest()


@pytest.mark.parametrize("backend_name", ["pytorch", "onnx_int8"])
def test_apply_refuses_non_fp32_backend_overrides(tmp_path, monkeypatch, backend_name):
    fake = _FakeBackend()
    monkeypatch.setattr(migrate, "_open_backend", lambda: fake)
    monkeypatch.setenv("BGE_BACKEND", backend_name)
    plan = migrate.MigrationPlan(
        index=tmp_path / "x.sqlite",
        onnx_fingerprint="onnx-fp",
        pytorch_fingerprint="old-fp",
        pending=(),
        retrievable_chunks=0,
        already_onnx=0,
    )
    with pytest.raises(SystemExit, match="must select the ONNX fp32"):
        migrate.apply_migration(plan.index, plan)

def test_apply_requires_sibling_backup(tmp_path, monkeypatch):
    from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend

    old_backend = DeterministicEmbeddingBackend(dimension=4, model_id="test/old")
    path = _seed(tmp_path / "nobackup.sqlite", old_backend)
    fake = _FakeBackend()
    monkeypatch.setattr(migrate, "_open_backend", lambda: fake)
    monkeypatch.setenv("BGE_BACKEND", "onnx")
    plan = migrate.plan_migration(path)
    with pytest.raises(SystemExit, match="no backup"):
        migrate.apply_migration(path, plan)


def test_apply_migrates_and_resumes(tmp_path, monkeypatch):
    import shutil

    from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend

    old_backend = DeterministicEmbeddingBackend(dimension=4, model_id="test/old")
    path = _seed(tmp_path / "resume.sqlite", old_backend)
    shutil.copy2(path, tmp_path / "resume.sqlite.bak-test")
    fake = _FakeBackend()
    monkeypatch.setattr(migrate, "_open_backend", lambda: fake)
    monkeypatch.setenv("BGE_BACKEND", "onnx")
    plan = migrate.plan_migration(path)
    assert migrate.apply_migration(path, plan, batch_size=1) == 2
    assert fake.calls == 2
    resumed = migrate.plan_migration(path)
    assert len(resumed.pending) == 0
    assert resumed.already_onnx == 2
    assert migrate.apply_migration(path, resumed) == 0
    conn = sqlite3.connect(path)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM chunk_embeddings WHERE model_fingerprint = 'onnx-fp'"
        ).fetchone()[0] == 2
        assert conn.execute(
            "SELECT COUNT(*) FROM chunk_sparse_embeddings WHERE model_fingerprint = 'onnx-fp'"
        ).fetchone()[0] == 2
        # Old PyTorch-era rows are preserved, never overwritten.
        assert conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 4
    finally:
        conn.close()
