"""BK-ERRCODE: extended extraction (N/O/L/M/R) + KTD matching + backfill.

Test data are VERBATIM strings from the real workbook
(Loi KDTPS.xlsx, sheet 'History KDTPS') — never invented. The KTD
filenames used are real names seen in 'Lịch sử lỗi/C Call/'.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from aios_habit.error_cases import (
    analyze_row_codes,
    backfill_error_code_i_extended,
    connect,
    extract_code_from_row,
    init_db,
    list_ktd_dossiers,
    match_ktd_dossiers,
    parse_ktd_filename,
    scan_free_text_codes,
    write_manual_csv,
)

# --- verbatim samples from Loi KDTPS.xlsx (History KDTPS) --------------------
# Column N (investigation JP): the real code is stated as displayed.
N_C0180 = (
    "＋Log取得済み\n＋機器へのUSB間の結線確認：OK\n"
    "＋ラインアウト→起動後C0180表示\n＋電源OFF/ON：再現有り\n"
    "→電気技術、製造技術\n外観検査：問題なし\nI/F再チェック：NG FCT1 STEP 005-003"
)
# Column L (work content JP): code stated mid-sentence.
L_F000 = "Upsoft途中でLCD画面がF000表示→30秒後、自動リセット→30秒後発生"
# Column M (work content VN): note the source typo 'FOOO'; the real F000
# appears later and is still found.
M_F000 = (
    "Lỗi FOOO\n* Hiện trạng : NTT đang Upsoft LCD báo F000 => Sau khoảng 30s "
    "máy tự động Reset màn hình LCD ở trạng thái chờ"
)
# Column O (investigation VN): explicit 'Jamcode;' label.
O_JAMCODE = (
    "- Liên lạc KTCT xác nhận và điều tra\n- Jamcode; Jam4311.\n"
    "- Dựa vào hiện trạng phát sinh;"
)
# False positive: Japanese word OFF in 電源ON/OFF15回 -> 'FF15'.
FP_OFF15 = (
    "Engine基板のCPU部品加熱、冷却実施も再現しない\n"
    "電源ON/OFF15回実施時再現しない場合は、再現しない不良処理"
)
# False positive: serial number containing a code-shaped run.
FP_SERIAL = (
    'MES上のSerial Number：" INQ3021"表示\n'
    "実際のSerial Number ：D8V102ZC2797\n→このS/Nがどのマシンにも書き込まない"
)
# False positive: part number containing a code-shaped run.
FP_PART = 'o Jam " Paper Jammed in the Rear Cover" FQA1533F7816-1702TA7US0  => Thay GUIDE E'
# Ambiguous: F401 is a PCB fuse designator here, not a fault code.
FP_FUSE = (
    " Q403 部品が短絡されたため、F401ヒューズが断線→継続調査\n"
    "→メーカーに連携し不良部品検査方法検討"
)
# Conflict: N says C7620, O says C7620 then C7612 -> manual review.
CONFLICT_N = (
    "＋ログ取得済み\n→ラインアウト\n＋Process画像 8枚印字→濃度測定：OK\n"
    "＋Calibration実施：C7620表示\n＋ID Sensor交換：NG"
)
CONFLICT_O = (
    "*Đã lấy LOG\n*Line out máy\n-Calibration => LCD báo C7620\n"
    "-Lắp lại LSU cũ, Aging => Error 80, Calibration => C7612"
)


def test_scan_free_text_finds_code_in_investigation():
    hits = scan_free_text_codes(N_C0180)
    confident = [h for h in hits if h["confident"]]
    assert [(h["code"]) for h in confident] == ["C0180"]


def test_scan_free_text_finds_code_in_work_content():
    assert [h["code"] for h in scan_free_text_codes(L_F000) if h["confident"]] == ["F000"]
    assert [h["code"] for h in scan_free_text_codes(M_F000) if h["confident"]] == ["F000"]


def test_scan_free_text_jamcode_label_counts():
    hits = scan_free_text_codes(O_JAMCODE)
    assert [h["code"] for h in hits if h["confident"]] == ["JAM4311"]


def test_scan_free_text_rejects_off15_word():
    assert scan_free_text_codes(FP_OFF15) == []


def test_scan_free_text_rejects_serial_number():
    assert scan_free_text_codes(FP_SERIAL) == []


def test_scan_free_text_rejects_part_number():
    assert scan_free_text_codes(FP_PART) == []


def test_scan_free_text_rejects_fuse_designator():
    hits = scan_free_text_codes(FP_FUSE)
    assert [h for h in hits if h["confident"]] == []


def test_analyze_row_codes_priority_i_first():
    raw = {"I": "LCD画面にF000表示", "N": N_C0180}
    assert extract_code_from_row(raw) == ("F000", "I")


def test_analyze_row_codes_from_extra_columns():
    assert extract_code_from_row({"I": "", "N": N_C0180}) == ("C0180", "N")
    assert extract_code_from_row({"I": None, "L": L_F000}) == ("F000", "L")
    assert extract_code_from_row({"I": "", "M": M_F000}) == ("F000", "M")
    assert extract_code_from_row({"I": "", "O": O_JAMCODE}) == ("JAM4311", "O")


def test_analyze_row_codes_conflict_goes_manual():
    r = analyze_row_codes({"I": "", "N": CONFLICT_N, "O": CONFLICT_O})
    assert r["code"] is None
    assert {c["code"] for c in r["conflicts"]} == {"C7620", "C7612"}


def test_analyze_row_codes_nothing():
    assert extract_code_from_row({"I": "", "N": "", "O": None}) == (None, None)
    assert extract_code_from_row(None) == (None, None)


def test_parse_ktd_filename():
    p = parse_ktd_filename("KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx")
    assert p == {"ym": "2026-08", "machine": "Iris2024", "line": "C33",
                 "code": "C4001", "file": "KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx"}
    # lowercase jam code in the code slot
    p = parse_ktd_filename("KTD-2026-02-0167-Iris2024-C35-A8-Jam0501.xlsx")
    assert p["code"] == "JAM0501"
    # J-family code in the code slot
    p = parse_ktd_filename("KTD-2026-01-0104-Iris2024-C35-A7-J4002.xlsx")
    assert p["code"] == "J4002"
    # descriptive tail, not a code -> never forced
    p = parse_ktd_filename("KTD-2026-05-0410-Iris2024-C35-A7-error80.xlsx")
    assert p["code"] is None
    p = parse_ktd_filename("KTD-2026-06-0540-Iris2024-C35-A2-NG Fax.xlsx")
    assert p["code"] is None
    # malformed names
    assert parse_ktd_filename("KTD-2026-01-0011-Iris2024-Eva-.xlsx")["code"] is None
    assert parse_ktd_filename("random.xlsx") is None


def test_match_ktd_dossiers_by_line_month_machine():
    dossiers = [
        {"ym": "2024-10", "machine": "Iris2020", "line": "C34",
         "code": "C0980", "file": "KTD-2024-10-1272-Iris2020-C34-A1-C0980.xlsx"},
        {"ym": "2024-10", "machine": "Iris2020", "line": "C34",
         "code": "C0363", "file": "KTD-2024-10-1300-Iris2020-C34-A1-C0363.xlsx"},
        {"ym": "2024-11", "machine": "Iris2020", "line": "C34",
         "code": "C0980", "file": "KTD-2024-11-0001-Iris2020-C34-A1-C0980.xlsx"},
    ]
    # history D holds 'Iris2020\n下位' -> substring match
    two = match_ktd_dossiers(dossiers, machine_type="Iris2020\n下位",
                             line="C34", occurred_at="2024-10-05")
    assert len(two) == 2
    one = match_ktd_dossiers(dossiers, machine_type="Iris2020\n下位",
                             line="C34", occurred_at="2024-11-05")
    assert [d["code"] for d in one] == ["C0980"]
    assert match_ktd_dossiers(dossiers, machine_type="Iris2020",
                              line="C35", occurred_at="2024-10-05") == []
    assert match_ktd_dossiers(dossiers, machine_type="Iris2020",
                              line="C34", occurred_at=None) == []


def _insert(conn, batch_id=1, **kw):
    from aios_habit.error_cases import upsert_case
    fields = {
        "no_dvd": kw.pop("no_dvd"),
        "machine_type": kw.pop("machine_type", "Iris2020\n下位"),
        "line": kw.pop("line", "C34"),
        "occurred_at": kw.pop("occurred_at", None),
        "error_code_h": kw.pop("error_code_h", "ERROR"),
        "error_code_i": kw.pop("error_code_i", None),
        "raw": kw.pop("raw", {}),
    }
    return upsert_case(conn, batch_id=batch_id, source_row=1,
                       fields=fields, format="history_29")


def test_backfill_extended_dry_run_then_apply(tmp_path):
    db = tmp_path / "bk.db"
    conn = connect(db)
    try:
        init_db(conn)
        conn.execute(
            "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
            " VALUES ('t.xlsx', 'x', 'History KDTPS')"
        )
        # A: strict extraction from column N
        _insert(conn, no_dvd="2024/1", occurred_at="2024-10-05",
                raw={"I": "LCD画面にTIME OUT表示", "N": N_C0180})
        # B: no text code; KTD single match
        _insert(conn, no_dvd="2024/2", occurred_at="2024-11-05",
                raw={"I": "PC画面にFAX 2 NG表示"})
        # C: nothing anywhere, and a month with no KTD dossier -> manual list
        _insert(conn, no_dvd="2024/3", occurred_at="2024-09-06",
                raw={"I": "ハンディターミナルが Engine基板検知せず", "N": FP_SERIAL})
        # D: already has a code, missing provenance -> stamped
        _insert(conn, no_dvd="2024/4", occurred_at="2024-10-07",
                error_code_i="F000", raw={"I": "LCD画面にF000表示"})

        ktd_dir = tmp_path / "ktd"
        ktd_dir.mkdir()
        (ktd_dir / "KTD-2024-11-0001-Iris2020-C34-A1-C0980.xlsx").write_bytes(b"x")
        (ktd_dir / "KTD-2024-10-1272-Iris2020-C34-A1-C0980.xlsx").write_bytes(b"x")

        dry = backfill_error_code_i_extended(conn, ktd_dir=ktd_dir)
        assert dry["status"] == "planned"
        assert dry["extracted_auto"] == 1, dry
        assert dry["ktd_auto"] == 1, dry
        assert dry["manual_list"] == 1, dry
        assert dry["src_stamped"] == 1, dry
        assert dry["updated"] == 0
        # dry-run writes nothing
        assert conn.execute("SELECT error_code_i FROM error_cases").fetchall()[0][0] is None

        applied = backfill_error_code_i_extended(conn, apply=True, ktd_dir=ktd_dir)
        assert applied["status"] == "applied"
        assert applied["updated"] == 2, applied  # A + B get codes; D only gets src stamp
        assert applied["src_stamped"] == 1, applied
        rows = {r[0]: (r[1], r[2]) for r in conn.execute(
            "SELECT no_dvd, error_code_i, error_code_i_src FROM error_cases")}
        assert rows["2024/1"] == ("C0180", "extracted_them")
        assert rows["2024/2"] == ("C0980", "ktd_matched")
        assert rows["2024/3"][0] is None
        assert rows["2024/4"] == ("F000", "extracted_them")
        note_b = conn.execute(
            "SELECT error_code_i_note FROM error_cases WHERE no_dvd='2024/2'").fetchone()[0]
        assert "KTD-2024-11-0001" in note_b
        note_a = conn.execute(
            "SELECT error_code_i_note FROM error_cases WHERE no_dvd='2024/1'").fetchone()[0]
        assert note_a.startswith("cột N")

        # manual CSV contains only the unresolvable row
        csv_path = tmp_path / "manual.csv"
        assert write_manual_csv(csv_path, applied["manual"]) == 1
        content = csv_path.read_text(encoding="utf-8-sig")
        assert "2024/3" in content and "2024/1" not in content

        # rerun: idempotent
        rerun = backfill_error_code_i_extended(conn, apply=True, ktd_dir=ktd_dir)
        assert rerun["updated"] == 0 and rerun["no_change"] == 3, rerun
        assert rerun["manual_list"] == 1
    finally:
        conn.close()


def test_backfill_dry_run_unmigrated_db_missing_src_column(tmp_path):
    """Regression: dry-run (migrate=False) on a DB that has error_code_i but
    no error_code_i_src must NOT raise 'no such column: error_code_i_src'.
    Simulates the BK-ERRCODE dry-run on a copy that was never migrated."""
    db = tmp_path / "bk_nomigrate.db"
    conn = connect(db)
    try:
        init_db(conn)
        conn.execute(
            "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
            " VALUES ('t.xlsx', 'x', 'History KDTPS')"
        )
        _insert(conn, no_dvd="2024/1", occurred_at="2024-10-05",
                raw={"I": "LCD画面にTIME OUT表示", "N": N_C0180})
        # Simulate an unmigrated DB: provenance column was never added.
        conn.execute("ALTER TABLE error_cases DROP COLUMN error_code_i_src")
        result = backfill_error_code_i_extended(conn, migrate=False)
        assert result["status"] == "planned"
        assert result["rows_read"] == 1
        assert result["extracted_auto"] == 1, result
        assert result["manual_list"] == 0, result
        assert result["updated"] == 0
        # dry-run writes nothing
        assert conn.execute("SELECT error_code_i FROM error_cases").fetchall()[0][0] is None
    finally:
        conn.close()


def test_backfill_extended_multi_ktd_goes_manual(tmp_path):
    db = tmp_path / "bk2.db"
    conn = connect(db)
    try:
        init_db(conn)
        conn.execute(
            "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
            " VALUES ('t.xlsx', 'x', 'History KDTPS')"
        )
        _insert(conn, no_dvd="2024/9", occurred_at="2024-10-05",
                raw={"I": "LCD画面にERROR表示"})
        ktd_dir = tmp_path / "ktd"
        ktd_dir.mkdir()
        (ktd_dir / "KTD-2024-10-1272-Iris2020-C34-A1-C0980.xlsx").write_bytes(b"x")
        (ktd_dir / "KTD-2024-10-1300-Iris2020-C34-A1-C0363.xlsx").write_bytes(b"x")
        res = backfill_error_code_i_extended(conn, apply=True, ktd_dir=ktd_dir)
        assert res["ktd_auto"] == 0
        assert res["manual_list"] == 1
        assert conn.execute("SELECT error_code_i FROM error_cases").fetchone()[0] is None
    finally:
        conn.close()


def test_list_ktd_dossiers_skips_non_code_tails(tmp_path):
    d = tmp_path / "c"
    d.mkdir()
    (d / "KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx").write_bytes(b"x")
    (d / "KTD-2026-05-0410-Iris2024-C35-A7-error80.xlsx").write_bytes(b"x")
    (d / "notes.txt").write_bytes(b"x")
    dossiers = list_ktd_dossiers(d)
    assert [x["code"] for x in dossiers] == ["C4001"]


def _load_cli():
    path = Path(__file__).resolve().parent.parent / "scripts" / "backfill_errcode.py"
    spec = importlib.util.spec_from_file_location("backfill_errcode", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_refuses_production_db(tmp_path):
    cli = _load_cli()
    prod = tmp_path / "error_cases_deploy.db"
    prod.write_bytes(b"x")
    assert cli._is_denied(prod, []) is not None
    prod_dir = tmp_path / "production"
    prod_dir.mkdir()
    other = prod_dir / "copy.db"
    other.write_bytes(b"x")
    assert cli._is_denied(other, []) is not None
    ok_copy = tmp_path / "error_cases_copy.db"
    ok_copy.write_bytes(b"x")
    assert cli._is_denied(ok_copy, []) is None
    assert cli._is_denied(prod, [str(prod)]) is not None
    assert cli._is_denied(ok_copy, [str(prod)]) is None
