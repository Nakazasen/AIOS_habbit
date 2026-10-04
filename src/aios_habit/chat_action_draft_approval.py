"""Builtin chat action: list unapproved drafts inside the answer bubble.

Matches the user asking "liet ke ban thao chua duyet [ve X]" and renders
the pending list right in the reply area (no separate screen).
Read-only over the draft store + approval log; never writes production.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)

ACTION_NAME = "liet_ke_ban_thao_chua_duyet"
ACTION_TITLE = "Liệt kê bản thảo chưa duyệt"

_HINTS = (
    "liet ke ban thao chua duyet",
    "ban thao chua duyet",
    "danh sach ban thao chua duyet",
)


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _draft_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "phieu-viec" / "chatgpt-enrichment-fixed"
        if candidate.exists():
            return candidate
    return Path.cwd() / "docs" / "phieu-viec" / "chatgpt-enrichment-fixed"


def _excerpt(text: str, limit: int = 90) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    from aios_habit import answer_draft_fallback as fallback
    from aios_habit import draft_approval as approval

    if not approval.draft_approval_enabled():
        return None
    normalized = request.normalized_question
    if "ban thao chua duyet" not in normalized and "liet ke ban thao" not in normalized:
        return None
    root = _draft_root()
    entries = fallback.load_draft_entries(root) if root.exists() else []
    # Optional topic after the command ("... về X").
    topic = normalized
    for marker in ("liet ke ban thao chua duyet", "ban thao chua duyet"):
        if marker in topic:
            topic = topic.split(marker, 1)[1]
            break
    topic = topic.replace("ve", " ", 1).strip() if topic.strip().startswith("ve ") else topic.strip()
    if topic.startswith("ve "):
        topic = topic[3:].strip()
    if topic:
        entries = [e for e in entries if topic in normalize_text(e.question)] or entries
        entries = entries[:20]
    else:
        entries = entries[:20]
    decisions = approval.read_decisions()
    latest: dict[str, dict] = {}
    for item in decisions:
        pid = str(item.get("pair_id", "") or "").strip()
        if pid:
            latest[pid] = item
    approved_ids = {
        pid
        for pid, rec in latest.items()
        if str(rec.get("decision", "")) in ("approved", "revised")
    }
    rejected_ids = {
        pid for pid, rec in latest.items() if str(rec.get("decision", "")) == "rejected"
    }
    rows: list[tuple[str, str, str]] = []
    for entry in entries:
        pid = f"{entry.source_file}#{entry.position}"
        if pid in approved_ids or pid in rejected_ids:
            continue
        rows.append((pid, _excerpt(entry.question), _excerpt(entry.answer, 80)))
        if len(rows) >= 15:
            break
    if not rows:
        return _message("Không còn bản thảo chưa duyệt.")
    metrics = approval.compute_approval_metrics(
        decisions, total_tracked=len(entries) or len(rows)
    )
    caption = (
        f"Tỉ lệ duyệt: {metrics.approved}/{metrics.total_tracked} "
        f"({round(metrics.approval_rate * 100)}%) · "
        f"Từ chối: {metrics.rejected} · Chưa duyệt: {metrics.pending}"
    )
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(
            ChatActionBlock(
                BLOCK_MARKDOWN,
                text=f"**Bản thảo chưa duyệt** (hiển thị {len(rows)} cặp đầu tiên).",
            ),
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("Mã cặp", "Câu hỏi", "Trích đáp"),
                rows=rows,
                caption=caption,
            ),
        ),
    )


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description="Liệt kê bản thảo chưa duyệt ngay trong vùng trả lời.",
        )
    )


register()
