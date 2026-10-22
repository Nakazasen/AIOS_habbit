"""Builtin chat action: tra cứu lỗi tương tự (B1-FEAT).

Wires the Buoc 0-5 error-case store into the Workspace Chat through the
`chat_action` framework (TOOL-2):

- The user types an error code (C0030, F000, C7620, ...) or describes the
  symptom in words. The action searches the local ``error_cases`` SQLite
  DB (built by the Buoc 0-5 pipeline from the real KDTPS history) and
  renders the top 3-5 similar cases as cards inside the answer bubble:
  hien tuong, nguyen nhan, doi sach, plus the original-report provenance
  (file › sheet › row › ma phieu) so every suggestion traces back to a
  real report. No follow-up questions: an error code alone is enough.
- Error codes also resolve through the error-code glossary (C_CALL, F_SYSTEM,
  SCT_ADJ, JAM): the header shows the dictionary meaning when known.
- Read-only: the DB is opened in read-only mode, nothing is written and
  no files are created. Fail-closed: any problem (missing DB, empty DB,
  no match, any exception) returns None so the chat keeps its normal RAG
  answer flow instead of leaking a raw traceback.
- Ticket DESKTOP-HOME-MACHINE-SERIAL-DATE-FILTER (2026-10-22):
  Entity recognition and structured filtering on machine name (phủ toàn bộ machine_type
  trong DB: Iris, 6thNext, Virgo, Libra 2, Sirius 2...), serial (raw_json['G']),
  and occurred date range (occurred_at). Summary line on each card:
  "May: <machine_type> | Serial: <serial> | Ngay phat sinh: <occurred_at>".
  Continuous improvement logging to local_cases/machine_serial_date_filter_events.jsonl.

DB location (first hit wins): the request context key ``error_cases_db``,
the ``AIOS_ERROR_CASES_DB`` env var, then the well-known deploy path
``C:/tmp/kdtps_standard/error_cases_reconciled.db`` (hoặc DB cũ ``error_cases_dict.db``) on the home machine.
"""

from __future__ import annotations

import calendar
import datetime
import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)

ACTION_NAME = "tra_cuu_loi_tuong_tu"
TITLE = "Tra cứu lỗi tương tự"

_HINTS = (
    "tra cuu loi",
    "loi tuong tu",
    "tim loi",
    "tim kiem loi",
    "ma loi",
    "error code",
    "lich su loi",
    "loi nay",
    "gap loi",
    "bao loi",
    "hien tuong",
    "trieu chung",
    "ket giay",
    "jam",
    "c call",
    "f call",
)

# Error codes match standard patterns: "C0030", "F000", "C 7620", "JAM4212", "J-411".
_CODE_RE = re.compile(r"\b(JAM|[CFJScfjs])\s*-?\s*(\d{3,4})\b", re.IGNORECASE)

# Serial patterns (e.g. WD72Z12772, 3V2XM1930, WD85X36474, C9P1056J6209)
_SERIAL_PREFIX_RE = re.compile(
    r"(?:serial|so\s*serial|số\s*serial|so\s*may|số\s*máy|seri|kiban|機番|s/n|sn)[\s:=]*([A-Za-z0-9_-]{5,25})",
    re.IGNORECASE,
)
_SERIAL_STANDALONE_RE = re.compile(
    r"\b(?!(?:JAM|[CFJS])\d{3,4}\b)([A-Z0-9]{2,5}[0-9][A-Z0-9]{4,12})\b",
    re.IGNORECASE,
)

