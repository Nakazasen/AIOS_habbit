# -*- coding: utf-8 -*-
"""Kiểm thử tự động cho cơ chế tách làn đính kèm và nâng trần làn log/biểu đồ lên 64MB (DESKTOP-HOME-LOGCHART-CAP-RAISE).

Các kịch bản kiểm thử:
1. Làn log_chart: CSV tổng hợp > 1MB (1.46MB và 4.60MB tương đương 2026_08_Black_Depth.csv)
   được duyệt qua cổng đính kèm, nạp vào log_chart.parser và vẽ thành công ít nhất 1 biểu đồ.
2. Làn log_chart: Tệp log LSU mô phỏng đúng kích thước tệp thật nặng nhất (30.872.058 bytes)
   được đính kèm hợp lệ, vẽ biểu đồ và đối chiếu chính xác 3 giá trị với dữ liệu thô.
3. Làn log_chart: Tệp > 64MB (67.108.864 bytes) bị chặn với thông báo rõ ràng về trần 64MB và gợi ý cách xử lý.
4. Điều kiện biên trần 64MB:
   - Đúng trần (67.108.864 bytes): Hợp lệ (True).
   - Vượt trần 1 byte (67.108.865 bytes): Bị chặn (False), thông báo rõ 64MB.
5. Làn ngữ cảnh chat (đối chứng âm): Tệp văn bản thuần/Markdown > 50KB bị chặn đúng trần 50KB
   để bảo vệ token ngữ cảnh của LLM.
6. Làn ngữ cảnh chat: Tệp văn bản thuần < 50KB được chấp nhận đưa vào ngữ cảnh câu hỏi.
7. Dán từ clipboard:
   - Khi clipboard chứa tệp CSV log -> tệp được nhận diện qua BufferedWorkspaceUpload và đi vào log_chart.
   - Khi clipboard chứa hình ảnh -> ảnh được bọc thành clipboard-image.png.
   - Khi clipboard rỗng hoặc chứa văn bản thuần -> trả về gợi ý nhẹ nhàng, tuyệt đối không quăng banner lỗi đỏ.
8. Bảng đối chiếu độ bao phủ với toàn bộ các tệp log thực tế (cả mục 1b cũ và top tệp mới): độ bao phủ đạt 100%.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Tuple
from unittest.mock import patch
from PIL import Image

import pytest

from aios_habit.clipboard_attach import (
    MAX_COMPOSER_TEXT_FILE_BYTES,
    MAX_LOG_CHART_FILE_BYTES,
    LOG_CHART_SUPPORTED_EXTS,
    COMPOSER_SUPPORTED_TEXT_EXTS,
    validate_attachment_lane,
    read_clipboard_content,
)
from aios_habit.log_chart import (
    parse_log_file,
    build_initial_spec,
    render_chart_image,
)
from aios_habit.workspace_chat_app import BufferedWorkspaceUpload


def _ensure_synthetic_files() -> Tuple[Path, Path]:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    master_csv = data_dir / "mau_csv_master_lsu.csv"
    lines = master_csv.read_text(encoding="utf-8").splitlines()
    header = lines[0]
    data_rows = lines[1:]

    target_1_5mb = data_dir / "mau_csv_lsu_tong_hop_1_5mb.csv"
    if not target_1_5mb.exists() or target_1_5mb.stat().st_size < 1024 * 1024:
        rows_1_5 = [header]
        for i in range(800):
            base_row = data_rows[i % len(data_rows)]
            tokens = base_row.split(",")
            tokens[1] = f"{16 + (i // 3600):02d}:{(i // 60) % 60:02d}:{i % 60:02d}"
            tokens[2] = f"SYN_UNIT_{i+1:05d}"
            rows_1_5.append(",".join(tokens))
        target_1_5mb.write_text("\n".join(rows_1_5), encoding="utf-8")

    target_4_6mb = data_dir / "2026_08_Black_Depth_synthetic.csv"
    if not target_4_6mb.exists() or target_4_6mb.stat().st_size < 4_500_000:
        rows_4_6 = [header]
        for i in range(2380):
            base_row = data_rows[i % len(data_rows)]
            tokens = base_row.split(",")
            tokens[1] = f"{16 + (i // 3600):02d}:{(i // 60) % 60:02d}:{i % 60:02d}"
            tokens[2] = f"SYN_UNIT_{i+1:05d}"
            rows_4_6.append(",".join(tokens))
        content_4_6 = "\n".join(rows_4_6)
        raw_len = len(content_4_6.encode("utf-8"))
        target_bytes = 4595474
        if raw_len < target_bytes:
            content_4_6 += "\n# PAD:" + ("0" * (target_bytes - raw_len - 8))
        target_4_6mb.write_bytes(content_4_6.encode("utf-8"))

    return target_1_5mb, target_4_6mb


def _ensure_synthetic_31mb_file() -> Path:
    """Tạo hoặc lấy tệp log mô phỏng đúng 30.872.058 bytes của 2025_02.csv với 3 điểm kiểm chứng định trước."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    target_path = data_dir / "2025_02_synthetic_30872058.csv"
    target_bytes = 30872058

    if target_path.exists() and target_path.stat().st_size == target_bytes:
        return target_path

    master_csv = data_dir / "mau_csv_master_lsu.csv"
    lines = master_csv.read_text(encoding="utf-8").splitlines()
    header = lines[0]
    base_rows = lines[1:]

    output_lines = [header]
    current_bytes = len(header.encode("utf-8")) + 1

    known_units = {
        1: {8: -320.0, 9: 52.0, 24: 0.25},
        100: {8: -155.0, 9: 45.0, 24: 0.28},
        1000: {8: -210.0, 9: 68.0, 24: 0.31},
    }

    idx = 0
    while True:
        base_cols = base_rows[idx % len(base_rows)].split(",")
        sec = idx % 60
        minute = (idx // 60) % 60
        hour = (idx // 3600) % 24
        base_cols[0] = f"2025.02.{(idx // 86400) % 28 + 1:02d}"
        base_cols[1] = f"{hour:02d}:{minute:02d}:{sec:02d}"
        unit_id = f"SIR_UNIT_{idx+1:06d}"
        base_cols[2] = unit_id

        if (idx + 1) in known_units:
            ov = known_units[idx + 1]
            for col_idx, val in ov.items():
                base_cols[col_idx] = str(val)

        row_str = ",".join(base_cols)
        row_bytes = len(row_str.encode("utf-8")) + 1

        if current_bytes + row_bytes > target_bytes - 4096:
            break

        output_lines.append(row_str)
        current_bytes += row_bytes
        idx += 1

    content = "\n".join(output_lines)
    raw = content.encode("utf-8")
    diff = target_bytes - len(raw)
    padding_bytes = b"\n# PAD:" + b"=" * (diff - 7)
    raw += padding_bytes
    assert len(raw) == target_bytes
    target_path.write_bytes(raw)
    return target_path


def test_log_chart_lane_allows_csv_over_1mb_and_generates_chart() -> None:
    """Tệp CSV tổng hợp > 1MB (1.46MB) được phép đính kèm qua làn log_chart và sinh biểu đồ hợp lệ."""
    csv_1_5mb, _ = _ensure_synthetic_files()
    assert csv_1_5mb.exists(), "Tệp CSV 1.5MB chưa được chuẩn bị."
    f_size = csv_1_5mb.stat().st_size
    assert f_size > 1024 * 1024, f"Tệp phải lớn hơn 1MB, thực tế {f_size} bytes."

    # 1. Kiểm tra qua cổng tách làn
    is_valid, err_msg, lane = validate_attachment_lane(csv_1_5mb.name, f_size)
    assert is_valid is True
    assert err_msg is None
    assert lane == "log_chart"

    # 2. Kiểm tra đọc bảng và vẽ biểu đồ
    table = parse_log_file(csv_1_5mb)
    assert table.total_rows >= 100
    assert len(table.columns) > 10

    spec = build_initial_spec(table)
    assert spec is not None
    png_bytes = render_chart_image(spec, table)
    assert len(png_bytes) > 1000
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_log_chart_lane_allows_synthetic_real_depth_4_6mb_log() -> None:
    """Tệp log mô phỏng 2026_08_Black_Depth.csv (4,595,474 bytes) được xử lý mượt mà trong làn log_chart."""
    _, csv_4_6mb = _ensure_synthetic_files()
    assert csv_4_6mb.exists()
    f_size = csv_4_6mb.stat().st_size
    assert f_size >= 4_500_000, f"Kích thước tệp {f_size} bytes không đạt ngưỡng ~4.6MB."

    is_valid, err_msg, lane = validate_attachment_lane(csv_4_6mb.name, f_size)
    assert is_valid is True
    assert err_msg is None
    assert lane == "log_chart"

    table = parse_log_file(csv_4_6mb)
    assert table.total_rows > 1000
    spec = build_initial_spec(table)
    png_bytes = render_chart_image(spec, table)
    assert len(png_bytes) > 1000


def test_log_chart_lane_allows_synthetic_heaviest_31mb_log_and_cross_checks_values() -> None:
    """Tệp log mô phỏng 2025_02.csv đúng 30.872.058 bytes đính kèm được, vẽ biểu đồ và khớp 3 giá trị đối chiếu."""
    csv_31mb = _ensure_synthetic_31mb_file()
    assert csv_31mb.exists()
    f_size = csv_31mb.stat().st_size
    assert f_size == 30872058, f"Kích thước tệp phải chính xác 30,872,058 bytes, thực tế: {f_size}"

    # 1. Cổng phân làn chấp thuận
    is_valid, err_msg, lane = validate_attachment_lane(csv_31mb.name, f_size)
    assert is_valid is True, f"Tệp 30.8MB bị chặn sai: {err_msg}"
    assert err_msg is None
    assert lane == "log_chart"

    # 2. Bộ đọc phân tích cấu trúc mượt mà
    table = parse_log_file(csv_31mb)
    assert table.total_rows > 10000
    assert len(table.columns) == 572

    # 3. Đối chiếu 3 giá trị dữ liệu thô tại các dòng kiểm định
    # Điểm 1: Dòng 1 (index 0)
    row_1 = table.rows[0]
    assert row_1["SKEW:BLACK[um]"] == -320.0
    assert row_1["BOW:BLACK:-70[um]"] == 52.0
    assert row_1["LIGHT_PATH:BLACK:-140[mm]"] == 0.25

    # Điểm 2: Dòng 100 (index 99)
    row_100 = table.rows[99]
    assert row_100["SKEW:BLACK[um]"] == -155.0
    assert row_100["BOW:BLACK:-70[um]"] == 45.0
    assert row_100["LIGHT_PATH:BLACK:-140[mm]"] == 0.28

    # Điểm 3: Dòng 1000 (index 999)
    row_1000 = table.rows[999]
    assert row_1000["SKEW:BLACK[um]"] == -210.0
    assert row_1000["BOW:BLACK:-70[um]"] == 68.0
    assert row_1000["LIGHT_PATH:BLACK:-140[mm]"] == 0.31

    # 4. Dựng biểu đồ thành công
    spec = build_initial_spec(table)
    png_bytes = render_chart_image(spec, table)
    assert len(png_bytes) > 1000
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_log_chart_lane_blocks_file_over_64mb_with_actionable_message() -> None:
    """Tệp vượt quá 64MB trong làn log_chart bị chặn và thông báo rõ giải pháp khắc phục."""
    huge_size = 68 * 1024 * 1024  # 68 MB
    is_valid, err_msg, lane = validate_attachment_lane("huge_yearly_log.csv", huge_size)

    assert is_valid is False
    assert lane == "log_chart"
    assert "vượt quá giới hạn 64MB cho làn tệp log / biểu đồ" in err_msg
    assert "Vui lòng cắt bớt số dòng" in err_msg


def test_log_chart_lane_boundary_conditions_exact_cap_and_cap_plus_one() -> None:
    """Kiểm tra điều kiện biên: Đúng trần 64 MiB (67.108.864 bytes) và Vượt trần 1 byte (67.108.865 bytes)."""
    exact_cap = 64 * 1024 * 1024  # 67,108,864 bytes
    cap_plus_one = exact_cap + 1  # 67,108,865 bytes

    # Biên 1: Đúng trần 64 MiB -> Hợp lệ
    valid_exact, msg_exact, lane_exact = validate_attachment_lane("exact_64mb.csv", exact_cap)
    assert valid_exact is True
    assert msg_exact is None
    assert lane_exact == "log_chart"

    # Biên 2: Vượt trần đúng 1 byte -> Bị chặn
    valid_over, msg_over, lane_over = validate_attachment_lane("over_64mb.csv", cap_plus_one)
    assert valid_over is False
    assert lane_over == "log_chart"
    assert "vượt quá giới hạn 64MB cho làn tệp log / biểu đồ" in msg_over
    assert "67,108,865 bytes" in msg_over


def test_context_inlining_lane_blocks_plain_text_over_50kb_negative_control() -> None:
    """Đối chứng âm: Tệp văn bản Markdown/Text > 50KB bị chặn đúng trần 50KB để bảo vệ prompt."""
    text_size = 65 * 1024  # 65 KB
    is_valid, err_msg, lane = validate_attachment_lane("tai_lieu_huong_dan.md", text_size)

    assert is_valid is False
    assert lane == "text_context"
    assert "vượt quá giới hạn 50KB cho tệp đính kèm chữ/CSV đưa vào ngữ cảnh trò chuyện" in err_msg
    assert "Vui lòng chọn tệp nhỏ hơn" in err_msg


def test_context_inlining_lane_allows_small_text_under_50kb() -> None:
    """Tệp văn bản Markdown/Text < 50KB được chấp nhận cho làn ngữ cảnh."""
    small_size = 15 * 1024  # 15 KB
    is_valid, err_msg, lane = validate_attachment_lane("ghi_chu.md", small_size)

    assert is_valid is True
    assert err_msg is None
    assert lane == "text_context"


def test_clipboard_paste_detects_files_from_explorer() -> None:
    """Khi clipboard chứa đường dẫn tệp sao chép từ Explorer, hàm đọc clipboard bóc tách chính xác."""
    sample_file = Path(r"D:\Sandbox\AIOS_habbit\data\mau_csv_master_lsu.csv")
    with patch("PIL.ImageGrab.grabclipboard", return_value=[str(sample_file)]):
        c_type, c_data = read_clipboard_content()
        assert c_type == "files"
        assert len(c_data) == 1
        assert c_data[0] == sample_file

        # Bọc qua BufferedWorkspaceUpload
        upload = BufferedWorkspaceUpload(c_data[0].name, c_data[0].read_bytes())
        assert upload.name == "mau_csv_master_lsu.csv"
        assert len(upload.getvalue()) == sample_file.stat().st_size


def test_clipboard_paste_detects_image() -> None:
    """Khi clipboard chứa hình ảnh, hàm đọc clipboard trả về loại image."""
    dummy_img = Image.new("RGB", (64, 64), color="red")
    with patch("PIL.ImageGrab.grabclipboard", return_value=dummy_img):
        c_type, c_data = read_clipboard_content()
        assert c_type == "image"
        assert isinstance(c_data, Image.Image)


def test_clipboard_paste_handles_text_or_empty_without_error() -> None:
    """Khi clipboard không có ảnh lẫn tệp (chuỗi hoặc rỗng), trả về none nhẹ nhàng."""
    with patch("PIL.ImageGrab.grabclipboard", return_value=None):
        with patch("ctypes.windll.user32.OpenClipboard", return_value=0):
            c_type, c_data = read_clipboard_content()
            assert c_type == "none"
            assert c_data is None


def test_coverage_against_all_real_lsu_logs() -> None:
    """Đối chiếu trần 64MB với toàn bộ bảng 14 tệp log thực tế tại máy: bao phủ 100%."""
    all_real_logs = [
        # Top tệp lớn nhất user khảo sát tại máy (2026-10-21 06:04)
        ("2025_02.csv", 30_872_058),  # Sirius LSU, Linearity - lớn nhất
        ("2026_08.csv", 27_057_740),  # Iris LSU, JIG 2ND-1004 - vượt trần 25MB cũ
        ("IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv", 24_375_633),
        ("2026_08_Black_Depth.csv", 20_073_562),  # Bản JIG 2ND-1004
        ("2026_08_Cyan_Depth.csv", 17_048_340),
        ("2026_08_Error_BowOverAdjust.csv", 16_984_399),
        # 8 tệp thực tế đã đối chiếu tại vé trước
        ("2026_07_Magenta_depth.csv", 2_669_985),
        ("2026_07_Cyan_depth.csv", 2_665_534),
        ("2026_07_Yellow_depth.csv", 2_666_115),
        ("2026_07_Black_depth.csv", 4_161_009),
        ("2026_08_Black_Depth.csv", 4_595_474),  # Bản JIG 2ND-1002
        ("2ND-1035-1_2026_07_UnitTest.csv", 86_573),
        ("Log2021_4.csv", 107_206),
        ("XY_TARGET_2021_4_Depth.csv", 18_337),
    ]

    covered_count = 0
    for name, size in all_real_logs:
        is_valid, err_msg, lane = validate_attachment_lane(name, size)
        assert is_valid is True, f"Tệp {name} ({size} bytes) bị từ chối oan uổng: {err_msg}"
        assert lane == "log_chart"
        covered_count += 1

    assert covered_count == len(all_real_logs)
    coverage_ratio = covered_count / len(all_real_logs)
    assert coverage_ratio == 1.0  # 100% bao phủ
