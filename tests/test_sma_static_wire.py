"""Tests for static log SMA(20) trend alerts wiring (DESKTOP-SMA-STATIC-WIRE-HOME).

Verifies:
1. Chat intent router classifies static log SMA trend queries to XU_HUONG_LOG_TINH.
2. Slot extraction extracts csv filename and test mode (chieu_cong vs chieu_xu_huong).
3. decide_jig_action handles XU_HUONG_LOG_TINH and returns comprehensive results.
4. Two-way gate logic:
   - Single isolated anomaly: "Cận biên", canh_bao = False (no alert).
   - 3+ consecutive anomalies: "Vi phạm", canh_bao = True (trend alert).
   - Normal points: "Đạt", canh_bao = False.
5. Regression: chart intent, import csv intent, threshold alert intent, and log archive commands remain unaffected.
"""

from __future__ import annotations

from pathlib import Path

from aios_habit.chat_intent_router import (
    CANH_BAO_NGUONG,
    VE_BIEU_DO,
    XU_HUONG_LOG_TINH,
    classify_intent,
    classify_all_intents,
    extract_slots,
)
from aios_habit.production_prediction.jig_chat_wire import (
    decide_jig_action,
    is_trend_static_intent,
    is_import_csv_intent,
    is_chart_intent,
)
from aios_habit.production_prediction.log_archive import la_lenh_kho_log
from aios_habit.production_prediction.static_log_trend import (
    phan_tich_chuoi_thong_so,
    quet_xu_huong_log_tinh,
)


def test_chat_intent_router_sma_static_classification():
    cau1 = "phân tích cảnh báo xu hướng theo cổng SMA(20) trên log tĩnh 2026_08_Master.csv"
    assert classify_intent(cau1) == XU_HUONG_LOG_TINH

    cau2 = "kiểm tra chiều cổng: điểm bất thường đơn lẻ theo SMA(20) trên log tĩnh 2026_08_Master.csv có thành cảnh báo không?"
    assert classify_intent(cau2) == XU_HUONG_LOG_TINH

    cau3 = "kiểm tra chiều xu hướng: đoạn trôi từ 3 điểm bất thường liên tiếp theo SMA(20) trên log tĩnh 2026_08_Master.csv"
    assert classify_intent(cau3) == XU_HUONG_LOG_TINH

    cau4 = "phân tích xu hướng SMA(20) trên log tĩnh"
    assert classify_intent(cau4) == XU_HUONG_LOG_TINH

    cau5 = "quét log tĩnh theo cổng SMA"
    assert classify_intent(cau5) == XU_HUONG_LOG_TINH


def test_slot_extraction_trend_static():
    cau1 = 'phân tích cảnh báo xu hướng theo cổng SMA(20) trên log tĩnh "2026_08_Master.csv"'
    slots1 = extract_slots(cau1, XU_HUONG_LOG_TINH)
    assert slots1.get("tep_csv") == "2026_08_Master.csv"

    cau2 = "kiểm tra chiều cổng: điểm bất thường đơn lẻ theo SMA(20) trên log tĩnh 2026_08_Master.csv có thành cảnh báo không?"
    slots2 = extract_slots(cau2, XU_HUONG_LOG_TINH)
    assert slots2.get("chieu_kiem_tra") == "chieu_cong"
    assert slots2.get("tep_csv") == "2026_08_Master.csv"

    cau3 = "kiểm tra chiều xu hướng: đoạn trôi từ 3 điểm bất thường liên tiếp theo SMA(20) trên log tĩnh 2026_08_Master.csv"
    slots3 = extract_slots(cau3, XU_HUONG_LOG_TINH)
    assert slots3.get("chieu_kiem_tra") == "chieu_xu_huong"


