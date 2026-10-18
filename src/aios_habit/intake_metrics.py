"""Vòng lặp cải thiện liên tục 3 điểm cho bộ máy thu tri thức (Luật User 2026-10-03).

Bao gồm đủ 3 thành tố bắt buộc:
(1) Điểm hứng feedback: vòng duyệt Đúng / Sửa / Loại tại chỗ ngay trong chat.
(2) Metric đo được:
    - Tỉ lệ mục được duyệt / tổng số mục nháp (`approved_rate`).
    - Độ đủ khuôn theo từng hồ sơ đích (`schema_completeness`).
    - Số phiên theo kho đích và theo chế độ (`sessions_count` theo store & mode).
(3) Vòng xem lại để cải thiện:
    Bề mặt xem lại danh sách mục CHO NẠP theo từng kho đích kèm toàn bộ metric trên.

Tương thích Python 3.11: không dùng f-string nhiều dòng (PEP 701), không type statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    STATUS_CHO_DUYET,
    STATUS_DA_SUA,
    STATUS_DUNG,
    STATUS_LOAI,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
)
from aios_habit.intake_target_profiles import (
    STORE_ID_LSU,
    TargetProfile,
    get_target_profile,
    list_target_profiles,
)


@dataclass(frozen=True)
class IntakeMetricsReport:
    """Báo cáo các chỉ số định lượng đo lường chất lượng thu tri thức."""

    total_draft_items: int
    approved_items: int  # dung + da_sua
    approval_rate: float  # approved_items / total_draft_items
    rejected_items: int
    pending_review_items: int
    pending_ingest_count: int  # số mục mang trạng thái CHO_NAP
    schema_completeness_by_store: Dict[str, float]  # độ đủ khuôn theo từng kho (0.0 - 1.0)
    sessions_by_store_and_mode: Dict[str, Dict[str, int]]  # {store_id: {mode: count}}
    generated_at: str = ""


def compute_intake_metrics(
    store_id: Optional[str] = None,
    staging_store: Optional[IntakeStagingStore] = None,
) -> IntakeMetricsReport:
    """Tính toán toàn bộ metric đo được từ staging store (Điểm 2 của vòng lặp cải thiện).

    Nếu có `store_id`, chỉ tính toán cho kho đích đó.
    Nếu `store_id=None`, tính toán tổng hợp trên toàn hệ thống nhưng vẫn phân rã theo kho.
    """
    store = staging_store or IntakeStagingStore()
    now_iso = datetime.now().isoformat()

    if store_id:
        all_drafts = store.list_draft_items_by_store(store_id)
        all_sessions = store.list_sessions_by_store(store_id)
    else:
        all_drafts = store.list_all_draft_items()
        all_sessions = store.list_sessions_by_store()

    total_drafts = len(all_drafts)
    approved_count = sum(
        1 for d in all_drafts if d.review_status in (STATUS_DUNG, STATUS_DA_SUA)
    )
    rejected_count = sum(1 for d in all_drafts if d.review_status == STATUS_LOAI)
    pending_review_count = sum(1 for d in all_drafts if d.review_status == STATUS_CHO_DUYET)
    pending_ingest_count = sum(1 for d in all_drafts if d.ingest_status == INGEST_CHO_NAP)

    approval_rate = (
        float(approved_count) / float(total_drafts) if total_drafts > 0 else 0.0
    )

    # Tính độ đủ khuôn theo từng hồ sơ đích trên các mục đã duyệt
    # Độ đủ khuôn = tỉ lệ các trường bắt buộc của hồ sơ đích có dữ liệu hợp lệ (khác rỗng và khác 'chưa xác nhận')
    drafts_by_store: Dict[str, List[IntakeDraftItemRecord]] = {}
    for d in all_drafts:
        drafts_by_store.setdefault(d.store_id, []).append(d)

    completeness_by_store: Dict[str, float] = {}
    for sid, s_drafts in drafts_by_store.items():
        profile = get_target_profile(sid)
        if profile is None or not profile.required_fields:
            completeness_by_store[sid] = 1.0
            continue
        # Xét các mục đã được duyệt (hoặc toàn bộ nếu chưa có mục nào duyệt)
        target_drafts = [
            d for d in s_drafts if d.review_status in (STATUS_DUNG, STATUS_DA_SUA)
        ]
        if not target_drafts:
            target_drafts = s_drafts

        scores = [profile.calculate_completeness(d.fields) for d in target_drafts]
        completeness_by_store[sid] = sum(scores) / float(len(scores)) if scores else 0.0

    # Phân bổ số phiên theo kho đích và theo chế độ
    sessions_by_store_and_mode: Dict[str, Dict[str, int]] = {}
    for sess in all_sessions:
        s_dict = sessions_by_store_and_mode.setdefault(sess.store_id, {})
        s_dict[sess.mode] = s_dict.get(sess.mode, 0) + 1

    return IntakeMetricsReport(
        total_draft_items=total_drafts,
        approved_items=approved_count,
        approval_rate=round(approval_rate, 4),
        rejected_items=rejected_count,
        pending_review_items=pending_review_count,
        pending_ingest_count=pending_ingest_count,
        schema_completeness_by_store=completeness_by_store,
        sessions_by_store_and_mode=sessions_by_store_and_mode,
        generated_at=now_iso,
    )


# ---------------------------------------------------------------------------
# Bề mặt xem lại để cải thiện (Điểm 3 của vòng lặp cải thiện)
# ---------------------------------------------------------------------------


def format_review_surface_markdown(
    store_id: Optional[str] = None,
    staging_store: Optional[IntakeStagingStore] = None,
) -> str:
    """Tạo nội dung Markdown cho bề mặt xem lại danh sách mục CHO NẠP và metric cải thiện.

    Đáp ứng Điểm (3) của vòng lặp cải thiện liên tục.
    """
    store = staging_store or IntakeStagingStore()
    target_sid = store_id or STORE_ID_LSU
    profile = get_target_profile(target_sid)
    profile_name = profile.display_name if profile else target_sid

    metrics = compute_intake_metrics(target_sid, staging_store=store)
    pending_items = store.list_draft_items_by_store(target_sid, ingest_status=INGEST_CHO_NAP)

    lines: List[str] = [
        "## 📋 Bề mặt xem lại & cải thiện thu tri thức — %s" % profile_name,
        "",
        "> **Quy tắc 3 điểm (2026-10-03):** (1) Điểm hứng feedback tại chỗ -> "
        "(2) Metric đo được -> (3) Bề mặt xem lại danh sách mục CHO NẠP.",
        "",
        "### 📊 1. Chỉ số đo lường chất lượng (Metrics)",
        "",
        "- **Tỉ lệ duyệt thành công:** **%.1f%%** (%d/%d mục nháp)"
        % (metrics.approval_rate * 100.0, metrics.approved_items, metrics.total_draft_items),
        "- **Số mục sẵn sàng CHỜ NẠP (`CHO_NAP`):** **%d** mục" % metrics.pending_ingest_count,
        "- **Số mục bị loại:** **%d** mục" % metrics.rejected_items,
    ]

    # Độ đủ khuôn
    store_comp = metrics.schema_completeness_by_store.get(target_sid, 0.0)
    lines.append("- **Độ đủ khuôn (%s):** **%.1f%%** (các trường bắt buộc có dữ liệu thực)" % (profile_name, store_comp * 100.0))

    # Phiên theo chế độ
    mode_counts = metrics.sessions_by_store_and_mode.get(target_sid, {})
    pv_count = mode_counts.get("phong_van", 0)
    day_count = mode_counts.get("day", 0)
    lines.append("- **Số phiên thu tri thức:** **%d** (Phỏng vấn: %d | Dạy: %d)" % (pv_count + day_count, pv_count, day_count))
    lines.append("")

    # Danh sách mục CHO_NAP
    lines.extend([
        "### 📥 2. Danh sách mục CHỜ NẠP theo kho đích (%s)" % profile_name,
        "",
    ])

    if not pending_items:
        lines.append("*Hiện chưa có mục nào ở trạng thái CHỜ NẠP cho kho này. "
                     "Các mục cần được duyệt 'Đúng' hoặc 'Sửa' trong khung chat.*")
        lines.append("")
    else:
        lines.append("| ID Mục | Mã lỗi | Hiện tượng | Nguyên nhân | Đối sách | Công đoạn | Nhãn nguồn |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for it in pending_items:
            f = it.fields
            m_loi = f.get("ma_loi", "chưa xác nhận")
            ht = f.get("hien_tuong", "chưa xác nhận")[:40].replace("\n", " ")
            nn = f.get("nguyen_nhan", "chưa xác nhận")[:40].replace("\n", " ")
            ds = f.get("doi_sach", "chưa xác nhận")[:40].replace("\n", " ")
            cd = f.get("cong_doan", "chưa xác nhận")
            tag = it.source_tag
            lines.append("| `%s` | **%s** | %s | %s | %s | %s | `%s` |" % (
                it.draft_id, m_loi, ht, nn, ds, cd, tag
            ))
        lines.append("")

    # Vòng lặp cải thiện: Khuyến nghị hành động
    lines.extend([
        "### 🔄 3. Vòng xem lại để cải thiện câu hỏi (Improvement Loop)",
        "",
    ])
    if store_comp < 0.8:
        lines.append(
            "- ⚠️ **Cảnh báo độ đủ khuôn:** Độ đủ khuôn hiện đạt %.1f%% (< 80%%). "
            "Cần tăng cường câu hỏi đào sâu về các trường còn thiếu (như Công đoạn, Nguyên nhân gốc rễ Why-Why) "
            "ngay trong phiên trước khi kết thúc." % (store_comp * 100.0)
        )
    else:
        lines.append("- ✅ **Độ đủ khuôn đạt chuẩn:** Các mục nháp đạt tỉ lệ điền trường bắt buộc cao.")

    if metrics.total_draft_items > 0 and metrics.approval_rate < 0.7:
        lines.append(
            "- ⚠️ **Tỉ lệ duyệt thấp (%.1f%%):** Chuyên gia sửa hoặc loại nhiều mục. "
            "Xem lại các câu hỏi đào sâu để tránh câu hỏi mang tính suy diễn hoặc quá rộng." % (metrics.approval_rate * 100.0)
        )
    else:
        lines.append("- ✅ **Tỉ lệ duyệt tốt:** Đa số các mục nháp được chuyên gia xác nhận đúng.")

    return "\n".join(lines)
