"""Builtin chat actions: draw the local knowledge maps inside the answer bubble.

Wires the visual-map group of the TOOL-1 inventory into the chat through the
`chat_action` framework (TOOL-2):

- `worklens_semantic_map.build_worklens_semantic_graph` builds the workspace
  knowledge map from the local notebook/case stores (read-only).
- `knowledge_map_html` supplies the board vocabulary used by the chat output:
  the zone titles (`ZONE_DEFS`) and the Vietnamese relation labels
  (`RELATION_LABELS`); the map image is grouped by the same zones.
- `visual_knowledge_map` builds the map of one case/profile (evidence, strong
  answers, lesson cards) with its own metrics.
- `evidence_graph_viewer.build_evidence_graph_view_model` builds the evidence
  graph of the latest answer trace of the conversation (the bubble keeps its
  own on-demand "Xem đồ thị bằng chứng" button; this action adds the typed
  question path).

The map itself is rendered as a PNG by `visual_map_image.render_map_png` and
carried by the proven `chart` block (data URI, capped), so it shows right in
the answer and persists with the message. Streamlit's Mermaid element was not
used: on the app page it cuts the diagram (see the TOOL-5 report).

Read-only: no index writes, no store writes, no new files.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence, Tuple

from aios_habit.chat_action import (
    BLOCK_CHART,
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)

ACTION_TRI_THUC = "ban_do_tri_thuc"
TITLE_TRI_THUC = "Bản đồ tri thức"

ACTION_HO_SO = "ban_do_ho_so"
TITLE_HO_SO = "Bản đồ hồ sơ"

ACTION_BANG_CHUNG = "do_thi_bang_chung"
TITLE_BANG_CHUNG = "Đồ thị bằng chứng"

_HINTS_TRI_THUC = ("bản đồ tri thức", "sơ đồ tri thức")
_HINTS_HO_SO = ("bản đồ hồ sơ", "sơ đồ hồ sơ", "bản đồ case", "sơ đồ case")
_HINTS_BANG_CHUNG = ("đồ thị bằng chứng", "sơ đồ bằng chứng")

# Connectors stripped from the topic tail: "về quy trình hàn" -> "quy trình hàn".
_TOPIC_CONNECTORS = (
    "về việc",
    "về chủ đề",
    "với chủ đề",
    "chủ đề",
    "của",
    "cho",
    "về",
    "trong",
    "ở",
)

_PUNCTUATION = " \t\r\n.,:;!?…\"'“”‘’()[]"

# Caps keep the bubble light and the persisted message small.
_MAX_MAP_NODES = 60
_MAX_MAP_EDGES = 120
_MAX_FOCUS_NODES = 30
_MAX_FOCUS_EDGES = 60
_MAX_ZONE_ROWS = 8
_MAX_NODE_ROWS = 20
_MAX_EDGE_ROWS = 15
_MAX_CASE_ROWS = 10
_MAX_LABEL = 60
_MAX_IMAGE_NODES = 15
_MAX_IMAGE_EDGES = 24

_CASE_ZONE_LABELS = {
    "case": "Hồ sơ",
    "evidence": "Bằng chứng",
    "answer": "Trả lời mạnh",
    "lesson": "Bài học",
}

_CASE_RELATION_LABELS = {
    "case_has_evidence": "có bằng chứng",
    "case_has_answer": "có câu trả lời",
    "answer_cites_evidence": "trích dẫn bằng chứng",
    "action_creates_lesson": "rút ra bài học",
}


def _message(text: str, action: str, title: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=action,
        title=title,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _clip(text: Any, limit: int = _MAX_LABEL) -> str:
    cleaned = " ".join(str(text if text is not None else "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _topic_from_question(question: str, hints: Sequence[str]) -> str:
    """Extract the topic typed after the hint ("vẽ bản đồ tri thức về X" -> "X")."""
    raw = str(question or "")
    lowered = raw.casefold()
    for hint in hints:
        index = lowered.find(hint.casefold())
        if index >= 0:
            return _clean_topic(raw[index + len(hint) :])
    normalized = normalize_text(raw)
    for hint in hints:
        hint_norm = normalize_text(hint)
        index = normalized.find(hint_norm)
        if index >= 0:
            return _clean_topic(normalized[index + len(hint_norm) :])
    return ""


def _clean_topic(tail: str) -> str:
    cleaned = str(tail or "").strip(_PUNCTUATION)
    changed = True
    while changed and cleaned:
        changed = False
        lowered = cleaned.casefold()
        for connector in _TOPIC_CONNECTORS:
            if lowered == connector:
                return ""
            if lowered.startswith(connector + " "):
                cleaned = cleaned[len(connector) :].strip(_PUNCTUATION)
                changed = True
                break
    return cleaned


# --------------------------------------------------------------------------
# Local store readers (injectable so tests stay hermetic)
# --------------------------------------------------------------------------


def _load_graph_inputs() -> Tuple[Sequence[Any], ...]:
    """Read the local JSONL stores: notebooks, sources, cases, evidence, lessons."""
    from aios_habit.case_store import load_cases, load_evidence
    from aios_habit.learning_models import load_learning_cards
    from aios_habit.source_ingest import load_sources
    from aios_habit.workspace_models import load_notebooks

    return (
        load_notebooks(),
        load_sources(),
        load_cases(),
        load_evidence(),
        load_learning_cards(),
    )


def _load_case_store() -> Tuple[Sequence[Any], Sequence[Any]]:
    from aios_habit.case_store import load_cases, load_evidence

    return load_cases(), load_evidence()


def _load_case_lessons(case_id: str) -> Sequence[Any]:
    from aios_habit.learning_models import load_learning_cards_for_case

    return load_learning_cards_for_case(case_id)


def _latest_conversation_trace(conversation_id: str) -> Optional[Any]:
    """Latest stored evidence trace of one conversation (append order)."""
    from aios_habit.workspace_chat_store import load_conversation_traces

    traces = load_conversation_traces(conversation_id)
    return traces[-1] if traces else None


# --------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------


def _meta_note(meta: Mapping[str, Any]) -> str:
    """One Vietnamese confidence line for a worklens graph metadata block."""
    kind = str(meta.get("graph_kind") or "unknown")
    if kind == "empty":
        text = "Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức."
    elif bool(meta.get("uses_sample_data")):
        text = "Dữ liệu mẫu/import — chưa phải hồ sơ thật."
    elif kind == "imported":
        text = "Đồ thị nhập từ NotebookLM — kiểm tra lại trước khi kết luận."
    elif kind == "structural":
        text = "Sơ đồ cấu trúc ứng dụng — không phải bản đồ nghiệp vụ đã xác minh."
    elif kind == "semantic":
        state = str(meta.get("business_verification_state") or "")
        if bool(meta.get("has_verified_business_data")) or state == "verified":
            text = "Bản đồ nghiệp vụ từ hồ sơ/sổ tri thức đã xác minh."
        elif state == "needs_verification":
            text = "Bản đồ nghiệp vụ từ hồ sơ nháp/import — cần xác minh trước khi kết luận."
        else:
            text = "Bản đồ nghiệp vụ có dữ liệu chưa rõ nguồn gốc — cần xác minh trước khi kết luận."
    else:
        text = f"Loại đồ thị: {kind}"
    warnings = [str(item) for item in (meta.get("warnings") or []) if str(item).strip()]
    if warnings:
        text += " Lưu ý: " + "; ".join(warnings) + "."
    return text


def _zone_defs() -> Tuple[Tuple[str, str, Tuple[str, ...]], ...]:
    from aios_habit.knowledge_map_html import ZONE_DEFS

    return ZONE_DEFS


def _zone_title(node_type: Any) -> str:
    ntype = str(node_type or "other").lower()
    fallback = "Khác"
    for _key, title, types in _zone_defs():
        if ntype in types:
            return title
        fallback = title
    return fallback


def _relation_label(raw: Any) -> str:
    from aios_habit.knowledge_map_html import RELATION_LABELS

    relation = str(raw or "").strip()
    if not relation:
        return "liên quan đến"
    if relation in _CASE_RELATION_LABELS:
        return _CASE_RELATION_LABELS[relation]
    return RELATION_LABELS.get(relation, relation.replace("_", " "))


def _focus_subgraph(
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    topic: str,
) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]], int]:
    """Keep the nodes matching the typed topic plus their direct neighbors."""
    topic_norm = normalize_text(topic)
    if not topic_norm:
        return list(nodes), list(edges), 0

    def _matches(node: Mapping[str, Any]) -> bool:
        haystack = normalize_text(
            " ".join(
                str(node.get(key) or "")
                for key in ("id", "label", "description", "source_ref")
            )
        )
        return topic_norm in haystack

    matched_ids = {str(node.get("id")) for node in nodes if _matches(node)}
    if not matched_ids:
        return [], [], 0

    keep_ids = set(matched_ids)
    for edge in edges:
        source = str(edge.get("from"))
        target = str(edge.get("to"))
        if source in matched_ids:
            keep_ids.add(target)
        if target in matched_ids:
            keep_ids.add(source)

    kept_nodes = [node for node in nodes if str(node.get("id")) in keep_ids]
    dropped = len(nodes) - len(kept_nodes)
    kept_nodes = kept_nodes[:_MAX_FOCUS_NODES]
    kept_ids = {str(node.get("id")) for node in kept_nodes}
    kept_edges = [
        edge
        for edge in edges
        if str(edge.get("from")) in kept_ids and str(edge.get("to")) in kept_ids
    ][:_MAX_FOCUS_EDGES]
    return kept_nodes, kept_edges, dropped


def _chart_block(nodes: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]], caption: str) -> ChatActionBlock:
    """Draw the map with `visual_map_image` and wrap it in a chart block."""
    from aios_habit.visual_map_image import (
        MapEdgeSpec,
        MapImageSpec,
        MapNodeSpec,
        render_map_png,
    )

    picked = _pick_image_nodes(nodes)
    node_specs = []
    for node in picked:
        node_specs.append(
            MapNodeSpec(
                node_id=str(node.get("id")),
                label=_clip(node.get("label") or node.get("id"), 48),
                zone=_node_zone_label(node),
                kind=str(node.get("type") or "other"),
            )
        )
    image_ids = {spec.node_id for spec in node_specs}
    edge_specs = [
        MapEdgeSpec(
            source=str(edge.get("from")),
            target=str(edge.get("to")),
            label=_relation_label(edge.get("relation")),
        )
        for edge in edges
        if str(edge.get("from")) in image_ids and str(edge.get("to")) in image_ids
    ][:_MAX_IMAGE_EDGES]
    png = render_map_png(
        MapImageSpec(title="", nodes=tuple(node_specs), edges=tuple(edge_specs))
    )
    return ChatActionBlock(BLOCK_CHART, image_png=png, caption=caption, alt="Bản đồ tri thức")


def _node_zone_label(node: Mapping[str, Any]) -> str:
    zone_hint = node.get("zone")
    if zone_hint:
        return str(zone_hint)
    return _zone_title(node.get("type"))


# Nodes that carry the story (case/evidence/lessons) win the limited image slots.
_IMAGE_KIND_ORDER = {
    "case": 0,
    "evidence": 1,
    "answer": 1,
    "learning": 2,
    "lesson": 2,
    "cause": 2,
    "error": 2,
    "action": 2,
    "setting": 2,
    "process": 3,
    "system": 3,
    "document": 4,
    "source": 4,
    "question": 1,
    "citation": 2,
    "other": 5,
}


def _pick_image_nodes(nodes: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    indexed = list(enumerate(nodes))
    indexed.sort(
        key=lambda pair: (
            _IMAGE_KIND_ORDER.get(str(pair[1].get("type") or "other").lower(), 5),
            pair[0],
        )
    )
    return [node for _index, node in indexed[:_MAX_IMAGE_NODES]]


def _zone_table(nodes: Sequence[Mapping[str, Any]]) -> ChatActionBlock:
    order: List[str] = []
    counts: dict = {}
    examples: dict = {}
    for node in nodes:
        title = _zone_title(node.get("type"))
        if title not in counts:
            order.append(title)
            counts[title] = 0
            examples[title] = []
        counts[title] += 1
        if len(examples[title]) < 3:
            examples[title].append(_clip(node.get("label") or node.get("id"), 32))
    rows = [
        (title, str(counts[title]), "; ".join(examples[title]))
        for title in order
    ]
    return ChatActionBlock(
        BLOCK_TABLE,
        headers=("Khu", "Số nút", "Ví dụ"),
        rows=rows[:_MAX_ZONE_ROWS],
        caption="Khu được nhóm theo bảng khu của màn Bản đồ tri thức (không phải toàn bộ nút).",
    )


def _relation_table(edges: Sequence[Mapping[str, Any]], labels: Mapping[str, str]) -> ChatActionBlock:
    rows = []
    for edge in edges[:_MAX_EDGE_ROWS]:
        rows.append(
            (
                _clip(labels.get(str(edge.get("from")), edge.get("from")), 32),
                _relation_label(edge.get("relation")),
                _clip(labels.get(str(edge.get("to")), edge.get("to")), 32),
            )
        )
    caption = ""
    if len(edges) > _MAX_EDGE_ROWS:
        caption = f"Hiện {_MAX_EDGE_ROWS}/{len(edges)} quan hệ."
    return ChatActionBlock(
        BLOCK_TABLE,
        headers=("Từ", "Quan hệ", "Đến"),
        rows=rows,
        caption=caption,
    )


# --------------------------------------------------------------------------
# Action: knowledge map (worklens_semantic_map + knowledge_map_html zones)
# --------------------------------------------------------------------------


def _tri_thuc_handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    topic = _topic_from_question(request.question, _HINTS_TRI_THUC)
    try:
        notebooks, sources, cases, evidence, learning_cards = _load_graph_inputs()
    except Exception:
        return _message(
            "Chưa đọc được dữ liệu cục bộ để dựng bản đồ tri thức. Bạn thử lại sau nhé.",
            ACTION_TRI_THUC,
            TITLE_TRI_THUC,
        )

    from aios_habit.worklens_semantic_map import build_worklens_semantic_graph

    graph = build_worklens_semantic_graph(
        notebooks=notebooks,
        sources=sources,
        cases=cases,
        evidence=evidence,
        learning_cards=learning_cards,
        max_nodes=_MAX_MAP_NODES,
        max_edges=_MAX_MAP_EDGES,
    )
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    meta = dict(graph.get("meta") or {})

    if not nodes:
        return _message(
            "Chưa có dữ liệu để dựng bản đồ tri thức trên máy này. "
            "Hãy tạo sổ tri thức, hồ sơ hoặc bằng chứng trước nhé.",
            ACTION_TRI_THUC,
            TITLE_TRI_THUC,
        )

    total_nodes = len(nodes)
    truncated_focus = 0
    if topic:
        nodes, edges, truncated_focus = _focus_subgraph(nodes, edges, topic)
        if not nodes:
            return _message(
                f"Chưa tìm thấy “{topic}” trong bản đồ tri thức hiện có "
                f"({total_nodes} nút). Bạn thử từ khóa khác, hoặc bỏ phần “về …” "
                "để xem toàn bộ bản đồ nhé.",
                ACTION_TRI_THUC,
                TITLE_TRI_THUC,
            )

    scope = f"quanh chủ đề “{topic}”" if topic else "toàn bộ"
    blocks = [
        ChatActionBlock(
            BLOCK_MARKDOWN,
            text=(
                f"Bản đồ tri thức {scope} — {len(nodes)} nút, {len(edges)} quan hệ "
                f"(chỉ đọc).\n\n{_meta_note(meta)}"
            ),
        ),
        _chart_block(
            nodes,
            edges,
            caption=(
                f"Bản đồ tri thức — ảnh vẽ tối đa {_MAX_IMAGE_NODES} nút, "
                f"{_MAX_IMAGE_EDGES} quan hệ; bảng dưới liệt kê đầy đủ."
            ),
        ),
    ]
    if truncated_focus:
        blocks.append(
            ChatActionBlock(
                BLOCK_MARKDOWN,
                text=(
                    f"Đã ẩn {truncated_focus} nút ngoài chủ đề để bản đồ gọn hơn "
                    "(tối đa "
                    f"{_MAX_FOCUS_NODES} nút)."
                ),
            )
        )

    labels = {}
    for node in nodes:
        labels[str(node.get("id"))] = _clip(node.get("label") or node.get("id"), 32)
    blocks.append(_zone_table(nodes))
    if edges:
        blocks.append(_relation_table(edges, labels))

    return ChatActionOutcome(
        action=ACTION_TRI_THUC, title=TITLE_TRI_THUC, blocks=tuple(blocks)
    )


# --------------------------------------------------------------------------
# Action: one case/profile map (visual_knowledge_map)
# --------------------------------------------------------------------------


def _match_case(cases: Sequence[Any], topic: str) -> Optional[Any]:
    topic_norm = normalize_text(topic)
    if not topic_norm:
        return None
    for case in cases:
        case_id = str(getattr(case, "case_id", "") or "")
        title = str(getattr(case, "title", "") or "")
        if topic_norm == normalize_text(case_id) or topic_norm in normalize_text(title):
            return case
    return None


def _lesson_label(card: Any) -> str:
    lesson = str(getattr(card, "reusable_lesson", "") or "").strip()
    if lesson:
        return _clip(lesson, 48)
    return str(getattr(card, "learning_id", "") or "Bài học")


def _ho_so_handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    topic = _topic_from_question(request.question, _HINTS_HO_SO)
    try:
        cases, evidence_items = _load_case_store()
    except Exception:
        return _message(
            "Chưa đọc được sổ hồ sơ cục bộ. Bạn thử lại sau nhé.",
            ACTION_HO_SO,
            TITLE_HO_SO,
        )

    if not cases:
        return _message(
            "Máy này chưa có hồ sơ nào để vẽ bản đồ. Hãy tạo hồ sơ trong workspace trước nhé.",
            ACTION_HO_SO,
            TITLE_HO_SO,
        )

    case = _match_case(cases, topic) if topic else None
    if case is None:
        rows = [
            (
                str(index),
                str(getattr(item, "case_id", "") or "")[:12],
                _clip(getattr(item, "title", ""), 48),
                str(getattr(item, "status", "") or "—"),
            )
            for index, item in enumerate(cases[:_MAX_CASE_ROWS], start=1)
        ]
        caption = ""
        if len(cases) > _MAX_CASE_ROWS:
            caption = f"Hiện {_MAX_CASE_ROWS}/{len(cases)} hồ sơ."
        if topic:
            intro = (
                f"Chưa tìm thấy hồ sơ “{topic}”. Bạn thử lại đúng mã hoặc tên hồ sơ dưới đây nhé."
            )
        else:
            intro = "Bạn muốn vẽ bản đồ hồ sơ nào? Gõ “vẽ bản đồ hồ sơ <mã hoặc tên>”."
        return ChatActionOutcome(
            action=ACTION_HO_SO,
            title=TITLE_HO_SO,
            blocks=(
                ChatActionBlock(BLOCK_MARKDOWN, text=intro),
                ChatActionBlock(
                    BLOCK_TABLE,
                    headers=("#", "Mã hồ sơ", "Tên hồ sơ", "Trạng thái"),
                    rows=rows,
                    caption=caption,
                ),
            ),
        )

    case_id = str(getattr(case, "case_id", "") or "")
    case_evidence = [
        item
        for item in evidence_items
        if str(getattr(item, "case_id", "") or "") == case_id
    ]
    answers = [
        item
        for item in case_evidence
        if str(getattr(item, "source_type", "") or "") == "ide_handoff_strong_answer"
    ]
    try:
        lessons = list(_load_case_lessons(case_id))
    except Exception:
        lessons = []
    lesson_dtos = [{"title": _lesson_label(card)} for card in lessons]

    from aios_habit.visual_knowledge_map import (
        build_visual_knowledge_graph,
        summarize_map_metrics,
    )

    graph = build_visual_knowledge_graph(case, case_evidence, lesson_dtos, answers)
    metrics = summarize_map_metrics(graph)
    image_nodes = [
        {
            "id": node.id,
            "label": node.label,
            "type": node.type,
            "zone": _CASE_ZONE_LABELS.get(node.type, "Khác"),
        }
        for node in graph.nodes.values()
    ]
    image_edges = [
        {"from": edge.source, "to": edge.target, "relation": edge.relation}
        for edge in graph.edges
    ]

    blocks = [
        ChatActionBlock(
            BLOCK_MARKDOWN,
            text=(
                f"Bản đồ hồ sơ “{_clip(getattr(case, 'title', '') or case_id, 60)}” — "
                f"{metrics['node_count']} nút, {metrics['edge_count']} quan hệ (chỉ đọc)."
            ),
        ),
        _chart_block(
            image_nodes,
            image_edges,
            caption=f"Bản đồ hồ sơ — ảnh vẽ tối đa {_MAX_IMAGE_NODES} nút (chỉ đọc).",
        ),
        ChatActionBlock(
            BLOCK_TABLE,
            headers=("Chỉ số", "Giá trị"),
            rows=(
                ("Số nút", str(metrics["node_count"])),
                ("Số quan hệ", str(metrics["edge_count"])),
                ("Bằng chứng", str(metrics["evidence_count"])),
                ("Câu trả lời mạnh", str(metrics["answer_count"])),
                ("Bài học", str(metrics["lesson_count"])),
                ("Độ phủ trích dẫn", str(metrics["citation_coverage"])),
            ),
        ),
    ]

    other_nodes = [
        node for node in graph.nodes.values() if node.id != graph.case.case_id
    ]
    node_rows = []
    for index, node in enumerate(other_nodes[:_MAX_NODE_ROWS], start=1):
        node_rows.append(
            (
                str(index),
                str(node.type),
                _clip(node.label, 48),
                _clip(node.details.get("source_type") or node.details.get("privacy") or "", 24),
            )
        )
    if node_rows:
        caption = ""
        if len(other_nodes) > _MAX_NODE_ROWS:
            caption = f"Hiện {_MAX_NODE_ROWS}/{len(other_nodes)} nút (không kể nút hồ sơ)."
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("#", "Nhóm", "Nhãn", "Nguồn"),
                rows=node_rows,
                caption=caption,
            )
        )

    return ChatActionOutcome(
        action=ACTION_HO_SO, title=TITLE_HO_SO, blocks=tuple(blocks)
    )


# --------------------------------------------------------------------------
# Action: evidence graph of the latest answer trace (evidence_graph_viewer)
# --------------------------------------------------------------------------


def _evidence_image_edges(
    edges: Sequence[Mapping[str, Any]],
) -> List[Mapping[str, Any]]:
    """Normalize the view-model edges for the PNG renderer."""
    return [
        {
            "from": edge.get("source_id"),
            "to": edge.get("target_id"),
            "relation": edge.get("display_label") or edge.get("label") or edge.get("relation"),
        }
        for edge in edges
    ]


def _bang_chung_handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    conversation_id = str(request.conversation_id or "").strip()
    if not conversation_id:
        return _message(
            "Chưa rõ cuộc trò chuyện đang mở nên chưa tìm được dấu vết bằng chứng. "
            "Hãy mở một cuộc trò chuyện cụ thể rồi hỏi lại.",
            ACTION_BANG_CHUNG,
            TITLE_BANG_CHUNG,
        )
    try:
        trace = _latest_conversation_trace(conversation_id)
    except Exception:
        return _message(
            "Chưa đọc được dấu vết bằng chứng của cuộc trò chuyện. Bạn thử lại sau nhé.",
            ACTION_BANG_CHUNG,
            TITLE_BANG_CHUNG,
        )
    if trace is None:
        return _message(
            "Cuộc trò chuyện này chưa có câu trả lời nào kèm dấu vết bằng chứng. "
            "Hãy đặt một câu hỏi cần tra cứu tài liệu trước nhé.",
            ACTION_BANG_CHUNG,
            TITLE_BANG_CHUNG,
        )

    from aios_habit.evidence_graph_viewer import build_evidence_graph_view_model

    try:
        view = build_evidence_graph_view_model(trace, locale=request.locale or "vi")
    except Exception:
        return _message(
            "Chưa dựng được đồ thị bằng chứng cho câu trả lời này. Bạn thử lại sau nhé.",
            ACTION_BANG_CHUNG,
            TITLE_BANG_CHUNG,
        )

    if view.is_insufficient:
        text = str(view.notice or "Bằng chứng chưa đủ để dựng đồ thị.")
        if view.notice_desc:
            text += "\n\n" + str(view.notice_desc)
        return _message(text, ACTION_BANG_CHUNG, TITLE_BANG_CHUNG)

    nodes = list(view.nodes or [])
    edges = list(view.edges or [])
    image_nodes = [
        {
            "id": node.get("id"),
            "label": node.get("title") or node.get("id"),
            "type": node.get("node_type") or "other",
            "zone": node.get("type_label") or "Khác",
        }
        for node in nodes
    ]
    blocks = [
        ChatActionBlock(
            BLOCK_MARKDOWN,
            text=(
                f"Đồ thị bằng chứng của câu trả lời gần nhất — {view.stats_label} "
                "(chỉ đọc, bám đúng dấu vết)."
            ),
        ),
        _chart_block(
            image_nodes,
            _evidence_image_edges(edges),
            caption=f"Đồ thị bằng chứng — ảnh vẽ tối đa {_MAX_IMAGE_NODES} nút (chỉ đọc).",
        ),
    ]
    rows = []
    for index, node in enumerate(nodes[:_MAX_NODE_ROWS], start=1):
        rows.append(
            (
                str(index),
                str(node.get("type_label") or node.get("node_type") or ""),
                _clip(node.get("title") or node.get("id"), 48),
                _clip(node.get("source_id") or node.get("citation_id") or "", 32),
            )
        )
    if rows:
        caption = ""
        if len(nodes) > _MAX_NODE_ROWS:
            caption = f"Hiện {_MAX_NODE_ROWS}/{len(nodes)} nút."
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("#", "Loại", "Nhãn", "Nguồn / trích dẫn"),
                rows=rows,
                caption=caption,
            )
        )
    return ChatActionOutcome(
        action=ACTION_BANG_CHUNG, title=TITLE_BANG_CHUNG, blocks=tuple(blocks)
    )


def register() -> Tuple[ChatAction, ...]:
    return (
        register_action(
            ChatAction(
                name=ACTION_TRI_THUC,
                title=TITLE_TRI_THUC,
                hints=_HINTS_TRI_THUC,
                handler=_tri_thuc_handler,
                description=(
                    "Vẽ bản đồ tri thức cục bộ (sổ, tài liệu, hồ sơ, bằng chứng) "
                    "thành ảnh bản đồ kèm bảng theo khu — nối worklens_semantic_map "
                    "+ knowledge_map_html, chỉ đọc."
                ),
            )
        ),
        register_action(
            ChatAction(
                name=ACTION_HO_SO,
                title=TITLE_HO_SO,
                hints=_HINTS_HO_SO,
                handler=_ho_so_handler,
                description=(
                    "Vẽ bản đồ một hồ sơ (bằng chứng, câu trả lời mạnh, bài học) "
                    "thành ảnh bản đồ kèm bảng chỉ số — nối visual_knowledge_map, chỉ đọc."
                ),
            )
        ),
        register_action(
            ChatAction(
                name=ACTION_BANG_CHUNG,
                title=TITLE_BANG_CHUNG,
                hints=_HINTS_BANG_CHUNG,
                handler=_bang_chung_handler,
                description=(
                    "Vẽ đồ thị bằng chứng của câu trả lời gần nhất trong cuộc trò chuyện "
                    "(dấu vết đã lưu) — nối evidence_graph_viewer, chỉ đọc."
                ),
            )
        ),
    )


register()
