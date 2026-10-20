"""Tests for ticket DESKTOP-MEMORY-DRAFT-PERSIST-HOME.

Verifies:
1. Command drafts ("Hãy nhớ:" / "Hãy quên:") save, restore across sessions, and clear on confirm/cancel.
2. Conflict drafts (command conflicts and correction conflicts) save, restore across sessions, and clear on apply/cancel.
3. Correction form drafts ("Sửa để AIOS học") save, restore across sessions, and clear on confirm/cancel/clear.
4. Corrupted file fail-safe (corrupt JSON, empty file, binary garbage, non-dict JSON) never crashes the app.
5. Full round-trip simulation matching ticket acceptance criteria.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

from aios_habit.workspace_memory_models import CorrectionLessonCandidate
from aios_habit.workspace_memory_service import (
    _read_jsonl,
    append_memory_decision,
    clear_pending_command,
    clear_pending_correction_conflict,
    clear_pending_correction_form,
    clear_pending_drafts,
    default_decisions_path,
    default_pending_drafts_path,
    load_pending_drafts,
    make_memory_decision,
    override_decisions_path,
    override_pending_drafts_path,
    read_effective_memory,
    save_pending_command,
    save_pending_command_conflict,
    save_pending_correction_conflict,
    save_pending_correction_form,
    save_pending_drafts,
)
from aios_habit.workspace_memory_ui import (
    PENDING_COMMAND_KEY,
    PENDING_CONFLICT_KEY,
    _render_correction_form,
    _render_pending_command,
    queue_memory_command_if_present,
    render_workspace_memory_workspace,
    restore_pending_drafts_to_session_state,
)


class FakeSessionState(dict):
    """Mock streamlit.session_state with attribute and dict access."""

    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError:
            return None

    def __setattr__(self, name: str, value):
        self[name] = value

    def __delattr__(self, name: str):
        self.pop(name, None)


def test_command_draft_save_restore_and_clear_on_confirm(tmp_path: Path) -> None:
    """Loai 1: Nhap lenh 'Hay nho:' luu xuong dia, song sot qua phien moi, va xoa khi xac nhan."""
    drafts_path = tmp_path / "pending_drafts.json"
    decisions_path = tmp_path / "memory_decisions.jsonl"

    with override_pending_drafts_path(drafts_path), override_decisions_path(decisions_path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_dec_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: decisions_path

        mock_st = MagicMock()
        session_1 = FakeSessionState()
        mock_st.session_state = session_1
        sys.modules["streamlit"] = mock_st

        try:
            # 1. User inputs command
            queued = queue_memory_command_if_present("Hãy nhớ: Kiểm tra áp suất khí nén 6 bar")
            assert queued is True
            assert PENDING_COMMAND_KEY in session_1
            assert session_1[PENDING_COMMAND_KEY]["statement"] == "Kiểm tra áp suất khí nén 6 bar"

            # Verify saved on disk
            assert drafts_path.exists()
            disk_drafts = load_pending_drafts(drafts_path)
            assert disk_drafts.get("command") is not None
            assert disk_drafts["command"]["statement"] == "Kiểm tra áp suất khí nén 6 bar"

            # 2. Simulate closing browser / starting a brand-new session (empty session_state)
            session_2 = FakeSessionState()
            mock_st.session_state = session_2

            # New session restores drafts
            restore_pending_drafts_to_session_state(drafts_path)
            assert PENDING_COMMAND_KEY in session_2
            assert session_2[PENDING_COMMAND_KEY]["statement"] == "Kiểm tra áp suất khí nén 6 bar"

            # 3. User clicks "Xác nhận" in the restored session
            mock_st.button.side_effect = lambda label, key=None: key == "wsc_memory_confirm"
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            _render_pending_command(workspace_id="test_ws")

            # 4. Draft is removed from session and disk
            assert PENDING_COMMAND_KEY not in session_2
            assert not drafts_path.exists() or load_pending_drafts(drafts_path).get("command") is None

            # 5. Decision is saved in memory_decisions.jsonl
            rows = _read_jsonl(decisions_path)
            assert len(rows) == 1
            assert rows[0]["statement"] == "Kiểm tra áp suất khí nén 6 bar"
            assert rows[0]["action"] == "confirm"
        finally:
            mem_ui.default_decisions_path = orig_dec_path
            sys.modules.pop("streamlit", None)


def test_command_draft_clear_on_cancel(tmp_path: Path) -> None:
    """Nhap lenh 'Hay nho:' bi huy bo se xoa ban nhap tren dia."""
    drafts_path = tmp_path / "pending_drafts.json"
    decisions_path = tmp_path / "memory_decisions.jsonl"

    with override_pending_drafts_path(drafts_path), override_decisions_path(decisions_path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_dec_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: decisions_path

        mock_st = MagicMock()
        session = FakeSessionState({
            PENDING_COMMAND_KEY: {"action": "confirm", "statement": "Bài học sẽ hủy"}
        })
        save_pending_command(session[PENDING_COMMAND_KEY], path=drafts_path)
        assert drafts_path.exists()

        mock_st.session_state = session
        mock_st.button.side_effect = lambda label, key=None: key == "wsc_memory_cancel"
        mock_st.columns.return_value = (MagicMock(), MagicMock())
        sys.modules["streamlit"] = mock_st

        try:
            _render_pending_command(workspace_id="test_ws")
            assert PENDING_COMMAND_KEY not in session
            assert not drafts_path.exists() or load_pending_drafts(drafts_path).get("command") is None
            assert not decisions_path.exists() or len(_read_jsonl(decisions_path)) == 0
        finally:
            mem_ui.default_decisions_path = orig_dec_path
            sys.modules.pop("streamlit", None)


def test_command_conflict_draft_save_restore_and_apply(tmp_path: Path) -> None:
    """Loai 2a: Nhap xung dot lenh chua chon cach xu ly luu xuong dia, khoi phuc va xoa sau khi chon."""
    drafts_path = tmp_path / "pending_drafts.json"
    decisions_path = tmp_path / "memory_decisions.jsonl"

    # Pre-populate an existing memory
    existing = make_memory_decision(
        action="confirm",
        statement="Kiểm tra áp suất thủy lực 150 bar",
        scope="workspace:test_ws",
        evidence_refs=("user_confirm",),
    )
    append_memory_decision(existing, path=decisions_path)

    with override_pending_drafts_path(drafts_path), override_decisions_path(decisions_path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_dec_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: decisions_path

        mock_st = MagicMock()
        session_1 = FakeSessionState({
            PENDING_COMMAND_KEY: {"action": "confirm", "statement": "Kiểm tra áp suất thủy lực 160 bar"}
        })
        save_pending_command(session_1[PENDING_COMMAND_KEY], path=drafts_path)
        mock_st.session_state = session_1
        # Click confirm -> conflict detected
        mock_st.button.side_effect = lambda label, key=None: key == "wsc_memory_confirm"
        mock_st.columns.return_value = (MagicMock(), MagicMock())
        sys.modules["streamlit"] = mock_st

        try:
            _render_pending_command(workspace_id="test_ws")
            assert PENDING_CONFLICT_KEY in session_1

            # Check that conflict is persisted to disk
            disk_drafts = load_pending_drafts(drafts_path)
            assert disk_drafts.get("command_conflict") is not None
            assert disk_drafts.get("command") is not None

            # Simulate new session
            session_2 = FakeSessionState()
            mock_st.session_state = session_2
            restore_pending_drafts_to_session_state(drafts_path)

            assert PENDING_COMMAND_KEY in session_2
            assert PENDING_CONFLICT_KEY in session_2

            # Now apply choice: replace
            mock_st.radio.return_value = "replace"
            mock_st.button.side_effect = lambda label, key=None: key == "wsc_memory_conflict_apply"
            _render_pending_command(workspace_id="test_ws")

            # Must be cleared from session and disk
            assert PENDING_COMMAND_KEY not in session_2
            assert PENDING_CONFLICT_KEY not in session_2
            assert not drafts_path.exists() or not load_pending_drafts(drafts_path).get("command")

            # Decisions ledger updated
            rows = _read_jsonl(decisions_path)
            assert len(rows) == 2
            assert rows[-1]["action"] == "supersede"
        finally:
            mem_ui.default_decisions_path = orig_dec_path
            sys.modules.pop("streamlit", None)


def test_correction_form_draft_save_restore_and_confirm(tmp_path: Path) -> None:
    """Loai 3: Trang thai form 'Sua de AIOS hoc' dang cho xac nhan luu xuong dia, khoi phuc va xoa khi xac nhan."""
    drafts_path = tmp_path / "pending_drafts.json"
    decisions_path = tmp_path / "memory_decisions.jsonl"
    msg_id = "msg_asst_123"

    with override_pending_drafts_path(drafts_path), override_decisions_path(decisions_path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_dec_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: decisions_path

        mock_st = MagicMock()
        session_1 = FakeSessionState()
        mock_st.session_state = session_1
        mock_st.columns.return_value = (MagicMock(), MagicMock())
        mock_st.text_area.return_value = "Luôn tắt nguồn trước khi tháo cảm biến"
        mock_st.text_input.side_effect = (
            lambda label, key=None: "Tháo cảm biến áp suất" if "Áp dụng khi" in label else ""
        )
        # Not clicking confirm yet: just typing
        mock_st.button.return_value = False
        sys.modules["streamlit"] = mock_st

        try:
            # First render: user typed statement and applies_when
            _render_correction_form(message_id=msg_id, trace_id="trc_99", workspace_id="ws_main")

            # Check that form draft is saved to disk
            assert drafts_path.exists()
            drafts = load_pending_drafts(drafts_path)
            form_drafts = drafts.get("correction_forms", {})
            assert msg_id in form_drafts
            assert form_drafts[msg_id]["statement"] == "Luôn tắt nguồn trước khi tháo cảm biến"
            assert form_drafts[msg_id]["applies_when"] == "Tháo cảm biến áp suất"

            # Simulate new session (page refresh / browser reopen)
            session_2 = FakeSessionState()
            mock_st.session_state = session_2

            # Render in new session: should restore draft into session state
            restore_pending_drafts_to_session_state(drafts_path)
            assert session_2.get(f"wsc_corr_statement_{msg_id}") == "Luôn tắt nguồn trước khi tháo cảm biến"
            assert session_2.get(f"wsc_corr_applies_{msg_id}") == "Tháo cảm biến áp suất"

            # Now user clicks "Xác nhận bài học"
            mock_st.button.side_effect = lambda label, key=None: key == f"wsc_corr_confirm_{msg_id}"
            _render_correction_form(message_id=msg_id, trace_id="trc_99", workspace_id="ws_main")

            # Form draft must be cleared from disk
            assert not drafts_path.exists() or msg_id not in load_pending_drafts(drafts_path).get("correction_forms", {})

            # Decision must be appended to memory_decisions.jsonl
            rows = _read_jsonl(decisions_path)
            assert len(rows) == 1
            assert rows[0]["statement"] == "Luôn tắt nguồn trước khi tháo cảm biến"
            assert rows[0]["action"] == "confirm"
        finally:
            mem_ui.default_decisions_path = orig_dec_path
            sys.modules.pop("streamlit", None)


def test_correction_form_draft_cleared_on_cancel(tmp_path: Path) -> None:
    """Nguoi dung bam 'Huy bai hoc' se xoa ban nhap form sua tren dia."""
    drafts_path = tmp_path / "pending_drafts.json"
    decisions_path = tmp_path / "memory_decisions.jsonl"
    msg_id = "msg_asst_cancel"

    save_pending_correction_form(
        msg_id,
        statement="Bài học thử nghiệm",
        applies_when="Khi test",
        path=drafts_path,
    )
    assert drafts_path.exists()

    with override_pending_drafts_path(drafts_path), override_decisions_path(decisions_path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_dec_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: decisions_path

        mock_st = MagicMock()
        session = FakeSessionState({
            f"wsc_corr_statement_{msg_id}": "Bài học thử nghiệm",
            f"wsc_corr_applies_{msg_id}": "Khi test",
        })
        mock_st.session_state = session
        mock_st.columns.return_value = (MagicMock(), MagicMock())
        mock_st.text_area.return_value = "Bài học thử nghiệm"
        mock_st.text_input.side_effect = lambda label, key=None: "Khi test" if "Áp dụng khi" in label else ""
        mock_st.button.side_effect = lambda label, key=None: key == f"wsc_corr_cancel_{msg_id}"
        sys.modules["streamlit"] = mock_st

        try:
            _render_correction_form(message_id=msg_id, trace_id=None, workspace_id="ws_main")
            assert not drafts_path.exists() or msg_id not in load_pending_drafts(drafts_path).get("correction_forms", {})
            assert not decisions_path.exists() or len(_read_jsonl(decisions_path)) == 0
        finally:
            mem_ui.default_decisions_path = orig_dec_path
            sys.modules.pop("streamlit", None)


def test_correction_conflict_draft_save_restore_and_apply(tmp_path: Path) -> None:
    """Loai 2b: Nhap xung dot form sua chua chon cach xu ly luu xuong dia, khoi phuc va xoa sau khi chon."""
    drafts_path = tmp_path / "pending_drafts.json"
    decisions_path = tmp_path / "memory_decisions.jsonl"
    msg_id = "msg_asst_conflict"

    # Pre-populate an existing memory
    existing = make_memory_decision(
        action="confirm",
        statement="Vặn ốc theo chiều kim đồng hồ",
        scope="workspace:ws_mech",
        evidence_refs=("user_confirm",),
    )
    append_memory_decision(existing, path=decisions_path)

    with override_pending_drafts_path(drafts_path), override_decisions_path(decisions_path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_dec_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: decisions_path

        mock_st = MagicMock()
        session_1 = FakeSessionState({
            f"wsc_corr_statement_{msg_id}": "Vặn ốc ngược chiều kim đồng hồ",
            f"wsc_corr_applies_{msg_id}": "Lắp ren ngược",
        })
        mock_st.session_state = session_1
        mock_st.columns.return_value = (MagicMock(), MagicMock())
        mock_st.text_area.return_value = "Vặn ốc ngược chiều kim đồng hồ"
        mock_st.text_input.side_effect = lambda label, key=None: "workspace:ws_mech" if "Áp dụng khi" in label else ""
        # Click confirm -> duplicate detected -> sets conflict state
        mock_st.button.side_effect = lambda label, key=None: key == f"wsc_corr_confirm_{msg_id}"
        sys.modules["streamlit"] = mock_st

        try:
            _render_correction_form(message_id=msg_id, trace_id=None, workspace_id="ws_mech")
            corr_key = f"wsc_corr_conflict_{msg_id}"
            assert corr_key in session_1

            # Check that correction conflict is saved on disk
            drafts = load_pending_drafts(drafts_path)
            assert msg_id in drafts.get("correction_conflicts", {})

            # Simulate new session
            session_2 = FakeSessionState()
            mock_st.session_state = session_2
            restore_pending_drafts_to_session_state(drafts_path)
            assert corr_key in session_2

            # Now apply choice: merge
            mock_st.radio.return_value = "merge"
            mock_st.button.side_effect = lambda label, key=None: key == f"wsc_corr_apply_{msg_id}"
            _render_correction_form(message_id=msg_id, trace_id=None, workspace_id="ws_mech")

            # Must be cleared from session and disk
            assert corr_key not in session_2
            assert not drafts_path.exists() or msg_id not in load_pending_drafts(drafts_path).get("correction_conflicts", {})

            # Decisions ledger updated with merged decision
            rows = _read_jsonl(decisions_path)
            assert len(rows) == 2
            assert rows[-1]["action"] == "merge"
        finally:
            mem_ui.default_decisions_path = orig_dec_path
            sys.modules.pop("streamlit", None)


@pytest.mark.parametrize(
    "corrupt_content",
    [
        "{" * 50,  # Corrupt JSON syntax
        "",  # 0-byte file
        "   \n  \t ",  # Whitespace only
        "null",  # JSON null
        "[1, 2, 3]",  # JSON array instead of dict
        '"just a string"',  # JSON string instead of dict
        "12345",  # JSON number
        b"\x00\xff\xfe\x12\x34\x88\x99".decode("latin-1"),  # Binary garbage
    ],
)
def test_corrupted_file_fail_safe_never_crashes(tmp_path: Path, corrupt_content: str) -> None:
    """Yeu cau (d): Tep pending bi hong/khong doc duoc: fail-safe ve trang thai khong-co-nhap-cho, TUYET DOI khong lam sap app."""
    corrupt_file = tmp_path / "pending_drafts.json"
    corrupt_file.write_text(corrupt_content, encoding="utf-8")

    # 1. load_pending_drafts must return empty dict, never raise
    loaded = load_pending_drafts(corrupt_file)
    assert loaded == {}

    # 2. restore_pending_drafts_to_session_state must execute cleanly
    mock_st = MagicMock()
    session = FakeSessionState()
    mock_st.session_state = session
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    mock_st.text_area.return_value = ""
    mock_st.text_input.return_value = ""
    mock_st.button.return_value = False
    sys.modules["streamlit"] = mock_st
    try:
        restore_pending_drafts_to_session_state(corrupt_file)
        assert len(session) == 0

        # 3. render_workspace_memory_workspace must execute cleanly without error
        render_workspace_memory_workspace(
            conversation_id="conv_1",
            last_question="Câu hỏi bình thường",
            last_assistant_id="asst_1",
            workspace_id="ws_1",
        )
    finally:
        sys.modules.pop("streamlit", None)


def test_clear_all_pending_drafts_removes_file(tmp_path: Path) -> None:
    """Khi toan bo ban nhap duoc xoa, tep pending_drafts.json bien mat khoi dia."""
    drafts_path = tmp_path / "pending_drafts.json"
    save_pending_command({"action": "confirm", "statement": "Test"}, path=drafts_path)
    assert drafts_path.exists()

    clear_pending_drafts(drafts_path)
    assert not drafts_path.exists()
    assert load_pending_drafts(drafts_path) == {}
