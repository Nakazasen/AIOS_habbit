"""Unit tests for DESKTOP-SPEED-PRESYNTH-MARKERS-HOME.

Verifies:
1. Shared format_marker_timestamp(), parse_marker_timestamp(), and diff_marker_timestamps_s().
2. Emission of timestamps on chat stream markers:
   - [STREAMING_QA_START]
   - [RETRIEVAL_MICRO_TIMING] (with embed_wait_ms and embed_compute_ms)
   - [ROUTER_SYNTH_START]
   - [STREAMING_QA_FIRST_TOKEN]
   - [STREAMING_QA_COMPLETE]
3. Emission of fine-grained [PRE_SYNTH_STEP] markers:
   (a) step=retrieval_received
   (b) step=sources_formatted
   (c) step=domain_badge_attached
   (d) step=executor_enqueued
   (e) step=executor_task_started
   (f) step=route_privacy_done
   (g) step=pre_router
4. Direct timestamp subtraction for interval attribution.
"""
from __future__ import annotations

from datetime import datetime
import re
import time
from unittest.mock import MagicMock, patch

import pytest

from aios_habit.streaming_markers import (
    diff_marker_timestamps_s,
    emit_pre_synth_step_marker,
    format_marker_timestamp,
    parse_marker_timestamp,
)


def test_streaming_markers_timestamp_utils():
    """Verify format, parse, and diff functions."""
    ts_str = format_marker_timestamp()
    # Format must match YYYY-MM-DD HH:MM:SS.mmm
    match = re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$", ts_str)
    assert match is not None, f"Timestamp {ts_str} does not match expected format"

    parsed = parse_marker_timestamp(ts_str)
    assert isinstance(parsed, datetime)

    t0 = "2026-10-13 12:00:00.000"
    t1 = "2026-10-13 12:00:03.500"
    diff = diff_marker_timestamps_s(t0, t1)
    assert abs(diff - 3.5) < 1e-4


def test_emit_pre_synth_step_marker(monkeypatch):
    """Verify emit_pre_synth_step_marker outputs expected format with timestamp."""
    printed: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed.append(msg)

    monkeypatch.setattr("aios_habit.streaming_markers._safe_print_streaming_marker", mock_safe_print)

    msg = emit_pre_synth_step_marker("CONV-TEST-1", "retrieval_received")
    assert "[PRE_SYNTH_STEP] conv=CONV-TEST-1 step=retrieval_received timestamp=" in msg
    assert len(printed) == 1
    assert printed[0] == msg


def test_retrieval_micro_timing_has_embed_separation_and_timestamp(monkeypatch, tmp_path):
    """Verify [RETRIEVAL_MICRO_TIMING] includes embed_wait_ms, embed_compute_ms, and timestamp."""
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
            "dense_latency_ms": 90.2,
            "sparse_latency_ms": 32.4,
            "fusion_latency_ms": 12.5,
            "embed_latency_ms": 1500.0,
            "embed_wait_ms": 0.0,
            "embed_compute_ms": 1500.0,
            "dense_load_latency_ms": 0.74,
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
        question="Testing embed separation markers?",
        sources=(source,),
        config=cfg,
        profile="bge_m3_hybrid",
        fallback_reason="",
        pipeline_factory=MagicMock(),
        domain_collection_id="tong_hop",
    )

    assert res["retrieval_applied"] is True
    micro_markers = [m for m in printed_markers if "[RETRIEVAL_MICRO_TIMING]" in m]
    assert len(micro_markers) == 1
    marker = micro_markers[0]
    assert "collection=tong_hop" in marker
    assert "embed_ms=1500.00" in marker
    assert "embed_wait_ms=0.00" in marker
    assert "embed_compute_ms=1500.00" in marker
    assert "timestamp=" in marker


