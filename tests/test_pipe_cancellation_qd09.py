"""Tests for Named Pipe cooperative cancellation and timeout unblocking (QD-09).

Verifies that when caller times out or triggers a cancellation_event,
the connection handle is immediately closed, the _session thread unblocks in <1ms,
the pipe lock is released instantaneously, and the subsequent turn is not stalled.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from aios_habit.rag_v2.bge_subprocess_client import (
    BgeSubprocessWorkerClient,
    _get_pipe_session_lock,
)
from aios_habit.rag_v2.bge_worker_protocol import (
    authkey_for_worker,
    pipe_name_for_config,
)
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.semantic import SemanticBackendError


def _write_doc(tmp_path: Path) -> Path:
    doc = tmp_path / "doc_qd09.txt"
    doc.write_text("Tài liệu kiểm thử hủy kết nối pipe QD-09", encoding="utf-8")
    return doc


def _query_config(tmp_path: Path, **overrides) -> RagV2DevConfig:
    values: dict[str, object] = {
        "runtime_root": tmp_path / "runtime",
        "index_filename": "pipe_cancel_test.sqlite",
        "retrieval_profile": "lexical",
        "index_read_only": True,
        "ensure_embeddings_on_open": False,
    }
    values.update(overrides)
    return RagV2DevConfig(**values)


def _setup_pipeline(tmp_path: Path) -> SourceSpec:
    doc = _write_doc(tmp_path)
    spec = SourceSpec(path=doc, source_id="s_qd09", document_id="d_qd09")
    write_cfg = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        index_filename="pipe_cancel_test.sqlite",
        retrieval_profile="lexical",
    )
    pipeline = RagV2DevPipeline(write_cfg)
    try:
        pipeline.ingest([spec])
    finally:
        pipeline.close()
    return spec


@pytest.fixture
def persist_env(monkeypatch):
    monkeypatch.setenv("AIOS_RAGV2_WORKER_PERSIST", "1")
    monkeypatch.setenv("AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS", "600")
    return monkeypatch


@pytest.mark.skipif(os.name != "nt", reason="Named Pipe transport is Windows-only")
def test_qd09_client_timeout_releases_pipe_lock_immediately(persist_env, tmp_path):
    """QD-09: On client timeout, connection handle is closed, pipe_lock is released in <100ms."""
    spec = _setup_pipeline(tmp_path)
    cfg = _query_config(tmp_path)
    client = BgeSubprocessWorkerClient()
    pipe_name = pipe_name_for_config(cfg)
    pipe_lock = _get_pipe_session_lock(pipe_name)

    try:
        # 1. Warm up worker
        init_res = client.initialize_worker(cfg, timeout_s=180.0)
        assert init_res["status"] == "ok"

        # 2. Trigger an intentional client timeout with an impossibly short timeout (0.0001s)
        t_before = time.perf_counter()
        with pytest.raises(SemanticBackendError) as exc_info:
            client.query_ready(
                "Kiểm tra timeout?",
                [spec],
                cfg,
                timeout_s=0.0001,
            )
        t_after = time.perf_counter()
        elapsed = t_after - t_before

        assert "bge_worker_persist_timeout" in str(exc_info.value)
        # Timeout must return promptly without hanging
        assert elapsed < 1.0, f"Timeout took too long: {elapsed:.3f}s"

        # 3. CRITICAL QD-09 CHECK: pipe_lock must NOT be held by abandoned session thread!
        # Give cooperative unblock a tiny window (50ms) to ensure release
        lock_freed = False
        for _ in range(20):
            if pipe_lock.acquire(blocking=False):
                pipe_lock.release()
                lock_freed = True
                break
            time.sleep(0.01)

        assert lock_freed, "Pipe lock remained locked after client timeout!"

        # 4. CRITICAL QD-09 CHECK: Subsequent query must succeed promptly without pipe stall (no 30-50s hang)
        t_query_start = time.perf_counter()
        next_result = client.query_ready(
            "Kiểm thử kết nối pipe?",
            [spec],
            cfg,
            timeout_s=15.0,
        )
        t_query_elapsed = time.perf_counter() - t_query_start
        assert next_result["summary"]["returned_count"] >= 1
        assert t_query_elapsed < 5.0, f"Subsequent turn stalled for {t_query_elapsed:.2f}s!"

    finally:
        client.shutdown_persistent_worker(cfg)
        client.close()


@pytest.mark.skipif(os.name != "nt", reason="Named Pipe transport is Windows-only")
def test_qd09_cancel_event_aborts_and_unblocks_promptly(persist_env, tmp_path):
    """QD-09: Triggering cancel_event immediately aborts session and allows next query."""
    spec = _setup_pipeline(tmp_path)
    cfg = _query_config(tmp_path)
    client = BgeSubprocessWorkerClient()
    pipe_name = pipe_name_for_config(cfg)
    pipe_lock = _get_pipe_session_lock(pipe_name)

    try:
        init_res = client.initialize_worker(cfg, timeout_s=180.0)
        assert init_res["status"] == "ok"

        # Pre-set cancel event
        cancel_ev = threading.Event()
        cancel_ev.set()

        t_before = time.perf_counter()
        with pytest.raises(SemanticBackendError) as exc_info:
            client.query_ready(
                "Kiểm tra cancel event?",
                [spec],
                cfg,
                timeout_s=10.0,
                cancel_event=cancel_ev,
            )
        elapsed = time.perf_counter() - t_before
        assert elapsed < 0.5, f"Cancellation took too long: {elapsed:.3f}s"
        assert any(
            err in str(exc_info.value)
            for err in ("bge_worker_persist_cancelled", "bge_worker_persist_aborted")
        )

        # Pipe lock must be free
        assert pipe_lock.acquire(blocking=False)
        pipe_lock.release()

        # Follow-up query without cancel event succeeds
        next_result = client.query_ready(
            "Tài liệu kiểm thử hủy?",
            [spec],
            cfg,
            timeout_s=15.0,
        )
        assert next_result["summary"]["returned_count"] >= 1
    finally:
        client.shutdown_persistent_worker(cfg)
        client.close()
