from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol

MAX_PREVIEW_CHARS_PER_SOURCE = 300
MAX_SOURCES_IN_ANSWER = 20

class WorkspacePreviewSourceLike(Protocol):
    id: str
    source_type: str
    title: str
    content_preview: str
    content_text: str

@dataclass(frozen=True)
class WorkspaceTrialSourcePreview:
    source_id: str
    source_scope: str
    source_type: str
    title: str
    preview: str

@dataclass(frozen=True)
class WorkspaceTrialAnswerPreview:
    question: str
    answer_text: str
    enabled_sources: tuple[WorkspaceTrialSourcePreview, ...]

@dataclass(frozen=True)
class WorkspaceTrialSourceInput:
    source_id: str
    source_scope: str
    source_type: str
    title: str
    content_preview: str = ""
    content_text: str = ""

def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def _cap_preview(value: str) -> str:
    normalized = _normalize_whitespace(value)
    if len(normalized) <= MAX_PREVIEW_CHARS_PER_SOURCE:
        return normalized
    return normalized[:MAX_PREVIEW_CHARS_PER_SOURCE].rstrip()

def _friendly_source_type(source_type: str) -> str:
    normalized = (source_type or "").strip().lower()
    if normalized == "xlsx":
        return "Excel"
    if normalized in {"text", "pasted_text", "plain_text"}:
        return "Văn bản"
    return "Nguồn"

def _source_input_from_any(source: WorkspaceTrialSourceInput | WorkspacePreviewSourceLike) -> WorkspaceTrialSourceInput:
    if isinstance(source, WorkspaceTrialSourceInput):
        return source
    return WorkspaceTrialSourceInput(
        source_id=getattr(source, "id", ""),
        source_scope=getattr(source, "source_scope", ""),
        source_type=getattr(source, "source_type", ""),
        title=getattr(source, "title", ""),
        content_preview=getattr(source, "content_preview", ""),
        content_text=getattr(source, "content_text", ""),
    )

def build_trial_answer_preview(
    question: str,
    enabled_sources: Iterable[WorkspaceTrialSourceInput | WorkspacePreviewSourceLike],
) -> WorkspaceTrialAnswerPreview:
    normalized_question = _normalize_whitespace(question)
    source_inputs = tuple(_source_input_from_any(source) for source in enabled_sources)
    visible_source_inputs = source_inputs[:MAX_SOURCES_IN_ANSWER]
    source_previews: list[WorkspaceTrialSourcePreview] = []
    answer_lines = [
        "Chỉ xem trước trên máy",
        "",
        "AIOS chưa nối AI thật ở bước này.",
        "",
        "Câu hỏi hiện tại:",
        normalized_question,
        "",
    ]
    if not source_inputs:
        answer_lines.extend([
            "Chưa có nguồn nào đang bật cho cuộc trò chuyện này.",
            "",
            "Đây chưa phải câu trả lời phân tích cuối cùng.",
        ])
        return WorkspaceTrialAnswerPreview(normalized_question, "\n".join(answer_lines), ())
    answer_lines.append("Nguồn đang bật cho cuộc trò chuyện:")
    for source in visible_source_inputs:
        preview_text = _cap_preview(source.content_preview or source.content_text)
        friendly_type = _friendly_source_type(source.source_type)
        title = _normalize_whitespace(source.title) or "Nguồn chưa đặt tên"
        source_previews.append(WorkspaceTrialSourcePreview(source.source_id, source.source_scope, friendly_type, title, preview_text))
        answer_lines.append(f"- {title} · {friendly_type}")
        if preview_text:
            answer_lines.append(f"  Đoạn xem trước sẽ dùng ở bước sau: {preview_text}")
        else:
            answer_lines.append("  Đoạn xem trước sẽ dùng ở bước sau: chưa có nội dung xem trước.")
    hidden_count = len(source_inputs) - len(visible_source_inputs)
    if hidden_count > 0:
        answer_lines.append(f"Còn {hidden_count} nguồn đang bật chưa hiển thị trong bản xem trước.")
    answer_lines.extend(["", "Đây chưa phải câu trả lời phân tích cuối cùng."])
    return WorkspaceTrialAnswerPreview(normalized_question, "\n".join(answer_lines), tuple(source_previews))
