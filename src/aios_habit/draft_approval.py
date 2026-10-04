"""Expert approval for draft answers (ticket DRAFT-APPROVAL).

Step 2 of the feedback loop: experts unlock with a PIN once per shift,
then approve / revise / reject directly under the draft answer in chat.
Approving only swaps the label, the pair stays in the draft store.
No import into the production index happens in this ticket.

Fail-closed behind ``AIOS_FEATURE_DRAFT_APPROVAL`` (default OFF).
PIN hash and decision logs live under ``local_cases/`` (never committed).

Compatible with Python 3.11.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from aios_habit.answer_draft_fallback import DRAFT_LABEL

FLAG_ENV_KEY = "AIOS_FEATURE_DRAFT_APPROVAL"

_overrides: Dict[str, bool] = {}

# PIN must be 4-6 digits (set by the user, shared with 2-3 experts).
PIN_MIN_LEN = 4
PIN_MAX_LEN = 6

# One unlock lasts a whole work shift.
UNLOCK_HOURS = 8

# Lock after repeated wrong PINs (no hint is ever revealed).
MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60

DECISION_APPROVED = "approved"
DECISION_REJECTED = "rejected"
DECISION_REVISED = "revised"
DECISION_UNAPPROVED = "unapproved"
_DECISIONS = (
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_REVISED,
    DECISION_UNAPPROVED,
)

REVIEW_GUIDE_VI = (
    "Cách xem lại định kỳ: mở nhật ký duyệt trong "
    "local_cases/draft_approval_log.jsonl, chạy hàm tính tỉ lệ duyệt theo mẻ "
    "(compute_approval_metrics), rồi đọc gợi ý cải thiện. Ngưỡng cần cải thiện: "
    "tỉ lệ duyệt dưới 70%, số cặp từ chối tăng 3 mẻ liên tiếp, "
    "hoặc còn trên 20% cặp chưa duyệt sau 2 vòng xem lại."
)


def set_draft_approval_override(enabled: bool) -> None:
    """Set an in-memory flag override (used by tests)."""
    _overrides["enabled"] = bool(enabled)


def clear_draft_approval_override() -> None:
    """Clear the in-memory flag override."""
    _overrides.pop("enabled", None)


def draft_approval_enabled() -> bool:
    """Return True only when the approval lane is explicitly enabled."""
    if "enabled" in _overrides:
        return _overrides["enabled"]
    raw = os.environ.get(FLAG_ENV_KEY, "")
    if not raw.strip():
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _local_cases_dir() -> Path:
    base = os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    if base.strip():
        return Path(base.strip())
    return Path.cwd() / "local_cases"


def config_path() -> Path:
    return _local_cases_dir() / "draft_approval_config.json"


def log_path() -> Path:
    return _local_cases_dir() / "draft_approval_log.jsonl"


def versions_path() -> Path:
    return _local_cases_dir() / "draft_approval_versions.jsonl"


def attempts_path() -> Path:
    return _local_cases_dir() / "draft_approval_attempts.json"


def pin_format_ok(pin: str) -> bool:
    """Check the PIN has 4-6 digits (nothing else is accepted)."""
    text = str(pin or "").strip()
    if len(text) < PIN_MIN_LEN or len(text) > PIN_MAX_LEN:
        return False
    return text.isdigit()


def new_salt() -> str:
    return secrets.token_hex(16)


def hash_pin(pin: str, salt: str) -> str:
    """Hash a PIN with salt (SHA-256, hex)."""
    payload = f"{salt}:{str(pin or '').strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_pin_hash(pin: str, salt: str, expected_hash: str) -> bool:
    """Compare a PIN against its hash in constant time."""
    candidate = hash_pin(pin, salt)
    return hmac.compare_digest(candidate, str(expected_hash or ""))


def set_pin(pin: str) -> Dict:
    """Set a new expert PIN (stores only salt + hash locally)."""
    if not pin_format_ok(pin):
        return {"ok": False, "error_vi": "Mã PIN phải gồm 4–6 chữ số."}
    salt = new_salt()
    payload = {"salt": salt, "pin_hash": hash_pin(pin, salt)}
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    clear_failed_attempts()
    return {"ok": True}


def load_pin_store() -> Dict:
    """Load salt + hash from the local config (empty dict when unset)."""
    path = config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _read_attempts() -> Dict:
    path = attempts_path()
    if not path.exists():
        return {"failed": 0, "locked_until": 0.0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"failed": 0, "locked_until": 0.0}
    if not isinstance(data, dict):
        return {"failed": 0, "locked_until": 0.0}
    return {
        "failed": int(data.get("failed", 0) or 0),
        "locked_until": float(data.get("locked_until", 0.0) or 0.0),
    }


def _write_attempts(failed: int, locked_until: float) -> None:
    path = attempts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"failed": failed, "locked_until": locked_until}, ensure_ascii=False),
        encoding="utf-8",
    )


def is_locked(now: float | None = None) -> bool:
    """Return True while the PIN entry is temporarily locked."""
    current = float(now if now is not None else time.time())
    return current < float(_read_attempts().get("locked_until", 0.0))


def record_failed_attempt(now: float | None = None) -> Dict:
    """Count one wrong PIN; lock after too many failures."""
    current = float(now if now is not None else time.time())
    state = _read_attempts()
    failed = int(state.get("failed", 0)) + 1
    locked_until = float(state.get("locked_until", 0.0))
    if failed >= MAX_FAILED_ATTEMPTS:
        locked_until = current + LOCK_SECONDS
    _write_attempts(failed, locked_until)
    return {"failed": failed, "locked_until": locked_until}


def clear_failed_attempts() -> None:
    """Reset the wrong-PIN counter (called after a correct PIN)."""
    _write_attempts(0, 0.0)


def verify_pin(pin: str, now: float | None = None) -> Dict:
    """Verify an expert PIN without revealing any hint on failure."""
    if is_locked(now=now):
        return {"ok": False, "error_vi": "Bạn nhập sai nhiều lần. Hãy chờ một lúc rồi thử lại."}
    store = load_pin_store()
    salt = str(store.get("salt", "") or "")
    expected = str(store.get("pin_hash", "") or "")
    if not salt or not expected:
        return {"ok": False, "error_vi": "Chưa đặt mã PIN duyệt. Hãy nhờ người phụ trách đặt mã trước."}
    if verify_pin_hash(pin, salt, expected):
        clear_failed_attempts()
        return {"ok": True}
    record_failed_attempt(now=now)
    return {"ok": False, "error_vi": "Mã PIN chưa đúng. Bạn kiểm tra lại rồi thử nhé."}


def new_unlock_until(hours: float = UNLOCK_HOURS, now: float | None = None) -> float:
    """Create an unlock expiry timestamp (one work shift by default)."""
    current = float(now if now is not None else time.time())
    return current + float(hours) * 3600.0


def unlock_valid(unlocked_until: float | None, now: float | None = None) -> bool:
    """Check whether a shift unlock is still valid."""
    if not unlocked_until:
        return False
    current = float(now if now is not None else time.time())
    try:
        return current < float(unlocked_until)
    except (TypeError, ValueError):
        return False


def is_draft_answer(answer_text: str) -> bool:
    """Return True when the answer still carries the draft label."""
    return DRAFT_LABEL in str(answer_text or "")


_APPROVED_LABEL_RE = re.compile(r"Đã duyệt bởi .+, ngày \d{4}-\d{2}-\d{2}")


def is_approved_answer(answer_text: str) -> bool:
    """Return True when the answer carries an approval label."""
    return bool(_APPROVED_LABEL_RE.search(str(answer_text or "")))


def format_approved_label(reviewer_name: str, date_str: str) -> str:
    """Build the approval label (reviewer name + date, no warehouse write)."""
    return f"Đã duyệt bởi {reviewer_name.strip()}, ngày {date_str.strip()}"


def today_str() -> str:
    return datetime.now().astimezone().date().isoformat()


def apply_approval_label(answer_text: str, reviewer_name: str, date_str: str = "") -> Dict:
    """Swap the draft label for the approval label (pair stays in drafts)."""
    name = str(reviewer_name or "").strip()
    if not name:
        return {"ok": False, "error_vi": "Bạn cho mình xin tên người duyệt để ghi nhật ký nhé."}
    day = str(date_str or "").strip() or today_str()
    text = str(answer_text or "")
    if DRAFT_LABEL not in text:
        return {"ok": False, "error_vi": "Câu trả lời này không phải bản thảo nên không duyệt được."}
    label = format_approved_label(name, day)
    return {"ok": True, "answer_text": text.replace(DRAFT_LABEL, label), "label": label}


def remove_approval_label(answer_text: str) -> Dict:
    """Undo an approval (restore the draft label, keep the pair in drafts)."""
    text = str(answer_text or "")
    match = _APPROVED_LABEL_RE.search(text)
    if not match:
        return {"ok": False, "error_vi": "Câu trả lời này chưa được duyệt nên không cần gỡ."}
    restored = text[: match.start()] + DRAFT_LABEL + text[match.end():]
    return {"ok": True, "answer_text": restored}


def batch_of(source_file: str) -> str:
    """Extract a batch name (file stem) for per-batch metrics."""
    name = str(source_file or "").strip().replace("\\", "/").split("/")[-1]
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name or "không rõ mẻ"


def record_decision(
    pair_id: str,
    reviewer_name: str,
    decision: str,
    *,
    reason: str = "",
    version: int = 1,
    source_file: str = "",
    batch: str = "",
) -> Dict:
    """Append one approval decision (pair stays in the draft store)."""
    pid = str(pair_id or "").strip()
    name = str(reviewer_name or "").strip()
    choice = str(decision or "").strip()
    note = str(reason or "").strip()
    if not pid:
        return {"ok": False, "error_vi": "Thiếu mã cặp bản thảo nên chưa ghi được."}
    if not name:
        return {"ok": False, "error_vi": "Bạn cho mình xin tên người duyệt để ghi nhật ký nhé."}
    if choice not in _DECISIONS:
        return {"ok": False, "error_vi": "Quyết định duyệt chưa hợp lệ."}
    if choice == DECISION_REJECTED and not note:
        return {"ok": False, "error_vi": "Bạn từ chối thì cho mình xin lý do để cải thiện nhé."}
    record = {
        "pair_id": pid,
        "reviewer_name": name,
        "decided_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "decision": choice,
        "reason": note,
        "version": int(version or 1),
        "source_file": str(source_file or ""),
        "batch": str(batch or "").strip() or batch_of(source_file),
    }
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "record": record}


def read_decisions(limit: int = 10000) -> List[Dict]:
    """Read recent approval decisions (newest last, tolerant of bad lines)."""
    path = log_path()
    if not path.exists():
        return []
    records: List[Dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                records.append(item)
    if limit <= 0:
        return []
    return records[-limit:]


@dataclass(frozen=True)
class ApprovalMetrics:
    """Measurable review metrics: approval share per batch + totals."""

    total_tracked: int = 0
    approved: int = 0
    rejected: int = 0
    pending: int = 0
    approval_rate: float = 0.0
    rejection_rate: float = 0.0
    by_batch: Dict[str, Dict[str, int]] | None = None


def _latest_decision_by_pair(records: Sequence[Dict]) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    for item in records or []:
        pid = str(item.get("pair_id", "") or "").strip()
        if pid:
            latest[pid] = item
    return latest


def compute_approval_metrics(
    records: Sequence[Dict] | None = None,
    *,
    total_tracked: int = 0,
    pair_ids: Sequence[str] | None = None,
) -> ApprovalMetrics:
    """Compute approved / rejected / pending + per-batch counts.

    Only the latest decision per pair counts. ``revised`` counts as approved
    (a new version was approved). ``unapproved`` counts as pending again.
    """
    items = list(records) if records else read_decisions()
    latest = _latest_decision_by_pair(items)
    if pair_ids:
        wanted = {str(pid or "").strip() for pid in pair_ids if str(pid or "").strip()}
        latest = {pid: rec for pid, rec in latest.items() if pid in wanted}
        tracked = len(wanted)
    else:
        tracked = int(total_tracked or 0) or len(latest)
        if tracked < len(latest):
            tracked = len(latest)
    approved_ids = {
        pid
        for pid, rec in latest.items()
        if str(rec.get("decision", "")) in (DECISION_APPROVED, DECISION_REVISED)
    }
    rejected_ids = {
        pid for pid, rec in latest.items() if str(rec.get("decision", "")) == DECISION_REJECTED
    }
    approved = len(approved_ids)
    rejected = len(rejected_ids)
    pending = max(0, tracked - approved - rejected)
    by_batch: Dict[str, Dict[str, int]] = {}
    for pid, rec in latest.items():
        key = str(rec.get("batch", "") or "").strip() or batch_of(str(rec.get("source_file", "")))
        slot = by_batch.setdefault(key, {"theo_doi": 0, "da_duyet": 0, "tu_choi": 0})
        slot["theo_doi"] += 1
        if pid in approved_ids:
            slot["da_duyet"] += 1
        elif pid in rejected_ids:
            slot["tu_choi"] += 1
    return ApprovalMetrics(
        total_tracked=tracked,
        approved=approved,
        rejected=rejected,
        pending=pending,
        approval_rate=round(approved / tracked, 3) if tracked else 0.0,
        rejection_rate=round(rejected / tracked, 3) if tracked else 0.0,
        by_batch=by_batch,
    )


def approval_review_hints(metrics: ApprovalMetrics) -> List[str]:
    """Short Vietnamese hints for the periodic approval review."""
    hints: List[str] = []
    if metrics.total_tracked == 0:
        return ["Chưa có cặp nào được theo dõi. Hãy liệt kê bản thảo chưa duyệt rồi duyệt thử."]
    if metrics.approval_rate < 0.7:
        hints.append("Tỉ lệ duyệt dưới 70%. Hãy xem lại các lý do từ chối rồi sửa bản thảo.")
    if metrics.pending and metrics.pending / max(1, metrics.total_tracked) > 0.2:
        hints.append("Còn trên 20% cặp chưa duyệt. Hãy ưu tiên duyệt mẻ tồn nhiều nhất.")
    if metrics.rejected and metrics.rejection_rate > 0.3:
        hints.append("Tỉ lệ từ chối trên 30% trong 3 mẻ gần nhất cần họp lại với chuyên gia.")
    if not hints:
        hints.append("Số liệu ổn. Giữ nhịp xem lại định kỳ.")
    return hints


def create_revised_version(
    pair_id: str,
    old_answer: str,
    new_answer: str,
    reviewer_name: str,
    *,
    source_file: str = "",
) -> Dict:
    """Save a revised-then-approved version while keeping the old one."""
    pid = str(pair_id or "").strip()
    name = str(reviewer_name or "").strip()
    old_text = str(old_answer or "").strip()
    new_text = str(new_answer or "").strip()
    if not pid:
        return {"ok": False, "error_vi": "Thiếu mã cặp bản thảo nên chưa lưu được bản sửa."}
    if not name:
        return {"ok": False, "error_vi": "Bạn cho mình xin tên người duyệt để ghi nhật ký nhé."}
    if not old_text or not new_text:
        return {"ok": False, "error_vi": "Bản cũ và bản sửa đều cần có nội dung."}
    if old_text == new_text:
        return {"ok": False, "error_vi": "Bản sửa chưa khác bản cũ. Bạn sửa nội dung rồi thử lại."}
    path = versions_path()
    existing = 0
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict) and str(item.get("pair_id", "")) == pid:
                    try:
                        existing = max(existing, int(item.get("version", 0) or 0))
                    except (TypeError, ValueError):
                        continue
    record = {
        "pair_id": pid,
        "version": existing + 1,
        "old_answer": old_text,
        "new_answer": new_text,
        "reviewer_name": name,
        "source_file": str(source_file or ""),
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "record": record}


def get_versions(pair_id: str, limit: int = 100) -> List[Dict]:
    """List saved versions for one pair (oldest first, old text kept)."""
    pid = str(pair_id or "").strip()
    path = versions_path()
    if not pid or not path.exists():
        return []
    out: List[Dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict) and str(item.get("pair_id", "")) == pid:
                out.append(item)
    out.sort(key=lambda item: int(item.get("version", 0) or 0))
    if limit <= 0:
        return []
    return out[-limit:]
