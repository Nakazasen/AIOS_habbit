"""Draft fallback for Workspace Chat answers (ticket ANSWER-DRAFT-FALLBACK).

Priority: (a) RAG answer as-is, (b) draft store fallback with label only when
RAG cannot answer, (c) honest not-found message, never invent an answer.

The draft store is the audited ``docs/phieu-viec/chatgpt-enrichment-fixed/``
markdown files (54 files). They are read as plain text (Hoi/Dap pairs) and
never go through ``golden_answer_importer`` or the production index.

Feature flag ``AIOS_FEATURE_ANSWER_DRAFT_FALLBACK`` defaults to ON per the
explicit user request on 2026-10-04 (turning it off restores legacy RAG-only
behaviour). Feedback reuses ``answer_feedback`` (local_cases only, never the
knowledge store).

Compatible with Python 3.11.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

# Mandatory label shown inside every draft-sourced answer (non-negotiable).
DRAFT_LABEL = "Bản thảo — chưa qua chuyên gia duyệt"

# Honest answer when neither RAG nor the draft store can help.
NOT_FOUND_MESSAGE = (
    "Tôi không tìm thấy trong tài liệu có nội dung trả lời câu hỏi này."
)

# Env flag name. Default ON per user decision 2026-10-04 (exception to the
# usual default-off convention, documented here and in the ticket report).
FLAG_ENV_KEY = "AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"

# In-memory override for tests (no global registry side effects).
_overrides: Dict[str, bool] = {}

# RAG outcomes that mean "RAG could not answer".
_RAG_FAILURE_OUTCOMES = frozenset({"insufficient_evidence", "provider_error"})

# Confidence labels that mean "RAG could not answer".
_WEAK_CONFIDENCE = frozenset(
    {"low", "insufficient", "insufficient_evidence", "no_evidence"}
)

# Folded markers meaning the RAG text itself admits it has no answer.
_RAG_ADMITS_UNKNOWN_MARKERS = (
    "khong tim thay",
    "chua tim thay",
    "chua du thong tin",
    "khong du thong tin",
    "chua du bang chung",
    "khong du bang chung",
    "khong co thong tin",
    "chua co thong tin",
    "chua co nguon nao",
    "khong co nguon nao",
    "chua co tai lieu nao",
    "khong co tai lieu nao",
)


def set_draft_fallback_override(enabled: bool) -> None:
    """Set an in-memory flag override (used by tests)."""
    _overrides["enabled"] = bool(enabled)


def clear_draft_fallback_override() -> None:
    """Clear the in-memory flag override."""
    _overrides.pop("enabled", None)


def draft_fallback_enabled() -> bool:
    """Return True when the draft fallback lane is enabled (default ON)."""
    if "enabled" in _overrides:
        return _overrides["enabled"]
    raw = os.environ.get(FLAG_ENV_KEY, "")
    if not raw.strip():
        return True
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _fold(value: str) -> str:
    normalized = unicodedata.normalize(
        "NFKD", (value or "").casefold().replace("đ", "d")
    )
    folded = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    return " ".join(folded.split())


def _tokenize(value: str) -> List[str]:
    return [t for t in re.findall(r"[\w]+", _fold(value), re.UNICODE) if len(t) > 1]


def is_rag_usable(
    *,
    rag_ok: bool,
    answer_text: str = "",
    outcome_status: str = "",
    confidence_label: str = "",
    abstained: bool = False,
) -> bool:
    """Decide whether the RAG answer is good enough to show directly."""
    if abstained:
        return False
    if not rag_ok:
        return False
    text = (answer_text or "").strip()
    if not text:
        return False
    if (outcome_status or "").strip() in _RAG_FAILURE_OUTCOMES:
        return False
    if (confidence_label or "").strip().lower() in _WEAK_CONFIDENCE:
        return False

    # Check for structured template: if the answer contains a boilerplate
    # "Điểm chưa đủ bằng chứng" caveat header, inspect the main substantive
    # answer part preceding that header. This prevents high-quality answers
    # (like ctrlMode) with standard caveat sections from being falsely rejected.
    text_to_check = text
    caveat_splits = re.split(r"##\s*điểm chưa đủ bằng chứng", text, flags=re.IGNORECASE)
    if len(caveat_splits) > 1 and caveat_splits[0].strip():
        text_to_check = caveat_splits[0].strip()

    folded = _fold(text_to_check)
    for marker in _RAG_ADMITS_UNKNOWN_MARKERS:
        if marker in folded:
            return False
    return True


@dataclass(frozen=True)
class DraftEntry:
    """One Hoi/Dap pair parsed from a fixed markdown file."""

    question: str
    answer: str
    source_file: str = ""
    position: int = 0


def parse_draft_text(text: str, source_file: str = "") -> List[DraftEntry]:
    """Parse ``## CÂU HỎI`` blocks with ``Hỏi:``/``Đáp:`` lines."""
    entries: List[DraftEntry] = []
    blocks = re.split(r"^##\s*CÂU HỎI.*$", text or "", flags=re.MULTILINE)
    position = 0
    for block in blocks:
        question = ""
        answer = ""
        for raw_line in block.splitlines():
            line = raw_line.strip().lstrip("-* \t")
            lowered = _fold(line[:6])
            if lowered.startswith("hoi:"):
                question = raw_line.split(":", 1)[1].strip() if ":" in raw_line else ""
            elif lowered.startswith("dap:"):
                answer = raw_line.split(":", 1)[1].strip() if ":" in raw_line else ""
            elif lowered.startswith("hoi ") or lowered.startswith("dap "):
                # Tolerate missing colon ("Hỏi ...").
                payload = line[3:].strip().lstrip(":").strip()
                if lowered.startswith("hoi ") and not question:
                    question = payload
                elif lowered.startswith("dap ") and not answer:
                    answer = payload
        if question and answer:
            position += 1
            entries.append(
                DraftEntry(
                    question=question,
                    answer=answer,
                    source_file=source_file,
                    position=position,
                )
            )
    return entries


