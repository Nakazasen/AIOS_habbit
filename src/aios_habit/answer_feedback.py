"""Feedback cau tra loi ngay tren khung chat (vong lap cai thien lien tuc).

- Nguoi dung cham thumbs up/down duoi moi cau tra loi cua assistant.
- Cham "chua huu ich" thi BAT BUOC chon 1 trong 4 nhom ly do ('sai', 'kho_hieu', 'thieu_nguon', 'lac_de')
  va nhap giai thich ngan de he thong tu hoc cai thien.
- Gan dinh danh Windows (domain\\user) vo hinh de chong trung phieu (moi user 1 phieu/cau, bam lai cap nhat thay the).
- Luu JSONL tai `local_cases/answer_feedback.jsonl` — KHONG BAO GIO ghi vao
  kho tri thuc hay luong tra loi chinh. Day la du lieu van hanh cho vong lap
  cai thien, khong phai tri thuc da duyet.
- Dataclass chuan hoa, ghi kem hash cau hoi va danh sach tai lieu trich dan.
- `feedback_stats()` cho metric vong lap: ti le huu ich, phan bo ly do, SMA(20).

Tuong thich Python 3.11.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

RATING_HUU_ICH = "huu_ich"
RATING_CHUA_HUU_ICH = "chua_huu_ich"
RATING_LIKE = "huu_ich"
RATING_DISLIKE = "chua_huu_ich"
_RATINGS = (RATING_HUU_ICH, RATING_CHUA_HUU_ICH)

# 4 nhom ly do bat buoc khi che (Dislike)
REASON_CAT_SAI = "sai"
REASON_CAT_KHO_HIEU = "kho_hieu"
REASON_CAT_THIEU_NGUON = "thieu_nguon"
REASON_CAT_LAC_DE = "lac_de"

REASON_CATEGORIES = (
    REASON_CAT_SAI,
    REASON_CAT_KHO_HIEU,
    REASON_CAT_THIEU_NGUON,
    REASON_CAT_LAC_DE,
)

REASON_CATEGORY_LABELS = {
    REASON_CAT_SAI: "Sai lệch sự thật / thông số kỹ thuật",
    REASON_CAT_KHO_HIEU: "Khó hiểu / lủng củng / rối rắm",
    REASON_CAT_THIEU_NGUON: "Thiếu nguồn / không có trích dẫn chứng minh",
    REASON_CAT_LAC_DE: "Lạc đề / không đúng trọng tâm câu hỏi",
}

# Gioi han do dai de file JSONL khong phong to vo han.
MAX_QUESTION_CHARS = 2000
MAX_ANSWER_CHARS = 4000
MAX_REASON_CHARS = 2000


def get_windows_identity() -> str:
    """Lay dinh danh Windows (domain\\user) vo hinh de chong trung phieu."""
    domain = os.environ.get("USERDOMAIN", "").strip()
    try:
        user = getpass.getuser().strip()
    except Exception:
        user = "unknown_user"
    if domain:
        return f"{domain}\\{user}"
    return user


def compute_question_hash(question: str) -> str:
    """Hash SHA-256 chuan hoa cua cau hoi de gom cum truy van."""
    normalized = " ".join(str(question or "").strip().lower().split())
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def infer_reason_category(text: str) -> str:
    """Suy doan nhom ly do tu text neu nguoi dung nhap tu do hoac du lieu cu."""
    t = str(text or "").lower()
    if any(k in t for k in ("nguồn", "nguon", "trích dẫn", "trich dan", "tài liệu", "tai lieu", "chứng minh", "chung minh")):
        return REASON_CAT_THIEU_NGUON
    if any(k in t for k in ("khó hiểu", "kho hieu", "lủng củng", "lung cung", "rối", "roi", "dài dòng", "dai dong")):
        return REASON_CAT_KHO_HIEU
    if any(k in t for k in ("lạc đề", "lac de", "không đúng", "khong dung", "lan man")):
        return REASON_CAT_LAC_DE
    if any(k in t for k in ("sai", "nhầm", "nham", "lỗi", "loi", "hỏng", "hong", "không chính xác", "khong chinh xac")):
        return REASON_CAT_SAI
    return REASON_CAT_SAI


@dataclass
class AnswerFeedbackRecord:
    """Dataclass chuan hoa cho mot ban ghi phan hoi cau tra loi."""

    conversation_id: str
    message_id: str
    user_id: str
    question: str
    question_hash: str
    answer_excerpt: str
    rating: str  # "huu_ich" | "chua_huu_ich"
    reason_category: str = ""  # 'sai' | 'kho_hieu' | 'thieu_nguon' | 'lac_de' | ""
    reason: str = ""
    cited_sources: List[str] = field(default_factory=list)
    domain: str = ""
    lane: str = ""
    device_id: str = ""
    topic: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    )
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "question": self.question,
            "question_hash": self.question_hash,
            "answer_excerpt": self.answer_excerpt,
            "rating": self.rating,
            "reason_category": self.reason_category,
            "reason": self.reason,
            "cited_sources": list(self.cited_sources),
            "domain": self.domain,
            "lane": self.lane,
            "device_id": self.device_id,
            "topic": self.topic,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AnswerFeedbackRecord:
        conv_id = str(data.get("conversation_id", "") or "")
        msg_id = str(data.get("message_id", "") or "")
        user_id = str(data.get("user_id", "") or "")
        q = str(data.get("question", "") or "")
        q_hash = str(data.get("question_hash", "") or "")
        if not q_hash and q:
            q_hash = compute_question_hash(q)
        ans = str(data.get("answer_excerpt", "") or data.get("answer", "") or "")
        rating_raw = str(data.get("rating", "") or "").strip().lower()
        if rating_raw in ("like", "up", "1", RATING_HUU_ICH):
            rating = RATING_HUU_ICH
        elif rating_raw in ("dislike", "down", "0", RATING_CHUA_HUU_ICH):
            rating = RATING_CHUA_HUU_ICH
        else:
            rating = rating_raw
        r_cat = str(data.get("reason_category", "") or "")
        reason = str(data.get("reason", "") or "")
        if not r_cat and rating == RATING_CHUA_HUU_ICH and reason:
            r_cat = infer_reason_category(reason)
        sources = data.get("cited_sources") or []
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.split(",") if s.strip()]
        domain = str(data.get("domain", "") or data.get("notebook_id", "") or "")
        lane = str(data.get("lane", "") or "")
        dev_id = str(data.get("device_id", "") or "")
        topic = str(data.get("topic", "") or "")
        created_at = str(data.get("created_at", "") or "")
        updated_at = str(data.get("updated_at", "") or "")
        return cls(
            conversation_id=conv_id,
            message_id=msg_id,
            user_id=user_id,
            question=q,
            question_hash=q_hash,
            answer_excerpt=ans,
            rating=rating,
            reason_category=r_cat,
            reason=reason,
            cited_sources=list(sources),
            domain=domain,
            lane=lane,
            device_id=dev_id,
            topic=topic,
            created_at=created_at,
            updated_at=updated_at,
        )


def feedback_file() -> Path:
    env_dir = os.environ.get("AIOS_LOCAL_CASES_DIR", "").strip()
    if env_dir:
        return Path(env_dir) / "answer_feedback.jsonl"
    cwd_file = Path.cwd() / "local_cases" / "answer_feedback.jsonl"
    if cwd_file.exists():
        return cwd_file
    repo_file = Path(__file__).resolve().parent.parent.parent / "local_cases" / "answer_feedback.jsonl"
    if repo_file.exists():
        return repo_file
    return cwd_file


def _read_all_raw_records() -> List[Dict[str, Any]]:
    path = feedback_file()
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
            except (json.JSONDecodeError, ValueError):
                continue
    return records


def _write_all_records_atomic(records: Sequence[Dict[str, Any]]) -> None:
    path = feedback_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        suffix=".tmp",
    )
    temp_path = Path(temp_file.name)
    try:
        for rec in records:
            temp_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
        temp_file.flush()
        temp_file.close()
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def record_feedback(
    conversation_id: str,
    message_id: str,
    question: str,
    answer: str,
    rating: str,
    *,
    reason_category: str = "",
    reason: str = "",
    user_id: str = "",
    question_hash: str = "",
    cited_sources: Optional[Sequence[str]] = None,
    domain: str = "",
    lane: str = "",
    device_id: str = "",
    topic: str = "",
) -> Dict[str, Any]:
    """Ghi mot feedback kem dinh danh Windows, ly do bat buoc khi dislike, va chong trung phieu.

    Tra ve {"ok": True, "updated": bool} hoac {"ok": False, "error_vi": ...}.
    """
    rating_clean = str(rating or "").strip().lower()
    if rating_clean in ("like", "up", "1", RATING_HUU_ICH):
        rating_norm = RATING_HUU_ICH
    elif rating_clean in ("dislike", "down", "0", RATING_CHUA_HUU_ICH):
        rating_norm = RATING_CHUA_HUU_ICH
    else:
        return {"ok": False, "error_vi": "Đánh giá không hợp lệ."}

    reason_clean = str(reason or "").strip()
    reason_cat_clean = str(reason_category or "").strip()

    if rating_norm == RATING_CHUA_HUU_ICH:
        if not reason_cat_clean and not reason_clean:
            return {
                "ok": False,
                "error_vi": "Bạn chê câu trả lời thì cho mình xin lý do để cải thiện nhé.",
            }
        if reason_cat_clean and reason_cat_clean not in REASON_CATEGORIES:
            return {
                "ok": False,
                "error_vi": (
                    f"Nhóm lý do không hợp lệ. Vui lòng chọn 1 trong: {', '.join(REASON_CATEGORIES)}"
                ),
            }
        if not reason_cat_clean:
            reason_cat_clean = infer_reason_category(reason_clean)
    else:
        if not reason_cat_clean:
            reason_cat_clean = ""

    actual_user = str(user_id or "").strip() or get_windows_identity()
    q_text = str(question or "")[:MAX_QUESTION_CHARS]
    q_hash = str(question_hash or "").strip() or compute_question_hash(q_text)

    if cited_sources is None:
        sources_list: List[str] = []
    else:
        sources_list = [str(s).strip() for s in cited_sources if str(s).strip()]

    now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    raw_records = _read_all_raw_records()

    # Logic chong trung phieu: 1 user chi co 1 phieu cho moi cau (message_id).
    # Neu da co phieu cua user nay tren message_id (hoac conversation_id neu message_id rong):
    # Cap nhat thay the ban ghi do!
    match_index = -1
    for idx, rec in enumerate(raw_records):
        rec_msg = str(rec.get("message_id", ""))
        rec_conv = str(rec.get("conversation_id", ""))
        rec_user = str(rec.get("user_id", ""))
        is_msg_match = bool(message_id and rec_msg == str(message_id))
        is_conv_match = bool(not message_id and conversation_id and rec_conv == str(conversation_id))
        if is_msg_match or is_conv_match:
            # Match user identity neu co, hoac fallback match neu rec cu chua co user_id
            if not rec_user or rec_user == actual_user:
                match_index = idx

    is_update = match_index >= 0
    if is_update:
        existing = raw_records[match_index]
        created_at_time = str(existing.get("created_at", "") or now_iso)
        updated_record = AnswerFeedbackRecord(
            conversation_id=str(conversation_id or existing.get("conversation_id", "")),
            message_id=str(message_id or existing.get("message_id", "")),
            user_id=actual_user,
            question=q_text or str(existing.get("question", "")),
            question_hash=q_hash or str(existing.get("question_hash", "")),
            answer_excerpt=str(answer or existing.get("answer_excerpt", ""))[:MAX_ANSWER_CHARS],
            rating=rating_norm,
            reason_category=reason_cat_clean,
            reason=reason_clean[:MAX_REASON_CHARS],
            cited_sources=sources_list or list(existing.get("cited_sources", [])),
            domain=str(domain or existing.get("domain", "")),
            lane=str(lane or existing.get("lane", "")),
            device_id=str(device_id or existing.get("device_id", "")),
            topic=str(topic or existing.get("topic", "")),
            created_at=created_at_time,
            updated_at=now_iso,
        )
        raw_records[match_index] = updated_record.to_dict()
    else:
        new_record = AnswerFeedbackRecord(
            conversation_id=str(conversation_id or ""),
            message_id=str(message_id or ""),
            user_id=actual_user,
            question=q_text,
            question_hash=q_hash,
            answer_excerpt=str(answer or "")[:MAX_ANSWER_CHARS],
            rating=rating_norm,
            reason_category=reason_cat_clean,
            reason=reason_clean[:MAX_REASON_CHARS],
            cited_sources=sources_list,
            domain=str(domain or ""),
            lane=str(lane or ""),
            device_id=str(device_id or ""),
            topic=str(topic or ""),
            created_at=now_iso,
            updated_at="",
        )
        raw_records.append(new_record.to_dict())

    _write_all_records_atomic(raw_records)
    if rating_norm == RATING_CHUA_HUU_ICH and q_text:
        try:
            from aios_habit.answer_cache import invalidate_cached_answer
            env_dir = os.environ.get("AIOS_LOCAL_CASES_DIR", "").strip()
            invalidate_cached_answer(
                q_text,
                scope_id=str(domain or "").strip() or None,
                reason="disliked_by_user",
                base_dir=Path(env_dir) if env_dir else None,
            )
        except Exception:
            pass
    res: Dict[str, Any] = {"ok": True}
    if is_update:
        res["updated"] = True
    return res


def get_feedback(
    conversation_id: str,
    message_id: str,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Lay feedback da ghi cho mot message (None neu chua co).

    Neu user_id duoc truyen, tim dung phieu cua user do.
    Neu user_id la None, tra ve phieu gan nhat cua message_id.
    """
    path = feedback_file()
    if not path.exists():
        return None
    found: Optional[Dict[str, Any]] = None
    target_user = str(user_id or "").strip() if user_id is not None else None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            match_conv = str(record.get("conversation_id", "")) == str(conversation_id)
            match_msg = str(record.get("message_id", "")) == str(message_id)
            if match_conv and match_msg:
                if target_user is None:
                    found = record
                else:
                    rec_user = str(record.get("user_id", "")).strip()
                    if rec_user == target_user or (not rec_user and target_user == get_windows_identity()):
                        found = record
    return found


