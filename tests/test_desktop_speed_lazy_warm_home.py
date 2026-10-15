"""Unit tests for DESKTOP-SPEED-LAZY-WARM-HOME.

Verifies:
1. Lazy Startup Warming: ensure_workspace_chat_startup_warming() with default collections=None
   warms ONLY the active/default notebook collection (1 worker) and does NOT spawn workers
   for the remaining 3 collections.
2. Active Notebook Resolution: resolve_active_notebook_collection_id resolves the active
   notebook's collection_id (e.g. lsu, dieu_tra_loi, tong_hop, tri_thuc) or falls back to
   the first active notebook / tri_thuc.
3. On-Demand Notebook Switch Warming: open_notebook_callback and trigger_collection_warming_on_demand
   trigger non-blocking worker warming for the switched notebook's collection.
4. Cross-Collection & Auto-Routed Query Warming: retrieve_workspace_chat_evidence and
   _run_chat_turn_async automatically trigger warming for a missing target collection
   (both explicit forced_domain and Auto domain-routed queries) and wait until ready without
   skipping the collection.
5. UI Warming Status Line: format_worker_warming_status_line renders clear Vietnamese progress
   messages with step details while warming, and returns empty string when ready.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from threading import Lock
from unittest.mock import MagicMock

import pytest

import aios_habit.workspace_chat_rag_v2_adapter as adapter
import aios_habit.workspace_chat_app as chat_app


def _mock_pipe_cfg_factory():
    def _mock_pipe_cfg(cfg, profile, *, read_only=True, include_reranker=False, collection_id=None):
        mock_obj = MagicMock()
        mock_obj.collection_id = collection_id or "tri_thuc"
        mock_obj.runtime_root = Path(f"C:/fake_runtime/{collection_id or 'tri_thuc'}")
        mock_obj.index_path = MagicMock()
        mock_obj.index_path.is_file.return_value = True
        return mock_obj

    return _mock_pipe_cfg


def test_startup_warming_default_only_warms_single_active_collection_tri_thuc(monkeypatch):
    """Startup warming with collections=None must ONLY warm 1 collection (tri_thuc by default), NOT 4."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, requested_profile="bge_m3_hybrid")

    warmed_calls: list[dict[str, object]] = []

    def mock_warming(*, config=None, blocking=False, pipe_config=None, collection_id=None, **kwargs):
        coll = collection_id or getattr(pipe_config, "collection_id", None) or "tri_thuc"
        warmed_calls.append(
            {
                "collection": coll,
                "blocking": blocking,
                "pipe_config": pipe_config,
            }
        )
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming)
    monkeypatch.setattr(adapter, "_pipeline_config", _mock_pipe_cfg_factory())

    expected_tri_thuc_cfg = MagicMock()
    expected_tri_thuc_cfg.collection_id = "tri_thuc"
    monkeypatch.setattr(adapter, "_warmup_pipeline_config", lambda cfg: expected_tri_thuc_cfg)
    monkeypatch.setattr(
        "aios_habit.workspace_chat_store.load_active_notebooks",
        lambda: [SimpleNamespace(id="nb-1", collection_id="tri_thuc")],
    )

    results = adapter.ensure_workspace_chat_startup_warming(config=config)

    assert len(warmed_calls) == 1
    assert warmed_calls[0]["collection"] == "tri_thuc"
    assert warmed_calls[0]["blocking"] is False
    assert warmed_calls[0]["pipe_config"] is expected_tri_thuc_cfg
    assert list(results.keys()) == ["tri_thuc"]
    assert results["tri_thuc"] is True
    for unused_col in ("lsu", "dieu_tra_loi", "tong_hop"):
        assert unused_col not in results


