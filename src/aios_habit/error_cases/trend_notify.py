"""B4: periodic trend report + threshold alerts with chart by email.

Wires the error_cases trend engine (:mod:`trend_analysis`) to the JIG
notification machinery instead of reinventing it:

- chart: ``production_prediction.spc_chart.render_spc_png`` (Pillow,
  Monozukuri style, threshold drawn as the UCL line, breach points
  circled) — one chart per alerted group;
- mail: ``production_prediction.alert_mailer`` (Vietnamese mail with the
  chart inline and the markdown report attached);
- SMTP: ``production_prediction.smtp_config`` (config lives outside Git);
- anti-spam cooldown: ``alert_mailer.AlertCooldownTracker``;
- threshold storage: JSON under ``local_cases/`` (runtime, gitignored),
  the same file-based mechanism as the JIG threshold store in
  ``production_prediction.metric_limits``.

The mail path is a stub by default: :func:`run_scheduled_report` only
sends when the caller passes ``send_fn`` (production passes
``smtp_config.gui_voi_cau_hinh`` partially applied, or its own sender);
tests pass a capturing stub, so nothing is ever sent for real here.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

from aios_habit.error_cases.trend_analysis import (
    DIMENSION_LABELS_VI,
    Alert,
    Record,
    check_thresholds,
    detect_rising_trend,
    fetch_records,
    generate_report,
    incidence_table,
)
from aios_habit.production_prediction.alert_mailer import (
    AlertCooldownTracker,
    AlertMailProposal,
    build_alert_email,
)

#: Runtime threshold config (gitignored), same mechanism as the JIG store.
MAC_DINH_NGUONG_PATH = Path("local_cases") / "nguong_xu_huong_loi.json"

#: Default report directory (gitignored).
MAC_DINH_BAO_CAO_DIR = Path("local_cases") / "bao_cao_xu_huong"

#: Key inside a dimension mapping holding the fallback threshold.
DEFAULT_KEY = "__default__"

#: Send statuses of run_scheduled_report.
DA_GUI = "da_gui"
CHUA_GUI = "chua_gui"
KHONG_GUI = "khong_gui"

# JSON shape: {dimension: {group: threshold_0_to_1, "__default__": ...}}
ThresholdStore = Dict[str, Dict[str, float]]


def _la_so_hop_le(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 < number <= 1.0:
        return number
    return None


def load_thresholds(path: Union[str, Path] = MAC_DINH_NGUONG_PATH) -> ThresholdStore:
    """Read user-set thresholds. Missing/corrupt file -> empty store (fail-soft)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    store: ThresholdStore = {}
    for dimension, mapping in data.items():
        if not isinstance(mapping, dict):
            continue
        clean: Dict[str, float] = {}
        for group, value in mapping.items():
            number = _la_so_hop_le(value)
            if number is not None:
                clean[str(group)] = number
        if clean:
            store[str(dimension)] = clean
    return store


