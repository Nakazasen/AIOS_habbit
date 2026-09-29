"""G2 backend-aware prepare gate: the 'chuan bi' gate must check the embedding
fingerprint of the backend the E-chain currently selects.

A backend switch (onnx <-> pytorch, onnxruntime upgrade, ...) changes the
model fingerprint stamped on vectors. The gate must then fail closed
(not READY) so the worker re-embeds with the current backend instead of
silently serving vectors produced by a different backend.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
import aios_habit.workspace_chat_rag_v2_adapter as adapter

REVISION = "test-revision-5617a9f"
ONNX_CHECKSUM = "sha256:" + "aa" * 32
PYTORCH_CHECKSUM = "sha256:" + "bb" * 32


def _source(text: str = "Nội dung kiểm thử cổng chuẩn bị") -> WorkspaceAIContextSource:
    return WorkspaceAIContextSource(
        source_id="source-gate-1",
        source_scope="temporary",
        source_type="pasted_text",
        title="gate-notes.txt",
        privacy_label="local_only",
        text=text,
        included_chars=len(text),
        truncated=False,
    )


@pytest.fixture(autouse=True)
def _clean_preparation_registry():
    adapter._PREPARATION_REGISTRY.clear()
    yield
    adapter._PREPARATION_REGISTRY.clear()


@pytest.fixture()
def clean_env(monkeypatch):
    for key in ("BGE_BACKEND", "AIOS_BGE_ONNX_MODEL_PATH", "AIOS_BGE_ONNX_CHECKSUM"):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture()
def onnx_model_dir(tmp_path, clean_env):
    """Fake ONNX model tree: model.onnx + sibling .sha256 sidecar."""
    model_dir = tmp_path / "onnx-model"
    model_dir.mkdir()
    (model_dir / "model.onnx").write_bytes(b"fake-onnx")
    (tmp_path / "onnx-model.sha256").write_text(ONNX_CHECKSUM + "  model.onnx\n")
    clean_env.setenv("AIOS_BGE_ONNX_MODEL_PATH", str(model_dir))
    return model_dir


def _config(tmp_path: Path, **overrides):
    kwargs = {
        "enabled": True,
        "runtime_root": tmp_path / "rag",
        "bge_m3_model_revision": REVISION,
    }
    kwargs.update(overrides)
    return adapter.WorkspaceChatRagV2CanaryConfig(**kwargs)


def _insert_ledger_row(config, source, *, state="ready", model_fingerprint=""):
    db_path = adapter._get_ledger_db_path(config)
    adapter._init_preparation_ledger_db(db_path)
    row = adapter.SourcePreparationLedgerRow(
        source_scope=source.source_scope,
        source_id=source.source_id,
        source_fingerprint=adapter._source_fingerprint(source),
        model_id="BAAI/bge-m3",
        model_revision=config.bge_m3_model_revision,
        state=state,
        document_id=adapter._document_id(source),
        model_fingerprint=model_fingerprint,
    )
    adapter._upsert_ledger_row(db_path, row)
    return db_path


def _make_index(config, source, *, vector_fingerprint: str) -> Path:
    """Minimal index sqlite with one retrievable chunk + matching vectors."""
    from aios_habit import workspace_chat_store as store

    collection_id = adapter._collection_id_for_sources((source,))
    profile_root = config.runtime_root / config.requested_profile
    collection_root, index_filename = store.collection_runtime_layout(
        collection_id, profile_root
    )
    collection_root.mkdir(parents=True, exist_ok=True)
    index_path = collection_root / index_filename
    document_id = adapter._document_id(source)
    conn = sqlite3.connect(index_path)
    try:
        conn.execute(
            "CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT, retrievable INTEGER)"
        )
        conn.execute(
            "CREATE TABLE chunk_embeddings (chunk_id TEXT, model_fingerprint TEXT,"
            " model_id TEXT, model_revision TEXT)"
        )
        conn.execute(
            "CREATE TABLE chunk_sparse_embeddings (chunk_id TEXT, model_fingerprint TEXT)"
        )
        conn.execute(
            "INSERT INTO chunks VALUES ('chunk-1', ?, 1)", (document_id,)
        )
        conn.execute(
            "INSERT INTO chunk_embeddings VALUES ('chunk-1', ?, 'BAAI/bge-m3', ?)",
            (vector_fingerprint, config.bge_m3_model_revision),
        )
        conn.execute(
            "INSERT INTO chunk_sparse_embeddings VALUES ('chunk-1', ?)",
            (vector_fingerprint,),
        )
        conn.commit()
    finally:
        conn.close()
    return index_path


# --- _expected_backend_fingerprint ----------------------------------------


def test_expected_fingerprint_empty_without_revision(tmp_path, clean_env, onnx_model_dir):
    config = _config(tmp_path, bge_m3_model_revision="")
    assert adapter._expected_backend_fingerprint(config) == ""


def test_expected_fingerprint_empty_without_model(tmp_path, clean_env):
    # The repo default model tree may exist on a dev machine; point the ONNX
    # model path at a missing directory so "no model" is deterministic.
    clean_env.setenv("AIOS_BGE_ONNX_MODEL_PATH", str(tmp_path / "no-model"))
    config = _config(tmp_path)
    assert adapter._expected_backend_fingerprint(config) == ""


def test_expected_fingerprint_onnx_stable_and_mirrors_descriptor(
    tmp_path, clean_env, onnx_model_dir
):
    from aios_habit.rag_v2.bge_onnx_backend import (
        BGE_M3_DIMENSION,
        BGE_M3_MODEL_ID,
        _onnxruntime_version,
        resolve_onnx_checksum,
    )
    from aios_habit.rag_v2.semantic import SemanticModelDescriptor

    config = _config(tmp_path)
    first = adapter._expected_backend_fingerprint(config)
    assert len(first) == 64 and all(c in "0123456789abcdef" for c in first)

    manual = SemanticModelDescriptor(
        model_id=BGE_M3_MODEL_ID,
        revision=REVISION,
        runtime="onnxruntime-int8",
        runtime_version=_onnxruntime_version(),
        dimension=BGE_M3_DIMENSION,
        normalized=True,
        artifact_checksum=resolve_onnx_checksum(onnx_model_dir),
        device="cpu",
    ).fingerprint
    assert first == manual
    assert adapter._expected_backend_fingerprint(config) == first


def test_expected_fingerprint_changes_with_backend_switch(
    tmp_path, clean_env, onnx_model_dir
):
    config = _config(tmp_path, bge_m3_model_checksum=PYTORCH_CHECKSUM)
    onnx_fp = adapter._expected_backend_fingerprint(config)
    assert len(onnx_fp) == 64

    clean_env.setenv("BGE_BACKEND", "pytorch")
    pytorch_fp = adapter._expected_backend_fingerprint(config)
    assert len(pytorch_fp) == 64
    assert pytorch_fp != onnx_fp


def test_expected_fingerprint_empty_for_unknown_backend(
    tmp_path, clean_env, onnx_model_dir
):
    clean_env.setenv("BGE_BACKEND", "bogus-backend")
    config = _config(tmp_path)
    assert adapter._expected_backend_fingerprint(config) == ""


def test_expected_fingerprint_empty_for_pytorch_without_checksum(
    tmp_path, clean_env, onnx_model_dir
):
    clean_env.setenv("BGE_BACKEND", "pytorch")
    config = _config(tmp_path)  # no bge_m3_model_checksum
    assert adapter._expected_backend_fingerprint(config) == ""


# --- prepare gate ----------------------------------------------------------


def test_gate_ready_row_with_matching_stamp(tmp_path, clean_env, onnx_model_dir):
    config = _config(tmp_path)
    source = _source()
    expected = adapter._expected_backend_fingerprint(config)
    assert expected
    _insert_ledger_row(config, source, model_fingerprint=expected)

    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] == "ready"
    assert summary["ready"] == 1


def test_gate_stale_stamp_forces_pending(tmp_path, clean_env, onnx_model_dir):
    config = _config(tmp_path)
    source = _source()
    expected = adapter._expected_backend_fingerprint(config)
    assert expected
    _insert_ledger_row(config, source, model_fingerprint="0" * 64)

    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] == "pending"
    assert summary["ready"] == 0


def test_gate_legacy_row_backfills_stamp_from_index(
    tmp_path, clean_env, onnx_model_dir
):
    config = _config(tmp_path)
    source = _source()
    expected = adapter._expected_backend_fingerprint(config)
    assert expected
    db_path = _insert_ledger_row(config, source, model_fingerprint="")
    _make_index(config, source, vector_fingerprint=expected)

    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] == "ready"

    row = adapter._load_ledger_row(db_path, source.source_scope, source.source_id)
    assert row is not None and row.model_fingerprint == expected


def test_gate_legacy_row_without_index_coverage_stays_pending(
    tmp_path, clean_env, onnx_model_dir
):
    config = _config(tmp_path)
    source = _source()
    _insert_ledger_row(config, source, model_fingerprint="")

    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] == "pending"


def test_gate_unknown_backend_reports_pending(tmp_path, clean_env):
    # No model configured -> backend identity unknown -> fail closed.
    config = _config(tmp_path)
    source = _source()
    _insert_ledger_row(config, source, model_fingerprint="")

    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] == "pending"
    assert summary["ready"] == 0


def test_durable_coverage_rejects_wrong_backend_fingerprint(
    tmp_path, clean_env, onnx_model_dir
):
    config = _config(tmp_path)
    source = _source()
    expected = adapter._expected_backend_fingerprint(config)
    assert expected
    _make_index(config, source, vector_fingerprint="f" * 64)

    assert adapter._durable_semantic_coverage_ready(source, config) is False


def test_durable_coverage_accepts_current_backend_fingerprint(
    tmp_path, clean_env, onnx_model_dir
):
    config = _config(tmp_path)
    source = _source()
    expected = adapter._expected_backend_fingerprint(config)
    assert expected
    _make_index(config, source, vector_fingerprint=expected)

    assert adapter._durable_semantic_coverage_ready(source, config) is True


def test_reconcile_reenqueues_row_stamped_by_another_backend(
    tmp_path, clean_env, onnx_model_dir
):
    """Self-healing: a READY row stamped by a different backend is reset to
    pending and re-enqueued so the worker re-embeds with the current backend.
    """
    config = _config(tmp_path)
    source = _source()
    expected = adapter._expected_backend_fingerprint(config)
    assert expected
    db_path = _insert_ledger_row(config, source, model_fingerprint="0" * 64)

    count = adapter.reconcile_and_enqueue_workspace_chat_sources(
        (source,), config=config
    )
    assert count == 1
    row = adapter._load_ledger_row(db_path, source.source_scope, source.source_id)
    assert row is not None
    assert row.state == adapter.PREP_STATE_PENDING
    # The stale stamp is wiped; the worker will stamp the current backend.
    assert row.model_fingerprint == ""


def test_reconcile_preserves_row_when_backend_unknown(tmp_path, clean_env):
    """Backend unknown: the READY row is preserved untouched (not clobbered),
    but the gate still reports pending (fail closed)."""
    # No model on this machine: point the ONNX model path at a missing dir.
    clean_env.setenv("AIOS_BGE_ONNX_MODEL_PATH", str(tmp_path / "no-model"))
    config = _config(tmp_path)  # revision set, but no model dir
    source = _source()
    assert adapter._expected_backend_fingerprint(config) == ""
    db_path = _insert_ledger_row(config, source, model_fingerprint="ab" * 32)

    count = adapter.reconcile_and_enqueue_workspace_chat_sources(
        (source,), config=config
    )
    assert count == 0
    row = adapter._load_ledger_row(db_path, source.source_scope, source.source_id)
    assert row is not None
    assert row.state == adapter.PREP_STATE_READY
    assert row.model_fingerprint == "ab" * 32
    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] == "pending"


def test_commit_result_stamps_fingerprint_on_ready(tmp_path, clean_env):
    config = _config(tmp_path)
    source = _source()
    db_path = _insert_ledger_row(config, source, state="pending")
    adapter._commit_preparation_result(
        db_path,
        source.source_scope,
        source.source_id,
        adapter.PREP_STATE_READY,
        model_fingerprint="ab" * 32,
    )
    row = adapter._load_ledger_row(db_path, source.source_scope, source.source_id)
    assert row is not None
    assert row.state == adapter.PREP_STATE_READY
    assert row.model_fingerprint == "ab" * 32


def test_memory_ready_invalidated_by_backend_switch(tmp_path, clean_env, onnx_model_dir):
    """In-memory READY must not survive a backend switch.

    The preparation key embeds the runtime key, which now includes the
    backend name, so entries prepared under another backend are invisible
    after the switch and the gate reports not-ready instead of READY.
    """
    config = _config(tmp_path)
    source = _source()
    key = adapter._preparation_key(config, source)
    adapter._PREPARATION_REGISTRY[key] = adapter._preparation_entry(
        config, source, adapter.PREP_STATE_READY
    )

    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] == "ready"

    clean_env.setenv("BGE_BACKEND", "pytorch")
    summary = adapter.get_workspace_chat_preparation_summary((source,), config=config)
    assert summary["statuses"]["temporary:source-gate-1"] != "ready"


def test_runtime_key_changes_with_backend(tmp_path, clean_env, onnx_model_dir):
    config = _config(tmp_path)
    before = adapter._runtime_key(config, config.requested_profile)
    clean_env.setenv("BGE_BACKEND", "pytorch")
    after = adapter._runtime_key(config, config.requested_profile)
    assert before != after
