# -*- coding: utf-8 -*-
"""Unit tests for /huongdan command (ticket DESKTOP-HOME-HUONGDAN-COMMAND).

Testing scope:
1. Command recognition (positive & negative controls)
2. Argument parsing (menu, sections, subsections, all, close)
3. Content integrity & base64 image embedding (verifying all 57 images)
4. Specific section extraction (C4 recurrence alert card, full manual)
5. Suggestion chips generation (matching existing suggestion chip mechanism)
6. Continuous improvement metrics logging in local_cases
7. Chat intent router integration (zero fake turns, local deterministic routing)
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pytest

from aios_habit.huongdan_command import (
    clear_manual_cache,
    embed_images_as_base64,
    get_chips_for_section,
    get_huongdan_metrics,
    handle_huongdan_command,
    is_huongdan_command,
    load_and_parse_manual,
    parse_huongdan_args,
    record_huongdan_metric,
    resolve_images_dir,
    resolve_manual_path,
)
from aios_habit.chat_intent_router import (
    classify_all_intents,
    extract_slots,
    HUONG_DAN,
)


EXPECTED_MANUAL_SHA256 = "008D2974F8F1E5FF141F9C5228F8331E8012BF6552187FAA87E1147E612B9B82"


def test_manual_file_integrity_and_57_images():
    """Kiểm tra tệp cẩm nang đúng SHA-256 và thư mục images chứa đúng 57 ảnh."""
    manual_path = resolve_manual_path()
    assert manual_path.is_file(), f"Không tìm thấy cẩm nang tại {manual_path}"

    data = manual_path.read_bytes()
    sha = hashlib.sha256(data).hexdigest().upper()
    assert sha == EXPECTED_MANUAL_SHA256, f"SHA-256 không khớp: nhận {sha}, kỳ vọng {EXPECTED_MANUAL_SHA256}"
    assert len(data) == 35103, f"Số byte không khớp: {len(data)}"

    images_dir = resolve_images_dir()
    assert images_dir.is_dir(), f"Không tìm thấy thư mục ảnh tại {images_dir}"
    imgs = [f for f in os.listdir(images_dir) if f.endswith(".png")]
    assert len(imgs) == 57, f"Kỳ vọng đúng 57 ảnh, thực tế có {len(imgs)} ảnh"


def test_is_huongdan_command_positive_and_negative():
    """Kiểm tra nhận diện câu lệnh /huongdan và cách ly câu hỏi tra cứu thông thường."""
    # Positive commands
    assert is_huongdan_command("/huongdan")
    assert is_huongdan_command("/huongdan A1")
    assert is_huongdan_command("/huongdan C4")
    assert is_huongdan_command("/huongdan tat-ca")
    assert is_huongdan_command("/huongdan toan-bo")
    assert is_huongdan_command("/huongdan B")
    assert is_huongdan_command("/huong-dan")
    assert is_huongdan_command("/help")
    assert is_huongdan_command("/guide")
    assert is_huongdan_command("huong dan")
    assert is_huongdan_command("huong dan su dung")
    assert is_huongdan_command("cam nang aios")
    assert is_huongdan_command("hướng dẫn sử dụng aios")

    # Negative controls (không cướp câu hỏi RAG / câu nghiệp vụ thông thường)
    assert not is_huongdan_command("Lỗi C7620 xuất hiện khi nào?")
    assert not is_huongdan_command("Quy trình tháo lắp cụm sấy trong tài liệu hướng dẫn")
    assert not is_huongdan_command("Tra cứu mã lỗi JAM4212")
    assert not is_huongdan_command("In ra tờ giấy trắng nguyên nhân do đâu?")
    assert not is_huongdan_command("")


def test_parse_huongdan_args():
    """Kiểm tra trích xuất đối số phân đoạn cẩm nang."""
    assert parse_huongdan_args("/huongdan") == "danh_muc"
    assert parse_huongdan_args("/huongdan ") == "danh_muc"
    assert parse_huongdan_args("/huongdan A1") == "A1"
    assert parse_huongdan_args("/huongdan a1") == "A1"
    assert parse_huongdan_args("/huongdan C4") == "C4"
    assert parse_huongdan_args("/huongdan c4") == "C4"
    assert parse_huongdan_args("/huongdan G18") == "G18"
    assert parse_huongdan_args("/huongdan B") == "B"
    assert parse_huongdan_args("/huongdan phan b") == "B"
    assert parse_huongdan_args("/huongdan tat-ca") == "tat_ca"
    assert parse_huongdan_args("/huongdan toan-bo") == "tat_ca"
    assert parse_huongdan_args("/huongdan all") == "tat_ca"
    assert parse_huongdan_args("/huongdan phu-luc") == "phu_luc"
    assert parse_huongdan_args("/huongdan gioi-thieu") == "gioi_thieu"
    assert parse_huongdan_args("/huongdan dong") == "dong"


def test_handle_huongdan_danh_muc_menu():
    """Kiểm tra gọi /huongdan trả về danh mục kèm đủ 10 chip gợi ý."""
    clear_manual_cache()
    res = handle_huongdan_command("/huongdan", conversation_id="CONV-UNIT-TEST")
    assert res.section_key == "danh_muc"
    assert "CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS" in res.markdown_content
    assert "| **Phần A** |" in res.markdown_content
    assert "| **Phần C** |" in res.markdown_content
    assert "| **Toàn bộ** |" in res.markdown_content

    chips = res.chips
    assert len(chips) == 10
    chip_cmds = [cmd for _, cmd in chips]
    assert "/huongdan gioi-thieu" in chip_cmds
    assert "/huongdan A" in chip_cmds
    assert "/huongdan B" in chip_cmds
    assert "/huongdan C" in chip_cmds
    assert "/huongdan D" in chip_cmds
    assert "/huongdan E" in chip_cmds
    assert "/huongdan F" in chip_cmds
    assert "/huongdan G" in chip_cmds
    assert "/huongdan phu-luc" in chip_cmds
    assert "/huongdan tat-ca" in chip_cmds


def test_handle_huongdan_c4_recurrence_alert():
    """Cổng 3: Mở hạng mục C4 (Thẻ cảnh báo tái phát C7620) đúng chữ và ảnh hiển thị thật."""
    clear_manual_cache()
    res = handle_huongdan_command("/huongdan C4", conversation_id="CONV-UNIT-TEST")
    assert res.section_key == "C4"

    # Kiểm tra nội dung chữ khớp cẩm nang
    assert "### C4. Phân loại tự động & Thẻ Cảnh báo Tái phát Bước 5 (C7620)" in res.markdown_content
    assert "Thẻ Cảnh báo Tái phát Bước 5" in res.markdown_content
    assert "Tái phát: mã C7620 đã xuất hiện 136 lần trong cơ sở dữ liệu lịch sử (30.075 ca)" in res.markdown_content
    assert "Ca gần nhất: vụ FY27H2/263" in res.markdown_content

    # Kiểm tra ảnh minh họa hiển thị thật qua base64 data URI (không phải đường dẫn chết)
    assert "data:image/png;base64," in res.markdown_content
    assert "images/anh-r3-c4-the-canh-bao-tai-phat-c7620.png" not in res.markdown_content

    # Kiểm tra chip điều hướng
    chip_cmds = [cmd for _, cmd in res.chips]
    assert "/huongdan" in chip_cmds
    assert "/huongdan C" in chip_cmds
    assert "/huongdan tat-ca" in chip_cmds


def test_handle_huongdan_tat_ca_full_manual():
    """Cổng 4: Chọn Toàn bộ xem được trọn vẹn cả 7 phần + phụ lục + 57 ảnh."""
    clear_manual_cache()
    res = handle_huongdan_command("/huongdan tat-ca", conversation_id="CONV-UNIT-TEST")
    assert res.section_key == "tat_ca"

    content = res.markdown_content
    # Đầy đủ 7 phần + phụ lục
    assert "PHẦN 1: NHÓM A" in content
    assert "PHẦN 2: NHÓM B" in content
    assert "PHẦN 3: NHÓM C" in content
    assert "PHẦN 4: NHÓM D" in content
    assert "PHẦN 5: NHÓM E" in content
    assert "PHẦN 6: NHÓM F" in content
    assert "PHẦN 7: NHÓM G" in content
    assert "8. PHỤ LỤC: BẢNG TRA CỨU NHANH CÁC THAO TÁC CỐT LÕI" in content

    # Không còn đường dẫn ảnh chết nào
    assert "images/anh-hd-" not in content
    assert "images/anh-r" not in content

    # Chứa đúng 57 ảnh dạng data:image/png;base64,
    assert content.count("data:image/png;base64,") == 57


def test_continuous_improvement_metrics():
    """Vòng lặp cải thiện liên tục: Ghi đếm cục bộ số lượt gọi và xem từng hạng mục."""
    record_huongdan_metric("/huongdan", "danh_muc", "CONV-M1")
    record_huongdan_metric("/huongdan C4", "C4", "CONV-M1")
    record_huongdan_metric("/huongdan tat-ca", "tat_ca", "CONV-M1")

    m = get_huongdan_metrics()
    assert m["total_calls"] >= 3
    assert m["by_section"].get("danh_muc", 0) >= 1
    assert m["by_section"].get("C4", 0) >= 1
    assert m["by_section"].get("tat_ca", 0) >= 1
    assert "last_called_at" in m


def test_chat_intent_router_huongdan_integration():
    """Kiểm tra định tuyến ý định chat: /huongdan được nhận diện ở tầng intent router."""
    intents_menu = classify_all_intents("/huongdan")
    assert len(intents_menu) == 1
    assert intents_menu[0][0] == HUONG_DAN
    assert intents_menu[0][1]["muc"] == "danh_muc"

    intents_c4 = classify_all_intents("/huongdan C4")
    assert len(intents_c4) == 1
    assert intents_c4[0][0] == HUONG_DAN
    assert intents_c4[0][1]["muc"] == "C4"

    intents_full = classify_all_intents("/huongdan tat-ca")
    assert len(intents_full) == 1
    assert intents_full[0][0] == HUONG_DAN
    assert intents_full[0][1]["muc"] == "tat_ca"

    # Câu hỏi tra cứu thông thường không bị định tuyến nhầm
    intents_rag = classify_all_intents("Tra cứu lỗi C7620")
    assert all(yd != HUONG_DAN for yd, _ in intents_rag)
