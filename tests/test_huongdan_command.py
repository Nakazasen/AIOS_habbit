# -*- coding: utf-8 -*-
"""Unit tests for 3-language user guide command (tickets DESKTOP-HOME-HUONGDAN-COMMAND & DESKTOP-HOME-HUONGDAN-I18N).

Testing scope:
1. File integrity & SHA-256 for Vietnamese, Chinese, and Japanese manuals + shared 57 images.
2. Command recognition across 3 languages (positive & negative controls).
3. Argument parsing across 3 languages (common codes A1..G18, sections A..G, aliases in JA/ZH/VI).
4. Menu rendering for VI (/huongdan), JA (/使い方), ZH (/使用指南).
5. Subsection C4 rendering (136 occurrences, FY27H2/263, 30.075 cases, real base64 images).
6. Full manual rendering (tat-ca / 全体 / 全部) with all 57 images embedded as base64 data URI.
7. Continuous improvement metrics logging with language field in events.jsonl and by_language in metrics.json.
8. Chat intent router integration for all 3 languages (zero fake turns, local deterministic routing).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pytest

from aios_habit.huongdan_command import (
    clear_manual_cache,
    detect_huongdan_language,
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


EXPECTED_VI_SHA256 = "ADC5CDDA1D1E8A896A5EC87A0A32EFA8CE51D9E553F6A8376A0F3DE2AE0FC595"
EXPECTED_ZH_SHA256 = "945C5EC6970ED368ED8717EF1FF957F50577DC17A0AB4C080C6FD9035CBCE7C5"
EXPECTED_JA_SHA256 = "9D07A2376AFA6999F44F4715DCBCD5E974B848F0115CBF89356A7AE10049DDAB"


def test_manual_file_integrity_and_57_images():
    """Kiểm tra tệp cẩm nang 3 thứ tiếng đúng byte, đúng SHA-256 và thư mục images chứa đúng 57 ảnh."""
    # 1. Tiếng Việt (VI)
    path_vi = resolve_manual_path("vi")
    assert path_vi.is_file(), f"Không tìm thấy cẩm nang VI tại {path_vi}"
    data_vi = path_vi.read_bytes()
    sha_vi = hashlib.sha256(data_vi).hexdigest().upper()
    assert sha_vi == EXPECTED_VI_SHA256, f"SHA-256 VI không khớp: nhận {sha_vi}"
    assert len(data_vi) == 42695, f"Số byte VI không khớp: {len(data_vi)}"

    # 2. Tiếng Trung (ZH)
    path_zh = resolve_manual_path("zh")
    assert path_zh.is_file(), f"Không tìm thấy cẩm nang ZH tại {path_zh}"
    data_zh = path_zh.read_bytes()
    sha_zh = hashlib.sha256(data_zh).hexdigest().upper()
    assert sha_zh == EXPECTED_ZH_SHA256, f"SHA-256 ZH không khớp: nhận {sha_zh}"
    assert len(data_zh) == 35132, f"Số byte ZH không khớp: {len(data_zh)}"

    # 3. Tiếng Nhật (JA)
    path_ja = resolve_manual_path("ja")
    assert path_ja.is_file(), f"Không tìm thấy cẩm nang JA tại {path_ja}"
    data_ja = path_ja.read_bytes()
    sha_ja = hashlib.sha256(data_ja).hexdigest().upper()
    assert sha_ja == EXPECTED_JA_SHA256, f"SHA-256 JA không khớp: nhận {sha_ja}"
    assert len(data_ja) == 45053, f"Số byte JA không khớp: {len(data_ja)}"

    # 4. Thư mục ảnh dùng chung 57 ảnh PNG
    images_dir = resolve_images_dir()
    assert images_dir.is_dir(), f"Không tìm thấy thư mục ảnh tại {images_dir}"
    imgs = [f for f in os.listdir(images_dir) if f.endswith(".png")]
    assert len(imgs) == 57, f"Kỳ vọng đúng 57 ảnh, thực tế có {len(imgs)} ảnh"


def test_is_huongdan_command_positive_and_negative():
    """Kiểm tra nhận diện câu lệnh cẩm nang trên cả 3 ngôn ngữ và cách ly câu hỏi tra cứu thông thường."""
    # Positive - Tiếng Việt
    assert is_huongdan_command("/huongdan")
    assert is_huongdan_command("/huongdan A1")
    assert is_huongdan_command("/huongdan C4")
    assert is_huongdan_command("/huongdan tat-ca")
    assert is_huongdan_command("/huongdan toan-bo")
    assert is_huongdan_command("/huongdan B")
    assert is_huongdan_command("/huong-dan")
    assert not is_huongdan_command("/help")
    assert not is_huongdan_command("/guide")
    assert is_huongdan_command("huong dan")
    assert is_huongdan_command("huong dan su dung")
    assert is_huongdan_command("cam nang aios")
    assert is_huongdan_command("hướng dẫn sử dụng aios")

    # Positive - Tiếng Nhật
    assert is_huongdan_command("/使い方")
    assert is_huongdan_command("/使い方 C4")
    assert is_huongdan_command("/使い方 A1")
    assert is_huongdan_command("/使い方 tat-ca")
    assert is_huongdan_command("/使い方 全体")
    assert is_huongdan_command("/使い方 B")
    assert is_huongdan_command("使い方")
    assert is_huongdan_command("使い方 C4")
    assert is_huongdan_command("/つかいかた")

    # Positive - Tiếng Trung
    assert is_huongdan_command("/使用指南")
    assert is_huongdan_command("/使用指南 C4")
    assert is_huongdan_command("/使用指南 A1")
    assert is_huongdan_command("/使用指南 tat-ca")
    assert is_huongdan_command("/使用指南 全部")
    assert is_huongdan_command("/使用指南 B")
    assert is_huongdan_command("使用指南")
    assert is_huongdan_command("使用指南 C4")

    # Negative controls (không cướp câu hỏi RAG / câu nghiệp vụ thông thường)
    assert not is_huongdan_command("Lỗi C7620 xuất hiện khi nào?")
    assert not is_huongdan_command("Quy trình tháo lắp cụm sấy trong tài liệu hướng dẫn")
    assert not is_huongdan_command("Tra cứu mã lỗi JAM4212")
    assert not is_huongdan_command("In ra tờ giấy trắng nguyên nhân do đâu?")
    assert not is_huongdan_command("エラーC7620の発生原因は何ですか？")
    assert not is_huongdan_command("定着ユニットの使い方を詳しく教えて")
    assert not is_huongdan_command("如何处理故障代码 C7620？")
    assert not is_huongdan_command("")


def test_detect_huongdan_language():
    """Kiểm tra nhận diện chính xác ngôn ngữ của lệnh hướng dẫn."""
    assert detect_huongdan_language("/huongdan") == "vi"
    assert detect_huongdan_language("/huongdan C4") == "vi"
    assert detect_huongdan_language("huong dan su dung") == "vi"
    assert detect_huongdan_language("/使い方") == "ja"
    assert detect_huongdan_language("/使い方 C4") == "ja"
    assert detect_huongdan_language("使い方") == "ja"
    assert detect_huongdan_language("/使用指南") == "zh"
    assert detect_huongdan_language("/使用指南 C4") == "zh"
    assert detect_huongdan_language("使用指南") == "zh"


def test_parse_huongdan_args():
    """Kiểm tra trích xuất đối số phân đoạn cẩm nang dùng chung và theo từng ngôn ngữ."""
    # Tiếng Việt
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

    # Tiếng Nhật
    assert parse_huongdan_args("/使い方") == "danh_muc"
    assert parse_huongdan_args("/使い方 C4") == "C4"
    assert parse_huongdan_args("/使い方 A1") == "A1"
    assert parse_huongdan_args("/使い方 B") == "B"
    assert parse_huongdan_args("/使い方 tat-ca") == "tat_ca"
    assert parse_huongdan_args("/使い方 全体") == "tat_ca"
    assert parse_huongdan_args("/使い方 目次") == "danh_muc"
    assert parse_huongdan_args("/使い方 概要") == "gioi_thieu"
    assert parse_huongdan_args("/使い方 付録") == "phu_luc"
    assert parse_huongdan_args("/使い方 閉じる") == "dong"

    # Tiếng Trung
    assert parse_huongdan_args("/使用指南") == "danh_muc"
    assert parse_huongdan_args("/使用指南 C4") == "C4"
    assert parse_huongdan_args("/使用指南 A1") == "A1"
    assert parse_huongdan_args("/使用指南 B") == "B"
    assert parse_huongdan_args("/使用指南 tat-ca") == "tat_ca"
    assert parse_huongdan_args("/使用指南 全部") == "tat_ca"
    assert parse_huongdan_args("/使用指南 目录") == "danh_muc"
    assert parse_huongdan_args("/使用指南 综合介绍") == "gioi_thieu"
    assert parse_huongdan_args("/使用指南 附录") == "phu_luc"
    assert parse_huongdan_args("/使用指南 关闭") == "dong"


def test_handle_huongdan_danh_muc_menu_all_3_languages():
    """Kiểm tra gọi lệnh danh mục trả về đúng ngôn ngữ và chip gợi ý tương ứng."""
    clear_manual_cache()

    # 1. Tiếng Việt (/huongdan)
    res_vi = handle_huongdan_command("/huongdan", conversation_id="CONV-UNIT-VI")
    assert res_vi.section_key == "danh_muc"
    assert res_vi.language == "vi"
    assert "CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS" in res_vi.markdown_content
    assert "| **Phần A** |" in res_vi.markdown_content
    assert len(res_vi.chips) == 11
    assert all(cmd.startswith("/huongdan") for _, cmd in res_vi.chips)
    chip_texts_vi = [txt for txt, _ in res_vi.chips]
    assert any("Danh mục lệnh" in t for t in chip_texts_vi)

    # 2. Tiếng Nhật (/使い方)
    res_ja = handle_huongdan_command("/使い方", conversation_id="CONV-UNIT-JA")
    assert res_ja.section_key == "danh_muc"
    assert res_ja.language == "ja"
    assert "AIOS台帳 総合利用マニュアル" in res_ja.markdown_content
    assert "| **グループA** |" in res_ja.markdown_content
    assert len(res_ja.chips) == 11
    assert all(cmd.startswith("/使い方") for _, cmd in res_ja.chips)
    chip_texts_ja = [txt for txt, _ in res_ja.chips]
    assert any("概要" in t for t in chip_texts_ja)
    assert any("グループA" in t for t in chip_texts_ja)
    assert any("コマンド一覧" in t for t in chip_texts_ja)

    # 3. Tiếng Trung (/使用指南)
    res_zh = handle_huongdan_command("/使用指南", conversation_id="CONV-UNIT-ZH")
    assert res_zh.section_key == "danh_muc"
    assert res_zh.language == "zh"
    assert "AIOS 台账综合使用指南" in res_zh.markdown_content
    assert "| **A组** |" in res_zh.markdown_content
    assert len(res_zh.chips) == 11
    assert all(cmd.startswith("/使用指南") for _, cmd in res_zh.chips)
    chip_texts_zh = [txt for txt, _ in res_zh.chips]
    assert any("综合介绍" in t for t in chip_texts_zh)
    assert any("A组" in t for t in chip_texts_zh)
    assert any("命令目录" in t for t in chip_texts_zh)


def test_handle_huongdan_c4_recurrence_alert_all_3_languages():
    """Kiểm tra mở mục C4 (Thẻ cảnh báo tái phát C7620) đúng nội dung, số liệu và ảnh hiển thị thật."""
    clear_manual_cache()

    # 1. Tiếng Việt: /huongdan C4
    res_vi = handle_huongdan_command("/huongdan C4", conversation_id="CONV-UNIT-VI")
    assert res_vi.section_key == "C4"
    assert res_vi.language == "vi"
    assert "### C4. Phân loại tự động & Thẻ Cảnh báo Tái phát Bước 5 (C7620)" in res_vi.markdown_content
    assert "136" in res_vi.markdown_content
    assert "FY27H2/263" in res_vi.markdown_content
    assert "30.075" in res_vi.markdown_content
    assert "data:image/png;base64," in res_vi.markdown_content
    assert all(cmd.startswith("/huongdan") for _, cmd in res_vi.chips)

    # 2. Tiếng Nhật: /使い方 C4
    res_ja = handle_huongdan_command("/使い方 C4", conversation_id="CONV-UNIT-JA")
    assert res_ja.section_key == "C4"
    assert res_ja.language == "ja"
    assert "### C4. 自動分類とステップ5再発警告カード（C7620）" in res_ja.markdown_content
    assert "136" in res_ja.markdown_content
    assert "FY27H2/263" in res_ja.markdown_content
    assert "30.075" in res_ja.markdown_content
    assert "data:image/png;base64," in res_ja.markdown_content
    assert all(cmd.startswith("/使い方") for _, cmd in res_ja.chips)
    assert "/使い方" in [cmd for _, cmd in res_ja.chips]
    assert "/使い方 C" in [cmd for _, cmd in res_ja.chips]

    # 3. Tiếng Trung: /使用指南 C4
    res_zh = handle_huongdan_command("/使用指南 C4", conversation_id="CONV-UNIT-ZH")
    assert res_zh.section_key == "C4"
    assert res_zh.language == "zh"
    assert "### C4. 自动分类与第5步复发预警卡片(C7620)" in res_zh.markdown_content
    assert "136" in res_zh.markdown_content
    assert "FY27H2/263" in res_zh.markdown_content
    assert "30.075" in res_zh.markdown_content
    assert "data:image/png;base64," in res_zh.markdown_content
    assert all(cmd.startswith("/使用指南") for _, cmd in res_zh.chips)
    assert "/使用指南" in [cmd for _, cmd in res_zh.chips]
    assert "/使用指南 C" in [cmd for _, cmd in res_zh.chips]


def test_handle_huongdan_tat_ca_full_manual_all_3_languages():
    """Kiểm tra xem Toàn bộ cẩm nang hiển thị trọn vẹn 7 phần + phụ lục + 57 ảnh cho cả 3 ngôn ngữ."""
    clear_manual_cache()

    # 1. Tiếng Việt
    res_vi = handle_huongdan_command("/huongdan tat-ca", conversation_id="CONV-UNIT-VI")
    assert res_vi.section_key == "tat_ca"
    assert res_vi.markdown_content.count("data:image/png;base64,") == 57
    assert "PHẦN 1: NHÓM A" in res_vi.markdown_content
    assert "PHẦN 7: NHÓM G" in res_vi.markdown_content

    # 2. Tiếng Nhật
    res_ja = handle_huongdan_command("/使い方 tat-ca", conversation_id="CONV-UNIT-JA")
    assert res_ja.section_key == "tat_ca"
    assert res_ja.markdown_content.count("data:image/png;base64,") == 57
    assert "第1部：グループA" in res_ja.markdown_content
    assert "第7部：グループG" in res_ja.markdown_content

    # 3. Tiếng Trung
    res_zh = handle_huongdan_command("/使用指南 tat-ca", conversation_id="CONV-UNIT-ZH")
    assert res_zh.section_key == "tat_ca"
    assert res_zh.markdown_content.count("data:image/png;base64,") == 57
    assert "第1部分:A组" in res_zh.markdown_content
    assert "第7部分:G组" in res_zh.markdown_content


def test_continuous_improvement_metrics_with_language():
    """Vòng lặp cải thiện liên tục: Ghi đếm cục bộ số lượt gọi kèm trường ngôn ngữ (vi, zh, ja)."""
    record_huongdan_metric("/huongdan", "danh_muc", "CONV-M1", language="vi")
    record_huongdan_metric("/使い方 C4", "C4", "CONV-M1", language="ja")
    record_huongdan_metric("/使用指南 tat-ca", "tat_ca", "CONV-M1", language="zh")

    m = get_huongdan_metrics()
    assert m["total_calls"] >= 3
    assert m["by_section"].get("danh_muc", 0) >= 1
    assert m["by_section"].get("C4", 0) >= 1
    assert m["by_section"].get("tat_ca", 0) >= 1

    # Kiểm tra mở rộng trường by_language
    by_lang = m.get("by_language", {})
    assert by_lang.get("vi", 0) >= 1
    assert by_lang.get("ja", 0) >= 1
    assert by_lang.get("zh", 0) >= 1
    assert "last_called_at" in m


def test_chat_intent_router_huongdan_integration_all_3_languages():
    """Kiểm tra định tuyến ý định chat nhận diện lệnh hướng dẫn trên cả 3 ngôn ngữ."""
    # Tiếng Việt
    intents_vi = classify_all_intents("/huongdan")
    assert len(intents_vi) == 1
    assert intents_vi[0][0] == HUONG_DAN
    assert intents_vi[0][1]["language"] == "vi"
    assert intents_vi[0][1]["muc"] == "danh_muc"

    intents_vi_c4 = classify_all_intents("/huongdan C4")
    assert intents_vi_c4[0][0] == HUONG_DAN
    assert intents_vi_c4[0][1]["language"] == "vi"
    assert intents_vi_c4[0][1]["muc"] == "C4"

    # Tiếng Nhật
    intents_ja = classify_all_intents("/使い方")
    assert len(intents_ja) == 1
    assert intents_ja[0][0] == HUONG_DAN
    assert intents_ja[0][1]["language"] == "ja"
    assert intents_ja[0][1]["muc"] == "danh_muc"

    intents_ja_c4 = classify_all_intents("/使い方 C4")
    assert intents_ja_c4[0][0] == HUONG_DAN
    assert intents_ja_c4[0][1]["language"] == "ja"
    assert intents_ja_c4[0][1]["muc"] == "C4"

    # Tiếng Trung
    intents_zh = classify_all_intents("/使用指南")
    assert len(intents_zh) == 1
    assert intents_zh[0][0] == HUONG_DAN
    assert intents_zh[0][1]["language"] == "zh"
    assert intents_zh[0][1]["muc"] == "danh_muc"

    intents_zh_c4 = classify_all_intents("/使用指南 C4")
    assert intents_zh_c4[0][0] == HUONG_DAN
    assert intents_zh_c4[0][1]["language"] == "zh"
    assert intents_zh_c4[0][1]["muc"] == "C4"

    # Câu hỏi tra cứu thông thường không bị định tuyến nhầm
    assert all(yd != HUONG_DAN for yd, _ in classify_all_intents("Tra cứu lỗi C7620"))
    assert all(yd != HUONG_DAN for yd, _ in classify_all_intents("エラーC7620の発生原因は何ですか？"))
    assert all(yd != HUONG_DAN for yd, _ in classify_all_intents("如何处理故障代码 C7620？"))
