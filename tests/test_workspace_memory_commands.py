"""US2 remember/forget persistence tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from aios_habit.feature_flags import override_feature_flags
from aios_habit.workspace_chat_store import LibraryWriterLease
from aios_habit.workspace_memory_service import (
    append_memory_decision,
    make_memory_decision,
    override_decisions_path,
    override_recall_records,
    preview_memory_decision,
    recall_workspace_memory,
)
from aios_habit.workspace_memory_models import WorkspaceMemoryRecallRequest
from aios_habit.workspace_memory_ui import confirm_cancelled_message, parse_memory_command


def test_preview_and_cancel_write_nothing(tmp_path: Path) -> None:
    path = tmp_path / "memory_decisions.jsonl"
    preview = preview_memory_decision(
        action="confirm",
        statement="Luôn kiểm tra phớt trước khi chạy",
        scope="workspace:ws_demo",
        evidence_refs=("user_confirm",),
    )
    assert preview["durable"] is False
    assert not path.exists()
    assert "Không ghi" in confirm_cancelled_message() or "hủy" in confirm_cancelled_message().lower()


def test_confirm_append_only_restart_and_forget(tmp_path: Path) -> None:
    path = tmp_path / "workspace_memory" / "memory_decisions.jsonl"
    decision = make_memory_decision(
        action="confirm",
        statement="Luôn kiểm tra phớt trước khi chạy",
        scope="workspace:ws_demo",
        evidence_refs=("user_confirm",),
        applies_when="Thay phớt",
    )
    stored = append_memory_decision(decision, path=path)
    again = append_memory_decision(decision, path=path)
    assert stored.decision_id == again.decision_id or path.read_text(encoding="utf-8").count("\n") == 1
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    request = WorkspaceMemoryRecallRequest(
        question="Thay phớt xong cần kiểm tra gì?",
        workspace_id="ws_demo",
        collection_id="col_demo",
        provider_mode="local",
        include_local_only=True,
    )
    with override_feature_flags(adaptive_work_memory=True), override_recall_records(()), override_decisions_path(path):
        remembered = recall_workspace_memory(request, records=(), decisions_path=path)
        assert any("phớt" in item.statement for item in remembered.items)
        forget = make_memory_decision(
            action="forget",
            statement=decision.statement,
            scope=decision.scope,
            evidence_refs=("user_confirm",),
            memory_id=decision.memory_id,
        )
        append_memory_decision(forget, path=path)
        forgotten = recall_workspace_memory(request, records=(), decisions_path=path)
        assert forgotten.items == ()
    assert path.read_text(encoding="utf-8").count("\n") >= 2


def test_lease_contention_fail_closed(tmp_path: Path) -> None:
    folder = tmp_path / "workspace_memory"
    folder.mkdir()
    path = folder / "memory_decisions.jsonl"
    holder = LibraryWriterLease(folder)
    assert holder.acquire(owner="other") is True
    try:
        decision = make_memory_decision(
            action="confirm",
            statement="Không ghi khi bận",
            scope="workspace:ws_demo",
            evidence_refs=("user_confirm",),
        )
        with pytest.raises(RuntimeError):
            append_memory_decision(decision, path=path)
        assert not path.exists() or path.read_text(encoding="utf-8").strip() == ""
    finally:
        holder.release()


def test_parse_remember_forget_commands() -> None:
    assert parse_memory_command("Hãy nhớ: Kiểm tra dầu")["action"] == "confirm"
    assert parse_memory_command("Hãy quên: Kiểm tra dầu")["action"] == "forget"
    assert parse_memory_command("xin chào") is None


def test_reconfirm_forgotten_memory_appends_decision_and_restores_recall(tmp_path: Path) -> None:
    """F5 Regression: Re-confirming a forgotten memory must append a new decision instead of returning old row."""
    from aios_habit.workspace_memory_service import read_effective_memory

    path = tmp_path / "workspace_memory" / "memory_decisions.jsonl"
    decision = make_memory_decision(
        action="confirm",
        statement="Siết bulong đúng lực",
        scope="workspace:ws_demo",
        evidence_refs=("user_confirm",),
    )
    append_memory_decision(decision, path=path)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    assert len(read_effective_memory(path)) == 1

    # Forget it
    forget = make_memory_decision(
        action="forget",
        statement=decision.statement,
        scope=decision.scope,
        evidence_refs=("user_confirm",),
        memory_id=decision.memory_id,
    )
    append_memory_decision(forget, path=path)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    assert len(read_effective_memory(path)) == 0

    # Re-confirm it
    reconfirm = make_memory_decision(
        action="confirm",
        statement=decision.statement,
        scope=decision.scope,
        evidence_refs=("user_confirm",),
        memory_id=decision.memory_id,
    )
    stored_reconfirm = append_memory_decision(reconfirm, path=path)
    # File MUST now have 3 lines, NOT 2 lines!
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 3
    # Effective memory MUST NOT be empty!
    effective = read_effective_memory(path)
    assert len(effective) == 1
    assert effective[0]["statement"] == "Siết bulong đúng lực"

    # Repeated re-confirm is idempotent (keeps 3 lines)
    again = append_memory_decision(reconfirm, path=path)
    assert len([l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]) == 3


def test_ui_forget_targets_existing_memory_id(tmp_path: Path) -> None:
    """F2 Regression: 'Hãy quên' on UI must point to existing memory_id rather than generating a new random ID."""
    from unittest.mock import MagicMock
    import sys
    from aios_habit.workspace_memory_service import read_effective_memory, _read_jsonl
    from aios_habit.workspace_memory_ui import _render_pending_command, PENDING_COMMAND_KEY

    class FakeSessionState(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                return None

        def __setattr__(self, name, value):
            self[name] = value

        def __delattr__(self, name):
            self.pop(name, None)

    path = tmp_path / "workspace_memory" / "memory_decisions.jsonl"
    decision = make_memory_decision(
        action="confirm",
        statement="Kiểm tra mức dầu trước khi bật máy",
        scope="workspace:NB-42",
        evidence_refs=("user_confirm",),
    )
    append_memory_decision(decision, path=path)
    assert len(read_effective_memory(path)) == 1

    # Mock streamlit session_state and buttons to simulate user confirming "Hãy quên"
    fake_session_state = FakeSessionState({
        PENDING_COMMAND_KEY: {
            "action": "forget",
            "statement": "Kiểm tra mức dầu trước khi bật máy",
        }
    })
    mock_st = MagicMock()
    mock_st.session_state = fake_session_state
    # st.button returns True for "Xác nhận"
    def fake_button(label, key=None):
        return key == "wsc_memory_confirm"
    mock_st.button.side_effect = fake_button
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    with override_decisions_path(path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_default_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: path
        sys.modules["streamlit"] = mock_st
        try:
            _render_pending_command(workspace_id="NB-42")
        finally:
            mem_ui.default_decisions_path = orig_default_path
            sys.modules.pop("streamlit", None)

    # Verify that the forget decision targeted the original decision's memory_id
    rows = _read_jsonl(path)
    assert len(rows) >= 2
    forget_row = rows[-1]
    assert forget_row["action"] == "forget"
    assert forget_row["memory_id"] == decision.memory_id
    # Effective memory must now be empty!
    assert len(read_effective_memory(path)) == 0


def test_append_memory_decision_idempotency_not_hijacked_by_another_memory_with_same_digest(tmp_path: Path) -> None:
    """Idempotency check for a specific memory_id must not be hijacked by another memory with same digest."""
    from aios_habit.workspace_memory_service import _read_jsonl

    path = tmp_path / "workspace_memory" / "memory_decisions.jsonl"
    d_a = make_memory_decision(
        action="confirm",
        statement="Kiểm tra mức dầu trước khi bật máy",
        scope="workspace:ws_demo",
        evidence_refs=("user_confirm",),
        memory_id="mem_A",
    )
    append_memory_decision(d_a, path=path)

    # mem_B has same statement & scope but different memory_id, and is forgotten
    d_b = make_memory_decision(
        action="forget",
        statement="Kiểm tra mức dầu trước khi bật máy",
        scope="workspace:ws_demo",
        evidence_refs=("user_confirm",),
        memory_id="mem_B",
    )
    append_memory_decision(d_b, path=path)
    assert len(_read_jsonl(path)) == 2

    # Calling append_memory_decision for mem_A again must be idempotent and NOT append a 3rd row!
    res = append_memory_decision(d_a, path=path)
    assert res.memory_id == "mem_A"
    rows = _read_jsonl(path)
    assert len(rows) == 2, f"Expected 2 rows due to idempotency, got {len(rows)}"


def test_ui_forget_unmatched_lesson_reports_error_and_does_not_append_phantom_record(tmp_path: Path) -> None:
    """UI 'Hãy quên' on completely unmatched lesson must report error and NOT append phantom record."""
    from unittest.mock import MagicMock
    import sys
    from aios_habit.workspace_memory_service import _read_jsonl
    from aios_habit.workspace_memory_ui import _render_pending_command, PENDING_COMMAND_KEY, NOT_FOUND_FORGET_ERROR

    class FakeSessionState(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                return None

        def __setattr__(self, name, value):
            self[name] = value

        def __delattr__(self, name):
            self.pop(name, None)

    path = tmp_path / "workspace_memory" / "memory_decisions.jsonl"
    d = make_memory_decision(
        action="confirm",
        statement="Kiểm tra mức dầu trước khi bật máy",
        scope="workspace:NB-42",
        evidence_refs=("user_confirm",),
    )
    append_memory_decision(d, path=path)
    assert len(_read_jsonl(path)) == 1

    fake_session_state = FakeSessionState({
        PENDING_COMMAND_KEY: {
            "action": "forget",
            "statement": "Bơm thủy lực hoàn toàn không liên quan",
        }
    })
    mock_st = MagicMock()
    mock_st.session_state = fake_session_state
    mock_st.button.side_effect = lambda label, key=None: key == "wsc_memory_confirm"
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    with override_decisions_path(path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_default_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: path
        sys.modules["streamlit"] = mock_st
        try:
            _render_pending_command(workspace_id="NB-42")
        finally:
            mem_ui.default_decisions_path = orig_default_path
            sys.modules.pop("streamlit", None)

    # Must NOT have appended phantom record!
    rows = _read_jsonl(path)
    assert len(rows) == 1
    # Must have set user-facing error in Vietnamese
    assert fake_session_state.wsc_action_error == NOT_FOUND_FORGET_ERROR
    assert fake_session_state.wsc_action_message is None
    # Pending command must be cleared
    assert PENDING_COMMAND_KEY not in fake_session_state


def test_ui_forget_matches_by_token_overlap_in_effective_memory(tmp_path: Path) -> None:
    """UI 'Hãy quên' with partial query matches active lesson by token overlap."""
    from unittest.mock import MagicMock
    import sys
    from aios_habit.workspace_memory_service import read_effective_memory, _read_jsonl
    from aios_habit.workspace_memory_ui import _render_pending_command, PENDING_COMMAND_KEY

    class FakeSessionState(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                return None

        def __setattr__(self, name, value):
            self[name] = value

        def __delattr__(self, name):
            self.pop(name, None)

    path = tmp_path / "workspace_memory" / "memory_decisions.jsonl"
    d = make_memory_decision(
        action="confirm",
        statement="Trước khi vận hành phải kiểm tra phớt dầu hộp số",
        scope="workspace:NB-42",
        evidence_refs=("user_confirm",),
    )
    append_memory_decision(d, path=path)

    fake_session_state = FakeSessionState({
        PENDING_COMMAND_KEY: {
            "action": "forget",
            "statement": "kiểm tra phớt dầu",
        }
    })
    mock_st = MagicMock()
    mock_st.session_state = fake_session_state
    mock_st.button.side_effect = lambda label, key=None: key == "wsc_memory_confirm"
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    with override_decisions_path(path):
        import aios_habit.workspace_memory_ui as mem_ui
        orig_default_path = mem_ui.default_decisions_path
        mem_ui.default_decisions_path = lambda: path
        sys.modules["streamlit"] = mock_st
        try:
            _render_pending_command(workspace_id="NB-42")
        finally:
            mem_ui.default_decisions_path = orig_default_path
            sys.modules.pop("streamlit", None)

    rows = _read_jsonl(path)
    assert len(rows) == 2
    assert rows[-1]["action"] == "forget"
    assert rows[-1]["memory_id"] == d.memory_id
    assert len(read_effective_memory(path)) == 0


def test_ui_forget_refuses_ambiguous_or_other_workspace_match(tmp_path: Path) -> None:
    from aios_habit.workspace_memory_ui import _resolve_forget_target

    path = tmp_path / "workspace_memory" / "memory_decisions.jsonl"
    for memory_id, statement, scope in (
        ("mem_a", "Kiểm tra bơm alpha", "workspace:NB-42"),
        ("mem_b", "Kiểm tra van beta", "workspace:NB-42"),
        ("mem_c", "Kiểm tra bơm gamma", "workspace:NB-99"),
    ):
        append_memory_decision(
            make_memory_decision(
                action="confirm",
                statement=statement,
                scope=scope,
                evidence_refs=("user_confirm",),
                memory_id=memory_id,
            ),
            path=path,
        )

    assert _resolve_forget_target("kiểm tra", "workspace:NB-42", path) is None
    assert _resolve_forget_target("Kiểm tra bơm gamma", "workspace:NB-42", path) is None

