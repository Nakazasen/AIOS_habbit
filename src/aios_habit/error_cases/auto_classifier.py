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
# Table order = tie-break priority: lap_rap first, then thiet_ke, linh_kien, khac.
#
# Term selection: precision-gated on the TRAIN split (80%) of the real
# History KDTPS cases, ground truth mapped to the 4 ticket groups.
# Minority groups (linh_kien, lap_rap, thiet_ke) are precision-gated
# to avoid collapsing into khac.
CAUSE_KEYWORDS: Dict[str, List[str]] = {
    "lap_rap": [
        "quên", "lắp sai", "chưa cắm", "chưa lắp", "chưa vặn", "chưa gắn",
        "chưa nối", "lắp ngược", "lỏng ốc", "tuột cáp", "chưa siết",
        "未挿入", "誤組付け", "欠品", "忘れ", "組付不良",
        # DESKTOP-STEP5-LAPRAP-CLASS-IMPROVE-HOME: Nghiệp vụ thao tác & hướng dẫn lắp ráp xưởng sản xuất
        "yêu cầu ntt", "hướng dẫn lại ntt", "đào tạo lại ntt", "ntt chú ý", "ntt tuân thủ",
        "dừng thao tác", "thao tác của ntt", "nguyên nhân do thao tác", "lỗi do thao tác",
        "vô tình làm", "vô tình để", "vít rơi", "do ntt đặt", "do ntt khi", "do ntt làm", "'do ntt",
        # Cơ cấu cơ khí & lắp ráp hoàn thiện, kết nối cáp/tiếp điểm
        "chưa hoàn chỉnh", "chưa hoàn chỉn", "lắp không hoàn chỉnh", "lắp nhầm", "lấy nhầm",
        "chưa bôi mỡ", "chưa bôi", "chưa xửi lý", "kết nối nghiêng", "lắp lệch", "không ăn khớp", "kẹp dây",
        # Thuật ngữ tiếng Nhật nghiệp vụ lỗi lắp ráp và sai sót thao tác (mounting & worker error)
        "未塗布", "未接続", "組み付けされていない", "取付不良", "取付不完全",
        "締め忘れ", "締め付け不良", "斜め挿入", "作業ミス", "作業不良",
        "ポカヨケ", "逆付け", "逆挿入", "半挿入",
    ],
    "thiet_ke": ["設計要因", "bản vẽ", "lỗi thiết kế", "sai thiết kế"],
    "linh_kien": [
        "部品品管", "外製品管", "品管", "ロット", "supplier", "lỗi linh kiện",
        "交換で再現", "ベンダー", "単品部品確認", "部品のエラー",
        "サプライヤー", "発生基板", "サプライヤーに調査依頼", "ベンダーに調査依頼",
        "外製品質管理", "に連携し選別", "調査依頼済み",
    ],
    "khac": [
        "không tái hiện", "再現せず", "治具", "jig", "原因不明", "要因不明",
        "異物付着", "chưa xác định",
    ],
}

DEPT_KEYWORDS: Dict[str, List[str]] = {
    "Điện": [
        "điện", "sensor", "cảm biến", "motor", "động cơ", "mạch",
        "board", "nguồn điện", "dây điện", "chập", "mất nguồn",
        "電気", "電気技術", "基板",
    ],
    "Cơ khí": [
        "cơ khí", "trục", "bánh răng", "vít", "ốc", "khớp nối",
        "vòng bi", "bearing", "dây đai", "belt", "kẹt cơ",
        "メカ", "機構",
    ],
    "Thiết kế": ["thiết kế", "thiet ke", "設計", "bản vẽ", "ban ve", "design"],
    "Chất lượng": ["chất lượng", "qc", "không đạt", " lỗi ng", " hàng ng", "ngoại quan", "品管", "品質", "工程qc", "qa"],
    "Kỹ thuật": ["kỹ thuật", "căn chỉnh", "calibration", "hiệu chuẩn", "技術", "製造技術", "生産技術"],
    "Vận hành": ["vận hành", "thao tác", "operation", "người vận hành", "製造", "機器製造"],
    "Bảo trì": ["bảo trì", "bảo dưỡng", "maintenance", "vệ sinh máy", "保全"],
}

