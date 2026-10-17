"""Continuous Improvement Loop for Auto-classification (Step 5 / B5).

Implements the 3 mandatory points of the continuous improvement loop:
1. Inline feedback capture (hứng phản hồi đúng/sai nhãn ngay tại chỗ).
2. Measurable metrics (coverage rate, accuracy/positive rate, class breakdown).
3. Review surface (bề mặt xem lại qua lệnh chat và báo cáo tóm tắt).

Storage contract:
- Persisted locally to ``local_cases/autoclassify_feedback.jsonl``.
- NEVER written to the RAG vector index or global knowledge store.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LOCAL_CASES_DIR = Path("local_cases")
LOCAL_FEEDBACK_FILE = LOCAL_CASES_DIR / "autoclassify_feedback.jsonl"

RATING_DUNG = "đúng"
RATING_SAI = "sai"
RATING_MOT_PHAN = "một phần"
VALID_RATINGS = (RATING_DUNG, RATING_SAI, RATING_MOT_PHAN)


@dataclass
class AutoclassifyFeedbackRecord:
    feedback_id: str
    case_id: str
    created_at: str
    rating: str  # "đúng" | "sai" | "một phần" | "chờ đánh giá"
    suggested_nhom_nguyen_nhan: str = ""
    suggested_cong_doan: Optional[str] = None
    suggested_bo_phan: Optional[str] = None
    confirmed_nhom_nguyen_nhan: str = ""
    confirmed_cong_doan: Optional[str] = None
    confirmed_bo_phan: Optional[str] = None
    can_cu: Dict[str, str] = field(default_factory=dict)
    is_recurrence: bool = False
    recurrence_count: int = 0
    user_correction: Optional[str] = None
    user_note: Optional[str] = None
    conversation_id: str = ""


def _ensure_dir() -> None:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)


def log_autoclassify_suggestion(
    case_id: str,
    suggested_nhom_nguyen_nhan: str,
    suggested_cong_doan: Optional[str] = None,
    suggested_bo_phan: Optional[str] = None,
    confirmed_nhom_nguyen_nhan: Optional[str] = None,
    confirmed_cong_doan: Optional[str] = None,
    confirmed_bo_phan: Optional[str] = None,
    can_cu: Optional[Dict[str, str]] = None,
    is_recurrence: bool = False,
    recurrence_count: int = 0,
    conversation_id: str = "",
) -> str:
    """Log initial classification when a case is created or previewed."""
    _ensure_dir()
    feedback_id = f"FB-AUTO-{uuid.uuid4().hex[:8].upper()}"
    rec = AutoclassifyFeedbackRecord(
        feedback_id=feedback_id,
        case_id=case_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        rating="chờ đánh giá",
        suggested_nhom_nguyen_nhan=suggested_nhom_nguyen_nhan,
        suggested_cong_doan=suggested_cong_doan,
        suggested_bo_phan=suggested_bo_phan,
        confirmed_nhom_nguyen_nhan=confirmed_nhom_nguyen_nhan or suggested_nhom_nguyen_nhan,
        confirmed_cong_doan=confirmed_cong_doan or suggested_cong_doan,
        confirmed_bo_phan=confirmed_bo_phan or suggested_bo_phan,
        can_cu=dict(can_cu or {}),
        is_recurrence=is_recurrence,
        recurrence_count=recurrence_count,
        conversation_id=conversation_id,
    )
    line = json.dumps(asdict(rec), ensure_ascii=False)
    with LOCAL_FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return feedback_id


def record_autoclassify_feedback(
    case_id: str,
    rating: str,
    user_correction: Optional[str] = None,
    user_note: Optional[str] = None,
    conversation_id: str = "",
    feedback_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture inline user feedback (đúng / sai / một phần) for a case classification."""
    _ensure_dir()
    norm_rating = rating.strip().lower()
    if norm_rating not in VALID_RATINGS:
        norm_rating = RATING_MOT_PHAN if "phần" in norm_rating else (RATING_DUNG if "đúng" in norm_rating else RATING_SAI)

    # Read existing records
    records = load_all_feedback()
    target_idx = -1
    if feedback_id:
        for idx, r in enumerate(records):
            if r.get("feedback_id") == feedback_id:
                target_idx = idx
                break
    if target_idx < 0 and case_id:
        for idx in range(len(records) - 1, -1, -1):
            if records[idx].get("case_id") == case_id:
                target_idx = idx
                break

    if target_idx >= 0:
        records[target_idx]["rating"] = norm_rating
        if user_correction:
            records[target_idx]["user_correction"] = user_correction
        if user_note:
            records[target_idx]["user_note"] = user_note
        if conversation_id:
            records[target_idx]["conversation_id"] = conversation_id
        records[target_idx]["updated_at"] = datetime.now(timezone.utc).isoformat()
        saved_rec = records[target_idx]
    else:
        new_fid = feedback_id or f"FB-AUTO-{uuid.uuid4().hex[:8].upper()}"
        saved_rec = {
            "feedback_id": new_fid,
            "case_id": case_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rating": norm_rating,
            "user_correction": user_correction,
            "user_note": user_note,
            "conversation_id": conversation_id,
        }
        records.append(saved_rec)

    # Atomic rewrite
    tmp_path = LOCAL_FEEDBACK_FILE.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp_path.replace(LOCAL_FEEDBACK_FILE)

    return saved_rec


def load_all_feedback() -> List[Dict[str, Any]]:
    """Load all feedback records from local_cases/autoclassify_feedback.jsonl."""
    if not LOCAL_FEEDBACK_FILE.is_file():
        return []
    records: List[Dict[str, Any]] = []
    with LOCAL_FEEDBACK_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    records.append(data)
            except Exception:
                continue
    return records


