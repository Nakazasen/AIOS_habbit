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
import time
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
        coll_id = getattr(pipe_config, "collection_id", None)
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

    assert results["tri_thuc"] is True
    assert results["tong_hop"] is True
    assert results["lsu"] is True
    assert results["dieu_tra_loi"] is True

    # Bất biến: cả 4 khối đều được gọi làm ấm không chặn (blocking=False)
    assert len(warmed_calls) == 4
    for call in warmed_calls:
        assert call["blocking"] is False

    # 3 khối ban đầu mang collection_id tương ứng
    initial_colls = [c["collection"] for c in warmed_calls[:3]]
    assert set(initial_colls) == {"tong_hop", "lsu", "dieu_tra_loi"}

    # Riêng tri_thuc mang pipe_config thật không-None (DESKTOP-SPEED-TRITHUC-WARM-FIX-HOME)
    tri_thuc_call = warmed_calls[3]
    assert tri_thuc_call["pipe_config"] is not None


def test_startup_warming_resilience_to_single_collection_failure(monkeypatch):
    """Failure warming one collection must not crash app or block other collections."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, requested_profile="bge_m3_hybrid")

    warmed_calls = []

    def mock_warming_with_failure(*, config=None, blocking=False, pipe_config=None, **kwargs):
        coll_id = getattr(pipe_config, "collection_id", None)
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


def test_warm_priority_scope_activation_and_deactivation():
    """Verify set_user_retrieval_active, set_user_retrieval_finished, and scope manager."""
    adapter.set_user_retrieval_active("dieu_tra_loi")
    try:
        assert adapter._ACTIVE_USER_RETRIEVAL_COUNT >= 1
        assert "dieu_tra_loi" in adapter._ACTIVE_USER_RETRIEVAL_COLLECTIONS
    finally:
        adapter.set_user_retrieval_finished("dieu_tra_loi")

    with adapter.user_retrieval_priority_scope("lsu"):
        assert adapter._ACTIVE_USER_RETRIEVAL_COUNT >= 1
        assert "lsu" in adapter._ACTIVE_USER_RETRIEVAL_COLLECTIONS

    assert "lsu" not in adapter._ACTIVE_USER_RETRIEVAL_COLLECTIONS


def test_background_warm_does_not_yield_for_matching_collection():
    """When user retrieval is active for dieu_tra_loi, warming dieu_tra_loi must proceed immediately."""
    with adapter.user_retrieval_priority_scope("dieu_tra_loi"):
        # Calling _check_and_yield_background_warming for dieu_tra_loi must return immediately
        t0 = time.monotonic()
        adapter._check_and_yield_background_warming("dieu_tra_loi", None, max_yield_timeout_s=5.0)
        assert (time.monotonic() - t0) < 0.5


def test_background_warm_yields_for_unrelated_collection():
    """When user retrieval is active for dieu_tra_loi, warming tong_hop must yield until user retrieval finishes."""
    import threading

    yield_completed = []

    def warm_worker():
        adapter._check_and_yield_background_warming("tong_hop", None, max_yield_timeout_s=5.0)
        yield_completed.append(True)

    with adapter.user_retrieval_priority_scope("dieu_tra_loi"):
        th = threading.Thread(target=warm_worker, daemon=True)
        th.start()
        time.sleep(0.3)
        # Background worker must be yielding (not completed yet)
        assert len(yield_completed) == 0

    # Once scope exits, background worker must resume and complete
    th.join(timeout=2.0)
    assert len(yield_completed) == 1


def test_warm_priority_scope_tri_thuc_and_default_equivalence():
    """Verify that tri_thuc and default are treated as aliases for the unified knowledge block."""
    # 1. Scoping with default activates both default and tri_thuc
    with adapter.user_retrieval_priority_scope("default"):
        assert "default" in adapter._ACTIVE_USER_RETRIEVAL_COLLECTIONS
        assert "tri_thuc" in adapter._ACTIVE_USER_RETRIEVAL_COLLECTIONS

        # Checking tri_thuc must proceed immediately without yielding
        t0 = time.monotonic()
        adapter._check_and_yield_background_warming("tri_thuc", None, max_yield_timeout_s=5.0)
        assert (time.monotonic() - t0) < 0.5

        # Checking default must proceed immediately without yielding
        t0 = time.monotonic()
        adapter._check_and_yield_background_warming("default", None, max_yield_timeout_s=5.0)
        assert (time.monotonic() - t0) < 0.5

    # 2. Scoping with tri_thuc activates both default and tri_thuc
    with adapter.user_retrieval_priority_scope("tri_thuc"):
        assert "default" in adapter._ACTIVE_USER_RETRIEVAL_COLLECTIONS
        assert "tri_thuc" in adapter._ACTIVE_USER_RETRIEVAL_COLLECTIONS

        t0 = time.monotonic()
        adapter._check_and_yield_background_warming("default", None, max_yield_timeout_s=5.0)
        assert (time.monotonic() - t0) < 0.5


def test_background_warm_does_not_timeout_while_user_active():
    """Verify that unrelated collection does NOT timeout after 60s while user retrieval is active."""
    import threading

    yield_completed = []

    def warm_worker():
        # Even with max_yield_timeout_s=1.0, worker must NOT exit while user retrieval is active
        adapter._check_and_yield_background_warming("dieu_tra_loi", None, max_yield_timeout_s=1.0)
        yield_completed.append(True)

    with adapter.user_retrieval_priority_scope("tri_thuc"):
        th = threading.Thread(target=warm_worker, daemon=True)
        th.start()
        # Wait 2.0s (longer than 1.0s timeout)
        time.sleep(2.0)
        # Background worker must still be yielding (NOT timed out)
        assert len(yield_completed) == 0

    # Once user scope finishes, worker resumes and completes
    th.join(timeout=2.0)
    assert len(yield_completed) == 1


def test_select_domain_route_skips_fallback_when_confidence_low():
    """When question has no domain keyword signals (confidence < 0.4), domain routing does NOT force dieu_tra_loi."""
    from aios_habit.index_domain import Classification, DOMAIN_DIEU_TRA_LOI, CONFIDENCE_LOW_THRESHOLD

    cfg = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        requested_profile="bge_m3_hybrid",
    )
    # Question about general regulations/knowledge base
    q = "Theo tài liệu trong kho tri thức hợp nhất, quy định chung và các văn bản nghiệp vụ hướng dẫn vận hành hệ thống là gì?"
    route = adapter._select_domain_route(q, (), cfg, forced_domain="auto")
    # Must NOT force route to dieu_tra_loi
    if route is not None:
        assert route.applied is False or route.domain != DOMAIN_DIEU_TRA_LOI or (
            route.detected is not None and route.detected.confidence >= CONFIDENCE_LOW_THRESHOLD
        )