STAGE_KEYWORDS: Dict[str, List[str]] = {
    "Lắp ráp": ["lắp ráp", "assembly", "組立", "組付け", "lắp đặt"],
    "Kiểm tra": ["kiểm tra", "kiểm tra chất lượng", "test", "đo đạc",
                 "inspection", "検査", "確認"],
    "Điều chỉnh": ["điều chỉnh", "adjust", "căn chỉnh", "calibration",
                   "hiệu chuẩn", "調整"],
    "Vận hành": ["vận hành", "chạy máy", "operation", "運転"],
    "In ấn": ["in ấn", "print", "kẹt giấy", "paper jam", "印刷", "通紙"],
    "Bảo trì": ["bảo trì", "bảo dưỡng", "メンテ", "保全"],
    "Gia công": ["gia công", "chế tạo", "machining", "加工"],
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


def _has_glossary_table(conn: Optional[sqlite3.Connection]) -> bool:
    if conn is None:
        return False
    try:
        r = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='error_glossary'"
        ).fetchone()
        return bool(r)
    except Exception:
        return False


def _norm_text(*parts: Any) -> str:
    text = " ".join("" if p is None else str(p) for p in parts)
    return unicodedata.normalize("NFKC", text).lower()


def _score_keywords_with_hits(text: str, table: Dict[str, List[str]]) -> Dict[str, List[str]]:
    return {
        label: [kw for kw in keywords if kw in text]
        for label, keywords in table.items()
    }


def _score_keywords(text: str, table: Dict[str, List[str]]) -> Dict[str, int]:
    return {
        label: sum(1 for kw in keywords if kw in text)
        for label, keywords in table.items()
    }


