"""B5 acceptance: classifier accuracy on REAL History KDTPS labels + recurrence.

Ground truth: column AA (要因/Nguyen nhan) of the real `Loi KDTPS.xlsx`
(15,707 cases), mapped to the 4 ticket groups (lap rap - thiet ke -
linh kien - khac). Holdout is deterministic
(md5(no_dvd|machine|line) % 10 < 2, ~20%) and was NEVER used for keyword
selection — the keyword table was precision-gated on the TRAIN split only
(see auto_classifier.CAUSE_KEYWORDS).

Gate (ticket B5): overall accuracy >= 0.80 on the holdout.
Anti-gaming guard: the classifier must actually predict `linh_kien` and
`thiet_ke` on the holdout — an always-`khac` classifier would also clear
0.80 overall (majority class) but is degenerate.

The recurrence demo (3 real error codes) cross-checks detect_recurrence
counts against a direct SQL count on the imported history DB.
"""
from __future__ import annotations

import hashlib
import os
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None

from aios_habit.error_cases import (
    auto_classifier as ac,
)
from aios_habit.error_cases import (
    column_map,
    connect,
    init_db,
    import_history,
    start_batch,
    upsert_case,
)
from aios_habit.error_cases.case_form import submit_case

# ---------------------------------------------------------------------------
# Real-data ground truth: History KDTPS column AA -> ticket group
# ---------------------------------------------------------------------------

#: Column AA (要因/Nguyen nhan) value -> B5 group. Byte-exact source values;
#: counts below are from the real workbook (2026-10-01):
#: khac 12,599 (incl. 不要 8,315 + unknown-cause 3,667 + その他-class 617),
#: linh_kien 2,584, lap_rap 474, thiet_ke 72.
AA_CAUSE_GROUP = {
    # linh kien — component causes
    "部品要因(電気)": "linh_kien", "部品要因(Supplier)": "linh_kien",
    "部品要因(外制)": "linh_kien", "部品要因(TONER)": "linh_kien",
    "部品要因(部制)": "linh_kien", "メカ部品要因": "linh_kien",
    "部管": "linh_kien",
    # lap rap — assembly cause
    "組立": "lap_rap",
    # thiet ke — design causes
    "設計": "thiet_ke", "ソフト要因": "thiet_ke",
    # khac — other / undetermined (honest fallback bucket)
    "その他": "khac", "治具": "khac", "IT": "khac", "設備": "khac",
    "異物付着": "khac", "生管": "khac", "KDTCN": "khac",
    "不要": "khac", "要": "khac",
    "要因不明(製造)": "khac", "要因不明(電気)": "khac",
    "原因不明（メカ）": "khac", "原因不明（製造）": "khac",
    "原因不明(電気)": "khac",
}

#: Ticket acceptance gate.
B5_ACCURACY_GATE = 0.80

_CANDIDATE_WORKBOOKS = [
    os.environ.get("AIOS_B5_WORKBOOK", ""),
    "/home/hatch/workspace/aios_data/dieu_tra_loi/Điều chỉnh/Lịch sử lỗi/Loi KDTPS.xlsx",
    "D:/Sandbox/AIOS_habbit/docs/Loi KDTPS.xlsx",
]


def _find_workbook() -> Path:
    for cand in _CANDIDATE_WORKBOOKS:
        if cand and Path(cand).is_file():
            return Path(cand)
    pytest.skip(
        "B5 real-data tests need Loi KDTPS.xlsx "
        "(set AIOS_B5_WORKBOOK); skipping on machines without it."
    )


def _holdout_key(no_dvd, machine, line) -> bool:
    h = hashlib.md5(f"{no_dvd}|{machine}|{line}".encode()).hexdigest()
    return int(h[:8], 16) % 10 < 2


def _load_holdout(xlsx: Path):
    """Read the workbook directly (-> col AA labels survive; the DB import
    drops columns past Y). Returns (labeled_cases, n_skipped_unmapped)."""
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb["History KDTPS"]
    cases = []
    unmapped = 0
    unlabeled = 0
    try:
        for row in ws.iter_rows(min_row=5, max_col=29, values_only=True):
            if row[0] is None and row[1] is None:
                continue
            aa = str(row[26]).strip() if row[26] else ""
            if not aa:
                unlabeled += 1  # no ground truth -> excluded, like analysis
                continue
            group = AA_CAUSE_GROUP.get(aa)
            if group is None:
                unmapped += 1
                continue
            fields = column_map.normalize_history_row(list(row))
            key = (fields.get("no_dvd"), fields.get("machine_type"),
                   fields.get("line"))
            if not _holdout_key(*key):
                continue  # train split — never evaluated here
            code = (
                fields.get("error_code_i")
                or fields.get("error_code_c")
                or fields.get("error_code_h")
                or ""
            )
            cases.append({
                "error_code": code,
                "phenomenon": str(row[8] or ""),
                "investigation": " ".join(
                    str(row[i] or "") for i in (11, 12, 13, 14)),
                "machine_type": fields.get("machine_type"),
                "line": fields.get("line"),
                "expected": {"nhom_nguyen_nhan": group},
            })
    finally:
        wb.close()
    return cases, unmapped, unlabeled


