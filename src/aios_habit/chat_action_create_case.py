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


def format_case_status(status: str) -> str:
    """Format case status into Vietnamese readable label with exact raw status code."""
    raw = str(status or "").strip().lower()
    mapping = {
        "open": "Mở (`open`)",
        "investigating": "Đang điều tra (`investigating`)",
        "waiting": "Chờ xử lý (`waiting`)",
        "resolved": "Đã giải quyết (`resolved`)",
        "archived": "Đã lưu trữ (`archived`)",
    }
    if raw in mapping:
        return mapping[raw]
    return f"{status} (`{raw}`)" if raw else "Mở (`open`)"


def get_active_case_id() -> str:
    """Get active investigation case ID from current Streamlit session if active."""
    try:
        import streamlit as st

        return str(st.session_state.get("wsc_active_case_id") or "").strip()
    except Exception:
        return ""


def set_active_case_id(case_id: str) -> None:
    """Set active investigation case ID into current Streamlit session if active."""
    cid = str(case_id or "").strip()
    if not cid:
        return
    try:
        import streamlit as st

        st.session_state["wsc_active_case_id"] = cid
    except Exception:
        pass


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
    set_active_case_id(case_id)
    raw_status = str(saved.get("status") or "open")
    status_label = format_case_status(raw_status)

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
        f"- **Trạng thái:** {status_label}",
        f"- **Ngữ cảnh phiên:** Vụ **`{case_id}`** đã được đặt làm ngữ cảnh điều tra hiện tại.",
        "- **Kho lưu trữ:** `local_cases/cases.jsonl`",
        "",
        "💡 *Lệnh tiếp nối:* Gõ **`Xem tiến độ vụ này`** hoặc **`Lập cây 4M cho vụ này`** để tiếp tục.",
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


def execute_view_case_progress(
    case_id: Optional[str] = None,
    conversation_id: str = "",
) -> str:
    """Handle 'Xem tiến độ vụ này': returns real case status, phenomenon, creation time, fields present/missing."""
    from aios_habit.case_store import load_cases, load_evidence

    target_case_id = str(case_id or "").strip() or get_active_case_id()
    if not target_case_id and conversation_id:
        try:
            from aios_habit.workspace_chat_store import load_messages

            msgs = load_messages(conversation_id)
            for m in reversed(msgs):
                match = re.search(
                    r"\b(CASE-[A-Za-z0-9_-]+)\b", m.content or "", re.IGNORECASE
                )
                if match:
                    target_case_id = match.group(1).upper()
                    break
        except Exception:
            pass

    if not target_case_id:
        return (
            "### ⚠️ Chưa có vụ điều tra nào trong ngữ cảnh phiên chat\n\n"
            "Hệ thống chưa ghi nhận vụ điều tra nào đang hoạt động trong phiên này.\n\n"
            "Bạn có thể:\n"
            "- Tạo vụ mới bằng lệnh: `Tạo vụ điều tra lỗi mới: <mô tả hiện tượng>`\n"
            "- Hoặc chỉ định rõ mã vụ: `Xem tiến độ vụ CASE-XXXX`"
        )

    all_cases = load_cases()
    case = next((c for c in all_cases if c.case_id == target_case_id), None)
    if case is None:
        return (
            f"### ⚠️ Không tìm thấy vụ `{target_case_id}`\n\n"
            f"Vụ điều tra `{target_case_id}` không tồn tại trong kho lưu trữ `local_cases/cases.jsonl`."
        )

    set_active_case_id(target_case_id)
    status_label = format_case_status(case.status)
    phenomenon = case.current_situation or case.title

    all_evs = load_evidence()
    case_evs = [e for e in all_evs if e.case_id == target_case_id]
    ev_count = max(len(case_evs), len(case.evidence_items))

    hypo_count = len(case.hypotheses)
    hypo_text = f"Đã có {hypo_count} giả thuyết" if hypo_count > 0 else "Chưa có (còn trống)"

    actions_count = len(case.next_actions)
    actions_text = (
        f"Đã có {actions_count} hành động" if actions_count > 0 else "Chưa có (còn trống)"
    )

    decisions_count = len(case.decisions)
    decisions_text = (
        f"Đã có {decisions_count} quyết định" if decisions_count > 0 else "Chưa có (còn trống)"
    )

    outcome_text = (
        case.outcome.strip() if case.outcome.strip() else "Chưa có (còn trống)"
    )
    lessons_text = (
        case.lessons_learned.strip() if case.lessons_learned.strip() else "Chưa có (còn trống)"
    )

    created_str = case.created_at
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(case.created_at)
        created_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    lines = [
        f"### 📊 Tiến độ vụ điều tra `{case.case_id}`",
        "",
        f"📌 **Ngữ cảnh phiên:** Vụ **`{case.case_id}`**",
        "",
        "#### 1. Thông tin chung",
        f"- **Mã vụ:** `{case.case_id}`",
        f"- **Tiêu đề:** {case.title}",
        f"- **Hiện tượng:** {phenomenon}",
        f"- **Trạng thái:** {status_label}",
        f"- **Mức độ ưu tiên:** `{case.priority}`",
        f"- **Thời điểm tạo:** {created_str}",
        f"- **Kho lưu trữ:** `local_cases/cases.jsonl`",
        "",
        "#### 2. Dữ liệu đã có",
        f"- **Bằng chứng / Hiện vật:** {ev_count} mục",
        f"- **Dữ kiện ban đầu:** Đã ghi nhận mô tả hiện trường và phân loại sự cố",
        f"- **Bước 1 (Tra cứu ca tương tự KDTPS):** Đã tra cứu dữ liệu lịch sử",
        "",
        "#### 3. Các trường còn trống cho các bước tiếp theo",
        f"- **Bước 2 (Giả thuyết nguyên nhân):** {hypo_text}",
        f"- **Bước 3 (Cây điều tra 4M & Why-Why):** Chưa lập (bạn có thể gõ `Lập cây 4M cho vụ này`)",
        f"- **Bước 4 (Hành động & Quyết định):** {actions_text} / {decisions_text}",
        f"- **Bước 5 (Kết quả điều tra & Bài học):** {outcome_text} / {lessons_text}",
        "",
        "---",
        "💡 *Gợi ý lệnh tiếp nối:* Gõ **`Lập cây 4M cho vụ này`** để tự động tạo cây phân tích 4M và chuỗi Why-Why Bước 3.",
    ]
    return "\n".join(lines)


