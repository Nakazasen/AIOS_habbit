"""Vietnamese memory UI copy tests."""

from __future__ import annotations

from aios_habit.workspace_memory_models import WorkspaceMemoryRecallItem
from aios_habit.workspace_memory_ui import (
    conflict_choice_labels,
    correction_action_label,
    forget_preview_text,
    format_why_memory_lines,
    memory_toggle_help,
    memory_toggle_label,
    memory_toggle_status,
    remember_preview_text,
    why_memory_panel_title,
)


def test_why_panel_is_vietnamese_without_paths() -> None:
    item = WorkspaceMemoryRecallItem(
        memory_key="memory_unit:mu_torque:v1",
        source_kind="memory_unit",
        source_id="mu_torque",
        title="Momen siết",
        statement="Siết 35 N·m",
        applies_when="Lắp nắp máy",
        does_not_apply_when="",
        scope="workspace:ws_demo",
        status="verified",
        evidence_refs=("ev_1",),
        privacy_classification="local_only",
        export_allowed=False,
        updated_at="2026-08-01T00:00:00+00:00",
    )
    title = why_memory_panel_title()
    lines = format_why_memory_lines((item,))
    blob = title + " ".join(lines)
    assert "Vì sao AIOS nhớ" in title
    assert "D:\\" not in blob
    assert "traceback" not in blob.lower()
    assert "graphrag" not in blob.lower()


def test_memory_toggle_copy_is_plain_vietnamese() -> None:
    assert memory_toggle_label() == "Cho AIOS ghi nhớ để hỗ trợ tôi tốt hơn"
    assert memory_toggle_status(True) == "Đang bật ghi nhớ"
    assert memory_toggle_status(False) == "Đang tắt ghi nhớ"
    help_text = memory_toggle_help()
    assert "xác nhận" in help_text
    assert "feature" not in help_text.lower()
    assert "cá nhân hóa" not in help_text.lower()


def test_preview_copy_vietnamese() -> None:
    remember = remember_preview_text("Kiểm tra phớt", "workspace:ws_demo")
    forget = forget_preview_text("Kiểm tra phớt")
    assert "Xem trước" in remember
    assert "xác nhận" in remember
    assert "ngừng dùng" in forget
    assert all(" " in label or label for label in conflict_choice_labels().values())
    assert "Sửa để AIOS học" in correction_action_label()
    for label in conflict_choice_labels().values():
        assert "D:\\" not in label
        assert "traceback" not in label.lower()
