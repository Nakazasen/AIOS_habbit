"""Persistent BGE worker transport + resumable init tests (SPEED-COLDSTART-PC0575)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from aios_habit.rag_v2.bge_subprocess_client import BgeSubprocessWorkerClient
from aios_habit.rag_v2.bge_worker_protocol import (
    authkey_for_worker,
    persistent_worker_enabled,
    pipe_name_for_config,
)
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.semantic import SemanticBackendError


def _write_doc(tmp_path: Path) -> Path:
    doc = tmp_path / "doc.txt"
    doc.write_text("Lỗi beam diameter LSU kiểm tra LD mirror trục quang", encoding="utf-8")
    return doc


def _runtime_root(tmp_path: Path) -> Path:
    return tmp_path / "runtime"


def _query_config(tmp_path: Path, **overrides) -> RagV2DevConfig:
    values: dict[str, object] = {
        "runtime_root": _runtime_root(tmp_path),
        "index_filename": "persist.sqlite",
        "retrieval_profile": "lexical",
        "index_read_only": True,
        "ensure_embeddings_on_open": False,
    }
    values.update(overrides)
    return RagV2DevConfig(**values)


def _write_pipeline(tmp_path: Path):
    write_cfg = RagV2DevConfig(
        runtime_root=_runtime_root(tmp_path),
        index_filename="persist.sqlite",
        retrieval_profile="lexical",
    )
    pipeline = RagV2DevPipeline(write_cfg)
    return pipeline


@pytest.fixture
def persist_env(monkeypatch):
    monkeypatch.setenv("AIOS_RAGV2_WORKER_PERSIST", "1")
    monkeypatch.setenv("AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS", "600")
    return monkeypatch


def test_persistent_worker_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("AIOS_RAGV2_WORKER_PERSIST", raising=False)
    assert persistent_worker_enabled() is False
    client = BgeSubprocessWorkerClient()
    try:
        assert client._persistent_applies(_query_config(tmp_path)) is False
    finally:
        client.close()


@pytest.mark.skipif(os.name != "nt", reason="named-pipe transport is Windows-only")
def test_persistent_worker_survives_client_restart(persist_env, tmp_path):
    doc = _write_doc(tmp_path)
    spec = SourceSpec(path=doc, source_id="s1", document_id="d1")
    pipeline = _write_pipeline(tmp_path)
    try:
        pipeline.ingest([spec])
    finally:
        pipeline.close()

    cfg = _query_config(tmp_path)
    client_a = BgeSubprocessWorkerClient()
    client_b = BgeSubprocessWorkerClient()
    try:
        report_a = client_a.initialize_worker(cfg, timeout_s=180.0)
        assert report_a["status"] == "ok"
        assert report_a["reused"] is False
        pid_a = report_a["readiness"].get("pid")
        assert pid_a

        result_a = client_a.query_ready(
            "Lỗi beam diameter kiểm tra gì?", [spec], cfg, timeout_s=120.0
        )
        assert result_a["summary"]["returned_count"] >= 1

        client_a.close()  # app exit; the daemon must survive it

        probe = client_b.readiness(cfg)
        assert probe["ready"] is True
        assert probe["pid"] == pid_a

        report_b = client_b.initialize_worker(cfg, timeout_s=60.0)
        assert report_b["reused"] is True
        assert report_b["readiness"].get("pid") == pid_a

        result_b = client_b.query_ready(
            "Lỗi beam diameter kiểm tra gì?", [spec], cfg, timeout_s=120.0
        )
        assert result_b["summary"]["returned_count"] >= 1
    finally:
        client_a.close()
        client_b.shutdown_persistent_worker(cfg)
        client_b.close()


@pytest.mark.skipif(os.name != "nt", reason="named-pipe transport is Windows-only")
def test_persistent_worker_rejects_mismatched_config_on_same_pipe(persist_env, tmp_path):
    import multiprocessing.connection as mpc

    doc = _write_doc(tmp_path)
    spec = SourceSpec(path=doc, source_id="s1", document_id="d1")
    pipeline = _write_pipeline(tmp_path)
    try:
        pipeline.ingest([spec])
    finally:
        pipeline.close()

    cfg = _query_config(tmp_path)
    client = BgeSubprocessWorkerClient()
    try:
        assert client.initialize_worker(cfg, timeout_s=180.0)["status"] == "ok"
        conn = mpc.Client(
            pipe_name_for_config(cfg), family="AF_PIPE", authkey=authkey_for_worker()
        )
        try:
            conn.send(
                {
                    "command": "init",
                    "config": {**cfg.__dict__, "retrieval_limit": 3},
                }
            )
            response = conn.recv()
        finally:
            conn.close()
        assert response["status"] == "error"
        assert response["error"] == "persistent_worker_configuration_mismatch"
    finally:
        client.shutdown_persistent_worker(cfg)
        client.close()


def test_init_timeout_keeps_loading_worker_and_resumes(tmp_path):
    """A timing-out caller must not kill the loading worker; the next call resumes it."""
    cfg = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        index_filename="persist.sqlite",
        retrieval_profile="lexical",
    )
    client = BgeSubprocessWorkerClient()
    try:
        with pytest.raises(SemanticBackendError):
            client.initialize_worker(cfg, timeout_s=0.05)
        pending = client._pending_init
        assert pending is not None
        assert client._process is not None and client._process.poll() is None
        first_launcher_pid = client._process.pid

        report = client.initialize_worker(cfg, timeout_s=180.0)
        assert report["status"] == "ok"
        # The same loading process must be kept and resumed, not respawned.
        assert client._process is not None
        assert client._process.pid == first_launcher_pid
        assert client._pending_init is None
    finally:
        client.close()
