"""Builtin chat actions: vong phan hoi (B2 feedback loop).

Wires the Step-2/B2 feedback loop into the Workspace Chat through the
``chat_action`` framework (TOOL-2), honoring the chat-first UI rule
(one input box + one answer area, no extra toolbars or buttons):

- ``danh_gia_goi_y``: after a suggestion answer, the user types
  "đánh giá đúng" / "đánh giá sai" / "đánh giá một phần" right in the
  chat box. The rating is logged against the newest unrated suggestion
  call of this conversation (re-rating updates: latest rating wins).
- ``dong_phieu_loi``: close an error ticket from chat. The user sends
  "đóng phiếu" + "mã phiếu / nguyên nhân thật / đối sách thật"
  (+ "hiện tượng / công đoạn" for new tickets). The B2 hard rules apply:
  missing actual cause/countermeasure (or phenomenon/process stage on
  new tickets per QD-BK82-1) BLOCKS the close with a plain-language
  message — never a raw traceback.
- ``bao_cao_phan_hoi``: feedback metrics — % of suggestion calls rated
  (target >= 80%) and the correct/partial rate per quarter.

DB location (first hit wins): the request context key ``error_cases_db``,
the ``AIOS_ERROR_CASES_DB`` env var, then the well-known deploy path
``C:/tmp/buoc0-deploy/error_cases_deploy.db`` on the home machine.
Fail-closed: no DB -> None (the chat keeps its normal answer flow).
Rating/close write to the Step-0 ``error_cases`` DB (same DB the B0-FORM
action already writes to); a logging failure never breaks the answer.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

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
from aios_habit.error_cases import feedback_loop as _feedback
from aios_habit.error_cases import store as _store
from aios_habit.error_cases.feedback_loop import (
    RATING_CORRECT,
    RATING_PARTIAL,
    RATING_WRONG,
    RATINGS,
    ClosureBlockedError,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def _open_ro(path: Path) -> sqlite3.Connection:
    uri = "file:" + path.as_posix() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _squash(text: str) -> str:
    """Normalized question with punctuation removed (for command matching)."""
    return re.sub(r"[^a-z0-9 ]", " ", normalize_text(text or "")).strip()


def _message(action: str, title: str, text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=action,
        title=title,
        blocks=(ChatActionBlock(kind=BLOCK_MARKDOWN, text=text),),
    )


# ---------------------------------------------------------------------------
# 1. danh_gia_goi_y — rate the latest suggestion in this conversation
# ---------------------------------------------------------------------------

RATE_ACTION_NAME = "danh_gia_goi_y"
RATE_TITLE = "Đánh giá gợi ý"

_RATE_EXACT = frozenset(
    {
        "danh gia dung",
        "danh gia sai",
        "danh gia mot phan",
        "goi y dung",
        "goi y sai",
        "goi y mot phan",
    }
)

_RATE_HELP = (
    "Đánh giá gợi ý vừa nhận bằng một trong 3 lệnh:\n\n"
    "- `đánh giá đúng`\n"
    "- `đánh giá sai`\n"
    "- `đánh giá một phần`\n\n"
    "_Gõ ngay trong ô chat, ngay sau câu trả lời chứa gợi ý._"
)


def _parse_rating(question: str) -> Optional[str]:
    """Extract the rating from a rate command; None when not parseable."""
    q = _squash(question)
    if not (q.startswith("danh gia goi y") or q in _RATE_EXACT):
        return None
    if "mot phan" in q:
        return RATING_PARTIAL
    if re.search(r"\bsai\b", q):
        return RATING_WRONG
    if re.search(r"\bdung\b", q):
        return RATING_CORRECT
    return None


class _RateAction(ChatAction):
    """Matches only explicit rate commands (never hijacks plain questions)."""

    def matches(self, request: ChatActionRequest) -> bool:
        return _parse_rating(request.question or "") is not None


def _rate_handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    db_path = resolve_db_path(request)
    if db_path is None:
        return None
    rating = _parse_rating(request.question or "")
    if rating is None:  # defensive; matches() already filtered
        return _message(RATE_ACTION_NAME, RATE_TITLE, _RATE_HELP)
    try:
        conn = _store.connect(db_path)
    except Exception:
        return None
    try:
        _feedback.init_feedback_loop(conn)
        conv = request.conversation_id or ""
        call = _feedback.latest_unrated_suggestion_call(conn, conv or None)
        updated = False
        if call is None:
            call = _feedback.latest_suggestion_call(conn, conv or None)
            updated = True
        if call is None:
            return _message(
                RATE_ACTION_NAME,
                RATE_TITLE,
                "Chưa có gợi ý nào trong cuộc trò chuyện này để đánh giá.\n\n"
                "Hãy tra cứu lỗi trước (VD: gõ `F000`), rồi đánh giá gợi ý nhận được.",
            )
        _feedback.record_rating(conn, int(call["id"]), rating)
        try:
            refs = json.loads(call["suggested_refs"] or "[]")
        except (ValueError, TypeError):
            refs = []
        ref_label = ", ".join(f"`{r}`" for r in refs[:5]) or "gợi ý vừa rồi"
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass
    note = " (cập nhật đánh giá trước đó)" if updated else ""
    return _message(
        RATE_ACTION_NAME,
        RATE_TITLE,
        f"Đã ghi nhận đánh giá: **{rating}** cho {ref_label}{note}.",
    )


# ---------------------------------------------------------------------------
# 2. dong_phieu_loi — close an error ticket (B2 hard rules enforced)
# ---------------------------------------------------------------------------

CLOSE_ACTION_NAME = "dong_phieu_loi"
CLOSE_TITLE = "Đóng phiếu lỗi"

_CLOSE_LABELS: Dict[str, str] = {
    "ma phieu": "case_ref",
    "phieu": "case_ref",
    "nguyen nhan that": "actual_cause",
    "doi sach that": "actual_countermeasure",
    "hien tuong": "phenomenon",
    "cong doan": "process_stage",
}

_CLOSE_TEMPLATE = """### Đóng phiếu lỗi

