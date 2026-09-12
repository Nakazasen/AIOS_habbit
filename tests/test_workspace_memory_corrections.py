"""US3 correction candidate tests."""

from __future__ import annotations

from pathlib import Path

from aios_habit.feature_flags import override_feature_flags
from aios_habit.workspace_memory_models import CorrectionLessonCandidate
from aios_habit.workspace_memory_service import (
    append_memory_decision,
    find_near_duplicates,
    override_recall_records,
    recall_workspace_memory,
)
from aios_habit.workspace_memory_models import WorkspaceMemoryRecallRequest
from aios_habit.workspace_memory_ui import correction_preview_text, conflict_choice_labels


def test_candidate_not_recalled_until_confirmed(tmp_path: Path) -> None:
    candidate = CorrectionLessonCandidate(
        candidate_id="cand_1",
        statement="Không tăng áp thủy lực khi quá tải",
        applies_when="Quá tải thủy lực",
        does_not_apply_when="",
        message_ref="msg_42",
        trace_ref="trc_1",
    )
    assert candidate.status == "candidate"
    assert "Chưa dùng" in correction_preview_text(candidate)
    path = tmp_path / "memory_decisions.jsonl"
    request = WorkspaceMemoryRecallRequest(
        question="Có được tăng áp thủy lực khi quá tải không?",
        workspace_id="ws_demo",
        collection_id="col_demo",
        provider_mode="local",
        include_local_only=True,
    )
    with override_feature_flags(adaptive_work_memory=True), override_recall_records(()):
        before = recall_workspace_memory(request, records=(), decisions_path=path)
        assert before.items == ()
        decision = candidate.to_decision(
            actor_label="người dùng",
            scope="workspace:ws_demo",
            evidence_refs=("msg_42",),
        )
        append_memory_decision(decision, path=path)
        after = recall_workspace_memory(request, records=(), decisions_path=path)
        assert any("thủy lực" in item.statement for item in after.items)


def test_duplicate_and_conflict_choices(tmp_path: Path) -> None:
    path = tmp_path / "memory_decisions.jsonl"
    first = CorrectionLessonCandidate(
        candidate_id="cand_a",
        statement="Không tăng áp thủy lực khi quá tải",
        applies_when="Quá tải thủy lực",
        does_not_apply_when="",
        message_ref="msg_1",
    ).to_decision(actor_label="người dùng", scope="workspace:ws_demo", evidence_refs=("msg_1",))
    append_memory_decision(first, path=path)
    hits = find_near_duplicates(first.statement, first.scope, path)
    assert hits
    labels = conflict_choice_labels()
    assert set(labels) == {"merge", "replace", "keep_both", "cancel"}


def test_conflict_choices_persist_or_cancel(tmp_path: Path) -> None:
    from aios_habit.workspace_memory_service import apply_conflict_choice

    path = tmp_path / "memory_decisions.jsonl"
    first = CorrectionLessonCandidate(
        candidate_id="cand_keep",
        statement="Không tăng áp thủy lực khi quá tải",
        applies_when="Quá tải thủy lực",
        does_not_apply_when="",
        message_ref="msg_keep",
    )
    append_memory_decision(
        first.to_decision(actor_label="người dùng", scope="workspace:ws_demo", evidence_refs=("msg_keep",)),
        path=path,
    )
    second = CorrectionLessonCandidate(
        candidate_id="cand_new",
        statement="Không tăng áp thủy lực khi quá tải trừ khi có lệnh",
        applies_when="Quá tải thủy lực",
        does_not_apply_when="",
        message_ref="msg_new",
    )
    cancelled = apply_conflict_choice("cancel", second, path=path, scope="workspace:ws_demo")
    assert cancelled is None
    replaced = apply_conflict_choice("replace", second, path=path, scope="workspace:ws_demo")
    assert replaced is not None
    assert replaced.action == "supersede"
    assert "trừ khi" in replaced.statement


def test_candidate_does_not_store_raw_answer() -> None:
    candidate = CorrectionLessonCandidate(
        candidate_id="cand_raw",
        statement="Chỉ ghi phần sửa của người dùng",
        applies_when="Sửa câu trả lời",
        does_not_apply_when="",
        message_ref="msg_9",
    )
    assert "raw assistant" not in candidate.statement.lower()
    assert candidate.message_ref.startswith("msg_")


