"""Builtin chat action: lập báo cáo điều tra lỗi (agent báo cáo).

The user types a command in the single chat box, e.g. "lap bao cao dieu tra
cho ca FORM-20261001-0001" or "lap bao cao dieu tra cho ca C7620". The
action finds the case in the Step 0-5 error-case DB and assembles a .docx
investigation report from the features already shipped:

- 12 standard fields of the case (Buoc 0 form),
- similar history cases + countermeasures already used (Buoc 1),
- 4M investigation tree + Why-Why chain (Buoc 3),
- auto classification + recurrence alert (Buoc 5),
- a real-data trend chart of the same error code when available.

The report file is saved under ``local_runs/bao_cao_dieu_tra/`` and its
path is printed inside the answer bubble (same pattern as the Buoc 3
investigation-plan files); the trend chart (if any) is also rendered
inline. No extra button or toolbar — everything stays in the answer area.

Fail-closed: gated by ``AIOS_FEATURE_INVESTIGATION_REPORT`` (default off,
sits on top of ``AIOS_FEATURE_CHAT_ACTION``); missing DB / unknown case /
any exception returns None so the chat keeps its normal RAG answer flow.
The DB is only read. Nothing is ever invented: a section without data
says "Chua co du lieu" inside the report, and a case that cannot be
identified yields guidance asking for the ticket number / error code.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.chat_action import (
    BLOCK_CHART,
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)
from aios_habit.error_cases.investigation_report import (
    MISSING,
    assemble_report_data,
    case_file_slug,
    render_report_docx,
    render_trend_chart,
)
from aios_habit.feature_flags import (
    FEATURE_INVESTIGATION_REPORT,
    is_feature_enabled,
)

from .chat_action_error_lookup import (
    _has_error_code_i,
    _open_ro,
    extract_codes,
    resolve_db_path,
)

ACTION_NAME = "lap_bao_cao_dieu_tra"
TITLE = "Báo cáo điều tra lỗi"

# Command phrases for the report agent. None of them overlaps the hints of
# the case-form actions ("nhap bao cao", "nop bao cao", ...) or the Buoc 3
# plan actions ("huong dieu tra", "cay dieu tra", "ke hoach dieu tra", ...).
# Registration order still matters for the bare-code fallback of
# chat_action_error_lookup (a bare "C7620" must not swallow the command),
# so this module is registered BEFORE chat_action_error_lookup.
_HINTS = (
    "lap bao cao dieu tra",
    "tao bao cao dieu tra",
    "xuat bao cao dieu tra",
    "viet bao cao dieu tra",
    "lap bao cao cho ca",
    "bao cao dieu tra cho ca",
)

_EXPORT_DIRNAME = "bao_cao_dieu_tra"

# New-style ticket numbers issued by the Buoc 0 form.
_FORM_NO_RE = re.compile(r"FORM-\d{8}-\d{4}", re.IGNORECASE)
# Historic KDTPS ticket numbers look like "2023/5".
_YEAR_NO_RE = re.compile(r"\b\d{4}/\d+\b")
# "phiếu 2023/5" -> the token after "phiếu" (diacritics already folded).
_TICKET_TOKEN_RE = re.compile(r"(?:phieu|so phieu)\s+([a-z0-9][a-z0-9\-/]*)")


# ---------------------------------------------------------------------------
# Case identification (never invents a case)
# ---------------------------------------------------------------------------


def extract_ticket(question: str) -> str:
    """Ticket number (no_dvd) from the question, or "" when not specified."""
    m = _FORM_NO_RE.search(question or "")
    if m:
        return m.group(0).upper()
    m = _YEAR_NO_RE.search(question or "")
    if m:
        return m.group(0)
    m = _TICKET_TOKEN_RE.search(normalize_text(question or ""))
    if m:
        return m.group(1)
    return ""


def _row_to_case(row: sqlite3.Row) -> Dict[str, Any]:
    case = dict(row)
    try:
        raw = json.loads(case.get("raw_json") or "{}")
    except (ValueError, TypeError):
        raw = {}
    case["_raw"] = raw if isinstance(raw, dict) else {}
    return case


def _fetch_case_by_id(conn: sqlite3.Connection, case_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT ec.*, b.source_file, b.sheet_name "
        "FROM error_cases ec "
        "LEFT JOIN import_batches b ON b.id = ec.batch_id "
        "WHERE ec.id = ?",
        (case_id,),
    ).fetchone()
    return _row_to_case(row) if row else None


def find_case(
    conn: sqlite3.Connection, question: str
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Locate the target case. Returns (case, how_it_was_found).

    Exact ticket number first; otherwise the most recent case carrying
    the error code. (None, "") means nothing identifiable was found.
    """
    ticket = extract_ticket(question)
    if ticket:
        rows = conn.execute(
            "SELECT id FROM error_cases WHERE no_dvd = ? ORDER BY id DESC",
            (ticket,),
        ).fetchall()
        if rows:
            case = _fetch_case_by_id(conn, int(rows[0][0]))
            note = f"số phiếu {ticket}"
            if len(rows) > 1:
                note += f" (phiếu này có {len(rows)} bản ghi, lấy bản mới nhất)"
            return case, note
    codes = extract_codes(question)
    if codes:
        code = codes[0]
        columns = ["error_code_c", "error_code_h"]
        if _has_error_code_i(conn):
            columns.append("error_code_i")
        where = " OR ".join(f"UPPER({col}) = ?" for col in columns)
        row = conn.execute(
            "SELECT id FROM error_cases WHERE (" + where + ") "
            "ORDER BY COALESCE(NULLIF(occurred_at, ''), created_at) DESC, id DESC "
            "LIMIT 1",
            [code] * len(columns),
        ).fetchone()
        if row:
            return _fetch_case_by_id(conn, int(row[0])), f"mã lỗi {code} (ca gần nhất)"
    return None, ""


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _out_dir(request: ChatActionRequest) -> Path:
    ctx = request.context or {}
    raw = ctx.get("report_out_dir")
    if raw:
        out = Path(str(raw))
    else:
        # <repo>/src/aios_habit/chat_action_bao_cao_dieu_tra.py -> parents[2] == <repo>
        root = Path(__file__).resolve().parents[2]
        out = root / "local_runs" / _EXPORT_DIRNAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def _render_summary(data, docx_path: Path, chart_path: Optional[Path]) -> str:
    case = data.case
    lines = [
        f"Đã lập **báo cáo điều tra** cho ca **{case.get('no_dvd') or '—'}**"
        + (f" (mã lỗi **{data.code}**)" if data.code else ""),
        "",
        f"- **Hiện tượng:** {data.phenomenon or MISSING}",
    ]
    if data.classification is not None:
        c = data.classification
        lines.append(
            f"- **Phân loại tự động gợi ý:** {c.nhom_nguyen_nhan or MISSING} "
            f"(độ tin cậy {c.confidence:.0%}) — cần người điều tra xác nhận"
        )
    else:
        lines.append("- **Phân loại tự động:** Chưa có dữ liệu")
    if data.recurrence:
        lines.append(
            f"- **Tái phát:** ⚠️ mã {data.recurrence['code']} đã phát sinh "
            f"{data.recurrence['count']} lần quanh thời điểm ca này"
        )
    elif data.code:
        lines.append("- **Tái phát:** không phát hiện quanh thời điểm ca này")
    lines.append(f"- **Ca tương tự đối chiếu:** {len(data.similar)} ca")
    lines.append("")
    lines.append(f"**File báo cáo (.docx):** `{docx_path}`")
    if chart_path is not None:
        lines.append(f"**File biểu đồ xu hướng (.png):** `{chart_path}`")
    lines.append(
        "_Mục nào thiếu dữ liệu, báo cáo ghi rõ \"Chưa có dữ liệu\" — "
        "agent không tự bịa số liệu._"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def _guidance_outcome(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=TITLE,
        blocks=(ChatActionBlock(kind=BLOCK_MARKDOWN, text=text),),
    )


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    # Fail-closed at every step: None falls back to the normal RAG flow.
    if not is_feature_enabled(FEATURE_INVESTIGATION_REPORT):
        return None
    try:
        db_path = resolve_db_path(request)
        if db_path is None:
            return None
        conn = _open_ro(db_path)
    except Exception:
        return None
    try:
        case, how = find_case(conn, request.question)
        if case is None:
            ticket = extract_ticket(request.question)
            codes = extract_codes(request.question)
            if ticket or codes:
                label = ticket or ", ".join(codes)
                return _guidance_outcome(
                    f"Không tìm thấy ca **{label}** trong DB ca lỗi Bước 0–5. "
                    "Kiểm tra lại số phiếu/mã lỗi, hoặc xem ca tương tự bằng cách "
                    "gõ mã lỗi trần (VD: `C7620`)."
                )
            return _guidance_outcome(
                "Cho tôi **số phiếu** hoặc **mã lỗi** của ca cần lập báo cáo, "
                "ví dụ: `lập báo cáo điều tra cho ca FORM-20261001-0001` "
                "hoặc `lập báo cáo điều tra cho ca C7620`."
            )
        data = assemble_report_data(conn, case)
        out_dir = _out_dir(request)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = case_file_slug(case)
        chart_path = render_trend_chart(data, out_dir / f"xu-huong-{slug}-{stamp}.png")
        docx_path = render_report_docx(
            data, out_dir / f"bao-cao-dieu-tra-{slug}-{stamp}.docx",
            chart_path=chart_path,
        )
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

    blocks: List[ChatActionBlock] = [
        ChatActionBlock(kind=BLOCK_MARKDOWN, text=_render_summary(data, docx_path, chart_path))
    ]
    if chart_path is not None:
        try:
            blocks.append(
                ChatActionBlock(
                    kind=BLOCK_CHART,
                    image_png=chart_path.read_bytes(),
                    alt=f"Xu hướng mã {data.code}",
                    caption=f"Số ca mỗi tuần của mã {data.code} (dữ liệu thật trong DB)",
                )
            )
        except Exception:
            pass
    return ChatActionOutcome(action=ACTION_NAME, title=TITLE, blocks=tuple(blocks))


def register() -> None:
    register_action(
        ChatAction(
            name=ACTION_NAME,
            title=TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Lập báo cáo điều tra lỗi: gõ 'lap bao cao dieu tra cho ca "
                "<so phieu / ma loi>', nhận 1 file .docx gom thông tin ca "
                "(Bước 0), ca tương tự + đối sách đã dùng (Bước 1), cây 4M + "
                "Why-Why (Bước 3), phân loại + cảnh báo tái phát (Bước 5) và "
                "biểu đồ xu hướng dữ liệu thật. Sau cờ "
                "AIOS_FEATURE_INVESTIGATION_REPORT."
            ),
        )
    )


register()
