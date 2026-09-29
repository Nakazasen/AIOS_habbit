"""Builtin chat action: score the quality of the latest answer in a conversation.

Wires the benchmark group from the TOOL-1 inventory into the chat through the
`chat_action` framework (TOOL-2):

- `rag_evaluator.evaluate_grounded_answer` scores the answer against the
  evidence stored in its `EvidenceTrace` (heuristic 0-1 metrics).
- `mom_benchmark.score_mom_real_answer` + `weighted_real_answer_score` apply
  the MOM answer rubric (7 criteria 0-5, weighted total /100).
- `rag_benchmark.run_rag_benchmark` re-runs retrieval in-memory over the cited
  evidence snippets to check that the answer evidence is still findable.

Read-only: reads the local chat store (messages + traces), runs everything
in-memory, never writes the production index and adds no UI controls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Tuple

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    register_action,
)

ACTION_NAME = "danh_gia_chat_luong_tra_loi"
ACTION_TITLE = "Đánh giá chất lượng trả lời"

_HINTS = (
    "đánh giá chất lượng trả lời",
    "đánh giá chất lượng câu trả lời",
    "chất lượng trả lời",
    "chất lượng câu trả lời",
    "đánh giá câu trả lời",
    "chấm điểm câu trả lời",
)

# Node types that carry retrievable evidence inside an EvidenceTrace.
_EVIDENCE_NODE_TYPES = frozenset({"source", "chunk", "evidence", "citation"})

_EVALUATOR_LABELS: Tuple[Tuple[str, str], ...] = (
    ("retrieval_coverage", "Độ phủ bằng chứng"),
    ("evidence_relevance", "Độ liên quan bằng chứng"),
    ("metadata_only_rate", "Tỷ lệ bằng chứng chỉ metadata"),
    ("answer_groundedness", "Độ neo câu trả lời vào bằng chứng"),
    ("source_intent_match", "Khớp ý định truy vấn"),
    ("abstention_correctness", "Xử lý thiếu bằng chứng"),
)

_RUBRIC_LABELS: Tuple[Tuple[str, str], ...] = (
    ("source_traceability", "Truy vết nguồn"),
    ("evidence_alignment", "Khớp bằng chứng"),
    ("completeness", "Độ đầy đủ"),
    ("unknown_handling", "Xử lý điều chưa biết"),
    ("actionability", "Tính hành động"),
    ("clarity", "Độ rõ ràng"),
    ("hallucination_control", "Kiểm soát ảo giác"),
)

_PASS_LABELS = {
    "PASS": "Đạt",
    "PASS_WITH_WARNINGS": "Đạt (có cảnh báo)",
    "FAIL": "Chưa đạt",
}

_RUBRIC_NOTE = (
    "Rubric MOM chấm theo cấu trúc câu trả lời bằng chứng (mục “điều có bằng chứng”, "
    "“chưa đủ bằng chứng”, “next checks”); câu trả lời không có các mục này sẽ thấp "
    "điểm ở phần cấu trúc."
)

_HEURISTIC_NOTE = (
    "Điểm số là heuristic tự động từ `rag_evaluator`, rubric `mom_benchmark` và tự "
    "kiểm tra truy xuất `rag_benchmark` — không phải ground truth, không thay thế "
    "kiểm tra thủ công."
)


@dataclass(frozen=True)
class _AnswerView:
    """Minimal answer view shaped for `rag_evaluator.evaluate_grounded_answer`."""

    answer_text: str
    answer_kind: str = ""
    final_answer: bool = False


@dataclass(frozen=True)
class _EvidenceItem:
    """Minimal evidence item view: text plus raw node metadata."""

    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _EvidencePackView:
    """Minimal evidence pack view accepted by the evaluator."""

    items: Sequence[_EvidenceItem] = ()
    privacy_mode: str = "local_only"


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _excerpt(text: str, limit: int = 140) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    number = max(0.0, min(1.0, number))
    return f"{round(number * 100)}%"


def _clean_snippet(text: Any) -> str:
    return " ".join(str(text or "").split())


def _evidence_nodes(trace: Any) -> list[Any]:
    nodes: list[Any] = []
    for node in getattr(trace, "nodes", ()) or ():
        node_type = str(getattr(node, "node_type", "") or "").strip().lower()
        if node_type in _EVIDENCE_NODE_TYPES and _clean_snippet(getattr(node, "snippet", "")):
            nodes.append(node)
    return nodes


def _node_ref_label(node: Any) -> str:
    return str(
        getattr(node, "source_id", "")
        or getattr(node, "title", "")
        or getattr(node, "id", "")
        or "không rõ nguồn"
    ).strip()


def _panel_evaluator(answer_text: str, nodes: Sequence[Any]) -> Tuple[list[tuple[str, str]], Any]:
    from aios_habit.rag_evaluator import evaluate_grounded_answer

    items = [
        _EvidenceItem(
            text=_clean_snippet(getattr(node, "snippet", "")),
            metadata=dict(getattr(node, "metadata", None) or {}),
        )
        for node in nodes
    ]
    result = evaluate_grounded_answer(
        _AnswerView(answer_text=answer_text),
        _EvidencePackView(items=tuple(items)),
    )
    rows = [(label, _percent(getattr(result, key, 0.0))) for key, label in _EVALUATOR_LABELS]
    return rows, result


def _panel_rubric(answer_text: str, nodes: Sequence[Any], trace: Any) -> Tuple[list[tuple[str, str]], float]:
    from aios_habit.mom_benchmark import score_mom_real_answer, weighted_real_answer_score

    trace_metadata = dict(getattr(trace, "metadata", None) or {}) if trace is not None else {}
    mom_answer = {
        "answer_text": answer_text,
        "source_refs": [{"relative_path": _node_ref_label(node)} for node in nodes],
        "confidence_level": str(trace_metadata.get("confidence_level") or ""),
    }
    scores = score_mom_real_answer(mom_answer, valid_source_refs=bool(nodes))
    rows = [(label, f"{int(scores.get(key, 0))}/5") for key, label in _RUBRIC_LABELS]
    return rows, weighted_real_answer_score(scores)


def _chunk_from_node(index: int, node: Any) -> Any:
    from aios_habit.rag_ingest import RAGChunk

    node_id = str(getattr(node, "id", "") or f"EVID-{index}")
    title = _clean_snippet(getattr(node, "title", "")) or node_id
    source_id = str(getattr(node, "source_id", "") or node_id)
    return RAGChunk(
        chunk_id=node_id,
        document_id=source_id,
        element_ids=[node_id],
        text=_clean_snippet(getattr(node, "snippet", "")),
        source_title=title,
        source_path=source_id,
        relative_path=source_id,
        citation_label=str(getattr(node, "citation_id", "") or title),
        file_type="evidence_trace",
        element_types=["evidence"],
        page_numbers=[],
        sheet_names=[],
        slide_numbers=[],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[],
        privacy_mode=str(getattr(node, "privacy_label", "") or "local_only"),
        chunk_index=index,
    )


def _panel_retrieval(bench_query: str, nodes: Sequence[Any]) -> list[tuple[str, str]]:
    from aios_habit.rag_benchmark import (
        RAGBenchmarkConfig,
        RAGBenchmarkQuestion,
        run_rag_benchmark,
    )

    chunks = [_chunk_from_node(index, node) for index, node in enumerate(nodes, start=1)]
    question = RAGBenchmarkQuestion(
        question_id="Q-HOI-THOAI",
        question=bench_query,
        expected_answer_type="answerable",
        expected_chunk_ids=[chunk.chunk_id for chunk in chunks],
        expected_document_ids=[chunk.document_id for chunk in chunks],
        expected_citation_labels=[chunk.citation_label for chunk in chunks],
    )
    config = RAGBenchmarkConfig(tier="custom", top_k=min(10, max(3, len(chunks))))
    summary = run_rag_benchmark(chunks, [question], config)
    return [
        ("Số đoạn bằng chứng kiểm tra", str(len(chunks))),
        ("Tìm lại đoạn bằng chứng", _percent(summary.top_chunk_hit_rate)),
        ("Tìm lại tài liệu nguồn", _percent(summary.document_hit_rate)),
        ("Kết quả", _PASS_LABELS.get(summary.pass_fail, summary.pass_fail)),
    ]


def _latest_answer_messages(messages: Sequence[Any]) -> Tuple[Any, str]:
    """Return the last assistant answer (with content) and its preceding user question."""
    answer_message = None
    question_for_answer = ""
    last_user_text = ""
    for message in messages:
        role = str(getattr(message, "role", "") or "")
        content = str(getattr(message, "content", "") or "").strip()
        if role == "user":
            last_user_text = content
        elif role == "assistant" and content:
            answer_message = message
            question_for_answer = last_user_text
    return answer_message, question_for_answer


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    conversation_id = str(request.conversation_id or "").strip()
    if not conversation_id:
        return _message(
            "Chưa xác định được hội thoại đang mở nên chưa chấm điểm được. "
            "Hãy mở một hội thoại rồi hỏi lại."
        )

    from aios_habit.workspace_chat_store import load_message_trace, load_messages

    try:
        messages = load_messages(conversation_id)
    except Exception:
        return _message("Chưa đọc được nội dung hội thoại lúc này. Bạn thử lại sau nhé.")

    answer_message, question_text = _latest_answer_messages(messages)
    if answer_message is None:
        return _message(
            "Hội thoại này chưa có câu trả lời nào để đánh giá. "
            "Hãy đặt một câu hỏi trước rồi hỏi lại tôi."
        )

    answer_text = str(getattr(answer_message, "content", "") or "").strip()
    trace = None
    try:
        trace = load_message_trace(str(getattr(answer_message, "id", "") or ""))
        trace_id = str(getattr(answer_message, "trace_id", "") or "").strip()
        if trace is None and trace_id:
            from aios_habit.workspace_chat_store import load_evidence_trace

            trace = load_evidence_trace(trace_id)
    except Exception:
        trace = None

    nodes = _evidence_nodes(trace)

    try:
        evaluator_rows, evaluator_result = _panel_evaluator(answer_text, nodes)
    except Exception:
        return _message("Chưa chấm được điểm chất lượng trả lời lúc này. Bạn thử lại sau nhé.")

    rubric_rows: list[tuple[str, str]] = []
    rubric_total: Optional[float] = None
    try:
        rubric_rows, rubric_total = _panel_rubric(answer_text, nodes, trace)
    except Exception:
        rubric_total = None

    blocks: list[ChatActionBlock] = [
        ChatActionBlock(
            BLOCK_MARKDOWN,
            text=(
                "Chấm điểm **câu trả lời mới nhất** trong hội thoại.\n\n"
                f"- Câu hỏi: {_excerpt(question_text) or '(không rõ)'}\n"
                f"- Trả lời: {_excerpt(answer_text)}"
            ),
        ),
        ChatActionBlock(
            BLOCK_TABLE,
            headers=("Chỉ số bằng chứng", "Điểm"),
            rows=evaluator_rows,
            caption="Tầng 1 — `rag_evaluator` trên dấu vết bằng chứng của câu trả lời.",
        ),
    ]

    if rubric_total is not None:
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("Tiêu chí rubric MOM", "Điểm"),
                rows=rubric_rows,
                caption=f"Tầng 2 — rubric `mom_benchmark`; tổng có trọng số: {rubric_total}/100.",
            )
        )

    notes = [_HEURISTIC_NOTE]
    if not nodes:
        notes.append(
            "Không tìm thấy dấu vết bằng chứng (EvidenceTrace) cho câu trả lời này — "
            "các chỉ số bằng chứng chỉ mang tính tham khảo."
        )
    else:
        metadata_rate = float(getattr(evaluator_result, "metadata_only_rate", 0.0) or 0.0)
        groundedness = float(getattr(evaluator_result, "answer_groundedness", 0.0) or 0.0)
        if metadata_rate >= 1.0:
            notes.append(
                "Toàn bộ mục bằng chứng chỉ có metadata, không có nội dung trích dẫn để đối chiếu."
            )
        elif groundedness < 0.3:
            notes.append(
                "Câu trả lời ít trùng từ ngữ với bằng chứng trích dẫn — nên kiểm tra lại nguồn trước khi dùng."
            )

        bench_query = str(getattr(trace, "query", "") or "").strip() or question_text
        if bench_query:
            try:
                blocks.append(
                    ChatActionBlock(
                        BLOCK_TABLE,
                        headers=("Tự kiểm tra truy xuất", "Giá trị"),
                        rows=_panel_retrieval(bench_query, nodes),
                        caption=(
                            "Tầng 3 — `rag_benchmark` chạy trong bộ nhớ trên chính các đoạn bằng chứng "
                            "đã trích dẫn (ngưỡng mặc định của công cụ)."
                        ),
                    )
                )
            except Exception:
                notes.append("Chưa chạy được phần tự kiểm tra truy xuất lúc này.")
        else:
            notes.append("Thiếu câu hỏi gốc nên chưa chạy được phần tự kiểm tra truy xuất.")

    notes.append(_RUBRIC_NOTE)
    blocks.append(ChatActionBlock(BLOCK_MARKDOWN, text="\n".join(f"- {note}" for note in notes)))

    return ChatActionOutcome(action=ACTION_NAME, title=ACTION_TITLE, blocks=tuple(blocks))


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Chấm điểm câu trả lời mới nhất của hội thoại theo bằng chứng (rag_evaluator), "
                "rubric MOM (mom_benchmark) và tự kiểm tra truy xuất (rag_benchmark)."
            ),
        )
    )


register()
