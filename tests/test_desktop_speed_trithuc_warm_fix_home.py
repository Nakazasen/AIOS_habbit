"""Tests for DESKTOP-SPEED-TRITHUC-WARM-FIX-HOME.

Verifies:
1. ensure_workspace_chat_startup_warming passes explicit pipe_config for tri_thuc via _warmup_pipeline_config.
2. The pipe_config passed for tri_thuc is not None and is distinct from other collections.
3. Resilience: failure during tri_thuc warming does not crash or impact other collections.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import aios_habit.workspace_chat_rag_v2_adapter as adapter


def test_ensure_workspace_chat_startup_warming_passes_explicit_tri_thuc_pipe_config(monkeypatch):
    """ensure_workspace_chat_startup_warming must pass explicit pipe_config for tri_thuc."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, requested_profile="bge_m3_hybrid")

    warmed_calls = {}

    def mock_warming(*, config=None, blocking=False, pipe_config=None, **kwargs):
        coll = getattr(pipe_config, "collection_id", None) or "tri_thuc"
        warmed_calls[coll] = {
            "blocking": blocking,
            "pipe_config": pipe_config,
        }
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming)

    expected_tri_thuc_cfg = MagicMock()
    expected_tri_thuc_cfg.collection_id = "tri_thuc"

    monkeypatch.setattr(adapter, "_warmup_pipeline_config", lambda cfg: expected_tri_thuc_cfg)

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
    assert "tri_thuc" in warmed_calls
    assert warmed_calls["tri_thuc"]["pipe_config"] is not None
    assert warmed_calls["tri_thuc"]["pipe_config"] is expected_tri_thuc_cfg
    assert warmed_calls["tri_thuc"]["blocking"] is False


def test_tri_thuc_warming_failure_resilience(monkeypatch):
    """Failure resolving or warming tri_thuc must not crash or impact other collections."""
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, requested_profile="bge_m3_hybrid")

    def mock_pipe_cfg(cfg, profile, *, read_only=True, collection_id=None):
        mock_obj = MagicMock()
        mock_obj.collection_id = collection_id
        mock_obj.index_path = MagicMock()
        mock_obj.index_path.is_file.return_value = True
        return mock_obj

    monkeypatch.setattr(adapter, "_pipeline_config", mock_pipe_cfg)

    # Simulate _warmup_pipeline_config raising error
    def mock_warmup_fail(cfg):
        raise RuntimeError("simulated tri_thuc warmup failure")

    monkeypatch.setattr(adapter, "_warmup_pipeline_config", mock_warmup_fail)

    warmed_calls = {}

    def mock_warming(*, config=None, blocking=False, pipe_config=None, **kwargs):
        coll = getattr(pipe_config, "collection_id", None) or "tri_thuc"
        warmed_calls[coll] = True
        return True

    monkeypatch.setattr(adapter, "ensure_workspace_chat_worker_warming", mock_warming)

    results = adapter.ensure_workspace_chat_startup_warming(
        config=config,
        collections=("tong_hop", "lsu", "dieu_tra_loi"),
    )

    assert results["tri_thuc"] is False
    assert results["tong_hop"] is True
    assert results["lsu"] is True
    assert results["dieu_tra_loi"] is True
