"""Contract tests for realtime JIG stream listener (US12 T063)."""

from __future__ import annotations

import json
import urllib.request

import pytest

from aios_habit.production_prediction.stream_api import (
    STREAM_PATH,
    StreamBuffer,
    StreamListener,
    decide_stream_event,
    parse_stream_record,
)


def test_phan_tich_ban_ghi_stream_hop_le():
    record = parse_stream_record({
        "timestamp": "2026-09-20T08:00:00",
        "unit_serial": "UNIT001",
        "jig_id": "JIG-01",
        "metric": "bowskew",
        "value": 0.12,
        "unit": "mm",
    })
    assert record.unit_serial == "UNIT001"
    assert record.value == 0.12


def test_tu_choi_ban_ghi_thieu_khoa():
    with pytest.raises(ValueError, match="Thiếu mã Unit"):
        parse_stream_record({"jig_id": "JIG-01", "metric": "bowskew"})


def test_bo_dem_luu_ngam_va_tinh_ewma(tmp_path):
    buffer = StreamBuffer(tmp_path / "stream.sqlite")
    for i in range(10):
        buffer.append(parse_stream_record({
            "unit_serial": f"UNIT{i:03d}",
            "jig_id": "JIG-01",
            "metric": "bowskew",
            "value": 0.10,
        }))
    assert len(buffer.recent_values("JIG-01", "bowskew")) == 10
    status = buffer.ewma_status("JIG-01", "bowskew")
    assert status["canh_bao"] is False


def test_quyet_dinh_lang_nghe_tinh_lang():
    assert decide_stream_event({"canh_bao": False}) == "silent"
    assert decide_stream_event({"canh_bao": True}) == "alert"


def test_http_listener_nhan_json_va_ndjson(tmp_path):
    buffer = StreamBuffer(tmp_path / "stream_http.sqlite")
    listener = StreamListener(host="127.0.0.1", port=18765, buffer=buffer)
    info = listener.start()
    try:
        assert "Đang lắng nghe" in info["trang_thai"]
        payload = json.dumps({
            "unit_serial": "UNIT900",
            "jig_id": "JIG-HTTP",
            "metric": "bowskew",
            "value": 0.11,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:18765{STREAM_PATH}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
        assert body["trang_thai"] == "Đã ghi nhận"
        assert len(buffer.recent_values("JIG-HTTP", "bowskew")) == 1
    finally:
        listener.stop()