# ---------------------------------------------------------------------------
# 1. Accuracy gate on the real holdout
# ---------------------------------------------------------------------------

def test_b5_accuracy_on_real_holdout():
    if openpyxl is None:
        pytest.skip("openpyxl not installed")
    xlsx = _find_workbook()
    cases, unmapped, unlabeled = _load_holdout(xlsx)
    assert unmapped == 0, f"AA labels without a group mapping: {unmapped}"
    assert unlabeled == 8, f"expected the 8 empty-AA rows, got {unlabeled}"
    assert len(cases) > 2000, f"holdout too small: {len(cases)}"

    result = ac.evaluate_accuracy(cases)
    acc = result["nhom_nguyen_nhan"]

    # Anti-gaming: the classifier must really predict the minority groups.
    predicted = Counter()
    for case in cases:
        pred = ac.classify_error(
            case["error_code"], phenomenon=case["phenomenon"],
            investigation=case["investigation"],
            machine_type=case["machine_type"], line=case["line"],
        )
        predicted[pred.nhom_nguyen_nhan] += 1

    detail = (
        f"n={len(cases)} acc={acc:.4f} "
        f"predicted={dict(predicted)}"
    )
    assert predicted["linh_kien"] > 0, "degenerate: never predicts linh_kien"
    assert predicted["thiet_ke"] > 0, "degenerate: never predicts thiet_ke"
    assert acc >= B5_ACCURACY_GATE, (
        f"B5 gate FAILED: accuracy {acc:.4f} < {B5_ACCURACY_GATE} ({detail})"
    )
    print(f"\nB5 real-holdout accuracy: {detail}")


# ---------------------------------------------------------------------------
# 2. Recurrence demo: 3 real error codes, counts cross-checked vs SQL
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def history_db(tmp_path_factory):
    if openpyxl is None:
        pytest.skip("openpyxl not installed")
    xlsx = _find_workbook()
    db_path = tmp_path_factory.mktemp("b5") / "b5_history.db"
    conn = connect(str(db_path))  # row_factory=sqlite3.Row (module default)
    init_db(conn)
    result = import_history(conn, str(xlsx))
    assert result["status"] == "imported"
    assert result["rows_imported"] > 15000
    yield conn
    conn.close()


def _top_real_codes(conn, n=3):
    rows = conn.execute(
        "SELECT error_code_i, COUNT(*) c FROM error_cases "
        "WHERE error_code_i IS NOT NULL AND error_code_i != '' "
        "GROUP BY error_code_i ORDER BY c DESC LIMIT ?",
        (n,),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def test_b5_recurrence_demo_three_real_codes(history_db):
    """3 real error codes -> detect_recurrence count == SQL count + 1.

    `now` is fixed after the newest occurred_at and the window covers the
    whole history, so the count is deterministic.
    """
    conn = history_db
    codes = _top_real_codes(conn, 3)
    assert len(codes) == 3, f"expected 3 real codes, got {codes}"
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)
    window_hours = 24.0 * 366 * 5  # whole history
    start = now - timedelta(hours=window_hours)
    for code, _ in codes:
        alert = ac.detect_recurrence(
            conn, code, window_hours=window_hours, threshold=2, now=now)
        assert alert is not None, f"no recurrence alert for real code {code}"
        # Independent cross-check: direct SQL count of matching history rows.
        rows = conn.execute(
            "SELECT error_code_c, error_code_h, error_code_i, occurred_at, "
            "created_at FROM error_cases"
        ).fetchall()
        expected_hist = 0
        for r in rows:
            rc = ac.norm_code(r[0])
            rh = ac.norm_code(r[1])
            ri = ac.norm_code(r[2])
            c0 = ac.norm_code(code)
            if not (rc == c0 or rh == c0 or ri == c0):
                continue
            occ = r[3]
            if occ is not None:
                if not (start.strftime("%Y-%m-%d") <= occ[:10]
                        <= now.strftime("%Y-%m-%d")):
                    continue
            else:
                if not (start.strftime("%Y-%m-%d %H:%M:%S") <= r[4]
                        <= now.strftime("%Y-%m-%d %H:%M:%S")):
                    continue
            expected_hist += 1
        # +1 = the new case being entered (not in the DB yet).
        assert alert.count == expected_hist + 1, (
            f"code {code}: alert.count={alert.count} != "
            f"sql_count+1={expected_hist + 1}"
        )
        assert str(alert.count) in alert.message_vi
        # Remedy provenance: points at a real history record or is None.
        if alert.suggested_from is not None:
            hit = conn.execute(
                "SELECT 1 FROM error_cases WHERE no_dvd = ?",
                (alert.suggested_from,),
            ).fetchone()
            assert hit is not None


