"""Step 2 / B2: feedback loop for error-case suggestions.

After each suggestion call, the user rates it: dung / sai / mot_phan
(correct / wrong / partially correct). When closing an error ticket,
the ACTUAL root cause and countermeasure must be entered; they are
written back into the knowledge store (error_cases.investigation).

B2 hard rules (ticket B2 + QD-BK82-1, 2026-10-01):
- close_case is BLOCKED unless the actual root cause and the actual
  countermeasure are provided (non-blank).
- For NEW cases (FORM tickets, or YYYY/NNNN tickets from 2026 onward),
  closing additionally requires the phenomenon (hien tuong) and the
  process stage (cong doan): from the stored row or supplied at close
  time (written back, never auto-inferred from other columns).
- QD-BK82-2: legacy rows with no recorded phenomenon get the
  hientuong_missing='1' flag; M/O investigation text is surfaced as a
  suggestion WITH provenance, never auto-filled.

This module only *reads* store.py/schema.sql contracts and adds its
own tables/columns; it never modifies existing modules.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

# Public rating labels (Vietnamese domain terms, kept as constants).
RATING_CORRECT = "đúng"
RATING_WRONG = "sai"
RATING_PARTIAL = "một phần"
RATINGS = (RATING_CORRECT, RATING_WRONG, RATING_PARTIAL)
_POSITIVE_RATINGS = (RATING_CORRECT, RATING_PARTIAL)

_FEEDBACK_SCHEMA = """
CREATE TABLE IF NOT EXISTS suggestion_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id         INTEGER NOT NULL REFERENCES error_cases (id),
    suggested_at    TEXT NOT NULL DEFAULT (datetime('now')),
    suggested_refs  TEXT NOT NULL DEFAULT '[]',  -- JSON list of suggested case refs
    note            TEXT NOT NULL DEFAULT '',
    conversation_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS suggestion_ratings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id     INTEGER NOT NULL REFERENCES suggestion_calls (id),
    rating      TEXT NOT NULL CHECK (rating IN ('đúng', 'sai', 'một phần')),
    rated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    rater       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS case_closures (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id              INTEGER NOT NULL UNIQUE REFERENCES error_cases (id),
    actual_cause         TEXT NOT NULL,  -- nguyen nhan that (mandatory)
    actual_countermeasure TEXT NOT NULL, -- doi sach that (mandatory)
    closed_at            TEXT NOT NULL DEFAULT (datetime('now')),
    closed_by            TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_suggestion_calls_case
    ON suggestion_calls (case_id);
CREATE INDEX IF NOT EXISTS idx_suggestion_calls_conversation
    ON suggestion_calls (conversation_id);
CREATE INDEX IF NOT EXISTS idx_suggestion_ratings_call
    ON suggestion_ratings (call_id);
"""

# Blank definition per BK-82 (source-verified): null / empty / whitespace /
# placeholder dashes used in the real workbook.
_PLACEHOLDER_MARKS = frozenset(
    {"ー", "－", "—", "–", "-", "--", "/", "//", "ｰ", "‐", "−"}
)

#: Public alias: values that count as "not recorded" for free-text fields.
BLANK_MARKS = _PLACEHOLDER_MARKS

# QD-BK82-1: tickets from this year onward are "new" and must be complete
# at close time (no retroactive auto-fill for legacy rows).
_NEW_CASE_CUTOFF_YEAR = 2026
_RE_TICKET_YEAR = re.compile(r"^(20\d{2})/")

# Columns close_case may write back (blank-fill only, never overwrite).
_CLOSE_FILL_COLUMNS = (
    ("phenomenon", "TEXT"),
    ("process_stage", "TEXT"),
    ("cause", "TEXT"),
    ("countermeasure", "TEXT"),
    ("closed_at", "TEXT"),
    ("hientuong_missing", "TEXT"),
)


class ClosureBlockedError(ValueError):
    """Raised when a ticket cannot be closed (missing mandatory close fields)."""


def _is_blank_text(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text in _PLACEHOLDER_MARKS


def _ensure_feedback_migrations(conn: sqlite3.Connection) -> None:
    """Additive migrations for feedback tables created by an older version."""
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='suggestion_calls'"
    ).fetchone()
    if not table_exists:
        # Fresh DB (or schema script not run yet): CREATE TABLE IF NOT EXISTS
        # in _FEEDBACK_SCHEMA carries the latest columns already.
        return
    cols = {
        row[1] for row in conn.execute("PRAGMA table_info(suggestion_calls)")
    }
    if "conversation_id" not in cols:
        conn.execute("ALTER TABLE suggestion_calls ADD COLUMN conversation_id TEXT")
        conn.execute(
            "UPDATE suggestion_calls SET conversation_id = '' "
            "WHERE conversation_id IS NULL"
        )
    conn.commit()


def init_feedback_loop(conn: sqlite3.Connection) -> None:
    """Create feedback tables idempotently (requires error_cases schema first).

    Migrations run BEFORE the schema script: the script creates an index on
    suggestion_calls(conversation_id), which old DBs lack — the migration adds
    that column first so the index creation cannot fail.
    """
    _ensure_feedback_migrations(conn)
    conn.executescript(_FEEDBACK_SCHEMA)
    conn.commit()


def _ensure_close_columns(conn: sqlite3.Connection) -> None:
    """Ensure every column close_case may write back exists (old DBs)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(error_cases)")}
    for name, ddl in _CLOSE_FILL_COLUMNS:
        if name not in cols:
            conn.execute(f"ALTER TABLE error_cases ADD COLUMN {name} {ddl}")
    conn.commit()


def _safe_col(row: sqlite3.Row, name: str) -> str:
    """Read a possibly-missing column as stripped text (old-schema safe)."""
    try:
        return str(row[name] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _raw_json_of(row: sqlite3.Row) -> Dict[str, object]:
    import json

    try:
        data = json.loads(_safe_col(row, "raw_json") or "{}")
    except (ValueError, TypeError):
        data = {}
    return data if isinstance(data, dict) else {}


def log_suggestion_call(
    conn: sqlite3.Connection,
    case_id: int,
    *,
    suggested_refs: Optional[List[str]] = None,
    note: str = "",
    suggested_at: Optional[str] = None,
    conversation_id: str = "",
) -> int:
    """Log one suggestion call for a case; returns the call id."""
    import json

    cur = conn.execute(
        """INSERT INTO suggestion_calls
           (case_id, suggested_at, suggested_refs, note, conversation_id)
           VALUES (?, ?, ?, ?, ?)""",
        (
            case_id,
            suggested_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(suggested_refs or [], ensure_ascii=False),
            note,
            conversation_id or "",
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def latest_suggestion_call(
    conn: sqlite3.Connection, conversation_id: Optional[str] = None
) -> Optional[sqlite3.Row]:
    """Newest suggestion call, optionally scoped to one conversation."""
    if conversation_id:
        return conn.execute(
            "SELECT * FROM suggestion_calls WHERE conversation_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (conversation_id,),
        ).fetchone()
    return conn.execute(
        "SELECT * FROM suggestion_calls ORDER BY id DESC LIMIT 1"
    ).fetchone()


def latest_unrated_suggestion_call(
    conn: sqlite3.Connection, conversation_id: Optional[str] = None
) -> Optional[sqlite3.Row]:
    """Newest suggestion call that has no rating yet (per conversation)."""
    sql = (
        "SELECT c.* FROM suggestion_calls c "
        "WHERE NOT EXISTS (SELECT 1 FROM suggestion_ratings r "
        "WHERE r.call_id = c.id)"
    )
    params: List[object] = []
    if conversation_id:
        sql += " AND c.conversation_id = ?"
        params.append(conversation_id)
    sql += " ORDER BY c.id DESC LIMIT 1"
    return conn.execute(sql, params).fetchone()


def get_ratings(conn: sqlite3.Connection, call_id: int) -> List[sqlite3.Row]:
    """All ratings for one suggestion call, oldest first."""
    return list(
        conn.execute(
            "SELECT * FROM suggestion_ratings WHERE call_id = ? ORDER BY id",
            (call_id,),
        ).fetchall()
    )


def record_rating(
    conn: sqlite3.Connection,
    call_id: int,
    rating: str,
    *,
    rater: str = "",
    rated_at: Optional[str] = None,
) -> int:
    """Save a user rating for a suggestion call; returns the rating id."""
    if rating not in RATINGS:
        raise ValueError(f"rating must be one of {RATINGS}, got {rating!r}")
    cur = conn.execute(
        """INSERT INTO suggestion_ratings (call_id, rating, rated_at, rater)
           VALUES (?, ?, ?, ?)""",
        (
            call_id,
            rating,
            rated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            rater,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def _is_new_case(conn: sqlite3.Connection, case_id: int) -> bool:
    """QD-BK82-1: a case counts as "new" (must be complete at close).

    New = created through the B0-FORM entry form (FORM- ticket numbers),
    or a YYYY/NNNN history ticket from the cutoff year onward. Legacy
    rows keep the no-retroactive-fill rule and get the hientuong_missing
    flag instead (QD-BK82-2).
    """
    row = conn.execute(
        "SELECT no_dvd FROM error_cases WHERE id = ?", (case_id,)
    ).fetchone()
    if row is None:
        return False
    no_dvd = _safe_col(row, "no_dvd")
    if no_dvd.startswith("FORM-"):
        return True
    match = _RE_TICKET_YEAR.match(no_dvd)
    return bool(match and int(match.group(1)) >= _NEW_CASE_CUTOFF_YEAR)


def _effective_phenomenon(row: sqlite3.Row, supplied: Optional[str]) -> str:
    """Phenomenon available at close: supplied > column > legacy raw I."""
    if not _is_blank_text(supplied):
        return str(supplied).strip()
    if not _is_blank_text(_safe_col(row, "phenomenon")):
        return _safe_col(row, "phenomenon")
    raw_i = str(_raw_json_of(row).get("I") or "").strip()
    return "" if _is_blank_text(raw_i) else raw_i


def _effective_process_stage(row: sqlite3.Row, supplied: Optional[str]) -> str:
    """Process stage available at close: supplied > column > legacy raw F."""
    if not _is_blank_text(supplied):
        return str(supplied).strip()
    if not _is_blank_text(_safe_col(row, "process_stage")):
        return _safe_col(row, "process_stage")
    raw_f = str(_raw_json_of(row).get("F") or "").strip()
    return "" if _is_blank_text(raw_f) else raw_f


def close_case(
    conn: sqlite3.Connection,
    case_id: int,
    *,
    actual_cause: str,
    actual_countermeasure: str,
    closed_by: str = "",
    phenomenon: Optional[str] = None,
    process_stage: Optional[str] = None,
) -> int:
    """Close an error ticket.

    HARD RULES (ticket B2 + QD-BK82-1):
    - BLOCKED unless both the actual root cause and the actual
      countermeasure are provided (non-blank).
    - For NEW cases, BLOCKED unless the phenomenon and the process stage
      are also known (stored row or supplied here; supplied values are
      written back, never inferred from other columns).

    On success the actuals are written back into the knowledge store:
    case_closures row + error_cases.investigation (with a [Thực tế]
    provenance marker) + blank-fill of the cause / countermeasure /
    phenomenon / process_stage / closed_at columns + is_completed='o'.
    Existing values are never overwritten. Returns the closure id.
    """
    if _is_blank_text(actual_cause):
        raise ClosureBlockedError(
            "Không đóng được phiếu: thiếu nguyên nhân thật (actual_cause)."
        )
    if _is_blank_text(actual_countermeasure):
        raise ClosureBlockedError(
            "Không đóng được phiếu: thiếu đối sách thật (actual_countermeasure)."
        )
    _ensure_close_columns(conn)
    row = conn.execute(
        "SELECT * FROM error_cases WHERE id = ?", (case_id,)
    ).fetchone()
    if row is None:
        raise ClosureBlockedError(f"Không đóng được phiếu: không tìm thấy ca id={case_id}.")
    if _is_new_case(conn, case_id):
        missing: List[str] = []
        if not _effective_phenomenon(row, phenomenon):
            missing.append("Hiện tượng")
        if not _effective_process_stage(row, process_stage):
            missing.append("Công đoạn")
        if missing:
            raise ClosureBlockedError(
                "Không đóng được phiếu: phiếu mới bắt buộc nhập thêm "
                + " và ".join(missing)
                + " khi đóng (quy ước BK-82: không bù ngược tự động)."
            )
    cur = conn.execute(
        """INSERT INTO case_closures
           (case_id, actual_cause, actual_countermeasure, closed_by)
           VALUES (?, ?, ?, ?)
           ON CONFLICT (case_id) DO UPDATE SET
             actual_cause = excluded.actual_cause,
             actual_countermeasure = excluded.actual_countermeasure,
             closed_at = datetime('now'),
             closed_by = excluded.closed_by""",
        (
            case_id,
            str(actual_cause).strip(),
            str(actual_countermeasure).strip(),
            closed_by,
        ),
    )
    conn.commit()
    closure_id = int(cur.lastrowid) if cur.lastrowid else int(
        conn.execute(
            "SELECT id FROM case_closures WHERE case_id = ?", (case_id,)
        ).fetchone()["id"]
    )
    # Write back into the knowledge store: keep provenance, update the
    # investigation text with the verified actual cause + countermeasure.
    prior = _safe_col(row, "investigation")
    actuals = (
        f"[Thực tế] Nguyên nhân: {str(actual_cause).strip()} | "
        f"Đối sách: {str(actual_countermeasure).strip()}"
    )
    merged = f"{prior}\n{actuals}" if prior else actuals
    # Blank-fill the dedicated columns (never overwrite a stored value).
    fills: Dict[str, str] = {}
    if not _safe_col(row, "cause"):
        fills["cause"] = str(actual_cause).strip()
    if not _safe_col(row, "countermeasure"):
        fills["countermeasure"] = str(actual_countermeasure).strip()
    if not _is_blank_text(phenomenon) and not _safe_col(row, "phenomenon"):
        fills["phenomenon"] = str(phenomenon).strip()
    if not _is_blank_text(process_stage) and not _safe_col(row, "process_stage"):
        fills["process_stage"] = str(process_stage).strip()
    if not _safe_col(row, "closed_at"):
        fills["closed_at"] = date.today().isoformat()
    set_clause = ", ".join(["investigation = ?"] + [f"{k} = ?" for k in fills])
    set_clause += ", is_completed = 'o', updated_at = datetime('now')"
    conn.execute(
        f"UPDATE error_cases SET {set_clause} WHERE id = ?",
        [merged, *fills.values(), case_id],
    )
    conn.commit()
    return closure_id


def get_closure(conn: sqlite3.Connection, case_id: int) -> Optional[sqlite3.Row]:
    """Return the closure row for a case, or None if not closed."""
    return conn.execute(
        "SELECT * FROM case_closures WHERE case_id = ?", (case_id,)
    ).fetchone()


def phenomenon_state(conn: sqlite3.Connection, case_id: int) -> Dict[str, object]:
    """QD-BK82-2: where a case's phenomenon stands.

    Returns {"has_phenomenon", "source" ("phenomenon" | "raw_I" | None),
    "missing", "suggested_text", "suggested_source" ("M" | "O" | None)}.
    The M/O suggestion carries provenance and is NEVER auto-filled into
    the phenomenon field.
    """
    row = conn.execute(
        "SELECT * FROM error_cases WHERE id = ?", (case_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"no error_cases row id={case_id}")
    has_col = not _is_blank_text(_safe_col(row, "phenomenon"))
    raw = _raw_json_of(row)
    raw_i = str(raw.get("I") or "").strip()
    has_i = not _is_blank_text(raw_i)
    suggested_text: Optional[str] = None
    suggested_source: Optional[str] = None
    for key in ("M", "O"):
        text = str(raw.get(key) or "").strip()
        if not _is_blank_text(text):
            suggested_text, suggested_source = text, key
            break
    return {
        "case_id": case_id,
        "has_phenomenon": bool(has_col or has_i),
        "source": "phenomenon" if has_col else ("raw_I" if has_i else None),
        "missing": not (has_col or has_i),
        "suggested_text": suggested_text,
        "suggested_source": suggested_source,
    }


def flag_hientuong_missing(
    conn: sqlite3.Connection, case_id: Optional[int] = None
) -> int:
    """Persist the QD-BK82-2 flag: hientuong_missing='1' where the
    phenomenon is not recorded (cleared otherwise). Scopes to one case
    when case_id is given, else the whole table. Returns flagged count.
    """
    _ensure_close_columns(conn)
    if case_id is not None:
        ids = [case_id]
    else:
        ids = [r["id"] for r in conn.execute("SELECT id FROM error_cases")]
    flagged = 0
    for cid in ids:
        missing = bool(phenomenon_state(conn, int(cid))["missing"])
        conn.execute(
            "UPDATE error_cases SET hientuong_missing = ? WHERE id = ?",
            ("1" if missing else "", cid),
        )
        flagged += 1 if missing else 0
    conn.commit()
    return flagged


def rating_coverage(conn: sqlite3.Connection) -> Dict[str, float]:
    """Share of suggestion calls that received at least one rating.

    Target per spec: >= 80%.
    Returns {"calls": n, "rated": m, "coverage": m/n}.
    """
    row = conn.execute(
        """SELECT COUNT(DISTINCT c.id) AS calls,
                  COUNT(DISTINCT r.call_id) AS rated
           FROM suggestion_calls c
           LEFT JOIN suggestion_ratings r ON r.call_id = c.id"""
    ).fetchone()
    calls, rated = int(row["calls"]), int(row["rated"])
    return {
        "calls": calls,
        "rated": rated,
        "coverage": (rated / calls) if calls else 0.0,
    }


def _quarter_of(ts: str) -> str:
    dt = datetime.strptime(ts[:10], "%Y-%m-%d")
    return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"


def positive_rate_by_quarter(conn: sqlite3.Connection) -> Dict[str, Dict[str, float]]:
    """Per-quarter share of rated calls whose latest rating is correct/partial.

    Returns {quarter: {"rated": n, "positive": m, "rate": m/n}}.
    """
    rows = conn.execute(
        """SELECT c.id AS call_id, c.suggested_at AS ts, r.rating AS rating,
                  r.rated_at AS rated_at
           FROM suggestion_calls c
           JOIN suggestion_ratings r ON r.call_id = c.id
           ORDER BY c.id, r.rated_at DESC, r.id DESC"""
    ).fetchall()
    latest: Dict[int, tuple] = {}
    for row in rows:
        if int(row["call_id"]) not in latest:
            latest[int(row["call_id"])] = (row["ts"], row["rating"])
    buckets: Dict[str, Dict[str, int]] = {}
    for ts, rating in latest.values():
        q = _quarter_of(ts)
        b = buckets.setdefault(q, {"rated": 0, "positive": 0})
        b["rated"] += 1
        if rating in _POSITIVE_RATINGS:
            b["positive"] += 1
    return {
        q: {
            "rated": b["rated"],
            "positive": b["positive"],
            "rate": (b["positive"] / b["rated"]) if b["rated"] else 0.0,
        }
        for q, b in sorted(buckets.items())
    }
