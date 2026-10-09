"""Tests for the TOOL-4 chat action previewing the expert interview flow."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from aios_habit import chat_action
from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_expert_interview import ACTION_NAME
from aios_habit.expert_identity import VerifiedPrincipal
from aios_habit.expert_interview_service import ExpertInterviewService
from aios_habit.feature_flags import reset_feature_flags
from aios_habit.knowledge_coverage import (
    GAP_STATUS_ACCEPTED,
    GAP_TYPE_MISSING_CONDITION,
    GAP_TYPE_MISSING_THRESHOLD,
    KnowledgeGapCandidate,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository

QUESTION = "Phỏng vấn chuyên gia về ngưỡng bước sóng quang học"
ANSWER = "Bước sóng được duy trì ở mức chuẩn ổn định của xưởng."


@pytest.fixture(autouse=True)
def _clean_state():
    reset_feature_flags()
    chat_action.reset_actions()
    yield
    reset_feature_flags()
    chat_action.reset_actions()


def _gap(gap_id: str, title: str, gap_type: str, description: str = "Mô tả chi tiết") -> KnowledgeGapCandidate:
    return KnowledgeGapCandidate(
        gap_id=gap_id,
        collection_id="lsu_docs",
        scope="lsu_optical_assembly",
        title=title,
        description=description,
        gap_type=gap_type,
        evidence_refs=("DOC-OPT-01#p4",),
        status=GAP_STATUS_ACCEPTED,
        priority="high",
    )


def _seed_store(tmp_path: Path, *, with_session: bool = True, with_second_topic: bool = False) -> Path:
    db_path = tmp_path / "workspace_cases.sqlite"
    store = WorkspaceCaseRepository(db_path)
    store.initialize()
    first = _gap("GAP-TOOL4-1", "Thiếu ngưỡng bước sóng quang học", GAP_TYPE_MISSING_THRESHOLD)
    store.save_gap_candidate(first, "IDEMP-GAP-TOOL4-1", "tester")
    if with_second_topic:
        second = _gap(
            "GAP-TOOL4-2",
            "Quy trình hàn chì thiếu ngoại lệ",
            GAP_TYPE_MISSING_CONDITION,
            description="Ngoại lệ nhiệt độ khi hàn chì",
        )
        store.save_gap_candidate(second, "IDEMP-GAP-TOOL4-2", "tester")
    if with_session:
        service = ExpertInterviewService(store=store)
        plan = service.create_interview_plan(gap_id=first.gap_id)
        principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
        session = service.start_interview_session(
            plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-TOOL4"
        )
        service.submit_interview_turn(
            session_id=session.session_id,
            answer_text=ANSWER,
            principal=principal,
            idempotency_key="IDEMP-TURN-TOOL4-1",
        )
        if with_second_topic:
            second_plan = service.create_interview_plan(gap_id="GAP-TOOL4-2")
            service.start_interview_session(
                second_plan.plan_id,
                VerifiedPrincipal("expert_solder", "local_test", "Chuyên gia Hàn"),
                "expert_solder",
                "IDEMP-START-TOOL4-2",
            )
    return db_path


def _ask(question: str, db_path: Path):
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(
        ChatActionRequest(question=question, context={"case_db_path": str(db_path)})
    )
    assert outcome is not None
    return outcome


def _render(outcome) -> str:
    return chat_action.render_outcome(outcome)


def _dump_logical(db_path: Path) -> list:
    # Logical content snapshot: immune to WAL storage churn (checkpoint page
    # moves change file bytes without changing any row).
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return [
            (table, sorted((tuple(r) for r in con.execute(f'SELECT * FROM "{table}"')), key=repr))
            for table in tables
        ]
    finally:
        con.close()


def test_builtin_registry_includes_interview_module():
    assert "aios_habit.chat_action_expert_interview" in chat_action.BUILTIN_ACTION_MODULES
    chat_action.load_builtin_actions()
    assert ACTION_NAME in [action.name for action in chat_action.registered_actions()]


@pytest.mark.parametrize(
    "question",
    (
        QUESTION,
        "phong van chuyen gia ve nguong buoc song quang hoc",
        "Chạy phỏng vấn chuyên gia về ngưỡng bước sóng",
    ),
)
def test_action_matches_accented_and_unaccented_questions(tmp_path, question):
    outcome = _ask(question, _seed_store(tmp_path))
    assert outcome.action == ACTION_NAME


def test_unrelated_question_is_not_handled(tmp_path):
    chat_action.load_builtin_actions()
    assert (
        chat_action.dispatch(
            ChatActionRequest(
                question="Tóm tắt tài liệu này giúp tôi",
                context={"case_db_path": str(_seed_store(tmp_path))},
            )
        )
        is None
    )


def test_missing_store_returns_guidance_and_creates_nothing(tmp_path):
    db_path = tmp_path / "missing.sqlite"
    outcome = _ask(QUESTION, db_path)
    rendered = _render(outcome)
    assert "chưa có sổ hồ sơ phỏng vấn" in rendered
    assert not db_path.exists()


def test_topic_without_match_returns_guidance(tmp_path):
    outcome = _ask("Phỏng vấn chuyên gia về quy trình mạ kẽm", _seed_store(tmp_path))
    rendered = _render(outcome)
    assert "Chưa tìm thấy chủ đề" in rendered
    assert "quy trình mạ kẽm" in rendered


def test_gap_without_session_shows_seed_questions(tmp_path):
    outcome = _ask(QUESTION, _seed_store(tmp_path, with_session=False))
    rendered = _render(outcome)
    assert "Câu hỏi mồi" in rendered
    assert "chưa mở phiên" in rendered
    assert "Thiếu ngưỡng bước sóng quang học" in rendered


def test_session_preview_shows_turns_and_next_question(tmp_path):
    outcome = _ask(QUESTION, _seed_store(tmp_path))
    rendered = _render(outcome)
    assert "Diễn biến phiên gần nhất" in rendered
    assert "expert_opt_lead" in rendered
    assert ANSWER[:30] in rendered
    assert "Câu hỏi tiếp theo" in rendered
    assert "ngưỡng kỹ thuật" in rendered


def test_topic_filter_excludes_other_sessions(tmp_path):
    db_path = _seed_store(tmp_path, with_second_topic=True)
    rendered = _render(_ask("Phỏng vấn chuyên gia về hàn chì", db_path))
    assert "Quy trình hàn chì thiếu ngoại lệ" in rendered
    assert "expert_solder" in rendered
    assert "Thiếu ngưỡng bước sóng quang học" not in rendered


def test_dispatch_is_read_only(tmp_path):
    # TEST-SUITE-HYGIENE-HOME: compare logical rows, not raw file bytes. WAL
    # storage churn (checkpoint page moves during import) changes the SHA
    # without changing any row — diagnosed 2026-10-09: 28/28 tables identical.
    db_path = _seed_store(tmp_path)
    before = _dump_logical(db_path)
    before_files = {path.name for path in tmp_path.iterdir()}
    _ask(QUESTION, db_path)
    assert _dump_logical(db_path) == before
    assert {path.name for path in tmp_path.iterdir()} == before_files


def test_handle_chat_text_saves_interview_bubble(tmp_path):
    db_path = _seed_store(tmp_path)
    saved: list[tuple[str, str]] = []
    handled = chat_action.handle_chat_text(
        QUESTION,
        conversation_id="C1",
        context={"case_db_path": str(db_path)},
        save_user=lambda content: saved.append(("user", content)),
        save_assistant=lambda content: saved.append(("assistant", content)),
    )
    assert handled is True
    assert [role for role, _ in saved] == ["user", "assistant"]
    assert "Phỏng vấn chuyên gia" in saved[1][1]
    assert "Phiên" in saved[1][1]
