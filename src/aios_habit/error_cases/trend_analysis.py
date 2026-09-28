"""Buoc 4: trend analysis & early warning for error cases.

Groups imported error cases along business dimensions (model / line /
stage / paper / machine), computes the incidence rate per time bucket,
raises automatic alerts when a rate crosses its threshold, and renders
periodic markdown reports.

Input is a list of plain record dicts; see ``fetch_records`` for the
SQLite adapter over the ``error_cases`` table. The incidence table
returned by ``incidence_table`` is bucket x group data ready for
charting (no image rendering here).

Only the standard library is used, and the module performs no relative
imports, so it stays importable without optional dependencies.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

# Business dimensions an error case can be sliced by.
DIMENSIONS = ("model", "line", "stage", "paper", "machine")

# Vietnamese labels for user-facing alerts and reports.
DIMENSION_LABELS_VI = {
    "model": "Model",
    "line": "Line",
    "stage": "Công đoạn",
    "paper": "Loại giấy",
    "machine": "Máy",
}

# Supported time-bucket granularities.
PERIODS = ("day", "week", "month")

# A record is a plain dict. Required keys: "occurred_at" (datetime or
# ISO-8601 string). Dimension keys are looked up in DIMENSIONS; missing
# dimensions fall back to the placeholder below.
Record = Dict[str, Any]
MISSING_GROUP = "(không rõ)"


def _parse_dt(value: Any) -> datetime:
    """Parse an occurred_at value into a datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"occurred_at must be datetime or ISO string, got {type(value)!r}")


def bucket_key(dt: datetime, period: str) -> str:
    """Map a datetime to its time-bucket label.

    day   -> "2026-09-28"
    week  -> "2026-W39" (ISO calendar)
    month -> "2026-09"
    """
    if period == "day":
        return dt.strftime("%Y-%m-%d")
    if period == "week":
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"
    if period == "month":
        return dt.strftime("%Y-%m")
    raise ValueError(f"period must be one of {PERIODS}, got {period!r}")


