"""Tests cho UI phien phong van trong chat + feedback tung goi y (Task 1).

Tat ca test dung AIOS_LOCAL_CASES_DIR -> tmp_path: khong cham vao
local_cases that hay kho tri thuc. Widget nhan doi tuong `st` gia lap.
"""

from __future__ import annotations

import re

import pytest

from aios_habit import chat_interview_ui as ui
from aios_habit.chat_action import ChatActionRequest
from aios_habit.expert_interview_session import (
    start_session,
    unanswered_questions,
)
from aios_habit.golden_question_export import fixture_phenomena
from aios_habit.suggestion_feedback import get_feedback, get_suggestion


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    ui._STORE.clear()
    yield
    ui._STORE.clear()


# ---------------------------------------------------------------------------
# Fake streamlit
# ---------------------------------------------------------------------------


class _FakeColumn:
    def __init__(self, fake):
        self._fake = fake

    def __enter__(self):
        return self._fake

    def __exit__(self, *args):
        return False


class FakeSt:
    def __init__(self, session_state=None):
        self.session_state = {} if session_state is None else session_state
        self.calls = []
        self.text_area_values = {}
        self.text_input_values = {}
        self.multiselect_values = {}
        self.button_presses = set()
        self.rerun_called = False

    def _rec(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    def markdown(self, *a, **k):
        self._rec("markdown", *a, **k)

    def warning(self, *a, **k):
        self._rec("warning", *a, **k)

    def success(self, *a, **k):
        self._rec("success", *a, **k)

    def error(self, *a, **k):
        self._rec("error", *a, **k)

    def info(self, *a, **k):
        self._rec("info", *a, **k)

    def caption(self, *a, **k):
        self._rec("caption", *a, **k)

    def text_area(self, label, key=None, **k):
        self._rec("text_area", label, key=key)
        return self.text_area_values.get(key, "")

    def text_input(self, label, key=None, **k):
        self._rec("text_input", label, key=key)
        return self.text_input_values.get(key, "")

    def multiselect(self, label, options=None, key=None, **k):
        self._rec("multiselect", label, key=key)
        return self.multiselect_values.get(key, [])

    def button(self, label, key=None, **k):
        self._rec("button", label, key=key)
        return key in self.button_presses

    def columns(self, n):
        self._rec("columns", n)
        return [_FakeColumn(self) for _ in range(n)]

    def rerun(self):
        self.rerun_called = True

    def called(self, name):
        return [c for c in self.calls if c[0] == name]

    def button_keys(self):
        return [c[2].get("key") for c in self.called("button")]


def _make_session(n_questions=1):
    ctx = fixture_phenomena("BATCH-UI-TEST")[0]
    session = start_session(ctx, questions_per_session=n_questions)
    ui.store_session(session)
    return session


_FULL_ANSWER = {
    "answer_text": "Đã kiểm tra áp suất khí nén tại van chính, giá trị ổn định 0.6 MPa trong 30 phút.",
    "hypotheses": "Van điều áp bị kẹt\nCảm biến áp suất báo sai",
    "causal_mechanism": "Van kẹt nửa chừng làm áp suất dao động gây dừng máy.",
    "m4_branches": ["Machine"],
    "evidence_to_collect": "Log áp suất 24h\nẢnh van điều áp",
    "confirm_criteria": "Áp suất ổn định sau khi vệ sinh van.",
    "discriminate_notes": "Van kẹt thì áp suất dao động; cảm biến sai thì áp suất thật vẫn ổn định.",
}


def _send_key(fake):
    keys = [k for k in fake.button_keys() if k and k.endswith("_send")]
    assert keys, "missing send button"
    return keys[0]


# ---------------------------------------------------------------------------
# Marker helpers
# ---------------------------------------------------------------------------


def test_marker_roundtrip():
    marker = ui.interview_marker("IS-ABC")
    assert ui.extract_interview_session_id("xxx\n" + marker + "\nzzz") == "IS-ABC"
    assert ui.extract_interview_session_id("no marker") == ""
    smarker = ui.suggestion_marker("SG-1", expert="anh A")
    found = ui.extract_suggestion_markers("a" + smarker + "b")
    assert found == [{"suggestion_id": "SG-1", "expert": "anh A"}]
    stripped = ui.strip_interactive_markers("hello\n" + marker + "\n" + smarker)
    assert stripped == "hello"
    assert "aios_interview_session" not in stripped
    assert "aios_suggestion" not in stripped


def test_session_store_bounded():
    ctx = fixture_phenomena("BATCH-UI-TEST")[0]
    for _ in range(25):
        ui.store_session(start_session(ctx, questions_per_session=1))
    assert len(ui._STORE._sessions) == 20


# ---------------------------------------------------------------------------
# Interview submit logic
# ---------------------------------------------------------------------------


def test_submit_answer_missing_parts_warns():
    session = _make_session()
    qid = session.questions[0].question_id
    ok, message = ui.submit_interview_answer(session, qid, {})
    assert ok is False
    assert "Còn thiếu" in message
    assert len(session.answers) == 0


def test_submit_answer_full_advances():
    session = _make_session(n_questions=2)
    total = len(session.questions)
    qid = session.questions[0].question_id
    ok, message = ui.submit_interview_answer(session, qid, dict(_FULL_ANSWER))
    assert ok is True
    assert message == ""
    assert len(unanswered_questions(session)) == total - 1


def test_submit_last_answer_completes_session():
    session = _make_session(n_questions=1)
    message = ""
    for question in list(session.questions):
        ok, message = ui.submit_interview_answer(
            session, question.question_id, dict(_FULL_ANSWER)
        )
        assert ok is True
    assert "Đã lưu nháp chờ duyệt" in message
    assert ui.get_session(session.session_id) is None


def test_missing_parts_hint_names_cause_and_evidence():
    hint = ui.missing_parts_hint(
        "Đáp án 'answered' mà thiếu nhân quả/bằng chứng thì bị từ chối "
        "(thiếu: hypotheses (giả thuyết nguyên nhân); evidence_to_collect (bằng chứng cần thu thập))."
    )
    assert "nguyên nhân" in hint
    assert "bằng chứng" in hint


# ---------------------------------------------------------------------------
# Interview widget rendering
# ---------------------------------------------------------------------------


def test_render_interview_widget_shows_question_and_fields():
    session = _make_session()
    fake = FakeSt()
    ui.render_interview_widget(fake, session.session_id)
    md_texts = [c[1][0] for c in fake.called("markdown")]
    assert any("Câu 1/" in t for t in md_texts)
    assert len(fake.called("text_area")) >= 5
    assert len(fake.called("multiselect")) == 1
    assert len(fake.called("button")) == 1


def test_render_interview_widget_submit_missing_shows_warning():
    session = _make_session()
    shared = {}
    fake = FakeSt(session_state=shared)
    ui.render_interview_widget(fake, session.session_id)
    send_key = _send_key(fake)
    fake2 = FakeSt(session_state=shared)
    fake2.button_presses.add(send_key)
    ui.render_interview_widget(fake2, session.session_id)
    warnings = [c[1][0] for c in fake2.called("warning")]
    assert any("Còn thiếu" in w for w in warnings)
    assert len(session.answers) == 0
    assert fake2.rerun_called is False


def test_render_interview_widget_submit_full_advances_and_reruns():
    session = _make_session(n_questions=2)
    fake = FakeSt()
    ui.render_interview_widget(fake, session.session_id)
    send_key = _send_key(fake)
    base = send_key[: -len("_send")]
    for payload_key, _label, _kind in ui.ANSWER_FIELDS:
        field_key = base + "_" + payload_key
        value = _FULL_ANSWER[payload_key]
        if isinstance(value, list):
            fake.multiselect_values[field_key] = value
        else:
            fake.text_area_values[field_key] = value
    disc_key = base + "_discriminate_notes"
    if disc_key in [c[2].get("key") for c in fake.called("text_area")]:
        fake.text_area_values[disc_key] = _FULL_ANSWER["discriminate_notes"]
    fake.button_presses.add(send_key)
    ui.render_interview_widget(fake, session.session_id)
    assert len(session.answers) == 1
    assert fake.rerun_called is True


def test_render_interview_widget_expired_session():
    fake = FakeSt()
    ui.render_interview_widget(fake, "IS-KHONG-TON-TAI")
    infos = [c[1][0] for c in fake.called("info")]
    assert any("hết hạn" in t for t in infos)


# ---------------------------------------------------------------------------
# Suggestion cards + feedback widget
# ---------------------------------------------------------------------------


def test_emit_suggestion_card_logs_once_and_embeds_marker():
    card = ui.emit_suggestion_card("SG-C1", "Gợi ý 1", "Kiểm tra áp suất khí nén")
    assert get_suggestion("SG-C1")["content"] == "Kiểm tra áp suất khí nén"
    assert ui.extract_suggestion_markers(card) == [
        {"suggestion_id": "SG-C1", "expert": ""}
    ]
    # Idempotent: second emit does not duplicate the log.
    ui.emit_suggestion_card("SG-C1", "Gợi ý 1", "Nội dung khác")
    assert get_suggestion("SG-C1")["content"] == "Kiểm tra áp suất khí nén"


def test_emit_suggestion_card_prepends_lesson_note():
    ui.emit_suggestion_card("SG-OLD", "Gợi ý cũ", "Kiểm tra van điều áp khí nén")
    ok, _ = ui.save_suggestion_feedback(
        "SG-OLD", "chuyen_gia", "sai",
        "Bỏ qua van điều áp", "Van điều áp bị kẹt", "Kiểm tra van điều áp trước",
    )
    assert ok is True
    card = ui.emit_suggestion_card("SG-NEW", "Gợi ý mới", "Nên kiểm tra van điều áp khí nén")
    assert card.startswith("💡 Lưu ý:")
    assert "từng bị chê vì" in card


def test_save_feedback_dung_ok():
    ui.emit_suggestion_card("SG-D", "Gợi ý", "Nạp tài liệu nguồn vào sổ tri thức")
    ok, message = ui.save_suggestion_feedback("SG-D", "chuyen_gia", "dung", "", "", "")
    assert ok is True
    assert "đúng" in message
    assert get_feedback("SG-D")


def test_save_feedback_sai_missing_fields_fails():
    ui.emit_suggestion_card("SG-E", "Gợi ý", "Thay cảm biến mới")
    ok, message = ui.save_suggestion_feedback("SG-E", "chuyen_gia", "sai", "", "", "")
    assert ok is False
    assert message.startswith("⚠️")
    assert get_feedback("SG-E") == []


def test_save_feedback_sai_creates_lesson_and_metric_event():
    from aios_habit.self_improvement import LessonStore, improvement_overview

    ui.emit_suggestion_card("SG-F", "Gợi ý", "Tăng áp suất khí nén lên 0.8 MPa")
    ok, _ = ui.save_suggestion_feedback(
        "SG-F", "chuyen_gia", "mot_phan",
        "Áp suất cao gây rò rỉ", "Áp suất chuẩn là 0.6 MPa", "Giữ 0.6 MPa và kiểm tra rò rỉ",
    )
    assert ok is True
    assert len(LessonStore().all()) == 1
    overview = improvement_overview()
    assert overview["so_bai_hoc"] == 1


def test_render_suggestion_widget_buttons_then_fields_then_save():
    ui.emit_suggestion_card("SG-W1", "Gợi ý", "Vệ sinh van điều áp")
    shared = {}
    fake = FakeSt(session_state=shared)
    ui.render_suggestion_widget(fake, "SG-W1")
    keys = fake.button_keys()
    assert any(k.endswith("_dung") for k in keys)
    assert any(k.endswith("_mot_phan") for k in keys)
    assert any(k.endswith("_sai") for k in keys)

    # Press "Sai" -> the 3 mandatory fields appear inline.
    sai_key = next(k for k in keys if k.endswith("_sai"))
    fake2 = FakeSt(session_state=shared)
    fake2.button_presses.add(sai_key)
    ui.render_suggestion_widget(fake2, "SG-W1")
    labels = [c[1][0] for c in fake2.called("text_input")]
    assert labels == ["Lý do", "Nguyên nhân thật", "Nắn lại thế nào"]
    save_key = next(k for k in fake2.button_keys() if k.endswith("_save"))

    # Save with empty fields -> warning, nothing stored.
    fake3 = FakeSt(session_state=shared)
    fake3.button_presses.add(save_key)
    ui.render_suggestion_widget(fake3, "SG-W1")
    assert any(c[1][0].startswith("⚠️") for c in fake3.called("warning"))
    assert get_feedback("SG-W1") == []

    # Fill all 3 fields -> saved.
    base = save_key[: -len("_save")]
    fake4 = FakeSt(session_state=shared)
    fake4.text_input_values[base + "_ly_do"] = "Chưa đủ căn cứ"
    fake4.text_input_values[base + "_nn"] = "Van điều áp kẹt"
    fake4.text_input_values[base + "_sua"] = "Vệ sinh van trước khi thay"
    fake4.button_presses.add(save_key)
    ui.render_suggestion_widget(fake4, "SG-W1")
    assert any("Đã ghi nhận" in c[1][0] for c in fake4.called("success"))
    assert get_feedback("SG-W1")


def test_render_suggestion_widget_dung_saves_immediately():
    ui.emit_suggestion_card("SG-W2", "Gợi ý", "Nạp tài liệu nguồn")
    shared = {}
    fake = FakeSt(session_state=shared)
    ui.render_suggestion_widget(fake, "SG-W2")
    dung_key = next(k for k in fake.button_keys() if k.endswith("_dung"))
    fake2 = FakeSt(session_state=shared)
    fake2.button_presses.add(dung_key)
    ui.render_suggestion_widget(fake2, "SG-W2")
    assert get_feedback("SG-W2")
    # Already rated -> caption instead of buttons on the next render.
    fake3 = FakeSt(session_state=shared)
    ui.render_suggestion_widget(fake3, "SG-W2")
    assert fake3.called("caption")


def test_repetition_metric_line():
    assert "Chưa có dữ liệu" in ui.repetition_metric_line()
    ui.emit_suggestion_card("SG-M", "Gợi ý", "Kiểm tra van điều áp khí nén")
    ui.save_suggestion_feedback(
        "SG-M", "chuyen_gia", "sai", "lý do", "nguyên nhân thật", "nắn lại"
    )
    line = ui.repetition_metric_line()
    assert "Tỉ lệ lặp lại lỗi" in line


# ---------------------------------------------------------------------------
# Chat action wiring
# ---------------------------------------------------------------------------


def test_interview_chat_action_matches():
    from aios_habit import chat_action

    chat_action.load_builtin_actions()
    req = ChatActionRequest(question="mở phiên phỏng vấn F000")
    names = [a.name for a in chat_action.registered_actions() if a.matches(req)]
    assert "phien_phong_van_chat" in names
    assert "phong_van_chuyen_gia" not in names


def test_interview_chat_action_without_code_asks_for_code():
    from aios_habit import chat_action

    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(ChatActionRequest(question="mở phiên phỏng vấn"))
    assert outcome is not None
    assert outcome.action == "phien_phong_van_chat"
    assert "Cho mình mã lỗi" in chat_action.render_outcome(outcome)


def test_next_actions_appends_suggestion_cards_but_keeps_table(monkeypatch):
    from aios_habit import chat_action
    from aios_habit.chat_action import BLOCK_MARKDOWN, BLOCK_TABLE

    chat_action.load_builtin_actions()
    req = ChatActionRequest(
        question="Tiếp theo nên làm gì?", notebook_id="NB-123", workspace_id="default"
    )
    from aios_habit import chat_action_next_actions as _na
    from aios_habit import daily_next_actions

    monkeypatch.setattr(
        daily_next_actions,
        "suggest_next_actions",
        lambda ws, nb: ["Nạp tài liệu nguồn."],
    )
    outcome = _na._handler(req)
    assert outcome is not None
    tables = [b for b in outcome.blocks if b.kind == BLOCK_TABLE]
    assert len(tables) == 1
    assert tables[0].headers == ("#", "Việc nên làm tiếp")
    md_blocks = [b for b in outcome.blocks if b.kind == BLOCK_MARKDOWN]
    assert any("aios_suggestion" in b.text for b in md_blocks)
    markers = ui.extract_suggestion_markers(md_blocks[-1].text)
    assert len(markers) == 1
    assert markers[0]["suggestion_id"].startswith("SG-NEXT-")


def test_suggestion_review_appends_repetition_metric():
    from aios_habit import chat_action
    from aios_habit import chat_action_suggestion_review as _sr

    chat_action.load_builtin_actions()
    outcome = _sr._handler(ChatActionRequest(question="báo cáo cải thiện gợi ý"))
    assert outcome is not None
    rendered = chat_action.render_outcome(outcome)
    assert "cải thiện gợi ý" in rendered
