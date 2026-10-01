"""Hotfix 2026-09-30 (PC0575 ``cho-muse`` escalation, ve ``hodap-lsu-loi``).

Field report (2026-09-30, KDTVN-PC0575, CPU-only):
- the dense coverage query in ``_durable_semantic_coverage_ready`` planned a
  full scan of the 108k-row ``chunk_embeddings`` table on
  ``model_fingerprint`` -> 71.9 s for a 15-chunk document;
- the status/readiness gate re-enters that check 4-5 times per question ->
  ~211 s/question, far above the 30 s worker query budget;
- the 30 s query budget had no env override.

Fixes under test:
1. ``_DENSE_COVERAGE_SQL`` / ``_SPARSE_COVERAGE_SQL`` pin the join order with
   ``CROSS JOIN`` so SQLite drives from ``chunks`` (document_id) into the
   embedding tables by ``chunk_id``.
2. ``default_query_timeout_seconds()`` reads ``AIOS_BGE_QUERY_TIMEOUT``
   (default 30.0 s, clamped >= 1.0 s) and the adapter uses it instead of a
   hard literal.
3. ``_durable_semantic_coverage_ready`` caches successful lookups for 60 s
   (fail-closed: exceptions are never cached).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import aios_habit.workspace_chat_rag_v2_adapter as adapter
from aios_habit.rag_v2.bge_subprocess_client import default_query_timeout_seconds
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource

REVISION = "test-revision-5617a9f"
ONNX_CHECKSUM = "sha256:" + "aa" * 32


@pytest.fixture(autouse=True)
def _clean_caches():
    adapter._COVERAGE_CACHE.clear()
    yield
    adapter._COVERAGE_CACHE.clear()


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


def _make_index(
    config,
    source,
    *,
    fingerprint: str,
    chunk_count: int = 15,
    missing_dense: int = 0,
    missing_sparse: int = 0,
    noise_chunks: int = 0,
) -> Path:
    """Production-like index sqlite: PK + model index, like ``rag_v2/index.py``."""
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
            "CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY,"
            " document_id TEXT, retrievable INTEGER, text TEXT)"
        )
        conn.execute(
            "CREATE TABLE chunk_embeddings (chunk_id TEXT NOT NULL,"
            " model_fingerprint TEXT NOT NULL, content_hash TEXT,"
            " model_id TEXT NOT NULL, model_revision TEXT NOT NULL,"
            " runtime TEXT, runtime_version TEXT, dimension INTEGER,"
            " dtype TEXT, normalized INTEGER, vector_blob BLOB,"
            " created_at TEXT,"
            " PRIMARY KEY (chunk_id, model_fingerprint))"
        )
        conn.execute(
            "CREATE INDEX idx_chunk_embeddings_model"
            " ON chunk_embeddings(model_fingerprint, chunk_id)"
        )
        conn.execute(
            "CREATE TABLE chunk_sparse_embeddings (chunk_id TEXT NOT NULL,"
            " model_fingerprint TEXT NOT NULL, content_hash TEXT,"
            " sparse_json TEXT, created_at TEXT,"
            " PRIMARY KEY (chunk_id, model_fingerprint))"
        )
        conn.execute("CREATE INDEX idx_chunks_document_id ON chunks(document_id)")
        for i in range(chunk_count):
            chunk_id = f"chunk-{i}"
            conn.execute(
                "INSERT INTO chunks VALUES (?, ?, 1, ?)",
                (chunk_id, document_id, "text"),
            )
            if i >= missing_dense:
                conn.execute(
                    "INSERT INTO chunk_embeddings (chunk_id, model_fingerprint,"
                    " model_id, model_revision) VALUES (?, ?, 'BAAI/bge-m3', ?)",
                    (chunk_id, fingerprint, REVISION),
                )
            if i >= missing_sparse:
                conn.execute(
                    "INSERT INTO chunk_sparse_embeddings (chunk_id, model_fingerprint)"
                    " VALUES (?, ?)",
                    (chunk_id, fingerprint),
                )
        for i in range(noise_chunks):
            conn.execute(
                "INSERT INTO chunk_embeddings (chunk_id, model_fingerprint,"
                " model_id, model_revision) VALUES (?, ?, 'BAAI/bge-m3', ?)",
                (f"noise-{i}", fingerprint, REVISION),
            )
        conn.commit()
    finally:
        conn.close()
    return index_path


_OLD_DENSE_SQL = """SELECT COUNT(DISTINCT c.chunk_id)
   FROM chunks c JOIN chunk_embeddings e ON e.chunk_id=c.chunk_id
   WHERE c.document_id=? AND c.retrievable=1
     AND e.model_id='BAAI/bge-m3' AND e.model_revision=?
     AND e.model_fingerprint=?"""


def _plan_lines(conn, sql, params):
    return [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params)]


def _first_table_step(plan):
    for line in plan:
        if "SEARCH" in line or "SCAN" in line:
            return line
    return ""


def test_dense_coverage_plan_drives_from_chunks(
    tmp_path, clean_env, onnx_model_dir
):
    """The fixed dense query must not lead with the embeddings table."""
    config = _config(tmp_path)
    source = _source()
    fingerprint = adapter._expected_backend_fingerprint(config)
    assert len(fingerprint) == 64
    index_path = _make_index(
        config, source, fingerprint=fingerprint, chunk_count=15, noise_chunks=5000
    )
    document_id = adapter._document_id(source)
    params = (document_id, REVISION, fingerprint)
    conn = sqlite3.connect(f"file:{index_path.as_posix()}?mode=ro", uri=True)
    try:
        # Control: the pre-fix query shape reproduces the field failure --
        # it leads with the embeddings table (the 71.9 s full scan).
        old_plan = _plan_lines(conn, _OLD_DENSE_SQL, params)
        assert old_plan, "expected a query plan for the old SQL"
        old_first = _first_table_step(old_plan)
        assert " c " not in old_first and "chunks" not in old_first, old_plan

        new_plan = _plan_lines(conn, adapter._DENSE_COVERAGE_SQL, params)
        assert new_plan, "expected a query plan for the fixed SQL"
        new_first = _first_table_step(new_plan)
        assert " c " in new_first or "chunks" in new_first, new_plan
        assert not any(
            "SCAN" in line and "chunk_embeddings" in line for line in new_plan
        ), new_plan
    finally:
        conn.close()


def test_durable_coverage_ready_true_when_fully_covered(
    tmp_path, clean_env, onnx_model_dir
):
    config = _config(tmp_path)
    source = _source()
    fingerprint = adapter._expected_backend_fingerprint(config)
    _make_index(config, source, fingerprint=fingerprint, chunk_count=15)
    assert adapter._durable_semantic_coverage_ready(source, config) is True


def test_durable_coverage_ready_false_when_dense_missing(
    tmp_path, clean_env, onnx_model_dir
):
    """Fail-closed semantics preserved: one uncovered chunk -> not ready."""
    config = _config(tmp_path)
    source = _source()
    fingerprint = adapter._expected_backend_fingerprint(config)
    _make_index(config, source, fingerprint=fingerprint, chunk_count=15, missing_dense=1)
    assert adapter._durable_semantic_coverage_ready(source, config) is False


def test_durable_coverage_ready_false_when_sparse_missing(
    tmp_path, clean_env, onnx_model_dir
):
    config = _config(tmp_path)
    source = _source()
    fingerprint = adapter._expected_backend_fingerprint(config)
    _make_index(config, source, fingerprint=fingerprint, chunk_count=15, missing_sparse=1)
    assert adapter._durable_semantic_coverage_ready(source, config) is False


def test_query_timeout_default_and_env_override(monkeypatch):
    monkeypatch.delenv("AIOS_BGE_QUERY_TIMEOUT", raising=False)
    assert default_query_timeout_seconds() == 30.0
    monkeypatch.setenv("AIOS_BGE_QUERY_TIMEOUT", "120")
    assert default_query_timeout_seconds() == 120.0
    monkeypatch.setenv("AIOS_BGE_QUERY_TIMEOUT", "not-a-number")
    assert default_query_timeout_seconds() == 30.0
    monkeypatch.setenv("AIOS_BGE_QUERY_TIMEOUT", "0")
    assert default_query_timeout_seconds() == 1.0


def test_coverage_cache_collapses_repeat_calls(tmp_path, clean_env, onnx_model_dir, monkeypatch):
    """Repeat gate passes within one question must not re-open SQLite."""
    config = _config(tmp_path)
    source = _source()
    fingerprint = adapter._expected_backend_fingerprint(config)
    _make_index(config, source, fingerprint=fingerprint, chunk_count=15)
    assert adapter._durable_semantic_coverage_ready(source, config) is True

    real_connect = sqlite3.connect
    opens = []

    def counting_connect(*args, **kwargs):
        opens.append(1)
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", counting_connect)
    # 4 more passes, like one question's gate chain: no new SQLite open.
    for _ in range(4):
        assert adapter._durable_semantic_coverage_ready(source, config) is True
    assert opens == []
    # After dropping the TTL window, the gate queries SQLite again.
    adapter._COVERAGE_CACHE.clear()
    assert adapter._durable_semantic_coverage_ready(source, config) is True
    assert len(opens) == 1


def test_coverage_gate_false_when_index_missing(tmp_path, clean_env, onnx_model_dir):
    """Missing index fails closed (the cheap is_file check stays first)."""
    config = _config(tmp_path)
    source = _source()
    assert adapter._durable_semantic_coverage_ready(source, config) is False


def test_coverage_cache_does_not_mask_unready(tmp_path, clean_env, onnx_model_dir):
    """Negative results are cached too: repeated not-ready calls stay False."""
    config = _config(tmp_path)
    source = _source()
    fingerprint = adapter._expected_backend_fingerprint(config)
    _make_index(config, source, fingerprint=fingerprint, chunk_count=15, missing_dense=1)
    assert adapter._durable_semantic_coverage_ready(source, config) is False
    assert adapter._durable_semantic_coverage_ready(source, config) is False


def test_routing_allowlist_covers_all_producer_codes():
    """Regression 2026-10-01 (E1 blocked: invalid_routing_reason_code).

    bge_subprocess_client kept a hand-copied allowlist that drifted from
    adaptive_retrieval.ALLOWLISTED_REASON_CODES (the producer): e.g. a
    causality question emits causality_intent, which the stale copy
    rejected before the worker was even called. The client must accept
    every code the producer can emit.
    """
    from aios_habit.rag_v2 import bge_subprocess_client as client
    from aios_habit.rag_v2.adaptive_retrieval import ALLOWLISTED_REASON_CODES

    missing = set(ALLOWLISTED_REASON_CODES) - set(
        client.ALLOWLISTED_ROUTING_REASON_CODES
    )
    assert not missing, f"client allowlist missing producer codes: {sorted(missing)}"
    for code in (
        "causality_intent",
        "contradiction_intent",
        "temporal_change_intent",
        "multi_part_query",
    ):
        assert code in client.ALLOWLISTED_ROUTING_REASON_CODES
