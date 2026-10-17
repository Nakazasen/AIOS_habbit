"""Continuous Improvement Loop for Investigation Trees (Step 3 / B3).

Implements the 3 mandatory points of the continuous improvement loop:
1. Inline feedback capture (hứng phản hồi đúng hướng / thiếu nhánh / không hữu ích ngay tại chỗ).
2. Measurable metrics (coverage rate, helpful rate, basis grounding rate, file exports).
3. Review surface (bề mặt xem lại qua lệnh chat và báo cáo tóm tắt).

Storage contract:
- Persisted locally to ``local_cases/investigation_feedback.jsonl``.
- NEVER written to the RAG vector index or global knowledge store.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

LOCAL_CASES_DIR = Path("local_cases")
LOCAL_INVESTIGATION_FEEDBACK_FILE = LOCAL_CASES_DIR / "investigation_feedback.jsonl"

RATING_DUNG_HUONG = "đúng hướng"
RATING_THIEU_NHANH = "thiếu nhánh"
RATING_KHONG_HUU_ICH = "không hữu ích"
VALID_INVESTIGATION_RATINGS = (RATING_DUNG_HUONG, RATING_THIEU_NHANH, RATING_KHONG_HUU_ICH)


@dataclass
class InvestigationFeedbackRecord:
    feedback_id: str
    tree_id: str
    case_id: str = ""
    phenomenon: str = ""
    code: str = ""
    created_at: str = ""
    rating: str = "chờ đánh giá"  # "đúng hướng" | "thiếu nhánh" | "không hữu ích" | "chờ đánh giá"
    user_note: Optional[str] = None
    missing_branch: Optional[str] = None
    total_items: int = 0
    grounded_items: int = 0
    generic_items: int = 0
    branch_basis: Dict[str, str] = field(default_factory=dict)
    exported_files: List[str] = field(default_factory=list)
    conversation_id: str = ""
    updated_at: Optional[str] = None


def _ensure_dir() -> None:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)


def log_investigation_tree(
    tree_id: str,
    phenomenon: str,
    code: str = "",
    case_id: str = "",
    total_items: int = 0,
    grounded_items: int = 0,
    generic_items: int = 0,
    branch_basis: Optional[Dict[str, str]] = None,
    exported_files: Optional[Sequence[str]] = None,
    conversation_id: str = "",
) -> str:
    """Log initial investigation tree generation into local storage."""
    _ensure_dir()
    feedback_id = f"FB-TREE-{uuid.uuid4().hex[:8].upper()}"
    rec = InvestigationFeedbackRecord(
        feedback_id=feedback_id,
        tree_id=tree_id or f"TREE-{uuid.uuid4().hex[:8].upper()}",
        case_id=case_id,
        phenomenon=phenomenon,
        code=code,
        created_at=datetime.now(timezone.utc).isoformat(),
        rating="chờ đánh giá",
        total_items=total_items,
        grounded_items=grounded_items,
        generic_items=generic_items,
        branch_basis=dict(branch_basis or {}),
        exported_files=list(exported_files or []),
        conversation_id=conversation_id,
    )
    line = json.dumps(asdict(rec), ensure_ascii=False)
    with LOCAL_INVESTIGATION_FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return feedback_id


def record_investigation_feedback(
    rating: str,
    user_note: Optional[str] = None,
    missing_branch: Optional[str] = None,
    tree_id: Optional[str] = None,
    case_id: Optional[str] = None,
    conversation_id: str = "",
    feedback_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture inline user feedback (đúng hướng / thiếu nhánh / không hữu ích) for an investigation tree."""
    _ensure_dir()
    norm_rating = rating.strip().lower()
    if norm_rating not in VALID_INVESTIGATION_RATINGS:
        if "thieu" in norm_rating or "nhanh" in norm_rating:
            norm_rating = RATING_THIEU_NHANH
        elif "khong" in norm_rating or "sai" in norm_rating or "kem" in norm_rating:
            norm_rating = RATING_KHONG_HUU_ICH
        else:
            norm_rating = RATING_DUNG_HUONG

    records = load_all_investigation_feedback()
    target_idx = -1

    if feedback_id:
        for idx, r in enumerate(records):
            if r.get("feedback_id") == feedback_id:
                target_idx = idx
                break

    if target_idx < 0 and tree_id:
        for idx in range(len(records) - 1, -1, -1):
            if records[idx].get("tree_id") == tree_id:
                target_idx = idx
                break

    if target_idx < 0 and case_id:
        for idx in range(len(records) - 1, -1, -1):
            if records[idx].get("case_id") == case_id:
                target_idx = idx
                break

    if target_idx < 0 and conversation_id:
        for idx in range(len(records) - 1, -1, -1):
            if records[idx].get("conversation_id") == conversation_id:
                target_idx = idx
                break

    if target_idx < 0 and records:
        # Match latest record
        target_idx = len(records) - 1

    if target_idx >= 0:
        records[target_idx]["rating"] = norm_rating
        if user_note:
            records[target_idx]["user_note"] = user_note
        if missing_branch:
            records[target_idx]["missing_branch"] = missing_branch
        if conversation_id:
            records[target_idx]["conversation_id"] = conversation_id
        records[target_idx]["updated_at"] = datetime.now(timezone.utc).isoformat()
        saved_rec = records[target_idx]
    else:
        new_fid = feedback_id or f"FB-TREE-{uuid.uuid4().hex[:8].upper()}"
        saved_rec = {
            "feedback_id": new_fid,
            "tree_id": tree_id or f"TREE-{uuid.uuid4().hex[:8].upper()}",
            "case_id": case_id or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rating": norm_rating,
            "user_note": user_note,
            "missing_branch": missing_branch,
            "conversation_id": conversation_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        records.append(saved_rec)

    # Atomic rewrite
    tmp_path = LOCAL_INVESTIGATION_FEEDBACK_FILE.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp_path.replace(LOCAL_INVESTIGATION_FEEDBACK_FILE)

    return saved_rec


def load_all_investigation_feedback() -> List[Dict[str, Any]]:
    """Load all feedback records from local_cases/investigation_feedback.jsonl."""
    if not LOCAL_INVESTIGATION_FEEDBACK_FILE.is_file():
        return []
    records: List[Dict[str, Any]] = []
    with LOCAL_INVESTIGATION_FEEDBACK_FILE.open("r", encoding="utf-8") as f:
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


def compute_investigation_metrics() -> Dict[str, Any]:
    """Compute measurable metrics for the Step 3 continuous improvement loop."""
    records = load_all_investigation_feedback()
    total_logged = len(records)
    rated_records = [r for r in records if r.get("rating") in VALID_INVESTIGATION_RATINGS]
    total_rated = len(rated_records)

    coverage_rate = (total_rated / total_logged) if total_logged > 0 else 0.0

    ratings_count = {
        RATING_DUNG_HUONG: 0,
        RATING_THIEU_NHANH: 0,
        RATING_KHONG_HUU_ICH: 0,
    }

    total_items_sum = 0
    grounded_items_sum = 0
    generic_items_sum = 0
    exported_files_count = 0

    for r in records:
        total_items_sum += int(r.get("total_items") or 0)
        grounded_items_sum += int(r.get("grounded_items") or 0)
        generic_items_sum += int(r.get("generic_items") or 0)
        exported_files_count += len(r.get("exported_files") or [])

    for r in rated_records:
        r_label = r.get("rating")
        if r_label in ratings_count:
            ratings_count[r_label] += 1

    positive_ratings = ratings_count[RATING_DUNG_HUONG] + ratings_count[RATING_THIEU_NHANH]
    helpful_rate = (positive_ratings / total_rated) if total_rated > 0 else 0.0
    exact_helpful_rate = (ratings_count[RATING_DUNG_HUONG] / total_rated) if total_rated > 0 else 0.0

    basis_coverage_rate = (grounded_items_sum / total_items_sum) if total_items_sum > 0 else 0.0

    return {
        "total_trees_generated": total_logged,
        "total_rated": total_rated,
        "coverage_rate": round(coverage_rate, 4),
        "coverage_percent": round(coverage_rate * 100, 1),
        "helpful_rate": round(helpful_rate, 4),
        "helpful_percent": round(helpful_rate * 100, 1),
        "exact_helpful_rate": round(exact_helpful_rate, 4),
        "exact_helpful_percent": round(exact_helpful_rate * 100, 1),
        "ratings_count": ratings_count,
        "total_items_generated": total_items_sum,
        "grounded_items_count": grounded_items_sum,
        "generic_items_count": generic_items_sum,
        "basis_coverage_rate": round(basis_coverage_rate, 4),
        "basis_coverage_percent": round(basis_coverage_rate * 100, 1),
        "exported_files_count": exported_files_count,
    }


def format_investigation_review_summary() -> str:
    """Render the Review Surface (Bề mặt xem lại) for Step 3 investigation feedback."""
    metrics = compute_investigation_metrics()
    records = load_all_investigation_feedback()
    rated_records = [r for r in records if r.get("rating") in VALID_INVESTIGATION_RATINGS]

    lines = [
        "### 📊 Bề Mặt Xem Lại Cây Điều Tra 4M & Why-Why (Bước 3)",
        "",
        "Hệ thống giám sát chất lượng gợi ý hướng điều tra qua 3 điểm vòng cải thiện liên tục:",
        "",
        "#### 1. 📈 Chỉ số đo lường hiệu quả (Measurable Metrics)",
        f"- **Tổng số cây điều tra đã lập:** {metrics['total_trees_generated']} kế hoạch",
        f"- **Số lượt phản hồi ghi nhận (Rated):** {metrics['total_rated']} lượt",
        f"- **Tỷ lệ bao phủ phản hồi (Coverage):** **{metrics['coverage_percent']}%**",
        f"- **Độ hữu ích ghi nhận từ người dùng:** **{metrics['helpful_percent']}%** "
        f"({metrics['ratings_count'][RATING_DUNG_HUONG]} đúng hướng · "
        f"{metrics['ratings_count'][RATING_THIEU_NHANH]} thiếu nhánh · "
        f"{metrics['ratings_count'][RATING_KHONG_HUU_ICH]} không hữu ích)",
        f"- **Tỷ lệ đúng hướng tuyệt đối:** {metrics['exact_helpful_percent']}%",
        f"- **Hạng mục có căn cứ lịch sử thật:** **{metrics['grounded_items_count']}** / "
        f"{metrics['total_items_generated']} hạng mục (**{metrics['basis_coverage_percent']}%** bám sát ca tương tự)",
        f"- **Số tệp báo cáo đã xuất:** {metrics['exported_files_count']} tệp (.md / .docx)",
        "",
        "#### 2. 🔍 Danh sách phản hồi gần đây (Review Surface)",
    ]

    if rated_records:
        limit_show = min(len(rated_records), 5)
        for idx, r in enumerate(reversed(rated_records[-limit_show:]), start=1):
            r_icon = (
                "✅" if r.get("rating") == RATING_DUNG_HUONG
                else ("⚠️" if r.get("rating") == RATING_THIEU_NHANH else "❌")
            )
            tid = r.get("tree_id", "N/A")
            cid = f" (Vụ `{r.get('case_id')}`)" if r.get("case_id") else ""
            phen = r.get("phenomenon", "")
            phen_str = f" — *{phen[:50]}...*" if len(phen) > 50 else (f" — *{phen}*" if phen else "")
            note = f" — Góp ý: *{r.get('user_note')}*" if r.get("user_note") else ""
            mb = f" — Nhánh thiếu: *{r.get('missing_branch')}*" if r.get("missing_branch") else ""
            lines.append(f"{idx}. {r_icon} `{tid}`{cid} [{r.get('rating')}]{phen_str}{note}{mb}")
    else:
        lines.append("- _Chưa có lượt đánh giá nào từ người dùng._")

    lines.extend([
        "",
        "---",
        "🔒 **Quy tắc an toàn dữ liệu:** Phản hồi lưu độc lập tại `local_cases/investigation_feedback.jsonl`, "
        "tuyệt đối không ghi đè hay làm nhiễu kho tri thức RAG.",
    ])

    return "\n".join(lines)
