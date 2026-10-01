"""Builtin chat action: nhap bao cao loi moi qua form chuan Buoc 0 (B0-FORM).

Wires the Step-0 standard entry form into the Workspace Chat through the
``chat_action`` framework (TOOL-2), honoring the chat-first UI rule
(one input box + one answer area, no extra toolbars or buttons):

- The user types "nhap bao cao loi" -> the action renders the blank 12-field
  form template inside the answer bubble.
- The user fills the "Label: value" lines and sends them back starting with
  "nop bao cao" -> the action validates, checks duplicates and writes the
  new case straight into the Step-0 ``error_cases`` DB (no intermediate
  file). The answer bubble shows the confirmation card (ticket number,
  warnings) or the blocking error list — never a raw traceback.

Validation (blocking): 5 required fields, closed >= occurred date,
parseable dates. Unknown error codes only warn (never block). An exact
duplicate (model, line, error code, occurred date) warns and is NOT
inserted twice.

DB location (first hit wins): the request context key ``error_cases_db``,
the ``AIOS_ERROR_CASES_DB`` env var, then the well-known deploy path
``C:/tmp/buoc0-deploy/error_cases_deploy.db`` on the home machine.
Fail-closed: no DB -> None (the chat keeps its normal answer flow).
The action never creates a DB file implicitly.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Optional

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)
from aios_habit.error_cases import case_form
from aios_habit.error_cases import store as _store

ACTION_NAME = "nhap_bao_cao_loi"
TITLE = "Nhập báo cáo lỗi (form Bước 0)"

_HINTS = (
    "nhap bao cao",
    "nop bao cao",
    "gui bao cao",
    "luu bao cao",
    "them bao cao",
    "bao cao loi moi",
    "form nhap",
    "nhap ca loi",
    "them ca loi",
    "phieu bao cao",
)

# Well-known deploy locations (home machine first).
_DEFAULT_DB_CANDIDATES = (
    Path("C:/tmp/buoc0-deploy/error_cases_deploy.db"),
    Path.home() / "tmp" / "buoc0-deploy" / "error_cases_deploy.db",
)


def resolve_db_path(request: ChatActionRequest) -> Optional[Path]:
    """Locate the Step-0 DB without creating anything. None = absent."""
    ctx: Mapping[str, Any] = request.context or {}
    for key in ("error_cases_db", "error_cases_db_path"):
        raw = ctx.get(key)
        if raw:
            p = Path(str(raw))
            if p.is_file():
                return p
    env = os.environ.get("AIOS_ERROR_CASES_DB")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    for cand in _DEFAULT_DB_CANDIDATES:
        if cand.is_file():
            return cand
    return None


def _template_outcome() -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=TITLE,
        blocks=[
            ChatActionBlock(kind=BLOCK_MARKDOWN, text=case_form.render_blank_form())
        ],
    )


def _render_auto_section(auto: Optional[dict]) -> list:
    """B5: render AI suggestion + recurrence alert (Vietnamese, no traceback)."""
    if not auto:
        return []
    lines = ["", "### 🤖 Phân loại tự động (AI gợi ý — người nhập xác nhận)", ""]
    grp = auto.get("nhom_nguyen_nhan_vi") or auto.get("nhom_nguyen_nhan")
    conf = auto.get("confidence") or 0.0
    stage = auto.get("cong_doan") or "—"
    dept = auto.get("bo_phan") or "—"
    lines.append(f"- Nhóm nguyên nhân: **{grp}** (độ tin cậy {conf:.0%})")
    lines.append(f"- Công đoạn gợi ý: {stage} · Bộ phận gợi ý: {dept}")
    if conf < 0.5:
        lines.append("- AI chưa chắc chắn — người nhập kiểm tra lại nhóm nguyên nhân.")
    n_hist = auto.get("history_match_count") or 0
    # NOTE: no nested / multiline f-string expressions (PEP 701, Python >= 3.12
    # only) - home machine runs Python 3.11 and raises SyntaxError here.
    hist_txt = f"tìm thấy {n_hist} ca tương tự" if n_hist else "không thấy ca tương tự"
    lines.append(f"- Đã đối chiếu lịch sử: {hist_txt}.")
    rec = auto.get("recurrence")
    if rec:
        lines += [
            "",
            "### ⚠️ Cảnh báo tái phát",
            "",
            f"- {rec['message_vi']}",
        ]
        if rec.get("suggested_from"):
            lines.append(f"  (đối sách lấy từ phiếu {rec['suggested_from']})")
    return lines


def _render_result(result: dict) -> ChatActionOutcome:
    status = result.get("status")
    if status == "inserted":
        lines = [
            "### Đã ghi nhận báo cáo mới",
            "",
            f"- **Mã phiếu:** `{result['no_dvd']}`",
            "- Đủ 12 trường chuẩn đã lưu vào DB Bước 0.",
        ]
        for w in result.get("warnings", []):
            lines.append(f"- ⚠️ {w}")
        lines += _render_auto_section(result.get("auto"))
        kind = BLOCK_MARKDOWN
        text = "\n".join(lines)
    elif status == "duplicate":
        text = "\n".join(
            [
                "### Không nhập đúp",
                "",
                f"- ⚠️ {result['warnings'][0] if result.get('warnings') else 'Ca này đã có trong DB.'}",
            ]
        )
        kind = BLOCK_MARKDOWN
    else:  # blocked
        lines = ["### Chưa ghi được — cần sửa các mục sau:", ""]
        for e in result.get("errors", []):
            lines.append(f"- ❌ {e}")
        for w in result.get("warnings", []):
            lines.append(f"- ⚠️ {w}")
        lines += ["", "Sửa lại rồi gửi form một lần nữa (bắt đầu bằng `nộp báo cáo`)."]
        text = "\n".join(lines)
        kind = BLOCK_MARKDOWN
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=TITLE,
        blocks=[ChatActionBlock(kind=kind, text=text)],
    )


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    db_path = resolve_db_path(request)
    if db_path is None:
        return None
    try:
        if case_form.looks_like_filled_form(request.question):
            data = case_form.parse_form_text(request.question)
            conn = _store.connect(db_path)
            try:
                result = case_form.submit_case(conn, data)
            finally:
                conn.close()
            return _render_result(result)
        return _template_outcome()
    except Exception:
        return None


def register() -> None:
    register_action(
        ChatAction(
            name=ACTION_NAME,
            title=TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Nhập báo cáo lỗi mới theo form chuẩn 12 trường Bước 0: "
                "gõ 'nhập báo cáo lỗi' lấy mẫu, điền xong gửi lại bắt đầu "
                "bằng 'nộp báo cáo' — validate, chống trùng, ghi thẳng DB."
            ),
        )
    )
