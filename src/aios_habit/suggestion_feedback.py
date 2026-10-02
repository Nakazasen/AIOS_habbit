"""Feedback cua chuyen gia cho tung GOI Y cua AI (UX-INTERVIEW-FEEDBACK).

Vong lap cai thien lien tuc cho goi y chan doan/huong dieu tra:
- AI log goi y khi dua ra (`log_suggestion`).
- Chuyen gia cham: `dung` / `mot_phan` / `sai`.
- `sai` hoac `mot_phan` BAT BUOC nhap du 3 truong: ly do sai, nguyen nhan
  that (ground truth), noi dung nan lai.
- Luu JSONL tai `local_cases/suggestion_feedback.jsonl` — KHONG vao kho tri
  thuc. `improvement_report()` tong hop de vong xem lai cai thien.

Tuong thich Python 3.11.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

VERDICT_DUNG = "dung"
VERDICT_MOT_PHAN = "mot_phan"
VERDICT_SAI = "sai"
_VERDICTS = (VERDICT_DUNG, VERDICT_MOT_PHAN, VERDICT_SAI)

MAX_CONTENT_CHARS = 4000
MAX_FIELD_CHARS = 2000


def feedback_file() -> Path:
    base = Path(os.environ.get("AIOS_LOCAL_CASES_DIR", "") or Path.cwd() / "local_cases")
    return base / "suggestion_feedback.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log_suggestion(
    suggestion_id: str,
    content: str,
    *,
    context: str = "",
    source: str = "",
) -> Dict:
    """AI ghi lai mot goi y vua dua ra de chuyen gia cham sau."""
    suggestion_id = str(suggestion_id or "").strip()
    if not suggestion_id:
        return {"ok": False, "error_vi": "Thiếu mã gợi ý."}
    record = {
        "type": "suggestion",
        "suggestion_id": suggestion_id,
        "content": str(content or "")[:MAX_CONTENT_CHARS],
        "context": str(context or "")[:MAX_FIELD_CHARS],
        "source": str(source or "")[:200],
        "created_at": _now_iso(),
    }
    _append(record)
    return {"ok": True, "suggestion_id": suggestion_id}


def record_feedback(
    suggestion_id: str,
    expert: str,
    verdict: str,
    *,
    reason: str = "",
    true_cause: str = "",
    correction: str = "",
) -> Dict:
    """Chuyen gia cham mot goi y. Sai/mot_phan bat buoc du 3 truong."""
    suggestion_id = str(suggestion_id or "").strip()
    verdict = str(verdict or "").strip()
    if not suggestion_id:
        return {"ok": False, "error_vi": "Thiếu mã gợi ý."}
    if verdict not in _VERDICTS:
        return {"ok": False, "error_vi": "Đánh giá phải là: đúng / một phần / sai."}
    reason = str(reason or "").strip()
    true_cause = str(true_cause or "").strip()
    correction = str(correction or "").strip()
    if verdict in (VERDICT_SAI, VERDICT_MOT_PHAN):
        missing = []
        if not reason:
            missing.append("lý do")
        if not true_cause:
            missing.append("nguyên nhân thật")
        if not correction:
            missing.append("nội dung nắn lại")
        if missing:
            return {
                "ok": False,
                "error_vi": (
                    "Chấm '%s' thì phải nhập đủ: %s."
                    % ("sai" if verdict == VERDICT_SAI else "một phần", ", ".join(missing))
                ),
            }
    record = {
        "type": "feedback",
        "suggestion_id": suggestion_id,
        "expert": str(expert or "")[:200],
        "verdict": verdict,
        "reason": reason[:MAX_FIELD_CHARS],
        "true_cause": true_cause[:MAX_FIELD_CHARS],
        "correction": correction[:MAX_FIELD_CHARS],
        "created_at": _now_iso(),
    }
    _append(record)
    return {"ok": True}


def _append(record: Dict) -> None:
    path = feedback_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_all() -> List[Dict]:
    path = feedback_file()
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue
    return records


def get_suggestion(suggestion_id: str) -> Optional[Dict]:
    for record in _read_all():
        if record.get("type") == "suggestion" and record.get("suggestion_id") == suggestion_id:
            return record
    return None


def get_feedback(suggestion_id: str) -> List[Dict]:
    return [
        r
        for r in _read_all()
        if r.get("type") == "feedback" and r.get("suggestion_id") == suggestion_id
    ]


def feedback_stats() -> Dict:
    """Metric vong lap: ti le goi y dung, top ly do sai."""
    records = _read_all()
    feedbacks = [r for r in records if r.get("type") == "feedback"]
    total = len(feedbacks)
    by_verdict = Counter(r.get("verdict", "") for r in feedbacks)
    reasons = Counter(
        str(r.get("reason", "")).strip()[:120]
        for r in feedbacks
        if r.get("verdict") in (VERDICT_SAI, VERDICT_MOT_PHAN) and str(r.get("reason", "")).strip()
    )
    return {
        "total": total,
        "dung": by_verdict.get(VERDICT_DUNG, 0),
        "mot_phan": by_verdict.get(VERDICT_MOT_PHAN, 0),
        "sai": by_verdict.get(VERDICT_SAI, 0),
        "ti_le_dung": round(by_verdict.get(VERDICT_DUNG, 0) / total, 3) if total else 0.0,
        "top_ly_do_sai": [
            {"ly_do": text, "so_lan": count} for text, count in reasons.most_common(10)
        ],
    }


def improvement_report(limit: int = 50) -> Dict:
    """Bao cao vong xem lai: goi y bi che + noi dung nan lai cua chuyen gia."""
    records = _read_all()
    suggestions = {
        r["suggestion_id"]: r for r in records if r.get("type") == "suggestion"
    }
    corrections = []
    for r in records:
        if r.get("type") != "feedback":
            continue
        if r.get("verdict") not in (VERDICT_SAI, VERDICT_MOT_PHAN):
            continue
        sid = r.get("suggestion_id", "")
        sug = suggestions.get(sid, {})
        corrections.append(
            {
                "suggestion_id": sid,
                "goi_y_goc": str(sug.get("content", ""))[:500],
                "verdict": r.get("verdict"),
                "ly_do": r.get("reason", ""),
                "nguyen_nhan_that": r.get("true_cause", ""),
                "noi_dung_nan_lai": r.get("correction", ""),
                "chuyen_gia": r.get("expert", ""),
                "created_at": r.get("created_at", ""),
            }
        )
    corrections.sort(key=lambda c: c["created_at"], reverse=True)
    return {
        "stats": feedback_stats(),
        "can_nan_lai": corrections[:limit],
        "so_muc_can_xem_lai": len(corrections),
    }