# ---------------------------------------------------------------------------
# 3. Form integration: submit -> recurrence alert shown immediately
# ---------------------------------------------------------------------------

def _seed_history(conn, code, n, investigation, hours_ago=1, line="T0"):
    batch = start_batch(
        conn, source_file="B5-TEST-HISTORY", file_sha256="b5" * 32,
        sheet_name="test", sheet_type="Máy in", notes="B5 test seed",
    )
    base = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    for i in range(n):
        upsert_case(
            conn, batch_id=batch, source_row=i + 1,
            fields={
                "no_dvd": f"B5TEST/{code}/{i}",
                "sheet_type": "Máy in",
                "machine_type": "TestModel",
                "line": line,
                "error_code_c": code,
                "investigation": investigation,
                "occurred_at": base.strftime("%Y-%m-%d"),
            },
        )
    conn.commit()


def test_b5_form_submit_shows_recurrence_alert(tmp_path):
    conn = connect(str(tmp_path / "b5_form.db"))
    try:
        init_db(conn)
        # 2 recent history rows with the same code -> alert count must be 3
        # (2 history + 1 new case being entered). Seed on line T0 so the new
        # case on line T1 is not a dedup duplicate (dedup key includes line).
        _seed_history(conn, "C0099", 2,
                      "Thay board mạch, ベンダーに調査依頼 (B5-TEST)")
        result = submit_case(conn, {
            "model": "TestModel",
            "line": "T1",
            "cong_doan": "Vận hành",
            "ten_loi": "Lỗi B5 test",
            "error_code": "C0099",
            "hien_tuong": "LCD báo lỗi C0099",
            "noi_dung_dieu_tra": "ベンダーに調査依頼済み (B5-TEST)",
            "nguyen_nhan": "Đang điều tra",
            "doi_sach": "Thay board",
            "bo_phan_pt": "Bảo trì",
            "ngay_phat_sinh": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "ngay_dong": "",
            "link_bao_cao": "",
        })
        assert result["status"] == "inserted", result
        auto = result.get("auto")
        assert auto is not None, "B5: submit_case must run auto classification"
        assert auto["history_checked"] is True
        rec = auto.get("recurrence")
        assert rec is not None, "B5: expected a recurrence alert for C0099"
        assert rec["count"] == 3, f"expected 2 history + 1 new = 3, got {rec}"
        assert "3" in rec["message_vi"] and "C0099" in rec["message_vi"]
        assert auto["nhom_nguyen_nhan"] == "linh_kien"
    finally:
        conn.close()


def test_b5_form_submit_without_history_still_inserts(tmp_path):
    """No history -> no alert, but the insert and suggestion still work."""
    conn = connect(str(tmp_path / "b5_form2.db"))
    try:
        init_db(conn)
        result = submit_case(conn, {
            "model": "TestModel",
            "line": "T1",
            "cong_doan": "Vận hành",
            "ten_loi": "Lỗi lạ",
            "error_code": "ZZZ1234",
            "hien_tuong": "Hiện tượng chưa từng thấy",
            "noi_dung_dieu_tra": "",
            "nguyen_nhan": "Đang điều tra",
            "doi_sach": "Theo dõi",
            "bo_phan_pt": "Bảo trì",
            "ngay_phat_sinh": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "ngay_dong": "",
            "link_bao_cao": "",
        })
        assert result["status"] == "inserted", result
        auto = result.get("auto")
        assert auto is not None
        assert auto["recurrence"] is None
        assert auto["nhom_nguyen_nhan"] == "khac"
    finally:
        conn.close()
