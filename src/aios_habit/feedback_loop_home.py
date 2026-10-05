"""Device feedback loop: like/dislike per machine, habit learning, metrics.

Ticket FEEDBACK-LOOP-HOME extends the existing ``answer_feedback`` store
(thumbs under each answer, local_cases only) into a full loop without
user accounts:

- Each machine has a random local ID (``local_cases/device_id``).
- Feedback records carry ``device_id`` + ``topic`` (lsu / dieu_tra_loi / mom).
- Metrics group dislike rates by answer and by topic.
- Habit profiles per machine suggest adjustments
  (e.g. morning LSU questions -> prefer the LSU block;
  frequent "too long" complaints -> answer concisely for that machine).
- Chat history already on disk is part of the memory.
"""

from __future__ import annotations

import os
import re
import secrets
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

FLAG_ENV_KEY = "AIOS_FEATURE_FEEDBACK_LOOP_HOME"

_overrides: Dict[str, bool] = {}

# Preset dislike reasons (short choices + free text for "other").
REASON_SAI_NOI_DUNG = "sai_noi_dung"
REASON_THIEU_SO_LIEU = "thieu_so_lieu"
REASON_DAI_DONG = "dai_dong"
REASON_KHO_HIEU = "kho_hieu"
REASON_KHAC = "khac"

PRESET_REASONS = (
    REASON_SAI_NOI_DUNG,
    REASON_THIEU_SO_LIEU,
    REASON_DAI_DONG,
    REASON_KHO_HIEU,
    REASON_KHAC,
)

REASON_LABELS_VI = {
    REASON_SAI_NOI_DUNG: "Trả lời sai nội dung",
    REASON_THIEU_SO_LIEU: "Thiếu số liệu cụ thể",
    REASON_DAI_DONG: "Trả lời dài dòng",
    REASON_KHO_HIEU: "Khó hiểu",
    REASON_KHAC: "Lý do khác (ghi bên dưới)",
}

REVIEW_GUIDE_VI = (
    "Cách xem lại định kỳ: thu thập phản hồi tại chỗ trong "
    "local_cases/answer_feedback.jsonl, chạy compute_loop_metrics để xem "
    "tỉ lệ chê theo câu trả lời / theo chủ đề, rồi đọc review_recommendations. "
    "Ngưỡng cần sửa gốc: một câu bị chê từ 2 máy khác nhau trở lên, "
    "hoặc một chủ đề có tỉ lệ chê trên 30%."
)


def set_feedback_loop_override(enabled: bool) -> None:
    """Set an in-memory flag override (used by tests)."""
    _overrides["enabled"] = bool(enabled)


def clear_feedback_loop_override() -> None:
    """Clear the in-memory flag override."""
    _overrides.pop("enabled", None)


def feedback_loop_enabled() -> bool:
    """Return True only when the feedback-loop lane is explicitly enabled."""
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


def device_id_path() -> Path:
    """Local file holding the random machine ID (never committed)."""
    return _local_cases_dir() / "device_id"


def _device_id_ok(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not 4 <= len(cleaned) <= 64:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-_]*", cleaned))


def get_or_create_device_id() -> str:
    """Return the stable machine ID, creating it once per machine."""
    path = device_id_path()
    try:
        if path.exists():
            existing = path.read_text(encoding="utf-8").strip().splitlines()
            candidate = (existing[0].strip() if existing else "")
            if _device_id_ok(candidate):
                return candidate
    except (OSError, ValueError):
        pass
    fresh = "may-" + secrets.token_hex(6)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fresh + "\n", encoding="utf-8")
    except OSError:
        return fresh
    return fresh


def detect_topic(question: str) -> str:
    """Detect the knowledge block a question belongs to (lsu/mom/dieu_tra_loi)."""
    text = str(question or "").strip()
    if not text:
        return "chua_phan_loai"
    try:
        from aios_habit.index_domain import detect_domain_from_question
    except (ImportError, ValueError):
        return "chua_phan_loai"
    try:
        result = detect_domain_from_question(text)
    except (ValueError, TypeError):
        return "chua_phan_loai"
    domain = str(getattr(result, "domain", "") or "").strip()
    if domain in ("lsu", "mom", "dieu_tra_loi"):
        return domain
    return "chua_phan_loai"


