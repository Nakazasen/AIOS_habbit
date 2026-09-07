"""Reporting engine for LSU Iris historical replay comparisons.

Generates clean, aggregate-only Vietnamese markdown and dictionary reports
without leaking raw records, proprietary machine parameters, or local file paths.

Adheres strictly to specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md and
specs/008-evidence-case-loop/plan.md section 5.1.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from aios_habit.production_prediction.evaluation import (
    ReplayProtocol,
    evaluate_ewma_baseline,
    evaluate_replay_baseline,
    evaluate_supervised_model,
)
from aios_habit.production_prediction.models import (
    JoinedUnitTrace,
    LsuDatasetSnapshot,
)


def generate_replay_comparison_report(
    snapshot: LsuDatasetSnapshot,
    traces: Dict[str, JoinedUnitTrace],
    protocol: ReplayProtocol,
) -> Dict[str, Any]:
    """Generate structured comparison report between no_alert, EWMA, and optional supervised model."""
    metrics_no_alert = evaluate_replay_baseline(snapshot, traces, protocol)
    ewma_report = evaluate_ewma_baseline(snapshot, traces, protocol, return_report=True)
    metrics_ewma = ewma_report.metrics_by_method["ewma"]
    metrics_model = evaluate_supervised_model(snapshot, traces, protocol)

    total_units = len(traces)
    ok_count = sum(1 for t in traces.values() if t.target_label == "OK")
    ng_count = sum(1 for t in traces.values() if t.target_label == "NG")
    unknown_count = sum(1 for t in traces.values() if t.target_label == "UNKNOWN")

    methods_summary: List[Dict[str, Any]] = [
        {
            "ten_phuong_an": "Không phát cảnh báo (Phương án nền đối chứng)",
            "trang_thai": "Đã đánh giá",
            "dung_ng": metrics_no_alert.true_positives,
            "canh_bao_nham": metrics_no_alert.false_positives,
            "bo_sot_ng": metrics_no_alert.false_negatives,
            "ty_le_phat_hien_ng": "0.0%",
            "thoi_gian_canh_bao_som_giay": 0.0,
            "ly_do": metrics_no_alert.reason,
            "ke_hoach_bo_sung": "Dùng để đối chứng hiệu quả giảm tỷ lệ bỏ sót lỗi của các phương án cảnh báo sớm.",
            "ket_luan": "Phương án thụ động, toàn bộ lỗi NG chỉ được ghi nhận khi đã xảy ra tại JIG.",
        },
        {
            "ten_phuong_an": "Kiểm soát quá trình thống kê EWMA",
            "trang_thai": "Khuyến nghị thử nghiệm chạy bóng",
            "dung_ng": metrics_ewma.true_positives,
            "canh_bao_nham": metrics_ewma.false_positives,
            "bo_sot_ng": metrics_ewma.false_negatives,
            "ty_le_phat_hien_ng": f"{metrics_ewma.recall_ng_percent:.1f}%",
            "thoi_gian_canh_bao_som_giay": metrics_ewma.median_lead_time_seconds,
            "ket_luan": (
                f"Phát hiện sớm {metrics_ewma.true_positives}/{ng_count} lỗi NG trước thời điểm kiểm tra JIG."
                if metrics_ewma.true_positives > 0
                else "Chưa ghi nhận cảnh báo sớm vượt ngưỡng trên tập dữ liệu này."
            ),
        },
        {
            "ten_phuong_an": "Mô hình học máy hồi quy Logistic",
            "trang_thai": "Chưa đủ điều kiện kích hoạt",
            "dung_ng": 0,
            "canh_bao_nham": 0,
            "bo_sot_ng": ng_count,
            "ty_le_phat_hien_ng": "Chưa áp dụng",
            "thoi_gian_canh_bao_som_giay": 0.0,
            "ly_do": metrics_model.reason,
            "ke_hoach_bo_sung": (
                "Cần tích lũy tối thiểu 200 Unit và 30 lỗi NG thực tế qua chế độ chạy bóng "
                "trước khi huấn luyện mô hình có giám sát."
            ),
            "ket_luan": "Nhánh mô hình học máy giữ trạng thái chưa kích hoạt (not_applicable).",
        },
    ]

    # Count distinct time periods (e.g. distinct dates from assembly_time or jig_event_time)
    distinct_periods = set()
    for t in traces.values():
        if t.assembly_time:
            distinct_periods.add(t.assembly_time.strftime("%Y-%m-%d"))
        elif t.jig_event_time:
            distinct_periods.add(t.jig_event_time.strftime("%Y-%m-%d"))
    distinct_period_count = len(distinct_periods)

    # Evaluation conclusion according to rubric sections 3.1 & 3.2
    auto_shadow_unmet_reasons: List[str] = []
    if ewma_report.future_leakage_detected:
        auto_shadow_unmet_reasons.append(
            "Phát hiện rò rỉ dữ liệu tương lai (future_leakage_detected=True) trong quá trình phát lại."
        )
    if metrics_ewma.status != "evaluated":
        auto_shadow_unmet_reasons.append("Phương án EWMA chưa hoàn tất đánh giá trên tập dữ liệu.")
    if total_units < 200:
        auto_shadow_unmet_reasons.append(f"Cỡ mẫu chưa đủ 200 Unit (hiện có {total_units} Unit).")
    if ng_count < 30:
        auto_shadow_unmet_reasons.append(f"Số lỗi thực tế chưa đủ 30 NG (hiện có {ng_count} NG).")
    if distinct_period_count < 3:
        auto_shadow_unmet_reasons.append(
            f"Chưa đủ 3 khoảng thời gian đánh giá độc lập (hiện có {distinct_period_count} khoảng)."
        )
    if metrics_ewma.recall_ng_percent < 80.0:
        auto_shadow_unmet_reasons.append(
            f"Tỷ lệ phát hiện lỗi NG chưa đạt 80% (hiện đạt {metrics_ewma.recall_ng_percent:.1f}%)."
        )
    if metrics_ewma.false_alert_rate_per_100 > 10.0:
        auto_shadow_unmet_reasons.append(
            f"Tỷ lệ cảnh báo nhầm vượt ngưỡng 10/100 Unit (hiện là {metrics_ewma.false_alert_rate_per_100:.1f}/100)."
        )
    if metrics_ewma.median_lead_time_seconds <= 0.0:
        auto_shadow_unmet_reasons.append("Trung vị thời gian cảnh báo sớm chưa lớn hơn 0 giây.")
    if metrics_ewma.maximum_alerts_per_unit > 1:
        auto_shadow_unmet_reasons.append(
            f"Mỗi Unit có nhiều hơn 1 cảnh báo trong cửa sổ (hiện là {metrics_ewma.maximum_alerts_per_unit})."
        )
    if metrics_ewma.false_negatives >= metrics_no_alert.false_negatives:
        auto_shadow_unmet_reasons.append(
            "Hiệu quả cảnh báo chưa tốt hơn phương án đối chứng không cảnh báo về số lỗi bỏ sót."
        )

    # Check slice invariant: no JIG group with >= 10 NGs has recall < 60%
    jig_ng_total: Dict[str, int] = {}
    jig_ng_detected: Dict[str, int] = {}
    for u_serial, t in traces.items():
        jig_names = {j.jig_id for j in t.jig_measurements if j.jig_id}
        if not jig_names:
            jig_names = {"CHUA_XAC_DINH"}
        if t.target_label == "NG":
            for jig_name in jig_names:
                jig_ng_total[jig_name] = jig_ng_total.get(jig_name, 0) + 1
                if u_serial in ewma_report.unit_alerts:
                    jig_ng_detected[jig_name] = jig_ng_detected.get(jig_name, 0) + 1

    for jig_name, j_total_ng in jig_ng_total.items():
        if j_total_ng >= 10:
            j_detected = jig_ng_detected.get(jig_name, 0)
            j_recall = (j_detected / j_total_ng) * 100.0
            if j_recall < 60.0:
                auto_shadow_unmet_reasons.append(
                    f"Nhóm thiết bị kiểm tra (JIG {jig_name}) có {j_total_ng} lỗi NG nhưng tỷ lệ phát hiện chỉ đạt {j_recall:.1f}% (dưới ngưỡng rubric 60.0%)."
                )

    if not auto_shadow_unmet_reasons:
        che_do_khuyen_nghi = "AUTO_SHADOW"
        huong_dan_khuyen_nghi = (
            "Đạt đầy đủ 10 tiêu chuẩn rubric khởi động. Tự động kích hoạt chế độ chạy bóng đọc-only "
            "với ngưỡng tham số kiểm soát đã đóng băng."
        )
    else:
        che_do_khuyen_nghi = "LEARNING_SHADOW"
        unmet_text = "; ".join(auto_shadow_unmet_reasons)
        huong_dan_khuyen_nghi = (
            f"Đạt an toàn kỹ thuật nhưng chưa đủ điều kiện tự động kích hoạt ngưỡng sản xuất ({unmet_text}). "
            f"Hệ thống mở chế độ chạy bóng học hỏi đọc-only để tiếp tục thu thập dữ liệu nhãn thực tế."
        )

    report_data = {
        "tieu_de": "Báo cáo phát lại lịch sử đánh giá cảnh báo sớm LSU Iris",
        "phien_ban_rubric": protocol.rubric_version,
        "ma_kiem_tra_giao_thuc": protocol.compute_digest(),
        "ma_kiem_tra_du_lieu": snapshot.content_digest,
        "thoi_diem_tao": datetime.now(timezone.utc).isoformat(),
        "tong_so_unit": total_units,
        "so_unit_dat_ok": ok_count,
        "so_unit_loi_ng": ng_count,
        "so_unit_chua_xac_dinh": unknown_count,
        "so_sanh_phuong_an": methods_summary,
        "che_do_khuyen_nghi": che_do_khuyen_nghi,
        "huong_dan_khuyen_nghi": huong_dan_khuyen_nghi,
        "future_leakage_detected": ewma_report.future_leakage_detected,
        "ly_do_chua_dat_auto_shadow": auto_shadow_unmet_reasons,
    }

    digest_payload = {k: v for k, v in report_data.items() if k != "thoi_diem_tao"}
    raw_json = json.dumps(digest_payload, sort_keys=True, ensure_ascii=False)
    report_data["bao_cao_digest"] = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
    return report_data


def render_report_markdown(report: Dict[str, Any]) -> str:
    """Format replay comparison report into standard Vietnamese markdown for UI display."""
    md = []
    md.append(f"# {report['tieu_de']}")
    md.append(f"**Phiên bản thang chấm:** `{report['phien_ban_rubric']}`")
    md.append(f"**Dấu kiểm tra giao thức:** `{report['ma_kiem_tra_giao_thuc'][:16]}`")
    md.append(f"**Dấu kiểm tra dữ liệu:** `{report['ma_kiem_tra_du_lieu'][:16]}`")
    md.append(f"**Dấu kiểm tra báo cáo:** `{report['bao_cao_digest'][:16]}`")
    md.append("")
    md.append("## 1. Tổng quan tập dữ liệu đánh giá")
    md.append(f"- **Tổng số Unit đánh giá:** {report['tong_so_unit']}")
    md.append(f"- **Số Unit Đạt (OK):** {report['so_unit_dat_ok']}")
    md.append(f"- **Số Unit Lỗi (NG):** {report['so_unit_loi_ng']}")
    md.append(f"- **Số Unit Chưa xác định:** {report['so_unit_chua_xac_dinh']}")
    md.append("")
    md.append("## 2. Bảng so sánh các phương án cảnh báo")
    md.append("| Phương án | Trạng thái | Đúng (TP) | Cảnh báo nhầm (FP) | Bỏ sót (FN) | Tỷ lệ phát hiện NG |")
    md.append("|---|---|---:|---:|---:|---:|")
    for m in report["so_sanh_phuong_an"]:
        md.append(
            f"| {m['ten_phuong_an']} | {m['trang_thai']} | {m.get('dung_ng', 0)} | "
            f"{m.get('canh_bao_nham', 0)} | {m.get('bo_sot_ng', 0)} | {m.get('ty_le_phat_hien_ng', '-')} |"
        )
    md.append("")
    md.append("## 3. Kết luận và chế độ mở tự động")
    md.append(f"- **Chế độ khuyến nghị:** `{report['che_do_khuyen_nghi']}`")
    md.append(f"- **Hướng dẫn hành động:** {report['huong_dan_khuyen_nghi']}")
    md.append("")
    md.append("> *Lưu ý an toàn: Báo cáo chỉ phục vụ chế độ chạy bóng đọc-only. Không phát lệnh điều khiển máy hoặc dừng chuyền.*")
    return "\n".join(md)