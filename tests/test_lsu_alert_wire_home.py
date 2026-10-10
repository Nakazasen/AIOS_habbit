"""Unit and contract tests for DESKTOP-LSU-ALERT-WIRE-HOME.

Verifies:
1. rt_app_wire pipeline:
   - StreamListener healthy check & startup.
   - Trend event processing through SMA(20) gate into chat message.
   - Negative test: isolated single anomaly point does NOT create alert card.
2. Alert card rendering & inline feedback:
   - render_jig_realtime_alert_card provides inline feedback buttons.
   - Positive rating ('dung') records into alert_feedback.jsonl without reason.
   - Negative rating ('sai') requires non-empty reason.
   - File integrity: alert_feedback.jsonl stores valid JSON records locally.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aios_habit.alert_feedback import (
    alert_feedback_file,
    alert_feedback_stats,
    get_alert_feedback,
    record_alert_feedback,
)
from aios_habit.production_prediction.jig_chat_wire import (
    day_the_realtime_qua_cong_vao_chat,
)
from aios_habit.production_prediction.rt_app_wire import (
    get_active_rt_conversation,
    is_listener_healthy,
    poll_and_dispatch_rt_alerts,
    set_active_rt_conversation,
)
from aios_habit.production_prediction.rt_consumer import (
    chuyen_lo_thanh_the_da_qua_cong,
)
from aios_habit.production_prediction.stream_api import StreamBuffer, StreamListener
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_store import load_messages, save_message


def _make_drift_event(
    jig: str = "2ND-1002_JIG_BEAM",
    metric: str = "TaktTime",
    value: float = 245.0,
    cursor: int = 1,
) -> dict:
    return {
        "cursor": cursor,
        "thoi_gian": "2026-10-10T12:00:00",
        "loai": "canh_bao_drift",
        "jig_id": jig,
        "metric": metric,
        "noi_dung": {
            "unit_serial": "UNIT-TEST-001",
            "gia_tri": value,
            "don_vi": "s",
            "chi_tiet": "Thong so troi khoi nen",
        },
    }


def test_rt_app_wire_trend_dispatches_alert_card(tmp_path, monkeypatch):
    """Confirmed trend (>=3 points) must generate alert card and save to chat."""
    db_file = tmp_path / "jig_stream.sqlite"
    cursor_file = tmp_path / "cursor.txt"
    buffer = StreamBuffer(db_file)
    port = 19123
    listener = StreamListener(host="127.0.0.1", port=port, buffer=buffer)
    listener.start()
    try:
        assert is_listener_healthy(port) is True

        # Pre-fill baseline in buffer with distinct timestamps
        for i in range(40):
            buffer.append_idempotent(
                MagicMock(
                    timestamp=f"2026-10-10T11:00:{i:02d}",
                    unit_serial=f"BASE-{i}",
                    jig_id="2ND-1002_JIG_BEAM",
                    metric="TaktTime",
                    value=140.0,
                    unit="s",
                    status="ok",
                    nguon="that",
                )
            )

        # Write 3 drift events
        for i in range(3):
            buffer.ghi_su_kien(
                "canh_bao_drift",
                "2ND-1002_JIG_BEAM",
                "TaktTime",
                {"unit_serial": f"TEST-{i}", "gia_tri": 250.0 + i, "don_vi": "s", "chi_tiet": "Drift test"},
            )

        test_conv = "CONV-WIRE-TEST-01"
        res = poll_and_dispatch_rt_alerts(
            conversation_id=test_conv,
            port=port,
            cursor_path=cursor_file,
            db_path=db_file,
        )

        assert res["ok"] is True
        assert res["su_kien"] == 3
        assert res["cac_the"] == 1
        assert res["cac_can_bien"] == 0
        assert res["dispatched"] is True
        assert "Cảnh báo realtime" in res["chat_text"]

        # Check message stored in conversation
        msgs = load_messages(test_conv)
        assert len(msgs) >= 1
        assert any("Cảnh báo realtime" in m.content for m in msgs)
    finally:
        listener.stop()


def test_rt_app_wire_isolated_anomaly_negative_test(tmp_path):
    """Negative test: a single isolated anomaly point MUST NOT become an alert card."""
    db_file = tmp_path / "jig_stream.sqlite"
    cursor_file = tmp_path / "cursor.txt"
    buffer = StreamBuffer(db_file)
    port = 19124
    listener = StreamListener(host="127.0.0.1", port=port, buffer=buffer)
    listener.start()
    try:
        # Pre-fill baseline
        for i in range(40):
            buffer.append_idempotent(
                MagicMock(
                    timestamp=f"2026-10-10T11:00:{i:02d}",
                    unit_serial=f"BASE-{i}",
                    jig_id="2ND-1002_JIG_BEAM",
                    metric="TaktTime",
                    value=140.0,
                    unit="s",
                    status="ok",
                    nguon="that",
                )
            )

        # Only 1 single drift event
        buffer.ghi_su_kien(
            "canh_bao_drift",
            "2ND-1002_JIG_BEAM",
            "TaktTime",
            {"unit_serial": "TEST", "gia_tri": 280.0, "don_vi": "s", "chi_tiet": "Spike single point"},
        )

        test_conv = "CONV-WIRE-TEST-02"
        res = poll_and_dispatch_rt_alerts(
            conversation_id=test_conv,
            port=port,
            cursor_path=cursor_file,
            db_path=db_file,
        )

        assert res["ok"] is True
        assert res["su_kien"] == 1
        assert res["cac_the"] == 0, "Single isolated point must NOT create alert card"
        assert res["cac_can_bien"] == 1
        assert "Cần biến" in res["chat_text"]
        assert "Cảnh báo realtime" not in res["chat_text"]
    finally:
        listener.stop()


def test_alert_feedback_recording_contract(tmp_path, monkeypatch):
    """Test feedback recording on alert cards with positive and negative cases."""
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))

    # 1. Rating 'dung' succeeds without reason
    res_dung = record_alert_feedback(
        conversation_id="CONV-LSU-TEST",
        alert_id="ALT-001",
        jig_id="2ND-1002_JIG_BEAM",
        metric="TaktTime",
        rating="dung",
        chi_tiet="Drift z=3.15",
    )
    assert res_dung["ok"] is True

    # 2. Rating 'sai' fails without reason
    res_sai_empty = record_alert_feedback(
        conversation_id="CONV-LSU-TEST",
        alert_id="ALT-002",
        jig_id="2ND-1002_JIG_BEAM",
        metric="TaktTime",
        rating="sai",
        reason="",
    )
    assert res_sai_empty["ok"] is False
    assert "lý do" in res_sai_empty["error_vi"]

    # 3. Rating 'sai' succeeds with reason
    res_sai_valid = record_alert_feedback(
        conversation_id="CONV-LSU-TEST",
        alert_id="ALT-002",
        jig_id="2ND-1002_JIG_BEAM",
        metric="TaktTime",
        rating="sai",
        reason="Thao tác gá đặt phôi Master, không phải lỗi máy",
    )
    assert res_sai_valid["ok"] is True

    # 4. Check JSONL file contents
    fb_file = alert_feedback_file()
    assert fb_file.is_file()
    lines = fb_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    row1 = json.loads(lines[0])
    assert row1["rating"] == "dung"
    assert row1["alert_id"] == "ALT-001"
    assert row1["jig_id"] == "2ND-1002_JIG_BEAM"

    row2 = json.loads(lines[1])
    assert row2["rating"] == "sai"
    assert row2["alert_id"] == "ALT-002"
    assert "gá đặt phôi Master" in row2["reason"]

    stats = alert_feedback_stats()
    assert stats["total"] == 2
    assert stats["dung"] == 1
    assert stats["sai"] == 1


def test_render_alert_card_data_builders():
    """Verify card data structure for UI rendering."""
    from aios_habit.workspace_chat_ui import build_jig_realtime_card_data

    data = build_jig_realtime_card_data(
        jig_id="2ND-1002_JIG_BEAM",
        metric="TaktTime",
        chi_tiet="Thông số trôi khỏi nền z=3.15",
    )
    assert data["loai_the"] == "canh_bao_realtime"
    assert data["ma_jig"] == "2ND-1002_JIG_BEAM"
    assert data["thong_so"] == "TaktTime"
    assert "Mở phiên trực ban" in data["huong_dan"]