def question_key(question: str, limit: int = 200) -> str:
    """Normalized key grouping the same question across machines."""
    text = str(question or "").lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if limit > 0 else text


def _parse_hour(value: object) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        # ISO timestamps: take the hour part directly (local wall time).
        match = re.search(r"[T ](\d{1,2}):\d{2}", text)
        if match:
            hour = int(match.group(1))
            if 0 <= hour <= 23:
                return hour
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.hour
    except (ValueError, TypeError):
        return None


def _hour_bucket(hour: int) -> str:
    if 5 <= hour <= 10:
        return "buoi_sang"
    if 11 <= hour <= 13:
        return "buoi_trua"
    if 14 <= hour <= 17:
        return "buoi_chieu"
    if 18 <= hour <= 22:
        return "buoi_toi"
    return "buoi_dem"


def record_device_feedback(
    conversation_id: str,
    message_id: str,
    question: str,
    answer: str,
    rating: str,
    *,
    reason: str = "",
    lane: str = "",
    device_id: str = "",
    topic: str = "",
) -> Dict:
    """Record one feedback with machine ID + topic (local_cases only)."""
    from aios_habit import answer_feedback

    machine = str(device_id or "").strip() or get_or_create_device_id()
    block = str(topic or "").strip() or detect_topic(question)
    return answer_feedback.record_feedback(
        conversation_id,
        message_id,
        question,
        answer,
        rating,
        reason=reason,
        lane=lane,
        device_id=machine,
        topic=block,
    )


def read_device_records(device_id: str = "", limit: int = 10000) -> List[Dict]:
    """Read feedback records, optionally filtered to one machine."""
    from aios_habit import answer_feedback

    records = answer_feedback.iter_recent(limit=limit)
    wanted = str(device_id or "").strip()
    if not wanted:
        return records
    return [r for r in records if str(r.get("device_id", "") or "") == wanted]


def compute_loop_metrics(records: Sequence[Dict] | None = None) -> Dict:
    """Dislike rates overall, per answer group, and per topic."""
    from aios_habit import answer_feedback

    items = list(records) if records is not None else answer_feedback.iter_recent(limit=10000)
    total = len(items)
    good = sum(1 for r in items if r.get("rating") == "huu_ich")
    bad = sum(1 for r in items if r.get("rating") == "chua_huu_ich")

    by_answer: Dict[str, Dict] = {}
    by_topic: Dict[str, Dict] = {}
    for record in items:
        key = question_key(str(record.get("question", "") or ""))
        if not key:
            key = "(cau_hoi_rong)"
        slot = by_answer.setdefault(
            key,
            {
                "cau_hoi": str(record.get("question", "") or "")[:160],
                "tong": 0,
                "che": 0,
                "cac_may": set(),
            },
        )
        slot["tong"] += 1
        if record.get("rating") == "chua_huu_ich":
            slot["che"] += 1
        machine = str(record.get("device_id", "") or "").strip()
        if machine:
            slot["cac_may"].add(machine)

        topic = str(record.get("topic", "") or "").strip() or "chua_phan_loai"
        tslot = by_topic.setdefault(topic, {"chu_de": topic, "tong": 0, "che": 0})
        tslot["tong"] += 1
        if record.get("rating") == "chua_huu_ich":
            tslot["che"] += 1

    theo_cau = []
    for key, slot in by_answer.items():
        tong = int(slot["tong"] or 0)
        che = int(slot["che"] or 0)
        theo_cau.append(
            {
                "khoa_cau_hoi": key[:120],
                "cau_hoi": slot["cau_hoi"],
                "tong": tong,
                "che": che,
                "ti_le_che": round(che / tong, 3) if tong else 0.0,
                "so_may": len(slot["cac_may"]),
            }
        )
    theo_cau.sort(key=lambda row: (row["ti_le_che"], row["che"]), reverse=True)

    theo_chu_de = []
    for topic, slot in by_topic.items():
        tong = int(slot["tong"] or 0)
        che = int(slot["che"] or 0)
        theo_chu_de.append(
            {
                "chu_de": slot["chu_de"],
                "tong": tong,
                "che": che,
                "ti_le_che": round(che / tong, 3) if tong else 0.0,
            }
        )
    theo_chu_de.sort(key=lambda row: (row["ti_le_che"], row["che"]), reverse=True)

    return {
        "tong": total,
        "khen": good,
        "che": bad,
        "ti_le_che": round(bad / total, 3) if total else 0.0,
        "theo_cau_tra_loi": theo_cau,
        "theo_chu_de": theo_chu_de,
    }


