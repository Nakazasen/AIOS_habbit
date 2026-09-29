"""Tests for the TOOL-3 chat action scoring the quality of the latest answer."""

import pytest

from aios_habit import chat_action
from aios_habit import workspace_chat_store as store
from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_answer_quality import ACTION_NAME
from aios_habit.evidence_trace import EvidenceNode, create_evidence_trace
from aios_habit.feature_flags import reset_feature_flags
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_store import save_evidence_trace, save_message

QUESTION = "Quy trình đăng ký lịch sử sản xuất gồm những bước chính nào?"
ANSWER = (
    "Quy trình đăng ký lịch sử sản xuất gồm 4 bước chính: tiếp nhận, kiểm tra, "
    "xác nhận và lưu hồ sơ."
)


@pytest.fixture(autouse=True)
def _clean_state():
    reset_feature_flags()
    chat_action.reset_actions()
    yield
    reset_feature_flags()
    chat_action.reset_actions()


@pytest.fixture()
def _isolated_store(tmp_path, monkeypatch):
    """Point the workspace chat store at a temp dir (same pattern as TOOL-2 tests)."""
    chat_dir = tmp_path / "workspace_chat"
    chat_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", chat_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", chat_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "COLLECTIONS_FILE", chat_dir / "collections.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", chat_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", chat_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", chat_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", chat_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(
        store, "SOURCE_SELECTIONS_FILE", chat_dir / "conversation_source_selections.jsonl"
    )
    monkeypatch.setattr(store, "TRACES_FILE", chat_dir / "traces.jsonl")
    return chat_dir


def _node(node_id: str, snippet: str, source_id: str, title: str) -> EvidenceNode:
    return EvidenceNode(
        id=node_id, node_type="evidence", title=title, snippet=snippet, source_id=source_id
    )


def _seed_pair(
    conversation_id: str = "C1",
    *,
    suffix: str = "1",
    question: str = QUESTION,
    answer: str = ANSWER,
    nodes: list | None = None,
    with_trace: bool = True,
) -> None:
    save_message(
        ChatMessage(
            id=f"MSG-U-{suffix}", conversation_id=conversation_id, role="user", content=question
        )
    )
    trace_id = ""
    if with_trace:
        trace = create_evidence_trace(
            conversation_id=conversation_id,
            user_message_id=f"MSG-U-{suffix}",
            assistant_message_id=f"MSG-A-{suffix}",
            query=question,
            answer_text=answer,
            nodes=list(nodes or []),
        )
        save_evidence_trace(trace)
        trace_id = trace.trace_id
    save_message(
        ChatMessage(
            id=f"MSG-A-{suffix}",
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            trace_id=trace_id,
        )
    )


def _ask(question: str = "Đánh giá chất lượng trả lời", conversation_id: str = "C1"):
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(
        ChatActionRequest(question=question, conversation_id=conversation_id)
    )
    assert outcome is not None
    return outcome


def test_builtin_registry_includes_answer_quality_module():
    assert "aios_habit.chat_action_answer_quality" in chat_action.BUILTIN_ACTION_MODULES
    chat_action.load_builtin_actions()
    assert ACTION_NAME in [action.name for action in chat_action.registered_actions()]


@pytest.mark.parametrize(
    "question",
    (
        "Đánh giá chất lượng trả lời",
        "danh gia chat luong tra loi",
        "Chấm điểm câu trả lời giúp tôi",
    ),
)
def test_action_matches_accented_and_unaccented_questions(_isolated_store, question):
    outcome = _ask(question)
    assert outcome.action == ACTION_NAME


def test_unrelated_question_is_not_handled(_isolated_store):
    chat_action.load_builtin_actions()
    assert chat_action.dispatch(ChatActionRequest(question="Tóm tắt tài liệu này giúp tôi")) is None


def test_without_conversation_returns_guidance(_isolated_store):
    outcome = _ask(conversation_id="")
    rendered = chat_action.render_outcome(outcome)
    assert "Chưa xác định được hội thoại" in rendered


def test_without_answer_returns_guidance(_isolated_store):
    save_message(
        ChatMessage(id="MSG-U-1", conversation_id="C1", role="user", content=QUESTION)
    )
    rendered = chat_action.render_outcome(_ask())
    assert "chưa có câu trả lời nào để đánh giá" in rendered


