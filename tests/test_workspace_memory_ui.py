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


def test_forget_preview_text_consequence_and_empty_safe() -> None:
    """Verifies ticket DESKTOP-HOME-LESSON-FORGET-PANEL-CLARITY 2.2(b):
    1. Statement rỗng trả về chuỗi rỗng, không bao giờ tạo preview rỗng '“”'.
    2. Statement thật hiển thị đầy đủ hậu quả bằng tiếng Việt: không dùng nữa, lịch sử giữ để khôi phục.
    """
    assert forget_preview_text("") == ""
    assert forget_preview_text("   ") == ""
    assert forget_preview_text("\n\t") == ""

    text = forget_preview_text("Kiểm tra áp suất khí nén 6 bar")
    assert "ngừng dùng bài học “Kiểm tra áp suất khí nén 6 bar”" in text
    assert "Từ nay AIOS không dùng bài học này để trả lời nữa" in text
    assert "Lịch sử quyết định vẫn được giữ để có thể khôi phục" in text
    assert "Bấm xác nhận để quên" in text


def test_panel_when_no_lesson_hides_forget_completely(monkeypatch) -> None:
    """Verifies ticket 2.2(a):
    Khi KHÔNG có bài học đã xác nhận liên quan:
    - Chỉ hiện đúng 1 dòng trạng thái giải thích ('Chưa có bài học đã xác nhận cho câu hỏi này.').
    - Ẩn hẳn hành động quên: không hiện hộp xem trước, không nút xác nhận, không nút quên.
    """
    import sys
    from unittest.mock import MagicMock
    from aios_habit.workspace_memory_ui import (
        PENDING_COMMAND_KEY,
        render_workspace_memory_panel,
        render_workspace_memory_workspace,
    )

    captions = []
    infos = []
    buttons = []

    mock_st = MagicMock()
    mock_st.session_state = {
        # Stale/empty draft that previously caused contradictory UI
        PENDING_COMMAND_KEY: {"action": "forget", "statement": ""}
    }
    mock_st.caption.side_effect = lambda msg: captions.append(msg)
    mock_st.info.side_effect = lambda msg: infos.append(msg)
    mock_st.button.side_effect = lambda label, key=None: buttons.append((label, key))

    monkeypatch.setattr("aios_habit.workspace_memory_ui.get_workspace_memory_enabled_preference", lambda: True)
    monkeypatch.setitem(sys.modules, "streamlit", mock_st)

    # 1. render_workspace_memory_panel directly with empty items
    render_workspace_memory_panel(items=(), locale="vi")
    assert any("Chưa có bài học đã xác nhận" in str(c) for c in captions)
    assert len(infos) == 0
    assert len(buttons) == 0

    # 2. render_workspace_memory_workspace with question having no lessons
    captions.clear()
    infos.clear()
    buttons.clear()
    render_workspace_memory_workspace(
        conversation_id="CONV-NO-LESSON",
        last_question="Câu hỏi hoàn toàn chưa có bài học nào",
        workspace_id="test_ws",
    )
    # Must only show status explanation, NO forget preview, NO buttons
    assert any("Chưa có bài học đã xác nhận" in str(c) for c in captions)
    assert len(infos) == 0
    assert not any("Xác nhận" in str(b[0]) for b in buttons)
    assert not any("Quên" in str(b[0]) for b in buttons)
    # Stale forget with empty statement should be cleaned up
    assert PENDING_COMMAND_KEY not in mock_st.session_state