def flag_answers_for_fix(
    records: Sequence[Dict] | None = None,
    *,
    min_devices: int = 2,
    min_dislikes: int = 2,
) -> List[Dict]:
    """Answers disliked from several distinct machines (fix the source)."""
    metrics = compute_loop_metrics(records)
    flagged = [
        row
        for row in metrics["theo_cau_tra_loi"]
        if int(row.get("so_may", 0) or 0) >= int(min_devices or 0)
        and int(row.get("che", 0) or 0) >= int(min_dislikes or 0)
    ]
    return flagged


def review_recommendations(metrics: Dict) -> List[str]:
    """Short Vietnamese hints for the periodic feedback review."""
    if not isinstance(metrics, dict) or int(metrics.get("tong", 0) or 0) == 0:
        return ["Chưa có phản hồi nào. Hãy dùng khung chat rồi chấm thích / chê để máy học."]
    hints: List[str] = []
    ti_le_che = float(metrics.get("ti_le_che", 0.0) or 0.0)
    if ti_le_che > 0.3:
        hints.append("Tỉ lệ chê trên 30%. Hãy mở các câu bị chê nhiều nhất rồi sửa gốc.")
    flagged = [r for r in metrics.get("theo_cau_tra_loi", []) if int(r.get("so_may", 0) or 0) >= 2]
    if flagged:
        hints.append(
            "Có %d câu bị chê từ 2 máy trở lên. Ưu tiên sửa gốc các câu này trước." % len(flagged)
        )
    for row in metrics.get("theo_chu_de", []):
        if int(row.get("tong", 0) or 0) >= 3 and float(row.get("ti_le_che", 0.0) or 0.0) > 0.3:
            hints.append(
                "Chủ đề %s bị chê %d/%d. Hãy xem lại đống tri thức của chủ đề này."
                % (row.get("chu_de", "?"), row.get("che", 0), row.get("tong", 0))
            )
            break
    if not hints:
        hints.append("Số liệu ổn. Giữ nhịp xem lại định kỳ.")
    return hints


def _local_chat_questions() -> List[Dict]:
    """User questions already on disk (part of the machine memory)."""
    try:
        from aios_habit.workspace_chat_store import load_all_messages
    except (ImportError, ValueError):
        return []
    try:
        messages = load_all_messages()
    except (OSError, ValueError):
        return []
    out: List[Dict] = []
    for msg in messages:
        role = str(getattr(msg, "role", "") or "")
        if role != "user":
            continue
        out.append(
            {
                "question": str(getattr(msg, "content", "") or ""),
                "created_at": str(getattr(msg, "created_at", "") or ""),
            }
        )
    return out


