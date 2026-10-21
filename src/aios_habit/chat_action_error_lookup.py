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
    trong trên dưới từ tu đến den tới toi bị được có không gì mà thì là các cac những nhung
    một hai máy may lỗi error loi ma code tra cuu tim kiem tuong tu
    ca vụ vu phiếu phieu dòng dong họ ho model serial seri số so
    năm nam tháng thang ngày ngay phát phat sinh thuộc thuoc danh sách sach liệt liet kê ke
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
# Entity recognition (Machine, Serial, Date)
# ---------------------------------------------------------------------------


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
    """Extract date range, month/year, or year from question."""
    m_range = _DATE_RANGE_RE.search(question)
    if m_range:
        d1, d2 = m_range.group(1), m_range.group(2)
        return {"type": "range", "clause": "ec.occurred_at >= ? AND ec.occurred_at <= ?", "params": [d1, d2], "label": f"từ {d1} đến {d2}"}
    m_exact = _EXACT_DATE_RE.search(question)
    if m_exact:
        dt = m_exact.group(1)
        return {"type": "exact", "clause": "ec.occurred_at LIKE ?", "params": [f"{dt}%"], "label": f"ngày {dt}"}
    m_my = _MONTH_YEAR_RE.search(question)
    if m_my:
        month = int(m_my.group(1))
        year = m_my.group(2)
        m_str = f"{month:02d}"
        return {"type": "month", "clause": "ec.occurred_at LIKE ?", "params": [f"{year}-{m_str}%"], "label": f"tháng {m_str}/{year}"}
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
            "top_dvds": [c.get("no_dvd") for c in top_cases if c.get("no_dvd")],
            "top_ids": [c.get("id") for c in top_cases if c.get("id")],
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


