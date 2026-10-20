# -*- coding: utf-8 -*-
"""Vong lap cai thien lien tuc & do luong metric cho Log Chart Builder (Requirement 2c).

Nguyen tac bat buoc:
- Duoi moi bieu do co diem cham huu ich/chua huu ich; che bat buoc ghi ro ly do.
- Metric do duoc: so luot dung tung kieu bieu do, ty le ve thanh cong (render success rate).
- Be mat xem lai (review surface) de biet kieu bieu do nao duoc dung that.
- Luu tai local_cases/chart_feedback.jsonl va local_cases/chart_render_events.jsonl.
- KHONG ghi vao kho tri thuc.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()

RATING_HUU_ICH = "huu_ich"
RATING_CHUA_HUU_ICH = "chua_huu_ich"

PRESET_CHART_DISLIKE_REASONS = [
    "Sai kiểu biểu đồ không phù hợp mục đích",
    "Lọc dữ liệu không đúng điều kiện",
    "Nhận diện sai cột hoặc sai trục tọa độ",
    "Tỷ lệ trục / khoảng chia không rõ ràng",
    "Đường SMA / Giới hạn SPC tính chưa đúng",
    "Lý do khác",
]


def _local_cases_dir() -> Path:
    env_p = os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    if env_p:
        p = Path(env_p)
    else:
        p = Path.cwd() / "local_cases"
    p.mkdir(parents=True, exist_ok=True)
    return p


def chart_feedback_file() -> Path:
    return _local_cases_dir() / "chart_feedback.jsonl"


def chart_render_events_file() -> Path:
    return _local_cases_dir() / "chart_render_events.jsonl"


def record_chart_feedback(
    conversation_id: str,
    chart_id: str,
    chart_type: str,
    rating: str,
    *,
    reason: str = "",
    file_name: str = "",
    user_comment: str = "",
) -> Dict[str, Any]:
    """Ghi nhan danh gia cua nguoi dung cho bieu do."""
    rating = str(rating or "").strip().lower()
    if rating not in (RATING_HUU_ICH, RATING_CHUA_HUU_ICH):
        return {"ok": False, "error_vi": f"Đánh giá không hợp lệ (phải là '{RATING_HUU_ICH}' hoặc '{RATING_CHUA_HUU_ICH}')."}

    reason = str(reason or "").strip()
    if rating == RATING_CHUA_HUU_ICH and not reason:
        return {"ok": False, "error_vi": "Khi đánh giá chưa hữu ích, bắt buộc phải chọn hoặc nhập lý do góp ý."}

    record = {
        "event_time": datetime.now(timezone.utc).isoformat(),
        "conversation_id": conversation_id,
        "chart_id": chart_id,
        "chart_type": chart_type,
        "rating": rating,
        "reason": reason,
        "user_comment": user_comment,
        "file_name": file_name,
    }

    with _LOCK:
        try:
            with open(chart_feedback_file(), "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            return {"ok": False, "error_vi": f"Lỗi khi lưu phản hồi: {e}"}

    return {"ok": True, "message": "Đã ghi nhận phản hồi đánh giá biểu đồ thành công."}


def record_chart_render_event(
    chart_type: str,
    success: bool,
    *,
    duration_ms: float = 0.0,
    error_msg: str = "",
    file_name: str = "",
    rows_count: int = 0,
) -> None:
    """Ghi nhan mot luot ve bieu do de theo doi metric he thong."""
    record = {
        "event_time": datetime.now(timezone.utc).isoformat(),
        "chart_type": chart_type,
        "success": bool(success),
        "duration_ms": round(duration_ms, 2),
        "error_msg": str(error_msg or ""),
        "file_name": str(file_name or ""),
        "rows_count": int(rows_count),
    }

    with _LOCK:
        try:
            with open(chart_render_events_file(), "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass


def get_chart_metrics() -> Dict[str, Any]:
    """Tong hop toan bo metric ve bieu do va phan hoi."""
    total_renders = 0
    successful_renders = 0
    failed_renders = 0
    usage_by_type: Dict[str, int] = {}

    rev_file = chart_render_events_file()
    if rev_file.exists():
        with open(rev_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    total_renders += 1
                    ct = str(d.get("chart_type") or "unknown")
                    usage_by_type[ct] = usage_by_type.get(ct, 0) + 1
                    if d.get("success"):
                        successful_renders += 1
                    else:
                        failed_renders += 1
                except Exception:
                    pass

    success_rate_pct = (successful_renders / total_renders * 100.0) if total_renders > 0 else 100.0

    # Doc feedback
    feedback_counts = {RATING_HUU_ICH: 0, RATING_CHUA_HUU_ICH: 0}
    reasons_list: List[str] = []
    fb_by_type: Dict[str, Dict[str, int]] = {}

    fb_file = chart_feedback_file()
    if fb_file.exists():
        with open(fb_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    r = d.get("rating")
                    ct = str(d.get("chart_type") or "unknown")
                    fb_by_type.setdefault(ct, {RATING_HUU_ICH: 0, RATING_CHUA_HUU_ICH: 0})
                    if r in feedback_counts:
                        feedback_counts[r] += 1
                        fb_by_type[ct][r] = fb_by_type[ct].get(r, 0) + 1
                    if r == RATING_CHUA_HUU_ICH and d.get("reason"):
                        reasons_list.append(str(d["reason"]))
                except Exception:
                    pass

    return {
        "total_renders": total_renders,
        "successful_renders": successful_renders,
        "failed_renders": failed_renders,
        "render_success_rate_pct": round(success_rate_pct, 2),
        "usage_by_type": usage_by_type,
        "feedback_counts": feedback_counts,
        "feedback_by_type": fb_by_type,
        "negative_reasons": reasons_list,
    }


def get_chart_feedback_summary_markdown() -> str:
    """Tao bao cao tom tat be mat xem lai (review surface) bang markdown."""
    m = get_chart_metrics()
    total_renders = m["total_renders"]
    rate = m["render_success_rate_pct"]
    huu_ich = m["feedback_counts"][RATING_HUU_ICH]
    chua_huu_ich = m["feedback_counts"][RATING_CHUA_HUU_ICH]
    total_fb = huu_ich + chua_huu_ich
    satisfaction_rate = (huu_ich / total_fb * 100.0) if total_fb > 0 else 100.0

    lines: List[str] = [
        "### 📊 Bề mặt xem lại chất lượng & tần suất sử dụng biểu đồ (Review Surface)",
        "",
        f"- **Tổng lượt tạo biểu đồ**: `{total_renders}` lượt",
        f"- **Tỷ lệ vẽ thành công**: `{rate}%` ({m['successful_renders']} thành công / {m['failed_renders']} lỗi)",
        f"- **Tổng lượt người dùng đánh giá**: `{total_fb}` lượt",
        f"- **Tỷ lệ hài lòng (Hữu ích)**: `{satisfaction_rate:.1f}%` ({huu_ich} hữu ích / {chua_huu_ich} chưa hữu ích)",
        "",
        "#### 1. Thống kê theo từng kiểu biểu đồ:",
        "| Kiểu biểu đồ | Số lượt vẽ | Hữu ích 👍 | Chưa hữu ích 👎 |",
        "| :--- | :---: | :---: | :---: |",
    ]

    usage_map = m["usage_by_type"]
    fb_map = m["feedback_by_type"]
    all_types = sorted(set(list(usage_map.keys()) + list(fb_map.keys())))

    if not all_types:
        lines.append("| *(Chưa có dữ liệu vận hành)* | 0 | 0 | 0 |")
    else:
        for ct in all_types:
            u_cnt = usage_map.get(ct, 0)
            fb_stat = fb_map.get(ct, {})
            h_cnt = fb_stat.get(RATING_HUU_ICH, 0)
            c_cnt = fb_stat.get(RATING_CHUA_HUU_ICH, 0)
            lines.append(f"| `{ct}` | {u_cnt} | {h_cnt} | {c_cnt} |")

    if m["negative_reasons"]:
        lines.extend([
            "",
            "#### 2. Các lý do người dùng góp ý khi chê (Chưa hữu ích):",
        ])
        for r in m["negative_reasons"][-10:]:
            lines.append(f"- ⚠️ {r}")

    lines.append("")
    lines.append("*Dữ liệu được lưu trữ độc lập tại `local_cases/chart_feedback.jsonl` (Vòng lặp cải thiện liên tục).*")
    return "\n".join(lines)
