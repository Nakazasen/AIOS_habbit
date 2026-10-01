"""Step 5: automatic classification + recurrence alert for new error cases.

Rule-based classifier over the F4 glossary + keyword tables, history
matching against the F1 ``error_cases`` store, and recurrence detection
inside a time window. No ML, no external calls; everything runs on
SQLite + in-process rules.

Ticket labels (Vietnamese) — per ve B5 (lắp ráp – thiết kế – linh kiện – khác):
  nhom_nguyen_nhan: 'lap_rap' (assembly) | 'thiet_ke' (design) |
                    'linh_kien' (component) | 'khac' (other)
  cong_doan: production stage label (may be None when unknown)
  bo_phan: responsible department label (may be None when unknown)

Every new error is *always* compared against history (match_history
never returns None -- an empty list means "no similar record found").
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .glossary import (
    canonical_term as glossary_canonical_term,
    lookup as glossary_lookup,
    norm_code,
)

# ---------------------------------------------------------------------------
# Label tables
# ---------------------------------------------------------------------------

CAUSE_GROUPS = ("lap_rap", "thiet_ke", "linh_kien", "khac")

CAUSE_LABEL_VI = {
    "lap_rap": "Lắp ráp",
    "thiet_ke": "Thiết kế",
    "linh_kien": "Linh kiện",
    "khac": "Khác",
}

# keyword -> cause group. Matched against the lowercased, NFKC-normalized
# concatenation of error code + phenomenon + investigation (+ glossary text
# when available). Scoring counts hits per group; the max wins.
# Table order = tie-break priority: lap_rap first, then thiet_ke, linh_kien.
#
# Term selection (B5, 2026-10-01): every term below was precision-gated on
# the TRAIN split (80%) of the 15,707 real History KDTPS cases, ground truth
# = column AA (要因/Nguyen nhan) mapped to the 4 ticket groups. Only terms
# with train precision >= 0.60 and support >= 8 were kept:
#   linh_kien: 交換で再現 0.72, サプライヤー 0.66, ベンダー 0.77,
#              発生基板 0.60, supplier 0.75,
#              サプライヤーに調査依頼 0.88, ベンダーに調査依頼 0.91,
#              単品部品確認 0.83, 部品のエラー 0.75, 外製品質管理 0.86,
#              に連携し選別 0.93, 調査依頼済み 0.92
#   thiet_ke:  設計要因 0.73
# Deliberately excluded: generic part words (部品/交換/基板/linh kiện/
# sensor/hỏng/...) — train precision 0.14-0.30, they fire on process
# boilerplate (lien he/dieu tra/水平展開) and collapse khac accuracy.
#
# Known limitation (documented, not hidden): no text term predicts the
# 'lap_rap' (組立) group with usable precision on real data (best candidate
# 外れた: 0.38). Assembly cause is determined during physical investigation,
# not from the phenomenon text, so the keyword table has no lap_rap entry:
# such cases fall back to 'khac' with low confidence and the entry form
# asks the reporter to confirm the group by hand.
CAUSE_KEYWORDS: Dict[str, List[str]] = {
    "lap_rap": [],
    "thiet_ke": ["設計要因"],
    "linh_kien": [
        "交換で再現", "サプライヤー", "ベンダー", "発生基板", "supplier",
        "サプライヤーに調査依頼", "ベンダーに調査依頼", "単品部品確認",
        "部品のエラー", "外製品質管理", "に連携し選別", "調査依頼済み",
    ],
}

DEPT_KEYWORDS: Dict[str, List[str]] = {
    "Điện": [
        "điện", "sensor", "cảm biến", "motor", "động cơ", "mạch",
        "board", "nguồn điện", "dây điện", "chập", "mất nguồn",
    ],
    "Cơ khí": [
        "cơ khí", "trục", "bánh răng", "vít", "ốc", "khớp nối",
        "vòng bi", "bearing", "dây đai", "belt", "kẹt cơ",
    ],
    "Thiết kế": ["thiết kế", "thiet ke", "設計", "bản vẽ", "ban ve", "design"],
    "Chất lượng": ["chất lượng", "qc", "không đạt", "ng ", "ngoại quan"],
    "Kỹ thuật": ["kỹ thuật", "căn chỉnh", "calibration", "hiệu chuẩn"],
    "Vận hành": ["vận hành", "thao tác", "operation", "người vận hành"],
    "Bảo trì": ["bảo trì", "bảo dưỡng", "maintenance", "vệ sinh máy"],
}

STAGE_KEYWORDS: Dict[str, List[str]] = {
    "Lắp ráp": ["lắp ráp", "assembly"],
    "Kiểm tra": ["kiểm tra", "kiểm tra chất lượng", "test", "đo đạc",
                 "inspection"],
    "Điều chỉnh": ["điều chỉnh", "adjust", "căn chỉnh", "calibration",
                   "hiệu chuẩn"],
    "Vận hành": ["vận hành", "chạy máy", "operation"],
    "In ấn": ["in ấn", "print", "kẹt giấy", "paper jam"],
    "Bảo trì": ["bảo trì", "bảo dưỡng"],
}

# Conservative defaults when the code family is known but no keyword hits.
# (Printer company domain: Máy in / KIT.)
FAMILY_DEFAULTS: Dict[str, Dict[str, str]] = {
    "C_CALL": {"bo_phan": "Bảo trì", "cong_doan": "Vận hành"},
    "F_SYSTEM": {"bo_phan": "Điện", "cong_doan": "Vận hành"},
    "JAM": {"bo_phan": "Vận hành", "cong_doan": "In ấn"},
    "SCT_ADJ": {"bo_phan": "Kỹ thuật", "cong_doan": "Điều chỉnh"},
}

_FAMILY_PATTERNS = (
    ("C_CALL", re.compile(r"C\d{4}")),
    ("F_SYSTEM", re.compile(r"F[0-9A-FX]{3,4}")),
    ("JAM", re.compile(r"[0-9A-F]{4}")),
    ("SCT_ADJ", re.compile(r"[0-9A-F]{2}")),
)


def detect_family(code: str) -> Optional[str]:
    """Guess the glossary code family from the code shape (may be None)."""
    c = norm_code(code)
    for family, pattern in _FAMILY_PATTERNS:
        if pattern.fullmatch(c):
            return family
    return None


def _norm_text(*parts: Any) -> str:
    text = " ".join("" if p is None else str(p) for p in parts)
    return unicodedata.normalize("NFKC", text).lower()


def _score_keywords(text: str, table: Dict[str, List[str]]) -> Dict[str, int]:
    return {
        label: sum(1 for kw in keywords if kw in text)
        for label, keywords in table.items()
    }


def _pick_best(scores: Dict[str, int]) -> tuple[Optional[str], int]:
    best_label: Optional[str] = None
    best_hits = 0
    for label, hits in scores.items():  # table order = tie-break priority
        if hits > best_hits:
            best_label, best_hits = label, hits
    return best_label, best_hits


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class Classification:
    error_code: str
    code_family: Optional[str]
    nhom_nguyen_nhan: str
    cong_doan: Optional[str]
    bo_phan: Optional[str]
    confidence: float  # 0..1
    reasons: List[str] = field(default_factory=list)  # Vietnamese audit trail


@dataclass
class HistoryMatch:
    case: Dict[str, Any]
    score: float
    matched_on: List[str] = field(default_factory=list)  # Vietnamese


@dataclass
class RecurrenceAlert:
    code: str
    count: int            # occurrences inside the window, incl. the new one
    window_hours: float
    message_vi: str       # e.g. "Tái phát: mã C0030 đã phát sinh 3 lần ..."
    suggested_remedy: Optional[str] = None
    suggested_from: Optional[str] = None  # no_dvd of the source record


# ---------------------------------------------------------------------------
# 1. Classification
# ---------------------------------------------------------------------------

def classify_error(
    error_code: str,
    phenomenon: str = "",
    investigation: str = "",
    machine_type: Optional[str] = None,
    line: Optional[str] = None,
    glossary_conn: Optional[sqlite3.Connection] = None,
) -> Classification:
    """Auto-assign cause group / stage / department for a new error.

    Never raises on unknown input: unrecognized codes fall back to
    nhom_nguyen_nhan='khac' with low confidence.
    """
    code = norm_code(error_code)
    family = detect_family(code)
    reasons: List[str] = []

    glossary_text = ""
    if glossary_conn is not None:
        if family is None:
            # B0-DICT: the token may be a variant name spelling rather than
            # a code (e.g. copied from a workbook); resolve via the alias
            # index before giving up.
            alias = glossary_canonical_term(glossary_conn, error_code)
            if alias is not None:
                family, code = alias
                reasons.append(
                    f"Chuẩn hóa tên gọi: '{error_code}' -> {family} {code}."
                )
        if family is not None:
            entry = glossary_lookup(glossary_conn, family, code)
            if entry:
                glossary_text = " ".join(
                    str(entry.get(k) or "")
                    for k in ("name_vi", "name_en", "name_ja", "cause", "remedy")
                )
                reasons.append(
                    f"Tra cứu glossary: {family} {code} có trong từ điển mã lỗi."
                )
            else:
                reasons.append(
                    f"Mã {code} (nhóm {family}) không có trong từ điển mã lỗi."
                )
        else:
            reasons.append(f"Không nhận dạng được nhóm mã từ '{error_code}'.")
    elif family is not None:
        reasons.append(f"Nhận dạng nhóm mã: {family} (theo hình thức mã).")
    else:
        reasons.append(f"Không nhận dạng được nhóm mã từ '{error_code}'.")

    text = _norm_text(code, phenomenon, investigation, glossary_text)

    # --- cause group ---
    cause_scores = _score_keywords(text, CAUSE_KEYWORDS)
    cause_group, cause_hits = _pick_best(cause_scores)
    if cause_group is None:
        cause_group = "khac"
        cause_conf = 0.35
        reasons.append("Không khớp từ khóa nguyên nhân nào → nhóm 'Khác'.")
    else:
        cause_conf = min(0.95, 0.55 + 0.10 * (cause_hits - 1))
        reasons.append(
            f"Nhóm nguyên nhân '{CAUSE_LABEL_VI[cause_group]}': "
            f"khớp {cause_hits} từ khóa."
        )

    # --- department / stage: keyword override wins, else family default ---
    dept_scores = _score_keywords(text, DEPT_KEYWORDS)
    stage_scores = _score_keywords(text, STAGE_KEYWORDS)
    dept_kw, dept_hits = _pick_best(dept_scores)
    stage_kw, stage_hits = _pick_best(stage_scores)

    defaults = FAMILY_DEFAULTS.get(family or "", {})
    if dept_kw is not None:
        bo_phan: Optional[str] = dept_kw
        reasons.append(f"Bộ phận '{dept_kw}': khớp {dept_hits} từ khóa.")
    else:
        bo_phan = defaults.get("bo_phan")
        if bo_phan:
            reasons.append(
                f"Bộ phận '{bo_phan}': mặc định theo nhóm mã {family}."
            )
    if stage_kw is not None:
        cong_doan: Optional[str] = stage_kw
        reasons.append(f"Công đoạn '{stage_kw}': khớp {stage_hits} từ khóa.")
    else:
        cong_doan = defaults.get("cong_doan")
        if cong_doan:
            reasons.append(
                f"Công đoạn '{cong_doan}': mặc định theo nhóm mã {family}."
            )

    confidence = round(min(cause_conf, 0.95), 2)
    return Classification(
        error_code=code,
        code_family=family,
        nhom_nguyen_nhan=cause_group,
        cong_doan=cong_doan,
        bo_phan=bo_phan,
        confidence=confidence,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# 2. History matching (always runs: 100% of new errors are compared)
# ---------------------------------------------------------------------------

def _token_set(text: str) -> set:
    return {t for t in re.split(r"\W+", _norm_text(text)) if len(t) > 1}


def match_history(
    conn: sqlite3.Connection,
    error_code: str,
    machine_type: Optional[str] = None,
    line: Optional[str] = None,
    investigation: str = "",
    limit: int = 5,
) -> List[HistoryMatch]:
    """Return the most similar historical cases, best first.

    Always returns a list (possibly empty) -- the lookup itself is the
    "100% compared against history" criterion.
    """
    code = norm_code(error_code)
    try:
        rows = conn.execute(
            "SELECT * FROM error_cases ORDER BY id DESC LIMIT 5000"
        ).fetchall()
    except sqlite3.Error:
        return []

    new_tokens = _token_set(investigation)
    scored: List[HistoryMatch] = []
    for r in rows:
        row = dict(r)
        score = 0.0
        matched_on: List[str] = []
        row_c = norm_code(row.get("error_code_c"))
        row_h = norm_code(row.get("error_code_h"))
        # B5: history_29 rows keep the REAL code in error_code_i (extracted
        # from the phenomenon text); error_code_c is NULL and error_code_h
        # only holds the category ('F CALL', 'JAM', ...). Match it too.
        row_i = norm_code(row.get("error_code_i"))
        if code and (code == row_c or code == row_h or code == row_i):
            score += 10.0
            matched_on.append("mã lỗi trùng khớp")
        elif code and row_c and code[:1] == row_c[:1]:
            score += 2.0
            matched_on.append("cùng họ mã lỗi")
        if machine_type and row.get("machine_type") == machine_type:
            score += 2.0
            matched_on.append("cùng model máy")
        if line and row.get("line") == line:
            score += 2.0
            matched_on.append("cùng công đoạn/line")
        if new_tokens:
            row_tokens = _token_set(row.get("investigation"))
            if row_tokens:
                jaccard = len(new_tokens & row_tokens) / len(new_tokens | row_tokens)
                if jaccard > 0:
                    score += round(3.0 * jaccard, 2)
                    matched_on.append("nội dung điều tra tương đồng")
        if score > 0:
            scored.append(HistoryMatch(case=row, score=score,
                                      matched_on=matched_on))

    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[: max(0, limit)]


# ---------------------------------------------------------------------------
# 3. Recurrence detection
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def detect_recurrence(
    conn: sqlite3.Connection,
    error_code: str,
    window_hours: float = 12.0,
    threshold: int = 2,
    now: Optional[datetime] = None,
) -> Optional[RecurrenceAlert]:
    """Alert when the same code reappears inside the time window.

    The window ends at ``now`` (default: current time) and counts
    historical records by their occurrence time: ``occurred_at`` when the
    source carried a real date, else ``created_at`` (import time). Rows
    with a real date are day-granular in the source, so their window
    widens to the calendar days touched by [now - window, now]; rows
    without keep the exact timestamp window. The new case being entered
    counts as +1. Fires when total >= threshold (default 2 = recurring).
    """
    code = norm_code(error_code)
    ref = now or _utcnow()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    start = ref - timedelta(hours=window_hours)
    try:
        rows = conn.execute(
            """SELECT no_dvd, error_code_c, error_code_h, error_code_i,
                      investigation, created_at, occurred_at
               FROM error_cases
               WHERE (occurred_at IS NOT NULL
                      AND date(occurred_at) >= date(?)
                      AND date(occurred_at) <= date(?))
                  OR (occurred_at IS NULL
                      AND created_at >= ? AND created_at <= ?)
               ORDER BY COALESCE(occurred_at, created_at) DESC""",
            (
                start.strftime("%Y-%m-%d"),
                ref.strftime("%Y-%m-%d"),
                start.strftime("%Y-%m-%d %H:%M:%S"),
                ref.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ).fetchall()
    except sqlite3.Error:
        return None

    hits = [
        dict(r) for r in rows
        # B5: also match error_code_i — history_29 rows keep the real code
        # there (see match_history).
        if norm_code(r["error_code_c"]) == code
        or norm_code(r["error_code_h"]) == code
        or norm_code(r["error_code_i"]) == code
    ]
    total = len(hits) + 1  # +1 = the new case being entered
    if total < threshold:
        return None

    remedy: Optional[str] = None
    remedy_from: Optional[str] = None
    for h in hits:
        inv = (h.get("investigation") or "").strip()
        if inv:
            remedy = inv[:300]
            remedy_from = h.get("no_dvd")
            break

    if remedy:
        message_vi = (
            f"Tái phát: mã {code} đã phát sinh {total} lần trong "
            f"{window_hours:g} giờ qua. Đề xuất đối sách: {remedy}"
        )
    else:
        message_vi = (
            f"Tái phát: mã {code} đã phát sinh {total} lần trong "
            f"{window_hours:g} giờ qua. Chưa có đối sách trong lịch sử — "
            f"cần điều tra nguyên nhân gốc."
        )
    return RecurrenceAlert(
        code=code,
        count=total,
        window_hours=window_hours,
        message_vi=message_vi,
        suggested_remedy=remedy,
        suggested_from=remedy_from,
    )


# ---------------------------------------------------------------------------
# 4. Full pipeline for one new error
# ---------------------------------------------------------------------------

def classify_new_error(
    conn: sqlite3.Connection,
    error_code: str,
    phenomenon: str = "",
    investigation: str = "",
    machine_type: Optional[str] = None,
    line: Optional[str] = None,
    glossary_conn: Optional[sqlite3.Connection] = None,
    window_hours: float = 12.0,
    recurrence_threshold: int = 2,
) -> Dict[str, Any]:
    """Classify + compare against history + detect recurrence.

    Returns a dict with keys: classification, history_matches,
    recurrence_alert, history_checked (always True).
    """
    classification = classify_error(
        error_code,
        phenomenon=phenomenon,
        investigation=investigation,
        machine_type=machine_type,
        line=line,
        glossary_conn=glossary_conn,
    )
    history_matches = match_history(
        conn,
        error_code,
        machine_type=machine_type,
        line=line,
        investigation=investigation,
    )
    recurrence_alert = detect_recurrence(
        conn,
        error_code,
        window_hours=window_hours,
        threshold=recurrence_threshold,
    )
    return {
        "classification": classification,
        "history_matches": history_matches,
        "recurrence_alert": recurrence_alert,
        "history_checked": True,
    }


# ---------------------------------------------------------------------------
# 5. Accuracy measurement on a labeled test set
# ---------------------------------------------------------------------------

def evaluate_accuracy(
    labeled_cases: List[Dict[str, Any]],
    glossary_conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, float]:
    """Measure classification accuracy on a labeled test set.

    Each case: {error_code, phenomenon, investigation, machine_type, line,
    expected: {nhom_nguyen_nhan, cong_doan (optional), bo_phan (optional)}}.
    Fields with expected=None are skipped. Returns per-field accuracy
    (0..1) plus 'n' = number of cases.
    """
    fields = ("nhom_nguyen_nhan", "cong_doan", "bo_phan")
    correct = {f: 0 for f in fields}
    total = {f: 0 for f in fields}
    for case in labeled_cases:
        pred = classify_error(
            case.get("error_code", ""),
            phenomenon=case.get("phenomenon", ""),
            investigation=case.get("investigation", ""),
            machine_type=case.get("machine_type"),
            line=case.get("line"),
            glossary_conn=glossary_conn,
        )
        expected = case.get("expected", {})
        for f in fields:
            exp = expected.get(f)
            if exp is None:
                continue
            total[f] += 1
            if getattr(pred, f) == exp:
                correct[f] += 1
    result: Dict[str, float] = {"n": float(len(labeled_cases))}
    for f in fields:
        result[f] = round(correct[f] / total[f], 4) if total[f] else 0.0
    return result
