"""Background HTTP listener for realtime JIG streaming (US12 T063, J1-RT).

Silent by design: normal rows are stored quietly in SQLite; only drift or
threshold events are surfaced to the AI consumer through the events endpoint
(see J1-RT API spec). Standard library only: http.server, sqlite3, json,
threading, urllib.
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
from urllib.parse import parse_qs, urlsplit

STREAM_PATH = "/api/v1/jig/stream-log"
EVENTS_PATH = "/api/v1/jig/events"

# Nhan danh nguon ban tin: du lieu that tu jig hoac phat lai mo phong.
NGUON_THAT = "that"
NGUON_PHAT_LAI_MO_PHONG = "SIMULATED_REALTIME"

# Gioi han kich co lo tren mot request de server khong bi tran bo nho.
GIOI_HAN_BAN_TIN_MOI_LO = 100


@dataclass
class StreamRecord:
    timestamp: Optional[str]
    unit_serial: str
    jig_id: str
    metric: str
    value: Optional[float]
    unit: str = ""
    status: str = "unknown"
    nguon: str = NGUON_THAT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "unit_serial": self.unit_serial,
            "jig_id": self.jig_id,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "nguon": self.nguon,
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
    nguon = str(payload.get("nguon", NGUON_THAT)).strip() or NGUON_THAT
    if nguon not in (NGUON_THAT, NGUON_PHAT_LAI_MO_PHONG):
        raise ValueError("Nguồn bản tin không hợp lệ (chỉ nhận 'that' hoặc 'SIMULATED_REALTIME').")
    return StreamRecord(
        timestamp=timestamp,
        unit_serial=unit_serial,
        jig_id=jig_id,
        metric=metric,
        value=value,
        unit=str(payload.get("unit", "")).strip(),
        status=str(payload.get("status", "unknown")).strip() or "unknown",
        nguon=nguon,
    )


class StreamBuffer:
    """SQLite buffer plus in-memory EWMA state per (jig_id, metric)."""

    def __init__(self, db_path: str | Path, alpha: float = 0.2) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.alpha = alpha
        self._histories: Dict[Tuple[str, str], List[float]] = {}
        # RLock vi append() co the goi ghi_su_kien() khi dang giu lock.
        self._lock = threading.RLock()
        # Tap (jig_id, metric) dang trong dot vi pham: chi phat 1 su kien khi
        # BAT DAU dot vi pham, khong spam moi diem trong dot.
        self._dang_canh_bao: set = set()
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
                    status TEXT,
                    nguon TEXT NOT NULL DEFAULT 'that'
                )
                """
            )
            # Migration nhe cho DB cu (truoc J1-RT): them cot nguon neu thieu.
            cac_cot = {row[1] for row in conn.execute("PRAGMA table_info(jig_stream_logs)")}
            if "nguon" not in cac_cot:
                conn.execute("ALTER TABLE jig_stream_logs ADD COLUMN nguon TEXT NOT NULL DEFAULT 'that'")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jig_stream_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thoi_gian TEXT NOT NULL,
                    loai TEXT NOT NULL,
                    jig_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    noi_dung TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.commit()

    def append(self, record: StreamRecord) -> Dict[str, Any]:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO jig_stream_logs (timestamp, unit_serial, jig_id, metric, value, unit, status, nguon)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (record.timestamp, record.unit_serial, record.jig_id, record.metric,
                     record.value, record.unit, record.status, record.nguon),
                )
                conn.commit()
            key = (record.jig_id, record.metric)
            history = self._histories.setdefault(key, [])
            if record.value is not None:
                history.append(record.value)
                if len(history) > 200:
                    del history[:-200]
            ket_qua = {"trang_thai": "Đã ghi nhận", "so_diem_nen": len(history)}
            # Tu sinh su kien canh bao drift de AI consumer nhan qua events endpoint.
            # Dung phat_hien_drift (nen cu vs cua so moi); ewma_status cu giu lai
            # cho tuong thich nguoc nhung khong du nhay de bat dich chuyen that.
            kiem_drift = phat_hien_drift(self.recent_values(record.jig_id, record.metric, 50))
            if kiem_drift["canh_bao"]:
                ket_qua["canh_bao"] = True
                if key not in self._dang_canh_bao:
                    self._dang_canh_bao.add(key)
                    cursor = self.ghi_su_kien(
                        "canh_bao_drift",
                        record.jig_id,
                        record.metric,
                        {
                            "unit_serial": record.unit_serial,
                            "gia_tri": record.value,
                            "don_vi": record.unit,
                            "nguon": record.nguon,
                            "z": round(kiem_drift["z"], 2),
                            "trung_binh_nen": round(kiem_drift["trung_binh_nen"], 4),
                            "trung_binh_moi": round(kiem_drift["trung_binh_moi"], 4),
                            "chi_tiet": "Thông số trôi khỏi nền (z=%.2f) — có thể dẫn đến phát sinh NG." % kiem_drift["z"],
                        },
                    )
                    ket_qua["cursor_su_kien"] = cursor
            else:
                self._dang_canh_bao.discard(key)
            return ket_qua

    def ghi_su_kien(self, loai: str, jig_id: str, metric: str, noi_dung: Dict[str, Any]) -> int:
        """Ghi mot su kien len bang events, tra ve cursor (id tu tang)."""
        thoi_gian = datetime.now().replace(microsecond=0).isoformat()
        with self._lock:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO jig_stream_events (thoi_gian, loai, jig_id, metric, noi_dung)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (thoi_gian, loai, jig_id, metric, json.dumps(noi_dung, ensure_ascii=False)),
                )
                conn.commit()
                return int(cur.lastrowid)

    def doc_su_kien(self, tu_cursor: int = 0, gioi_han: int = 200) -> List[Dict[str, Any]]:
        """Doc cac su kien moi hon cursor, theo dung thu tu cursor tang dan."""
        gioi_han = max(1, min(int(gioi_han), 500))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, thoi_gian, loai, jig_id, metric, noi_dung FROM jig_stream_events"
                " WHERE id > ? ORDER BY id ASC LIMIT ?",
                (int(tu_cursor), gioi_han),
            ).fetchall()
        ket_qua = []
        for row in rows:
            try:
                noi_dung = json.loads(row[5]) if row[5] else {}
            except (ValueError, TypeError):
                noi_dung = {}
            ket_qua.append({
                "cursor": int(row[0]),
                "thoi_gian": row[1],
                "loai": row[2],
                "jig_id": row[3],
                "metric": row[4],
                "noi_dung": noi_dung,
            })
        return ket_qua

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
    # Token xac thuc Bearer cho moi jig. None = khong yeu cau auth (tuong thich
    # nguoc voi ban cu); dat token de bat buoc moi request phai co header
    # "Authorization: Bearer <token>".
    auth_token: Optional[str] = None
    _server: Optional[ThreadingHTTPServer] = field(default=None, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)

    def _kiem_tra_auth(self, handler: BaseHTTPRequestHandler) -> bool:
        if not self.auth_token:
            return True
        nhan = handler.headers.get("Authorization", "")
        return nhan.strip() == "Bearer " + self.auth_token

    def start(self) -> Dict[str, Any]:
        if self.buffer is None:
            raise ValueError("Thiếu kho đệm SQLite cho luồng JIG.")
        buffer = self.buffer
        listener = self

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

            def _tu_choi_neu_thieu_auth(self) -> bool:
                if not listener._kiem_tra_auth(self):
                    self._send_json(401, {"trang_thai": "Thiếu hoặc sai mã truy cập."})
                    return True
                return False

            def do_GET(self) -> None:
                duong_dan = urlsplit(self.path).path
                if duong_dan != EVENTS_PATH:
                    self._send_json(404, {"trang_thai": "Không tìm thấy địa chỉ lấy sự kiện."})
                    return
                if self._tu_choi_neu_thieu_auth():
                    return
                tham_so = parse_qs(urlsplit(self.path).query)
                try:
                    tu_cursor = int((tham_so.get("since") or ["0"])[0])
                except (ValueError, TypeError):
                    tu_cursor = 0
                try:
                    gioi_han = int((tham_so.get("limit") or ["200"])[0])
                except (ValueError, TypeError):
                    gioi_han = 200
                cac_su_kien = buffer.doc_su_kien(tu_cursor, gioi_han)
                cursor_moi = cac_su_kien[-1]["cursor"] if cac_su_kien else tu_cursor
                self._send_json(200, {
                    "trang_thai": "Đã ghi nhận",
                    "su_kien": cac_su_kien,
                    "cursor_moi": cursor_moi,
                })

            def do_POST(self) -> None:
                if self.path != STREAM_PATH:
                    self._send_json(404, {"trang_thai": "Không tìm thấy địa chỉ nhận log."})
                    return
                if self._tu_choi_neu_thieu_auth():
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
                    for item in records[:GIOI_HAN_BAN_TIN_MOI_LO]:
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