def build_device_profile(
    device_id: str,
    records: Sequence[Dict] | None = None,
    messages: Sequence[Dict] | None = None,
) -> Dict:
    """Habit profile for one machine ("càng dùng càng hiểu mình")."""
    machine = str(device_id or "").strip()
    if not machine:
        return {"ok": False, "error_vi": "Thiếu mã máy nên chưa dựng được hồ sơ."}
    from aios_habit import answer_feedback

    if records is None:
        items = [r for r in answer_feedback.iter_recent(limit=10000) if str(r.get("device_id", "") or "") == machine]
    else:
        items = [r for r in list(records) if str(r.get("device_id", "") or "") in ("", machine)]

    if messages is None:
        history = _local_chat_questions()
        topic_texts = [str(h.get("question", "") or "") for h in history]
        hours = [_parse_hour(h.get("created_at")) for h in history]
    else:
        topic_texts = [str(m.get("question", m.get("content", "")) or "") for m in list(messages)]
        hours = [_parse_hour(m.get("created_at")) for m in list(messages)]
    for record in items:
        topic_texts.append(str(record.get("question", "") or ""))
        hour = _parse_hour(record.get("created_at"))
        if hour is not None:
            hours.append(hour)

    topics = [detect_topic(text) for text in topic_texts if str(text or "").strip()]
    top_topics = Counter(topics).most_common(3)

    liked_lens = [len(str(r.get("answer_excerpt", "") or "")) for r in items if r.get("rating") == "huu_ich"]
    disliked_lens = [len(str(r.get("answer_excerpt", "") or "")) for r in items if r.get("rating") == "chua_huu_ich"]
    reasons = Counter(str(r.get("reason", "") or "").strip() for r in items if r.get("rating") == "chua_huu_ich")
    dai_dong_hits = sum(
        count for text, count in reasons.items() if "dài" in text or "dai" in text or REASON_DAI_DONG in text
    )
    avg_good = sum(liked_lens) / len(liked_lens) if liked_lens else 0.0
    avg_bad = sum(disliked_lens) / len(disliked_lens) if disliked_lens else 0.0
    if (dai_dong_hits >= 2) or (avg_bad - avg_good > 500 and len(items) >= 3):
        do_dai = "suc_tich"
    elif avg_good > 1500 and liked_lens:
        do_dai = "chi_tiet"
    else:
        do_dai = "binh_thuong"

    buckets = [_hour_bucket(h) for h in hours if h is not None]
    top_hours = [name for name, _ in Counter(buckets).most_common(2)]

    goi_y: List[str] = []
    if top_topics:
        chu_de = top_topics[0][0]
        if "buoi_sang" in top_hours and chu_de == "lsu":
            goi_y.append("Máy này hay hỏi LSU buổi sáng → ưu tiên tìm đống LSU khi máy hỏi buổi sáng.")
        else:
            goi_y.append("Máy này hay hỏi chủ đề %s → ưu tiên tìm đống %s trước." % (chu_de, chu_de.upper()))
    if do_dai == "suc_tich":
        goi_y.append("Máy này hay chê dài → trả lời súc tích hơn cho máy này.")
    elif do_dai == "chi_tiet":
        goi_y.append("Máy này thích câu trả lời chi tiết → giữ độ chi tiết cho máy này.")
    if not goi_y:
        goi_y.append("Chưa thấy thói quen rõ. Dùng thêm rồi máy sẽ hiểu hơn.")

    return {
        "ok": True,
        "ma_may": machine,
        "tong_feedback": len(items),
        "tong_cau_hoi": len(topic_texts),
        "chu_de_hay_hoi": [{"chu_de": name, "so_lan": count} for name, count in top_topics],
        "do_dai_ua_thich": do_dai,
        "gio_hay_dung": top_hours,
        "goi_y_dieu_chinh": goi_y,
    }


def device_adjustment(
    device_id: str,
    records: Sequence[Dict] | None = None,
    messages: Sequence[Dict] | None = None,
) -> Dict:
    """Small adjustment hint the app can apply for one machine."""
    profile = build_device_profile(device_id, records, messages)
    if not profile.get("ok"):
        return {"uu_tien_kho": "", "do_dai": "binh_thuong", "goi_y": []}
    top = profile.get("chu_de_hay_hoi") or []
    kho = str(top[0].get("chu_de", "") or "") if top else ""
    if kho == "chua_phan_loai":
        kho = ""
    return {
        "uu_tien_kho": kho,
        "do_dai": str(profile.get("do_dai_ua_thich", "binh_thuong") or "binh_thuong"),
        "goi_y": list(profile.get("goi_y_dieu_chinh", []) or []),
    }