def load_draft_entries(root: str | Path) -> List[DraftEntry]:
    """Load all draft pairs under ``root`` (expects ``mom/`` + ``lsu/``)."""
    base = Path(root)
    entries: List[DraftEntry] = []
    if not base.exists():
        return entries
    files = sorted(base.rglob("*.md"))
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = str(path.relative_to(base))
        except ValueError:
            rel = path.name
        entries.extend(parse_draft_text(text, source_file=rel))
    return entries


def search_drafts(
    question: str,
    entries: Sequence[DraftEntry],
    *,
    top_k: int = 1,
    min_overlap: int = 2,
) -> List[DraftEntry]:
    """Find draft entries sharing the most content tokens with the question."""
    query_tokens = set(_tokenize(question))
    if not query_tokens:
        return []
    folded_query = _fold(question)
    scored: List[tuple[int, int, DraftEntry]] = []
    for entry in entries:
        entry_tokens = set(_tokenize(entry.question))
        overlap = len(query_tokens & entry_tokens)
        bonus = 0
        folded_entry = _fold(entry.question)
        if folded_query and folded_query in folded_entry:
            bonus += 3
        elif folded_entry and folded_entry in folded_query:
            bonus += 2
        score = overlap + bonus
        if overlap >= min_overlap or bonus >= 2:
            scored.append((score, entry.position, entry))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if top_k <= 0:
        return []
    return [entry for _, _, entry in scored[:top_k]]


@dataclass(frozen=True)
class FallbackDecision:
    """Result of the a -> b -> c decision chain."""

    lane: str  # "rag" | "draft_fallback" | "not_found"
    answer_text: str
    draft_question: str = ""
    draft_source: str = ""
    has_draft_label: bool = False


def format_draft_answer(entry: DraftEntry) -> str:
    """Render a draft answer with the mandatory label inside the text."""
    body = (entry.answer or "").strip()
    return f"{body}\n\n{DRAFT_LABEL}"


def resolve_answer(
    question: str,
    *,
    rag_ok: bool,
    rag_answer: str = "",
    outcome_status: str = "",
    confidence_label: str = "",
    abstained: bool = False,
    draft_entries: Sequence[DraftEntry] = (),
    enabled: bool | None = None,
) -> FallbackDecision:
    """Apply the a -> b -> c chain without touching the RAG path itself."""
    flag_on = draft_fallback_enabled() if enabled is None else bool(enabled)
    if not flag_on:
        # Flag off restores legacy behaviour exactly: return RAG as-is.
        return FallbackDecision(lane="rag", answer_text=rag_answer or "")
    if is_rag_usable(
        rag_ok=rag_ok,
        answer_text=rag_answer,
        outcome_status=outcome_status,
        confidence_label=confidence_label,
        abstained=abstained,
    ):
        return FallbackDecision(lane="rag", answer_text=(rag_answer or "").strip())
    hits = search_drafts(question, draft_entries, top_k=1)
    if hits:
        best = hits[0]
        return FallbackDecision(
            lane="draft_fallback",
            answer_text=format_draft_answer(best),
            draft_question=best.question,
            draft_source=best.source_file,
            has_draft_label=True,
        )
    return FallbackDecision(lane="not_found", answer_text=NOT_FOUND_MESSAGE)


