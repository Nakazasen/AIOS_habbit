"""Parse factory line logs into a structured SQLite cabinet, never into RAG."""

from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
from aios_habit.workspace_chat_store import (
    COLLECTION_RUNTIME_DIRNAME,
    LOCAL_CHAT_DIR,
    load_collection,
)

LINE_EVENTS_BASENAME = "line_events.sqlite"
MAX_LINE_LOG_ROWS = 20_000
PROVENANCE_SUSPECTED = "suspected"

_TIME_ALIASES = frozenset({
    "time", "timestamp", "datetime", "date", "occurred", "occurred_at",
    "thoi_gian", "thoigian", "time_stamp",
})
_STATION_ALIASES = frozenset({
    "station", "line", "machine", "eqp", "equipment", "tram", "vi_tri",
})
_CODE_ALIASES = frozenset({
    "jam", "jam_code", "jamcode", "alarm", "alarm_code", "error", "error_code",
    "ma_loi", "code", "c_call", "ccall", "c-call", "call_code",
})
_SERIAL_ALIASES = frozenset({"serial", "sn", "lot", "barcode", "unit"})
_DURATION_ALIASES = frozenset({
    "duration", "duration_s", "time_ms", "cycle", "hold_time",
})
_JAM_HINTS = frozenset({"jam", "jam_code", "jamcode"})
_CCALL_HINTS = frozenset({"c_call", "ccall", "c-call", "call_code"})


@dataclass(frozen=True)
class LineLogEvent:
    event_id: str
    source_name: str
    dialect: str
    occurred_at: str
    station: str
    code: str
    serial: str
    duration_s: float | None
    provenance: str = PROVENANCE_SUSPECTED


@dataclass(frozen=True)
class LineLogParseResult:
    ok: bool
    dialect: str
    events: tuple[LineLogEvent, ...]
    truncated: bool = False
    owner_message: str = ""
    error_code: str = ""


@dataclass(frozen=True)
class LineLogIngestSummary:
    ok: bool
    dialect: str
    inserted: int
    truncated: bool
    db_path: str
    owner_message: str
    top_codes: tuple[tuple[str, int], ...] = ()


def _norm_header(name: str) -> str:
    raw = str(name or "").strip().lower().replace(" ", "_").replace("-", "_")
    return raw


def detect_line_log_dialect(headers: Sequence[str]) -> str:
    names = {_norm_header(item) for item in headers}
    if names & _JAM_HINTS:
        return "jam"
    if names & _CCALL_HINTS:
        return "c_call"
    return "unknown"


