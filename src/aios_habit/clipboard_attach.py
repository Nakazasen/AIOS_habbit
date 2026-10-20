# -*- coding: utf-8 -*-
"""Xử lý đính kèm tệp và hình ảnh qua clipboard và phân định giới hạn theo làn (DESKTOP-HOME-LOGCHART-CAP-RAISE).

Nguyên tắc tách làn:
1. Làn tệp log / biểu đồ (CSV, XLSX, XLS, LOG):
   - Giới hạn trần riêng: MAX_LOG_CHART_FILE_BYTES = 64 MiB (67,108,864 bytes).
   - Lý do: Bao phủ 100% các tệp log sản xuất thực tế đo được tại máy nhà (tệp lớn nhất 2025_02.csv = 30,872,058 bytes,
     hệ số dự phòng ~2.17 lần cho log LSU lớn theo quý/năm).
     Phù hợp với giới hạn an toàn của bộ đọc log_chart.parser (đọc theo luồng/chunk, cắt trần 30,000 dòng, lấy mẫu đều,
     xử lý mượt mà và an toàn RAM).
   - Khi vượt quá 64MB: Thông báo rõ trần của làn biểu đồ và hướng dẫn người dùng cắt bớt dòng/chia nhỏ tệp.
2. Làn tệp chữ / ngữ cảnh chat thông thường (MD, TXT, TSV không vẽ biểu đồ):
   - Giữ nguyên trần 50KB: MAX_COMPOSER_TEXT_FILE_BYTES = 50 * 1024 (51,200 bytes).
   - Lý do: Bảo vệ ngữ cảnh trò chuyện của LLM, tránh tràn cửa sổ ngữ cảnh (token blowout) khi trích văn bản thô vào prompt.
3. Cơ chế dán từ clipboard:
   - Khi clipboard chứa TỆP (sao chép từ Windows Explorer): đọc tệp, áp dụng đúng trần theo làn, đính kèm qua điểm nhận chung.
   - Khi clipboard chứa HÌNH ẢNH: đính kèm dưới dạng clipboard-image.png như cũ.
   - Khi clipboard không có ảnh lẫn tệp (văn bản thô hoặc rỗng): hiển thị gợi ý nhẹ nhàng, tuyệt đối không ném banner đỏ lỗi.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Giới hạn kích thước theo làn
MAX_COMPOSER_TEXT_FILE_BYTES: int = 50 * 1024  # 50 KB tối đa cho văn bản đưa vào ngữ cảnh trò chuyện
MAX_LOG_CHART_FILE_BYTES: int = 64 * 1024 * 1024  # 64 MiB (67,108,864 bytes) tối đa cho tệp log / biểu đồ (DESKTOP-HOME-LOGCHART-CAP-RAISE)
MAX_COMPOSER_ATTACHED_TEXT_CHARS: int = 3000  # 3000 ký tự tối đa gộp vào câu hỏi (đồng bộ OCR)

COMPOSER_SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
COMPOSER_SUPPORTED_TEXT_EXTS = {".csv", ".txt", ".tsv", ".md", ".log"}
COMPOSER_SUPPORTED_EXCEL_EXTS = {".xlsx", ".xls"}
LOG_CHART_SUPPORTED_EXTS = {".csv", ".xlsx", ".xls", ".log"}
COMPOSER_SUPPORTED_EXTS = COMPOSER_SUPPORTED_IMAGE_EXTS | COMPOSER_SUPPORTED_TEXT_EXTS | COMPOSER_SUPPORTED_EXCEL_EXTS


def validate_attachment_lane(file_name: str, file_size: int) -> Tuple[bool, Optional[str], str]:
    """Kiểm tra tính hợp lệ và phân làn kích thước cho tệp đính kèm.

    Returns:
        (is_valid, error_message, lane_type)
        lane_type: "image" | "log_chart" | "text_context" | "unsupported"
    """
    ext = Path(file_name).suffix.lower()

    if ext in COMPOSER_SUPPORTED_IMAGE_EXTS:
        if file_size == 0:
            return False, f'Tệp ảnh "{file_name}" rỗng. Vui lòng chọn tệp có nội dung.', "image"
        return True, None, "image"

    if ext in LOG_CHART_SUPPORTED_EXTS:
        if file_size == 0:
            return False, f'Tệp "{file_name}" rỗng. Vui lòng chọn tệp có nội dung.', "log_chart"
        if file_size > MAX_LOG_CHART_FILE_BYTES:
            msg = (
                f'Tệp "{file_name}" ({file_size:,} bytes) vượt quá giới hạn 64MB cho làn tệp log / biểu đồ. '
                "Vui lòng cắt bớt số dòng, chia nhỏ tệp theo khoảng thời gian hoặc lọc bớt cột trước khi tải lên."
            )
            return False, msg, "log_chart"
        return True, None, "log_chart"

    if ext in COMPOSER_SUPPORTED_TEXT_EXTS:
        if file_size == 0:
            return False, f'Tệp "{file_name}" rỗng. Vui lòng chọn tệp có nội dung.', "text_context"
        if file_size > MAX_COMPOSER_TEXT_FILE_BYTES:
            msg = (
                f'Tệp "{file_name}" ({file_size:,} bytes) vượt quá giới hạn 50KB cho tệp đính kèm chữ/CSV đưa vào ngữ cảnh trò chuyện. '
                "Vui lòng chọn tệp nhỏ hơn."
            )
            return False, msg, "text_context"
        return True, None, "text_context"

    msg = (
        f'Định dạng tệp "{file_name}" không được hỗ trợ. '
        "Khung soạn thảo chỉ nhận tệp ảnh (PNG, JPG, JPEG, WEBP, BMP) hoặc tệp chữ/CSV/Excel (CSV, TXT, TSV, MD, LOG, XLSX, XLS)."
    )
    return False, msg, "unsupported"


def read_clipboard_content() -> Tuple[str, Any]:
    """Đọc dữ liệu từ clipboard hệ điều hành (ưu tiên tệp sao chép từ Explorer, rồi đến ảnh).

    Returns:
        ("files", List[Path]) nếu có tệp sao chép từ Explorer
        ("image", PIL.Image) nếu có hình ảnh trong clipboard
        ("none", None) nếu clipboard rỗng hoặc chỉ có chuỗi chữ thường
    """
    # 1. Sử dụng PIL ImageGrab (hỗ trợ Windows, macOS)
    try:
        from PIL import ImageGrab
        grabbed = ImageGrab.grabclipboard()
        if isinstance(grabbed, list) and grabbed:
            valid_files = [Path(p) for p in grabbed if Path(p).is_file()]
            if valid_files:
                return "files", valid_files
        elif grabbed is not None:
            return "image", grabbed
    except Exception:
        pass

    # 2. Ctypes Windows API fallback cho định dạng CF_HDROP (15)
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        CF_HDROP = 15

        if user32.OpenClipboard(None):
            try:
                if user32.IsClipboardFormatAvailable(CF_HDROP):
                    handle = user32.GetClipboardData(CF_HDROP)
                    if handle:
                        shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
                        shell32.DragQueryFileW.restype = wintypes.UINT
                        count = shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0)
                        files = []
                        for i in range(count):
                            buf = ctypes.create_unicode_buffer(1024)
                            shell32.DragQueryFileW(handle, i, buf, 1024)
                            p = Path(buf.value)
                            if p.is_file():
                                files.append(p)
                        if files:
                            return "files", files
            finally:
                user32.CloseClipboard()
    except Exception:
        pass

    return "none", None