@dataclass(frozen=True)
class FallbackMetrics:
    """Measurable lane metrics for the periodic review loop."""

    total: int = 0
    rag_count: int = 0
    draft_count: int = 0
    not_found_count: int = 0
    correct_count: int = 0
    coverage: float = 0.0
    fallback_rate: float = 0.0
    draft_label_rate: float = 0.0


def compute_fallback_metrics(records: Sequence[Dict]) -> FallbackMetrics:
    """Compute coverage / fallback rate / draft label rate from lane records.

    Each record needs ``lane`` (rag/draft_fallback/not_found), ``correct``
    (bool) and, for draft lanes, ``has_draft_label`` (bool).
    """
    items = list(records or [])
    total = len(items)
    if not total:
        return FallbackMetrics()
    rag_count = sum(1 for r in items if r.get("lane") == "rag")
    draft_count = sum(1 for r in items if r.get("lane") == "draft_fallback")
    not_found_count = sum(1 for r in items if r.get("lane") == "not_found")
    correct_count = sum(1 for r in items if bool(r.get("correct")))
    labeled = sum(
        1
        for r in items
        if r.get("lane") == "draft_fallback" and bool(r.get("has_draft_label"))
    )
    return FallbackMetrics(
        total=total,
        rag_count=rag_count,
        draft_count=draft_count,
        not_found_count=not_found_count,
        correct_count=correct_count,
        coverage=round(correct_count / total, 3),
        fallback_rate=round(draft_count / total, 3),
        draft_label_rate=round((labeled / draft_count), 3) if draft_count else 0.0,
    )


def review_recommendations(metrics: FallbackMetrics) -> List[str]:
    """Short Vietnamese review hints used by the periodic metric review."""
    hints: List[str] = []
    if metrics.total == 0:
        return ["Chưa có mẫu đo. Hãy chạy bộ câu hỏi mẫu rồi đo lại."]
    if metrics.coverage < 0.8:
        hints.append(
            "Độ bao phủ dưới 80%. Hãy bổ sung bản thảo cho nhóm câu hỏi bị trượt."
        )
    if metrics.fallback_rate > 0.3:
        hints.append(
            "Tỉ lệ dùng bản thảo trên 30%. Hãy kiểm tra lại kho tài liệu chính."
        )
    if metrics.draft_count and metrics.draft_label_rate < 1.0:
        hints.append(
            "Có câu trả lời bản thảo thiếu nhãn. Phải sửa ngay cho đủ 100%."
        )
    if not hints:
        hints.append("Số liệu ổn. Giữ nhịp xem lại định kỳ.")
    return hints


# Periodic review helper: where the metrics come from and when to act.
REVIEW_GUIDE_VI = (
    "Cách xem lại định kỳ: thu thập phản hồi tại chỗ trong "
    "local_cases/answer_feedback.jsonl, chạy compute_fallback_metrics trên bộ "
    "câu hỏi mẫu (gồm cả câu hỏi dị dạng và diễn đạt lại), rồi đọc "
    "review_recommendations. Ngưỡng cần cải thiện: độ bao phủ dưới 80%, "
    "tỉ lệ dùng bản thảo trên 30%, hoặc nhãn bản thảo dưới 100%."
)


# Caching for default draft entries loaded from docs/phieu-viec/chatgpt-enrichment-fixed/
_CACHED_ENTRIES: List[DraftEntry] | None = None


def clear_cached_draft_entries() -> None:
    """Clear cached draft entries in memory (for test isolation)."""
    global _CACHED_ENTRIES
    _CACHED_ENTRIES = None


