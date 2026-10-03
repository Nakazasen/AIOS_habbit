"""Diem hung feedback + metric cho agent tao/sua bao cao bang loi (UX-AGENT-REPORT).

Vong lap cai thien lien tuc (theo quyet dinh user 2026-10-03):
1. Hung feedback ngay tai cho dung: moi lan agent tao/sua bao cao deu ghi
   `local_cases/agent_report_actions.jsonl`; user cham dung/mot_phan/sai ngay
   tren ket qua (ghi `local_cases/agent_report_feedback.jsonl`).
2. Metric do duoc: ti le thanh cong, ti le phai sua lai (redo rate).
3. Vong xem lai: `improvement_overview()` gom theo ky, tra xu huong giam_dan /
   khong_giam / khong_du_du_lieu de UI hien trong lan xem lai dinh ky.

Chi ghi local_cases, KHONG ghi vao kho tri thuc. Tuong thich Python 3.11.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ACTION_LOG_NAME = "agent_report_actions.jsonl"
FEEDBACK_LOG_NAME = "agent_report_feedback.jsonl"

VERDICT_GOOD = "dung"
VERDICT_PARTIAL = "mot_phan"
VERDICT_BAD = "sai"
VALID_VERDICTS = (VERDICT_GOOD, VERDICT_PARTIAL, VERDICT_BAD)

# Verdict khong dat thi bat buoc du 3 truong (giong suggestion_feedback).
_REQUIRED_FIELDS = (
    ("ly_do", "lý do"),
    ("nguyen_nhan_that", "nguyên nhân thật"),
    ("noi_dung_nan_lai", "nội dung nắn lại"),
)


class ReportFeedbackError(ValueError):
    """Raised khi feedback thieu truong bat buoc."""


def _local_cases_dir() -> Path:
    base = os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    root = Path(base) if base else Path.cwd() / "local_cases"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _append_jsonl(path: Path, record: Dict[str, Any]) -> Dict[str, Any]:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def log_report_action(
    *,
    work_id: str = "",
    command: str = "",
    filename: str = "",
    kind: str = "",
    ok: bool = True,
    applied: int = 0,
    backup: str = "",
    error: str = "",
) -> Dict[str, Any]:
    """Ghi 1 lan agent tao/sua bao cao vao log van hanh (diem 1 cua vong lap)."""
    record = {
        "event_id": uuid.uuid4().hex[:12],
        "work_id": work_id or ("ARE-" + uuid.uuid4().hex[:8].upper()),
        "command": command,
        "filename": filename,
        "kind": kind,
        "ok": bool(ok),
        "applied": int(applied),
        "backup": backup,
        "error": error,
        "created_at": _utc_now_iso(),
    }
    return _append_jsonl(_local_cases_dir() / ACTION_LOG_NAME, record)


def record_report_feedback(
    work_id: str,
    user: str,
    verdict: str,
    *,
    ly_do: str = "",
    nguyen_nhan_that: str = "",
    noi_dung_nan_lai: str = "",
    reason: str = "",
    true_cause: str = "",
    correction: str = "",
) -> Dict[str, Any]:
    """User cham ket qua tao/sua bao cao.

    verdict: "dung" | "mot_phan" | "sai". Neu khac "dung" thi bat buoc du
    3 truong (ly do, nguyen nhan that, noi dung nan lai) — thieu thi raise
    ReportFeedbackError (ValueError) voi thong bao tieng Viet, khong ghi log.
    Nhan ca ten truong tieng Viet lan tieng Anh.
    """
    verdict_norm = str(verdict or "").strip().lower()
    if verdict_norm not in VALID_VERDICTS:
        raise ReportFeedbackError(
            "Chấm không hợp lệ: chỉ nhận 'đúng', 'một phần' hoặc 'sai'."
        )
    merged = {
        "ly_do": ly_do or reason,
        "nguyen_nhan_that": nguyen_nhan_that or true_cause,
        "noi_dung_nan_lai": noi_dung_nan_lai or correction,
    }
    if verdict_norm != VERDICT_GOOD:
        missing = [label for key, label in _REQUIRED_FIELDS if not str(merged[key]).strip()]
        if missing:
            raise ReportFeedbackError(
                "Chấm '%s' thì phải ghi đủ: %s. Thiếu %s nên chưa lưu."
                % (verdict, ", ".join(label for _, label in _REQUIRED_FIELDS),
                   ", ".join(missing))
            )
    record = {
        "event_id": uuid.uuid4().hex[:12],
        "work_id": work_id,
        "user": user,
        "verdict": verdict_norm,
        "ly_do": str(merged["ly_do"]).strip(),
        "nguyen_nhan_that": str(merged["nguyen_nhan_that"]).strip(),
        "noi_dung_nan_lai": str(merged["noi_dung_nan_lai"]).strip(),
        "created_at": _utc_now_iso(),
    }
    return _append_jsonl(_local_cases_dir() / FEEDBACK_LOG_NAME, record)


def action_metrics() -> Dict[str, Any]:
    """Metric hanh dong: tong so, ti le thanh cong, theo dinh dang/loai."""
    actions = _read_jsonl(_local_cases_dir() / ACTION_LOG_NAME)
    total = len(actions)
    ok_count = sum(1 for a in actions if a.get("ok"))
    by_format: Dict[str, int] = {}
    by_kind: Dict[str, int] = {}
    for action in actions:
        suffix = Path(str(action.get("filename", ""))).suffix.lower() or "?"
        by_format[suffix] = by_format.get(suffix, 0) + 1
        kind = str(action.get("kind", "") or "?")
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "total": total,
        "ok": ok_count,
        "failed": total - ok_count,
        "success_rate": round(ok_count / total, 3) if total else None,
        "by_format": by_format,
        "by_kind": by_kind,
    }


def feedback_metrics() -> Dict[str, Any]:
    """Metric feedback: ti le cham + ti le phai sua lai (redo rate)."""
    feedbacks = _read_jsonl(_local_cases_dir() / FEEDBACK_LOG_NAME)
    total = len(feedbacks)
    counts = {v: 0 for v in VALID_VERDICTS}
    for feedback in feedbacks:
        verdict = str(feedback.get("verdict", ""))
        if verdict in counts:
            counts[verdict] += 1
    redo = counts[VERDICT_PARTIAL] + counts[VERDICT_BAD]
    return {
        "total": total,
        VERDICT_GOOD: counts[VERDICT_GOOD],
        VERDICT_PARTIAL: counts[VERDICT_PARTIAL],
        VERDICT_BAD: counts[VERDICT_BAD],
        "redo_rate": round(redo / total, 3) if total else None,
    }


def _redo_rate(records: List[Dict[str, Any]]) -> float | None:
    total = len(records)
    if not total:
        return None
    redo = sum(
        1 for r in records if str(r.get("verdict", "")) in (VERDICT_PARTIAL, VERDICT_BAD)
    )
    return redo / total


def improvement_overview() -> Dict[str, Any]:
    """Goi tong quan cho vong xem lai: metric + xu huong redo rate theo ky.

    Chia lich su feedback lam 2 nua theo thoi gian; nua sau co redo rate thap
    hon dang ke thi xu huong "giam_dan" (vong lap dang chay tot).
    """
    feedbacks = _read_jsonl(_local_cases_dir() / FEEDBACK_LOG_NAME)
    feedbacks.sort(key=lambda r: str(r.get("created_at", "")))
    trend = "khong_du_du_lieu"
    first_rate = second_rate = None
    if len(feedbacks) >= 4:
        half = len(feedbacks) // 2
        first_rate = _redo_rate(feedbacks[:half])
        second_rate = _redo_rate(feedbacks[half:])
        if first_rate is not None and second_rate is not None:
            trend = "giam_dan" if second_rate < first_rate else "khong_giam"
    return {
        "actions": action_metrics(),
        "feedback": feedback_metrics(),
        "xu_huong": trend,
        "redo_rate_ky_truoc": first_rate,
        "redo_rate_ky_nay": second_rate,
    }
