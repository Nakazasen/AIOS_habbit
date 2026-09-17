"""Contract tests for Omnibar JIG log ingest (US12 T058)."""

from __future__ import annotations

from aios_habit.production_prediction.jig_log_ingest import (
    evaluate_single_log_ewma,
    is_jig_log_line,
    parse_jig_log_line,
    route_omnibar_message,
)


def test_nhan_dien_dong_log_jig_tho():
    line = "2026-09-20T08:00:00,UNIT001,JIG-BOWSKEW-4BEAM,bowskew,0.12,mm,OK"
    assert is_jig_log_line(line) is True
    parsed = parse_jig_log_line(line)
    assert parsed is not None
    assert parsed.unit_serial == "UNIT001"
    assert parsed.jig_id == "JIG-BOWSKEW-4BEAM"
    assert parsed.metric == "bowskew"
    assert parsed.value == 0.12


def test_phan_luong_chat_thuong_ve_rag():
    assert route_omnibar_message("Hôm nay JIG có gì bất thường?") == "rag"
    assert route_omnibar_message("") == "rag"


def test_phan_luong_cau_lenh_ve_agent():
    assert route_omnibar_message("Tạo báo cáo lỗi xưởng tuần này") == "agent"


def test_phan_luong_chuoi_log_ve_data_gate():
    line = "2026-09-20T08:01:00\tUNIT002\tJIG-01\tbowskew\t0.15\tmm\tOK"
    assert route_omnibar_message(line) == "jig_log"


def test_cam_phan_manh_ui_khong_tao_nut_rieng():
    # Contract: ingest works on the raw pasted string, no extra widgets.
    import inspect

    import aios_habit.production_prediction.jig_log_ingest as module

    source = inspect.getsource(module)
    assert "st.button" not in source
    assert "st.text_area" not in source


def test_danh_gia_ewma_thieu_du_lieu():
    result = evaluate_single_log_ewma(None, [0.1, 0.11, 0.12])
    assert result["trang_thai"] == "Thiếu dữ liệu"
    assert result["canh_bao"] is False


def test_danh_gia_ewma_can_bien_khi_thieu_nen():
    result = evaluate_single_log_ewma(0.12, [0.1, 0.11])
    assert result["trang_thai"] == "Cận biên"


def test_danh_gia_ewma_phat_hien_vi_pham():
    history = [0.10] * 30
    result = evaluate_single_log_ewma(0.50, history)
    assert result["trang_thai"] == "Vi phạm"
    assert result["canh_bao"] is True