def compute_autoclassify_metrics() -> Dict[str, Any]:
    """Compute measurable metrics for the auto-classifier continuous improvement loop."""
    records = load_all_feedback()
    total_logged = len(records)
    rated_records = [r for r in records if r.get("rating") in VALID_RATINGS]
    total_rated = len(rated_records)

    coverage_rate = (total_rated / total_logged) if total_logged > 0 else 0.0

    ratings_count = {RATING_DUNG: 0, RATING_SAI: 0, RATING_MOT_PHAN: 0}
    group_counts: Dict[str, int] = {}
    recurrence_count = 0

    for r in rated_records:
        r_label = r.get("rating")
        if r_label in ratings_count:
            ratings_count[r_label] += 1
        grp = r.get("confirmed_nhom_nguyen_nhan") or r.get("suggested_nhom_nguyen_nhan")
        if grp:
            group_counts[grp] = group_counts.get(grp, 0) + 1
        if r.get("is_recurrence"):
            recurrence_count += 1

    positive_ratings = ratings_count[RATING_DUNG] + ratings_count[RATING_MOT_PHAN]
    accuracy_rate = (positive_ratings / total_rated) if total_rated > 0 else 0.0
    exact_accuracy_rate = (ratings_count[RATING_DUNG] / total_rated) if total_rated > 0 else 0.0

    return {
        "total_cases_logged": total_logged,
        "total_rated": total_rated,
        "coverage_rate": round(coverage_rate, 4),
        "coverage_percent": round(coverage_rate * 100, 1),
        "accuracy_rate": round(accuracy_rate, 4),
        "accuracy_percent": round(accuracy_rate * 100, 1),
        "exact_accuracy_rate": round(exact_accuracy_rate, 4),
        "exact_accuracy_percent": round(exact_accuracy_rate * 100, 1),
        "ratings_count": ratings_count,
        "group_counts": group_counts,
        "recurrence_count": recurrence_count,
    }


def format_autoclassify_review_summary() -> str:
    """Render the Review Surface (Bề mặt xem lại) for auto-classification metrics."""
    metrics = compute_autoclassify_metrics()
    records = load_all_feedback()
    rated_records = [r for r in records if r.get("rating") in VALID_RATINGS]

    lines = [
        "### 📊 Bề Mặt Xem Lại Phân Loại Tự Động & Tái Phát (Bước 5)",
        "",
        "Hệ thống giám sát chất lượng phân loại tự động và cảnh báo tái phát qua 3 điểm vòng cải thiện liên tục:",
        "",
        "#### 1. 📈 Chỉ số đo lường hiệu quả (Measurable Metrics)",
        f"- **Tổng số ca ghi nhận gợi ý:** {metrics['total_cases_logged']} vụ",
        f"- **Số ca đã được phản hồi (Rated):** {metrics['total_rated']} lượt",
        f"- **Tỷ lệ bao phủ phản hồi (Coverage):** **{metrics['coverage_percent']}%** (mục tiêu ≥ 80%)",
        f"- **Độ chính xác ghi nhận từ người dùng:** **{metrics['accuracy_percent']}%** "
        f"({metrics['ratings_count'][RATING_DUNG]} đúng · {metrics['ratings_count'][RATING_MOT_PHAN]} một phần · {metrics['ratings_count'][RATING_SAI]} sai)",
        f"- **Độ chính xác tuyệt đối:** {metrics['exact_accuracy_percent']}%",
        f"- **Số ca phát hiện tái phát:** {metrics['recurrence_count']} vụ",
        "",
        "#### 2. 🏷️ Phân bố nhóm nguyên nhân thực tế",
    ]

    grp_labels = {
        "linh_kien": "Linh kiện (部品)",
        "lap_rap": "Lắp ráp (組立)",
        "thiet_ke": "Thiết kế (設計)",
        "khac": "Khác (その他)",
    }
    if metrics["group_counts"]:
        for grp, cnt in sorted(metrics["group_counts"].items(), key=lambda x: x[1], reverse=True):
            name = grp_labels.get(grp, grp)
            lines.append(f"- **{name}:** {cnt} vụ")
    else:
        lines.append("- _Chưa có dữ liệu phân bố nhóm nguyên nhân._")

    lines.extend([
        "",
        "#### 3. 🔍 Danh sách phản hồi gần đây (Review Surface)",
    ])

    if rated_records:
        limit_show = min(len(rated_records), 5)
        for idx, r in enumerate(reversed(rated_records[-limit_show:]), start=1):
            r_icon = "✅" if r.get("rating") == RATING_DUNG else ("⚠️" if r.get("rating") == RATING_MOT_PHAN else "❌")
            cid = r.get("case_id", "N/A")
            grp = r.get("confirmed_nhom_nguyen_nhan", "")
            grp_str = grp_labels.get(grp, grp)
            corr = f" — Điều chỉnh: *{r.get('user_correction')}*" if r.get("user_correction") else ""
            lines.append(f"{idx}. {r_icon} `{cid}` [{r.get('rating')}] — Nhóm: **{grp_str}**{corr}")
    else:
        lines.append("- _Chưa có lượt đánh giá nào từ người dùng._")

    lines.extend([
        "",
        "---",
        "🔒 **Quy tắc an toàn dữ liệu:** Phản hồi lưu độc lập tại `local_cases/autoclassify_feedback.jsonl`, "
        "tuyệt đối không ghi đè hay làm nhiễu kho tri thức RAG.",
    ])

    return "\n".join(lines)
