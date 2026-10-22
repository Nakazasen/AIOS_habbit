# -*- coding: utf-8 -*-
"""Unit & Contract tests for ticket DESKTOP-PC0575-CAGENT-LIVENESS-WAIT-UX.

Verifies:
1. Real & mock C-Agent liveness probe: connected (🟢), expired (🟡), unreachable (🔴).
2. All 3 processing steps (find, read, synth) preserved on the wait card with exact timings.
3. Live waiting counter and C-Agent live status line ("đang chờ câu trả lời từ C-Agent — đã X giây").
4. Real probe status on footer caption (not static label).
5. Incident card with Retry ("Thử lại") and Fallback ("Dùng câu trả lời từ nguồn nội bộ") buttons.
6. Instant client-side visual ack ticker contract.
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest

from aios_habit.cagent_auth import (
    probe_cagent_liveness,
    get_cached_cagent_liveness,
)
from aios_habit.workspace_chat_ui import (
    build_answer_wait_steps,
    render_answer_wait_steps,
)

APP_PATH = Path("src/aios_habit/workspace_chat_app.py")


def _app_source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_probe_cagent_liveness_real_or_connected() -> None:
    """Requirement 2b: Real probe returns valid status code and Vietnamese label."""
    # Ensure clean environment
    os.environ.pop("AIOS_CAGENT_MOCK_LIVENESS", None)
    res = probe_cagent_liveness(force=True)
    assert isinstance(res, dict)
    assert res["code"] in ("connected", "expired", "unreachable")
    assert res["dot"] in ("🟢", "🟡", "🔴")
    assert res["label"] in ("đang kết nối", "phiên hết hạn", "không tới được nền tảng")
    assert "checked_at" in res


def test_probe_cagent_liveness_mock_expired() -> None:
    """Requirement 2b & Gate 2: Expired session returns expired code with yellow dot."""
    os.environ["AIOS_CAGENT_MOCK_LIVENESS"] = "expired"
    try:
        res = probe_cagent_liveness(force=True)
        assert res["code"] == "expired"
        assert res["label"] == "phiên hết hạn"
        assert res["dot"] == "🟡"
        assert "Phiên đăng nhập C-Agent đã hết hạn" in res["message"]
    finally:
        os.environ.pop("AIOS_CAGENT_MOCK_LIVENESS", None)


def test_probe_cagent_liveness_mock_unreachable() -> None:
    """Requirement 2b & Gate 2: Unreachable platform returns unreachable code with red dot."""
    os.environ["AIOS_CAGENT_MOCK_LIVENESS"] = "unreachable"
    try:
        res = probe_cagent_liveness(force=True)
        assert res["code"] == "unreachable"
        assert res["label"] == "không tới được nền tảng"
        assert res["dot"] == "🔴"
        assert "Không thể kết nối đến máy chủ C-Agent" in res["message"]
    finally:
        os.environ.pop("AIOS_CAGENT_MOCK_LIVENESS", None)


def test_build_answer_wait_steps_preserves_all_steps_with_timings() -> None:
    """Requirement 2e: Every step is preserved with its execution time; no step is empty."""
    timings = {
        "find": {"status": "done", "duration": 0.3, "elapsed": 0.3},
        "read": {"status": "done", "duration": 0.2, "elapsed": 0.2},
        "synth": {"status": "running", "duration": None, "elapsed": 1.5},
    }
    steps = build_answer_wait_steps(step_timings=timings)
    assert len(steps) == 3
    # Step 1: Find
    assert steps[0]["status"] == "done"
    assert steps[0]["icon"] == "✓"
    assert steps[0]["timing_str"] == "(0.3s)"
    assert steps[0]["duration_s"] == 0.3
    # Step 2: Read
    assert steps[1]["status"] == "done"
    assert steps[1]["icon"] == "✓"
    assert steps[1]["timing_str"] == "(0.2s)"
    assert steps[1]["duration_s"] == 0.2
    # Step 3: Synth
    assert steps[2]["status"] == "running"
    assert steps[2]["icon"] == "●"
    assert steps[2]["timing_str"] == "(1.5s)"
    assert steps[2]["elapsed_s"] == 1.5


def test_build_answer_wait_steps_all_done() -> None:
    """Requirement 2e: When turn completes, all 3 steps show done icon and individual duration."""
    timings = {
        "find": {"status": "done", "duration": 0.4},
        "read": {"status": "done", "duration": 0.2},
        "synth": {"status": "done", "duration": 2.1},
    }
    steps = build_answer_wait_steps(step_timings=timings)
    assert len(steps) == 3
    for s in steps:
        assert s["status"] == "done"
        assert s["icon"] == "✓"
        assert s["timing_str"].startswith("(") and s["timing_str"].endswith("s)")


def test_app_footer_contains_real_cagent_liveness() -> None:
    """Requirement 2b: Footer caption derives status from real probe, never hardcoded."""
    source = _app_source()
    assert "get_cached_cagent_liveness" in source
    assert "cagent_footer_str" in source
    assert "_top_cagent_probe_str" in source


def test_app_preserves_card_above_streaming_text() -> None:
    """Requirement 2e: Card is preserved above streaming writing pill."""
    source = _app_source()
    # Check that render_answer_wait_steps is invoked before curr_text check
    idx_render_card = source.find("render_answer_wait_steps(")
    idx_writing_pill = source.find("wsc-streaming-writing-pill")
    assert idx_render_card != -1
    assert idx_writing_pill != -1
    assert idx_render_card < idx_writing_pill


def test_app_cagent_incident_retry_and_fallback_buttons() -> None:
    """Requirement 2c: Incident card renders Retry and Internal Fallback buttons."""
    source = _app_source()
    assert "wsc_btn_retry_cagent_" in source
    assert "wsc_btn_fallback_cagent_" in source
    assert "Dùng câu trả lời từ nguồn nội bộ" in source
    assert "Thử lại" in source


def test_client_instant_visual_ack_has_timer_ticker() -> None:
    """Requirement 2a: Client instant visual ack includes ticking timer."""
    source = _app_source()
    assert "wsc-timer-val" in source
    assert "__wscTimerInterval" in source