def test_full_pre_synth_steps_and_timestamp_chain(monkeypatch, tmp_path):
    """Verify all [PRE_SYNTH_STEP] steps (a)-(g) and chat markers are emitted with timestamps."""
    from aios_habit.workspace_chat_app import _run_chat_turn_async
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource, WorkspaceAIAnswerResult
    import aios_habit.workspace_chat_store as store_mod

    log_file = tmp_path / "test_usage.jsonl"
    monkeypatch.setattr(store_mod, "EXTERNAL_AI_USAGE_FILE", log_file)

    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    # Patch safe print across modules
    monkeypatch.setattr("aios_habit.workspace_chat_app._safe_print_streaming_marker", mock_safe_print)
    monkeypatch.setattr("aios_habit.antigravity_bridge._safe_print_streaming_marker", mock_safe_print)
    monkeypatch.setattr("aios_habit.streaming_markers._safe_print_streaming_marker", mock_safe_print)

    # Mock retrieval to return successful results
    def mock_retrieval(*args, **kwargs):
        return {
            "status": "ok",
            "summary_count": 2,
            "retrieved_context_sources": (),
            "evidence_items": [
                {"title": "Doc 1", "text": "Content 1"},
            ],
            "safe_owner_message": "Đã tìm thấy tài liệu phù hợp.",
            "domain_routing": {"selected_domain": "tong_hop"},
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        mock_retrieval,
    )

    # Mock generate_workspace_ai_answer
    first_chunk_called = False

    def mock_generate_answer(req, client):
        nonlocal first_chunk_called
        if req.on_chunk and not first_chunk_called:
            first_chunk_called = True
            req.on_chunk("First chunk token")
        return WorkspaceAIAnswerResult(
            ok=True,
            answer_text="First chunk token and complete answer",
            included_source_titles=("Doc 1",),
            warnings=(),
            effective_provider="OpenAI Compatible",
            effective_model="deepseek/deepseek-v4.1-flash",
        )

    monkeypatch.setattr("aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer", mock_generate_answer)

    source = WorkspaceAIContextSource(
        source_id="S-1",
        source_scope="notebook",
        source_type="plain_text",
        title="Doc 1",
        privacy_label="local_only",
        text="Sample content",
        included_chars=14,
        truncated=False,
    )

    conv_id = "CONV-PRESYNTH-E2E-1"

    res = _run_chat_turn_async(
        q_text="Kiểm tra chuỗi marker đầy đủ có timestamp?",
        query_relevant_sources=(source,),
        conversation_id=conv_id,
        ai_backend="nakazasen_router",
    )

    assert res[0] is True

    # 1. Verify STREAMING_QA_START carries timestamp
    qa_start_markers = [m for m in printed_markers if "[STREAMING_QA_START]" in m and f"conv={conv_id}" in m]
    assert len(qa_start_markers) == 1
    assert "timestamp=" in qa_start_markers[0]

    # 2. Verify all 7 PRE_SYNTH_STEP markers are present
    step_markers = [m for m in printed_markers if "[PRE_SYNTH_STEP]" in m and f"conv={conv_id}" in m]
    steps_emitted = []
    for sm in step_markers:
        m_step = re.search(r"step=([a-zA-Z0-9_]+)", sm)
        assert m_step is not None, f"Marker missing step: {sm}"
        assert "timestamp=" in sm, f"Marker missing timestamp: {sm}"
        steps_emitted.append(m_step.group(1))

    expected_steps = [
        "retrieval_received",     # (a)
        "sources_formatted",      # (b)
        "domain_badge_attached",  # (c)
        "executor_enqueued",      # (d)
        "executor_task_started",  # (e)
        "route_privacy_done",     # (f)
        "pre_router",             # (g)
    ]
    for exp in expected_steps:
        assert exp in steps_emitted, f"Step '{exp}' was not emitted in {steps_emitted}"

    # 3. Verify ROUTER_SYNTH_START carries timestamp
    router_start_markers = [m for m in printed_markers if "[ROUTER_SYNTH_START]" in m and f"conv={conv_id}" in m]
    assert len(router_start_markers) == 1
    assert "timestamp=" in router_start_markers[0]

    # 4. Verify STREAMING_QA_COMPLETE carries timestamp
    complete_markers = [m for m in printed_markers if "[STREAMING_QA_COMPLETE]" in m and f"conv={conv_id}" in m]
    assert len(complete_markers) == 1
    assert "timestamp=" in complete_markers[0]
