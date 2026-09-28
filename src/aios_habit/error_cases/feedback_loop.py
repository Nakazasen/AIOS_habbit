"""Step 2: feedback loop for error-case suggestions.

After each suggestion call, the user rates it: dung / sai / mot_phan
(correct / wrong / partially correct). When closing an error ticket,
the ACTUAL root cause and countermeasure must be entered; they are
written back into the knowledge store (error_cases.investigation).

This module only *reads* store.py/schema.sql contracts and adds its
own tables; it never modifies existing modules.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
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
    note            TEXT NOT NULL DEFAULT ''
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
CREATE INDEX IF NOT EXISTS idx_suggestion_ratings_call
    ON suggestion_ratings (call_id);
"""


class ClosureBlockedError(ValueError):
    """Raised when a ticket cannot be closed (missing actual cause/countermeasure)."""


def init_feedback_loop(conn: sqlite3.Connection) -> None:
    """Create feedback tables idempotently (requires error_cases schema first)."""
    conn.executescript(_FEEDBACK_SCHEMA)
    conn.commit()


def log_suggestion_call(
    conn: sqlite3.Connection,
    case_id: int,
    *,
    suggested_refs: Optional[List[str]] = None,
    note: str = "",
    suggested_at: Optional[str] = None,
) -> int:
    """Log one suggestion call for a case; returns the call id."""
    import json

    cur = conn.execute(
        """INSERT INTO suggestion_calls (case_id, suggested_at, suggested_refs, note)
           VALUES (?, ?, ?, ?)""",
        (
            case_id,
            suggested_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(suggested_refs or [], ensure_ascii=False),
            note,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


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


def close_case(
    conn: sqlite3.Connection,
    case_id: int,
    *,
    actual_cause: str,
    actual_countermeasure: str,
    closed_by: str = "",
) -> int:
    """Close an error ticket.

    BLOCKED unless both the actual root cause and the actual
    countermeasure are provided (non-blank). On success the values are
    written back into error_cases.investigation ("ghi ngược lại kho tri thức").
    Returns the closure id.
    """
    if not (actual_cause or "").strip():
        raise ClosureBlockedError(
            "Không đóng được phiếu: thiếu nguyên nhân thật (actual_cause)."
        )
    if not (actual_countermeasure or "").strip():
        raise ClosureBlockedError(
            "Không đóng được phiếu: thiếu đối sách thật (actual_countermeasure)."
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
        (case_id, actual_cause.strip(), actual_countermeasure.strip(), closed_by),
    )
    conn.commit()
    closure_id = int(cur.lastrowid) if cur.lastrowid else int(
        conn.execute(
            "SELECT id FROM case_closures WHERE case_id = ?", (case_id,)
        ).fetchone()["id"]
    )
    # Write back into the knowledge store: keep provenance, update the
    # investigation text with the verified actual cause + countermeasure.
    row = conn.execute(
        "SELECT investigation FROM error_cases WHERE id = ?", (case_id,)
    ).fetchone()
    prior = (row["investigation"] or "").strip() if row else ""
    merged = (
        f"{prior}\n[Thực tế] Nguyên nhân: {actual_cause.strip()} | "
        f"Đối sách: {actual_countermeasure.strip()}"
        if prior
        else f"[Thực tế] Nguyên nhân: {actual_cause.strip()} | "
        f"Đối sách: {actual_countermeasure.strip()}"
    )
    conn.execute(
        """UPDATE error_cases
           SET investigation = ?, is_completed = 'o', updated_at = datetime('now')
           WHERE id = ?""",
        (merged, case_id),
    )
    conn.commit()
    return closure_id


def get_closure(conn: sqlite3.Connection, case_id: int) -> Optional[sqlite3.Row]:
    """Return the closure row for a case, or None if not closed."""
    return conn.execute(
        "SELECT * FROM case_closures WHERE case_id = ?", (case_id,)
    ).fetchone()


def rating_coverage(conn: sqlite3.Connection) -> Dict[str, float]:
    """Share of suggestion calls that received at least one rating.

    Target per spec: >= 80%.
    Returns {"calls": n, "rated": m, "coverage": m/n}.
    """
    row = conn.execute(
        """SELECT COUNT(*) AS calls,
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