def _mapped_columns(headers: Sequence[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, header in enumerate(headers):
        name = _norm_header(header)
        if name in _TIME_ALIASES and "occurred_at" not in mapping:
            mapping["occurred_at"] = index
        elif name in _STATION_ALIASES and "station" not in mapping:
            mapping["station"] = index
        elif name in _CODE_ALIASES and "code" not in mapping:
            mapping["code"] = index
        elif name in _SERIAL_ALIASES and "serial" not in mapping:
            mapping["serial"] = index
        elif name in _DURATION_ALIASES and "duration_s" not in mapping:
            mapping["duration_s"] = index
    return mapping


def _cell(row: Sequence[Any], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return str(row[index] or "").strip()


def _duration(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _event_id(source_name: str, row_no: int, occurred_at: str, station: str, code: str, serial: str) -> str:
    raw = f"{source_name}|{row_no}|{occurred_at}|{station}|{code}|{serial}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def parse_line_log_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    source_name: str,
) -> LineLogParseResult:
    mapping = _mapped_columns(headers)
    if "code" not in mapping and "occurred_at" not in mapping:
        return LineLogParseResult(
            ok=False,
            dialect="unknown",
            events=(),
            error_code="line_log_schema_unknown",
            owner_message="Không nhận ra cột thời gian hoặc mã lỗi. File CSV này chưa phải log Jam/C-call.",
        )
    dialect = detect_line_log_dialect(headers)
    events: list[LineLogEvent] = []
    truncated = False
    for row_no, row in enumerate(rows, start=2):
        if len(events) >= MAX_LINE_LOG_ROWS:
            truncated = True
            break
        occurred_at = _cell(row, mapping.get("occurred_at"))
        station = _cell(row, mapping.get("station"))
        code = _cell(row, mapping.get("code"))
        serial = _cell(row, mapping.get("serial"))
        if not occurred_at and not code:
            continue
        events.append(
            LineLogEvent(
                event_id=_event_id(source_name, row_no, occurred_at, station, code, serial),
                source_name=source_name,
                dialect=dialect,
                occurred_at=occurred_at,
                station=station,
                code=code,
                serial=serial,
                duration_s=_duration(_cell(row, mapping.get("duration_s"))),
            )
        )
    if not events:
        return LineLogParseResult(
            ok=False,
            dialect=dialect,
            events=(),
            error_code="line_log_empty",
            owner_message="Không đọc được dòng log nào.",
        )
    return LineLogParseResult(
        ok=True,
        dialect=dialect,
        events=tuple(events),
        truncated=truncated,
        owner_message=(
            f"Đã đọc {len(events)} dòng log ({dialect}), trạng thái nghi ngờ — chưa phải chẩn đoán."
            + (" File dài nên chỉ lấy phần đầu." if truncated else "")
        ),
    )


def parse_line_log_bytes(file_bytes: bytes, filename: str) -> LineLogParseResult:
    name = Path(filename or "log.csv").name
    suffix = Path(name).suffix.lower()
    if suffix != ".csv":
        return LineLogParseResult(
            ok=False,
            dialect="unknown",
            events=(),
            error_code="line_log_not_csv",
            owner_message="Pilot parser log chỉ nhận CSV. Excel SOP vẫn vào thư viện chữ.",
        )
    try:
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        headers = next(reader)
    except Exception:
        return LineLogParseResult(
            ok=False,
            dialect="unknown",
            events=(),
            error_code="line_log_unreadable",
            owner_message="Không đọc được file log.",
        )
    return parse_line_log_table(headers, reader, source_name=name)


def line_events_db_path(collection_id: str | None = None) -> Path:
    wanted = str(collection_id or DEFAULT_COLLECTION_ID).strip() or DEFAULT_COLLECTION_ID
    collection = load_collection(wanted)
    storage = str(getattr(collection, "storage_root", "") or "").strip() if collection else ""
    if storage:
        root = Path(storage) / COLLECTION_RUNTIME_DIRNAME
    else:
        root = LOCAL_CHAT_DIR / "collections" / wanted
    root.mkdir(parents=True, exist_ok=True)
    return root / LINE_EVENTS_BASENAME


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS line_events (
            event_id TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            dialect TEXT NOT NULL,
            occurred_at TEXT NOT NULL DEFAULT '',
            station TEXT NOT NULL DEFAULT '',
            code TEXT NOT NULL DEFAULT '',
            serial TEXT NOT NULL DEFAULT '',
            duration_s REAL,
            provenance TEXT NOT NULL DEFAULT 'suspected',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_line_events_code ON line_events(code)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_line_events_station ON line_events(station)"
    )


def ingest_line_log_bytes(
    file_bytes: bytes,
    filename: str,
    *,
    collection_id: str | None = None,
) -> LineLogIngestSummary:
    parsed = parse_line_log_bytes(file_bytes, filename)
    if not parsed.ok:
        return LineLogIngestSummary(
            ok=False,
            dialect=parsed.dialect,
            inserted=0,
            truncated=False,
            db_path="",
            owner_message=parsed.owner_message,
        )
    db_path = line_events_db_path(collection_id)
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_schema(conn)
        inserted = 0
        for event in parsed.events:
            conn.execute(
                """
                INSERT OR IGNORE INTO line_events (
                    event_id, source_name, dialect, occurred_at, station, code,
                    serial, duration_s, provenance, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.source_name,
                    event.dialect,
                    event.occurred_at,
                    event.station,
                    event.code,
                    event.serial,
                    event.duration_s,
                    event.provenance,
                    now,
                ),
            )
            inserted += conn.execute("SELECT changes()").fetchone()[0]
        conn.commit()
        top = conn.execute(
            """
            SELECT code, COUNT(*) AS n FROM line_events
            WHERE code != ''
            GROUP BY code ORDER BY n DESC, code ASC LIMIT 5
            """
        ).fetchall()
    finally:
        conn.close()
    return LineLogIngestSummary(
        ok=True,
        dialect=parsed.dialect,
        inserted=inserted,
        truncated=parsed.truncated,
        db_path=str(db_path),
        owner_message=parsed.owner_message + f" Đã ghi {inserted} sự kiện vào kho log (không embed).",
        top_codes=tuple((str(code), int(count)) for code, count in top),
    )


def ingest_line_log_files(
    paths: Sequence[str | Path],
    *,
    collection_id: str | None = None,
) -> LineLogIngestSummary:
    total = 0
    dialect = "unknown"
    truncated = False
    last_ok: LineLogIngestSummary | None = None
    messages: list[str] = []
    for path in paths:
        file_path = Path(path)
        try:
            payload = file_path.read_bytes()
        except OSError:
            messages.append(f"Không đọc được {file_path.name}.")
            continue
        summary = ingest_line_log_bytes(
            payload, file_path.name, collection_id=collection_id
        )
        if summary.ok:
            total += summary.inserted
            dialect = summary.dialect
            truncated = truncated or summary.truncated
            last_ok = summary
        else:
            messages.append(summary.owner_message)
    if last_ok is None:
        return LineLogIngestSummary(
            ok=False,
            dialect=dialect,
            inserted=0,
            truncated=False,
            db_path="",
            owner_message=messages[0] if messages else "Không nạp được log.",
        )
    extra = (" " + " ".join(messages)) if messages else ""
    return LineLogIngestSummary(
        ok=True,
        dialect=dialect,
        inserted=total,
        truncated=truncated,
        db_path=last_ok.db_path,
        owner_message=f"Đã ghi {total} sự kiện log ({dialect}), nghi ngờ — chưa chẩn đoán.{extra}",
        top_codes=last_ok.top_codes,
    )


def summarize_line_events(
    collection_id: str | None = None,
    *,
    limit: int = 5,
) -> Mapping[str, Any]:
    db_path = line_events_db_path(collection_id)
    if not db_path.is_file():
        return {"count": 0, "top_codes": (), "dialects": ()}
    conn = sqlite3.connect(str(db_path))
    try:
        count = int(conn.execute("SELECT COUNT(*) FROM line_events").fetchone()[0])
        top = conn.execute(
            """
            SELECT code, COUNT(*) AS n FROM line_events
            WHERE code != ''
            GROUP BY code ORDER BY n DESC, code ASC LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
        dialects = conn.execute(
            "SELECT dialect, COUNT(*) FROM line_events GROUP BY dialect"
        ).fetchall()
    finally:
        conn.close()
    return {
        "count": count,
        "top_codes": tuple((str(code), int(n)) for code, n in top),
        "dialects": tuple((str(name), int(n)) for name, n in dialects),
    }
