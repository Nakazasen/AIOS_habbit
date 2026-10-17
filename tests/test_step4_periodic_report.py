"""Tests cho tính năng tự động sinh báo cáo xu hướng định kỳ theo tuần (Bước 4).

Xác thực:
1. Bảng tỉ lệ phát sinh theo đủ 5 chiều: model / line / cong doan / loai giay / may cap thap.
2. Số liệu báo cáo đối chiếu đếm tay được 100% từ kho log (count_ng, count_total, rate).
3. Cổng cảnh báo giữ nguyên chuẩn SMA(20) đã chốt:
   - Điểm xấu đơn lẻ -> "Cận biên", canh_bao = False (không báo ảo từ 1 điểm đơn lẻ).
   - Xu hướng xấu (>= 3 điểm bất thường liên tiếp) -> "Vi phạm", canh_bao = True.
   - Bình thường -> "Đạt", canh_bao = False.
4. Biểu đồ xu hướng (ASCII trực quan + Monozukuri SPC PNG).
5. Tự động xuất file báo cáo Markdown chuẩn nghiệp vụ.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from aios_habit.production_prediction.log_archive import DongKhoLog
from aios_habit.production_prediction.periodic_trend_report import (
    DIMENSIONS,
    DIMENSION_LABELS_VI,
    CanhBaoDinhKy,
    KetQuaBaoCaoDinhKy,
    bucket_tuan_tu_datetime,
    danh_gia_cong_sma_cho_chieu,
    render_chart_png_cho_nhom,
    sinh_markdown_bao_cao,
    tao_bao_cao_dinh_ky_tuan,
    tinh_bang_ti_le_5_chieu,
    trich_xuat_ban_ghi_tu_dong_kho,
    ve_bieu_do_ascii,
)


def _tao_du_lieu_mau_tuan() -> list[dict]:
    """Tạo tập dữ liệu mô phỏng 4 tuần có số đếm tay chính xác."""
    records = []
    # Tuần 2026-W31: 10 bản ghi, 2 NG (20%)
    for i in range(10):
        records.append({
            "unit_serial": f"U31-{i}",
            "jig_id": "2ND-1002",
            "metric_name": "TaktTime",
            "value": 140.0,
            "status": "NG" if i < 2 else "OK",
            "ts": "2026-08-01T08:00:00",
            "tep": "2026_08_Master.csv",
        })
    # Tuần 2026-W32: 10 bản ghi, 2 NG (20%)
    for i in range(10):
        records.append({
            "unit_serial": f"U32-{i}",
            "jig_id": "2ND-1002",
            "metric_name": "TaktTime",
            "value": 142.0,
            "status": "NG" if i < 2 else "OK",
            "ts": "2026-08-08T08:00:00",
            "tep": "2026_08_Master.csv",
        })
    # Tuần 2026-W33: 10 bản ghi, 1 NG (10%)
    for i in range(10):
        records.append({
            "unit_serial": f"U33-{i}",
            "jig_id": "2ND-1002",
            "metric_name": "TaktTime",
            "value": 141.0,
            "status": "NG" if i < 1 else "OK",
            "ts": "2026-08-15T08:00:00",
            "tep": "2026_08_Master.csv",
        })
    # Tuần 2026-W34: 10 bản ghi, 4 NG (40%)
    for i in range(10):
        records.append({
            "unit_serial": f"U34-{i}",
            "jig_id": "2ND-1002",
            "metric_name": "TaktTime",
            "value": 145.0,
            "status": "NG" if i < 4 else "OK",
            "ts": "2026-08-22T08:00:00",
            "tep": "2026_08_Master.csv",
        })
    return records


def test_trich_xuat_ban_ghi_du_5_chieu():
    """Bản ghi log được trích xuất thành đúng 5 chiều nghiệp vụ."""
    dong = DongKhoLog(
        ts="2026-08-20T10:00:00",
        ghi_luc="2026-10-17T08:00:00",
        nguon="that",
        tep="2026_08_Master.csv",
        unit_serial="61C1068E6210",
        jig_id="2ND-1002_JIG_BEAM",
        metric_name="BOW_B",
        value=0.25,
        unit="mm",
        target_label="NG",
    )
    rec = trich_xuat_ban_ghi_tu_dong_kho(dong)

    assert rec["model"] == "Iris LSU"
    assert rec["line"] == "Line 1"
    assert rec["stage"] == "JIG BEAM"
    assert rec["paper"] == "N/A (Cụm quang học)"
    assert rec["machine"] == "2ND-1002_JIG_BEAM"
    assert rec["is_ng"] is True
    assert rec["bucket"] == "2026-W34"


def test_bang_ti_le_doi_chieu_dem_tay():
    """Số liệu bảng tỉ lệ khớp 100% khi đếm tay."""
    recs = _tao_du_lieu_mau_tuan()
    all_recs = [trich_xuat_ban_ghi_tu_dong_kho(r) for r in recs]

    bang = tinh_bang_ti_le_5_chieu(all_recs, "machine")

    # Tuần W31: 2 NG / 10 tổng = 20.0%
    assert bang["2026-W31"]["2ND-1002"]["count_ng"] == 2
    assert bang["2026-W31"]["2ND-1002"]["count_total"] == 10
    assert bang["2026-W31"]["2ND-1002"]["rate"] == pytest.approx(0.20)

    # Tuần W33: 1 NG / 10 tổng = 10.0%
    assert bang["2026-W33"]["2ND-1002"]["count_ng"] == 1
    assert bang["2026-W33"]["2ND-1002"]["count_total"] == 10
    assert bang["2026-W33"]["2ND-1002"]["rate"] == pytest.approx(0.10)

    # Tuần W34: 4 NG / 10 tổng = 40.0%
    assert bang["2026-W34"]["2ND-1002"]["count_ng"] == 4
    assert bang["2026-W34"]["2ND-1002"]["count_total"] == 10
    assert bang["2026-W34"]["2ND-1002"]["rate"] == pytest.approx(0.40)


def test_cong_sma_diem_xau_don_le_la_can_bien_khong_canh_bao():
    """Điểm bất thường đơn lẻ vượt ngưỡng: Cận biên, canh_bao = False (không báo ảo)."""
    # 4 tuần bình thường 5% + 1 tuần vọt lên 40% (điểm xấu đơn lẻ)
    table = {
        "2026-W30": {"GroupA": {"rate": 0.05, "count_ng": 5, "count_total": 100}},
        "2026-W31": {"GroupA": {"rate": 0.05, "count_ng": 5, "count_total": 100}},
        "2026-W32": {"GroupA": {"rate": 0.05, "count_ng": 5, "count_total": 100}},
        "2026-W33": {"GroupA": {"rate": 0.05, "count_ng": 5, "count_total": 100}},
        "2026-W34": {"GroupA": {"rate": 0.40, "count_ng": 40, "count_total": 100}},
    }
    alerts = danh_gia_cong_sma_cho_chieu(table, "model", ky_hien_tai="2026-W34", threshold=0.20)
    assert len(alerts) == 1
    a = alerts[0]
    # Điểm xấu đơn lẻ chưa thành xu hướng -> Cận biên, KHÔNG cảnh báo
    assert a.trang_thai == "Cận biên"
    assert a.canh_bao is False
    assert "chưa thành xu hướng liên tiếp" in a.message or "không cảnh báo đơn lẻ" in a.message


def test_cong_sma_xu_huong_xau_lien_tiep_la_vi_pham():
    """Từ 3 tuần xấu liên tiếp trở lên: Vi phạm, canh_bao = True."""
    table = {
        "2026-W30": {"GroupA": {"rate": 0.05, "count_ng": 5, "count_total": 100}},
        "2026-W31": {"GroupA": {"rate": 0.05, "count_ng": 5, "count_total": 100}},
        "2026-W32": {"GroupA": {"rate": 0.30, "count_ng": 30, "count_total": 100}},
        "2026-W33": {"GroupA": {"rate": 0.35, "count_ng": 35, "count_total": 100}},
        "2026-W34": {"GroupA": {"rate": 0.40, "count_ng": 40, "count_total": 100}},
    }
    alerts = danh_gia_cong_sma_cho_chieu(table, "model", ky_hien_tai="2026-W34", threshold=0.20)
    assert len(alerts) == 1
    a = alerts[0]
    assert a.trang_thai == "Vi phạm"
    assert a.canh_bao is True
    assert a.so_diem_lien_tiep >= 3


def test_sinh_bao_cao_dinh_ky_toan_dien(tmp_path):
    """Kiểm thử sinh toàn bộ báo cáo Markdown + ảnh biểu đồ SPC PNG."""
    recs = _tao_du_lieu_mau_tuan()
    res = tao_bao_cao_dinh_ky_tuan(
        records=recs,
        ky_tuan="2026-W34",
        output_dir=tmp_path,
        nguong_ti_le=0.25,
        render_png=True,
    )

    assert res.ky_tuan == "2026-W34"
    assert res.tong_so_ban_ghi == 10
    assert res.tong_so_ng == 4
    assert res.ti_le_ng_toan_ky == pytest.approx(0.40)

    # File báo cáo markdown được ghi thành công
    p_report = Path(res.duong_dan_bao_cao)
    assert p_report.is_file()
    content = p_report.read_text(encoding="utf-8")

    # Kiểm tra có đủ 5 chiều trong báo cáo
    for dim in DIMENSIONS:
        label = DIMENSION_LABELS_VI[dim]
        assert label in content

    # Kiểm tra biểu đồ ASCII
    assert "Biểu đồ xu hướng:" in content
    assert "█" in content

    # Kiểm tra phần đối chiếu đếm tay
    assert "ĐỐI CHIẾU SỐ LIỆU ĐẾM TAY" in content
    assert f"**{res.tong_so_ban_ghi}** dòng log được quét" in content