def get_default_draft_entries(root: str | Path | None = None) -> List[DraftEntry]:
    """Retrieve all draft entries with in-memory caching."""
    global _CACHED_ENTRIES
    if root is None and _CACHED_ENTRIES is not None:
        return _CACHED_ENTRIES

    target_root: Path | None = None
    if root is not None:
        target_root = Path(root)
    else:
        candidates = [
            Path("docs/phieu-viec/chatgpt-enrichment-fixed"),
            Path(__file__).resolve().parents[2] / "docs" / "phieu-viec" / "chatgpt-enrichment-fixed",
            Path.cwd() / "docs" / "phieu-viec" / "chatgpt-enrichment-fixed",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                target_root = c
                break
        if target_root is None:
            target_root = Path("docs/phieu-viec/chatgpt-enrichment-fixed")

    entries = load_draft_entries(target_root)
    if root is None:
        _CACHED_ENTRIES = entries
    return entries


def log_draft_fallback_activation(
    *,
    question: str,
    draft_source: str,
    draft_question: str,
    conversation_id: str = "",
    message_id: str = "",
    base_dir: str | Path | None = None,
) -> Path:
    """Record an activation of the draft fallback mechanism into local_cases (never KB)."""
    base = Path(base_dir) if base_dir is not None else (Path.cwd() / "local_cases")
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / "draft_fallback_activations.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "conversation_id": conversation_id,
        "message_id": message_id,
        "question": question,
        "draft_source": draft_source,
        "draft_question": draft_question,
        "has_draft_label": True,
        "lane": "draft_fallback",
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return log_path


def count_draft_fallback_activations(base_dir: str | Path | None = None) -> int:
    """Count the total number of draft fallback activations logged in local_cases."""
    base = Path(base_dir) if base_dir is not None else (Path.cwd() / "local_cases")
    log_path = base / "draft_fallback_activations.jsonl"
    if not log_path.exists():
        return 0
    count = 0
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def deliver_draft_answer(
    question: str,
    *,
    conversation_id: str,
    notebook_id: str = "",
    user_raw_input: str = "",
    user_message_id: str = "",
    current_ui_locale: str = "vi",
    answer_language: str = "vi",
    on_chunk: Any = None,
    draft_entries: Sequence[DraftEntry] | None = None,
    enabled: bool | None = None,
    base_cases_dir: str | Path | None = None,
) -> tuple[bool, str, dict[str, Any] | None, str | None] | None:
    """Attempt to resolve and deliver a draft answer directly to DB and UI.

    Returns:
        (ok, success_message, badge, error_message) if draft resolved and delivered,
        or None if draft fallback is disabled, unselected, or not matched.
    """
    entries = draft_entries if draft_entries is not None else get_default_draft_entries()
    decision = resolve_answer(
        question,
        rag_ok=False,
        draft_entries=entries,
        enabled=enabled,
    )
    if decision.lane != "draft_fallback":
        return None

    if on_chunk and decision.answer_text:
        try:
            on_chunk(decision.answer_text)
        except Exception:
            pass

    from aios_habit.workspace_chat_models import ChatMessage
    from aios_habit.workspace_chat_store import (
        save_message,
        save_evidence_trace,
    )
    from aios_habit.antigravity_bridge import _get_or_create_user_message
    from aios_habit.evidence_trace import build_evidence_trace_from_citations

    user_msg = _get_or_create_user_message(
        conversation_id, user_raw_input or question, reuse_message_id=user_message_id
    )
    assistant_msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"

    trace = build_evidence_trace_from_citations(
        query=question,
        answer_text=decision.answer_text,
        evidence_items=[],
        allowed_source_ids=[],
        notebook_id=notebook_id,
        conversation_id=conversation_id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg_id,
        ui_locale=current_ui_locale,
        answer_language=answer_language,
        provenance={
            "operational_mode": "draft_fallback",
            "provider_name": "Bản thảo ChatGPT",
            "model_name": "chatgpt_enrichment_draft",
            "draft_source": decision.draft_source,
            "draft_question": decision.draft_question,
            "has_draft_label": True,
        },
    )
    save_evidence_trace(trace)
    save_message(
        ChatMessage(
            id=assistant_msg_id,
            conversation_id=conversation_id,
            role="assistant",
            content=decision.answer_text,
            trace_id=trace.trace_id,
        )
    )

    log_draft_fallback_activation(
        question=question,
        draft_source=decision.draft_source,
        draft_question=decision.draft_question,
        conversation_id=conversation_id,
        message_id=assistant_msg_id,
        base_dir=base_cases_dir,
    )

    badge = {
        "conversation_id": conversation_id,
        "type": "ai_answered",
        "source_count": 1,
        "source_titles": [decision.draft_source],
        "ai_source": "Bản thảo ChatGPT",
        "bridge": "Dự bị bản thảo",
        "provider": "Bản thảo ChatGPT",
        "model_tool_name": "",
        "verified_model": "draft_fallback",
        "operational_mode": "draft_fallback",
        "retrieval_summary": f"Sử dụng bản thảo dự bị từ {decision.draft_source}",
        "evidence_items": [],
        "trace_id": trace.trace_id,
        "fallback_used": True,
        "is_draft_fallback": True,
        "draft_source": decision.draft_source,
    }
    return (
        True,
        "Đã nhận câu trả lời từ kho bản thảo dự bị (chưa qua chuyên gia duyệt).",
        badge,
        None,
    )

