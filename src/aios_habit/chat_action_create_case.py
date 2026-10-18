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
from pathlib import Path
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
    """Generate Phase 1 Preview Card markdown containing extracted entities, auto-classification, and recurrence alerts."""
    from aios_habit.chat_action import ChatActionRequest
    from aios_habit.chat_action_error_lookup import _open_ro, resolve_db_path
    from aios_habit.chat_intent_router import extract_case_entities
    from aios_habit.error_cases.auto_classifier import (
        CAUSE_LABEL_VI,
        classify_error,
        classify_new_error,
    )

    entities = dict(slots) if slots else extract_case_entities(text)
    phenomenon = str(entities.get("phenomenon") or "").strip() or "Sự cố sản xuất chưa rõ hiện tượng"
    line = str(entities.get("line") or "").strip()
    machine_type = str(entities.get("machine_type") or "").strip()
    error_code = str(entities.get("error_code") or "").strip()

    # Step 5: Run auto-classification + recurrence detection
    req = ChatActionRequest(question=text, conversation_id=conversation_id)
    db_path = resolve_db_path(req)

    cls_res = None
    rec_alert = None
    if db_path is not None and db_path.is_file():
        try:
            conn = _open_ro(db_path)
            try:
                out = classify_new_error(
                    conn,
                    error_code=error_code,
                    phenomenon=phenomenon,
                    machine_type=machine_type,
                    line=line,
                )
                cls_res = out.get("classification")
                rec_alert = out.get("recurrence_alert")
            finally:
                conn.close()
        except Exception:
            cls_res = None
            rec_alert = None

    if cls_res is None:
        cls_res = classify_error(
            error_code=error_code,
            phenomenon=phenomenon,
            machine_type=machine_type,
            line=line,
        )

    nhom_nguyen_nhan = cls_res.nhom_nguyen_nhan
    nhom_nguyen_nhan_vi = CAUSE_LABEL_VI.get(nhom_nguyen_nhan, nhom_nguyen_nhan)
    cong_doan_val = cls_res.cong_doan or ""
    bo_phan_val = cls_res.bo_phan or ""
    can_cu = dict(getattr(cls_res, "can_cu", {}))

    can_cu_nn = can_cu.get("nhom_nguyen_nhan", "Chưa đủ căn cứ cụ thể từ lịch sử hay từ khóa")
    can_cu_cd = can_cu.get("cong_doan", "Không đủ căn cứ suy luận")
    can_cu_bp = can_cu.get("bo_phan", "Không đủ căn cứ suy luận")

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
        "suggested_nhom_nguyen_nhan": nhom_nguyen_nhan,
        "suggested_nhom_nguyen_nhan_vi": nhom_nguyen_nhan_vi,
        "suggested_cong_doan": cong_doan_val,
        "suggested_bo_phan": bo_phan_val,
        "can_cu": can_cu,
        "is_recurrence": rec_alert is not None,
        "recurrence_count": rec_alert.count if rec_alert else 0,
        "recurrence_msg": rec_alert.message_vi if rec_alert else "",
        "recurrence_remedy": rec_alert.suggested_remedy if rec_alert else "",
        "recurrence_from": rec_alert.suggested_from if rec_alert else "",
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
        "#### 🏷️ Gợi ý phân loại tự động (Bước 5)",
        f"- **Công đoạn đề xuất:** {cong_doan_val if cong_doan_val else 'Chưa xác định'} *(Căn cứ: {can_cu_cd})*",
        f"- **Nhóm nguyên nhân:** **{nhom_nguyen_nhan_vi}** *(Căn cứ: {can_cu_nn})*",
        f"- **Bộ phận phụ trách:** {bo_phan_val if bo_phan_val else 'Chưa xác định'} *(Căn cứ: {can_cu_bp})*",
    ]

    if rec_alert is not None:
        lines.extend([
            "",
            "> ⚠️ **CẢNH BÁO TÁI PHÁT (Bước 5):**",
            f"> - {rec_alert.message_vi}",
        ])
        if rec_alert.suggested_remedy:
            src_str = f" *(từ phiếu `{rec_alert.suggested_from}`)*" if rec_alert.suggested_from else ""
            lines.append(f"> - Đối sách đã áp dụng trong lịch sử: **{rec_alert.suggested_remedy}**{src_str}")

    lines.extend([
        "",
        "_Bấm nút **Xác nhận tạo vụ** bên dưới để lưu hồ sơ và tự động tra cứu ca tương tự Bước 1._",
        "_Bạn cũng có thể mở rộng mục tùy chỉnh nhãn phân loại bên dưới để xác nhận hoặc chỉnh sửa trước khi lưu._",
        "",
        case_preview_marker(marker_payload),
    ])
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
    from aios_habit.error_cases.autoclassify_feedback import log_autoclassify_suggestion

    phenomenon = str(preview_data.get("phenomenon") or "").strip() or "Sự cố kẹt giấy"
    line = str(preview_data.get("line") or "").strip()
    machine_type = str(preview_data.get("machine_type") or "").strip()
    error_code = str(preview_data.get("error_code") or "").strip()

    # Confirmed or edited labels (Step 5: never silently overwrite)
    confirmed_cong_doan = str(
        preview_data.get("confirmed_cong_doan")
        or preview_data.get("suggested_cong_doan")
        or ""
    ).strip()
    confirmed_nhom = str(
        preview_data.get("confirmed_nhom_nguyen_nhan")
        or preview_data.get("suggested_nhom_nguyen_nhan")
        or "khac"
    ).strip()
    confirmed_nhom_vi = str(
        preview_data.get("confirmed_nhom_nguyen_nhan_vi")
        or preview_data.get("suggested_nhom_nguyen_nhan_vi")
        or "Khác"
    ).strip()
    confirmed_bo_phan = str(
        preview_data.get("confirmed_bo_phan")
        or preview_data.get("suggested_bo_phan")
        or ""
    ).strip()

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
    if confirmed_cong_doan:
        situation_parts.append(f"Công đoạn: {confirmed_cong_doan}")
    if confirmed_nhom_vi:
        situation_parts.append(f"Nhóm nguyên nhân: {confirmed_nhom_vi}")
    if confirmed_bo_phan:
        situation_parts.append(f"Bộ phận: {confirmed_bo_phan}")
    situation = ". ".join(situation_parts) + "."

    saved = create_quick_case_with_evidence(
        title=title,
        situation=situation,
        priority="normal",
        privacy="local_only",
        notes="Tạo tự động qua Workspace Chat (Bước 5 phân loại tự động).",
    )
    case_id = str(saved.get("case_id") or "")
    set_active_case_id(case_id)
    raw_status = str(saved.get("status") or "open")
    status_label = format_case_status(raw_status)

    # 1b. Step 5 Continuous Improvement Loop: log suggestion locally
    try:
        log_autoclassify_suggestion(
            case_id=case_id,
            suggested_nhom_nguyen_nhan=preview_data.get("suggested_nhom_nguyen_nhan", "khac"),
            suggested_cong_doan=preview_data.get("suggested_cong_doan"),
            suggested_bo_phan=preview_data.get("suggested_bo_phan"),
            confirmed_nhom_nguyen_nhan=confirmed_nhom,
            confirmed_cong_doan=confirmed_cong_doan,
            confirmed_bo_phan=confirmed_bo_phan,
            can_cu=preview_data.get("can_cu"),
            is_recurrence=bool(preview_data.get("is_recurrence")),
            recurrence_count=int(preview_data.get("recurrence_count", 0)),
            conversation_id=conversation_id or str(preview_data.get("conversation_id") or ""),
        )
    except Exception:
        pass

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
    if confirmed_cong_doan:
        header_lines.append(f"- **Công đoạn:** {confirmed_cong_doan}")
    if confirmed_nhom_vi:
        header_lines.append(f"- **Nhóm nguyên nhân:** **{confirmed_nhom_vi}**")
    if confirmed_bo_phan:
        header_lines.append(f"- **Bộ phận phụ trách:** {confirmed_bo_phan}")
    header_lines.extend([
        f"- **Trạng thái:** {status_label}",
        f"- **Ngữ cảnh phiên:** Vụ **`{case_id}`** đã được đặt làm ngữ cảnh điều tra hiện tại.",
        "- **Kho lưu trữ:** `local_cases/cases.jsonl`",
    ])

    if preview_data.get("is_recurrence"):
        rec_cnt = preview_data.get("recurrence_count", 0)
        rec_rem = preview_data.get("recurrence_remedy")
        rec_from = preview_data.get("recurrence_from")
        header_lines.extend([
            "",
            f"> ⚠️ **LƯU Ý TÁI PHÁT:** Phát hiện {rec_cnt} ca tương tự trong lịch sử.",
        ])
        if rec_rem:
            from_str = f" (từ phiếu `{rec_from}`)" if rec_from else ""
            header_lines.append(f"> - Đối sách lịch sử: **{rec_rem}**{from_str}")

    header_lines.extend([
        "",
        "💡 *Lệnh tiếp nối:* Gõ **`Xem tiến độ vụ này`** hoặc **`Lập cây 4M cho vụ này`** để tiếp tục.",
        "",
        "---",
        "",
        "### 🔍 Bước 1: Tra cứu ca lỗi tương tự trong lịch sử KDTPS",
        "",
    ])

    feedback_footer = [
        "",
        "---",
        "**Đánh giá gợi ý này:** `đánh giá đúng` · `đánh giá sai` · `đánh giá một phần`",
        "🏷️ **Phản hồi nhãn phân loại:** `đúng nhãn` · `sai nhãn` · `sửa nhãn: [nhóm]`",
        "_Gõ ngay trong ô chat — không cần mở thêm gì._",
    ]

    if cards_text:
        return "\n".join(header_lines) + cards_text + "\n" + "\n".join(feedback_footer)
    else:
        header_lines.extend([
            "_Chưa tìm thấy ca lỗi tương tự trong lịch sử hoặc DB chưa khả dụng._",
        ])
        header_lines.extend(feedback_footer)
        return "\n".join(header_lines)


