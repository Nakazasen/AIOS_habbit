"""Builtin chat action: Tạo vụ điều tra lỗi qua chat (DESKTOP-CASE-CREATE-FLOW).

Two-phase flow:
- Phase 1: The user types an investigation intent ("Tạo vụ điều tra lỗi mới: máy in báo
  lỗi kẹt giấy ở line 3"). The action returns a Preview Card inside the answer bubble
  with extracted fields (phenomenon, line, machine_type, error_code) and a confirmation
  button "Xác nhận tạo vụ".
- Phase 2: When the user confirms (clicking button or typing confirmation), the action
  calls `create_quick_case_with_evidence` in `case_store.py` to persist the case into
  `local_cases/cases.jsonl` (generating a CASE-XXXX id), then automatically runs Step 1
  `search_similar` from `chat_action_error_lookup.py` to display the top 3-5 similar
  historical cases with inline feedback hints inside the same bubble.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    register_action,
)

ACTION_NAME = "tao_vu_dieu_tra"
TITLE = "Tạo vụ điều tra lỗi"

_HINTS = (
    "tao vu dieu tra",
    "tao ho so dieu tra",
    "lap vu dieu tra",
    "mo vu dieu tra",
    "tao ca loi",
    "ghi nhan loi",
    "bao loi moi",
    "su co line",
    "loi line",
)

CASE_PREVIEW_TAG = "aios_case_preview"
_PREVIEW_RE = re.compile(
    r"<!--\s*aios_case_preview\s*:\s*(\{.*?\})\s*-->", re.DOTALL
)


def case_preview_marker(data: Dict[str, Any]) -> str:
    """HTML comment marker embedded into the preview markdown bubble."""
    return "<!-- %s: %s -->" % (
        CASE_PREVIEW_TAG,
        json.dumps(data, ensure_ascii=False),
    )


def extract_case_preview_marker(content: str) -> Optional[Dict[str, Any]]:
    """Extract case preview payload from message content, or None if absent."""
    match = _PREVIEW_RE.search(str(content or ""))
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError):
        return None


def strip_case_preview_marker(content: str) -> str:
    """Remove preview marker before rendering markdown body."""
    return _PREVIEW_RE.sub("", str(content or "")).strip()


def render_preview_card_text(
    text: str,
    slots: Dict[str, Any],
    conversation_id: str = "",
    notebook_id: str = "",
) -> str:
    """Generate Phase 1 Preview Card markdown containing extracted entities and metadata marker."""
    from aios_habit.chat_intent_router import extract_case_entities

    entities = dict(slots) if slots else extract_case_entities(text)
    phenomenon = str(entities.get("phenomenon") or "").strip() or "Sự cố sản xuất chưa rõ hiện tượng"
    line = str(entities.get("line") or "").strip()
    machine_type = str(entities.get("machine_type") or "").strip()
    error_code = str(entities.get("error_code") or "").strip()

    preview_id = f"PREV-{uuid.uuid4().hex[:8].upper()}"
    marker_payload = {
        "preview_id": preview_id,
        "phenomenon": phenomenon,
        "line": line,
        "machine_type": machine_type,
        "error_code": error_code,
        "conversation_id": conversation_id,
        "notebook_id": notebook_id,
        "raw_text": text,
    }

    lines = [
        "### 📋 Thẻ Xem Trước Vụ Điều Tra",
        "",
        "Hệ thống đã nhận diện các thông tin ban đầu từ yêu cầu của bạn:",
        "",
        f"- **Hiện tượng:** {phenomenon}",
        f"- **Dây chuyền:** {line if line else 'Chưa rõ (sẽ cập nhật trong điều tra)'}",
        f"- **Model máy:** {machine_type if machine_type else 'Chưa rõ (sẽ cập nhật trong điều tra)'}",
        f"- **Mã lỗi:** {error_code if error_code else 'Chưa có (hệ thống sẽ tra cứu theo hiện tượng)'}",
        "- **Trạng thái:** Chờ xác nhận tạo vụ",
        "",
        "_Bấm nút **Xác nhận tạo vụ** bên dưới để lưu hồ sơ và tự động tra cứu ca tương tự Bước 1._",
        "",
        case_preview_marker(marker_payload),
    ]
    return "\n".join(lines)


def execute_confirm_case(
    preview_data: Dict[str, Any],
    conversation_id: str = "",
) -> str:
    """Phase 2: Save case into local_cases/cases.jsonl, run search_similar, return complete bubble."""
    from aios_habit.case_store import create_quick_case_with_evidence
    from aios_habit.chat_action import ChatActionRequest
    from aios_habit.chat_action_error_lookup import (
        _log_suggestion_call,
        _open_ro,
        _render_cards,
        extract_codes,
        lookup_glossary,
        resolve_db_path,
        search_similar,
    )

    phenomenon = str(preview_data.get("phenomenon") or "").strip() or "Sự cố kẹt giấy"
    line = str(preview_data.get("line") or "").strip()
    machine_type = str(preview_data.get("machine_type") or "").strip()
    error_code = str(preview_data.get("error_code") or "").strip()

    # 1. Save case using built-in create_quick_case_with_evidence
    title_parts = []
    if machine_type:
        title_parts.append(machine_type)
    title_parts.append(phenomenon)
    if line:
        title_parts.append(f"({line})")
    title = "Sự cố " + " - ".join(title_parts)

    situation_parts = [f"Hiện tượng: {phenomenon}"]
    if line:
        situation_parts.append(f"Dây chuyền: {line}")
    if machine_type:
        situation_parts.append(f"Model: {machine_type}")
    if error_code:
        situation_parts.append(f"Mã lỗi: {error_code}")
    situation = ". ".join(situation_parts) + "."

    saved = create_quick_case_with_evidence(
        title=title,
        situation=situation,
        priority="normal",
        privacy="local_only",
        notes="Tạo tự động qua Workspace Chat.",
    )
    case_id = str(saved.get("case_id") or "")

    # 2. Run Step 1 search_similar
    search_query = f"{error_code} {phenomenon}".strip()
    req = ChatActionRequest(
        question=search_query,
        conversation_id=conversation_id or str(preview_data.get("conversation_id") or ""),
    )
    db_path = resolve_db_path(req)
    cards_text = ""
    if db_path is not None and db_path.is_file():
        try:
            conn = _open_ro(db_path)
            try:
                codes = extract_codes(search_query)
                glossary = lookup_glossary(conn, codes)
                extra: List[str] = []
                for c in codes:
                    entry = glossary.get(c, {})
                    extra.extend(
                        str(entry.get(k) or "")
                        for k in ("name_vi", "name_ja", "name_en", "cause", "remedy")
                    )
                cases, codes, total = search_similar(conn, search_query, extra_keywords=extra)
                if cases:
                    cards_text = _render_cards(cases, codes, glossary, total)
                    _log_suggestion_call(db_path, cases, req.conversation_id or "")
            finally:
                conn.close()
        except Exception:
            cards_text = ""

    header_lines = [
        f"### ✅ Đã tạo thành công vụ điều tra `{case_id}`",
        "",
        f"- **Mã vụ:** `{case_id}`",
        f"- **Hiện tượng:** {phenomenon}",
    ]
    if line:
        header_lines.append(f"- **Dây chuyền:** {line}")
    if machine_type:
        header_lines.append(f"- **Model máy:** {machine_type}")
    if error_code:
        header_lines.append(f"- **Mã lỗi:** {error_code}")
    header_lines.extend([
        "- **Trạng thái:** Đang điều tra (`investigating`)",
        "- **Kho lưu trữ:** `local_cases/cases.jsonl`",
        "",
        "---",
        "",
        "### 🔍 Bước 1: Tra cứu ca lỗi tương tự trong lịch sử KDTPS",
        "",
    ])

    if cards_text:
        return "\n".join(header_lines) + cards_text
    else:
        header_lines.extend([
            "_Chưa tìm thấy ca lỗi tương tự trong lịch sử hoặc DB chưa khả dụng._",
            "",
            "---",
            "**Đánh giá gợi ý này:** `đánh giá đúng` · `đánh giá sai` · `đánh giá một phần`",
            "_Gõ ngay trong ô chat — không cần mở thêm gì._",
        ])
        return "\n".join(header_lines)


def render_case_preview_widget(
    st_ctx: Any,
    preview_data: Dict[str, Any],
    conversation_id: str = "",
    message_id: str = "",
) -> None:
    """Render confirmation button inline in the chat bubble for Streamlit."""
    preview_id = str(preview_data.get("preview_id", "") or "")
    confirmed_key = f"wsc_case_confirmed_{preview_id}"
    session_state = getattr(st_ctx, "session_state", {})
    if session_state.get(confirmed_key):
        return

    btn_key = f"btn_confirm_case_{preview_id}_{message_id}"
    if st_ctx.button("Xác nhận tạo vụ", key=btn_key, type="primary"):
        outcome_text = execute_confirm_case(
            preview_data=preview_data,
            conversation_id=conversation_id,
        )
        if message_id:
            try:
                from aios_habit.workspace_chat_store import (
                    MESSAGES_FILE,
                    atomic_write_jsonl,
                    load_all_messages,
                )

                all_msgs = load_all_messages()
                for item in all_msgs:
                    if item.id == message_id:
                        item.content = outcome_text
                        break
                atomic_write_jsonl(MESSAGES_FILE, all_msgs)
            except Exception:
                pass
        if hasattr(st_ctx, "session_state"):
            st_ctx.session_state[confirmed_key] = True
        if hasattr(st_ctx, "rerun"):
            st_ctx.rerun()


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    """ChatAction handler for tao_vu_dieu_tra."""
    text = render_preview_card_text(
        request.question,
        slots={},
        conversation_id=request.conversation_id or "",
        notebook_id=request.notebook_id or "",
    )
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=TITLE,
        blocks=(ChatActionBlock(kind=BLOCK_MARKDOWN, text=text),),
    )


def register() -> None:
    register_action(
        ChatAction(
            name=ACTION_NAME,
            title=TITLE,
            hints=_HINTS,
            handler=_handler,
            fallback=False,
            description="Tạo vụ điều tra lỗi mới qua chat và tra cứu tương tự Bước 1.",
        )
    )


register()
