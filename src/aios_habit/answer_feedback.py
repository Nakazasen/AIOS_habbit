"""Feedback cau tra loi ngay tren khung chat (vong lap cai thien lien tuc).

- Nguoi dung cham thumbs up/down duoi moi cau tra loi cua assistant.
- Cham "chua huu ich" thi BAT BUOC nhap ly do (giong nguyen tac feedback
  chuyen gia: che thi phai noi ro che gi).
- Luu JSONL tai `local_cases/answer_feedback.jsonl` — KHONG BAO GIO ghi vao
  kho tri thuc hay luong tra loi chinh. Day la du lieu van hanh cho vong lap
  cai thien, khong phai tri thuc da duyet.
- `feedback_stats()` cho metric vong lap: ti le huu ich theo thoi gian.

Tuong thich Python 3.11.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

RATING_HUU_ICH = "huu_ich"
RATING_CHUA_HUU_ICH = "chua_huu_ich"
_RATINGS = (RATING_HUU_ICH, RATING_CHUA_HUU_ICH)

# Gioi han do dai de file JSONL khong phong to vo han.
MAX_QUESTION_CHARS = 2000
MAX_ANSWER_CHARS = 4000
MAX_REASON_CHARS = 2000


def feedback_file() -> Path:
    base = Path(os.environ.get("AIOS_LOCAL_CASES_DIR", "") or Path.cwd() / "local_cases")
    return base / "answer_feedback.jsonl"


def record_feedback(
    conversation_id: str,
    message_id: str,
    question: str,
    answer: str,
    rating: str,
    *,
    reason: str = "",
    lane: str = "",
) -> Dict:
    """Ghi mot feedback. Tra ve {"ok": True} hoac {"ok": False, "error_vi": ...}."""
    rating = str(rating or "").strip()
    if rating not in _RATINGS:
        return {"ok": False, "error_vi": "Đánh giá không hợp lệ."}
    reason = str(reason or "").strip()
    if rating == RATING_CHUA_HUU_ICH and not reason:
        return {
            "ok": False,
            "error_vi": "Bạn chê câu trả lời thì cho mình xin lý do để cải thiện nhé.",
        }
    record = {
        "conversation_id": str(conversation_id or ""),
        "message_id": str(message_id or ""),
        "question": str(question or "")[:MAX_QUESTION_CHARS],
        "answer_excerpt": str(answer or "")[:MAX_ANSWER_CHARS],
        "rating": rating,
        "reason": reason[:MAX_REASON_CHARS],
        "lane": str(lane or ""),
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    path = feedback_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


def get_feedback(conversation_id: str, message_id: str) -> Optional[Dict]:
    """Lay feedback da ghi cho mot message (None neu chua co)."""
    path = feedback_file()
    if not path.exists():
        return None
    found = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if (
                str(record.get("conversation_id", "")) == str(conversation_id)
                and str(record.get("message_id", "")) == str(message_id)
            ):
                found = record
    return found


def iter_recent(limit: int = 200) -> List[Dict]:
    """Doc cac feedback gan nhat (toi da `limit`)."""
    path = feedback_file()
    if not path.exists():
        return []
    records: List[Dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue
    return records[-limit:]


def feedback_stats() -> Dict:
    """Metric vong lap: tong so, ti le huu ich, top ly do bi che."""
    records = iter_recent(limit=10000)
    total = len(records)
    good = sum(1 for r in records if r.get("rating") == RATING_HUU_ICH)
    bad = sum(1 for r in records if r.get("rating") == RATING_CHUA_HUU_ICH)
    reasons: Dict[str, int] = {}
    for r in records:
        if r.get("rating") == RATING_CHUA_HUU_ICH and str(r.get("reason", "")).strip():
            reasons[str(r["reason"]).strip()[:120]] = reasons.get(str(r["reason"]).strip()[:120], 0) + 1
    top_reasons = sorted(reasons.items(), key=lambda item: item[1], reverse=True)[:10]
    return {
        "total": total,
        "huu_ich": good,
        "chua_huu_ich": bad,
        "ti_le_huu_ich": round(good / total, 3) if total else 0.0,
        "top_ly_do_che": [{"ly_do": text, "so_lan": count} for text, count in top_reasons],
    }
