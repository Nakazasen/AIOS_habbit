"""Line investigation assistant for factory cases (US4).

Constructs bounded investigation packs from line_events.sqlite:
- Timeline of suspected events (ordered chronologically)
- Grouped repeated patterns (recurring jam codes or station alarms)
- Missing clues checklist (missing serials, incomplete timestamps, multi-station drift)
- Strictly fail-closed: returns empty when no events match; never grabs 5 recent events.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence


@dataclass(frozen=True)
class LineInvestigationScope:
    station: Optional[str] = None
    code: Optional[str] = None
    serial: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    limit: int = 50

    def is_empty(self) -> bool:
        return not any(
            (
                (self.station or "").strip(),
                (self.code or "").strip(),
                (self.serial or "").strip(),
                (self.time_start or "").strip(),
                (self.time_end or "").strip(),
            )
        )


@dataclass(frozen=True)
class RepeatedPattern:
    pattern_type: str  # "ma_loi" (code) or "tram_may" (station)
    key: str
    count: int
    earliest: str
    latest: str
    description_vi: str


@dataclass(frozen=True)
class MissingClue:
    field_name: str
    description: str
    suggested_action: str


@dataclass(frozen=True)
class InvestigationTimelineEvent:
    event_id: str
    source_name: str
    dialect: str
    occurred_at: str
    station: str
    code: str
    serial: str
    duration_s: Optional[float]
    provenance: str = "suspected"


@dataclass(frozen=True)
class InvestigationPack:
    scope: LineInvestigationScope
    events: tuple[InvestigationTimelineEvent, ...]
    timeline: tuple[dict[str, Any], ...]
    repeated_patterns: tuple[RepeatedPattern, ...]
    missing_clues: tuple[MissingClue, ...]
    total_matched: int
    summary_vi: str


def build_investigation_pack(
    db_path: Path | str,
    scope: LineInvestigationScope,
) -> InvestigationPack:
    path = Path(db_path)
    empty_pack = InvestigationPack(
        scope=scope,
        events=(),
        timeline=(),
        repeated_patterns=(),
        missing_clues=(),
        total_matched=0,
        summary_vi="Không tìm thấy sự kiện phù hợp với tiêu chí điều tra.",
    )

    if not path.is_file() or scope.is_empty():
        return empty_pack

    clauses: list[str] = []
    params: list[Any] = []

    if scope.station and scope.station.strip():
        clauses.append("lower(station) LIKE ?")
        params.append(f"%{scope.station.strip().lower()}%")

    if scope.code and scope.code.strip():
        clauses.append("lower(code) LIKE ?")
        params.append(f"%{scope.code.strip().lower()}%")

    if scope.serial and scope.serial.strip():
        clauses.append("lower(serial) LIKE ?")
        params.append(f"%{scope.serial.strip().lower()}%")

    if scope.time_start and scope.time_start.strip():
        clauses.append("occurred_at >= ?")
        params.append(scope.time_start.strip())

    if scope.time_end and scope.time_end.strip():
        clauses.append("occurred_at <= ?")
        params.append(scope.time_end.strip())

    if not clauses:
        return empty_pack

    where_sql = " AND ".join(clauses)
    cap = max(1, min(scope.limit, 200))

    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        with conn:
            cursor = conn.execute(
                f"""
                SELECT event_id, source_name, dialect, occurred_at, station, code,
                       serial, duration_s, provenance
                FROM line_events
                WHERE {where_sql}
                ORDER BY occurred_at ASC, event_id ASC
                LIMIT ?
                """,
                (*params, cap),
            )
            rows = cursor.fetchall()
    except (sqlite3.Error, OSError):
        return empty_pack

    if not rows:
        return empty_pack

    events: list[InvestigationTimelineEvent] = []
    timeline: list[dict[str, Any]] = []
    missing_clues_list: list[MissingClue] = []

    has_missing_serial = False
    has_empty_time = False
    stations_seen: set[str] = set()
    code_counts: dict[str, list[str]] = {}

    for row in rows:
        ev_id = str(row["event_id"] or "")
        src = str(row["source_name"] or "")
        dia = str(row["dialect"] or "unknown")
        occ = str(row["occurred_at"] or "")
        sta = str(row["station"] or "")
        cod = str(row["code"] or "")
        ser = str(row["serial"] or "")
        dur = row["duration_s"]
        prov = str(row["provenance"] or "suspected")

        event = InvestigationTimelineEvent(
            event_id=ev_id,
            source_name=src,
            dialect=dia,
            occurred_at=occ,
            station=sta,
            code=cod,
            serial=ser,
            duration_s=dur,
            provenance=prov,
        )
        events.append(event)

        timeline.append(
            {
                "Mã sự kiện": ev_id,
                "Thời điểm": occ or "Chưa rõ",
                "Trạm / Máy": sta or "Chưa rõ",
                "Mã lỗi / Cảnh báo": cod or "Chưa rõ",
                "Số sê-ri / Unit": ser or "Không có",
                "Thời lượng (s)": f"{dur:.1f}" if dur is not None else "-",
                "Trạng thái": "Nghi ngờ" if prov == "suspected" else ("Đã duyệt" if prov == "approved" else prov),
            }
        )

        if not ser.strip():
            has_missing_serial = True
        if not occ.strip():
            has_empty_time = True
        if sta.strip():
            stations_seen.add(sta.strip())
        if cod.strip():
            code_counts.setdefault(cod.strip(), []).append(occ)

    if has_missing_serial:
        missing_clues_list.append(
            MissingClue(
                field_name="serial",
                description="Một số sự kiện thiếu thông tin số sê-ri linh kiện / Unit ID.",
                suggested_action="Đối chiếu thêm sổ theo dõi phôi hoặc nhật ký quét mã đầu trạm.",
            )
        )
    if has_empty_time:
        missing_clues_list.append(
            MissingClue(
                field_name="time",
                description="Một số sự kiện ghi nhận thiếu dấu thời gian đầy đủ.",
                suggested_action="Kiểm tra đồng bộ múi giờ NTP giữa PLC và máy tính thu thập log.",
            )
        )
    if len(stations_seen) > 1 and not (scope.station and scope.station.strip()):
        missing_clues_list.append(
            MissingClue(
                field_name="station",
                description=f"Sự kiện phân tán trên {len(stations_seen)} trạm máy khác nhau.",
                suggested_action="Thu hẹp phạm vi tìm kiếm theo từng trạm cụ thể để phân tích chuỗi lỗi dây chuyền.",
            )
        )

    repeated_patterns_list: list[RepeatedPattern] = []
    for cod, timestamps in code_counts.items():
        if len(timestamps) >= 2:
            sorted_times = sorted(t for t in timestamps if t)
            earliest = sorted_times[0] if sorted_times else ""
            latest = sorted_times[-1] if sorted_times else ""
            repeated_patterns_list.append(
                RepeatedPattern(
                    pattern_type="ma_loi",
                    key=cod,
                    count=len(timestamps),
                    earliest=earliest,
                    latest=latest,
                    description_vi=f"Mã lỗi {cod} lặp lại {len(timestamps)} lần (từ {earliest or '?'} đến {latest or '?'})",
                )
            )

    summary_vi = (
        f"Đã khớp {len(events)} sự kiện nghi ngờ từ kho log dây chuyền. "
        f"Phát hiện {len(repeated_patterns_list)} nhóm hiện tượng lặp và "
        f"{len(missing_clues_list)} dữ kiện cần làm rõ thêm."
    )

    return InvestigationPack(
        scope=scope,
        events=tuple(events),
        timeline=tuple(timeline),
        repeated_patterns=tuple(repeated_patterns_list),
        missing_clues=tuple(missing_clues_list),
        total_matched=len(events),
        summary_vi=summary_vi,
    )