def _pick_best(scores: Dict[str, int]) -> tuple[Optional[str], int]:
    best_label: Optional[str] = None
    best_hits = 0
    # Priority tie-breaking: lap_rap, thiet_ke, linh_kien, khac
    priority_order = ("lap_rap", "thiet_ke", "linh_kien", "khac")
    check_order = [p for p in priority_order if p in scores] + [k for k in scores if k not in priority_order]
    for label in check_order:
        hits = scores.get(label, 0)
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
    can_cu: Dict[str, str] = field(default_factory=dict)  # Provenance per field
    nhom_nguyen_nhan_vi: str = ""
    suggested_from_case: Optional[str] = None


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
    nhom_nguyen_nhan='khac' with low confidence and explicit provenance.
    """
    code = norm_code(error_code)
    family = detect_family(code)
    reasons: List[str] = []
    can_cu: Dict[str, str] = {}

    glossary_text = ""
    glossary_entry = None
    if glossary_conn is not None and _has_glossary_table(glossary_conn):
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
            glossary_entry = glossary_lookup(glossary_conn, family, code)
            if not glossary_entry:
                # Fallback search across known families
                for fam in ("C_CALL", "F_SYSTEM", "JAM", "SCT_ADJ"):
                    cur = glossary_conn.execute(
                        "SELECT * FROM error_glossary WHERE code_family = ? AND code = ? AND code_sub = ''",
                        (fam, code),
                    )
                    r = cur.fetchone()
                    if r:
                        glossary_entry = dict(r) if hasattr(r, "keys") else {desc[0]: val for desc, val in zip(cur.description, r)}
                        family = fam
                        break
            if glossary_entry:
                glossary_text = " ".join(
                    str(glossary_entry.get(k) or "")
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

    # Conflict check: when an error code has a defined meaning in the glossary,
    # verify whether symptom keywords contradict the code's inherent meaning.
    override_stage: Optional[str] = None
    override_dept: Optional[str] = None
    conflict_reason = ""
    if code and glossary_entry:
        entry_name_vi = str(glossary_entry.get("name_vi") or "").strip()
        entry_name_ja = str(glossary_entry.get("name_ja") or "").strip()
        phen_lower = (phenomenon or "").lower()

        jam_keywords_in_phen = [kw for kw in ("kẹt giấy", "jam", "dắt giấy", "paper jam") if kw in phen_lower]
        if family == "C_CALL" and jam_keywords_in_phen:
            kw_str = ", ".join(f"'{k}'" for k in jam_keywords_in_phen)
            reasons.append(
                f"Phát hiện mâu thuẫn: Hiện tượng chứa từ khóa kẹt giấy ({kw_str}) nhưng mã {code} thuộc họ C_CALL ({entry_name_vi or entry_name_ja})."
            )
            glossary_lower = f"{entry_name_vi} {entry_name_ja} {glossary_entry.get('cause', '')} {glossary_entry.get('remedy', '')}".lower()
            if any(term in glossary_lower for term in ("đăng ký màu", "レジスト", "registration", "calib", "hiệu chuẩn", "điều chỉnh", "lệch màu", "skew", "tilt")):
                override_stage = "Điều chỉnh"
                override_dept = "Kỹ thuật"
            elif any(term in glossary_lower for term in ("lắp ráp", "kết nối", "connector", "cắm", "rơi", "tuột")):
                override_stage = "Lắp ráp"
                override_dept = "Bảo trì"
            else:
                override_stage = "Điều chỉnh"
                override_dept = "Kỹ thuật"

            conflict_reason = (
                f"Hiện tượng mô tả có từ khóa ({kw_str}) mâu thuẫn với định nghĩa mã {code} trong từ điển {family} "
                f"('{entry_name_vi or entry_name_ja}'). Hệ thống ưu tiên căn cứ theo bản chất mã lỗi để đề xuất công đoạn '{override_stage}'."
            )

    text = _norm_text(code, phenomenon, investigation, glossary_text)

    # --- cause group ---
    cause_hits_map = _score_keywords_with_hits(text, CAUSE_KEYWORDS)
    cause_scores = {k: len(v) for k, v in cause_hits_map.items()}
    cause_group, cause_hits = _pick_best(cause_scores)
    if cause_group is None:
        cause_group = "khac"
        cause_conf = 0.35
        reasons.append("Không khớp từ khóa nguyên nhân nào → nhóm 'Khác'.")
        can_cu["nhom_nguyen_nhan"] = "Chưa đủ căn cứ cụ thể từ lịch sử/từ khóa → tạm xếp nhóm 'Khác' (cần người dùng xác nhận)"
    else:
        cause_conf = min(0.95, 0.55 + 0.10 * (cause_hits - 1))
        matched_kws = ", ".join(f"'{k}'" for k in cause_hits_map[cause_group][:3])
        reasons.append(
            f"Nhóm nguyên nhân '{CAUSE_LABEL_VI.get(cause_group, cause_group)}': "
            f"khớp {cause_hits} từ khóa ({matched_kws})."
        )
        can_cu["nhom_nguyen_nhan"] = f"Khớp từ khóa {matched_kws} trong mô tả lỗi"

    # --- department / stage: keyword override wins, else family default ---
    dept_hits_map = _score_keywords_with_hits(text, DEPT_KEYWORDS)
    stage_hits_map = _score_keywords_with_hits(text, STAGE_KEYWORDS)
    dept_scores = {k: len(v) for k, v in dept_hits_map.items()}
    stage_scores = {k: len(v) for k, v in stage_hits_map.items()}
    dept_kw, dept_hits = _pick_best(dept_scores)
    stage_kw, stage_hits = _pick_best(stage_scores)

    defaults = FAMILY_DEFAULTS.get(family or "", {})
    if override_dept:
        bo_phan: Optional[str] = override_dept
        reasons.append(f"Bộ phận '{bo_phan}': ưu tiên theo nghĩa mã trong từ điển {family}.")
        can_cu["bo_phan"] = f"Mặc định theo họ mã {family} và quy trình hiệu chuẩn ({code})"
    elif dept_kw is not None:
        bo_phan: Optional[str] = dept_kw
        matched_dept_kws = ", ".join(f"'{k}'" for k in dept_hits_map[dept_kw][:3])
        reasons.append(f"Bộ phận '{dept_kw}': khớp {dept_hits} từ khóa ({matched_dept_kws}).")
        can_cu["bo_phan"] = f"Khớp từ khóa {matched_dept_kws} trong mô tả"
    else:
        bo_phan = defaults.get("bo_phan")
        if bo_phan:
            reasons.append(
                f"Bộ phận '{bo_phan}': mặc định theo nhóm mã {family}."
            )
            can_cu["bo_phan"] = f"Mặc định theo họ mã {family}"
        else:
            can_cu["bo_phan"] = "Không đủ căn cứ suy luận"

    if override_stage:
        cong_doan: Optional[str] = override_stage
        reasons.append(f"Công đoạn '{cong_doan}': ưu tiên theo nghĩa mã trong từ điển {family}.")
        name_def = glossary_entry.get("name_vi") or glossary_entry.get("name_ja") if glossary_entry else ""
        can_cu["cong_doan"] = (
            f"Ưu tiên mã {code} theo từ điển {family} ('{name_def}' → công đoạn {cong_doan}) "
            f"thay vì từ khóa hiện tượng 'kẹt giấy'"
        )
        can_cu["mau_thuan_ma"] = conflict_reason
    elif stage_kw is not None:
        cong_doan: Optional[str] = stage_kw
        matched_stage_kws = ", ".join(f"'{k}'" for k in stage_hits_map[stage_kw][:3])
        reasons.append(f"Công đoạn '{stage_kw}': khớp {stage_hits} từ khóa ({matched_stage_kws}).")
        can_cu["cong_doan"] = f"Khớp từ khóa {matched_stage_kws} trong mô tả"
    else:
        cong_doan = defaults.get("cong_doan")
        if cong_doan:
            reasons.append(
                f"Công đoạn '{cong_doan}': mặc định theo nhóm mã {family}."
            )
            can_cu["cong_doan"] = f"Mặc định theo họ mã {family}"
        else:
            can_cu["cong_doan"] = "Không đủ căn cứ suy luận"

    confidence = round(min(cause_conf, 0.95), 2)
    nhom_vi = CAUSE_LABEL_VI.get(cause_group, cause_group)
    return Classification(
        error_code=code,
        code_family=family,
        nhom_nguyen_nhan=cause_group,
        cong_doan=cong_doan,
        bo_phan=bo_phan,
        confidence=confidence,
        reasons=reasons,
        can_cu=can_cu,
        nhom_nguyen_nhan_vi=nhom_vi,
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
    error_code: str = "",
    phenomenon: str = "",
    window_hours: float = 12.0,
    threshold: int = 2,
    now: Optional[datetime] = None,
) -> Optional[RecurrenceAlert]:
    """Alert when the same code or phenomenon reappears in historical database.

    - When error_code is present: recurrence checking MUST query against
      the historical database across all 30,075 cases (matching error_code_c,
      error_code_h, error_code_i). If count >= 1, is_recurrence=True, surfacing
      the total case count, the most recent case (ticket/date/model), and its
      countermeasure. If the code does not exist in DB (count == 0), no false
      recurrence is triggered (returns None).
    - When error_code is absent (phenomenon only): falls back to time-windowed
      symptom token matching.
    """
    import json
    code = norm_code(error_code).upper().replace(" ", "") if error_code else ""
    ref = now or _utcnow()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    start = ref - timedelta(hours=window_hours)

    if code:
        try:
            cnt_row = conn.execute(
                """SELECT COUNT(*) FROM error_cases
                   WHERE REPLACE(UPPER(COALESCE(error_code_c, '')), ' ', '') = ?
                      OR REPLACE(UPPER(COALESCE(error_code_h, '')), ' ', '') = ?
                      OR REPLACE(UPPER(COALESCE(error_code_i, '')), ' ', '') = ?""",
                (code, code, code),
            ).fetchone()
            count = int(cnt_row[0]) if cnt_row else 0
        except sqlite3.Error:
            count = 0

        if count < 1:
            return None

        # Fetch most recent case matching code
        try:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(error_cases)")}
            cm_select = ", countermeasure" if "countermeasure" in cols else ""
            latest_rows = conn.execute(
                f"""SELECT no_dvd, error_code_c, error_code_h, error_code_i,
                          machine_type, line, investigation{cm_select},
                          created_at, occurred_at, raw_json
                   FROM error_cases
                   WHERE REPLACE(UPPER(COALESCE(error_code_c, '')), ' ', '') = ?
                      OR REPLACE(UPPER(COALESCE(error_code_h, '')), ' ', '') = ?
                      OR REPLACE(UPPER(COALESCE(error_code_i, '')), ' ', '') = ?
                   ORDER BY COALESCE(occurred_at, created_at) DESC, id DESC
                   LIMIT 5""",
                (code, code, code),
            ).fetchall()
        except sqlite3.Error:
            latest_rows = []

        remedy = ""
        no_dvd = ""
        date_str = ""
        model_line = ""

        if latest_rows:
            top_r = dict(latest_rows[0])
            no_dvd = str(top_r.get("no_dvd") or "").strip()
            date_val = str(top_r.get("occurred_at") or top_r.get("created_at") or "").strip()
            date_str = date_val.split("T")[0].split(" ")[0] if date_val else "Chưa ghi nhận ngày"
            m_type = str(top_r.get("machine_type") or "").strip()
            l_val = str(top_r.get("line") or "").strip()
            if m_type and l_val:
                model_line = f"{m_type} / {l_val}"
            else:
                model_line = m_type or l_val or "Chưa rõ model"

            raw = {}
            if top_r.get("raw_json"):
                try:
                    raw = json.loads(top_r["raw_json"])
                except Exception:
                    raw = {}

            raw_cm = str(top_r.get("countermeasure") or raw.get("AB") or "").strip()
            if raw_cm and raw_cm not in ("-", "—", "ー"):
                remedy = raw_cm
            else:
                raw_inv = str(raw.get("O") or raw.get("M") or top_r.get("investigation") or "").strip()
                remedy = raw_inv[:300] if raw_inv else "Chưa có đối sách cụ thể trong lịch sử"

        message_vi = (
            f"Tái phát: mã {code} đã xuất hiện {count} lần trong cơ sở dữ liệu lịch sử (30.075 ca). "
            f"Ca gần nhất: vụ {no_dvd} (ngày {date_str}, model {model_line})."
        )
        return RecurrenceAlert(
            code=code,
            count=count,
            window_hours=window_hours,
            message_vi=message_vi,
            suggested_remedy=remedy,
            suggested_from=no_dvd,
        )

    # Fallback when code is absent (phenomenon only)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(error_cases)")}
        cm_select = ", countermeasure" if "countermeasure" in cols else ""
        rows = conn.execute(
            f"""SELECT no_dvd, error_code_c, error_code_h, error_code_i,
                      investigation{cm_select}, created_at, occurred_at
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

    hits: List[Dict[str, Any]] = []
    phen_tokens = _token_set(phenomenon) if phenomenon else set()
    if phen_tokens:
        for r in rows:
            inv = r.get("investigation") or ""
            inv_tokens = _token_set(inv)
            if len(phen_tokens & inv_tokens) >= 2:
                hits.append(dict(r))

    total = len(hits) + 1  # +1 = the new case being entered
    if total < threshold:
        return None

    remedy = None
    remedy_from = None
    for h in hits:
        inv = (h.get("countermeasure") or h.get("investigation") or "").strip()
        if inv:
            remedy = inv[:300]
            remedy_from = h.get("no_dvd")
            break

    disp_key = "hiện tượng tương tự"
    if remedy:
        message_vi = (
            f"Tái phát: {disp_key} đã phát sinh {total} lần trong "
            f"{window_hours:g} giờ qua. Đề xuất đối sách: {remedy}"
        )
    else:
        message_vi = (
            f"Tái phát: {disp_key} đã phát sinh {total} lần trong "
            f"{window_hours:g} giờ qua. Chưa có đối sách trong lịch sử — "
            f"cần điều tra nguyên nhân gốc."
        )
    return RecurrenceAlert(
        code=phenomenon[:20] if phenomenon else "",
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
    if glossary_conn is None and _has_glossary_table(conn):
        glossary_conn = conn

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
        investigation=f"{phenomenon} {investigation}".strip(),
    )

    # Enrich provenance with top historical match when strong
    if history_matches:
        top = history_matches[0]
        top_case = top.case
        classification.suggested_from_case = top_case.get("no_dvd")
        if top.score >= 5.0:
            top_stage = str(top_case.get("process_stage") or "").strip()
            mapped_stage = None
            if "調整" in top_stage:
                mapped_stage = "Điều chỉnh"
            elif "組立" in top_stage:
                mapped_stage = "Lắp ráp"
            elif "検査" in top_stage or "確認" in top_stage:
                mapped_stage = "Kiểm tra"
            elif top_stage in STAGE_KEYWORDS:
                mapped_stage = top_stage

            if mapped_stage and (classification.cong_doan is None or "mau_thuan_ma" in classification.can_cu):
                classification.cong_doan = mapped_stage
                classification.can_cu["cong_doan"] = (
                    f"Ưu tiên mã {classification.error_code} theo từ điển {classification.code_family or 'C_CALL'} "
                    f"và lịch sử ca #{top_case.get('no_dvd')} (công đoạn {top_stage} → {mapped_stage})"
                )
            elif top_case.get("process_stage") and classification.cong_doan is None:
                classification.cong_doan = str(top_case.get("process_stage"))
                classification.can_cu["cong_doan"] = (
                    f"Dựa trên ca lịch sử #{top_case.get('no_dvd')} (độ tương đồng {top.score:.1f})"
                )
            elif top_case.get("process_stage") and "can_cu" in dir(classification):
                classification.can_cu["cong_doan"] = (
                    f"{classification.can_cu.get('cong_doan', '')} · Tương đồng ca #{top_case.get('no_dvd')}"
                )

            if top_case.get("department") and classification.bo_phan is None:
                classification.bo_phan = str(top_case.get("department"))
                classification.can_cu["bo_phan"] = (
                    f"Dựa trên ca lịch sử #{top_case.get('no_dvd')} (độ tương đồng {top.score:.1f})"
                )
            elif top_case.get("department") and "can_cu" in dir(classification):
                classification.can_cu["bo_phan"] = (
                    f"{classification.can_cu.get('bo_phan', '')} · Tương đồng ca #{top_case.get('no_dvd')}"
                )

    recurrence_alert = detect_recurrence(
        conn,
        error_code=error_code,
        phenomenon=phenomenon,
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
