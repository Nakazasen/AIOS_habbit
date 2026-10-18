"""Tests for preflight resident warm-up and UI readiness gate (Ticket DESKTOP-RAG-PREFLIGHT-RESIDENT-WARMUP-HOME).

Fulfills requirements:
- Preflight warm-up must ensure dense vectors are in RAM (dense_resident=True).
- Worker pool allows all 4 collections to remain resident concurrently without LRU eviction.
- UI gate does not accept questions when worker is not resident.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aios_habit.rag_v2.bge_subprocess_client import (
    BgeSubprocessWorkerClient,
    get_max_persistent_workers,
    get_system_memory_info,
)
from aios_habit.rag_v2.pipeline import RagV2DevConfig
from aios_habit.workspace_chat_rag_v2_adapter import is_workspace_chat_worker_warmed


def test_max_persistent_workers_16gb_allows_4(monkeypatch):
    """Verify that host RAM >= 12GB allows 4 resident workers concurrently."""
    monkeypatch.delenv("AIOS_MAX_PERSISTENT_WORKERS", raising=False)
    monkeypatch.setattr(
        "aios_habit.rag_v2.bge_subprocess_client.get_system_memory_info",
        lambda: (16.0, 8.0),
    )
    assert get_max_persistent_workers() == 4


def test_max_persistent_workers_env_override(monkeypatch):
    """Verify explicit env override is respected."""
    monkeypatch.setenv("AIOS_MAX_PERSISTENT_WORKERS", "6")
    assert get_max_persistent_workers() == 6


def test_read_persistent_status_file_dense_resident_check(tmp_path, monkeypatch):
    """Verify _read_persistent_status_file returns ready=False when dense_resident=False."""
    cfg = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        index_filename="test.sqlite",
        retrieval_profile="bge_m3_hybrid",
        index_read_only=True,
        ensure_embeddings_on_open=False,
    )
    status_dir = tmp_path / "runtime" / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    status_file = status_dir / "worker_status.json"

    client = BgeSubprocessWorkerClient()
    monkeypatch.setattr(
        "aios_habit.rag_v2.bge_subprocess_client.status_file_for_config",
        lambda c, **kwargs: status_file,
    )
    monkeypatch.setattr(
        "aios_habit.rag_v2.bge_subprocess_client._is_worker_pid_alive",
        lambda pid: True,
    )
    monkeypatch.setattr(
        "aios_habit.rag_v2.bge_subprocess_client._pipe_instance_available",
        lambda pipe: True,
    )
    monkeypatch.setattr(
        "aios_habit.rag_v2.bge_subprocess_client.config_fingerprint_for_worker",
        lambda c: "test_fp_123",
    )

    # 1. Payload with dense_resident=False
    payload_not_dense = {
        "pid": 12345,
        "initialized": True,
        "config_fingerprint": "test_fp_123",
        "pipe_name": "test_pipe",
        "timestamp": 1000.0,
        "readiness": {
            "dense_resident": False,
            "dense_chunks": 0,
        },
    }
    status_file.write_text(json.dumps(payload_not_dense), encoding="utf-8")
    status = client._read_persistent_status_file(cfg)
    assert status is not None
    assert status["ready"] is False
    assert status["dense_resident"] is False
    assert status["reason"] == "dense_vectors_not_resident"

    # 2. Payload with dense_resident=True
    payload_dense_ready = {
        "pid": 12345,
        "initialized": True,
        "config_fingerprint": "test_fp_123",
        "pipe_name": "test_pipe",
        "timestamp": 1000.0,
        "readiness": {
            "dense_resident": True,
            "dense_chunks": 67751,
        },
    }
    status_file.write_text(json.dumps(payload_dense_ready), encoding="utf-8")
    status_ready = client._read_persistent_status_file(cfg)
    assert status_ready is not None
    assert status_ready["ready"] is True
    assert status_ready["dense_resident"] is True
    assert status_ready["dense_chunks"] == 67751


def test_is_workspace_chat_worker_warmed_verifies_resident(monkeypatch):
    """Verify is_workspace_chat_worker_warmed returns False if dense_resident is False or pipe is dead."""
    monkeypatch.setenv("AIOS_WORKSPACE_CHAT_RAG_V2", "1")
    monkeypatch.setenv("AIOS_WORKSPACE_CHAT_RETRIEVAL_PROFILE", "bge_m3_hybrid")

    with patch("aios_habit.workspace_chat_rag_v2_adapter._SUBPROCESS_CLIENT") as mock_client:
        mock_client._persistent_applies.return_value = True

        # Case A: status file probe returns dense_resident=False
        mock_client._read_persistent_status_file.return_value = {
            "ready": False,
            "dense_resident": False,
            "pid": 1234,
        }
        assert is_workspace_chat_worker_warmed(collection_id="dieu_tra_loi") is False

        # Case B: ready=True and dense_resident=True, but pipe not available
        mock_client._read_persistent_status_file.return_value = {
            "ready": True,
            "dense_resident": True,
            "pid": 1234,
        }
        with patch("aios_habit.workspace_chat_rag_v2_adapter._pipe_instance_available", return_value=False):
            assert is_workspace_chat_worker_warmed(collection_id="dieu_tra_loi") is False

        # Case C: all checks pass
        with patch("aios_habit.workspace_chat_rag_v2_adapter._pipe_instance_available", return_value=True):
            with patch("aios_habit.workspace_chat_rag_v2_adapter._is_worker_pid_alive", return_value=True):
                assert is_workspace_chat_worker_warmed(collection_id="dieu_tra_loi") is True