def find_case_investigation_tree(
    case_id: str,
    case: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Lookup Step 3 investigation tree status/summary for a case.

    Searches in:
    1. case.timeline_events (if case object is passed or loadable).
    2. local_cases/investigation_feedback.jsonl (Step 3 continuous improvement store).
    3. Alternative LOCAL_CASES_DIR / investigation_feedback.jsonl (for test isolation).
    """
    clean_id = str(case_id or "").strip().upper()
    if not clean_id:
        return None

    # 1. Check timeline events on case object
    if case is not None:
        events = getattr(case, "timeline_events", []) or []
        for ev in reversed(events):
            if isinstance(ev, dict) and (
                ev.get("type") in ("investigation_tree_built", "tree_built")
                or ev.get("tree_id")
            ):
                return {
                    "tree_id": str(ev.get("tree_id") or ""),
                    "total_items": int(ev.get("total_items") or 0),
                    "grounded_items": int(ev.get("grounded_items") or 0),
                    "generic_items": int(ev.get("generic_items") or 0),
                    "created_at": str(ev.get("timestamp") or ""),
                    "source": "timeline_events",
                }

    # 2. Check local_cases/investigation_feedback.jsonl via load_all_investigation_feedback
    try:
        from aios_habit.error_cases.investigation_feedback import (
            load_all_investigation_feedback,
        )

        records = load_all_investigation_feedback()
        matched = [
            r
            for r in records
            if isinstance(r, dict)
            and str(r.get("case_id") or "").strip().upper() == clean_id
        ]
        if matched:
            latest = matched[-1]
            return {
                "tree_id": str(latest.get("tree_id") or ""),
                "total_items": int(latest.get("total_items") or 0),
                "grounded_items": int(latest.get("grounded_items") or 0),
                "generic_items": int(latest.get("generic_items") or 0),
                "rating": str(latest.get("rating") or ""),
                "exported_files": list(latest.get("exported_files") or []),
                "created_at": str(latest.get("created_at") or ""),
                "source": "investigation_feedback",
            }
    except Exception:
        pass

    # 3. Check if aios_habit.case_store.LOCAL_CASES_DIR has its own investigation_feedback.jsonl
    try:
        from aios_habit.case_store import LOCAL_CASES_DIR

        alt_fb = Path(LOCAL_CASES_DIR) / "investigation_feedback.jsonl"
        if alt_fb.is_file():
            matched_lines = []
            with alt_fb.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if (
                            isinstance(data, dict)
                            and str(data.get("case_id") or "").strip().upper()
                            == clean_id
                        ):
                            matched_lines.append(data)
                    except Exception:
                        continue
            if matched_lines:
                latest = matched_lines[-1]
                return {
                    "tree_id": str(latest.get("tree_id") or ""),
                    "total_items": int(latest.get("total_items") or 0),
                    "grounded_items": int(latest.get("grounded_items") or 0),
                    "generic_items": int(latest.get("generic_items") or 0),
                    "rating": str(latest.get("rating") or ""),
                    "exported_files": list(latest.get("exported_files") or []),
                    "created_at": str(latest.get("created_at") or ""),
                    "source": "alt_investigation_feedback",
                }
    except Exception:
        pass

    return None


def format_case_tree_status(tree_info: Optional[Dict[str, Any]]) -> str:
    """Format the Step 3 investigation tree display string for case progress view."""
    if not tree_info:
        return "Chưa lập cây (còn trống)"

    tree_id = tree_info.get("tree_id") or ""
    total_items = tree_info.get("total_items", 0)
    grounded_items = tree_info.get("grounded_items", 0)

    details: List[str] = []
    if total_items > 0:
        details.append(f"{total_items} mục")
    if grounded_items > 0:
        details.append(f"{grounded_items} có căn cứ")
    elif total_items > 0:
        details.append("gợi ý chung")

    summary_str = f": {', '.join(details)}" if details else ""
    if tree_id:
        return f"Đã lập cây ({tree_id}{summary_str})"
    elif details:
        return f"Đã lập cây ({', '.join(details)})"
    return "Đã lập cây"


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

    tree_info = find_case_investigation_tree(target_case_id, case)
    tree_text = format_case_tree_status(tree_info)


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
        f"- **Bước 3 (Cây điều tra 4M & Why-Why):** {tree_text}",
        f"- **Bước 4 (Hành động & Quyết định):** {actions_text} / {decisions_text}",
        f"- **Bước 5 (Kết quả điều tra & Bài học):** {outcome_text} / {lessons_text}",
    ]

    cause_val = getattr(case, "actual_cause", "")
    remedy_val = getattr(case, "actual_countermeasure", "")
    closed_val = getattr(case, "closed_at", "")
    if cause_val or remedy_val or case.status == "resolved":
        lines.extend([
            "",
            "#### 🔒 Kết quả đóng vụ (Cổng hoàn thành Bước 2)",
            f"- **Nguyên nhân thật:** {cause_val if cause_val else 'Chưa có'}",
            f"- **Đối sách thật:** {remedy_val if remedy_val else 'Chưa có'}",
            f"- **Thời điểm đóng:** {closed_val if closed_val else 'Chưa đóng'}",
        ])

    lines.extend([
        "",
        "---",
        "💡 *Gợi ý lệnh tiếp nối:* Gõ **`Lập cây 4M cho vụ này`** để tạo cây phân tích 4M, hoặc gõ **`Đóng vụ`** kèm nguyên nhân và đối sách thật để hoàn tất hồ sơ.",
    ])
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

    # Save company-format files (md + docx) for pasting straight into the report
    saved_files: List[str] = []
    try:
        from aios_habit.error_cases.investigation_tree import export_report
        root_dir = Path(__file__).resolve().parents[2]
        outdir = root_dir / "local_runs" / "dieu_tra"
        outdir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug_phen = re.sub(r"[^a-z0-9]+", "-", phenomenon.lower())[:30].strip("-") or "case-tree"
        base_p = outdir / f"{stamp}-{case.case_id}-{slug_phen}"
        meta = {
            "report_id": f"KTD-{case.case_id}",
            "author": getattr(case, "assigned_to", "") or "Kỹ sư điều tra",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "model": getattr(case, "machine_type", "") or "",
            "line": getattr(case, "line", "") or "",
        }
        for sfx in (".md", ".docx"):
            try:
                p_out = export_report(tree, base_p.with_suffix(sfx), meta)
                saved_files.append(str(p_out))
            except Exception:
                pass
    except Exception:
        pass

    # Log suggestion to local continuous improvement loop
    try:
        from aios_habit.error_cases.investigation_feedback import log_investigation_tree
        log_investigation_tree(
            tree_id=tree.tree_id,
            phenomenon=phenomenon,
            code=code,
            case_id=case.case_id,
            total_items=tree.total_items,
            grounded_items=tree.grounded_items_count,
            generic_items=tree.generic_items_count,
            branch_basis=tree.branch_basis,
            exported_files=saved_files,
            conversation_id=conversation_id,
        )
    except Exception:
        pass

    # Record timeline event on case and persist to cases.jsonl
    try:
        from aios_habit.case_store import save_case

        case.timeline_events.append({
            "timestamp": datetime.now().isoformat(),
            "type": "investigation_tree_built",
            "tree_id": tree.tree_id,
            "total_items": str(tree.total_items),
            "grounded_items": str(tree.grounded_items_count),
            "generic_items": str(tree.generic_items_count),
            "description": f"Đã lập cây điều tra 4M & Why-Why ({tree.tree_id}): {tree.total_items} mục ({tree.grounded_items_count} có căn cứ, {tree.generic_items_count} gợi ý chung).",
        })
        save_case(case)
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
        f"- **Chỉ số căn cứ:** **{tree.grounded_items_count}** có căn cứ ca tương tự / kho · **{tree.generic_items_count}** gợi ý chung",
        f"- **Engine phân tích:** `aios_habit.error_cases.investigation_tree.build_tree`",
        "",
        "---",
        "",
        rendered_md,
    ]

    if saved_files:
        header_lines.extend([
            "",
            "---",
            "**Tệp kế hoạch điều tra (dán thẳng vào biểu mẫu báo cáo công ty):**",
            *[f"- `{f}`" for f in saved_files],
        ])

    header_lines.extend([
        "",
        "---",
        "**Đánh giá cây điều tra:** `cây điều tra đúng hướng` · `cây điều tra thiếu nhánh` · `cây điều tra không hữu ích`",
        "_Gõ ngay trong ô chat để gửi phản hồi cải thiện liên tục (lưu kho cục bộ, không ghi kho tri thức)._",
    ])

    return "\n".join(header_lines)


def execute_close_case(
    case_id: Optional[str] = None,
    actual_cause: str = "",
    actual_countermeasure: str = "",
    conversation_id: str = "",
    raw_text: str = "",
    closed_by: str = "user",
) -> str:
    """Handle intent DONG_VU: Enforce Close Gate (Step 2).

    Blocks closing if actual_cause or actual_countermeasure is missing.
    When valid, writes actual cause and remedy back into local_cases/cases.jsonl.
    Zero modifications to the knowledge store (library.sqlite / vector db).
    """
    from aios_habit.case_store import (
        close_investigation_case,
        InvestigationClosureBlockedError,
        load_cases,
    )
    from aios_habit.chat_intent_router import extract_case_id_from_text

    target_case_id = str(case_id or "").strip()
    if not target_case_id and raw_text:
        target_case_id = extract_case_id_from_text(raw_text)
    if not target_case_id:
        target_case_id = get_active_case_id()
    if not target_case_id and conversation_id:
        try:
            from aios_habit.workspace_chat_store import load_messages

            msgs = load_messages(conversation_id)
            for m in reversed(msgs):
                cid = extract_case_id_from_text(m.content)
                if cid:
                    target_case_id = cid
                    break
        except Exception:
            pass
    if not target_case_id:
        cases = load_cases()
        if cases:
            target_case_id = cases[-1].case_id

    if not target_case_id:
        return (
            "### ⚠️ Chưa xác định được vụ điều tra cần đóng\n\n"
            "Vui lòng chỉ định rõ mã vụ điều tra cần đóng (Ví dụ: `CASE-XXXXXXXX`).\n\n"
            "**Cú pháp chuẩn:**\n"
            "- `Đóng vụ CASE-XXXXXXXX: nguyên nhân: <nguyên nhân thật>, đối sách: <đối sách thật>`\n"
            "- Hoặc chọn xem tiến độ vụ trước: `Xem tiến độ vụ CASE-XXXXXXXX`"
        )

    cause_val = str(actual_cause or "").strip()
    remedy_val = str(actual_countermeasure or "").strip()

    if (not cause_val or not remedy_val) and raw_text:
        if not cause_val:
            m_c = re.search(
                r"(?:nguyên\s*nhân(?:\s*thật)?|nguyen\s*nhan(?:\s*that)?|lý\s*do(?:\s*thật)?|ly\s*do(?:\s*that)?|root\s*cause|cause)\s*[:=-]\s*(.*?)(?=(?:,\s*|\s*;\s*|\n)(?:đối\s*sách|doi\s*sach|biện\s*pháp|bien\s*phap|remedy|countermeasure)|$)",
                raw_text,
                re.IGNORECASE,
            )
            if m_c:
                cause_val = m_c.group(1).strip()
        if not remedy_val:
            m_r = re.search(
                r"(?:đối\s*sách(?:\s*thật)?|doi\s*sach(?:\s*that)?|biện\s*pháp(?:\s*thật)?|bien\s*phap(?:\s*that)?|phòng\s*ngừa|phong\s*ngua|hướng\s*xử\s*lý|countermeasure|remedy)\s*[:=-]\s*(.*?)(?=(?:,\s*|\s*;\s*|\n)(?:nguyên\s*nhân|nguyen\s*nhan|root\s*cause)|$)",
                raw_text,
                re.IGNORECASE,
            )
            if m_r:
                remedy_val = m_r.group(1).strip()

    try:
        closed_case = close_investigation_case(
            case_id=target_case_id,
            actual_cause=cause_val,
            actual_countermeasure=remedy_val,
            closed_by=closed_by,
        )
        set_active_case_id(target_case_id)
        return (
            f"### ✅ ĐÃ ĐÓNG VỤ ĐIỀU TRA THÀNH CÔNG (Cổng Bước 2 Đạt)\n\n"
            f"📌 **Hồ sơ:** Vụ **`{closed_case.case_id}`**\n"
            f"- **Tiêu đề:** {closed_case.title}\n"
            f"- **Trạng thái:** **Đã giải quyết (`resolved`)**\n"
            f"- **Nguyên nhân thật:** **{closed_case.actual_cause}**\n"
            f"- **Đối sách thật:** **{closed_case.actual_countermeasure}**\n"
            f"- **Thời điểm đóng:** `{closed_case.closed_at}`\n"
            f"- **Kho lưu trữ:** Đã cập nhật hồ sơ vào `local_cases/cases.jsonl` và ghi nhật ký đóng tại `local_cases/case_closures.jsonl`.\n"
            f"- **Kho tri thức RAG:** *Bảo toàn độc lập tuyệt đối (không ghi đè cơ sở dữ liệu tri thức tĩnh `library.sqlite`).*\n"
        )
    except InvestigationClosureBlockedError as err:
        missing_fmt = " và ".join(f"**{f}**" for f in err.missing_fields)
        return (
            f"### 🚫 CỔNG CHẶN ĐÓNG VỤ (Điều kiện hoàn thành Bước 2)\n\n"
            f"**Không thể đóng vụ điều tra `{target_case_id}` vì thiếu thông tin bắt buộc!**\n\n"
            f"- **Trường còn thiếu:** {missing_fmt}\n"
            f"- **Trạng thái hiện tại:** Vẫn giữ nguyên trạng thái mở/điều tra, không cho phép đóng hồ sơ.\n\n"
            f"> ⚠️ **Quy tắc tất định Bước 2:** Để đảm bảo chất lượng dữ liệu cải tiến liên tục, "
            f"mọi vụ điều tra sự cố bắt buộc phải xác định rõ **nguyên nhân thật** và **đối sách thật** "
            f"trước khi đóng hồ sơ.\n\n"
            f"**Vui lòng bổ sung đầy đủ theo cú pháp:**\n"
            f"```text\n"
            f"Đóng vụ {target_case_id}: nguyên nhân: <nguyên nhân thật>, đối sách: <đối sách thật>\n"
            f"```"
        )
    except KeyError:
        return (
            f"### ⚠️ Không tìm thấy hồ sơ vụ điều tra `{target_case_id}`\n\n"
            f"Vụ điều tra `{target_case_id}` không tồn tại trong kho lưu trữ `local_cases/cases.jsonl`."
        )
    except Exception as exc:
        return f"### ❌ Lỗi khi đóng vụ điều tra: {exc}"


def render_case_preview_widget(
    st_ctx: Any,
    preview_data: Dict[str, Any],
    conversation_id: str = "",
    message_id: str = "",
) -> None:
    """Render confirmation button inline in the chat bubble for Streamlit with editable classification labels."""
    preview_id = str(preview_data.get("preview_id", "") or "")
    confirmed_key = f"wsc_case_confirmed_{preview_id}"
    session_state = getattr(st_ctx, "session_state", {})
    if session_state.get(confirmed_key):
        return

    # User confirmation/edit controls (never silently overwrite)
    default_nhom_vi = str(preview_data.get("suggested_nhom_nguyen_nhan_vi") or "Khác")
    cause_options = ["Lắp ráp", "Thiết kế", "Linh kiện", "Khác"]
    idx_cause = cause_options.index(default_nhom_vi) if default_nhom_vi in cause_options else 3

    rev_cause = {
        "Lắp ráp": "lap_rap",
        "Thiết kế": "thiet_ke",
        "Linh kiện": "linh_kien",
        "Khác": "khac",
    }

    c_cd = preview_data.get("suggested_cong_doan", "")
    c_nhom = default_nhom_vi
    c_bp = preview_data.get("suggested_bo_phan", "")

    # Expander for editing labels before saving
    try:
        with st_ctx.expander("✏️ Xem hoặc sửa nhãn phân loại trước khi lưu (Bước 5)", expanded=False):
            c_cd = st_ctx.text_input(
                "Công đoạn sản xuất",
                value=str(preview_data.get("suggested_cong_doan", "") or ""),
                key=f"inp_cd_{preview_id}",
            )
            c_nhom = st_ctx.selectbox(
                "Nhóm nguyên nhân",
                options=cause_options,
                index=idx_cause,
                key=f"inp_nhom_{preview_id}",
            )
            c_bp = st_ctx.text_input(
                "Bộ phận phụ trách",
                value=str(preview_data.get("suggested_bo_phan", "") or ""),
                key=f"inp_bp_{preview_id}",
            )
    except Exception:
        pass

    btn_key = f"btn_confirm_case_{preview_id}_{message_id}"
    if st_ctx.button("Xác nhận tạo vụ", key=btn_key, type="primary"):
        # Put confirmed or edited labels into preview_data
        updated_data = dict(preview_data)
        updated_data["confirmed_cong_doan"] = str(c_cd or preview_data.get("suggested_cong_doan", "")).strip()
        updated_data["confirmed_nhom_nguyen_nhan"] = rev_cause.get(c_nhom, "khac")
        updated_data["confirmed_nhom_nguyen_nhan_vi"] = str(c_nhom)
        updated_data["confirmed_bo_phan"] = str(c_bp or preview_data.get("suggested_bo_phan", "")).strip()

        outcome_text = execute_confirm_case(
            preview_data=updated_data,
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