Để đóng phiếu, gửi lại theo mẫu — dòng đầu là `đóng phiếu`:

```
đóng phiếu
mã phiếu: 2026/2422
nguyên nhân thật: ...
đối sách thật: ...
```

- **Bắt buộc:** nguyên nhân thật + đối sách thật (thiếu thì không đóng được).
- **Phiếu mới (từ 2026):** bắt buộc thêm `hiện tượng:` và `công đoạn:`.
- Nguyên nhân/đối sách thật được ghi ngược vào kho tri thức khi đóng.
"""


def _parse_close_form(question: str) -> Dict[str, str]:
    """Parse "Label: value" lines of a close-ticket submission."""
    parsed: Dict[str, str] = {}
    for line in str(question or "").splitlines():
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        key = _CLOSE_LABELS.get(normalize_text(label))
        if key and value.strip() and key not in parsed:
            parsed[key] = value.strip()
    ref = parsed.get("case_ref", "")
    ref = re.sub(r"(?i)^phieu\s+", "", ref).strip()
    if ref:
        parsed["case_ref"] = ref
    return parsed


class _CloseAction(ChatAction):
    def matches(self, request: ChatActionRequest) -> bool:
        q = _squash(request.question or "")
        return q.startswith("dong phieu") or q.startswith("chot phieu")


def _close_handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    db_path = resolve_db_path(request)
    if db_path is None:
        return None
    parsed = _parse_close_form(request.question or "")
    if not parsed.get("case_ref") or not (
        parsed.get("actual_cause") or parsed.get("actual_countermeasure")
    ):
        return _message(CLOSE_ACTION_NAME, CLOSE_TITLE, _CLOSE_TEMPLATE)
    try:
        conn = _store.connect(db_path)
    except Exception:
        return None
    try:
        _feedback.init_feedback_loop(conn)
        row = conn.execute(
            "SELECT id, no_dvd FROM error_cases WHERE no_dvd = ?",
            (parsed["case_ref"],),
        ).fetchone()
        if row is None:
            return _message(
                CLOSE_ACTION_NAME,
                CLOSE_TITLE,
                f"Không tìm thấy phiếu `{parsed['case_ref']}` trong DB. "
                "Kiểm tra lại mã phiếu rồi gửi lại.",
            )
        case_id = int(row["id"])
        try:
            _feedback.close_case(
                conn,
                case_id,
                actual_cause=parsed.get("actual_cause") or "",
                actual_countermeasure=parsed.get("actual_countermeasure") or "",
                phenomenon=parsed.get("phenomenon"),
                process_stage=parsed.get("process_stage"),
            )
        except ClosureBlockedError as blocked:
            # The B2 hard rule, in plain Vietnamese — never a traceback.
            return _message(
                CLOSE_ACTION_NAME, CLOSE_TITLE, f"### Chưa đóng được phiếu\n\n{blocked}"
            )
        filled = []
        for label, key in (
            ("Hiện tượng", "phenomenon"),
            ("Công đoạn", "process_stage"),
        ):
            if parsed.get(key):
                filled.append(f"{label} đã ghi vào phiếu")
        extra = ("\n- " + "\n- ".join(filled)) if filled else ""
        return _message(
            CLOSE_ACTION_NAME,
            CLOSE_TITLE,
            "### Đã đóng phiếu `{}`\n\n"
            "- Nguyên nhân thật + đối sách thật đã ghi ngược vào kho tri thức.\n"
            "- Phiếu được đánh dấu hoàn thành.".format(parsed["case_ref"]) + extra,
        )
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 3. bao_cao_phan_hoi — feedback metrics report
# ---------------------------------------------------------------------------

REPORT_ACTION_NAME = "bao_cao_phan_hoi"
REPORT_TITLE = "Báo cáo vòng phản hồi"

_COVERAGE_TARGET = 0.80


class _ReportAction(ChatAction):
    def matches(self, request: ChatActionRequest) -> bool:
        q = _squash(request.question or "")
        return q.startswith(
            (
                "bao cao phan hoi",
                "thong ke phan hoi",
                "thong ke danh gia",
                "ti le danh gia",
                "ti le goi y",
            )
        )


def _pct(value: float) -> str:
    return f"{round(value * 100)}%"


def _report_handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    db_path = resolve_db_path(request)
    if db_path is None:
        return None
    try:
        conn = _open_ro(db_path)
    except Exception:
        return None
    try:
        has = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='suggestion_calls'"
        ).fetchone()
        if not has:
            return _message(
                REPORT_ACTION_NAME,
                REPORT_TITLE,
                "Chưa có dữ liệu phản hồi nào — hãy tra cứu và đánh giá gợi ý trước.",
            )
        cov = _feedback.rating_coverage(conn)
        by_quarter = _feedback.positive_rate_by_quarter(conn)
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass
    target_ok = cov["coverage"] >= _COVERAGE_TARGET
    head = (
        "### Báo cáo vòng phản hồi\n\n"
        f"- Lượt gợi ý: **{cov['calls']}** · đã đánh giá: **{cov['rated']}**\n"
        f"- **Tỉ lệ có đánh giá: {_pct(cov['coverage'])}** "
        f"(mục tiêu ≥ {_pct(_COVERAGE_TARGET)}) — "
        f"{'Đạt ✅' if target_ok else 'Chưa đạt ⚠️'}\n"
    )
    rows: Tuple[Tuple[str, ...], ...] = tuple(
        (
            quarter,
            str(stats["rated"]),
            str(stats["positive"]),
            _pct(stats["rate"]),
        )
        for quarter, stats in by_quarter.items()
    )
    blocks = [ChatActionBlock(kind=BLOCK_MARKDOWN, text=head)]
    if rows:
        blocks.append(
            ChatActionBlock(
                kind=BLOCK_TABLE,
                headers=("Quý", "Lượt được đánh giá", "Đúng / một phần", "Tỉ lệ"),
                rows=rows,
                caption="Tỉ lệ đúng/một phần theo quý (đánh giá mới nhất của mỗi lượt gợi ý).",
            )
        )
    else:
        blocks.append(
            ChatActionBlock(
                kind=BLOCK_MARKDOWN,
                text="_Chưa có lượt đánh giá nào — bảng theo quý sẽ hiện khi có dữ liệu._",
            )
        )
    return ChatActionOutcome(
        action=REPORT_ACTION_NAME, title=REPORT_TITLE, blocks=tuple(blocks)
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    register_action(
        _RateAction(
            name=RATE_ACTION_NAME,
            title=RATE_TITLE,
            hints=("danh gia goi y",),
            handler=_rate_handler,
            description=(
                "Đánh giá gợi ý vừa nhận: gõ 'đánh giá đúng' / 'đánh giá sai' / "
                "'đánh giá một phần' ngay trong ô chat — ghi log vào vòng phản hồi."
            ),
        )
    )
    register_action(
        _CloseAction(
            name=CLOSE_ACTION_NAME,
            title=CLOSE_TITLE,
            hints=("dong phieu",),
            handler=_close_handler,
            description=(
                "Đóng phiếu lỗi từ chat: 'đóng phiếu' + mã phiếu / nguyên nhân thật / "
                "đối sách thật — luật cứng B2 chặn khi thiếu trường bắt buộc."
            ),
        )
    )
    register_action(
        _ReportAction(
            name=REPORT_ACTION_NAME,
            title=REPORT_TITLE,
            hints=("bao cao phan hoi",),
            handler=_report_handler,
            description=(
                "Báo cáo vòng phản hồi: % lượt gợi ý có đánh giá (mục tiêu ≥ 80%) "
                "và tỉ lệ đúng/một phần theo quý."
            ),
        )
    )


register()