def execute_build_case_tree(
    case_id: Optional[str] = None,
    conversation_id: str = "",
) -> str:
    """Handle 'Lập cây 4M cho vụ này': calls build_tree in investigation_tree.py with active case facts."""
    from aios_habit.case_store import load_cases
    from aios_habit.chat_action import ChatActionRequest
    from aios_habit.chat_action_error_lookup import _open_ro, resolve_db_path
    from aios_habit.error_cases.investigation_tree import build_tree, render_markdown

    target_case_id = str(case_id or "").strip() or get_active_case_id()
    if not target_case_id and conversation_id:
        try:
            from aios_habit.workspace_chat_store import load_messages

            msgs = load_messages(conversation_id)
            for m in reversed(msgs):
                match = re.search(
                    r"\b(CASE-[A-Za-z0-9_-]+)\b", m.content or "", re.IGNORECASE
                )
                if match:
                    target_case_id = match.group(1).upper()
                    break
        except Exception:
            pass

    if not target_case_id:
        return (
            "### ⚠️ Chưa có vụ điều tra nào trong ngữ cảnh phiên chat\n\n"
            "Hệ thống chưa ghi nhận vụ điều tra nào để lập cây 4M.\n\n"
            "Bạn có thể:\n"
            "- Tạo vụ mới: `Tạo vụ điều tra lỗi mới: <mô tả hiện tượng>`\n"
            "- Hoặc chỉ định mã vụ: `Lập cây 4M cho vụ CASE-XXXX`"
        )

    all_cases = load_cases()
    case = next((c for c in all_cases if c.case_id == target_case_id), None)
    if case is None:
        return (
            f"### ⚠️ Không tìm thấy vụ `{target_case_id}`\n\n"
            f"Vụ điều tra `{target_case_id}` không tồn tại trong kho lưu trữ `local_cases/cases.jsonl`."
        )

    set_active_case_id(target_case_id)

    situation = str(case.current_situation or "").strip()
    title = str(case.title or "").strip()
    full_text = f"{situation} {title}".strip()

    phenomenon = ""
    m_phen = re.search(r"Hiện tượng:\s*([^.]+)", situation, re.IGNORECASE)
    if m_phen:
        phenomenon = m_phen.group(1).strip()
    if not phenomenon:
        phenomenon = situation if situation else title

    code_match = re.search(
        r"\b(?:(JAM)\s*-?\s*(\d{3,4})|([CFJcfj])\s*-?\s*(\d{3,4}))\b",
        full_text,
    )
    code = ""
    code_family = ""
    if code_match:
        if code_match.group(1):
            code_family = "JAM"
            code = code_match.group(2)
        elif code_match.group(3):
            prefix = code_match.group(3).upper()
            code = code_match.group(4)
            if prefix == "C":
                code_family = "C_CALL"
            elif prefix == "F":
                code_family = "F_SYSTEM"
            elif prefix == "J":
                code_family = "JAM"

    req = ChatActionRequest(question=full_text, conversation_id=conversation_id)
    db_path = resolve_db_path(req)
    conn = None
    if db_path is not None and db_path.is_file():
        try:
            conn = _open_ro(db_path)
        except Exception:
            conn = None

    try:
        tree = build_tree(
            phenomenon=phenomenon,
            code=code,
            code_family=code_family,
            conn=conn,
        )
        rendered_md = render_markdown(tree)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    status_label = format_case_status(case.status)
    header_lines = [
        f"### 🌳 Cây điều tra 4M & Chuỗi Why-Why (Bước 3) — Vụ `{case.case_id}`",
        "",
        f"📌 **Ngữ cảnh phiên:** Vụ **`{case.case_id}`**",
        f"- **Mã vụ:** `{case.case_id}`",
        f"- **Hiện tượng:** {phenomenon}",
        f"- **Trạng thái vụ:** {status_label}",
        f"- **Engine phân tích:** `aios_habit.error_cases.investigation_tree.build_tree`",
        "",
        "---",
        "",
        rendered_md,
    ]
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