def test_two_way_gate_logic_unit():
    # 1. Chuỗi bình thường quanh 50.0 (30 điểm)
    norm_vals = [50.0 + (i % 3) * 0.1 for i in range(30)]
    res_norm = phan_tich_chuoi_thong_so("TEST_NORM", norm_vals)
    assert res_norm.trang_thai == "Đạt"
    assert not res_norm.canh_bao
    assert res_norm.so_diem_bat_thuong == 0

    # 2. Chiều Cổng: 1 điểm đơn lẻ bất thường tại index 25 (vọt lên 80.0)
    single_vals = [50.0 + (i % 3) * 0.1 for i in range(30)]
    single_vals[25] = 80.0
    res_single = phan_tich_chuoi_thong_so("TEST_SINGLE", single_vals)
    assert res_single.trang_thai == "Cận biên"
    assert not res_single.canh_bao  # Cổng chặn báo ảo!
    assert res_single.so_diem_bat_thuong == 1
    assert res_single.doan_lien_tiep_dai_nhat == 1

    # 3. Chiều Xu Hướng: 3 điểm bất thường liên tiếp tại index 25, 26, 27 (vọt lên 80.0)
    consec_vals = [50.0 + (i % 3) * 0.1 for i in range(30)]
    consec_vals[25] = 80.0
    consec_vals[26] = 80.5
    consec_vals[27] = 81.0
    res_consec = phan_tich_chuoi_thong_so("TEST_CONSEC", consec_vals)
    assert res_consec.trang_thai == "Vi phạm"
    assert res_consec.canh_bao  # Kích hoạt cảnh báo xu hướng!
    assert res_consec.doan_lien_tiep_dai_nhat == 3


def test_decide_jig_action_synthesis_and_gates():
    # Tổng hợp
    cau_tong_hop = "phân tích cảnh báo xu hướng theo cổng SMA(20) trên log tĩnh 2026_08_Master.csv"
    assert is_trend_static_intent(cau_tong_hop)
    outcome1 = decide_jig_action(cau_tong_hop)
    assert outcome1.handled
    assert "Kết quả phân tích xu hướng SMA(20) trên log tĩnh" in outcome1.assistant_text
    assert "2026_08_Master.csv" in outcome1.assistant_text
    assert "HUMIDITY" in outcome1.assistant_text
    assert "BOW_B" in outcome1.assistant_text
    assert "LD1H_M70_Y_DPPM0" in outcome1.assistant_text

    # Chiều Cổng
    cau_chieu_cong = "kiểm tra chiều cổng: điểm bất thường đơn lẻ theo SMA(20) trên log tĩnh 2026_08_Master.csv có thành cảnh báo không?"
    outcome2 = decide_jig_action(cau_chieu_cong)
    assert outcome2.handled
    assert "Kiểm chứng Chiều Cổng SMA(20)" in outcome2.assistant_text
    assert "KHÔNG CẢNH BÁO" in outcome2.assistant_text
    assert "Cận biên" in outcome2.assistant_text

    # Chiều Xu Hướng
    cau_chieu_xu_huong = "kiểm tra chiều xu hướng: đoạn trôi từ 3 điểm bất thường liên tiếp theo SMA(20) trên log tĩnh 2026_08_Master.csv"
    outcome3 = decide_jig_action(cau_chieu_xu_huong)
    assert outcome3.handled
    assert "Kiểm chứng Chiều Xu Hướng SMA(20)" in outcome3.assistant_text
    assert "CẢNH BÁO XU HƯỚNG" in outcome3.assistant_text
    assert "Vi phạm" in outcome3.assistant_text


def test_regression_intents_intact():
    # Nhập tệp không bị cướp bởi xu hướng
    cau_nhap = 'nhập tệp log "D:\\test.csv"'
    assert is_import_csv_intent(cau_nhap)
    assert not is_trend_static_intent(cau_nhap)

    # Lệnh kho log không bị cướp
    cau_kho = "phân tích log 2ND-1002"
    assert la_lenh_kho_log(cau_kho)
    assert not is_trend_static_intent(cau_kho)

    # Lệnh vẽ biểu đồ không bị cướp
    cau_bieu_do = "chọn biểu đồ phân bố cho 2ND-1002"
    assert is_chart_intent(cau_bieu_do)
    assert classify_intent(cau_bieu_do) == VE_BIEU_DO
    assert not is_trend_static_intent(cau_bieu_do)

    # Cảnh báo ngưỡng không bị cướp
    cau_nguong = "cảnh báo khi nhiệt độ vượt 80"
    assert classify_intent(cau_nguong) == CANH_BAO_NGUONG
    assert not is_trend_static_intent(cau_nguong)