def fetch_records(
    conn: sqlite3.Connection,
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> List[Record]:
    """Read error_cases rows into trend records.

    Maps schema columns to dimensions (machine_type -> model,
    line -> line); extra dimensions (stage/paper/machine) are picked up
    from raw_json when the importer stored them there. ``since``/``until``
    are ISO date strings filtering on created_at.
    """
    query = (
        "SELECT machine_type, line, error_code_c, error_code_h,"
        " investigation, created_at, raw_json FROM error_cases"
    )
    clauses: List[str] = []
    params: List[Any] = []
    if since is not None:
        clauses.append("created_at >= ?")
        params.append(since)
    if until is not None:
        clauses.append("created_at < ?")
        params.append(until)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at"

    import json as _json

    records: List[Record] = []
    for row in conn.execute(query, params):
        raw: Dict[str, Any] = {}
        try:
            raw = _json.loads(row[6] or "{}")
        except ValueError:
            raw = {}
        error_code = row[2] or row[3] or ""
        records.append(
            {
                "model": row[0] or MISSING_GROUP,
                "line": row[1] or MISSING_GROUP,
                "stage": raw.get("stage") or raw.get("cong_doan") or MISSING_GROUP,
                "paper": raw.get("paper") or raw.get("loai_giay") or MISSING_GROUP,
                "machine": raw.get("machine") or raw.get("may") or MISSING_GROUP,
                "error_code": error_code,
                "occurred_at": row[5],
            }
        )
    return records


def group_by_dimension(records: Sequence[Record], dimension: str) -> Dict[str, List[Record]]:
    """Group records by one dimension value."""
    if dimension not in DIMENSIONS:
        raise ValueError(f"dimension must be one of {DIMENSIONS}, got {dimension!r}")
    groups: Dict[str, List[Record]] = defaultdict(list)
    for rec in records:
        groups[str(rec.get(dimension) or MISSING_GROUP)].append(rec)
    return dict(groups)


def bucketize(records: Sequence[Record], period: str = "week") -> Dict[str, List[Record]]:
    """Split records into time buckets, keys sorted chronologically."""
    buckets: Dict[str, List[Record]] = defaultdict(list)
    for rec in records:
        buckets[bucket_key(_parse_dt(rec["occurred_at"]), period)].append(rec)
    return dict(sorted(buckets.items()))


def incidence_table(
    records: Sequence[Record],
    dimension: str,
    period: str = "week",
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Build the bucket x group incidence table (chart-ready data).

    Returns ``{bucket: {group: {"count": n, "rate": r}}}`` where rate is
    the group's share of all cases in that bucket (0..1). Buckets with
    no cases are omitted.
    """
    table: Dict[str, Dict[str, Dict[str, float]]] = {}
    for bucket, recs in bucketize(records, period).items():
        total = len(recs)
        if total == 0:
            continue
        cell: Dict[str, Dict[str, float]] = {}
        for group, grec in group_by_dimension(recs, dimension).items():
            cell[group] = {"count": float(len(grec)), "rate": len(grec) / total}
        table[bucket] = cell
    return table


@dataclass
class Alert:
    """One threshold breach. ``message`` is Vietnamese (user-facing)."""

    dimension: str
    group: str
    bucket: str
    rate: float
    threshold: float
    message: str = field(default="")


def check_thresholds(
    table: Mapping[str, Mapping[str, Mapping[str, float]]],
    dimension: str,
    thresholds: Union[float, Mapping[str, float]],
) -> List[Alert]:
    """Raise an alert for every (bucket, group) whose rate exceeds its threshold.

    ``thresholds`` is either a single float applied to all groups or a
    mapping of group -> threshold. Groups without an explicit threshold
    fall back to ``thresholds.get("__default__", 1.0)`` (never fires).
    """
    alerts: List[Alert] = []
    label = DIMENSION_LABELS_VI.get(dimension, dimension)
    for bucket in sorted(table):
        for group in sorted(table[bucket]):
            rate = float(table[bucket][group]["rate"])
            if isinstance(thresholds, Mapping):
                threshold = float(thresholds.get(group, thresholds.get("__default__", 1.0)))
            else:
                threshold = float(thresholds)
            if rate > threshold:
                alerts.append(
                    Alert(
                        dimension=dimension,
                        group=group,
                        bucket=bucket,
                        rate=rate,
                        threshold=threshold,
                        message=(
                            f"Cảnh báo: [{label}={group}] tỉ lệ phát sinh "
                            f"{rate:.1%} vượt ngưỡng {threshold:.1%} trong kỳ {bucket}."
                        ),
                    )
                )
    return alerts


def detect_rising_trend(
    table: Mapping[str, Mapping[str, Mapping[str, float]]],
    dimension: str,
    *,
    min_buckets: int = 3,
) -> List[Alert]:
    """Early warning: rate strictly increasing over the last ``min_buckets`` buckets.

    Complements fixed thresholds — catches a group that is climbing fast
    but has not crossed its threshold yet.
    """
    alerts: List[Alert] = []
    label = DIMENSION_LABELS_VI.get(dimension, dimension)
    buckets = sorted(table)
    if len(buckets) < min_buckets:
        return alerts
    recent = buckets[-min_buckets:]
    groups = {g for b in recent for g in table[b]}
    for group in sorted(groups):
        rates = [float(table[b].get(group, {}).get("rate", 0.0)) for b in recent]
        if all(b > a for a, b in zip(rates, rates[1:])) and rates[-1] > 0:
            alerts.append(
                Alert(
                    dimension=dimension,
                    group=group,
                    bucket=recent[-1],
                    rate=rates[-1],
                    threshold=float("nan"),
                    message=(
                        f"Cảnh báo sớm: [{label}={group}] tỉ lệ phát sinh tăng "
                        f"liên tục {min_buckets} kỳ gần nhất "
                        f"({', '.join(f'{r:.1%}' for r in rates)})."
                    ),
                )
            )
    return alerts


def generate_report(
    table: Mapping[str, Mapping[str, Mapping[str, float]]],
    dimension: str,
    period: str,
    alerts: Sequence[Alert],
    *,
    title: Optional[str] = None,
    generated_at: Optional[str] = None,
) -> str:
    """Render a periodic report as Vietnamese markdown text."""
    label = DIMENSION_LABELS_VI.get(dimension, dimension)
    period_vi = {"day": "ngày", "week": "tuần", "month": "tháng"}.get(period, period)
    lines = [
        title or "# Báo cáo xu hướng lỗi (định kỳ)",
        "",
        f"- Chiều phân tích: {label}",
        f"- Chu kỳ: theo {period_vi}",
        f"- Thời điểm tạo: {generated_at or datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Bảng tỉ lệ phát sinh",
        "",
        "| Kỳ | Nhóm | Số lỗi | Tỉ lệ |",
        "| --- | --- | ---: | ---: |",
    ]
    if not table:
        lines.append("| (không có dữ liệu) | — | 0 | — |")
    for bucket in sorted(table):
        for group in sorted(table[bucket]):
            cell = table[bucket][group]
            lines.append(
                f"| {bucket} | {group} | {int(cell['count'])} | {cell['rate']:.1%} |"
            )
    lines += ["", "## Cảnh báo", ""]
    if not alerts:
        lines.append("Không có cảnh báo nào trong kỳ báo cáo.")
    else:
        for alert in alerts:
            lines.append(f"- {alert.message}")
    lines.append("")
    return "\n".join(lines)


def run_periodic_report(
    source: Union[sqlite3.Connection, Sequence[Record]],
    *,
    dimensions: Sequence[str] = ("model", "line", "stage"),
    period: str = "week",
    thresholds: Union[float, Mapping[str, float]] = 0.2,
    title: Optional[str] = None,
) -> str:
    """End-to-end periodic report: fetch -> incidence -> alerts -> markdown.

    ``source`` is either a sqlite3 connection (error_cases schema) or a
    ready-made list of record dicts. One section per dimension.
    """
    records = fetch_records(source) if isinstance(source, sqlite3.Connection) else list(source)
    sections: List[str] = []
    for dimension in dimensions:
        table = incidence_table(records, dimension, period)
        alerts = check_thresholds(table, dimension, thresholds)
        alerts += detect_rising_trend(table, dimension)
        sections.append(
            generate_report(
                table, dimension, period, alerts,
                title=(title or "# Báo cáo xu hướng lỗi (định kỳ)") + f" — {DIMENSION_LABELS_VI.get(dimension, dimension)}",
            )
        )
    return "\n\n---\n\n".join(sections)
