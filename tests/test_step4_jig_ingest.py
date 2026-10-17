"""Tests cho đầu tiếp nhận dữ liệu đẩy lên phía ứng dụng cho tool JIG (Bước 4).

Xác thực:
1. Điểm nhận nội bộ nhận lô bản ghi log (batch ingest qua JSON / NDJSON / dict).
2. Tách biệt tuyệt đối dữ liệu mô phỏng SIMULATED_* khỏi dữ liệu sản xuất thật.
3. Chạy cổng cảnh báo xu hướng SMA(20) ngay khi tiếp nhận lô:
   - Điểm đơn lẻ -> Cận biên, không cảnh báo.
   - Xu hướng nhiều điểm liên tiếp -> Vi phạm, cảnh báo xu hướng.
4. Kiểm chứng bằng dữ liệu mô phỏng sinh trực tiếp từ log JIG thật (2026_08_Master.csv).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aios_habit.production_prediction.jig_ingest_receiver import (
    JigIngestReceiver,
    sinh_du_lieu_mo_phong_tu_log_that,
    tiep_nhan_lo_ban_ghi_jig,
)
from aios_habit.production_prediction.log_archive import doc_kho

TEP_LOG_THAT = Path(
    r"D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Iris LSU\thu nghiem 6pcs do thong so va log\2ND-1002_JIG BEAM\2026_08_Master.csv"
)


def test_tiep_nhan_lo_san_xuat_that_ghi_kho_that(tmp_path):
    """Bản ghi sản xuất (nguon='that') được ghi vào kho sản xuất thật."""
    kho_that = tmp_path / "kho_that"
    kho_sim = tmp_path / "kho_sim"

    receiver = JigIngestReceiver(kho_that=kho_that, kho_mo_phong=kho_sim)

    lo_records = [
        {
            "unit_serial": f"PROD-{i}",
            "jig_id": "2ND-1002",
            "metric": "TaktTime",
            "value": 140.0 + i,
            "unit": "s",
            "status": "OK",
            "nguon": "that",
            "timestamp": f"2026-10-17T10:{i:02d}:00",
        }
        for i in range(5)
    ]

    res = receiver.tiep_nhan_lo(lo_records)

    assert res.thanh_cong is True
    assert res.tong_so_nhan == 5
    assert res.da_ghi_kho == 5
    assert res.la_mo_phong is False

    # Kiểm tra kho thật có đủ 5 dòng
    dong_that = doc_kho(kho_that)
    assert len(dong_that) == 5
    assert all(d.nguon == "that" for d in dong_that)

    # Kiểm tra kho mô phỏng không có bản ghi nào
    assert not kho_sim.exists() or len(doc_kho(kho_sim)) == 0


def test_tiep_nhan_lo_mo_phong_simulated_tach_biet_kho_that(tmp_path):
    """Bản ghi mô phỏng (nguon='SIMULATED_*') được ghi tách biệt, không lẫn vào sản xuất."""
    kho_that = tmp_path / "kho_that"
    kho_sim = tmp_path / "kho_sim"

    receiver = JigIngestReceiver(kho_that=kho_that, kho_mo_phong=kho_sim)

    # 1. Ghi 3 bản ghi sản xuất trước
    receiver.tiep_nhan_lo([
        {
            "unit_serial": "PROD-001",
            "jig_id": "2ND-1002",
            "metric": "TaktTime",
            "value": 140.0,
            "nguon": "that",
        }
    ])

    # 2. Ghi 10 bản ghi mô phỏng gắn mác SIMULATED_JIG_BEAM
    lo_sim = [
        {
            "unit_serial": f"SIM-{i}",
            "jig_id": "2ND-1002",
            "metric": "TaktTime",
            "value": 200.0 + i,
            "nguon": "SIMULATED_JIG_BEAM",
        }
        for i in range(10)
    ]
    res_sim = receiver.tiep_nhan_lo(lo_sim)

    assert res_sim.thanh_cong is True
    assert res_sim.da_ghi_kho == 10
    assert res_sim.la_mo_phong is True

    # Kiểm tra kho thật TUYỆT ĐỐI chỉ có 1 bản ghi sản xuất
    dong_that_toan_bo = doc_kho(kho_that)
    assert len(dong_that_toan_bo) == 1
    assert dong_that_toan_bo[0].unit_serial == "PROD-001"
    assert not dong_that_toan_bo[0].nguon.startswith("SIMULATED_")

    # Kiểm tra kho mô phỏng lưu đủ 10 bản ghi mô phỏng
    dong_sim = doc_kho(kho_sim)
    assert len(dong_sim) == 10
    assert all(d.nguon == "SIMULATED_JIG_BEAM" for d in dong_sim)


def test_chay_cong_sma_diem_xau_don_le_khong_canh_bao(tmp_path):
    """Khi tiếp nhận lô có 1 điểm xấu đơn lẻ, cổng SMA(20) xếp loại Cận biên, không cảnh báo."""
    receiver = JigIngestReceiver(kho_that=tmp_path / "kho_that", kho_mo_phong=tmp_path / "kho_sim")

    # Pre-fill 40 điểm nền 140.0s
    nen = [
        {
            "unit_serial": f"BASE-{i}",
            "jig_id": "2ND-1002",
            "metric": "TaktTime",
            "value": 140.0,
            "nguon": "that",
            "timestamp": f"2026-10-10T10:{i:02d}:00",
        }
        for i in range(40)
    ]
    receiver.tiep_nhan_lo(nen)

    # Đẩy 1 điểm xấu đơn lẻ 290.0s (vọt xa khỏi SMA 140.0s)
    lo_don_le = [
        {
            "unit_serial": "SPIKE-001",
            "jig_id": "2ND-1002",
            "metric": "TaktTime",
            "value": 290.0,
            "nguon": "that",
            "timestamp": "2026-10-10T11:00:00",
        }
    ]
    res = receiver.tiep_nhan_lo(lo_don_le)

    assert len(res.danh_sach_danh_gia_cong) == 1
    danh_gia = res.danh_sach_danh_gia_cong[0]
    # Cổng SMA(20) bảo vệ: điểm xấu đơn lẻ không cảnh báo
    assert danh_gia.trang_thai == "Cận biên"
    assert danh_gia.canh_bao is False
    assert res.so_canh_bao_vi_pham == 0
    assert res.so_can_bien == 1


def test_chay_cong_sma_xu_huong_troi_kich_hoat_canh_bao(tmp_path):
    """Khi tiếp nhận lô có chuỗi >= 3 điểm xấu liên tiếp, cổng kích hoạt cảnh báo Vi phạm."""
    receiver = JigIngestReceiver(kho_that=tmp_path / "kho_that", kho_mo_phong=tmp_path / "kho_sim")

    # Pre-fill 40 điểm nền
    nen = [
        {
            "unit_serial": f"BASE-{i}",
            "jig_id": "2ND-1002",
            "metric": "TaktTime",
            "value": 140.0,
            "nguon": "that",
            "timestamp": f"2026-10-10T10:{i:02d}:00",
        }
        for i in range(40)
    ]
    receiver.tiep_nhan_lo(nen)

    # Đẩy 4 điểm xấu liên tiếp
    lo_drift = [
        {
            "unit_serial": f"DRIFT-{i}",
            "jig_id": "2ND-1002",
            "metric": "TaktTime",
            "value": 260.0 + i * 5,
            "nguon": "that",
            "timestamp": f"2026-10-10T11:{i:02d}:00",
        }
        for i in range(4)
    ]
    res = receiver.tiep_nhan_lo(lo_drift)

    assert len(res.danh_sach_danh_gia_cong) == 1
    danh_gia = res.danh_sach_danh_gia_cong[0]
    assert danh_gia.trang_thai == "Vi phạm"
    assert danh_gia.canh_bao is True
    assert danh_gia.so_diem_lien_tiep >= 3
    assert res.so_canh_bao_vi_pham == 1


@pytest.mark.skipif(not TEP_LOG_THAT.is_file(), reason="Thiếu tệp log JIG thật trên máy")
def test_kiem_chung_mo_phong_tu_log_that(tmp_path):
    """Kiểm chứng toàn bộ quy trình tiếp nhận bằng dữ liệu mô phỏng sinh từ log thật."""
    receiver = JigIngestReceiver(kho_that=tmp_path / "kho_that", kho_mo_phong=tmp_path / "kho_sim")

    # 1. Kịch bản bình thường
    sim_normal = sinh_du_lieu_mo_phong_tu_log_that(
        TEP_LOG_THAT,
        metric_name="TaktTime",
        kich_ban="binh_thuong",
        tag_mo_phong="SIMULATED_JIG_BEAM",
    )
    res_normal = receiver.tiep_nhan_lo(sim_normal)
    assert res_normal.thanh_cong is True
    assert res_normal.so_canh_bao_vi_pham == 0
    assert all(d.la_mo_phong for d in res_normal.danh_sach_danh_gia_cong)

    # 2. Kịch bản 1 điểm đơn lẻ
    sim_spike = sinh_du_lieu_mo_phong_tu_log_that(
        TEP_LOG_THAT,
        metric_name="TaktTime",
        kich_ban="don_le",
        tag_mo_phong="SIMULATED_JIG_BEAM",
    )
    res_spike = receiver.tiep_nhan_lo(sim_spike)
    assert res_spike.so_canh_bao_vi_pham == 0
    assert res_spike.so_can_bien == 1

    # 3. Kịch bản xu hướng trôi
    sim_drift = sinh_du_lieu_mo_phong_tu_log_that(
        TEP_LOG_THAT,
        metric_name="TaktTime",
        kich_ban="xu_huong_troi",
        tag_mo_phong="SIMULATED_JIG_BEAM",
    )
    res_drift = receiver.tiep_nhan_lo(sim_drift)
    assert res_drift.so_canh_bao_vi_pham >= 1

    # Kiểm tra kho sản xuất thật không bị trộn dữ liệu mô phỏng
    assert not (tmp_path / "kho_that").exists() or len(doc_kho(tmp_path / "kho_that")) == 0