def test_scores_latest_answer_with_evidence_and_retrieval_check(_isolated_store):
    _seed_pair(
        suffix="1",
        question="Câu hỏi cũ?",
        answer="Câu trả lời cũ.",
        nodes=[_node("N0", "Đoạn bằng chứng cũ.", "SRC-0", "Nguồn cũ")],
    )
    _seed_pair(
        suffix="2",
        nodes=[
            _node(
                "N1",
                "Quy trình đăng ký lịch sử sản xuất gồm các bước chính: tiếp nhận, kiểm tra, xác nhận.",
                "SRC-1",
                "Quy trình đăng ký",
            ),
            _node(
                "N2",
                "Bước lưu hồ sơ gồm xác nhận thông tin và lưu hồ sơ sản xuất.",
                "SRC-2",
                "Lưu hồ sơ",
            ),
            _node(
                "N3",
                "Khi tiếp nhận hồ sơ, kiểm tra lịch sử sản xuất trước khi xác nhận.",
                "SRC-3",
                "Kiểm tra hồ sơ",
            ),
        ],
    )
    rendered = chat_action.render_outcome(_ask())

    # Latest answer (pair 2) is scored, not the older one.
    assert "4 bước chính" in rendered
    assert "Câu trả lời cũ" not in rendered

    # Tier 1 — rag_evaluator on the trace evidence.
    assert "Độ phủ bằng chứng" in rendered and "| 100% |" in rendered
    assert "Tỷ lệ bằng chứng chỉ metadata" in rendered

    # Tier 2 — mom_benchmark rubric + weighted total.
    assert "Truy vết nguồn" in rendered and "| 5/5 |" in rendered
    assert "tổng có trọng số" in rendered and "/100" in rendered

    # Tier 3 — rag_benchmark retrieval self-check over the cited evidence.
    assert "Tự kiểm tra truy xuất" in rendered
    assert "Số đoạn bằng chứng kiểm tra" in rendered and "| 3 |" in rendered
    assert "Tìm lại đoạn bằng chứng" in rendered and "| Đạt |" in rendered


def test_answer_without_trace_degrades_gracefully(_isolated_store):
    _seed_pair(with_trace=False)
    rendered = chat_action.render_outcome(_ask())
    assert "Không tìm thấy dấu vết bằng chứng" in rendered
    assert "Tự kiểm tra truy xuất" not in rendered
    assert "Độ phủ bằng chứng" in rendered and "| 0% |" in rendered
    assert "tổng có trọng số" in rendered


def test_store_error_returns_guidance(_isolated_store, monkeypatch):
    def boom(conversation_id):
        raise RuntimeError("store down")

    monkeypatch.setattr(store, "load_messages", boom)
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(
        ChatActionRequest(question="Đánh giá chất lượng trả lời", conversation_id="C1")
    )
    assert outcome is not None and outcome.action == ACTION_NAME
    assert "Chưa đọc được nội dung hội thoại" in chat_action.render_outcome(outcome)


def test_dispatch_is_read_only(_isolated_store):
    _seed_pair(nodes=[_node("N1", "Đoạn bằng chứng.", "SRC-1", "Nguồn 1")])
    chat_action.load_builtin_actions()
    before = {path.name: path.read_bytes() for path in _isolated_store.iterdir()}
    chat_action.dispatch(ChatActionRequest(question="đánh giá chất lượng trả lời", conversation_id="C1"))
    after = {path.name: path.read_bytes() for path in _isolated_store.iterdir()}
    assert before == after


def test_handle_chat_text_saves_answer_quality_bubble(_isolated_store):
    _seed_pair(nodes=[_node("N1", "Đoạn bằng chứng.", "SRC-1", "Nguồn 1")])
    chat_action.load_builtin_actions()
    saved = []
    handled = chat_action.handle_chat_text(
        "Đánh giá chất lượng trả lời",
        conversation_id="C1",
        save_user=lambda content: saved.append(("user", content)),
        save_assistant=lambda content: saved.append(("assistant", content)),
    )
    assert handled is True
    assert saved[0] == ("user", "Đánh giá chất lượng trả lời")
    assert "Đánh giá chất lượng trả lời" in saved[1][1]
    assert "Độ phủ bằng chứng" in saved[1][1]