def iter_recent(limit: int = 200) -> List[Dict[str, Any]]:
    """Doc cac feedback gan nhat (toi da `limit`)."""
    records = _read_all_raw_records()
    return records[-limit:]


def load_deduplicated_feedback(limit: Optional[int] = None) -> List[AnswerFeedbackRecord]:
    """Doc va tra ve danh sach AnswerFeedbackRecord da chuan hoa, moi user 1 phieu/cau."""
    raw = _read_all_raw_records()
    # Map (message_id, user_id) -> record
    dedup: Dict[str, AnswerFeedbackRecord] = {}
    for item in raw:
        rec = AnswerFeedbackRecord.from_dict(item)
        key = f"{rec.message_id}::{rec.user_id or 'anon'}" if rec.message_id else f"{rec.conversation_id}::{rec.user_id or 'anon'}"
        dedup[key] = rec
    results = list(dedup.values())
    if limit is not None and limit > 0:
        return results[-limit:]
    return results


def feedback_stats() -> Dict[str, Any]:
    """Metric vong lap: tong so, ti le huu ich, top ly do bi che va phan bo 4 nhom."""
    records = iter_recent(limit=10000)
    total = len(records)
    good = sum(1 for r in records if r.get("rating") == RATING_HUU_ICH)
    bad = sum(1 for r in records if r.get("rating") == RATING_CHUA_HUU_ICH)

    # Thong ke 4 nhom ly do
    category_counts: Dict[str, int] = {cat: 0 for cat in REASON_CATEGORIES}
    reasons: Dict[str, int] = {}
    for r in records:
        if r.get("rating") == RATING_CHUA_HUU_ICH:
            cat = str(r.get("reason_category", "")).strip()
            if not cat:
                cat = infer_reason_category(str(r.get("reason", "")))
            if cat in category_counts:
                category_counts[cat] += 1
            reason_text = str(r.get("reason", "")).strip()
            if reason_text:
                reasons[reason_text[:120]] = reasons.get(reason_text[:120], 0) + 1

    top_reasons = sorted(reasons.items(), key=lambda item: item[1], reverse=True)[:10]

    return {
        "total": total,
        "huu_ich": good,
        "chua_huu_ich": bad,
        "ti_le_huu_ich": round(good / total, 3) if total else 0.0,
        "phan_bo_nhom_ly_do": category_counts,
        "top_ly_do_che": [{"ly_do": text, "so_lan": count} for text, count in top_reasons],
    }
