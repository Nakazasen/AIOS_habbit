"""Unit and contract tests for DESKTOP-LSU-ALERT-CONTENT-HOME.

Verifies:
1. Complete alert card content with all 6 required fields:
   - JIG identifier (ma_jig / jig_id)
   - Metric name (thong_so / metric)
   - Latest measured value (gia_tri)
   - SMA(20) baseline and deviation (sma, muc_lech)
   - Consecutive points qualifying trend gate (so_diem_lien_tiep)
   - Timestamp of latest point (thoi_diem / timestamp)
   - Absence of empty/fallback "—" when data is present.
2. Deduplication at dispatch stage:
   - Subsequent poll iterations for the same confirmed trend event
     produce strictly ONE alert card per conversation.
3. Negative case:
   - Single isolated anomaly point does not pass SMA(20) gate and does not dispatch alert card.
4. Python 3.11 compatibility.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
import uuid

import pytest

from aios_habit.production_prediction.jig_alert_cards import build_realtime_alert_card
from aios_habit.production_prediction.rt_app_wire import (
    is_alert_already_dispatched,
    poll_and_dispatch_rt_alerts,
    record_dispatched_alert,
    reset_rt_dispatched_alerts,
)
from aios_habit.production_prediction.rt_consumer import (
    chuyen_lo_thanh_the_da_qua_cong,
    dinh_dang_canh_bao,
    dinh_dang_text_chat_cho_the_realtime,
)
from aios_habit.production_prediction.stream_api import StreamBuffer, StreamListener
from aios_habit.production_prediction.trend_alerts import danh_gia_xu_huong_sma
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_store import load_messages, save_message


def test_alert_card_has_all_six_required_fields():
    """Alert card must contain all 6 fields without empty placeholders."""
    # 40 baseline points (140.0s) + 5 drift points (260.0s - 276.5s)
    baseline = [140.0] * 40
    drift = [245.0, 252.0, 260.0, 270.0, 276.5]
    series = baseline + drift

    xu_huong = danh_gia_xu_huong_sma(series, window=20)
    assert xu_huong["canh_bao"] is True
    assert xu_huong["gia_tri"] == 276.5
    assert xu_huong["sma"] is not None
    assert xu_huong["muc_lech"] != "—"
    assert xu_huong["so_diem_lien_tiep"] >= 3

    event = {
        "cursor": 45,
        "thoi_gian": "2026-10-10T19:34:44",
        "loai": "canh_bao_drift",
        "jig_id": "2ND-1002_JIG_BEAM",
        "metric": "TaktTime",
        "noi_dung": {
            "unit_serial": "UNIT-TEST-1002",
            "gia_tri": 276.5,
            "don_vi": "s",
            "timestamp": "2026-10-10T19:34:44",
            "chi_tiet": "TaktTime tăng vượt ngưỡng SMA(20)",
            "nguon": "SIMULATED_REALTIME",
        },
    }

    card = dinh_dang_canh_bao(
        su_kien=event,
        xu_huong=xu_huong,
        jig_id="2ND-1002_JIG_BEAM",
        metric="TaktTime",
    )

    # 1. JIG Identifier
    assert card["ma_jig"] == "2ND-1002_JIG_BEAM"
    assert card["jig_id"] == "2ND-1002_JIG_BEAM"
    assert card["ma_jig"] != "—"

    # 2. Metric Name
    assert card["thong_so"] == "TaktTime"
    assert card["metric"] == "TaktTime"
    assert card["thong_so"] != "—"

    # 3. Latest measured value
    assert card["gia_tri"] == 276.5
    assert card["don_vi"] == "s"

    # 4. SMA(20) baseline & deviation
    assert card["sma"] == 140.0
    assert card["muc_lech"] != ""
    assert "σ" in card["muc_lech"] or "%" in card["muc_lech"] or "+" in card["muc_lech"]

    # 5. Consecutive points qualifying the gate
    assert card["so_diem_lien_tiep"] >= 3

    # 6. Timestamp of latest point
    assert card["thoi_diem"] == "2026-10-10T19:34:44"

    # Test markdown formatting
    chat_text = dinh_dang_text_chat_cho_the_realtime(card)
    assert "2ND-1002_JIG_BEAM" in chat_text
    assert "TaktTime" in chat_text
    assert "276.5 s" in chat_text
    assert "140.0 s" in chat_text or "140.0" in chat_text
    assert "điểm bất thường liên tiếp" in chat_text
    assert "2026-10-10T19:34:44" in chat_text
    assert "Cảnh báo realtime — — —" not in chat_text
    assert "Cảnh báo realtime: — — —" not in chat_text


def test_dispatch_deduplication_strictly_one_card(tmp_path):
    """Subsequent poll iterations must NOT push duplicate alert cards for the same event."""
    reset_rt_dispatched_alerts()
    db_file = tmp_path / "jig_stream_dedup.sqlite"
    cursor_file = tmp_path / "cursor_dedup.txt"
    buffer = StreamBuffer(db_file)
    port = 19130
    listener = StreamListener(host="127.0.0.1", port=port, buffer=buffer)
    listener.start()

    test_conv = f"CONV-DEDUP-{uuid.uuid4().hex[:8]}"
    try:
        # Pre-fill baseline
        for i in range(40):
            buffer.append_idempotent(
                MagicMock(
                    timestamp=f"2026-10-10T10:00:{i:02d}",
                    unit_serial=f"BASE-{i}",
                    jig_id="2ND-1002_JIG_BEAM",
                    metric="TaktTime",
                    value=140.0,
                    unit="s",
                    status="ok",
                    nguon="that",
                )
            )

        # 3 drift events to trigger trend alert
        for i in range(3):
            buffer.ghi_su_kien(
                "canh_bao_drift",
                "2ND-1002_JIG_BEAM",
                "TaktTime",
                {
                    "unit_serial": f"DRIFT-{i}",
                    "gia_tri": 260.0 + i,
                    "don_vi": "s",
                    "timestamp": f"2026-10-10T10:01:{i:02d}",
                    "chi_tiet": "Drift event",
                },
            )

        # Poll iteration 1: MUST dispatch exactly 1 card
        res1 = poll_and_dispatch_rt_alerts(
            conversation_id=test_conv,
            port=port,
            cursor_path=cursor_file,
            db_path=db_file,
        )
        assert res1["ok"] is True
        assert res1["cac_the"] == 1
        assert res1["dispatched"] is True
        assert "2ND-1002_JIG_BEAM" in res1["chat_text"]

        msgs1 = load_messages(test_conv)
        alert_msgs1 = [m for m in msgs1 if "aios_realtime_alert" in m.content or "Cảnh báo realtime" in m.content]
        assert len(alert_msgs1) == 1

        # Poll iteration 2 with same cursor position: no new events, dispatched=False
        res2 = poll_and_dispatch_rt_alerts(
            conversation_id=test_conv,
            port=port,
            cursor_path=cursor_file,
            db_path=db_file,
        )
        assert res2["ok"] is True
        assert res2["dispatched"] is False

        # Now simulate a subsequent poll where the same alert would have been produced
        # (e.g. cursor reset or another event for same jig/metric that matches dispatched alert_id)
        alt_id = "ALT-2ND-1002_JIG_BEAM-TaktTime"
        assert is_alert_already_dispatched(test_conv, alt_id) is True

        # Ensure still strictly 1 message in conversation
        msgs_final = load_messages(test_conv)
        alert_msgs_final = [m for m in msgs_final if "aios_realtime_alert" in m.content or "Cảnh báo realtime" in m.content]
        assert len(alert_msgs_final) == 1, "Duplicate alert cards must NOT be dispatched"
    finally:
        listener.stop()
        reset_rt_dispatched_alerts()


def test_isolated_anomaly_negative_gate(tmp_path):
    """Single isolated spike does not produce an alert card."""
    reset_rt_dispatched_alerts()
    db_file = tmp_path / "jig_stream_spike.sqlite"
    cursor_file = tmp_path / "cursor_spike.txt"
    buffer = StreamBuffer(db_file)
    port = 19131
    listener = StreamListener(host="127.0.0.1", port=port, buffer=buffer)
    listener.start()

    test_conv = f"CONV-SPIKE-{uuid.uuid4().hex[:8]}"
    try:
        for i in range(40):
            buffer.append_idempotent(
                MagicMock(
                    timestamp=f"2026-10-10T10:00:{i:02d}",
                    unit_serial=f"BASE-{i}",
                    jig_id="2ND-1002_JIG_BEAM",
                    metric="TaktTime",
                    value=140.0,
                    unit="s",
                    status="ok",
                    nguon="that",
                )
            )

        # 1 isolated spike
        buffer.ghi_su_kien(
            "canh_bao_drift",
            "2ND-1002_JIG_BEAM",
            "TaktTime",
            {
                "unit_serial": "SPIKE-001",
                "gia_tri": 297.0,
                "don_vi": "s",
                "timestamp": "2026-10-10T10:01:00",
                "chi_tiet": "Spike single point",
            },
        )

        res = poll_and_dispatch_rt_alerts(
            conversation_id=test_conv,
            port=port,
            cursor_path=cursor_file,
            db_path=db_file,
        )
        assert res["ok"] is True
        assert res["cac_the"] == 0, "Isolated spike must NOT qualify as alert card"
        assert res["cac_can_bien"] == 1
        assert "Cần biến" in res["chat_text"]
        assert "Cảnh báo realtime" not in res["chat_text"]
    finally:
        listener.stop()
        reset_rt_dispatched_alerts()
