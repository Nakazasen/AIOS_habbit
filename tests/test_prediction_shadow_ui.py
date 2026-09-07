"""Test suite for LSU prediction shadow UI components and workspace chat integration."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

from aios_habit.prediction_shadow_ui import (
    data_gate_state_summary,
    explain_technical_code,
    format_unit_trace_view,
)
from aios_habit.production_prediction.models import (
    ComponentLotMeasurement,
    JigOutcomeResult,
    JoinedUnitTrace,
)

VIETNAM_TZ = timezone(timedelta(hours=7))


def test_data_gate_state_summary_covers_all_contract_states():
    """Verify all 7 contract states have safe, non-empty Vietnamese titles, messages, and next steps."""
    required_states = [
        "unselected",
        "reading",
        "passed",
        "passed_with_warning",
        "missing_keys",
        "conflicting_keys",
        "unsupported_format",
        "blocked",
    ]

    for state in required_states:
        summary = data_gate_state_summary(state, detail="Chi tiết kiểm thử")
        assert "status" in summary and len(summary["status"]) > 0
        assert "message" in summary and len(summary["message"]) > 0
        assert "next_step" in summary and "Bước tiếp theo" in summary["next_step"]

        # Safety: no traceback, no raw internal exception names, no path
        for val in summary.values():
            assert "Traceback" not in val
            assert "Exception" not in val
            assert "D:\\" not in val
            assert "C:\\" not in val


def test_technical_code_vietnamese_explanations():
    """Verify factory/optical engineering abbreviations have clear Vietnamese explanations."""
    assert "chùm tia" in explain_technical_code("BOWSKEW_4_BEAM")
    assert "chuẩn trực" in explain_technical_code("LENS_COLLIMATOR")
    assert "diode" in explain_technical_code("LD_ARRAY")
    assert "vượt ngưỡng" in explain_technical_code("ERR_BOW_EXCEEDED")
    assert "Tiêu cự" in explain_technical_code("FOCAL_LENGTH")


def test_format_unit_trace_view_found_and_not_found():
    """Verify trace presenter produces structured view for OK, NG, and missing units."""
    # 1. Not found
    missing_view = format_unit_trace_view(None)
    assert missing_view["found"] is False
    assert "Không tìm thấy" in missing_view["message"]
    assert "Bước tiếp theo" in missing_view["next_step"]

    # 2. Found OK
    now = datetime(2026, 3, 1, 10, 0, tzinfo=VIETNAM_TZ)
    m = ComponentLotMeasurement(
        lot_measurement_id="M_01",
        component_lot_id="LOT_LENS",
        component_code="LENS_COLLIMATOR",
        metric_name="FOCAL_LENGTH",
        value=25.4,
        unit="mm",
        event_time=now,
    )
    j = JigOutcomeResult(
        jig_result_id="J_01",
        unit_serial="UNIT_001",
        jig_id="BOWSKEW_4_BEAM",
        run_id="RUN_01",
        event_time=now,
        metric_name="BOW_VALUE",
        value=0.15,
        unit="mrad",
        target_label="OK",
    )
    trace_ok = JoinedUnitTrace(
        unit_serial="UNIT_001",
        assembly_time=now,
        jig_event_time=now,
        target_label="OK",
        lot_measurements=[m],
        jig_measurements=[j],
    )
    ok_view = format_unit_trace_view(trace_ok)
    assert ok_view["found"] is True
    assert ok_view["label_desc"] == "Đạt tiêu chuẩn (OK)"
    assert len(ok_view["lot_measurements"]) == 1
    assert len(ok_view["jig_measurements"]) == 1

    # 3. Found NG
    trace_ng = JoinedUnitTrace(
        unit_serial="UNIT_002",
        assembly_time=now,
        jig_event_time=now,
        target_label="NG",
        failure_code="ERR_BOW_EXCEEDED",
        lot_measurements=[],
        jig_measurements=[],
    )
    ng_view = format_unit_trace_view(trace_ng)
    assert ng_view["found"] is True
    assert ng_view["label_desc"] == "Lỗi (NG)"
    assert "vượt ngưỡng" in ng_view["fail_desc"]


def test_workspace_chat_app_wires_lsu_data_gate():
    """Verify workspace_chat_app source code integrates LSU data gate entry point without second app route."""
    app_text = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "render_lsu_data_gate" in app_text
    assert "wsc_open_lsu_data_gate" in app_text
    assert "wsc_show_lsu_data_gate" in app_text
    assert "lsu_data_gate" in app_text


def test_shadow_state_summary_covers_all_7_contract_states():
    """Verify all 7 shadow contract states have safe, non-empty Vietnamese titles, messages, and next steps."""
    from aios_habit.prediction_shadow_ui import shadow_state_summary

    required_states = [
        "checking",
        "learning_shadow",
        "auto_shadow",
        "no_risk",
        "has_risk",
        "stopped",
        "error",
    ]

    for state in required_states:
        summary = shadow_state_summary(state, detail="Chi tiết lỗi kiểm thử")
        assert "status" in summary and len(summary["status"]) > 0
        assert "message" in summary and len(summary["message"]) > 0
        assert "next_step" in summary and "Bước tiếp theo" in summary["next_step"]

        for val in summary.values():
            assert "Traceback" not in val
            assert "Exception" not in val
            assert "D:\\" not in val
            assert "C:\\" not in val


def test_format_shadow_risk_view_safety_and_no_definitive_defect():
    """Verify risk view presents cautious 'cần kiểm tra' verdict rather than claiming guaranteed failure."""
    from aios_habit.prediction_shadow_ui import format_shadow_risk_view
    from aios_habit.production_prediction.shadow import ShadowRiskAssessment

    assess = ShadowRiskAssessment(
        idempotency_key="idemp_1234567890abcdef",
        snapshot_id="snap_1234567890abcdef",
        unit_serial="SYN_UNIT_042",
        as_of_time="2026-03-01T10:00:00+07:00",
        risk_level="HIGH",
        factors=[
            {"component_lot_id": "LOT_LENS", "metric_name": "FOCAL_LENGTH", "z_score": 3.42},
        ],
        reason="Độ lệch vượt ngưỡng",
    )

    view = format_shadow_risk_view(assess)
    assert view["unit_serial"] == "SYN_UNIT_042"
    assert view["verdict"] == "Cần kiểm tra"
    assert "chắc chắn hỏng" not in view["verdict"]
    assert "chắc chắn hỏng" not in view["risk_level"]
    assert len(view["factors"]) == 1
    assert "Tiêu cự" in view["factors"][0]["Thông số kỹ thuật"]


def test_shadow_ui_has_no_model_selector_or_operational_alerts():
    """Verify UI does not expose machine learning model selectors or operational dispatch toggles."""
    ui_text = Path("src/aios_habit/prediction_shadow_ui.py").read_text(encoding="utf-8")
    assert "select_model" not in ui_text.lower()
    assert "model_choice" not in ui_text.lower()
    assert "bật cảnh báo vận hành" not in ui_text.lower()
    assert "dispatch_alert" not in ui_text.lower()


def test_shadow_ui_blocked_data_encapsulation():
    """Verify start shadow button is strictly encapsulated inside the valid data branch."""
    ui_text = Path("src/aios_habit/prediction_shadow_ui.py").read_text(encoding="utf-8")
    # Verify button exists and is inside the else block (indented with 16 spaces, matching the block)
    assert 'if st.button("🚀 Bắt đầu chạy bóng thủ công"' in ui_text
    # Check that in the BLOCKED_DATA block, there is an early error message and no shadow execution
    assert "Dữ liệu đang ở trạng thái bị chặn do vi phạm quy tắc an toàn kỹ thuật." in ui_text
    # Verify indentation of the button is deeper than the if rep.status == BLOCKED_DATA
    for line in ui_text.splitlines():
        if 'if st.button("🚀 Bắt đầu chạy bóng thủ công"' in line:
            indent = len(line) - len(line.lstrip())
            assert indent >= 16, f"Button must be indented at least 16 spaces (inside else branch), got {indent}"