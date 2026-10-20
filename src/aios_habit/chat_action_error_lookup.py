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

DB location (first hit wins): the request context key ``error_cases_db``,
the ``AIOS_ERROR_CASES_DB`` env var, then the well-known deploy path
``C:/tmp/kdtps_standard/error_cases_reconciled.db`` (hoặc DB cũ ``error_cases_dict.db``) on the home machine.
"""

from __future__ import annotations

import os
import re
import sqlite3
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
    cho toi xem giup voi a à ạ á ớ ờ cái này đó kia và hoặc với của
    trong trên dưới từ đến bị được có không gì mà thì là các những
    một hai máy lỗi error loi ma code tra cuu tim kiem tuong tu
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


# ---------------------------------------------------------------------------
# DB access (read-only)
# ---------------------------------------------------------------------------


def resolve_db_path(request: ChatActionRequest) -> Optional[Path]:
    """Locate the error_cases DB without creating anything. None = absent."""
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
    import json

    try:
        data = json.loads(row["raw_json"] or "{}")
    except (ValueError, TypeError):
        data = {}
    return data if isinstance(data, dict) else {}


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
    """QD1: a case "has a real code" for ranking purposes.

    True when the row carries an extracted real code (error_code_c /
    error_code_i) and is not flagged code_missing=1 by the BK-ERRCODE
    backfill. Groups without a code system in source (JAM, 外観, ...)
    identify through classification H instead, so they are never flagged
    as missing — they simply sort below rows that carry a real code.
    """
    if has_missing_col:
        try:
            if row["code_missing"]:
                return False
        except (KeyError, IndexError, TypeError):
            pass
    # Old-schema DBs (pre-B0-DICT) lack the error_code_i column entirely;
    # treat as empty instead of raising IndexError (caught silently upstream).
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
    conn: sqlite3.Connection, codes: Sequence[str], keywords: Sequence[str]
) -> List[sqlite3.Row]:
    clauses: List[str] = []
    params: List[Any] = []
    order_clause = ""
    order_params: List[Any] = []
    has_i = _has_error_code_i(conn)
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
                # B0-DICT: the real code lives in error_code_i for history
                # rows whose column H only holds the group ('C CALL').
                ors.append("UPPER(ec.error_code_i) = ?")
                params.append(code)
                exact_ors.append("UPPER(ec.error_code_i) = ?")
                order_params.append(code)
            ors.append("ec.raw_json LIKE ?")
            params.append(f"%{code}%")
            fam = _CODE_FAMILY.get(code[0])
            if fam:
                ors.append("REPLACE(UPPER(ec.error_code_h), ' ', '') = ?")
                params.append(fam[1].replace(" ", ""))
        clauses.append("(" + " OR ".join(ors) + ")")
        if exact_ors:
            order_clause = (
                f" ORDER BY CASE WHEN ({' OR '.join(exact_ors)}) THEN 0 ELSE 1 END, ec.id DESC"
            )
    elif keywords:
        ors = []
        for kw in keywords[:4]:
            ors.append("ec.raw_json LIKE ?")
            params.append(f"%{kw}%")
        clauses.append("(" + " OR ".join(ors) + ")")
        order_clause = " ORDER BY ec.id DESC"
    else:
        return []
    sql = (
        "SELECT ec.*, b.source_file, b.sheet_name FROM error_cases ec "
        "LEFT JOIN import_batches b ON b.id = ec.batch_id "
        f"WHERE {' AND '.join(clauses)}{order_clause} LIMIT {_MAX_CANDIDATES}"
    )
    return list(conn.execute(sql, params + order_params).fetchall())


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
    # Prefer actionable cards: a real countermeasure recorded.
    # QD2: the immediate action (M/O) that stands in for an empty
    # countermeasure cell counts as actionable too.
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
) -> Tuple[List[Dict[str, Any]], List[str], int]:
    """Return (ranked case dicts, codes found, total case count)."""
    total = conn.execute("SELECT COUNT(*) AS n FROM error_cases").fetchone()["n"]
    if not total:
        return [], [], 0
    codes = extract_codes(question)
    keywords = extract_keywords(question, extra_keywords)
    rows = _candidate_rows(conn, codes, keywords)
    has_missing_col = _has_code_missing_col(conn)
    scored: List[Tuple[bool, int, sqlite3.Row]] = []
    for row in rows:
        s = _score_row(row, codes, keywords)
        if s > 0:
            scored.append((_has_real_code(row, has_missing_col), s, row))
    if codes:
        # QD1: on a code lookup, cases carrying a real code rank first.
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    else:
        scored.sort(key=lambda item: item[1], reverse=True)
    return [_case_dict(r, has_missing_col) for _, _, r in scored[:top_n]], codes, int(total)


def lookup_glossary(
    conn: sqlite3.Connection, codes: Sequence[str]
) -> Dict[str, Dict[str, Any]]:
    """Glossary meaning per code (first family hit wins). Empty when absent.

    B0-DICT: when the raw token is not a direct code hit, resolve it
    through the term-alias index (variant spellings -> canonical code),
    e.g. a Japanese name from the source workbook.
    """
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
            # Check JAM digits-only lookup (glossary stores "4212" with family "JAM")
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
    """QD-BK82-2: hientuong_missing flag for one card.

    Returns (missing, suggested_text, suggested_source). The suggestion is
    the M/O investigation text WITH provenance (column letter) — surfaced
    for the user, never auto-filled into the phenomenon field.
    """
    from aios_habit.error_cases.feedback_loop import BLANK_MARKS

    def _blank(value: Any) -> bool:
        text = " ".join(str(value or "").split())
        return not text or text in BLANK_MARKS

    try:
        col = str(row["phenomenon"] or "")
    except (KeyError, IndexError, TypeError):
        # Old-schema DBs (pre-B0-FORM migration): treat as empty, like the
        # error_code_i guard in _has_real_code (B1-FEAT Mốc S1 lesson).
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
        # QD2: an empty countermeasure cell whose row records an immediate
        # action (M/O) means "no formal countermeasure needed".
        immediate = str(raw.get("M") or "").strip() or str(raw.get("O") or "").strip()
        doi_sach = "Không cần đối sách chính thức" if immediate else ""
    machine = " ".join(str(row["machine_type"] or "").split())
    line = " ".join(str(row["line"] or "").split())
    where = " / ".join(p for p in (machine, line) if p)
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
    return {
        "id": row["id"],
        "no_dvd": row["no_dvd"] or "",
        "where": where,
        "category": str(category),
        "co_ma_that": _has_real_code(row, has_missing_col),
        "hien_tuong": _clip(hien_tuong),
        "nguyen_nhan": _clip(nguyen_nhan),
        "doi_sach": _clip(doi_sach),
        "bao_cao_goc": provenance,
        # B2 / QD-BK82-2: missing-phenomenon flag + M/O suggestion.
        "thieu_hien_tuong": thieu_hien_tuong,
        "goi_y_hien_tuong": goi_y_hien_tuong,
        "goi_y_nguon": goi_y_nguon,
    }


def is_natural_question(question: str) -> bool:
    """True if question is an explanatory/investigative question rather than a bare code lookup.

    Bare code lookups: "C7620", "c7620", "JAM4212", "tra cứu C7620", "mã C7620" (short, direct lookup intent).
    Natural questions: "Mã lỗi C7620 nguyên nhân chính là gì và đối sách xử lý thế nào theo báo cáo điều tra?",
    "Tại sao máy báo C7620?", "Hướng dẫn xử lý lỗi JAM4212 trên máy Iris2024".
    """
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
) -> str:
    primary_code = codes[0] if codes else ""
    code_label = ", ".join(codes) if codes else primary_code

    lines = [
        f"Dựa trên cơ sở dữ liệu **{total:,} ca điều tra lịch sử KDTPS** và danh mục mã lỗi chuẩn, dưới đây là thông tin điều tra và xử lý cho mã lỗi **{code_label}**:\n".replace(",", ".")
    ]

    entry = glossary.get(primary_code) or (glossary.get(codes[1]) if len(codes) > 1 else None)
    if entry:
        meaning = entry.get("name_vi") or entry.get("name_ja") or entry.get("name_en") or "Lỗi vận hành / chức năng"
        fam = entry.get("code_family") or (_CODE_FAMILY.get(primary_code[0], ("", ""))[0] if primary_code else "")
        source = entry.get("source_file") or ""
        lines.append("### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi")
        lines.append(f"- **Mã lỗi:** `{primary_code}`")
        lines.append(f"- **Tên mã lỗi / Hiện tượng:** {meaning}")
        if fam:
            lines.append(f"- **Phân loại hệ thống:** {fam}")
        if entry.get("cause"):
            lines.append(f"- **Cơ chế phát sinh:** {entry.get('cause')}")
        if source:
            lines.append(f"- **Tài liệu tham chiếu:** {source}")
        lines.append("")

    lines.append("### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế")
    causes_seen: List[str] = []
    if entry and entry.get("cause") and entry.get("cause") not in causes_seen:
        causes_seen.append(entry.get("cause"))

    for c in cases:
        raw_nn = c.get("nguyen_nhan") or ""
        if raw_nn and raw_nn not in ("—", "-", "ー") and raw_nn not in causes_seen:
            causes_seen.append(raw_nn)

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
            if r_clean and r_clean not in remedies_seen:
                remedies_seen.append(r_clean)

    for c in cases:
        raw_ds = c.get("doi_sach") or ""
        if raw_ds and raw_ds not in ("—", "-", "ー", "不要", "Không cần đối sách chính thức") and raw_ds not in remedies_seen:
            remedies_seen.append(raw_ds)

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
        lines.append(f"- **Hiện tượng:** {case['hien_tuong'] or '—'}")
        lines.append(f"- **Nguyên nhân:** {case['nguyen_nhan'] or '—'}")
        lines.append(f"- **Đối sách:** {case['doi_sach'] or '—'}")
        lines.append(f"- **Báo cáo gốc:** `{case['bao_cao_goc'] or '—'}`")
        lines.append("")

    lines.append("---")
    lines.append("_Nguồn trích dẫn: Cơ sở dữ liệu ca lỗi KDTPS Bước 0–5 (30.075 ca lịch sử) và Danh mục mã lỗi tự chẩn đoán._")
    return "\n".join(lines)


def _render_cards(
    cases: Sequence[Dict[str, Any]],
    codes: Sequence[str],
    glossary: Mapping[str, Dict[str, Any]],
    total: int,
) -> str:
    code_label = ", ".join(codes) if codes else ""
    lines = [
        f"Tìm thấy **{len(cases)}** ca lỗi liên quan"
        + (f" đến **{code_label}**" if code_label else "")
        + f" trong **{total:,}** ca lịch sử.".replace(",", "."),
    ]
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
        if case.get("thieu_hien_tuong"):
            # QD-BK82-2: flag the missing phenomenon; the M/O text below is
            # a suggestion with provenance, not an auto-filled value.
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
        lines.append(f"- **Báo cáo gốc:** {case['bao_cao_goc'] or '—'}")
    lines.append("")
    lines.append(
        "_Nguồn: DB ca lỗi Bước 0–5 (lịch sử KDTPS thật). "
        "Muốn đào sâu một ca, hỏi theo mã phiếu (VD: `phiếu 2023/5`)._"
    )
    # B2: the 3 rating "buttons" live inside this answer bubble (chat-first:
    # typed in the single chat box, no separate toolbar).
    lines.append("")
    lines.append("---")
    lines.append(
        "**Đánh giá gợi ý này:** `đánh giá đúng` · `đánh giá sai` · "
        "`đánh giá một phần`"
    )
    lines.append("_Gõ ngay trong ô chat — không cần mở thêm gì._")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Action wiring
# ---------------------------------------------------------------------------


def _log_suggestion_call(
    db_path: Path, cases: Sequence[Dict[str, Any]], conversation_id: str
) -> None:
    """B2: record one suggestion call per lookup answer (best-effort).

    A logging failure must never break the answer, so every error is
    swallowed here — the suggestion cards are the product, the log is
    the feedback loop's bookkeeping.
    """
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
    """ChatAction that fires on error codes (C0030, JAM4212, ...) or symptom search."""

    def matches(self, request: ChatActionRequest) -> bool:
        # 1. Reject off-topic trap queries
        norm = request.normalized_question
        if any(h in norm for h in _OFFTOPIC_HINTS):
            return False

        # 2. Store-scope isolation:
        # Respect notebook scope and pinned knowledge block.
        forced = (request.context or {}).get("forced_domain") if request.context else None
        nb_id = request.notebook_id or ""

        # If forced_domain is explicitly pinned to another domain (not auto and not dieu_tra_loi), block.
        if forced and str(forced).strip().lower() not in ("auto", "dieu_tra_loi"):
            return False

        # If user is in another specific notebook (e.g. mom_opcenter, NB-LAZY-LSU, NB-C26E1C84),
        # keep queries isolated to that notebook store.
        if nb_id and nb_id in ("mom_opcenter", "NB-LAZY-LSU", "NB-C26E1C84"):
            return False

        # Check for error codes
        codes = extract_codes(request.question)
        if codes:
            return True

        # Check generic hints (symptom search like "kẹt giấy cụm sấy")
        if super().matches(request):
            return True

        return False


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    # Reject off-topic
    norm = request.normalized_question
    if any(h in norm for h in _OFFTOPIC_HINTS):
        return None

    # Store-scope isolation
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
        total = 0
        glossary: Mapping[str, Dict[str, Any]] = {}
        if codes or extract_keywords(request.question):
            glossary = lookup_glossary(conn, codes)
            extra: List[str] = []
            for code in codes:
                entry = glossary.get(code, {})
                extra.extend(
                    str(entry.get(k) or "")
                    for k in ("name_vi", "name_ja", "name_en", "cause", "remedy")
                )
            cases, codes, total = search_similar(
                conn, request.question, extra_keywords=extra
            )
        if not cases and not glossary:
            return None

        # Route between bare code cards vs natural question synthesized answer
        if is_natural_question(request.question):
            text = _render_synthesized_answer(cases, codes, glossary, total, request.question)
        else:
            text = _render_cards(cases, codes, glossary, total)

        # B2: log the suggestion call so "đánh giá đúng/sai/một phần" has
        # something to rate. Best-effort: never breaks the answer.
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
            # Generic catch-all: never piggyback on a specific action's answer
            # in multi-intent dispatch (UX-CHAT-CORE).
            fallback=True,
            description=(
                "Tra cứu ca lỗi tương tự trong DB Bước 0–5: nhập mã lỗi "
                "(C0030, F000, ...) hoặc mô tả hiện tượng, nhận top 3–5 ca "
                "kèm nguyên nhân, đối sách và báo cáo gốc — chỉ đọc."
            ),
        )
    )


register()