def test_startup_warming_default_warms_only_active_notebook_collection_lsu(monkeypatch):
    """When active notebook uses 'lsu', startup warming warms ONLY 'lsu' and skips the other 3 collections."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, requested_profile="bge_m3_hybrid")

    warmed_calls: list[str] = []

    def mock_warming(*, config=None, blocking=False, pipe_config=None, collection_id=None, **kwargs):
        coll = str(collection_id or getattr(pipe_config, "collection_id", None) or "")
        warmed_calls.append(coll)
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming)
    monkeypatch.setattr(adapter, "_pipeline_config", _mock_pipe_cfg_factory())
    monkeypatch.setattr(
        "aios_habit.workspace_chat_store.load_active_notebooks",
        lambda: [
            SimpleNamespace(id="nb-general", collection_id="tri_thuc"),
            SimpleNamespace(id="nb-lsu", collection_id="lsu"),
        ],
    )

    results = adapter.ensure_workspace_chat_startup_warming(
        config=config,
        active_notebook_id="nb-lsu",
    )

    assert warmed_calls == ["lsu"]
    assert results == {"lsu": True}
    for unused_col in ("tri_thuc", "dieu_tra_loi", "tong_hop"):
        assert unused_col not in warmed_calls


def test_on_demand_warming_when_switching_notebook(monkeypatch):
    """Switching notebook via open_notebook_callback or trigger_collection_warming_on_demand warms the target collection."""
    warmed_collections: list[tuple[str | None, bool]] = []

    def mock_warming(*, config=None, blocking=False, pipe_config=None, collection_id=None, **kwargs):
        warmed_collections.append((collection_id, blocking))
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming)
    monkeypatch.setattr(
        chat_app,
        "load_active_notebooks",
        lambda: [
            SimpleNamespace(id="nb-dtl", title="Sổ Điều tra lỗi", collection_id="dieu_tra_loi"),
        ],
    )
    monkeypatch.setattr(
        "aios_habit.workspace_chat_store.load_active_notebooks",
        lambda: [
            SimpleNamespace(id="nb-dtl", title="Sổ Điều tra lỗi", collection_id="dieu_tra_loi"),
        ],
    )
    monkeypatch.setattr(chat_app, "set_query_params", lambda **kwargs: None)
    monkeypatch.setattr(chat_app, "safe_rerun", lambda: None)

    chat_app.open_notebook_callback("nb-dtl")

    assert warmed_collections == [("dieu_tra_loi", False)]


def test_cross_collection_and_auto_routed_queries_trigger_on_demand_warming(monkeypatch, tmp_path):
    """When a query targets an un-warmed collection (explicitly or via Auto routing), warming is triggered on demand."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        requested_profile="bge_m3_hybrid",
        runtime_root=tmp_path,
    )

    monkeypatch.setattr(adapter, "_pipeline_config", _mock_pipe_cfg_factory())
    monkeypatch.setattr(adapter, "_domain_index_ready", lambda cfg, cid: True)
    monkeypatch.setattr(adapter, "query_might_be_structured_excel", lambda q: False)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "_persistent_applies", lambda cfg: True)

    # Simulate: tri_thuc is already warmed, but lsu and dieu_tra_loi are NOT warmed yet
    monkeypatch.setattr(
        adapter._SUBPROCESS_CLIENT,
        "is_ready",
        lambda cfg: getattr(cfg, "collection_id", None) == "tri_thuc",
    )

    triggered_warm_collections: list[str] = []

    def mock_warming(*, config=None, blocking=False, pipe_config=None, collection_id=None, **kwargs):
        coll = str(collection_id or getattr(pipe_config, "collection_id", None) or "")
        triggered_warm_collections.append(coll)
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming)

    # 1. Explicit cross-collection query (forced_domain='lsu')
    res_lsu = adapter.retrieve_workspace_chat_evidence(
        "Thông số bowskew tại trạm fin test là bao nhiêu?",
        (),
        config=config,
        forced_domain="lsu",
    )
    assert res_lsu["status"] == "quality_search_unavailable"
    assert res_lsu["rag_v2_canary"]["fallback_reason"] == "bge_worker_warming_in_progress"
    assert res_lsu["domain_routing"]["applied"] is True
    assert res_lsu["domain_routing"]["collection_id"] == "lsu"
    assert "lsu" in triggered_warm_collections

    # 2. Auto-routed query requiring dieu_tra_loi (forced_domain='auto')
    triggered_warm_collections.clear()
    res_auto_dtl = adapter.retrieve_workspace_chat_evidence(
        "Trong báo cáo điều tra lỗi C7620 (KTD-2026-02-0244), nguyên nhân và đối sách là gì?",
        (),
        config=config,
        forced_domain="auto",
    )
    assert res_auto_dtl["status"] == "quality_search_unavailable"
    assert res_auto_dtl["rag_v2_canary"]["fallback_reason"] == "bge_worker_warming_in_progress"
    assert res_auto_dtl["domain_routing"]["applied"] is True
    assert res_auto_dtl["domain_routing"]["collection_id"] == "dieu_tra_loi"
    assert "dieu_tra_loi" in triggered_warm_collections


def test_format_worker_warming_status_line_shows_collection_and_steps():
    """format_worker_warming_status_line must show collection name and step details until ready."""
    line_step1 = chat_app.format_worker_warming_status_line(
        "lsu",
        progress={"ready": False, "alive": False, "pending": False},
        locale="vi",
    )
    assert "Đang nạp bộ đọc cho kho LSU" in line_step1
    assert "Bước 1/2" in line_step1

    line_step2 = chat_app.format_worker_warming_status_line(
        "dieu_tra_loi",
        progress={"ready": False, "alive": True, "pending": True, "pid": 43210},
        locale="vi",
    )
    assert "Đang nạp bộ đọc cho kho Điều tra lỗi" in line_step2
    assert "Bước 2/2" in line_step2
    assert "PID 43210" in line_step2

    line_ready = chat_app.format_worker_warming_status_line(
        "lsu",
        progress={"ready": True, "alive": True, "pending": False},
        locale="vi",
    )
    assert line_ready == ""


def test_notebook_title_domain_inference_for_default_tri_thuc(monkeypatch):
    """A notebook created with default collection_id='tri_thuc' but titled 'Điều tra lỗi LSU' resolves to 'lsu'."""
    monkeypatch.setattr(
        "aios_habit.workspace_chat_store.load_notebook",
        lambda nb_id: SimpleNamespace(
            id=nb_id,
            title="Điều tra lỗi LSU",
            description="Sổ tra cứu lỗi LSU",
            collection_id="tri_thuc",
        )
        if nb_id == "NB-E35A7BEE"
        else None,
    )
    resolved = adapter.resolve_active_notebook_collection_id(
        active_notebook_id="NB-E35A7BEE",
        active_collection_id="tri_thuc",
    )
    assert resolved == "lsu"

