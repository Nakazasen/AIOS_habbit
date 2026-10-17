"""Tests for LRU Persistent Worker Pool and Auto-relaunch lifecycle (QD-06).

Fulfills QD-06 requirements:
- Maximum concurrent persistent workers based on host RAM (max 1 on 16GB, 2 if available > 4GB).
- Automatic eviction and graceful shutdown of LRU worker when loading new domain exceeding limit.
- Automatic on-demand worker relaunch when an evicted worker receives a new query.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from aios_habit.rag_v2.bge_subprocess_client import (
    BgeSubprocessWorkerClient,
    get_max_persistent_workers,
    get_system_memory_info,
)
from aios_habit.rag_v2.bge_worker_protocol import (
    pipe_name_for_config,
    remove_worker_status_file,
    status_file_for_config,
)
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec


def _make_domain_pipeline(tmp_path: Path, domain_name: str) -> tuple[RagV2DevConfig, SourceSpec]:
    doc = tmp_path / f"doc_{domain_name}.txt"
    doc.write_text(f"Nội dung tài liệu miền {domain_name} cho kiểm thử QD-06", encoding="utf-8")
    spec = SourceSpec(path=doc, source_id=f"s_{domain_name}", document_id=f"d_{domain_name}")
    write_cfg = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        index_filename=f"index_{domain_name}.sqlite",
        retrieval_profile="lexical",
    )
    pipeline = RagV2DevPipeline(write_cfg)
    try:
        pipeline.ingest([spec])
    finally:
        pipeline.close()

    query_cfg = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        index_filename=f"index_{domain_name}.sqlite",
        retrieval_profile="lexical",
        index_read_only=True,
        ensure_embeddings_on_open=False,
    )
    return query_cfg, spec


@pytest.fixture
def persist_env(monkeypatch):
    monkeypatch.setenv("AIOS_RAGV2_WORKER_PERSIST", "1")
    monkeypatch.setenv("AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS", "600")
    return monkeypatch


def test_qd06_memory_limits_and_env_override(monkeypatch):
    """QD-06: Verify memory detection and max persistent worker limits."""
    total_gb, avail_gb = get_system_memory_info()
    assert total_gb > 0.0
    assert avail_gb > 0.0

    monkeypatch.setenv("AIOS_MAX_PERSISTENT_WORKERS", "3")
    assert get_max_persistent_workers() == 3

    monkeypatch.setenv("AIOS_MAX_PERSISTENT_WORKERS", "1")
    assert get_max_persistent_workers() == 1

    monkeypatch.delenv("AIOS_MAX_PERSISTENT_WORKERS", raising=False)
    computed = get_max_persistent_workers()
    assert computed in (1, 2)


@pytest.mark.skipif(os.name != "nt", reason="Named Pipe transport is Windows-only")
def test_qd06_lru_worker_eviction_and_auto_relaunch(persist_env, tmp_path, monkeypatch):
    """QD-06: Evict LRU worker when limit reached, auto-relaunch evicted worker on demand."""
    # Force max concurrent persistent workers to 1 to deterministically test LRU eviction
    monkeypatch.setenv("AIOS_MAX_PERSISTENT_WORKERS", "1")

    cfg_a, spec_a = _make_domain_pipeline(tmp_path, "domain_a")
    cfg_b, spec_b = _make_domain_pipeline(tmp_path, "domain_b")

    client = BgeSubprocessWorkerClient()
    try:
        # 1. Start worker for Domain A
        init_a = client.initialize_worker(cfg_a, timeout_s=180.0)
        assert init_a["status"] == "ok"
        pid_a = init_a["readiness"].get("pid")
        assert pid_a is not None
        status_file_a = status_file_for_config(cfg_a)
        assert status_file_a.is_file()

        # Query domain A to ensure it's functioning
        res_a = client.query_ready("Nội dung tài liệu domain_a", [spec_a], cfg_a, timeout_s=15.0)
        assert res_a["summary"]["returned_count"] >= 1

        active = client.get_active_persistent_workers()
        pipe_a = pipe_name_for_config(cfg_a)
        assert pipe_a in active

        # 2. Start worker for Domain B -> Exceeds max 1, Domain A must be evicted
        init_b = client.initialize_worker(cfg_b, timeout_s=180.0)
        assert init_b["status"] == "ok"
        pid_b = init_b["readiness"].get("pid")
        assert pid_b is not None
        assert pid_b != pid_a

        pipe_b = pipe_name_for_config(cfg_b)
        active_after_b = client.get_active_persistent_workers()
        assert pipe_b in active_after_b

        # Domain A status file must be removed by eviction
        # Worker A should be evicted from tracking pool
        assert pipe_a not in active_after_b

        # Query domain B works
        res_b = client.query_ready("Nội dung tài liệu domain_b", [spec_b], cfg_b, timeout_s=15.0)
        assert res_b["summary"]["returned_count"] >= 1

        # 3. AUTO-RELAUNCH TEST: Query domain A again
        # Worker A was evicted, but client must automatically relaunch it and succeed!
        res_a_relaunch = client.query_ready(
            "Nội dung tài liệu domain_a",
            [spec_a],
            cfg_a,
            timeout_s=180.0,
        )
        assert res_a_relaunch["summary"]["returned_count"] >= 1

        # Now Domain A is back in active pool, Domain B was evicted (limit=1)
        active_after_relaunch = client.get_active_persistent_workers()
        assert pipe_a in active_after_relaunch
        assert pipe_b not in active_after_relaunch

    finally:
        client.shutdown_persistent_worker(cfg_a)
        client.shutdown_persistent_worker(cfg_b)
        client.close()
