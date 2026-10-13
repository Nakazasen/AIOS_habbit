"""Tests for DESKTOP-SPEED-SEGMENT-MARKERS-FIX-HOME.

Verifies emission of the 3 marker groups:
1. [DRAFT_FALLBACK_COMPLETE] before returning draft answer in workspace_chat_app.py
2. [ROUTER_SYNTH_START] and [ROUTER_SYNTH_DONE] in antigravity_bridge.py
3. [RETRIEVAL_MICRO_TIMING] in workspace_chat_rag_v2_adapter.py
"""
from __future__ import annotations

import io
import sys
import time
from unittest.mock import MagicMock, patch

import pytest


def test_router_synth_markers_emitted(monkeypatch, tmp_path):
    """Verify [ROUTER_SYNTH_START] and [ROUTER_SYNTH_DONE] are printed during router execution."""
    from aios_habit.antigravity_bridge import route_workspace_chat_submission
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIAnswerResult
    import aios_habit.workspace_chat_store as store_mod

    log_file = tmp_path / "test_usage.jsonl"
    monkeypatch.setattr(store_mod, "EXTERNAL_AI_USAGE_FILE", log_file)

    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.antigravity_bridge._safe_print_streaming_marker", mock_safe_print)

    def mock_generate_answer(req, client):
        if req.on_chunk:
            req.on_chunk("Chunk 1 ")
        return WorkspaceAIAnswerResult(
            ok=True,
            answer_text="Chunk 1 test answer",
            included_source_titles=(),
            warnings=(),
            effective_provider="OpenAI Compatible",
            effective_model="deepseek/deepseek-v4.1-flash",
        )

    monkeypatch.setattr("aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer", mock_generate_answer)

    ok, msg, badge, err = route_workspace_chat_submission(
        question="Testing router synth markers?",
        evidence_items=[],
        packed_sources=(),
        conversation_id="CONV-ROUTER-MARKER-1",
        notebook_id="NB-1",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input="Testing router synth markers?",
        ai_mode="external",
    )

    assert ok is True
    assert any("[ROUTER_SYNTH_START] conv=CONV-ROUTER-MARKER-1 backend=nakazasen_router" in m for m in printed_markers)
    done_markers = [m for m in printed_markers if "[ROUTER_SYNTH_DONE]" in m]
    assert len(done_markers) == 1
    assert "conv=CONV-ROUTER-MARKER-1" in done_markers[0]
    assert "latency_s=" in done_markers[0]
    assert "ttft_s=" in done_markers[0]


def test_retrieval_micro_timing_marker_emitted(monkeypatch, tmp_path):
    """Verify [RETRIEVAL_MICRO_TIMING] is emitted in workspace_chat_rag_v2_adapter._run_profile."""
    from aios_habit.workspace_chat_rag_v2_adapter import _run_profile, WorkspaceChatRagV2CanaryConfig
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource

    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.workspace_chat_rag_v2_adapter._safe_print_streaming_marker", mock_safe_print)

    mock_client = MagicMock()
    mock_client.query_ready.return_value = {
        "status": "ok",
        "summary": {
            "filtered_as_stale_count": 0,
            "candidate_count": 10,
            "returned_count": 5,
            "indexed_chunk_count": 100,
            "dense_latency_ms": 85.5,
            "sparse_latency_ms": 120.0,
            "fusion_latency_ms": 45.0,
            "embed_latency_ms": 650.0,
            "dense_load_latency_ms": 0.0,
            "dense_resident": True,
        },
        "items": [],
        "routing": {},
        "synthesis": {},
    }
    monkeypatch.setattr("aios_habit.workspace_chat_rag_v2_adapter._SUBPROCESS_CLIENT", mock_client)

    dummy_model = tmp_path / "dummy_bge_m3"
    dummy_model.mkdir()
    cfg = WorkspaceChatRagV2CanaryConfig(
        bge_m3_model_path=dummy_model,
        bge_m3_model_revision="rev1",
        bge_m3_model_checksum="sha256:dummy",
    )
    source = WorkspaceAIContextSource(
        source_id="S-1",
        source_scope="notebook",
        source_type="plain_text",
        title="Test Source",
        privacy_label="local_only",
        text="Sample content",
        included_chars=14,
        truncated=False,
    )

    res = _run_profile(
        question="Testing retrieval micro timing?",
        sources=(source,),
        config=cfg,
        profile="bge_m3_hybrid",
        fallback_reason="",
        pipeline_factory=MagicMock(),
        domain_collection_id="lsu",
    )

    assert res["retrieval_applied"] is True
    micro_markers = [m for m in printed_markers if "[RETRIEVAL_MICRO_TIMING]" in m]
    assert len(micro_markers) == 1
    marker = micro_markers[0]
    assert "collection=lsu" in marker
    assert "embed_ms=650.00" in marker
    assert "dense_ms=85.50" in marker
    assert "sparse_ms=120.00" in marker
    assert "fuse_ms=45.00" in marker
    assert "dense_resident=True" in marker
    assert "dense_state=thuong_tru" in marker
    assert "dense_load_ms=0.00" in marker


def test_draft_fallback_complete_marker_emitted(monkeypatch):
    """Verify [DRAFT_FALLBACK_COMPLETE] is emitted before return draft_res in _run_chat_turn_async."""
    from aios_habit.workspace_chat_app import _run_chat_turn_async
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource

    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.workspace_chat_app._safe_print_streaming_marker", mock_safe_print)

    # Mock retrieval to return summary_count == 0 to trigger draft branch
    def mock_retrieval(*args, **kwargs):
        return {
            "status": "ok",
            "summary_count": 0,
            "retrieved_context_sources": (),
            "evidence_items": [],
            "safe_owner_message": "",
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        mock_retrieval,
    )

    # Mock deliver_draft_answer to return a valid tuple
    def mock_deliver(*args, **kwargs):
        return (True, "Draft answer text", {"provider": "Bản thảo ChatGPT"}, None)

    monkeypatch.setattr(
        "aios_habit.answer_draft_fallback.deliver_draft_answer",
        mock_deliver,
    )

    source = WorkspaceAIContextSource(
        source_id="S-1",
        source_scope="notebook",
        source_type="plain_text",
        title="Test Source",
        privacy_label="local_only",
        text="Sample content",
        included_chars=14,
        truncated=False,
    )

    res = _run_chat_turn_async(
        q_text="File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?",
        query_relevant_sources=(source,),
        conversation_id="CONV-DRAFT-MARKER-1",
    )

    assert res[0] is True
    draft_markers = [m for m in printed_markers if "[DRAFT_FALLBACK_COMPLETE]" in m]
    assert len(draft_markers) == 1
    assert "conv=CONV-DRAFT-MARKER-1" in draft_markers[0]
    assert "wait_s=" in draft_markers[0]
    assert "total_s=" in draft_markers[0]
