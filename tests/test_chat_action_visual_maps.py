"""Tests for the TOOL-5 chat actions drawing the visual knowledge maps."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from aios_habit import chat_action
from aios_habit import chat_action_visual_maps as visual
from aios_habit.chat_action import ChatActionRequest
from aios_habit.feature_flags import reset_feature_flags


@pytest.fixture(autouse=True)
def _clean_state():
    reset_feature_flags()
    chat_action.reset_actions()
    yield
    reset_feature_flags()
    chat_action.reset_actions()


# --------------------------------------------------------------------------
# Mock store records (duck-typed, same shape as the local JSONL stores)
# --------------------------------------------------------------------------


def _notebook(notebook_id: str, workspace: str, name: str):
    return SimpleNamespace(
        notebook_id=notebook_id, workspace_id=workspace, name=name, description=""
    )


def _source(source_id: str, notebook_id: str, title: str):
    return SimpleNamespace(
        source_id=source_id, notebook_id=notebook_id, title=title, description=""
    )


def _case(case_id: str, title: str, workspace: str = "ws", **extra):
    base = dict(
        case_id=case_id,
        title=title,
        workspace_id=workspace,
        priority="normal",
        current_situation="",
        hypotheses=[],
        next_actions=[],
        decisions=[],
        linked_notebook_ids=[],
        source_origin="unknown",
        verification_status="unknown",
        status="open",
    )
    base.update(extra)
    return SimpleNamespace(**base)


def _evidence(
    evidence_id: str,
    case_id: str,
    title: str,
    source_type: str = "note",
    **extra,
):
    base = dict(
        evidence_id=evidence_id,
        case_id=case_id,
        title=title,
        source_type=source_type,
        source_path="",
        extracted_text="",
        structured_summary="",
        confidence="low",
        source_origin="unknown",
        verification_status="unknown",
        review_status="raw",
        privacy_level="local_only",
    )
    base.update(extra)
    return SimpleNamespace(**base)


def _lesson(learning_id: str, case_id: str, lesson: str):
    return SimpleNamespace(
        learning_id=learning_id,
        case_id=case_id,
        reusable_lesson=lesson,
        true_cause="",
        actions_taken="",
        check_first_next_time="",
        confidence="draft",
    )


def _dispatch(question: str, **kwargs):
    chat_action.load_builtin_actions()
    return chat_action.dispatch(ChatActionRequest(question=question, **kwargs))


def _render(outcome) -> str:
    assert outcome is not None
    return chat_action.render_outcome(outcome)


# --------------------------------------------------------------------------
# Registration and matching
# --------------------------------------------------------------------------


def test_builtin_registry_includes_visual_maps_module():
    assert "aios_habit.chat_action_visual_maps" in chat_action.BUILTIN_ACTION_MODULES
    chat_action.load_builtin_actions()
    names = [action.name for action in chat_action.registered_actions()]
    assert visual.ACTION_TRI_THUC in names
    assert visual.ACTION_HO_SO in names
    assert visual.ACTION_BANG_CHUNG in names


def test_unrelated_question_is_not_handled():
    chat_action.load_builtin_actions()
    assert (
        chat_action.dispatch(
            ChatActionRequest(question="Tóm tắt tài liệu này giúp tôi")
        )
        is None
    )


@pytest.mark.parametrize(
    "question",
    (
        "Vẽ bản đồ tri thức",
        "vẽ bản đồ tri thức về hệ thống làm mát",
        "ve ban do tri thuc",
        "Sơ đồ tri thức của tôi",
    ),
)
def test_tri_thuc_matches_accented_and_unaccented(question, monkeypatch):
    monkeypatch.setattr(
        visual,
        "_load_graph_inputs",
        lambda: ([_notebook("NB-1", "ws", "Sổ A")], [], [_case("CASE-1", "Hệ thống làm mát")], [], []),
    )
    outcome = _dispatch(question)
    assert outcome is not None
    assert outcome.action == visual.ACTION_TRI_THUC


@pytest.mark.parametrize(
    "question",
    ("Vẽ bản đồ hồ sơ", "ve ban do ho so CASE-1", "Sơ đồ case CASE-1"),
)
def test_ho_so_matches_accented_and_unaccented(question, monkeypatch):
    monkeypatch.setattr(
        visual,
        "_load_case_store",
        lambda: ([_case("CASE-1", "Hệ thống làm mát")], []),
    )
    monkeypatch.setattr(visual, "_load_case_lessons", lambda case_id: [])
    outcome = _dispatch(question)
    assert outcome is not None
    assert outcome.action == visual.ACTION_HO_SO


# --------------------------------------------------------------------------
# Knowledge map action (worklens_semantic_map + knowledge_map_html zones)
# --------------------------------------------------------------------------


def _knowledge_map_fixture():
    notebooks = [_notebook("NB-1", "ws", "Sổ vận hành")]
    sources = [_source("SRC-1", "NB-1", "SOP vận hành")]
    cases = [
        _case("CASE-1", "Hệ thống làm mát", linked_notebook_ids=["NB-1"]),
        _case("CASE-2", "Máy nén khí"),
    ]
    evidence = [
        _evidence("EV-1", "CASE-1", "Quạt làm mát hỏng", source_type="note"),
        _evidence("EV-2", "CASE-2", "Rò dầu van xả", source_type="log"),
    ]
    return notebooks, sources, cases, evidence, []


def test_tri_thuc_renders_mermaid_zones_and_relations(monkeypatch):
    monkeypatch.setattr(visual, "_load_graph_inputs", _knowledge_map_fixture)
    rendered = _render(_dispatch("vẽ bản đồ tri thức"))

    assert "```mermaid" in rendered
    assert "flowchart LR" in rendered
    # Zone titles come from knowledge_map_html.ZONE_DEFS.
    assert "| Case trung tâm |" in rendered
    assert "| Bằng chứng |" in rendered
    # Relation labels come from knowledge_map_html.RELATION_LABELS.
    assert "có bằng chứng" in rendered
    # Source notebook nodes are part of the map.
    assert "Sổ vận hành" in rendered
    assert "chỉ đọc" in rendered


def test_tri_thuc_filters_by_topic_and_neighbors(monkeypatch):
    monkeypatch.setattr(visual, "_load_graph_inputs", _knowledge_map_fixture)
    rendered = _render(_dispatch("vẽ bản đồ tri thức về máy nén"))

    assert "Máy nén khí" in rendered
    assert "Rò dầu van xả" in rendered
    assert "Quạt làm mát hỏng" not in rendered
    assert "Đã ẩn" in rendered


def test_tri_thuc_unknown_topic_guides_without_map(monkeypatch):
    monkeypatch.setattr(visual, "_load_graph_inputs", _knowledge_map_fixture)
    rendered = _render(_dispatch("vẽ bản đồ tri thức về máy phát điện"))

    assert "Chưa tìm thấy" in rendered
    assert "máy phát điện" in rendered
    assert "```mermaid" not in rendered


def test_tri_thuc_empty_store_guides(monkeypatch):
    monkeypatch.setattr(visual, "_load_graph_inputs", lambda: ([], [], [], [], []))
    rendered = _render(_dispatch("vẽ bản đồ tri thức"))
    assert "Chưa có dữ liệu" in rendered
    assert "```mermaid" not in rendered


def test_tri_thuc_store_error_guides(monkeypatch):
    def _boom():
        raise OSError("store hỏng")

    monkeypatch.setattr(visual, "_load_graph_inputs", _boom)
    rendered = _render(_dispatch("vẽ bản đồ tri thức"))
    assert "Chưa đọc được dữ liệu cục bộ" in rendered


def test_tri_thuc_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(visual, "_load_graph_inputs", lambda: ([], [], [], [], []))
    _render(_dispatch("vẽ bản đồ tri thức"))
    assert list(tmp_path.rglob("*")) == []


# --------------------------------------------------------------------------
# Case map action (visual_knowledge_map)
# --------------------------------------------------------------------------


def test_ho_so_lists_cases_when_no_topic(monkeypatch):
    cases = [_case("CASE-1", "Hệ thống làm mát"), _case("CASE-2", "Máy nén khí")]
    monkeypatch.setattr(visual, "_load_case_store", lambda: (cases, []))
    rendered = _render(_dispatch("vẽ bản đồ hồ sơ"))

    assert "Bạn muốn vẽ bản đồ hồ sơ nào?" in rendered
    assert "Hệ thống làm mát" in rendered
    assert "Máy nén khí" in rendered


def test_ho_so_renders_case_graph_metrics_and_nodes(monkeypatch):
    case = _case("CASE-1", "Hệ thống làm mát")
    evidence = [
        _evidence("EV-1", "CASE-1", "Quạt làm mát hỏng", source_type="note"),
        _evidence(
            "ANS-1",
            "CASE-1",
            "Trả lời mạnh: thay quạt",
            source_type="ide_handoff_strong_answer",
            structured_summary='{"citation_ids": ["EV-1"]}',
        ),
    ]
    monkeypatch.setattr(visual, "_load_case_store", lambda: ([case], evidence))
    monkeypatch.setattr(
        visual, "_load_case_lessons", lambda case_id: [_lesson("L-1", case_id, "Kiểm tra quạt định kỳ")]
    )
    rendered = _render(_dispatch("vẽ bản đồ hồ sơ CASE-1"))

    assert "```mermaid" in rendered
    assert "graph TD" in rendered
    assert "Quạt làm mát hỏng" in rendered
    assert "Trả lời mạnh: thay quạt" in rendered
    assert "Bài học" in rendered
    assert "Độ phủ trích dẫn" in rendered
    assert "| 2 |" in rendered


def test_ho_so_unknown_case_guides(monkeypatch):
    monkeypatch.setattr(
        visual, "_load_case_store", lambda: ([_case("CASE-1", "Hệ thống làm mát")], [])
    )
    rendered = _render(_dispatch("vẽ bản đồ hồ sơ CASE-9"))
    assert "Chưa tìm thấy hồ sơ" in rendered
    assert "```mermaid" not in rendered


def test_ho_so_empty_store_guides(monkeypatch):
    monkeypatch.setattr(visual, "_load_case_store", lambda: ([], []))
    rendered = _render(_dispatch("vẽ bản đồ hồ sơ"))
    assert "chưa có hồ sơ nào" in rendered


# --------------------------------------------------------------------------
# Evidence graph action (evidence_graph_viewer)
# --------------------------------------------------------------------------


def _trace_dict(trace_id: str = "TRC-1", conversation_id: str = "CONV-1"):
    return {
        "trace_id": trace_id,
        "conversation_id": conversation_id,
        "query": "Quy trình hàn thế nào?",
        "answer_text": "Theo SOP hàn.",
        "nodes": [
            {"id": "q-1", "node_type": "question", "title": "Câu hỏi: Quy trình hàn?"},
            {"id": "a-1", "node_type": "answer", "title": "Câu trả lời tổng hợp"},
            {"id": "s-1", "node_type": "source", "title": "SOP-han.pdf", "source_id": "SRC-1"},
            {"id": "c-1", "node_type": "citation", "title": "Trích dẫn 1", "citation_id": "CIT-1"},
        ],
        "edges": [
            {"edge_id": "e1", "source_id": "q-1", "target_id": "a-1", "relation_type": "answers"},
            {"edge_id": "e2", "source_id": "a-1", "target_id": "s-1", "relation_type": "cites"},
            {"edge_id": "e3", "source_id": "s-1", "target_id": "c-1", "relation_type": "supports"},
        ],
    }


def test_bang_chung_matches_hint():
    chat_action.load_builtin_actions()
    assert (
        chat_action.match_action(ChatActionRequest(question="Vẽ đồ thị bằng chứng"))
        is not None
    )


def test_bang_chung_without_conversation_guides():
    chat_action.load_builtin_actions()
    rendered = _render(chat_action.dispatch(ChatActionRequest(question="vẽ đồ thị bằng chứng")))
    assert "Chưa rõ cuộc trò chuyện" in rendered


def test_bang_chung_without_trace_guides(monkeypatch):
    monkeypatch.setattr(visual, "_latest_conversation_trace", lambda conversation_id: None)
    rendered = _render(
        _dispatch("vẽ đồ thị bằng chứng", conversation_id="CONV-1")
    )
    assert "chưa có câu trả lời nào kèm dấu vết bằng chứng" in rendered
    assert "```mermaid" not in rendered


def test_bang_chung_renders_mermaid_and_stats(monkeypatch):
    from aios_habit.evidence_trace_schema import EvidenceTrace

    trace = EvidenceTrace.from_dict(_trace_dict())
    monkeypatch.setattr(
        visual, "_latest_conversation_trace", lambda conversation_id: trace
    )
    rendered = _render(_dispatch("vẽ đồ thị bằng chứng", conversation_id="CONV-1"))

    assert "```mermaid" in rendered
    assert "flowchart LR" in rendered
    assert "SOP-han.pdf" in rendered
    assert "Thống kê đồ thị: 4 nút" in rendered
    assert "Câu trả lời tổng hợp" in rendered


def test_bang_chung_insufficient_trace_guides(monkeypatch):
    from aios_habit.evidence_trace_schema import EvidenceTrace

    trace = EvidenceTrace.from_dict(
        {
            "trace_id": "TRC-2",
            "conversation_id": "CONV-1",
            "nodes": [{"id": "a-1", "node_type": "answer", "title": "Câu trả lời"}],
            "edges": [],
        }
    )
    monkeypatch.setattr(
        visual, "_latest_conversation_trace", lambda conversation_id: trace
    )
    rendered = _render(_dispatch("vẽ đồ thị bằng chứng", conversation_id="CONV-1"))

    assert "Chưa đủ bằng chứng để vẽ đồ thị" in rendered
    assert "```mermaid" not in rendered


def test_bang_chung_trace_loader_error_guides(monkeypatch):
    def _boom(conversation_id):
        raise OSError("store hỏng")

    monkeypatch.setattr(visual, "_latest_conversation_trace", _boom)
    rendered = _render(_dispatch("đồ thị bằng chứng", conversation_id="CONV-1"))
    assert "Chưa đọc được dấu vết bằng chứng" in rendered


# --------------------------------------------------------------------------
# Chat bubble rendering: mermaid fences become real diagrams
# --------------------------------------------------------------------------


def test_render_assistant_content_draws_mermaid_fence():
    from aios_habit.workspace_chat_ui import render_assistant_content

    content = "**Bản đồ tri thức**\n\n```mermaid\nflowchart LR\n    A-->B\n```\n\nCuối."
    with patch("streamlit.markdown") as mock_markdown, patch(
        "streamlit.mermaid_chart"
    ) as mock_mermaid:
        render_assistant_content(content, locale="vi")

    mock_mermaid.assert_called_once_with("flowchart LR\n    A-->B")
    rendered_parts = [call.args[0] for call in mock_markdown.call_args_list]
    assert any("**Bản đồ tri thức**" in part for part in rendered_parts)
    assert any("Cuối." in part for part in rendered_parts)
    assert all("```mermaid" not in part for part in rendered_parts)


def test_render_assistant_content_plain_text_uses_markdown_only():
    from aios_habit.workspace_chat_ui import render_assistant_content

    with patch("streamlit.markdown") as mock_markdown, patch(
        "streamlit.mermaid_chart"
    ) as mock_mermaid:
        render_assistant_content("Không có sơ đồ nào ở đây.", locale="vi")

    mock_mermaid.assert_not_called()
    mock_markdown.assert_called_once_with("Không có sơ đồ nào ở đây.")


def test_render_assistant_content_falls_back_without_mermaid_api():
    from aios_habit.workspace_chat_ui import render_assistant_content

    content = "```mermaid\nflowchart LR\n    A-->B\n```"
    with patch("streamlit.markdown") as mock_markdown, patch(
        "streamlit.mermaid_chart", None
    ):
        render_assistant_content(content, locale="vi")

    mock_markdown.assert_called_once_with(content)


def test_render_assistant_content_falls_back_when_diagram_fails():
    from aios_habit.workspace_chat_ui import render_assistant_content

    content = "```mermaid\nflowchart LR\n    A-->B\n```"
    with patch("streamlit.markdown") as mock_markdown, patch(
        "streamlit.mermaid_chart", MagicMock(side_effect=RuntimeError("mermaid lỗi"))
    ) as mock_mermaid:
        render_assistant_content(content, locale="vi")

    mock_mermaid.assert_called_once()
    mock_markdown.assert_called_once_with(content)


def test_chat_bubble_draws_map_for_assistant_message():
    from aios_habit.workspace_chat_models import ChatMessage
    from aios_habit.workspace_chat_ui import render_chat_bubble

    msg = ChatMessage(
        id="msg_map_001",
        conversation_id="conv_001",
        role="assistant",
        content="Bản đồ tri thức\n\n```mermaid\nflowchart LR\n    A-->B\n```",
        trace_id=None,
    )
    with patch("streamlit.chat_message") as mock_chat_message, patch(
        "streamlit.markdown"
    ) as mock_markdown, patch("streamlit.mermaid_chart") as mock_mermaid:
        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()
        render_chat_bubble(msg, is_latest=False, locale="vi", trace_loader=MagicMock())

    mock_mermaid.assert_called_once_with("flowchart LR\n    A-->B")
    assert any("Bản đồ tri thức" in call.args[0] for call in mock_markdown.call_args_list)


def test_chat_bubble_user_message_keeps_plain_markdown():
    from aios_habit.workspace_chat_models import ChatMessage
    from aios_habit.workspace_chat_ui import render_chat_bubble

    msg = ChatMessage(
        id="msg_user_002",
        conversation_id="conv_001",
        role="user",
        content="vẽ bản đồ tri thức",
    )
    with patch("streamlit.chat_message") as mock_chat_message, patch(
        "streamlit.markdown"
    ) as mock_markdown, patch("streamlit.mermaid_chart") as mock_mermaid:
        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()
        render_chat_bubble(msg, is_latest=False, locale="vi")

    mock_mermaid.assert_not_called()
    mock_markdown.assert_called_once_with("vẽ bản đồ tri thức")