def test_panel_when_has_lesson_shows_real_content_and_clear_consequences(monkeypatch) -> None:
    """Verifies ticket 2.2(b) & 4:
    Khi CÓ bài học:
    - Hiện nội dung thật của bài học (tóm tắt đọc được, không bao giờ rỗng).
    - Giải thích rõ hậu quả: từ nay không dùng nữa, lịch sử giữ để khôi phục.
    - Cung cấp hành động quên bài học rõ ràng.
    """
    import sys
    from unittest.mock import MagicMock
    from aios_habit.workspace_memory_ui import (
        PENDING_COMMAND_KEY,
        format_why_memory_lines,
        render_workspace_memory_panel,
        _render_pending_command,
    )

    item = WorkspaceMemoryRecallItem(
        memory_key="user_memory:mem_compressor:v1",
        source_kind="user_memory",
        source_id="mem_compressor",
        title="Bảo dưỡng máy nén khí",
        statement="Khi bảo dưỡng máy nén khí phải xả áp bình tích trước khi mở van",
        applies_when="Bảo dưỡng máy nén khí",
        does_not_apply_when="",
        scope="workspace:test_ws",
        status="confirmed",
        evidence_refs=("user_confirm",),
        privacy_classification="local_only",
        export_allowed=False,
        updated_at="2026-10-21T00:00:00+00:00",
    )

    # 1. format_why_memory_lines includes real statement
    lines = format_why_memory_lines((item,))
    blob = " ".join(lines)
    assert "Nội dung bài học: Khi bảo dưỡng máy nén khí phải xả áp bình tích trước khi mở van" in blob
    assert "Áp dụng khi: Bảo dưỡng máy nén khí" in blob

    # 2. Panel shows real content and consequence explanation
    captions = []
    buttons = []
    infos = []

    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.caption.side_effect = lambda msg: captions.append(msg)
    mock_st.info.side_effect = lambda msg: infos.append(msg)
    mock_st.button.side_effect = lambda label, key=None: buttons.append((label, key))
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    monkeypatch.setattr("aios_habit.workspace_memory_ui.get_workspace_memory_enabled_preference", lambda: True)
    monkeypatch.setitem(sys.modules, "streamlit", mock_st)

    render_workspace_memory_panel(items=(item,), workspace_id="test_ws", conversation_id="CONV-1")
    cap_blob = " ".join(captions)
    assert "Khi bảo dưỡng máy nén khí phải xả áp bình tích trước khi mở van" in cap_blob
    assert "từ nay AIOS không dùng bài học này trả lời nữa" in cap_blob
    assert "lịch sử vẫn giữ để khôi phục được" in cap_blob
    assert any("Quên bài học này" in str(b[0]) for b in buttons)

    # 3. When forget action is active, preview shows real content + consequence + confirm/cancel buttons
    mock_st.session_state[PENDING_COMMAND_KEY] = {
        "action": "forget",
        "statement": item.statement,
        "memory_id": item.source_id,
    }
    _render_pending_command(workspace_id="test_ws", active_items=(item,))
    assert len(infos) == 1
    assert "AIOS sẽ ngừng dùng bài học “Khi bảo dưỡng máy nén khí phải xả áp bình tích trước khi mở van”" in infos[0]
    assert "Từ nay AIOS không dùng bài học này để trả lời nữa" in infos[0]


def test_skip_empty_records_at_read_layer(tmp_path: Path) -> None:
    """Verifies ticket 2.3:
    Bản ghi bài học có statement rỗng phải được bỏ qua ở tầng đọc / hiển thị (ghi log warning).
    """
    from aios_habit.workspace_memory_service import (
        _effective_user_memory_records,
        list_ledger_memories,
    )
    from aios_habit.workspace_memory_ui import (
        PENDING_COMMAND_KEY,
        restore_pending_drafts_to_session_state,
    )
    import json
    import sys
    from unittest.mock import MagicMock

    dec_file = tmp_path / "memory_decisions.jsonl"
    # Write 1 valid row and 1 empty-statement row
    rows = [
        {
            "action": "confirm",
            "decision_id": "dec_1",
            "memory_id": "mem_valid",
            "statement": "Kiểm tra bu lông",
            "title": "Kiểm tra bu lông",
            "scope": "workspace:test_ws",
            "content_digest": "dig_1",
            "created_at": "2026-10-21T00:00:00+00:00",
        },
        {
            "action": "confirm",
            "decision_id": "dec_2",
            "memory_id": "mem_empty",
            "statement": "",  # Empty statement!
            "title": "Bài học rỗng",
            "scope": "workspace:test_ws",
            "content_digest": "dig_2",
            "created_at": "2026-10-21T00:00:00+00:00",
        },
    ]
    with dec_file.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # _effective_user_memory_records must skip mem_empty
    eff = _effective_user_memory_records(dec_file)
    assert len(eff) == 1
    assert eff[0]["source_id"] == "mem_valid"

    # list_ledger_memories must skip mem_empty
    items, _ = list_ledger_memories("tri_thuc", decisions_path=dec_file)
    ledger_user_items = [it for it in items if it["source_kind"] == "user_memory"]
    assert len(ledger_user_items) == 1
    assert ledger_user_items[0]["source_id"] == "mem_valid"

    # restore_pending_drafts_to_session_state must skip empty command drafts
    draft_file = tmp_path / "pending_drafts.json"
    draft_file.write_text(
        json.dumps({
            "schema_version": "1",
            "command": {"action": "forget", "statement": "   "},
        }),
        encoding="utf-8",
    )
    mock_st = MagicMock()
    mock_st.session_state = {}
    sys.modules["streamlit"] = mock_st
    try:
        restore_pending_drafts_to_session_state(path=draft_file)
        assert PENDING_COMMAND_KEY not in mock_st.session_state
    finally:
        sys.modules.pop("streamlit", None)