def test_correction_form_conflict_defers_to_user_choice(tmp_path: Path) -> None:
    """F4 Regression: Conflict detection in correction form must prompt user rather than auto-applying default choice."""
    from unittest.mock import MagicMock
    import sys
    from aios_habit.workspace_memory_service import _read_jsonl
    from aios_habit.workspace_memory_ui import _render_correction_form

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
    existing = CorrectionLessonCandidate(
        candidate_id="cand_orig",
        statement="Kiểm tra áp suất lốp trước khi xuất phát",
        applies_when="workspace:ws_demo",
        does_not_apply_when="",
        message_ref="msg_orig",
    ).to_decision(actor_label="người dùng", scope="workspace:ws_demo", evidence_refs=("msg_orig",))
    append_memory_decision(existing, path=path)
    assert len(_read_jsonl(path)) == 1

    msg_id = "msg_corr_1"
    corr_key = f"wsc_corr_conflict_{msg_id}"
    state = FakeSessionState()

    mock_st = MagicMock()
    mock_st.session_state = state
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    mock_st.text_area.return_value = "Kiểm tra áp suất lốp xe trước khi khởi hành"
    mock_st.text_input.side_effect = lambda label, key=None: "workspace:ws_demo" if "Áp dụng khi" in label else ""
    # On first render: user clicks "Xác nhận bài học"
    mock_st.button.side_effect = lambda label, key=None: key == f"wsc_corr_confirm_{msg_id}"

    import aios_habit.workspace_memory_ui as mem_ui
    orig_default_path = mem_ui.default_decisions_path
    mem_ui.default_decisions_path = lambda: path
    sys.modules["streamlit"] = mock_st
    try:
        # Step 1: Click confirm -> conflict detected
        _render_correction_form(message_id=msg_id, trace_id="trc_1", workspace_id="ws_demo")
        # MUST have set conflict state in session_state
        assert corr_key in state
        # MUST NOT have written to disk yet! Still exactly 1 row!
        assert len(_read_jsonl(path)) == 1

        # Step 2: Now simulate second render with radio selection "replace" and click "Áp dụng lựa chọn"
        mock_st.radio.return_value = "replace"
        mock_st.button.side_effect = lambda label, key=None: key == f"wsc_corr_apply_{msg_id}"
        _render_correction_form(message_id=msg_id, trace_id="trc_1", workspace_id="ws_demo")

        # Conflict key must be cleared after application
        assert corr_key not in state
        # MUST have written superseded decision to disk
        rows = _read_jsonl(path)
        assert len(rows) == 2
        assert rows[-1]["action"] == "supersede"
        assert rows[-1]["supersedes_decision_id"] == existing.decision_id
    finally:
        mem_ui.default_decisions_path = orig_default_path
        sys.modules.pop("streamlit", None)


def test_correction_form_handles_lease_busy_gracefully(tmp_path: Path) -> None:
    """When LibraryWriterLease is held by another process, correction conflict apply must show busy message."""
    from unittest.mock import MagicMock
    import sys
    from aios_habit.workspace_chat_store import LibraryWriterLease
    from aios_habit.workspace_memory_service import CorrectionLessonCandidate, append_memory_decision, _read_jsonl
    from aios_habit.workspace_memory_ui import _render_correction_form, LEASE_BUSY_MESSAGE

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
    existing = CorrectionLessonCandidate(
        candidate_id="cand_orig",
        statement="Kiểm tra áp suất lốp trước khi xuất phát",
        applies_when="workspace:ws_demo",
        does_not_apply_when="",
        message_ref="msg_orig",
    ).to_decision(actor_label="người dùng", scope="workspace:ws_demo", evidence_refs=("msg_orig",))
    append_memory_decision(existing, path=path)

    msg_id = "msg_corr_lease"
    corr_key = f"wsc_corr_conflict_{msg_id}"
    state = FakeSessionState({
        corr_key: {
            "candidate_id": f"corr_{msg_id}",
            "statement": "Kiểm tra áp suất lốp xe trước khi khởi hành",
            "applies_when": "workspace:ws_demo",
            "does_not_apply_when": "",
            "message_ref": msg_id,
            "trace_ref": "trc_1",
            "scope": "workspace:ws_demo",
        }
    })

    mock_st = MagicMock()
    mock_st.session_state = state
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    mock_st.radio.return_value = "replace"
    mock_st.button.side_effect = lambda label, key=None: key == f"wsc_corr_apply_{msg_id}"

    # Lock the lease
    lease = LibraryWriterLease(path.parent)
    assert lease.acquire(owner="other_process") is True

    import aios_habit.workspace_memory_ui as mem_ui
    orig_default_path = mem_ui.default_decisions_path
    mem_ui.default_decisions_path = lambda: path
    sys.modules["streamlit"] = mock_st
    try:
        _render_correction_form(message_id=msg_id, trace_id="trc_1", workspace_id="ws_demo")
        assert state.wsc_action_error == LEASE_BUSY_MESSAGE
        # No new row written
        assert len(_read_jsonl(path)) == 1
    finally:
        lease.release()
        mem_ui.default_decisions_path = orig_default_path
        sys.modules.pop("streamlit", None)