def phat_hien_drift(
    cac_gia_tri: List[float],
    diem_nen: int = 40,
    diem_moi: int = 10,
    nguong_sigma: float = 3.0,
) -> Dict[str, Any]:
    """Phat hien dich chuyen muc do cua thong so theo thoi gian.

    So sanh trung binh ``diem_moi`` diem gan nhat voi nen ``diem_nen`` diem
    ngay truoc do; canh bao khi lech >= ``nguong_sigma`` lan do lech chuan
    cua nen. Khac voi ``ewma_status`` (so EWMA voi trung binh CUNG cua so —
    tu triet tieu khi dich chuyen chiem phan lon cua so), ham nay giu nen
    cu lam chuan nen dich chuyen ben vung van bi bat. Dung cho duong
    realtime tu dong sinh su kien canh bao trong ``StreamBuffer.append``.
    """
    tong = diem_nen + diem_moi
    if len(cac_gia_tri) < tong:
        return {"trang_thai": "Chưa đủ dữ liệu", "canh_bao": False, "z": 0.0}
    nen = cac_gia_tri[-tong:-diem_moi]
    moi = cac_gia_tri[-diem_moi:]
    trung_binh_nen = sum(nen) / len(nen)
    phuong_sai = sum((v - trung_binh_nen) ** 2 for v in nen) / len(nen)
    do_lech_nen = phuong_sai ** 0.5
    trung_binh_moi = sum(moi) / len(moi)
    if do_lech_nen == 0:
        z = abs(trung_binh_moi - trung_binh_nen)
        canh_bao = z > 0
    else:
        z = abs(trung_binh_moi - trung_binh_nen) / do_lech_nen
        canh_bao = z >= nguong_sigma
    return {
        "trang_thai": "Vi phạm" if canh_bao else "Đạt",
        "canh_bao": canh_bao,
        "z": z,
        "trung_binh_nen": trung_binh_nen,
        "trung_binh_moi": trung_binh_moi,
    }


def decide_stream_event(ewma_result: Dict[str, Any]) -> str:
    """Silent streaming rule: only drift/threshold events surface on chat."""
    return "alert" if bool(ewma_result.get("canh_bao")) else "silent"