# Date patterns (year, month/year, range, exact date)
_YEAR_RE = re.compile(r"(?:năm|nam|in\s+)?\b(201\d|202\d)\b", re.IGNORECASE)
_MONTH_YEAR_RE = re.compile(r"(?:tháng|thang)\s*(\d{1,2})[\s/-]+(?:năm|nam\s*)?(\d{4})", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(
    r"(?:từ|tu)\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*(?:đến|den|tới|toi|-)\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    re.IGNORECASE,
)
_DATE_RANGE_DMY_RE = re.compile(
    r"(?:từ|tu)\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s*(?:đến|den|tới|toi|-)\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
    re.IGNORECASE,
)
_MONTH_RANGE_NORM_RE = re.compile(
    r"(?:tu\s+)?thang\s*(\d{1,2})\s*(?:den|toi|-)\s*(?:thang\s*)?(\d{1,2})[\s/-]+(?:nam\s*)?(\d{4})",
    re.IGNORECASE,
)
_MONTH_RANGE_TWO_YEARS_NORM_RE = re.compile(
    r"(?:tu\s+)?thang\s*(\d{1,2})[\s/-]+(?:nam\s*)?(\d{4})\s*(?:den|toi|-)\s*(?:thang\s*)?(\d{1,2})[\s/-]+(?:nam\s*)?(\d{4})",
    re.IGNORECASE,
)
_QUARTER_NORM_RE = re.compile(
    r"(?:quy|q)\s*([1-4])[\s/-]+(?:nam\s*)?(\d{4})",
    re.IGNORECASE,
)
_EXACT_DATE_RE = re.compile(r"(?:ngày|ngay)?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)

# Code letter/prefix -> (glossary family, history H-category).
_CODE_FAMILY: Dict[str, Tuple[str, str]] = {
    "C": ("C_CALL", "C CALL"),
    "F": ("F_SYSTEM", "F CALL"),
    "J": ("JAM", "JAM"),
    "JAM": ("JAM", "JAM"),
}
_GLOSSARY_FAMILIES = ("C_CALL", "F_SYSTEM", "SCT_ADJ", "JAM")

_TOP_N = 5
_MAX_CANDIDATES = 800
_CLIP = 280

_STOPWORDS = frozenset(
    """
    la gi cai gi nhu the nao tai sao khi nao o dau bao nhieu
    cho toi xem giup voi a à ạ á ớ ờ cái này đó kia và hoặc với của cua
    trong trên dưới từ tu đến den tới toi bị bi được duoc có co không khong gì mà thì là các cac những nhung
    một hai ba bốn máy may lỗi error loi ma code tra cuu tim kiem tuong tu
    ca vụ vu phiếu phieu dòng dong họ ho model serial seri số so
    năm nam tháng thang ngày ngay phát phat sinh thuộc thuoc danh sách sach liệt liet kê ke
    to tờ bi bị giup giúp hoi hỏi cho ra vao vào len lên xuong xuống lai lại roi rồi ve về hay hoac hoặc
    nhu như thay thấy tim tìm kiem kiếm dung dùng chua chưa va và voi với
    """.split()
)

_OFFTOPIC_HINTS = (
    "visa",
    "thuy si",
    "du lich",
    "mon an",
    "nau an",
    "thoi tiet",
    "bong da",
    "ho chieu",
    "passport",
    "khach san",
    "ve may bay",
)

# Well-known deploy locations (home machine first).
# MERGED-DB-SWITCH-HOME (2026-10-18): Uu tien DB gop chuan 30.075 ca, giu DB cu lam fallback duong lui.
_DEFAULT_DB_CANDIDATES = (
    Path("C:/tmp/kdtps_standard/error_cases_reconciled.db"),
    Path("C:/tmp/kdtps_standard/error_cases_dict.db"),
    Path("C:/tmp/buoc0-deploy/error_cases_deploy.db"),
    Path.home() / "tmp" / "buoc0-deploy" / "error_cases_deploy.db",
)

# Canonical factory models mapping (norm_key -> (display_name, sql_like_pattern, use_replace_space))
_CANONICAL_MACHINES: List[Tuple[str, str, str, bool]] = [
    ("iris2024", "Iris2024", "%Iris2024%", False),
    ("iris2020", "Iris2020", "%Iris2020%", False),
    ("iris", "Iris", "%Iris%", False),
    ("6thnext", "6thNext", "%6thNext%", True),
    ("6tha3s", "6th A3S", "%6thA3S%", True),
    ("6tha3", "6th A3", "%6thA3%", True),
    ("6tha4", "6th A4", "%6thA4%", True),
    ("6th", "6th", "%6th%", False),
    ("polarisnext", "Polaris Next", "%PolarisNext%", True),
    ("polaris", "Polaris", "%Polaris%", False),
    ("virgo", "Virgo", "%Virgo%", True),
    ("libra2", "Libra 2", "%Libra2%", True),
    ("libra1", "Libra 1", "%Libra1%", True),
    ("libra", "Libra", "%Libra%", False),
    ("sirius2", "Sirius 2", "%Sirius2%", True),
    ("sirius", "Sirius", "%Sirius%", False),
    ("mebius", "Mebius", "%Mebius%", False),
    ("brazil2", "Brazil 2", "%Brazil2%", True),
    ("brazil", "Brazil", "%Brazil%", False),
    ("kairos", "Kairos", "%Kairos%", False),
    ("pictor", "Pictor", "%Pictor%", False),
]

_DB_MACHINE_CACHE: Dict[str, Tuple[str, str, bool]] = {}


# ---------------------------------------------------------------------------
# DB access (read-only)
# ---------------------------------------------------------------------------


def resolve_db_path(request: Optional[ChatActionRequest] = None) -> Optional[Path]:
    """Locate the error_cases DB without creating anything. None = absent."""
    if request:
        ctx: Mapping[str, Any] = request.context or {}
        for key in ("error_cases_db", "error_cases_db_path"):
            raw = ctx.get(key)
            if raw:
                p = Path(str(raw))
                if p.is_file():
                    return p
    env = os.environ.get("AIOS_ERROR_CASES_DB")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    for cand in _DEFAULT_DB_CANDIDATES:
        if cand.is_file():
            return cand
    return None


def _open_ro(path: Path) -> sqlite3.Connection:
    # as_uri() -> file:///C:/... on Windows; hand-built "file:C:/...?mode=ro"
    # fails there (colon after the drive letter).
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _raw_json(row: sqlite3.Row) -> Dict[str, Any]:
    try:
        data = json.loads(row["raw_json"] or "{}")
    except (ValueError, TypeError):
        data = {}
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Entity recognition (Machine, Serial, Date, Phenomenon)
# ---------------------------------------------------------------------------
# Bilingual technical phenomenon concepts (Vietnamese <-> Japanese <-> English)
_PHENOMENON_CONCEPTS: List[Dict[str, Any]] = [
    {
        "id": "POSTCARD",
        "name": "tờ postcard / はがき",
        "triggers": ["postcard", "post card", "hagaki", "はがき", "ハガキ", "葉書"],
        "db_patterns": ["%postcard%", "%post card%", "%hagaki%", "%はがき%", "%ハガキ%", "%葉書%"],
    },
    {
        "id": "SKEW_MARGIN",
        "name": "lệch lề / skew / マージンズレ",
        "triggers": ["lech le", "lệch lề", "lech", "lệch", "skew", "nghieng", "nghiêng", "マージンズレ", "スキュー", "斜め給紙", "ズレ"],
        "db_patterns": ["%lệch lề%", "%lech le%", "%lệch%", "%lech%", "%skew%", "%スキュー%", "%マージンズレ%", "%ズレ%", "%斜め給紙%", "%cấp giấy nghiêng%", "%cap giay nghieng%"],
    },
    {
        "id": "WHITE_SCREEN",
        "name": "màn hình trắng / 真っ白",
        "triggers": ["man hinh trang", "màn hình trắng", "treo màn hình trắng", "trang man hinh", "trắng màn hình", "mat man hinh", "mất màn hình"],
        "db_patterns": ["%màn hình trắng%", "%man hinh trang%", "%treo màn hình trắng%", "%真っ白%", "%白画面%"],
    },
    {
        "id": "ABNORMAL_SOUND",
        "name": "âm thanh lạ / tiếng kêu bất thường / 異常音",
        "triggers": ["am thanh la", "âm thanh lạ", "tieng keu", "tiếng kêu", "am thanh bat thuong", "âm thanh bất thường", "keu bat thuong", "kêu bất thường", "di am", "dị âm", "異常音", "異音"],
        "db_patterns": ["%âm thanh lạ%", "%am thanh la%", "%tiếng kêu%", "%tieng keu%", "%âm thanh bất thường%", "%am thanh bat thuong%", "%異常音%", "%異音%"],
    },
    {
        "id": "COLOR_SHIFT",
        "name": "lệch màu / 色ズレ",
        "triggers": ["lech mau", "lệch màu", "sai mau", "sai màu"],
        "db_patterns": ["%lệch màu%", "%lech mau%", "%色ズレ%", "%色ずれ%", "%color shift%"],
    },
    {
        "id": "BLACK_LINE",
        "name": "vệt đen / sọc đen / 黒筋",
        "triggers": ["vet den", "vệt đen", "soc den", "sọc đen", "duong den", "đường đen"],
        "db_patterns": ["%vệt đen%", "%vet den%", "%sọc đen%", "%soc den%", "%黒筋%", "%黒スジ%", "%黒横筋%"],
    },
    {
        "id": "PAPER_JAM",
        "name": "kẹt giấy / JAM / 紙詰まり",
        "triggers": ["ket giay", "kẹt giấy", "dat giay", "dắt giấy"],
        "db_patterns": ["%kẹt giấy%", "%ket giay%", "%jam%", "%紙詰まり%", "%給紙せず%"],
    },
]


def extract_phenomenon_concepts(question: str) -> List[Dict[str, Any]]:
    """Extract recognized phenomenon concepts matching technical expressions in DB."""
    norm = _khong_dau(question)
    q_lower = question.lower()
    matched = []
    for concept in _PHENOMENON_CONCEPTS:
        for trig in concept["triggers"]:
            trig_norm = _khong_dau(trig)
            if trig in q_lower or trig_norm in norm:
                matched.append(concept)
                break
    return matched



def _khong_dau(text: str) -> str:
    """Lowercase + strip Vietnamese diacritics for keyword matching."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_key(s: str) -> str:
    """Normalize text into alphanumeric key without spaces or diacritics."""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("đ", "d")
    return re.sub(r"[^a-z0-9]", "", s)


def get_machine_registry(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Tuple[str, str, bool]]:
    """Return machine registry mapping norm_key -> (display_name, sql_like_pattern, use_replace_space).

    Populated with canonical factory models, and dynamically discovers any distinct machine_type
    present in the database (ticket 2.1(a)).
    """
    global _DB_MACHINE_CACHE
    if _DB_MACHINE_CACHE:
        return _DB_MACHINE_CACHE

    reg: Dict[str, Tuple[str, str, bool]] = {}
    for nk, name, pat, replace_space in _CANONICAL_MACHINES:
        reg[nk] = (name, pat, replace_space)

    if conn is not None:
        try:
            rows = conn.execute(
                "SELECT DISTINCT machine_type FROM error_cases WHERE machine_type IS NOT NULL AND TRIM(machine_type) != ''"
            ).fetchall()
            for (m_raw,) in rows:
                m = str(m_raw or "").strip()
                for line in m.split("\n"):
                    clean = re.sub(r"[\r\t\ufffd]", "", line).strip()
                    if len(clean) >= 2 and not clean.isdigit():
                        nk = _normalize_key(clean)
                        if nk and nk not in reg:
                            reg[nk] = (clean, f"%{clean}%", False)
        except Exception:
            pass

    _DB_MACHINE_CACHE = reg
    return reg


def extract_machine_entities(conn: Optional[sqlite3.Connection], question: str) -> Optional[Dict[str, Any]]:
    """Extract machine/model entity from question against distinct machine types in DB."""
    reg = get_machine_registry(conn)
    norm = _khong_dau(question)
    norm_no_space = _normalize_key(question)

    # 1. Match explicit prefix: "máy ...", "dòng máy ...", "họ máy ...", "model ..."
    m_exp = re.search(
        r"(?:dòng\s*máy|dong\s*may|họ\s*máy|ho\s*may|máy|may|model)\s*[:\s]+([A-Za-z0-9_-]+(?:\s+[A-Za-z0-9_-]+)?)",
        question,
        re.IGNORECASE,
    )
    if m_exp:
        raw_val = m_exp.group(1).strip()
        nk = _normalize_key(raw_val)
        if nk in reg:
            name, pat, rep_sp = reg[nk]
            return {
                "name": name,
                "pattern": pat,
                "replace_space": rep_sp,
                "label": f"dòng máy **{name}**" + (" (họ máy Iris)" if nk == "iris" else ""),
            }

    # 2. Match standalone tokens by length descending (e.g. "iris2024" before "iris", "sirius2" before "sirius")
    sorted_keys = sorted(reg.keys(), key=lambda x: len(x), reverse=True)
    for k in sorted_keys:
        if len(k) < 3 and k != "6th":
            continue
        word_boundary = r"(?:^|\W)" + re.escape(k) + r"(?:$|\W)"
        if re.search(word_boundary, norm) or (k in norm_no_space and (len(k) >= 4 or k == "6th")):
            name, pat, rep_sp = reg[k]
            return {
                "name": name,
                "pattern": pat,
                "replace_space": rep_sp,
                "label": f"dòng máy **{name}**" + (" (họ máy Iris)" if k == "iris" else ""),
            }
    return None


def extract_serial_entities(question: str) -> Optional[str]:
    """Extract machine serial pattern (WD72Z12772, 3V2XM1930) from question."""
    m1 = _SERIAL_PREFIX_RE.search(question)
    if m1:
        val = m1.group(1).strip().upper()
        if not _CODE_RE.fullmatch(val):
            return val
    m2 = _SERIAL_STANDALONE_RE.search(question)
    if m2:
        val = m2.group(1).strip().upper()
        if not _CODE_RE.fullmatch(val) and not val.isdigit():
            return val
    return None


def extract_date_entities(question: str) -> Optional[Dict[str, Any]]:
    """Extract date range, month range, quarter, month/year, or year from question."""
    norm = _khong_dau(question)

    # 1. Month range: "từ tháng 8 đến tháng 10 năm 2023", "tu thang 8 den 10 nam 2023", etc.
    m_mr = _MONTH_RANGE_NORM_RE.search(norm)
    if m_mr:
        m1 = int(m_mr.group(1))
        m2 = int(m_mr.group(2))
        yr = int(m_mr.group(3))
        if 1 <= m1 <= 12 and 1 <= m2 <= 12 and m1 <= m2:
            last_day = calendar.monthrange(yr, m2)[1]
            d1 = f"{yr:04d}-{m1:02d}-01"
            d2 = f"{yr:04d}-{m2:02d}-{last_day:02d}"
            return {
                "type": "range",
                "clause": "ec.occurred_at >= ? AND ec.occurred_at <= ?",
                "params": [d1, d2],
                "label": f"từ tháng {m1} đến tháng {m2} năm {yr} ({d1}..{d2})",
            }

    m_mr2 = _MONTH_RANGE_TWO_YEARS_NORM_RE.search(norm)
    if m_mr2:
        m1 = int(m_mr2.group(1))
        yr1 = int(m_mr2.group(2))
        m2 = int(m_mr2.group(3))
        yr2 = int(m_mr2.group(4))
        if 1 <= m1 <= 12 and 1 <= m2 <= 12:
            last_day = calendar.monthrange(yr2, m2)[1]
            d1 = f"{yr1:04d}-{m1:02d}-01"
            d2 = f"{yr2:04d}-{m2:02d}-{last_day:02d}"
            return {
                "type": "range",
                "clause": "ec.occurred_at >= ? AND ec.occurred_at <= ?",
                "params": [d1, d2],
                "label": f"từ tháng {m1}/{yr1} đến tháng {m2}/{yr2} ({d1}..{d2})",
            }

    # 2. Quarter: "quý 3 năm 2023", "quy 4 nam 2023", "Q1 2024"
    m_q = _QUARTER_NORM_RE.search(norm)
    if m_q:
        q = int(m_q.group(1))
        yr = int(m_q.group(2))
        q_map = {
            1: (1, 3, 31),
            2: (4, 6, 30),
            3: (7, 9, 30),
            4: (10, 12, 31),
        }
        start_m, end_m, end_d = q_map[q]
        d1 = f"{yr:04d}-{start_m:02d}-01"
        d2 = f"{yr:04d}-{end_m:02d}-{end_d:02d}"
        return {
            "type": "range",
            "clause": "ec.occurred_at >= ? AND ec.occurred_at <= ?",
            "params": [d1, d2],
            "label": f"Quý {q} năm {yr} ({d1}..{d2})",
        }

    # 3. Exact full date range (YYYY-MM-DD or DD/MM/YYYY)
    m_range = _DATE_RANGE_RE.search(question)
    if m_range:
        d1, d2 = m_range.group(1), m_range.group(2)
        return {
            "type": "range",
            "clause": "ec.occurred_at >= ? AND ec.occurred_at <= ?",
            "params": [d1, d2],
            "label": f"từ {d1} đến {d2}",
        }
    m_range_dmy = _DATE_RANGE_DMY_RE.search(question)
    if m_range_dmy:
        d1_raw, d2_raw = m_range_dmy.group(1), m_range_dmy.group(2)
        p1 = [int(x) for x in re.split(r"[-/]", d1_raw)]
        p2 = [int(x) for x in re.split(r"[-/]", d2_raw)]
        d1 = f"{p1[2]:04d}-{p1[1]:02d}-{p1[0]:02d}"
        d2 = f"{p2[2]:04d}-{p2[1]:02d}-{p2[0]:02d}"
        return {
            "type": "range",
            "clause": "ec.occurred_at >= ? AND ec.occurred_at <= ?",
            "params": [d1, d2],
            "label": f"từ {d1} đến {d2}",
        }

    # 4. Exact single date
    m_exact = _EXACT_DATE_RE.search(question)
    if m_exact:
        dt = m_exact.group(1)
        return {"type": "exact", "clause": "ec.occurred_at LIKE ?", "params": [f"{dt}%"], "label": f"ngày {dt}"}

    # 5. Month/year (e.g. "tháng 1/2023", "tháng 1 năm 2023")
    m_my = _MONTH_YEAR_RE.search(question)
    if m_my:
        month = int(m_my.group(1))
        year = m_my.group(2)
        m_str = f"{month:02d}"
        return {
            "type": "month",
            "clause": "ec.occurred_at LIKE ?",
            "params": [f"{year}-{m_str}%"],
            "label": f"tháng {m_str}/{year}",
        }

    # 6. Year (e.g. "C7620 năm 2025")
    m_yr = _YEAR_RE.search(question)
    if m_yr:
        year = m_yr.group(1)
        return {"type": "year", "clause": "ec.occurred_at LIKE ?", "params": [f"{year}%"], "label": f"năm {year}"}

    return None


def extract_filter_entities(conn: Optional[sqlite3.Connection], question: str) -> Dict[str, Any]:
    """Return dictionary of recognized structured filter entities."""
    return {
        "machine": extract_machine_entities(conn, question),
        "serial": extract_serial_entities(question),
        "date_range": extract_date_entities(question),
        "phenomenon_concepts": extract_phenomenon_concepts(question),
    }


def log_filter_event(
    question: str,
    entities: Mapping[str, Any],
    matched_count: int,
    top_cases: Sequence[Mapping[str, Any]],
    conversation_id: str = "",
    base_dir: Optional[Path] = None,
) -> None:
    """Continuous improvement event log (Requirement 2.5 / Rule 2026-10-03).

    Records filter usage to local_cases/machine_serial_date_filter_events.jsonl.
    """
    try:
        root = base_dir or Path("local_cases")
        root.mkdir(parents=True, exist_ok=True)
        log_file = root / "machine_serial_date_filter_events.jsonl"
        event = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "question": question,
            "conversation_id": conversation_id,
            "entities": dict(entities),
            "matched_count": matched_count,
            "is_zero_result": matched_count == 0,
            "top_dvds": [c.get("no_dvd") for c in top_cases if c.get("no_dvd")],
            "top_ids": [c.get("id") for c in top_cases if c.get("id")],
            "near_match_dvds": [
                c.get("no_dvd") for c in top_cases
                if c.get("no_dvd") and (c.get("is_near_match") or c.get("near_match_label"))
            ],
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Question analysis
# ---------------------------------------------------------------------------


def extract_codes(question: str) -> List[str]:
    """Error codes from the question, normalized (C0030, F000, JAM4212). Deduplicated."""
    seen: List[str] = []
    for prefix, digits in _CODE_RE.findall(question or ""):
        pref = prefix.upper()
        code = f"{pref}{digits}"
        if code not in seen:
            seen.append(code)
        if pref == "JAM":
            alt = f"J{digits}"
            if alt not in seen:
                seen.append(alt)
        elif pref == "J":
            alt = f"JAM{digits}"
            if alt not in seen:
                seen.append(alt)
    return seen


def extract_keywords(question: str, extra: Sequence[str] = ()) -> List[str]:
    """Normalized content tokens for the symptom-text search path."""
    tokens = normalize_text(question).split()
    keys: List[str] = []
    for tok in list(tokens) + [normalize_text(e) for e in extra]:
        for part in tok.split():
            if len(part) >= 2 and part not in _STOPWORDS and part not in keys:
                keys.append(part)
    return keys[:12]


# ---------------------------------------------------------------------------
# Search + ranking
# ---------------------------------------------------------------------------


def _has_error_code_i(conn: sqlite3.Connection) -> bool:
    """True when the DB was built/migrated with the B0-DICT error_code_i column."""
    return any(
        row[1] == "error_code_i"
        for row in conn.execute("PRAGMA table_info(error_cases)")
    )


def _has_code_missing_col(conn: sqlite3.Connection) -> bool:
    """True once the BK-ERRCODE backfill adds the code_missing flag column."""
    return any(
        row[1] == "code_missing"
        for row in conn.execute("PRAGMA table_info(error_cases)")
    )


def _has_real_code(row: sqlite3.Row, has_missing_col: bool) -> bool:
    """QD1: a case 'has a real code' for ranking purposes."""
    if has_missing_col:
        try:
            if row["code_missing"]:
                return False
        except (KeyError, IndexError, TypeError):
            pass
    try:
        code_c = (row["error_code_c"] or "").strip()
    except (KeyError, IndexError, TypeError):
        code_c = ""
    try:
        code_i = (row["error_code_i"] or "").strip()
    except (KeyError, IndexError, TypeError):
        code_i = ""
    return bool(code_c or code_i)



def is_exact_code_match(row: sqlite3.Row, codes: Sequence[str]) -> bool:
    """Return True if row matches any of the given error codes specifically."""
    if not codes:
        return False
    row_keys = row.keys() if hasattr(row, "keys") else []
    ecc = (row["error_code_c"] or "").upper().replace(" ", "")
    ech = (row["error_code_h"] or "").upper().replace(" ", "")
    eci = (row["error_code_i"] or "").upper().replace(" ", "") if "error_code_i" in row_keys else ""
    raw_str = (row["raw_json"] or "").upper()
    for code in codes:
        c_up = code.upper().replace(" ", "")
        if c_up == ecc or c_up == ech or c_up == eci:
            return True
        if c_up in raw_str:
            return True
    return False


def count_exact_cases(conn: sqlite3.Connection, codes: Sequence[str]) -> int:
    """Return honest count of exact matching cases in DB for the given error codes.
    Prioritizes canonical error code columns (error_code_i, error_code_c, error_code_h).
    If code column count is small (< 5) but raw_json contains rare occurrences (e.g. C0060),
    includes raw_json occurrences so rare codes are accurately counted.
    """
    if not codes:
        return 0
    has_i = _has_error_code_i(conn)
    total_exact = 0
    for code in codes:
        code_clean = (code or "").upper().strip()
        cols = ["UPPER(COALESCE(error_code_c, '')) = ?", "UPPER(COALESCE(error_code_h, '')) = ?"]
        params = [code_clean, code_clean]
        if has_i:
            cols.append("UPPER(COALESCE(error_code_i, '')) = ?")
            params.append(code_clean)
        where_clause = " OR ".join(cols)
        cnt_cols = conn.execute(
            f"SELECT COUNT(*) FROM error_cases WHERE {where_clause}",
            params,
        ).fetchone()[0]
        if cnt_cols >= 5:
            total_exact += int(cnt_cols)
        else:
            cnt_raw = conn.execute(
                "SELECT COUNT(*) FROM error_cases WHERE raw_json LIKE ?",
                (f"%{code_clean}%",),
            ).fetchone()[0]
            total_exact += int(max(cnt_cols, cnt_raw))
    return total_exact

def _candidate_rows(
    conn: sqlite3.Connection,
    codes: Sequence[str],
    keywords: Sequence[str],
    filter_entities: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[sqlite3.Row], int, List[sqlite3.Row]]:
    """Fetch candidate rows combining codes/keywords with structured filters."""
    clauses: List[str] = []
    params: List[Any] = []
    order_clause = ""
    order_params: List[Any] = []
    has_i = _has_error_code_i(conn)

    phenom_concepts: List[Dict[str, Any]] = (
        filter_entities.get("phenomenon_concepts", []) if filter_entities else []
    )

    has_structured_filter = bool(
        filter_entities
        and (
            filter_entities.get("machine")
            or filter_entities.get("serial")
            or filter_entities.get("date_range")
            or phenom_concepts
        )
    )

    # Filter out entity tokens from keywords when structured filter is active
    effective_keywords = list(keywords)
    if has_structured_filter and filter_entities:
        ent_tokens = set()
        if filter_entities.get("machine"):
            for part in normalize_text(filter_entities["machine"]["name"]).split():
                ent_tokens.add(part)
            ent_tokens.add(_normalize_key(filter_entities["machine"]["name"]))
        if filter_entities.get("serial"):
            ent_tokens.add(normalize_text(filter_entities["serial"]))
        if filter_entities.get("date_range"):
            for part in normalize_text(filter_entities["date_range"]["label"]).split():
                ent_tokens.add(part)
        for c in phenom_concepts:
            for trig in c["triggers"]:
                for part in normalize_text(trig).split():
                    ent_tokens.add(part)
                ent_tokens.add(_normalize_key(trig))

        effective_keywords = [
            kw for kw in effective_keywords
            if kw not in ent_tokens and _normalize_key(kw) not in ent_tokens and not kw.isdigit() and len(kw) >= 3
        ]

    # 1. Error codes condition
    if codes:
        ors: List[str] = []
        exact_ors: List[str] = []
        for code in codes:
            ors.append("UPPER(ec.error_code_c) = ?")
            params.append(code)
            exact_ors.append("UPPER(ec.error_code_c) = ?")
            order_params.append(code)
            ors.append("UPPER(ec.error_code_h) = ?")
            params.append(code)
            exact_ors.append("UPPER(ec.error_code_h) = ?")
            order_params.append(code)
            if has_i:
                ors.append("UPPER(ec.error_code_i) = ?")
                params.append(code)
                exact_ors.append("UPPER(ec.error_code_i) = ?")
                order_params.append(code)
            ors.append("ec.raw_json LIKE ?")
            params.append(f"%{code}%")
            exact_ors.append("ec.raw_json LIKE ?")
            order_params.append(f"%{code}%")
            if not has_structured_filter:
                fam = _CODE_FAMILY.get(code[0])
                if fam:
                    ors.append("REPLACE(UPPER(ec.error_code_h), ' ', '') = ?")
                    params.append(fam[1].replace(" ", ""))
        clauses.append("(" + " OR ".join(ors) + ")")
        if exact_ors:
            order_clause = (
                f" ORDER BY CASE WHEN ({' OR '.join(exact_ors)}) THEN 0 ELSE 1 END, ec.id DESC"
            )
    elif not phenom_concepts and effective_keywords:
        ors = []
        for kw in effective_keywords[:4]:
            ors.append("ec.raw_json LIKE ?")
            params.append(f"%{kw}%")
            ors.append("ec.phenomenon LIKE ?")
            params.append(f"%{kw}%")
        clauses.append("(" + " OR ".join(ors) + ")")
        order_clause = " ORDER BY ec.id DESC"

    # 2. Structured filters (Machine, Serial, Date, Phenomenon Concepts)
    if filter_entities:
        m_ent = filter_entities.get("machine")
        if m_ent:
            if m_ent.get("replace_space"):
                clauses.append("REPLACE(ec.machine_type, ' ', '') LIKE ?")
            else:
                clauses.append("ec.machine_type LIKE ?")
            params.append(m_ent["pattern"])

        s_val = filter_entities.get("serial")
        if s_val:
            clauses.append("json_extract(ec.raw_json, '$.G') LIKE ?")
            params.append(f"%{s_val}%")
            if not order_clause:
                order_clause = " ORDER BY ec.id ASC"

        d_ent = filter_entities.get("date_range")
        if d_ent:
            clauses.append(d_ent["clause"])
            params.extend(d_ent["params"])

        if phenom_concepts:
            for concept in phenom_concepts:
                c_ors = []
                for pat in concept["db_patterns"]:
                    c_ors.append("ec.raw_json LIKE ?")
                    params.append(pat)
                    c_ors.append("ec.phenomenon LIKE ?")
                    params.append(pat)
                clauses.append("(" + " OR ".join(c_ors) + ")")

    if not clauses:
        return [], 0, []

    where_sql = " AND ".join(clauses)
    cnt_sql = f"SELECT COUNT(*) AS n FROM error_cases ec WHERE {where_sql}"
    matched_count = conn.execute(cnt_sql, params).fetchone()["n"]

    if not order_clause:
        order_clause = " ORDER BY ec.id DESC"

    sql = (
        "SELECT ec.*, b.source_file, b.sheet_name FROM error_cases ec "
        "LEFT JOIN import_batches b ON b.id = ec.batch_id "
        f"WHERE {where_sql}{order_clause} LIMIT {_MAX_CANDIDATES}"
    )
    rows = list(conn.execute(sql, params + order_params).fetchall())

    # Requirement 2.5: Near-matches relaxation when matched_count == 0
    near_matches: List[sqlite3.Row] = []
    if matched_count == 0 and has_structured_filter and phenom_concepts:
        rel_clauses = []
        rel_params = []
        d_ent = filter_entities.get("date_range") if filter_entities else None
        if d_ent:
            rel_clauses.append(d_ent["clause"])
            rel_params.extend(d_ent["params"])
        for concept in phenom_concepts:
            c_ors = []
            for pat in concept["db_patterns"]:
                c_ors.append("ec.raw_json LIKE ?")
                rel_params.append(pat)
                c_ors.append("ec.phenomenon LIKE ?")
                rel_params.append(pat)
            rel_clauses.append("(" + " OR ".join(c_ors) + ")")

        if rel_clauses:
            rel_sql = (
                "SELECT ec.*, b.source_file, b.sheet_name FROM error_cases ec "
                "LEFT JOIN import_batches b ON b.id = ec.batch_id "
                f"WHERE {' AND '.join(rel_clauses)} ORDER BY ec.id DESC LIMIT 5"
            )
            near_matches = list(conn.execute(rel_sql, rel_params).fetchall())

    return rows, int(matched_count), near_matches


def _score_row(
    row: sqlite3.Row, codes: Sequence[str], keywords: Sequence[str]
) -> int:
    score = 0
    row_keys = row.keys() if hasattr(row, "keys") else []
    ecc = (row["error_code_c"] or "").upper().replace(" ", "")
    ech = (row["error_code_h"] or "").upper().replace(" ", "")
    eci = (
        (row["error_code_i"] or "").upper().replace(" ", "")
        if "error_code_i" in row_keys
        else ""
    )
    for code in codes:
        if code == ecc or code == ech or code == eci:
            score += 100
        elif code[0] in _CODE_FAMILY and _CODE_FAMILY[code[0]][1].replace(" ", "") == ech:
            score += 40
    raw = _raw_json(row)
    text = normalize_text(
        " ".join(
            str(v)
            for v in (
                raw.get("I"),
                raw.get("M"),
                raw.get("O"),
                raw.get("N"),
                raw.get("AA"),
                raw.get("AB"),
                row["error_code_c"],
                row["error_code_h"],
                eci,
            )
            if v
        )
    )
    for code in codes:
        if normalize_text(code) in text:
            score += 20
    for kw in keywords:
        if kw in text:
            score += 5
    ab = str(raw.get("AB") or "").strip()
    immediate = str(raw.get("M") or "").strip() or str(raw.get("O") or "").strip()
    if (ab and ab not in ("-", "—", "ー")) or immediate:
        score += 10
    return score


def search_similar(
    conn: sqlite3.Connection,
    question: str,
    *,
    top_n: int = _TOP_N,
    extra_keywords: Sequence[str] = (),
    filter_entities: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[str], int]:
    """Return (ranked case dicts, codes found, total case count)."""
    codes = extract_codes(question)
    keywords = extract_keywords(question, extra_keywords)
    if filter_entities is None:
        filter_entities = extract_filter_entities(conn, question)

    has_structured_filter = bool(
        filter_entities.get("machine")
        or filter_entities.get("serial")
        or filter_entities.get("date_range")
    )

    rows, matched_count, near_rows = _candidate_rows(conn, codes, keywords, filter_entities)
    has_missing_col = _has_code_missing_col(conn)
    if not rows and not matched_count:
        if near_rows and has_structured_filter:
            near_dicts = []
            for r in near_rows[:top_n]:
                cd = _case_dict(r, has_missing_col)
                cd["is_near_match"] = True
                cd["near_match_label"] = f"Gần đúng - Dòng máy khác: {cd.get('machine_type') or 'Khác'}"
                near_dicts.append(cd)
            return near_dicts, codes, 0
        return [], codes, 0

    total_count = matched_count if has_structured_filter else conn.execute("SELECT COUNT(*) AS n FROM error_cases").fetchone()["n"]

    exact_count = count_exact_cases(conn, codes) if codes else total_count

    if codes or (keywords and not filter_entities.get("phenomenon_concepts")):
        scored: List[Tuple[bool, bool, int, sqlite3.Row]] = []
        for row in rows:
            is_exact = is_exact_code_match(row, codes)
            s = _score_row(row, codes, keywords)
            if s > 0 or has_structured_filter or is_exact:
                scored.append((is_exact, _has_real_code(row, has_missing_col), s, row))
        if codes:
            scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        else:
            scored.sort(key=lambda item: item[2], reverse=True)
        final_rows = [r for _, _, _, r in scored[:top_n]]
    else:
        final_rows = rows[:top_n]

    result_cases = []
    fam_fallback_name = _CODE_FAMILY.get(codes[0][0], ("", ""))[0] if codes and codes[0][0] in _CODE_FAMILY else "cùng họ"
    for r in final_rows:
        cd = _case_dict(r, has_missing_col)
        cd["exact_count"] = exact_count
        if codes:
            is_exact = is_exact_code_match(r, codes)
            cd["is_exact_code"] = is_exact
            if not is_exact:
                cd["family_fallback_label"] = f"Tham khảo cùng họ {fam_fallback_name}"
        result_cases.append(cd)

    return result_cases, codes, int(total_count)


def lookup_glossary(
    conn: sqlite3.Connection, codes: Sequence[str]
) -> Dict[str, Dict[str, Any]]:
    """Glossary meaning per code (first family hit wins). Empty when absent."""
    found: Dict[str, Dict[str, Any]] = {}
    has_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='error_glossary'"
    ).fetchone()
    if not has_table:
        return found
    from aios_habit.error_cases import glossary as _glossary

    for code in codes:
        families = [_CODE_FAMILY[code[0]][0]] if code[0] in _CODE_FAMILY else []
        resolved = code
        for fam in list(families) + [f for f in _GLOSSARY_FAMILIES if f not in families]:
            row = conn.execute(
                "SELECT * FROM error_glossary "
                "WHERE code_family = ? AND code = ? AND code_sub = ''",
                (fam, code),
            ).fetchone()
            if row:
                found[code] = dict(row)
                break
        else:
            if code.startswith("JAM") or (code.startswith("J") and len(code) > 1 and code[1:].isdigit()):
                digits = code[3:] if code.startswith("JAM") else code[1:]
                row = conn.execute(
                    "SELECT * FROM error_glossary "
                    "WHERE code_family = 'JAM' AND code = ? AND code_sub = ''",
                    (digits,),
                ).fetchone()
                if row:
                    found[code] = dict(row)
                    continue
            alias = _glossary.canonical_term(conn, code)
            if alias:
                fam, resolved = alias
                row = conn.execute(
                    "SELECT * FROM error_glossary "
                    "WHERE code_family = ? AND code = ? AND code_sub = ''",
                    (fam, resolved),
                ).fetchone()
                if row:
                    found[code] = dict(row)
    return found


# ---------------------------------------------------------------------------
# Card rendering
# ---------------------------------------------------------------------------


def _clip(value: Any, limit: int = _CLIP) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def _phenomenon_flag(row: sqlite3.Row, raw: Dict[str, Any]) -> Tuple[bool, str, str]:
    """QD-BK82-2: hientuong_missing flag for one card."""
    from aios_habit.error_cases.feedback_loop import BLANK_MARKS

    def _blank(value: Any) -> bool:
        text = " ".join(str(value or "").split())
        return not text or text in BLANK_MARKS

    try:
        col = str(row["phenomenon"] or "")
    except (KeyError, IndexError, TypeError):
        col = ""
    i_text = str(raw.get("I") or "")
    missing = _blank(col) and _blank(i_text)
    suggestion, source = "", ""
    if missing:
        for key in ("M", "O"):
            text = str(raw.get(key) or "").strip()
            if not _blank(text):
                suggestion, source = _clip(text, 160), key
                break
    return missing, suggestion, source


def _case_dict(row: sqlite3.Row, has_missing_col: bool = False) -> Dict[str, Any]:
    raw = _raw_json(row)
    row_keys = row.keys() if hasattr(row, "keys") else []
    hien_tuong = (
        raw.get("I")
        or (row["phenomenon"] if "phenomenon" in row_keys and row["phenomenon"] else "")
        or row["investigation"]
        or raw.get("O")
        or ""
    )
    nguyen_nhan = (
        raw.get("AA")
        or (row["cause"] if "cause" in row_keys and row["cause"] else "")
        or row["investigation"]
        or ""
    )
    doi_sach = (
        raw.get("AB")
        or (row["countermeasure"] if "countermeasure" in row_keys and row["countermeasure"] else "")
        or ""
    )
    if str(doi_sach).strip() in ("", "-", "—", "ー"):
        immediate = str(raw.get("M") or "").strip() or str(raw.get("O") or "").strip()
        doi_sach = "Không cần đối sách chính thức" if immediate else ""

    # Machine / Line
    machine_raw = str(row["machine_type"] or "").strip() if "machine_type" in row_keys and row["machine_type"] else ""
    machine_clean = " ".join(machine_raw.split()) if machine_raw else "không ghi"
    line_clean = " ".join(str(row["line"] or "").split()) if "line" in row_keys and row["line"] else ""
    where = " / ".join(p for p in (machine_clean if machine_clean != "không ghi" else "", line_clean) if p)

    # Serial (raw_json['G'])
    raw_g = str(raw.get("G") or "").replace("\n", " ").strip()
    serial_val = raw_g if raw_g and raw_g not in ("-", "—", "ー", "None", "null") else "không ghi"

    # Occurred Date
    date_raw = str(row["occurred_at"] or "").strip() if "occurred_at" in row_keys and row["occurred_at"] else ""
    date_val = date_raw if date_raw and date_raw not in ("-", "—", "ー", "None", "null") else "không ghi"

    category = row["error_code_h"] or ""
    provenance = " › ".join(
        p
        for p in (
            row["source_file"],
            row["sheet_name"],
            f"dòng {row['source_row']}" if row["source_row"] else "",
        )
        if p
    )
    thieu_hien_tuong, goi_y_hien_tuong, goi_y_nguon = _phenomenon_flag(row, raw)
    from aios_habit.answer_language_policy import translate_kdtps_field
    hien_tuong_trans, _ = translate_kdtps_field(hien_tuong, field_name="phenomenon")
    nguyen_nhan_trans, _ = translate_kdtps_field(nguyen_nhan, field_name="cause")
    doi_sach_trans, _ = translate_kdtps_field(doi_sach, field_name="remedy")
    where_trans, _ = translate_kdtps_field(where, field_name="machine")
    machine_trans, _ = translate_kdtps_field(machine_clean, field_name="machine")
    return {
        "id": row["id"],
        "no_dvd": row["no_dvd"] or "",
        "where": where_trans,
        "machine_type": machine_trans,
        "serial": serial_val,
        "occurred_at": date_val,
        "category": str(category),
        "co_ma_that": _has_real_code(row, has_missing_col),
        "hien_tuong": _clip(hien_tuong_trans),
        "nguyen_nhan": _clip(nguyen_nhan_trans),
        "doi_sach": _clip(doi_sach_trans),
        "bao_cao_goc": provenance,
        "thieu_hien_tuong": thieu_hien_tuong,
        "goi_y_hien_tuong": goi_y_hien_tuong,
        "goi_y_nguon": goi_y_nguon,
    }


def is_natural_question(question: str) -> bool:
    """True if question is an explanatory/investigative question rather than a bare lookup."""
    raw = (question or "").strip()
    norm = normalize_text(raw)
    words = norm.split()

    interrogatives = ("the nao", "la gi", "tai sao", "nhu the nao", "sao lai", "ra sao", "o dau", "khi nao")
    has_interrogative = any(q in norm for q in interrogatives) or "?" in raw

    investigation_aspects = (
        "nguyen nhan", "doi sach", "xu ly", "khac phuc", "huong dan",
        "bao cao dieu tra", "tai lieu", "phuong an", "giai phap",
        "bien phap", "cach sua", "nguyen ly", "dieu tra"
    )
    has_aspect = any(asp in norm for asp in investigation_aspects)

    if len(words) <= 3 and not has_interrogative and not has_aspect:
        return False

    if has_interrogative or has_aspect or len(words) >= 6:
        return True

    return False


def explain_case_number(val: str) -> str:
    """Generate a concise explanation for a case registration number (no_dvd).

    Patterns:
      - YEAR/SEQ (e.g. 2025/1155) -> 'Số đăng ký vụ việc trong sổ gốc: 2025 là năm, 1155 là số thứ tự vụ trong năm'
      - FY.../... (e.g. FY27H2/263) -> 'Số đăng ký vụ việc trong sổ gốc: kỳ tài khóa FY27H2, vụ thứ 263'
      - Y/D + YEAR/SEQ (e.g. Y2015/0_r463, D2019/100) -> 'Số đăng ký vụ việc trong sổ gốc: năm 2015, vụ thứ 0 (bản ghi r463)'
      - Fallback -> 'Số đăng ký vụ việc trong sổ gốc: mã {val}'
    """
    s = str(val or "").strip()
    if not s or s in ("—", "-", "ー", "None"):
        return ""
    m_year = re.match(r"^(\d{4})/(\d+(?:\.\d+)?)$", s)
    if m_year:
        year, seq = m_year.groups()
        if seq.endswith(".0"):
            seq = seq[:-2]
        return f"Số đăng ký vụ việc trong sổ gốc: {year} là năm, {seq} là số thứ tự vụ trong năm"
    m_fy = re.match(r"^(FY[^/]+)/(\d+(?:\.\d+)?)$", s, re.IGNORECASE)
    if m_fy:
        fy, seq = m_fy.groups()
        return f"Số đăng ký vụ việc trong sổ gốc: kỳ tài khóa {fy}, vụ thứ {seq}"
    m_yd = re.match(r"^[YD](\d{4})/([^_\s]+?)(?:_r(\d+))?$", s)
    if m_yd:
        year, seq, r_num = m_yd.groups()
        r_part = f" (bản ghi r{r_num})" if r_num else ""
        return f"Số đăng ký vụ việc trong sổ gốc: năm {year}, vụ thứ {seq}{r_part}"
    return f"Số đăng ký vụ việc trong sổ gốc: mã {s}"


def _render_synthesized_answer(
    cases: Sequence[Dict[str, Any]],
    codes: Sequence[str],
    glossary: Mapping[str, Dict[str, Any]],
    total: int,
    question: str,
    filter_entities: Optional[Mapping[str, Any]] = None,
) -> str:
    primary_code = codes[0] if codes else ""
    code_label = ", ".join(codes) if codes else primary_code

    filter_bits = []
    if filter_entities:
        if filter_entities.get("machine"):
            filter_bits.append(filter_entities["machine"]["label"])
        if filter_entities.get("serial"):
            filter_bits.append(f"số serial **{filter_entities['serial']}**")
        if filter_entities.get("date_range"):
            filter_bits.append(filter_entities["date_range"]["label"])

    filter_suffix = f" (đang lọc theo: {', '.join(filter_bits)})" if filter_bits else ""

    lines = [
        f"Dựa trên cơ sở dữ liệu **{total:,} ca điều tra lịch sử KDTPS**{filter_suffix} và danh mục mã lỗi chuẩn, dưới đây là thông tin điều tra và xử lý cho mã lỗi **{code_label}**:\n".replace(",", ".")
    ]

    entry = glossary.get(primary_code) or (glossary.get(codes[1]) if len(codes) > 1 else None)
    from aios_habit.answer_language_policy import translate_kdtps_field, purify_markdown_text
    if entry:
        meaning = entry.get("name_vi") or entry.get("name_ja") or entry.get("name_en") or "Lỗi vận hành / chức năng"
        meaning, _ = translate_kdtps_field(meaning, field_name="error_name")
        fam = entry.get("code_family") or (_CODE_FAMILY.get(primary_code[0], ("", ""))[0] if primary_code else "")
        source = entry.get("source_file") or ""
        lines.append("### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi")
        lines.append(f"- **Mã lỗi:** `{primary_code}`")
        lines.append(f"- **Tên mã lỗi / Hiện tượng:** {meaning}")
        if fam:
            lines.append(f"- **Phân loại hệ thống:** {fam}")
        if entry.get("cause"):
            c_trans, _ = translate_kdtps_field(entry.get("cause"), field_name="cause")
            lines.append(f"- **Cơ chế phát sinh:** {c_trans}")
        if source:
            lines.append(f"- **Tài liệu tham chiếu:** {source}")
        lines.append("")

    lines.append("### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế")
    causes_seen: List[str] = []
    if entry and entry.get("cause"):
        c_trans, _ = translate_kdtps_field(entry.get("cause"), field_name="cause")
        if c_trans and c_trans not in causes_seen:
            causes_seen.append(c_trans)

    for c in cases:
        raw_nn = c.get("nguyen_nhan") or ""
        trans_nn, _ = translate_kdtps_field(raw_nn, field_name="cause")
        if trans_nn and trans_nn not in ("—", "-", "ー") and trans_nn not in causes_seen:
            causes_seen.append(trans_nn)

    if causes_seen:
        for idx, nn in enumerate(causes_seen[:6], 1):
            lines.append(f"- **Nguyên nhân {idx}:** {nn}")
    else:
        lines.append("- Ghi nhận các yếu tố bất thường về linh kiện cơ khí, cảm biến hoặc tín hiệu điện tử trong quá trình vận hành.")
    lines.append("")

    lines.append("### 3. Đối sách và biện pháp xử lý theo báo cáo điều tra")
    remedies_seen: List[str] = []
    if entry and entry.get("remedy"):
        for r_line in str(entry.get("remedy")).split("\n"):
            r_clean = r_line.strip()
            if r_clean:
                r_trans, _ = translate_kdtps_field(r_clean, field_name="remedy")
                if r_trans and r_trans not in remedies_seen:
                    remedies_seen.append(r_trans)

    for c in cases:
        raw_ds = c.get("doi_sach") or ""
        trans_ds, _ = translate_kdtps_field(raw_ds, field_name="remedy")
        if trans_ds and trans_ds not in ("—", "-", "ー") and trans_ds not in remedies_seen:
            remedies_seen.append(trans_ds)

    if remedies_seen:
        for idx, ds in enumerate(remedies_seen[:6], 1):
            lines.append(f"- **Biện pháp {idx}:** {ds}")
    else:
        lines.append("- Thực hiện phân tích log, kiểm tra ngoại quan linh kiện, thay thế bộ phận nghi ngờ hoặc xử lý theo lưu trình kiểm tra không tái hiện.")
    lines.append("")

    lines.append(f"### 4. Danh sách các ca điều tra thực tế đối chiếu (DB {total:,} ca)".replace(",", "."))
    exact_total = cases[0].get("exact_count", len(cases)) if cases else len(cases)
    if exact_total > len(cases):
        lines.append(
            f"Tìm thấy **{exact_total:,}** ca điều tra thực tế mã lỗi **{code_label}** trong CSDL {total:,} ca "
            f"(hiển thị **{len(cases)}** ca liên quan nhất):\n".replace(",", ".")
        )
    else:
        lines.append(
            f"Tìm thấy **{exact_total:,}** ca điều tra thực tế liên quan trực tiếp đến mã lỗi **{code_label}** "
            f"(hiển thị **{len(cases)}** ca):\n".replace(",", ".")
        )
    for i, case in enumerate(cases[:5], 1):
        vu = f"Vụ {case['no_dvd'] or '—'}"
        where = case.get("where") or ""
        head = f"**{i}. {vu}**" + (f" ({where})" if where else "")
        lines.append(head)
        exp = explain_case_number(case.get("no_dvd") or "")
        if exp:
            lines.append(f"- _{exp}_")
        lines.append(
            f"- **Máy:** {case.get('machine_type') or 'không ghi'} | **Serial:** {case.get('serial') or 'không ghi'} | **Ngày phát sinh:** {case.get('occurred_at') or 'không ghi'}"
        )
        lines.append(f"- **Hiện tượng:** {case['hien_tuong'] or '—'}")
        lines.append(f"- **Nguyên nhân:** {case['nguyen_nhan'] or '—'}")
        lines.append(f"- **Đối sách:** {case['doi_sach'] or '—'}")
        lines.append(f"- **Báo cáo gốc:** `{case['bao_cao_goc'] or '—'}`")
        lines.append("")

    lines.append("---")
    lines.append("_Nguồn trích dẫn: Cơ sở dữ liệu ca lỗi KDTPS Bước 0–5 (30.075 ca lịch sử) và Danh mục mã lỗi tự chẩn đoán._")
    res_text = "\n".join(lines)
    from aios_habit.answer_language_policy import purify_markdown_text
    return purify_markdown_text(res_text, question, route="error_lookup_synthesized")


def _render_cards(
    cases: Sequence[Dict[str, Any]],
    codes: Sequence[str],
    glossary: Mapping[str, Dict[str, Any]],
    total: int,
    filter_entities: Optional[Mapping[str, Any]] = None,
) -> str:
    code_label = ", ".join(codes) if codes else ""
    lines: List[str] = []

    # Check if structured filter applied
    has_filter = bool(
        filter_entities
        and (
            filter_entities.get("machine")
            or filter_entities.get("serial")
            or filter_entities.get("date_range")
        )
    )

    exact_total = cases[0].get("exact_count", len(cases)) if cases else 0
    exact_displayed = sum(1 for c in cases if c.get("is_exact_code"))
    fallback_displayed = len(cases) - exact_displayed
    fam_name = _CODE_FAMILY.get(codes[0][0], ("", ""))[0] if codes and codes[0][0] in _CODE_FAMILY else "cùng họ"

    if has_filter and filter_entities:
        filter_descs = []
        if filter_entities.get("machine"):
            filter_descs.append(filter_entities["machine"]["label"])
        if filter_entities.get("serial"):
            filter_descs.append(f"số serial **{filter_entities['serial']}**")
        if filter_entities.get("date_range"):
            filter_descs.append(filter_entities["date_range"]["label"])
        if filter_entities.get("phenomenon_concepts"):
            c_names = " + ".join([c["name"] for c in filter_entities["phenomenon_concepts"]])
            filter_descs.append(f"hiện tượng **{c_names}**")
        if codes:
            filter_descs.append(f"mã lỗi **{code_label}**")

        desc_str = ", ".join(filter_descs)
        if total == 0:
            lines.append(f"Không tìm thấy ca nào (0 ca) trong vùng đã khoanh ({desc_str}).")
            if cases:
                lines.append("")
                lines.append(
                    f"### Đề xuất các ca tương tự gần đúng (có nhãn gần đúng):\n"
                    f"Hệ thống tìm thấy **{len(cases)}** ca có cùng hiện tượng trong khoảng thời gian này trên dòng máy khác:"
                )
        else:
            lines.append(
                f"Đang lọc theo: {desc_str}. "
                f"Tìm thấy **{total:,}** ca phù hợp trong CSDL 30.075 ca lịch sử "
                f"(hiển thị {len(cases)} ca):".replace(",", ".")
            )
    elif codes and fallback_displayed > 0:
        # Ticket Requirement 2(a): Separate exact matches from family fallback matches
        lines.append(
            f"Tìm thấy **{exact_total}** ca **{code_label}** chính xác; "
            f"hiển thị thêm **{fallback_displayed}** ca cùng họ **{fam_name}** để tham khảo "
            f"(trong **{total:,}** ca lịch sử):".replace(",", ".")
        )
    elif codes:
        # Ticket Requirement 2(a): Honest count title with top-N indication like CAU_05
        if exact_total > len(cases):
            lines.append(
                f"Tìm thấy **{exact_total:,}** ca mã lỗi **{code_label}** trong **{total:,}** ca lịch sử "
                f"(hiển thị {len(cases)} ca liên quan nhất):".replace(",", ".")
            )
        else:
            lines.append(
                f"Tìm thấy **{exact_total:,}** ca mã lỗi **{code_label}** trong **{total:,}** ca lịch sử "
                f"(hiển thị {len(cases)} ca):".replace(",", ".")
            )
    else:
        lines.append(
            f"Tìm thấy **{len(cases)}** ca lỗi liên quan"
            + (f" đến **{code_label}**" if code_label else "")
            + f" trong **{total:,}** ca lịch sử.".replace(",", ".")
        )

    seen_entries = set()
    from aios_habit.answer_language_policy import translate_kdtps_field, has_japanese
    for code in codes:
        entry = glossary.get(code)
        if not entry:
            continue
        entry_key = entry.get("id") or (entry.get("code_family"), entry.get("code")) or code
        if entry_key in seen_entries:
            continue
        seen_entries.add(entry_key)

        fam = entry.get("code_family") or (_CODE_FAMILY.get(code[0], ("", ""))[0] if code else "glossary")
        raw_meaning = (
            entry.get("name_vi") or entry.get("name_ja") or entry.get("name_en") or ""
        )
        meaning, _ = translate_kdtps_field(raw_meaning, field_name="error_name")

        raw_cause = entry.get("cause") or ""
        cause_trans, _ = translate_kdtps_field(raw_cause, field_name="cause") if raw_cause else ("", "")
        cause = _clip(cause_trans, 160) if cause_trans and not has_japanese(cause_trans) else ""

        raw_remedy = entry.get("remedy") or ""
        remedy_trans, _ = translate_kdtps_field(raw_remedy, field_name="remedy") if raw_remedy else ("", "")
        remedy = _clip(remedy_trans, 160) if remedy_trans and not has_japanese(remedy_trans) else ""

        source = entry.get("source_file") or ""

        # If meaning still has raw Japanese (no translation available in dictionary/policy)
        if has_japanese(meaning):
            if source:
                lines.append(f"_Nguồn tham chiếu từ điển mã lỗi: `{source}`_")
            continue

        if not meaning and not cause and not remedy:
            if source:
                lines.append(f"_Nguồn tham chiếu từ điển mã lỗi: `{source}`_")
            continue

        fam_label = fam or "glossary"
        gloss = f"_Từ điển mã lỗi ({fam_label}): {meaning}_"
        extra_parts = []
        if cause:
            extra_parts.append(f"Nguyên nhân: {cause}")
        if remedy:
            extra_parts.append(f"Khắc phục: {remedy}")
        if source:
            extra_parts.append(f"Nguồn: {source}")
        extra = " · ".join(extra_parts)
        lines.append(gloss + (f" — {extra}" if extra else ""))

    for i, case in enumerate(cases, 1):
        near_label = case.get("near_match_label")
        fallback_label = case.get("family_fallback_label")
        if near_label:
            head = f"### {i}. Vụ {case['no_dvd'] or '—'} · [{near_label}]"
        elif fallback_label:
            head = f"### {i}. Vụ {case['no_dvd'] or '—'} · [{fallback_label}]"
        elif fallback_displayed > 0 and case.get("is_exact_code"):
            head = f"### {i}. Vụ {case['no_dvd'] or '—'} · [Khớp chính xác {code_label}]"
        else:
            head = f"### {i}. Vụ {case['no_dvd'] or '—'}"
        bits = [b for b in (case["where"], case["category"]) if b]
        if bits:
            head += " · " + " · ".join(bits)
        lines.append("")
        lines.append(head)
        exp = explain_case_number(case.get("no_dvd") or "")
        if exp:
            lines.append(f"- _{exp}_")
        # Ticket Requirement 2.3: exact summary line
        lines.append(
            f"- **Máy:** {case.get('machine_type') or 'không ghi'} | **Serial:** {case.get('serial') or 'không ghi'} | **Ngày phát sinh:** {case.get('occurred_at') or 'không ghi'}"
        )
        if case.get("thieu_hien_tuong"):
            lines.append("- **Hiện tượng:** ⚠️ chưa được ghi nhận")
            if case.get("goi_y_hien_tuong"):
                lines.append(
                    f"  - _Gợi ý từ biên bản (cột {case['goi_y_nguon']}): "
                    f"{case['goi_y_hien_tuong']}_"
                )
        else:
            lines.append(f"- **Hiện tượng:** {case['hien_tuong'] or '—'}")
        lines.append(f"- **Nguyên nhân:** {case['nguyen_nhan'] or '—'}")
        lines.append(f"- **Đối sách:** {case['doi_sach'] or '—'}")
        lines.append(f"- **Báo cáo gốc:** `{case['bao_cao_goc'] or '—'}`")

    lines.append("")
    lines.append(
        "_Nguồn: DB ca lỗi Bước 0–5 (lịch sử KDTPS thật). "
        "Muốn đào sâu một ca, hỏi theo mã vụ (VD: `vụ 2023/5`)._"
    )
    lines.append("")
    lines.append("---")
    lines.append(
        "**Đánh giá gợi ý này:** `đánh giá đúng` · `đánh giá sai` · "
        "`đánh giá một phần`"
    )
    lines.append("_Gõ ngay trong ô chat — không cần mở thêm gì._")
    res_text = "\n".join(lines)
    from aios_habit.answer_language_policy import purify_markdown_text
    return purify_markdown_text(res_text, code_label or "cards", route="error_lookup_cards")


# ---------------------------------------------------------------------------
# Action wiring
# ---------------------------------------------------------------------------


def _log_suggestion_call(
    db_path: Path, cases: Sequence[Dict[str, Any]], conversation_id: str
) -> None:
    try:
        from aios_habit.error_cases import feedback_loop as _feedback
        from aios_habit.error_cases import store as _store

        conn = _store.connect(db_path)
        try:
            _feedback.init_feedback_loop(conn)
            _feedback.log_suggestion_call(
                conn,
                int(cases[0]["id"]),
                suggested_refs=[c["no_dvd"] for c in cases if c.get("no_dvd")],
                note="tra_cuu_loi_tuong_tu",
                conversation_id=conversation_id or "",
            )
        finally:
            conn.close()
    except Exception:
        pass


def _is_dieu_tra_loi_scope(request: ChatActionRequest) -> bool:
    """Strictly isolate error lookup to the 'dieu_tra_loi' notebook and domain (Requirements 2.7 & 2.8)."""
    forced = (request.context or {}).get("forced_domain") if request.context else None
    nb_id = (request.notebook_id or "").strip()

    # 1. Explicit forced domain check
    if forced:
        f_str = str(forced).strip().lower()
        if f_str in ("dieu_tra_loi", "dtl"):
            return True
        if f_str in ("mom", "lsu", "tong_hop", "tri_thuc"):
            return False

    # 2. Notebook ID check
    if nb_id:
        if nb_id in ("NB-LAZY-DTL", "dieu_tra_loi"):
            return True
        if nb_id in ("mom_opcenter", "NB-LAZY-LSU", "NB-C26E1C84"):
            return False
        try:
            from aios_habit.draft_source_layer import resolve_notebook_draft_domain
            dom = resolve_notebook_draft_domain(nb_id)
            if dom in ("dieuchinh", "dieu_tra_loi"):
                return True
            if dom in ("mom", "lsu", "tong_hop"):
                return False
        except Exception:
            pass
        return False

    return True

class _ErrorLookupAction(ChatAction):
    """ChatAction that fires on error codes, machine/serial/date filters, or symptom search."""

    def matches(self, request: ChatActionRequest) -> bool:
        # 1. Reject off-topic trap queries
        norm = request.normalized_question
        if any(h in norm for h in _OFFTOPIC_HINTS):
            return False

        # 2. Domain scope isolation (Requirements 2.7 & 2.8)
        if not _is_dieu_tra_loi_scope(request):
            return False

        nb_id = request.notebook_id or ""

        # Check for error codes
        codes = extract_codes(request.question)
        if codes:
            return True

        # Check for structured filters (machine, serial, date, phenomenon concepts)
        ents = extract_filter_entities(None, request.question)
        if ents.get("machine") or ents.get("serial") or ents.get("phenomenon_concepts"):
            return True
        if ents.get("date_range") and (
            nb_id in ("NB-LAZY-DTL", "dieu_tra_loi")
            or any(w in norm for w in ("ca", "loi", "phieu", "dieu tra", "su co"))
        ):
            return True

        # Check generic hints (symptom search like "kẹt giấy cụm sấy")
        if super().matches(request):
            return True

        return False


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    norm = request.normalized_question
    if any(h in norm for h in _OFFTOPIC_HINTS):
        return None

    if not _is_dieu_tra_loi_scope(request):
        return None

    try:
        db_path = resolve_db_path(request)
        if db_path is None:
            return None
        conn = _open_ro(db_path)
    except Exception:
        return None
    try:
        cases: List[Dict[str, Any]] = []
        codes = extract_codes(request.question)
        filter_ents = extract_filter_entities(conn, request.question)
        total = 0
        glossary: Mapping[str, Dict[str, Any]] = {}
        has_filter = bool(
            filter_ents.get("machine")
            or filter_ents.get("serial")
            or filter_ents.get("date_range")
            or filter_ents.get("phenomenon_concepts")
        )

        if codes or extract_keywords(request.question) or has_filter:
            if codes:
                glossary = lookup_glossary(conn, codes)
            extra: List[str] = []
            for code in codes:
                entry = glossary.get(code, {})
                extra.extend(
                    str(entry.get(k) or "")
                    for k in ("name_vi", "name_ja", "name_en", "cause", "remedy")
                )
            cases, codes, total = search_similar(
                conn, request.question, extra_keywords=extra, filter_entities=filter_ents
            )

        if not cases and not glossary and total == 0 and not has_filter:
            return None

        # Route between bare cards vs synthesized answer
        if codes and is_natural_question(request.question) and total > 0:
            text = _render_synthesized_answer(cases, codes, glossary, total, request.question, filter_entities=filter_ents)
        else:
            text = _render_cards(cases, codes, glossary, total, filter_entities=filter_ents)

        # Log filter usage for continuous improvement loop (Requirements 2.5 & 2.6)
        if has_filter:
            log_filter_event(
                question=request.question,
                entities={
                    "machine": filter_ents.get("machine", {}).get("name") if filter_ents.get("machine") else None,
                    "serial": filter_ents.get("serial"),
                    "date_range": filter_ents.get("date_range", {}).get("label") if filter_ents.get("date_range") else None,
                    "phenomenon_concepts": [c["name"] for c in filter_ents.get("phenomenon_concepts", [])],
                    "codes": codes,
                },
                matched_count=total,
                top_cases=cases,
                conversation_id=request.conversation_id or "",
            )

        if cases:
            _log_suggestion_call(db_path, cases, request.conversation_id or "")
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=TITLE,
        blocks=(ChatActionBlock(kind=BLOCK_MARKDOWN, text=text),),
    )


def register() -> None:
    register_action(
        _ErrorLookupAction(
            name=ACTION_NAME,
            title=TITLE,
            hints=_HINTS,
            handler=_handler,
            fallback=True,
            description=(
                "Tra cứu ca lỗi tương tự trong DB Bước 0–5: nhập mã lỗi, "
                "bộ lọc tên máy/serial/ngày hoặc mô tả hiện tượng, nhận top 3–5 ca "
                "kèm nguyên nhân, đối sách và báo cáo gốc — chỉ đọc."
            ),
        )
    )


register()
