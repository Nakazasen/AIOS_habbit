"""JIG log ingestion via Omnibar for US12 (Moc 6).

Distinguishes normal chat, agent commands, and raw JIG log lines pasted
directly into the single Omnibar input. No extra text area or buttons.
Uses only the Python standard library and reuses Data Gate limits.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from aios_habit.production_prediction.lsu_iris import RECOGNIZED_UNITS

# Command keywords that must route to Agent Work, never to JIG ingest.
_AGENT_COMMAND_KEYWORDS = (
    "tao bao cao",
    "tạo báo cáo",
    "ra soat",
    "rà soát",
    "thiet ke",
    "thiết kế",
    "sua ma",
    "sửa mã",
    "giao viec",
    "giao việc",
    "luu vao ho so",
    "lưu vào hồ sơ",
)

# Config command keywords handled by alert_config_chat, not JIG ingest.
_CONFIG_COMMAND_KEYWORDS = (
    "them email",
    "thêm email",
    "xoa email",
    "xóa email",
    "doi nguong",
    "đổi ngưỡng",
    "gian cach",
    "giãn cách",
    "gop tin",
    "gộp tin",
    "truc ban",
    "trực ban",
    "che do ca nhan",
    "chế độ cá nhân",
)

_JIG_HINT = re.compile(r"(jig|unit|serial|lot|bowskew|beam|metric|value|timestamp)", re.IGNORECASE)


@dataclass
class JigLogLine:
    timestamp: Optional[str]
    unit_serial: str
    jig_id: str
    metric: str
    value: Optional[float]
    unit: str
    status: str
    raw: str

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


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _looks_like_command(text: str) -> bool:
    norm = _normalize(text)
    return any(k in norm for k in _AGENT_COMMAND_KEYWORDS + _CONFIG_COMMAND_KEYWORDS)


def _split_fields(line: str) -> List[str]:
    for delimiter in (",", "\t", ";", "|"):
        if delimiter in line:
            try:
                reader = csv.reader(io.StringIO(line), delimiter=delimiter)
                fields = next(reader, [])
                fields = [f.strip() for f in fields]
                if len(fields) >= 4:
                    return fields
            except csv.Error:
                continue
    return []


def _to_float(token: str) -> Optional[float]:
    try:
        return float(token.replace(",", "."))
    except (ValueError, TypeError, AttributeError):
        return None


def is_jig_log_line(text: str) -> bool:
    """Return True when a single line looks like a raw JIG log row."""
    if not text or not isinstance(text, str):
        return False
    line = text.strip()
    if not line or "\n" in line.strip("\n") and len(line.splitlines()) > 5:
        # Multi-line pastes are handled line-by-line by the caller.
        pass
    if _looks_like_command(line):
        return False
    if len(line) > 2000:
        return False
    fields = _split_fields(line)
    if len(fields) < 4:
        return False
    numeric_count = sum(1 for f in fields if _to_float(f) is not None)
    if numeric_count == 0:
        return False
    if _JIG_HINT.search(line):
        return True
    # Fallback: structured row with a numeric value and a unit-like token.
    lowered = [f.lower() for f in fields]
    if any(u in lowered for u in RECOGNIZED_UNITS) and numeric_count >= 1:
        return True
    # At least 5 columns with one float is enough for a machine row.
    return len(fields) >= 5 and numeric_count >= 1


def parse_jig_log_line(line: str) -> Optional[JigLogLine]:
    """Parse one raw JIG log line into a structured record."""
    if not is_jig_log_line(line):
        return None
    fields = _split_fields(line.strip())
    if len(fields) < 4:
        return None
    # Heuristic mapping for the common JIG export order:
    # timestamp, unit_serial, jig_id, metric, value, unit, status
    timestamp: Optional[str] = None
    first = fields[0]
    try:
        datetime.fromisoformat(first.replace("Z", "+00:00"))
        timestamp = first
        rest = fields[1:]
    except ValueError:
        rest = fields
    # Pad to 6 slots for uniform handling.
    padded = (rest + ["", "", "", "", "", ""])[:6]
    unit_serial, jig_id, metric = padded[0].strip(), padded[1].strip(), padded[2].strip()
    value_token = padded[3].strip()
    unit = padded[4].strip().lower()
    status = padded[5].strip() or "unknown"
    value = _to_float(value_token)
    if not unit_serial or not metric:
        return None
    if unit and unit not in RECOGNIZED_UNITS:
        # Keep unknown units but mark them; Data Gate will isolate them later.
        pass
    return JigLogLine(
        timestamp=timestamp,
        unit_serial=unit_serial,
        jig_id=jig_id or "unknown",
        metric=metric,
        value=value,
        unit=unit,
        status=status,
        raw=line.strip(),
    )


def route_omnibar_message(text: str) -> str:
    """Route an Omnibar message to rag, agent work, or JIG log ingest."""
    if not text or not text.strip():
        return "rag"
    if is_jig_log_line(text.strip().splitlines()[0]):
        return "jig_log"
    if _looks_like_command(text):
        # Config/persona commands are handled by their own chat modules,
        # but they must never fall into RAG as a plain question.
        return "agent"
    return "rag"


def evaluate_single_log_ewma(
    value: Optional[float],
    history: List[float],
    alpha: float = 0.2,
    limit_std: float = 3.0,
) -> Dict[str, Any]:
    """Compare one measurement against history with a light EWMA check."""
    clean = [v for v in history if isinstance(v, (int, float))]
    if value is None:
        return {
            "trang_thai": "Thiếu dữ liệu",
            "chi_tiet": "Dòng log không có giá trị số để đối chiếu.",
            "canh_bao": False,
        }
    if len(clean) < 5:
        return {
            "trang_thai": "Cận biên",
            "chi_tiet": "Chưa đủ điểm nền để kết luận xu hướng, cần thêm dữ liệu cùng JIG.",
            "canh_bao": False,
            "gia_tri": value,
        }
    mean = sum(clean) / len(clean)
    variance = sum((v - mean) ** 2 for v in clean) / len(clean)
    std = variance ** 0.5 if variance > 0 else 0.0
    ewma = clean[0]
    for v in clean[1:]:
        ewma = alpha * v + (1 - alpha) * ewma
    ewma_now = alpha * value + (1 - alpha) * ewma
    deviation = abs(ewma_now - mean)
    threshold = limit_std * std if std > 0 else 0.0
    if std == 0:
        if value == mean:
            return {
                "trang_thai": "Đạt",
                "chi_tiet": "Giá trị trùng với nền ổn định của JIG.",
                "canh_bao": False,
                "gia_tri": value,
            }
        return {
            "trang_thai": "Vi phạm",
            "chi_tiet": "Nền đang phẳng nhưng giá trị mới lệch khỏi nền, cần kiểm tra.",
            "canh_bao": True,
            "gia_tri": value,
        }
    if deviation >= threshold:
        return {
            "trang_thai": "Vi phạm",
            "chi_tiet": f"Xu hướng EWMA lệch {deviation:.3f} vượt ngưỡng {threshold:.3f}, cần kiểm tra.",
            "canh_bao": True,
            "gia_tri": value,
        }
    if deviation >= threshold * 0.7:
        return {
            "trang_thai": "Cận biên",
            "chi_tiet": f"Xu hướng đang trôi gần ngưỡng ({deviation:.3f}/{threshold:.3f}), nên theo dõi thêm.",
            "canh_bao": False,
            "gia_tri": value,
        }
    return {
        "trang_thai": "Đạt",
        "chi_tiet": "Giá trị nằm trong dải kiểm soát của JIG.",
        "canh_bao": False,
        "gia_tri": value,
    }
