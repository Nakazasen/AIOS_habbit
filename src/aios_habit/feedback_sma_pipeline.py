"""Module tinh toan xu huong phan hoi nguoi dung SMA(20).

Kien truc tu hoc thich nghi theo thiet ke muc 5.2 (DESKTOP-AIOS-SELF-LEARN-HERMES-ANALYSIS-HOME):
- Tinh Simple Moving Average tren 20 luot danh gia gan nhat (SMA(20)) theo 3 truc:
  1. Theo tung cau hoi / cum cau hoi tuong duong (Query Cluster).
  2. Theo tai lieu nguon trich dan (Source Document).
  3. Theo mien nghiep vu / so tay (Notebook Domain).
- Dinh nghia nguong xau (Negative Trigger):
  Trong cua so 20 luot gan nhat: Dislike >= 3 va ty le Dislike >= 30%.
  -> Trang thai ALERT_EXPERT_REVIEW: Dong goi day vao Hang doi Phe duyet Chuyen gia.
- Dinh nghia nguong tot (Positive Trigger / Tri thuc ung vien):
  Trong cua so 20 luot gan nhat: Like >= 5 va ty le Like >= 85%.
  -> Trang thai KNOWLEDGE_CANDIDATE: Gan nhan "Ung vien tri thuc chuan" de chuyen gia thang hang.
- Tinh toan toi uu sieu toc < 50ms de tich hop truc tiep vao Streamlit / Chat khong gay giat lag.

Tuong thich Python 3.11.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from aios_habit.answer_feedback import (
    RATING_CHUA_HUU_ICH,
    RATING_HUU_ICH,
    REASON_CATEGORIES,
    AnswerFeedbackRecord,
    compute_question_hash,
    infer_reason_category,
    load_deduplicated_feedback,
)

DEFAULT_SMA_WINDOW = 20

# Nguong canh bao xau: Dislike >= 3 va ty le Dislike >= 30%
MIN_DISLIKE_COUNT_FOR_ALERT = 3
MIN_DISLIKE_RATIO_FOR_ALERT = 0.30

# Nguong tot (Ung vien tri thuc): Like >= 5 va ty le Like >= 85%
MIN_LIKE_COUNT_FOR_CANDIDATE = 5
MIN_LIKE_RATIO_FOR_CANDIDATE = 0.85

# Trang thai danh gia
STATUS_ALERT_EXPERT = "ALERT_EXPERT_REVIEW"
STATUS_KNOWLEDGE_CANDIDATE = "KNOWLEDGE_CANDIDATE"
STATUS_STABLE = "STABLE"


@dataclass
class SMAWindowResult:
    """Ket qua tinh toan SMA(20) cho mot thuc the theo cua so truot."""

    dimension: str  # 'query_cluster' | 'source_document' | 'domain' | 'global'
    key: str
    display_name: str
    sample_count: int
    window_size: int
    like_count: int
    dislike_count: int
    like_ratio: float
    dislike_ratio: float
    reason_counts: Dict[str, int]
    status: str  # STATUS_ALERT_EXPERT | STATUS_KNOWLEDGE_CANDIDATE | STATUS_STABLE
    is_alert: bool
    is_candidate: bool
    recommendation: str
    recent_message_ids: List[str]
    latest_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SMAPipelineReport:
    """Bao cao tong the ket qua pipeline tinh toan xu huong SMA(20)."""

    total_raw_records: int
    deduplicated_records: int
    window_size: int
    calculation_time_ms: float
    by_query_cluster: Dict[str, SMAWindowResult]
    by_source_document: Dict[str, SMAWindowResult]
    by_domain: Dict[str, SMAWindowResult]
    global_sma: SMAWindowResult
    alerts: List[SMAWindowResult]
    candidates: List[SMAWindowResult]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_raw_records": self.total_raw_records,
            "deduplicated_records": self.deduplicated_records,
            "window_size": self.window_size,
            "calculation_time_ms": round(self.calculation_time_ms, 2),
            "by_query_cluster": {k: v.to_dict() for k, v in self.by_query_cluster.items()},
            "by_source_document": {k: v.to_dict() for k, v in self.by_source_document.items()},
            "by_domain": {k: v.to_dict() for k, v in self.by_domain.items()},
            "global_sma": self.global_sma.to_dict(),
            "alerts": [v.to_dict() for v in self.alerts],
            "candidates": [v.to_dict() for v in self.candidates],
            "generated_at": self.generated_at,
        }


def evaluate_sma_window(
    records: Sequence[Union[AnswerFeedbackRecord, Dict[str, Any]]],
    dimension: str,
    key: str,
    display_name: str = "",
    window_size: int = DEFAULT_SMA_WINDOW,
) -> SMAWindowResult:
    """Tinh toan chi so SMA(20) cho danh sach ban ghi cua mot thuc the."""
    # Chuyen doi sang AnswerFeedbackRecord neu truyen vao Dict
    norm_records: List[AnswerFeedbackRecord] = []
    for r in records:
        if isinstance(r, AnswerFeedbackRecord):
            norm_records.append(r)
        elif isinstance(r, dict):
            norm_records.append(AnswerFeedbackRecord.from_dict(r))

    # Sap xep theo thoi gian hoac giu nguyen thu tu xuat hien, lay toi da window_size phieu gan nhat
    window = norm_records[-window_size:] if norm_records else []
    sample_count = len(window)

    like_count = 0
    dislike_count = 0
    reason_counts: Dict[str, int] = {cat: 0 for cat in REASON_CATEGORIES}
    message_ids: List[str] = []
    latest_ts = ""

    for rec in window:
        if rec.message_id:
            message_ids.append(rec.message_id)
        if rec.created_at:
            latest_ts = rec.created_at

        if rec.rating in (RATING_HUU_ICH, "like", "1", "up"):
            like_count += 1
        elif rec.rating in (RATING_CHUA_HUU_ICH, "dislike", "0", "down"):
            dislike_count += 1
            cat = str(rec.reason_category or "").strip()
            if not cat:
                cat = infer_reason_category(rec.reason)
            if cat in reason_counts:
                reason_counts[cat] += 1
            else:
                reason_counts[cat] = 1

    if sample_count > 0:
        like_ratio = round(like_count / sample_count, 4)
        dislike_ratio = round(dislike_count / sample_count, 4)
    else:
        like_ratio = 0.0
        dislike_ratio = 0.0

    # Kiem tra nguong xau & nguong tot
    is_alert = bool(
        dislike_count >= MIN_DISLIKE_COUNT_FOR_ALERT
        and dislike_ratio >= MIN_DISLIKE_RATIO_FOR_ALERT
    )
    is_candidate = bool(
        like_count >= MIN_LIKE_COUNT_FOR_CANDIDATE
        and like_ratio >= MIN_LIKE_RATIO_FOR_CANDIDATE
    )

    if is_alert:
        status = STATUS_ALERT_EXPERT
        top_reason = max(reason_counts.items(), key=lambda x: x[1])[0] if reason_counts else "sai"
        recommendation = (
            f"CẢNH BÁO: Dislike {dislike_count}/{sample_count} ({dislike_ratio*100:.1f}% >= 30%). "
            f"Lý do chính: '{top_reason}'. Đẩy vào Hàng đợi Chuyên gia phê duyệt sửa đổi gốc."
        )
    elif is_candidate:
        status = STATUS_KNOWLEDGE_CANDIDATE
        recommendation = (
            f"ỨNG VIÊN TRI THỨC: Like {like_count}/{sample_count} ({like_ratio*100:.1f}% >= 85%). "
            f"Đề xuất chuyên gia thẩm định đưa vào Kho Tri Thức Chuẩn."
        )
    else:
        status = STATUS_STABLE
        if sample_count == 0:
            recommendation = "Chưa có dữ liệu đánh giá."
        elif dislike_count > 0:
            recommendation = (
                f"Ổn định ({dislike_count} dislike đơn lẻ, chưa vượt ngưỡng cảnh báo SMA(20))."
            )
        else:
            recommendation = f"Ổn định: {like_count}/{sample_count} lượt hữu ích."

    return SMAWindowResult(
        dimension=dimension,
        key=key,
        display_name=display_name or key,
        sample_count=sample_count,
        window_size=window_size,
        like_count=like_count,
        dislike_count=dislike_count,
        like_ratio=like_ratio,
        dislike_ratio=dislike_ratio,
        reason_counts=reason_counts,
        status=status,
        is_alert=is_alert,
        is_candidate=is_candidate,
        recommendation=recommendation,
        recent_message_ids=message_ids,
        latest_timestamp=latest_ts,
    )


def compute_feedback_sma_pipeline(
    records: Optional[Sequence[Union[AnswerFeedbackRecord, Dict[str, Any]]]] = None,
    window_size: int = DEFAULT_SMA_WINDOW,
) -> SMAPipelineReport:
    """Thuc thi pipeline tinh toan SMA(20) tren 3 truc du lieu.

    Dam bao thoi gian tinh toan < 50ms.
    """
    t_start = time.perf_counter()

    if records is None:
        norm_records = load_deduplicated_feedback()
        total_raw = len(norm_records)
    else:
        norm_records = []
        for r in records:
            if isinstance(r, AnswerFeedbackRecord):
                norm_records.append(r)
            elif isinstance(r, dict):
                norm_records.append(AnswerFeedbackRecord.from_dict(r))
        total_raw = len(records)

    dedup_count = len(norm_records)

    # Nhom 1: Theo cum cau hoi (Query Cluster) - gom theo question_hash
    query_groups: Dict[str, List[AnswerFeedbackRecord]] = defaultdict(list)
    query_titles: Dict[str, str] = {}
    for rec in norm_records:
        q_hash = rec.question_hash or compute_question_hash(rec.question)
        if not q_hash:
            q_hash = "cau_hoi_khong_xac_dinh"
        query_groups[q_hash].append(rec)
        if q_hash not in query_titles and rec.question:
            query_titles[q_hash] = rec.question[:80]

    # Nhom 2: Theo tai lieu nguon trich dan (Source Document)
    source_groups: Dict[str, List[AnswerFeedbackRecord]] = defaultdict(list)
    for rec in norm_records:
        if rec.cited_sources:
            for src in rec.cited_sources:
                s_clean = str(src).strip()
                if s_clean:
                    source_groups[s_clean].append(rec)
        else:
            source_groups["(khong_trich_dan)"].append(rec)

    # Nhom 3: Theo mien / so tay (Notebook Domain)
    domain_groups: Dict[str, List[AnswerFeedbackRecord]] = defaultdict(list)
    for rec in norm_records:
        dom = str(rec.domain or rec.topic or rec.lane or "chung").strip()
        domain_groups[dom].append(rec)

    # Tinh SMA(20) cho tung cum
    by_query_cluster: Dict[str, SMAWindowResult] = {}
    for q_hash, group in query_groups.items():
        disp = query_titles.get(q_hash) or q_hash
        by_query_cluster[q_hash] = evaluate_sma_window(
            group,
            dimension="query_cluster",
            key=q_hash,
            display_name=disp,
            window_size=window_size,
        )

    by_source_document: Dict[str, SMAWindowResult] = {}
    for src_name, group in source_groups.items():
        by_source_document[src_name] = evaluate_sma_window(
            group,
            dimension="source_document",
            key=src_name,
            display_name=src_name,
            window_size=window_size,
        )

    by_domain: Dict[str, SMAWindowResult] = {}
    for dom_name, group in domain_groups.items():
        by_domain[dom_name] = evaluate_sma_window(
            group,
            dimension="domain",
            key=dom_name,
            display_name=dom_name,
            window_size=window_size,
        )

    # Tinh toan Global SMA
    global_sma = evaluate_sma_window(
        norm_records,
        dimension="global",
        key="global",
        display_name="Toàn hệ thống",
        window_size=window_size,
    )

    # Thu thap danh sach Canh bao & Ung vien tri thuc
    all_evaluated: List[SMAWindowResult] = (
        list(by_query_cluster.values())
        + list(by_source_document.values())
        + list(by_domain.values())
    )

    alerts = [res for res in all_evaluated if res.is_alert]
    candidates = [res for res in all_evaluated if res.is_candidate]

    # Sap xep uu tien xu ly: canh bao co ty le dislike cao nhat len dau
    alerts.sort(key=lambda x: (x.dislike_ratio, x.dislike_count), reverse=True)
    candidates.sort(key=lambda x: (x.like_ratio, x.like_count), reverse=True)

    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    return SMAPipelineReport(
        total_raw_records=total_raw,
        deduplicated_records=dedup_count,
        window_size=window_size,
        calculation_time_ms=elapsed_ms,
        by_query_cluster=by_query_cluster,
        by_source_document=by_source_document,
        by_domain=by_domain,
        global_sma=global_sma,
        alerts=alerts,
        candidates=candidates,
    )


def format_sma_pipeline_summary_markdown(report: SMAPipelineReport) -> str:
    """Dinh dang bao cao tong ket SMA(20) sang Markdown phuc vu chat & dashboard."""
    lines: List[str] = []
    lines.append("### 📊 Phân Tích Xu Hướng Phản Hồi SMA(20) (Vòng Lặp Tự Học)")
    lines.append(
        f"- **Tổng số phiếu:** {report.deduplicated_records} phiếu hợp lệ "
        f"(từ {report.total_raw_records} bản ghi thô). Cửa sổ trượt: **SMA({report.window_size})**."
    )
    lines.append(f"- **Thời gian tính toán pipeline:** `{report.calculation_time_ms:.2f} ms` (chuẩn < 50ms).")

    g = report.global_sma
    lines.append(
        f"- **Toàn hệ thống (20 phiếu gần nhất):** 👍 {g.like_count} hữu ích ({g.like_ratio*100:.1f}%) | "
        f"👎 {g.dislike_count} chưa hữu ích ({g.dislike_ratio*100:.1f}%)."
    )

    # 1. Hàng đợi cảnh báo chuyên gia
    lines.append("\n#### 🚨 Hàng Đợi Cảnh Báo Chuyên Gia (Ngưỡng: Dislike ≥ 3 & Tỉ lệ Dislike ≥ 30%)")
    if not report.alerts:
        lines.append("- *Hiện không có cụm câu hỏi hay tài liệu nào vượt ngưỡng cảnh báo xấu.*")
    else:
        for idx, alt in enumerate(report.alerts, 1):
            reasons_str = ", ".join(f"{k}: {v}" for k, v in alt.reason_counts.items() if v > 0)
            lines.append(
                f"{idx}. **[{alt.dimension.upper()}] `{alt.display_name}`**\n"
                f"   - Dislike: **{alt.dislike_count}/{alt.sample_count}** ({alt.dislike_ratio*100:.1f}%).\n"
                f"   - Phân loại lý do: `{reasons_str or 'không nêu'}`\n"
                f"   - Khuyến nghị: `{alt.recommendation}`"
            )

    # 2. Ứng viên tri thức chuẩn
    lines.append("\n#### 🌟 Ứng Viên Tri Thức Chuẩn (Ngưỡng: Like ≥ 5 & Tỉ lệ Like ≥ 85%)")
    if not report.candidates:
        lines.append("- *Chưa có câu trả lời nào đạt đủ ngưỡng ứng viên tri thức (≥ 5 Like và ≥ 85%).*")
    else:
        for idx, cand in enumerate(report.candidates, 1):
            lines.append(
                f"{idx}. **[{cand.dimension.upper()}] `{cand.display_name}`**\n"
                f"   - Like: **{cand.like_count}/{cand.sample_count}** ({cand.like_ratio*100:.1f}%).\n"
                f"   - Khuyến nghị: `{cand.recommendation}`"
            )

    # 3. Thống kê theo 3 trục
    lines.append("\n#### 📈 Thống Kê Chi Tiết 3 Trục SMA(20)")
    lines.append(f"- **Cụm câu hỏi (Query Clusters):** {len(report.by_query_cluster)} cụm.")
    lines.append(f"- **Tài liệu nguồn trích dẫn (Source Documents):** {len(report.by_source_document)} tài liệu.")
    lines.append(f"- **Miền nghiệp vụ / Sổ tay (Domains):** {len(report.by_domain)} miền.")

    return "\n".join(lines)