def _candidate_rows(
    conn: sqlite3.Connection,
    codes: Sequence[str],
    keywords: Sequence[str],
    filter_entities: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[sqlite3.Row], int]:
    """Fetch candidate rows combining codes/keywords with structured filters."""
    clauses: List[str] = []
    params: List[Any] = []
    order_clause = ""
    order_params: List[Any] = []
    has_i = _has_error_code_i(conn)

    has_structured_filter = bool(
        filter_entities
        and (
            filter_entities.get("machine")
            or filter_entities.get("serial")
            or filter_entities.get("date_range")
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
        effective_keywords = [
            kw for kw in effective_keywords
            if kw not in ent_tokens and _normalize_key(kw) not in ent_tokens and not kw.isdigit()
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
    elif effective_keywords:
        ors = []
        for kw in effective_keywords[:4]:
            ors.append("ec.raw_json LIKE ?")
            params.append(f"%{kw}%")
        clauses.append("(" + " OR ".join(ors) + ")")
        order_clause = " ORDER BY ec.id DESC"

    # 2. Structured filters (Machine, Serial, Date)
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

    if not clauses:
        return [], 0

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
    return rows, int(matched_count)


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

    rows, matched_count = _candidate_rows(conn, codes, keywords, filter_entities)
    if not rows and not matched_count:
        return [], codes, 0

    total_count = matched_count if has_structured_filter else conn.execute("SELECT COUNT(*) AS n FROM error_cases").fetchone()["n"]

    has_missing_col = _has_code_missing_col(conn)
    if codes or keywords:
        scored: List[Tuple[bool, int, sqlite3.Row]] = []
        for row in rows:
            s = _score_row(row, codes, keywords)
            if s > 0 or has_structured_filter:
                scored.append((_has_real_code(row, has_missing_col), s, row))
        if codes:
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        else:
            scored.sort(key=lambda item: item[1], reverse=True)
        final_rows = [r for _, _, r in scored[:top_n]]
    else:
        final_rows = rows[:top_n]

    return [_case_dict(r, has_missing_col) for r in final_rows], codes, int(total_count)


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
    lines.append(f"Tìm thấy **{len(cases)}** ca điều tra thực tế liên quan trực tiếp đến mã lỗi **{code_label}**:\n")
    for i, case in enumerate(cases[:5], 1):
        phieu = f"Phiếu {case['no_dvd'] or '—'}"
        where = case.get("where") or ""
        head = f"**{i}. {phieu}**" + (f" ({where})" if where else "")
        lines.append(head)
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

    if has_filter and filter_entities:
        filter_descs = []
        if filter_entities.get("machine"):
            filter_descs.append(filter_entities["machine"]["label"])
        if filter_entities.get("serial"):
            filter_descs.append(f"số serial **{filter_entities['serial']}**")
        if filter_entities.get("date_range"):
            filter_descs.append(filter_entities["date_range"]["label"])
        if codes:
            filter_descs.append(f"mã lỗi **{code_label}**")

        desc_str = ", ".join(filter_descs)
        lines.append(
            f"Đang lọc theo: {desc_str}. "
            f"Tìm thấy **{total:,}** ca phù hợp trong CSDL 30.075 ca lịch sử "
            f"(hiển thị {len(cases)} ca):".replace(",", ".")
        )
    else:
        lines.append(
            f"Tìm thấy **{len(cases)}** ca lỗi liên quan"
            + (f" đến **{code_label}**" if code_label else "")
            + f" trong **{total:,}** ca lịch sử.".replace(",", ".")
        )

    for code in codes:
        entry = glossary.get(code)
        if entry:
            fam = _CODE_FAMILY.get(code[0], ("", ""))[0]
            meaning = (
                entry.get("name_vi") or entry.get("name_ja") or entry.get("name_en") or ""
            )
            cause = _clip(entry.get("cause"), 160)
            remedy = _clip(entry.get("remedy"), 160)
            source = entry.get("source_file") or ""
            gloss = f"_Từ điển mã lỗi ({fam or 'glossary'}): {meaning}_"
            extra = " · ".join(
                p for p in (f"Nguyên nhân: {cause}" if cause else "",
                            f"Khắc phục: {remedy}" if remedy else "",
                            f"Nguồn: {source}" if source else "") if p
            )
            lines.append(gloss + (f" — {extra}" if extra else ""))

    for i, case in enumerate(cases, 1):
        head = f"### {i}. Phiếu {case['no_dvd'] or '—'}"
        bits = [b for b in (case["where"], case["category"]) if b]
        if bits:
            head += " · " + " · ".join(bits)
        lines.append("")
        lines.append(head)
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
        "Muốn đào sâu một ca, hỏi theo mã phiếu (VD: `phiếu 2023/5`)._"
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


class _ErrorLookupAction(ChatAction):
    """ChatAction that fires on error codes, machine/serial/date filters, or symptom search."""

    def matches(self, request: ChatActionRequest) -> bool:
        # 1. Reject off-topic trap queries
        norm = request.normalized_question
        if any(h in norm for h in _OFFTOPIC_HINTS):
            return False

        # 2. Store-scope isolation
        forced = (request.context or {}).get("forced_domain") if request.context else None
        nb_id = request.notebook_id or ""

        if forced and str(forced).strip().lower() not in ("auto", "dieu_tra_loi"):
            return False

        if nb_id and nb_id in ("mom_opcenter", "NB-LAZY-LSU", "NB-C26E1C84"):
            return False

        # Check for error codes
        codes = extract_codes(request.question)
        if codes:
            return True

        # Check for structured filters (machine, serial, date)
        ents = extract_filter_entities(None, request.question)
        if ents.get("machine") or ents.get("serial"):
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

    forced = (request.context or {}).get("forced_domain") if request.context else None
    nb_id = request.notebook_id or ""
    if forced and str(forced).strip().lower() not in ("auto", "dieu_tra_loi"):
        return None
    if nb_id and nb_id in ("mom_opcenter", "NB-LAZY-LSU", "NB-C26E1C84"):
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
        has_filter = bool(filter_ents.get("machine") or filter_ents.get("serial") or filter_ents.get("date_range"))

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

        if not cases and not glossary:
            return None

        # Route between bare cards vs synthesized answer
        if codes and is_natural_question(request.question):
            text = _render_synthesized_answer(cases, codes, glossary, total, request.question, filter_entities=filter_ents)
        else:
            text = _render_cards(cases, codes, glossary, total, filter_entities=filter_ents)

        # Log filter usage for continuous improvement loop (Requirement 2.5)
        if has_filter:
            log_filter_event(
                question=request.question,
                entities={
                    "machine": filter_ents.get("machine", {}).get("name") if filter_ents.get("machine") else None,
                    "serial": filter_ents.get("serial"),
                    "date_range": filter_ents.get("date_range", {}).get("label") if filter_ents.get("date_range") else None,
                    "codes": codes,
                },
                matched_count=total,
                top_cases=cases,
                conversation_id=request.conversation_id or "",
            )

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
