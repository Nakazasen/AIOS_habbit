"""Tests for the TOOL-5 chat actions drawing the visual knowledge maps."""

from __future__ import annotations

import base64
import io
from types import SimpleNamespace
import pytest

from aios_habit import chat_action
from aios_habit import chat_action_visual_maps as visual
from aios_habit.chat_action import BLOCK_CHART, ChatActionRequest
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


def _chart_block(outcome):
    for block in outcome.blocks:
        if block.kind == BLOCK_CHART:
            return block
    return None


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


def test_tri_thuc_renders_map_image_zones_and_relations(monkeypatch):
    monkeypatch.setattr(visual, "_load_graph_inputs", _knowledge_map_fixture)
    outcome = _dispatch("vẽ bản đồ tri thức")
    rendered = _render(outcome)

    chart = _chart_block(outcome)
    assert chart is not None
    assert chart.image_png.startswith(b"\x89PNG")
    assert "data:image/png;base64," in rendered
    assert "ảnh vẽ tối đa" in rendered
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
    assert "data:image/png" not in rendered


def test_tri_thuc_empty_store_guides(monkeypatch):
    monkeypatch.setattr(visual, "_load_graph_inputs", lambda: ([], [], [], [], []))
    rendered = _render(_dispatch("vẽ bản đồ tri thức"))
    assert "Chưa có dữ liệu" in rendered
    assert "data:image/png" not in rendered


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


def test_ho_so_renders_case_map_metrics_and_nodes(monkeypatch):
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
    outcome = _dispatch("vẽ bản đồ hồ sơ CASE-1")
    rendered = _render(outcome)

    chart = _chart_block(outcome)
    assert chart is not None
    assert chart.image_png.startswith(b"\x89PNG")
    assert "data:image/png;base64," in rendered
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
    assert "data:image/png" not in rendered


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
    assert "data:image/png" not in rendered


def test_bang_chung_renders_map_image_and_stats(monkeypatch):
    from aios_habit.evidence_trace_schema import EvidenceTrace

    trace = EvidenceTrace.from_dict(_trace_dict())
    monkeypatch.setattr(
        visual, "_latest_conversation_trace", lambda conversation_id: trace
    )
    outcome = _dispatch("vẽ đồ thị bằng chứng", conversation_id="CONV-1")
    rendered = _render(outcome)

    chart = _chart_block(outcome)
    assert chart is not None
    assert chart.image_png.startswith(b"\x89PNG")
    assert "data:image/png;base64," in rendered
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
    assert "data:image/png" not in rendered


def test_bang_chung_trace_loader_error_guides(monkeypatch):
    def _boom(conversation_id):
        raise OSError("store hỏng")

    monkeypatch.setattr(visual, "_latest_conversation_trace", _boom)
    rendered = _render(_dispatch("đồ thị bằng chứng", conversation_id="CONV-1"))
    assert "Chưa đọc được dấu vết bằng chứng" in rendered


# --------------------------------------------------------------------------
# Map PNG renderer (visual_map_image)
# --------------------------------------------------------------------------


def _image_size(png: bytes):
    from PIL import Image

    with Image.open(io.BytesIO(png)) as image:
        return image.size


def test_render_map_png_returns_valid_small_png():
    from aios_habit.visual_map_image import (
        MapEdgeSpec,
        MapImageSpec,
        MapNodeSpec,
        render_map_png,
    )

    spec = MapImageSpec(
        title="Bản đồ thử",
        nodes=(
            MapNodeSpec("CASE-1", "Hệ thống làm mát quá nhiệt", zone="Hồ sơ", kind="case"),
            MapNodeSpec("EV-1", "Log nhiệt độ ca đêm", zone="Bằng chứng", kind="evidence"),
            MapNodeSpec("ANS-1", "Trả lời mạnh: vệ sinh quạt", zone="Trả lời mạnh", kind="answer"),
            MapNodeSpec("L-1", "Vệ sinh quạt định kỳ", zone="Bài học", kind="lesson"),
        ),
        edges=(
            MapEdgeSpec("CASE-1", "EV-1", "có bằng chứng"),
            MapEdgeSpec("CASE-1", "ANS-1", "có câu trả lời"),
            MapEdgeSpec("ANS-1", "EV-1", "trích dẫn bằng chứng"),
        ),
    )
    png = render_map_png(spec)

    assert png.startswith(b"\x89PNG")
    assert len(png) < chat_action.CHART_MAX_BYTES
    width, height = _image_size(png)
    assert width <= 1400
    assert height <= 1000
    assert width > 500
    assert height > 150


def test_render_map_png_empty_spec_is_valid():
    from aios_habit.visual_map_image import MapImageSpec, render_map_png

    png = render_map_png(MapImageSpec(title="", nodes=(), edges=()))
    assert png.startswith(b"\x89PNG")
    assert _image_size(png)[0] > 0


def test_render_map_png_caps_image_dimensions():
    from aios_habit.visual_map_image import (
        MapImageSpec,
        MapNodeSpec,
        render_map_png,
    )

    nodes = tuple(
        MapNodeSpec(
            f"N-{index}",
            f"Nút số {index} với nhãn dài để kiểm tra xuống dòng trong khung",
            zone=f"Khu {index % 3}",
            kind="other",
        )
        for index in range(30)
    )
    png = render_map_png(MapImageSpec(title="Bản đồ lớn", nodes=nodes, edges=()))
    width, height = _image_size(png)
    assert width <= 1400
    assert height <= 1000
    # Six columns max => the 30 nodes are truncated, the image stays bounded.
    assert width <= 28 * 2 + 6 * 240 + 5 * 76


def test_render_map_png_decodes_embedded_data_uri():
    from aios_habit.visual_map_image import (
        MapImageSpec,
        MapNodeSpec,
        render_map_png,
    )

    png = render_map_png(
        MapImageSpec(nodes=(MapNodeSpec("A", "Nút A", zone="Khu", kind="case"),))
    )
    data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    raw = base64.b64decode(data_uri.split(",", 1)[1])
    assert raw == png
