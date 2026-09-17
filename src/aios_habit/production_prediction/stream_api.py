"""Background HTTP listener for realtime JIG streaming (US12 T063).

Silent by design: normal rows are stored quietly in SQLite; only drift or
threshold events are surfaced by the chat layer (see T064 helpers below).
Standard library only: http.server, sqlite3, json, threading.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

STREAM_PATH = "/api/v1/jig/stream-log"


@dataclass
class StreamRecord:
    timestamp: Optional[str]
    unit_serial: str
    jig_id: str
    metric: str
    value: Optional[float]
    unit: str = ""
    status: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "unit_serial": self.unit_serial,
            "jig_id": self.jig_id,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
        }


def parse_stream_record(payload: Dict[str, Any]) -> StreamRecord:
    """Validate one streaming JSON object with Vietnamese errors."""
    if not isinstance(payload, dict):
        raise ValueError("Dữ liệu gửi lên phải là một bản ghi JSON.")
    unit_serial = str(payload.get("unit_serial", "")).strip()
    jig_id = str(payload.get("jig_id", "")).strip() or "unknown"
    metric = str(payload.get("metric", "")).strip()
    if not unit_serial or not metric:
        raise ValueError("Thiếu mã Unit hoặc tên thông số trong dòng log.")
    raw_value = payload.get("value")
    value: Optional[float] = None
    if raw_value is not None and raw_value != "":
        try:
            value = float(str(raw_value).replace(",", "."))
        except (ValueError, TypeError):
            raise ValueError("Giá trị đo phải là số.") from None
    timestamp = payload.get("timestamp")
    if timestamp is not None:
        timestamp = str(timestamp).strip() or None
        if timestamp:
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Thời gian gửi lên chưa đúng định dạng.") from None
    return StreamRecord(
        timestamp=timestamp,
        unit_serial=unit_serial,
        jig_id=jig_id,
        metric=metric,
        value=value,
        unit=str(payload.get("unit", "")).strip(),
        status=str(payload.get("status", "unknown")).strip() or "unknown",
    )


class StreamBuffer:
    """SQLite buffer plus in-memory EWMA state per (jig_id, metric)."""

    def __init__(self, db_path: str | Path, alpha: float = 0.2) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.alpha = alpha
        self._histories: Dict[Tuple[str, str], List[float]] = {}
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jig_stream_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    unit_serial TEXT NOT NULL,
                    jig_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL,
                    unit TEXT,
                    status TEXT
                )
                """
            )
            conn.commit()

    def append(self, record: StreamRecord) -> Dict[str, Any]:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO jig_stream_logs (timestamp, unit_serial, jig_id, metric, value, unit, status)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (record.timestamp, record.unit_serial, record.jig_id, record.metric,
                     record.value, record.unit, record.status),
                )
                conn.commit()
            key = (record.jig_id, record.metric)
            history = self._histories.setdefault(key, [])
            if record.value is not None:
                history.append(record.value)
                if len(history) > 200:
                    del history[:-200]
            return {"trang_thai": "Đã ghi nhận", "so_diem_nen": len(history)}

    def recent_values(self, jig_id: str, metric: str, limit: int = 50) -> List[float]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT value FROM jig_stream_logs WHERE jig_id = ? AND metric = ? AND value IS NOT NULL"
                " ORDER BY id DESC LIMIT ?",
                (jig_id, metric, limit),
            ).fetchall()
        return [float(r[0]) for r in rows if r[0] is not None][::-1]

    def ewma_status(self, jig_id: str, metric: str, limit_std: float = 3.0) -> Dict[str, Any]:
        values = self.recent_values(jig_id, metric, 50)
        if len(values) < 5:
            return {"trang_thai": "Chưa đủ dữ liệu", "canh_bao": False}
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5 if variance > 0 else 0.0
        ewma = values[0]
        for v in values[1:]:
            ewma = self.alpha * v + (1 - self.alpha) * ewma
        if std == 0:
            return {"trang_thai": "Đạt", "canh_bao": False}
        if abs(ewma - mean) >= limit_std * std:
            return {"trang_thai": "Vi phạm", "canh_bao": True}
        return {"trang_thai": "Đạt", "canh_bao": False}


@dataclass
class StreamListener:
    host: str = "127.0.0.1"
    port: int = 8765
    buffer: Optional[StreamBuffer] = None
    _server: Optional[ThreadingHTTPServer] = field(default=None, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)

    def start(self) -> Dict[str, Any]:
        if self.buffer is None:
            raise ValueError("Thiếu kho đệm SQLite cho luồng JIG.")
        buffer = self.buffer

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # Silence default logging.
                return

            def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                if self.path != STREAM_PATH:
                    self._send_json(404, {"trang_thai": "Không tìm thấy địa chỉ nhận log."})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                except ValueError:
                    length = 0
                if length <= 0 or length > 1_000_000:
                    self._send_json(400, {"trang_thai": "Nội dung gửi lên trống hoặc quá lớn."})
                    return
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                records: List[Dict[str, Any]] = []
                content_type = self.headers.get("Content-Type", "")
                try:
                    if "ndjson" in content_type or "\n" in raw.strip():
                        for line in raw.splitlines():
                            if line.strip():
                                item = json.loads(line)
                                if isinstance(item, dict):
                                    records.append(item)
                    else:
                        item = json.loads(raw)
                        if isinstance(item, dict):
                            records = [item]
                        elif isinstance(item, list):
                            records = [r for r in item if isinstance(r, dict)]
                except json.JSONDecodeError:
                    self._send_json(400, {"trang_thai": "Nội dung gửi lên không phải JSON hợp lệ."})
                    return
                if not records:
                    self._send_json(400, {"trang_thai": "Không có dòng log hợp lệ để ghi nhận."})
                    return
                try:
                    for item in records[:100]:
                        buffer.append(parse_stream_record(item))
                except ValueError as exc:
                    self._send_json(400, {"trang_thai": str(exc)})
                    return
                self._send_json(200, {"trang_thai": "Đã ghi nhận", "so_dong": len(records)})

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return {"trang_thai": "Đang lắng nghe", "dia_chi": f"{self.host}:{self.port}{STREAM_PATH}"}

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        self._server = None
        self._thread = None


def decide_stream_event(ewma_result: Dict[str, Any]) -> str:
    """Silent streaming rule: only drift/threshold events surface on chat."""
    return "alert" if bool(ewma_result.get("canh_bao")) else "silent"
