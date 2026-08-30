from __future__ import annotations

from aios_habit.ui_safety import safe_vietnamese_ui_message


def test_dynamic_english_or_internal_errors_fall_back_to_vietnamese():
    fallback = "Không thể hoàn tất thao tác."

    assert safe_vietnamese_ui_message("Permission denied", fallback) == fallback
    assert safe_vietnamese_ui_message("CASE_VERSION_CONFLICT", fallback) == fallback
    assert safe_vietnamese_ui_message(r"C:\secret\data.sqlite", fallback) == fallback
    assert safe_vietnamese_ui_message("Traceback: failure", fallback) == fallback
    assert safe_vietnamese_ui_message("Lỗi kết nối: connection refused", fallback) == fallback
    assert safe_vietnamese_ui_message("Dịch vụ unavailable", fallback) == fallback
    assert safe_vietnamese_ui_message("Lỗi CASE_SECRET đã xảy ra", fallback) == fallback
    assert safe_vietnamese_ui_message("Không đọc được /opt/private/data", fallback) == fallback
    assert safe_vietnamese_ui_message(r"Không đọc được \\may-chu\share", fallback) == fallback


def test_safe_vietnamese_dynamic_message_is_kept():
    assert (
        safe_vietnamese_ui_message("Không thể đọc tài liệu đã chọn.", "Lỗi an toàn.")
        == "Không thể đọc tài liệu đã chọn."
    )
