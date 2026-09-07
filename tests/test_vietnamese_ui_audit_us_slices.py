from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from aios_habit.i18n import LOCALE_NAMES, SUPPORTED_UI_LOCALES, t
from aios_habit.ui_safety import safe_vietnamese_ui_message
from aios_habit.workspace_chat_store import LibraryWriterLease


def test_supported_locales_only_vietnamese():
    assert list(SUPPORTED_UI_LOCALES) == ["vi"], "Chỉ hỗ trợ duy nhất ngôn ngữ tiếng Việt (vi) trên giao diện."
    assert LOCALE_NAMES["vi"] == "Tiếng Việt"


def test_safe_vietnamese_ui_message_redaction():
    raw_error_with_path = "sqlite3.OperationalError: unable to open database file at C:\\Secret\\Data\\db.sqlite"
    safe_msg = safe_vietnamese_ui_message(raw_error_with_path, "Không thể mở cơ sở dữ liệu.")
    assert "C:\\Secret\\Data" not in safe_msg
    assert "OperationalError" not in safe_msg
    assert safe_msg == "Không thể mở cơ sở dữ liệu."

    raw_traceback = "Traceback (most recent call last):\n  File 'app.py', line 10, in <module>\nZeroDivisionError: division by zero"
    safe_msg2 = safe_vietnamese_ui_message(raw_traceback, "Đã xảy ra lỗi khi tính toán.")
    assert "Traceback" not in safe_msg2
    assert "ZeroDivisionError" not in safe_msg2
    assert safe_msg2 == "Đã xảy ra lỗi khi tính toán."


def test_library_writer_lease_busy_message_vietnamese(tmp_path: Path):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    lease = LibraryWriterLease(runtime_dir)
    lease.acquire(owner="may_tram_01")

    busy_msg = LibraryWriterLease.format_busy_message(runtime_dir)
    assert "may_tram_01" in busy_msg
    assert "Thư viện hiện đang được cập nhật bởi máy/tiến trình:" in busy_msg
    assert "Vui lòng chờ máy trên hoàn tất thao tác trước khi thử lại." in busy_msg
    assert "Traceback" not in busy_msg

    lease.release()


def test_all_six_slices_have_vietnamese_translations():
    # US11: Thư viện dùng chung
    assert t("shared_library_expander", locale="vi") != ""
    assert t("shared_library_cleared", locale="vi") != ""
    # Safe fallback on unknown key returns key or fallback
    assert t("unknown_key_xyz", locale="vi") == "unknown_key_xyz"
