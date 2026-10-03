"""Chat action: mo phien phong van chuyen gia NGAY TRONG KHUNG CHAT (Task 1).

Khac voi action `phong_van_chuyen_gia` (chi doc — xem phien/khoang trong da
luu): action nay MO PHIEN MOI theo backend `expert_interview_session` (cau hoi
vang xac dinh, khong LLM) tu ma loi that trong kho ca loi, roi tra ve
markdown kem marker `aios_interview_session` de `workspace_chat_ui` ve widget
hoi/dap tung cau ngay duoi cau hoi (khong chuyen man hinh, khong form rieng).

Hint ("mo phien phong van", "bat dau phien phong van") khong giao voi action
cu ("phong van chuyen gia") nen hai action khong chay chong nhau.

Tuong thich Python 3.11: khong f-string nhieu dong (PEP 701).
"""

from __future__ import annotations

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

ACTION_NAME = "phien_phong_van_chat"
ACTION_TITLE = "Phiên phỏng vấn trong chat"

_HINTS = (
    "mo phien phong van",
    "bat dau phien phong van",
)


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _resolve_context(code: str, request: ChatActionRequest) -> Dict[str, Any]:
    """Build a PhenomenonContext from a real error case (read-only).

    Returns {"ok": True, "ctx": PhenomenonContext} or {"ok": False, "error_vi": ...}.
    """
    from aios_habit.chat_action_error_lookup import (
        _candidate_rows,
        _case_dict,
        _has_code_missing_col,
        _open_ro,
        resolve_db_path,
    )
    from aios_habit.golden_question_generator import PhenomenonContext

    db_path = resolve_db_path(request)
    if db_path is None:
        return {
            "ok": False,
            "error_vi": (
                "Chưa tìm thấy kho ca lỗi trên máy này nên chưa mở được phiên phỏng vấn."
            ),
        }
    try:
        conn = _open_ro(Path(db_path))
    except Exception:
        return {
            "ok": False,
            "error_vi": "Chưa đọc được kho ca lỗi lúc này. Bạn thử lại sau nhé.",
        }
    try:
        rows = _candidate_rows(conn, [code], [])
        has_missing = _has_code_missing_col(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass
    if not rows:
        return {
            "ok": False,
            "error_vi": "Chưa tìm thấy mã “%s” trong kho ca lỗi." % code,
        }
    scored: List[Any] = []
    for row in rows:
        info = _case_dict(row, has_missing)
        scored.append((info, row))
    scored.sort(key=lambda item: str(item[1]["id"]))
    info = scored[0][0]
    row = scored[0][1]
    phenomenon = str(info.get("hien_tuong") or "").strip() or "Mã lỗi %s" % code
    ref = str(info.get("no_dvd") or "").strip() or "id-%s" % row["id"]
    try:
        batch_id = str(row["batch_id"] or "").strip()
    except (KeyError, IndexError):
        batch_id = ""
    ctx = PhenomenonContext(
        batch_id=batch_id or "chat-phien-phong-van",
        error_code=code,
        phenomenon=phenomenon,
        case_ids=(ref,),
        error_group=str(info.get("category") or "").strip() or "F CALL",
    )
    return {"ok": True, "ctx": ctx, "phenomenon": phenomenon}


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    from aios_habit import chat_interview_ui as _ui
    from aios_habit.chat_action_error_lookup import extract_codes
    from aios_habit.expert_interview_session import (
        InterviewSessionError,
        start_session,
    )

    codes = extract_codes(request.question or "")
    if not codes:
        return _message(
            "Cho mình mã lỗi để mở phiên phỏng vấn — ví dụ: “mở phiên phỏng vấn F000”."
        )
    code = codes[0]
    resolved = _resolve_context(code, request)
    if not resolved.get("ok"):
        return _message(str(resolved.get("error_vi") or "Chưa mở được phiên phỏng vấn."))
    try:
        session = start_session(resolved["ctx"])
    except InterviewSessionError as exc:
        return _message("Chưa mở được phiên phỏng vấn: %s" % exc)
    _ui.store_session(session)
    lines = [
        "### 🎙️ Phiên phỏng vấn %s — mã **%s**" % (session.session_id, code),
        "",
        "- Hiện tượng: %s" % resolved.get("phenomenon", ""),
        "- Số câu hỏi: **%d** — trả lời ngay dưới từng câu hỏi, đáp án thiếu ý "
        "sẽ được nhắc bổ sung trước khi qua câu tiếp theo." % len(session.questions),
        "",
        _ui.interview_marker(session.session_id),
    ]
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text="\n".join(lines)),),
    )


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Mở phiên phỏng vấn chuyên gia ngay trong khung chat từ mã lỗi thật; "
                "hỏi từng câu, đáp án thiếu ý bị nhắc bổ sung, xong thì lưu nháp chờ duyệt."
            ),
        )
    )


register()