def save_thresholds(
    store: ThresholdStore, path: Union[str, Path] = MAC_DINH_NGUONG_PATH
) -> Path:
    """Persist user-set thresholds as UTF-8 JSON (runtime config, outside Git)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        str(dimension): {str(group): float(value) for group, value in mapping.items()}
        for dimension, mapping in (store or {}).items()
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def threshold_for(store: ThresholdStore, dimension: str, group: str) -> float:
    """Resolve the threshold for a group: group -> __default__ -> 1.0 (never fires)."""
    mapping = (store or {}).get(dimension) or {}
    value = mapping.get(group, mapping.get(DEFAULT_KEY, 1.0))
    number = _la_so_hop_le(value)
    return number if number is not None else 1.0


def _ten_file_an_toan(text: str, gioi_han: int = 40) -> str:
    clean = re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE).strip("_")
    return clean[:gioi_han] or "nhom"


def render_trend_chart(
    table: Mapping[str, Mapping[str, Mapping[str, float]]],
    dimension: str,
    group: str,
    path: Union[str, Path],
    *,
    threshold: Optional[float] = None,
) -> Path:
    """Draw the incidence-rate trend of one group as PNG.

    Reuses the JIG chart engine (``spc_chart.render_spc_png``): the rate
    series over time buckets, with the alert threshold drawn as the
    control line — points above it are circled by the engine itself.
    """
    from aios_habit.production_prediction.spc_chart import (
        SpcChartInput,
        render_spc_png,
    )

    buckets = sorted(table)
    if not buckets:
        raise ValueError("Không có dữ liệu để vẽ biểu đồ xu hướng.")
    values = [float(table[bucket].get(group, {}).get("rate", 0.0)) for bucket in buckets]
    label = DIMENSION_LABELS_VI.get(dimension, dimension)
    # Cảnh báo sớm (rising trend) không có ngưỡng số -> không vẽ đường ngưỡng.
    import math as _math

    gioi_han = None
    if isinstance(threshold, (int, float)) and not _math.isnan(threshold):
        gioi_han = float(threshold)
    chart = SpcChartInput(
        jig_id="Xu hướng lỗi",
        cong_doan=label,
        metric=f"{label}: {group}",
        values=values,
        nhan_thoi_gian=buckets,
        ucl=gioi_han,
    )
    return render_spc_png(chart, path)


@dataclass
class ScheduledReportResult:
    """Outcome of one periodic run (Vietnamese statuses, user-facing)."""

    report_markdown: str
    report_path: Optional[str]
    chart_paths: List[str] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    mail: Optional[MIMEMultipart] = None
    send_status: str = KHONG_GUI
    send_note: str = ""


def _html_bao_cao(
    alerts: Sequence[Alert], period_vi: str, chart_cid: bool
) -> str:
    if alerts:
        items = "".join(f"<li>{a.message}</li>" for a in alerts)
        tom_tat = (
            f"<p>Phát hiện <b>{len(alerts)}</b> cảnh báo trong kỳ {period_vi}:</p>"
            f"<ul>{items}</ul>"
        )
    else:
        tom_tat = f"<p>Không có cảnh báo nào trong kỳ {period_vi}.</p>"
    anh = '<img src="cid:bieudoxu_huong" alt="Biểu đồ xu hướng" />' if chart_cid else ""
    return (
        "<html><body>"
        "<h2>Báo cáo xu hướng lỗi định kỳ</h2>"
        f"{tom_tat}"
        "<p>Chi tiết đầy đủ trong file báo cáo đính kèm.</p>"
        f"{anh}"
        "</body></html>"
    )


def run_scheduled_report(
    source: Union[sqlite3.Connection, Sequence[Record]],
    *,
    dimensions: Sequence[str] = ("model", "line", "stage", "paper", "machine"),
    period: str = "week",
    thresholds: Optional[ThresholdStore] = None,
    recipients: Sequence[str] = (),
    send_fn: Optional[Callable[[MIMEMultipart], Any]] = None,
    report_dir: Optional[Union[str, Path]] = None,
    cooldown: Optional[AlertCooldownTracker] = None,
    max_charts: int = 8,
    generated_at: Optional[str] = None,
) -> ScheduledReportResult:
    """End-to-end periodic report: fetch -> incidence -> alerts -> charts -> mail.

    - Writes the markdown report to ``report_dir`` (always, even with no
      alerts and no recipients).
    - Draws one JIG-engine trend chart per alerted group (capped).
    - Composes the Vietnamese alert mail (chart inline + report attached)
      when ``recipients`` is set; sends ONLY through ``send_fn`` — with no
      ``send_fn`` the mail is built but never sent (stub path for tests).
    """
    store = thresholds if thresholds is not None else load_thresholds()
    records = fetch_records(source) if isinstance(source, sqlite3.Connection) else list(source)

    period_vi = {"day": "ngày", "week": "tuần", "month": "tháng"}.get(period, period)
    tables: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {}
    all_alerts: List[Alert] = []
    sections: List[str] = []
    for dimension in dimensions:
        table = incidence_table(records, dimension, period)
        tables[dimension] = table
        dim_thresholds = store.get(dimension) or {}
        alerts = check_thresholds(table, dimension, dim_thresholds)
        alerts += detect_rising_trend(table, dimension)
        all_alerts.extend(alerts)
        label = DIMENSION_LABELS_VI.get(dimension, dimension)
        sections.append(
            generate_report(
                table, dimension, period, alerts,
                title=f"# Báo cáo xu hướng lỗi (định kỳ) — {label}",
                generated_at=generated_at,
            )
        )
    report_markdown = "\n\n---\n\n".join(sections)

    out_dir = Path(report_dir) if report_dir else MAC_DINH_BAO_CAO_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = (generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")).replace(" ", "_").replace(":", "")
    report_path = out_dir / f"bao_cao_xu_huong_{stamp}.md"
    report_path.write_text(report_markdown, encoding="utf-8")

    chart_paths: List[str] = []
    for alert in all_alerts[:max(0, max_charts)]:
        chart_path = out_dir / (
            f"chart_{alert.dimension}_{_ten_file_an_toan(alert.group)}.png"
        )
        render_trend_chart(
            tables[alert.dimension], alert.dimension, alert.group,
            chart_path, threshold=alert.threshold,
        )
        chart_paths.append(str(chart_path))

    result = ScheduledReportResult(
        report_markdown=report_markdown,
        report_path=str(report_path),
        chart_paths=chart_paths,
        alerts=all_alerts,
    )

    nguoi_nhan = [str(e).strip() for e in recipients if str(e).strip()]
    if not nguoi_nhan:
        result.send_status = KHONG_GUI
        result.send_note = "Chưa cấu hình người nhận mail — chỉ sinh file báo cáo."
        return result

    chart_bytes: Optional[bytes] = None
    if chart_paths:
        chart_bytes = Path(chart_paths[0]).read_bytes()
    if all_alerts:
        tieu_de = (
            f"[Xu hướng lỗi] Báo cáo định kỳ theo {period_vi} — "
            f"{len(all_alerts)} cảnh báo"
        )
        tom_tat = "; ".join(a.message for a in all_alerts[:5])
    else:
        tieu_de = f"[Xu hướng lỗi] Báo cáo định kỳ theo {period_vi} — không có cảnh báo"
        tom_tat = "Không có cảnh báo nào trong kỳ báo cáo."
    proposal = AlertMailProposal(
        tieu_de=tieu_de,
        tom_tat=tom_tat,
        nguoi_nhan=nguoi_nhan,
        ten_anh="bieu_do_xu_huong.png",
    )
    mail = build_alert_email(
        proposal,
        noi_dung_html=_html_bao_cao(all_alerts, period_vi, chart_bytes is not None),
        anh_png_bytes=chart_bytes,
        bao_cao_markdown=report_markdown,
    )
    result.mail = mail

    if send_fn is None:
        result.send_status = CHUA_GUI
        result.send_note = (
            "Thư đã soạn xong (stub) nhưng chưa gửi — chưa cấu hình hàm gửi mail."
        )
        return result

    khoa_chong_spam = f"xu_huong_loi:{period}"
    if cooldown is not None and not cooldown.duoc_phep_gui(khoa_chong_spam):
        result.send_status = KHONG_GUI
        result.send_note = "Đang trong thời gian chờ chống spam — giữ lại thư này."
        return result
    try:
        send_fn(mail)
    except Exception as exc:  # fail-closed, ghi rõ lý do
        result.send_status = CHUA_GUI
        result.send_note = f"Chưa gửi được mail: {exc}"
        return result
    if cooldown is not None:
        cooldown.danh_dau_da_gui(khoa_chong_spam)
    result.send_status = DA_GUI
    result.send_note = f"Đã gửi báo cáo tới {', '.join(nguoi_nhan)}."
    return result
