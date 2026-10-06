"""Feedback cho the canh bao realtime ngay trong khung chat.

- Nguoi dung cham dung/sai ngay duoi the canh bao.
- Cham "sai" thi BAT BUOC nhap ly do (giong nguyen tac answer_feedback:
  che thi phai noi ro che gi).
- Luu JSONL tai `local_cases/alert_feedback.jsonl` — KHONG BAO GIO ghi vao
  kho tri thuc hay luong tra loi chinh. Day la du lieu van hanh cho vong lap
  cai thien, khong phai tri thuc da duyet.
- `alert_feedback_stats()` cho metric vong lap: ti le dung theo thoi gian.

Tuong thich Python 3.11.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

RATING_DUNG = "dung"
RATING_SAI = "sai"
_RATINGS = (RATING_DUNG, RATING_SAI)

MAX_CHI_TIET_CHARS = 2000
MAX_LY_DO_CHARS = 2000


def alert_feedback_file() -> Path:
    base = Path(os.environ.get("AIOS_LOCAL_CASES_DIR", "") or Path.cwd() / "local_cases")
    return base / "alert_feedback.jsonl"


def record_alert_feedback(
    conversation_id: str,
    alert_id: str,
    jig_id: str,
    metric: str,
    rating: str,
    *,
    reason: str = "",
    chi_tiet: str = "",
) -> Dict:
    """Ghi mot feedback cho the canh bao. Tra ve {"ok": True} hoac loi tieng Viet."""
    rating = str(rating or "").strip()
    if rating not in _RATINGS:
        return {"ok": False, "error_vi": "Đánh giá không hợp lệ."}
    reason = str(reason or "").strip()
    if rating == RATING_SAI and not reason:
        return {
            "ok": False,
            "error_vi": "Bạn chê cảnh báo thì cho mình xin lý do để cải thiện nhé.",
        }
    record = {
        "conversation_id": str(conversation_id or ""),
        "alert_id": str(alert_id or ""),
        "jig_id": str(jig_id or ""),
        "metric": str(metric or ""),
        "chi_tiet": str(chi_tiet or "")[:MAX_CHI_TIET_CHARS],
        "rating": rating,
        "reason": reason[:MAX_LY_DO_CHARS],
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    path = alert_feedback_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


def get_alert_feedback(conversation_id: str, alert_id: str) -> Optional[Dict]:
    """Lay feedback da ghi cho mot the canh bao (None neu chua co)."""
    path = alert_feedback_file()
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
                and str(record.get("alert_id", "")) == str(alert_id)
            ):
                found = record
    return found


def iter_alert_recent(limit: int = 200) -> List[Dict]:
    """Doc cac feedback canh bao gan nhat (toi da `limit`)."""
    path = alert_feedback_file()
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


def alert_feedback_stats() -> Dict:
    """Metric vong lap: tong so, ti le dung, top ly do bi che."""
    records = iter_alert_recent(limit=10000)
    total = len(records)
    good = sum(1 for r in records if r.get("rating") == RATING_DUNG)
    bad = sum(1 for r in records if r.get("rating") == RATING_SAI)
    reasons: Dict[str, int] = {}
    for r in records:
        if r.get("rating") == RATING_SAI and str(r.get("reason", "")).strip():
            key = str(r["reason"]).strip()[:120]
            reasons[key] = reasons.get(key, 0) + 1
    top_reasons = sorted(reasons.items(), key=lambda item: item[1], reverse=True)[:10]
    return {
        "total": total,
        "dung": good,
        "sai": bad,
        "ti_le_dung": round(good / total, 3) if total else 0.0,
        "top_ly_do_che": [{"ly_do": text, "so_lan": count} for text, count in top_reasons],
    }
