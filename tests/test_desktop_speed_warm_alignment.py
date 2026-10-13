"""Tests for DESKTOP-SPEED-WARM-ALIGNMENT-FIX-HOME.

Verifies:
1. Scripts set AIOS_RAGV2_WORKER_PERSIST=1 before probe execution.
2. Probe verifies from turn perspective (named pipe + is_ready) before reporting ready.
3. Startup warming warms multi-collection (tri_thuc, tong_hop, lsu, dieu_tra_loi) in background (blocking=False).
4. Startup warming resilience: failure in one collection does not crash or block others.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import aios_habit.workspace_chat_rag_v2_adapter as adapter


def test_verify_script_sets_worker_persist_env():
    """Verify scripts/verify_presynth_markers_live_home.py sets AIOS_RAGV2_WORKER_PERSIST=1."""
    script_path = Path(r"D:\Sandbox\AIOS_habbit\scripts\verify_presynth_markers_live_home.py")
    assert script_path.is_file()
    content = script_path.read_text(encoding="utf-8")

    # Env var must be set in os.environ before probe/warming imports
    assert 'os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"' in content
    
    # Check that warm_up_collection or warm_up_tong_hop verifies from turn perspective
    assert "_pipe_instance_available" in content
    assert "_SUBPROCESS_CLIENT.is_ready" in content


def _make_config(tmp_path: Path) -> adapter.WorkspaceChatRagV2CanaryConfig:
    (tmp_path / "pinned-bge-m3").mkdir(parents=True, exist_ok=True)
    return adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        requested_profile="bge_m3_hybrid",
        runtime_root=tmp_path,
        bge_m3_model_path=tmp_path / "pinned-bge-m3",
        bge_m3_model_revision="test-revision",
        bge_m3_model_checksum="sha256:" + "a" * 64,
        fail_closed_on_error=True,
    )


def test_probe_honesty_unaligned_turn_perspective(monkeypatch, tmp_path):
    """When persistent applies but pipe or client is unready, probe must report unready even if chunks > 0."""
    config = _make_config(tmp_path)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "is_alive", lambda: True)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "_persistent_applies", lambda cfg: True)
    # Simulate turn worker unready
    monkeypatch.setattr(adapter, "_pipe_instance_available", lambda pipe_name: False)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "is_ready", lambda cfg: False)

    # Retrieval returned chunks, but named pipe does not exist
    monkeypatch.setattr(
        adapter,
        "retrieve_workspace_chat_evidence",
        lambda *args, **kwargs: {"status": "ok", "summary_count": 18},
    )

    result = adapter.probe_workspace_chat_worker("test probe", config=config, domain="tong_hop")
    assert result["ready"] is False
    assert result["ok"] is False
    assert result["chunks"] == 18
    assert "duong luot chua san sang" in result["reason"]


def test_probe_honesty_aligned_turn_perspective(monkeypatch, tmp_path):
    """When persistent applies, pipe exists, client is ready, and chunks > 0, probe reports ready."""
    config = _make_config(tmp_path)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "is_alive", lambda: True)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "_persistent_applies", lambda cfg: True)
    monkeypatch.setattr(adapter, "_pipe_instance_available", lambda pipe_name: True)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "is_ready", lambda cfg: True)

    monkeypatch.setattr(
        adapter,
        "retrieve_workspace_chat_evidence",
        lambda *args, **kwargs: {"status": "ok", "summary_count": 18},
    )

    result = adapter.probe_workspace_chat_worker("test probe", config=config, domain="tong_hop")
    assert result["ready"] is True
    assert result["ok"] is True
    assert result["chunks"] == 18
    assert result["reason"] == "worker san sang that"


def test_ensure_workspace_chat_startup_warming_calls_all_collections(monkeypatch, tmp_path):
    """ensure_workspace_chat_startup_warming must trigger warming for tri_thuc, tong_hop, lsu, dieu_tra_loi."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, requested_profile="bge_m3_hybrid")

    warmed_calls = []

    def mock_warming(*, config=None, blocking=False, pipe_config=None, **kwargs):
        coll_id = getattr(pipe_config, "collection_id", None) if pipe_config else "tri_thuc"
        warmed_calls.append({"collection": coll_id, "blocking": blocking, "pipe_config": pipe_config})
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming)

    # Mock _pipeline_config to return valid configs with index_path.is_file() == True
    def mock_pipe_cfg(cfg, profile, *, read_only=True, collection_id=None):
        mock_obj = MagicMock()
        mock_obj.collection_id = collection_id
        mock_obj.index_path = MagicMock()
        mock_obj.index_path.is_file.return_value = True
        return mock_obj

    monkeypatch.setattr(adapter, "_pipeline_config", mock_pipe_cfg)

    results = adapter.ensure_workspace_chat_startup_warming(
        config=config,
        collections=("tong_hop", "lsu", "dieu_tra_loi"),
    )

    assert "tri_thuc" in results
    assert "tong_hop" in results
    assert "lsu" in results
    assert "dieu_tra_loi" in results

    # Verify all calls used non-blocking mode
    assert len(warmed_calls) == 4
    for call in warmed_calls:
        assert call["blocking"] is False

    warmed_colls = [c["collection"] for c in warmed_calls]
    assert "tri_thuc" in warmed_colls
    assert "tong_hop" in warmed_colls
    assert "lsu" in warmed_colls
    assert "dieu_tra_loi" in warmed_colls


def test_startup_warming_resilience_to_single_collection_failure(monkeypatch):
    """Failure warming one collection must not crash app or block other collections."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, requested_profile="bge_m3_hybrid")

    warmed_calls = []

    def mock_warming_with_failure(*, config=None, blocking=False, pipe_config=None, **kwargs):
        coll_id = getattr(pipe_config, "collection_id", None) if pipe_config else "tri_thuc"
        if coll_id == "lsu":
            raise RuntimeError("disk IO error on lsu")
        warmed_calls.append(coll_id)
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming_with_failure)

    def mock_pipe_cfg(cfg, profile, *, read_only=True, collection_id=None):
        mock_obj = MagicMock()
        mock_obj.collection_id = collection_id
        mock_obj.index_path = MagicMock()
        mock_obj.index_path.is_file.return_value = True
        return mock_obj

    monkeypatch.setattr(adapter, "_pipeline_config", mock_pipe_cfg)

    # Must NOT raise exception
    results = adapter.ensure_workspace_chat_startup_warming(
        config=config,
        collections=("tong_hop", "lsu", "dieu_tra_loi"),
    )

    assert results["tri_thuc"] is True
    assert results["tong_hop"] is True
    assert results["lsu"] is False  # Failed gracefully
    assert results["dieu_tra_loi"] is True  # Proceeded despite lsu failure
