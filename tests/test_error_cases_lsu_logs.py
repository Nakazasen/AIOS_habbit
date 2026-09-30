"""LSU-1 tests: importer for LSU production logs ("log jig" / "log 6 pcs").

Synthetic fixtures only — dữ liệu LSU thật không bao giờ vào Git.
Covers: dialect detection, NG-only filtering per dialect, field mapping +
provenance (no_dvd / raw markers / row digest), re-import skip + force,
tree import (family + unknown files), and the lsu_log completeness format
(cause/fix measured as unfilled → F3b gate trips honestly).
"""
import json

import pytest

from aios_habit.error_cases import (
    connect,
    detect_lsu_dialect,
    import_lsu_log,
    import_lsu_tree,
    init_db,
    measure_completeness,
    read_lsu_events,
    store,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures (never the real company files)
# ---------------------------------------------------------------------------

JIG_CSV = (
    "SelNo,Date,Time,JigNo,FinTest,Bow\n"
    "SN-1,2021/4/20,7:26:24,#1,OK,5.03\n"
    "SN-2,2021/4/20,8:15:46,#1,NG,5.20\n"
    "SN-3,2021/4/20,8:17:56,#1,NG,5.10\n"
    "SN-4,2021/4/20,8:20:10,#1,,\n"  # FinTest rỗng -> không phải sự kiện
)

CAM_CSV = (
    "DATE,TIME,CAM_ID,ERR_NUM\n"
    "2026.08.25,13:48:12,0,-1306\n"
    "2026.08.25,14:02:00,1,-1307\n"
)

JUDGE_CSV = (
    " DATE, TIME, JigNumber, S/N,TotalJudge, Black_TotalJudge, Magenta_TotalJudge\n"
    "2025/02/01,6:00:00,#1,SN-A,NG,OK,OK\n"
    "2025/02/01,6:01:00,#1,SN-B,OK,NG,OK\n"
    "2025/02/01,6:02:00,#1,SN-C,OK,OK,OK\n"
)

RESULT_CSV = (
    "DATE,TIME,SERIAL NUMBER,RESULT,RESULT:BLACK,RESULT:MAGENTA\n"
    "2026.08.01,13:18:48,61C1068E6210,OK,OK,OK\n"
    "2026.08.01,13:21:48,61C1068E6205,Bow Adjust No Need!!,OK,NG\n"
)


@pytest.fixture()
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


def _write(tmp_path, name, text, encoding="utf-8"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return path


def _case(conn, no_dvd):
    return conn.execute(
        "SELECT * FROM error_cases WHERE no_dvd = ?", (no_dvd,)
    ).fetchone()


# ---------------------------------------------------------------------------
# Detection + parsing
# ---------------------------------------------------------------------------

def test_detect_lsu_dialects():
    assert detect_lsu_dialect(["DATE", "TIME", "CAM_ID", "ERR_NUM"]) == "cam_error"
    assert detect_lsu_dialect(["SelNo", "Date", "Time", "JigNo", "FinTest"]) == "jig_result"
    assert detect_lsu_dialect([" DATE", " S/N", " Black_TotalJudge"]) == "unit_judge"
    assert detect_lsu_dialect(["DATE", "TIME", "SERIAL NUMBER", "RESULT:BLACK"]) == "unit_result"
    assert detect_lsu_dialect(["DATE", "TIME", "SERIAL NUMBER", "RESULT"]) == "unit_result"
    assert detect_lsu_dialect(["Date", "Time", "SelNo", "CAM"]) is None


def test_read_jig_events_filters_non_ok(tmp_path):
    path = _write(tmp_path, "Log2021_4.csv", JIG_CSV)
    parsed = read_lsu_events(path)
    assert parsed.dialect == "jig_result"
    assert parsed.rows_read == 4
    assert [e["row_no"] for e in parsed.events] == [2, 3]
    assert parsed.events[0]["date"] == "2021/4/20 8:15:46"
    assert "FinTest=NG" in parsed.events[0]["investigation"]
    assert parsed.events[0]["key_columns"]["SelNo"] == "SN-2"
    assert len(parsed.events[0]["row_sha256"]) == 64


def test_read_cam_error_takes_every_row(tmp_path):
    path = _write(tmp_path, "2ND-1035-1_2026_08_CamError.csv", CAM_CSV)
    parsed = read_lsu_events(path)
    assert parsed.dialect == "cam_error"
    assert len(parsed.events) == 2
    assert parsed.events[0]["code"] == "-1306"
    assert parsed.events[0]["investigation"] == "CamError: CAM_ID=0 ERR_NUM=-1306"


def test_read_judge_union_of_ng_columns(tmp_path):
    path = _write(tmp_path, "2025_02.csv", JUDGE_CSV)
    parsed = read_lsu_events(path)
    assert parsed.dialect == "unit_judge"
    assert [e["row_no"] for e in parsed.events] == [1, 2]
    assert "TotalJudge" in parsed.events[0]["investigation"]
    assert "Black_TotalJudge" in parsed.events[1]["investigation"]
    assert parsed.events[0]["stage"] == "#1"


def test_read_result_color_ng(tmp_path):
    path = _write(tmp_path, "2026_08_Error.csv", RESULT_CSV)
    parsed = read_lsu_events(path)
    assert parsed.dialect == "unit_result"
    assert len(parsed.events) == 1
    assert "RESULT:MAGENTA" in parsed.events[0]["investigation"]
    assert "S/N=61C1068E6205" in parsed.events[0]["investigation"]


def test_read_digest_covers_cells_beyond_header(tmp_path):
    """Log thật có dòng dài hơn header (6thA3: 71 ô vs 64 cột); digest dòng
    nguồn phải phủ các ô vượt cột header, nếu không sẽ mất khả năng đối chiếu."""
    base = "SelNo,Date,Time,JigNo,FinTest\nSN-1,2021/4/20,7:26:24,#1,NG,TAIL-A\n"
    other = base.replace("TAIL-A", "TAIL-B")
    first = read_lsu_events(_write(tmp_path, "a.csv", base))
    second = read_lsu_events(_write(tmp_path, "b.csv", other))
    assert first.events[0]["row_sha256"] != second.events[0]["row_sha256"]


# ---------------------------------------------------------------------------
# Import + provenance
# ---------------------------------------------------------------------------

def test_import_jig_log_counts_and_fields(conn, tmp_path):
    path = _write(tmp_path, "Log2021_4.csv", JIG_CSV)
    result = import_lsu_log(conn, path, family="6thA3", rel_name="6thA3 LSU/Log2021_4.csv")
    assert result["status"] == "imported"
    assert result["rows_read"] == 4
    assert result["rows_imported"] == 2
    assert result["rows_skipped"] == 2
    assert store.count_cases(conn) == 2

    row = _case(conn, "LSU/6thA3 LSU/Log2021_4/2")
    assert row is not None
    assert row["machine_type"] == "LSU"
    assert row["line"] == "6thA3"
    assert "FinTest=NG" in row["investigation"]
    raw = json.loads(row["raw_json"])
    assert raw["format"] == "lsu_log"
    assert raw["dialect"] == "jig_result"
    assert raw["date"] == "2021/4/20 8:15:46"
    assert raw["cause"] == "" and raw["fix"] == ""
    assert raw["source_row"] == 2
    assert raw["columns_total"] == 6
    stats = store.batch_stats(conn, result["batch_id"])
    assert stats["source_file"] == "6thA3 LSU/Log2021_4.csv"
    assert stats["sheet_name"] == "jig_result"
    assert stats["rows_read"] == 4 and stats["rows_imported"] == 2


def test_import_cam_error_sets_code(conn, tmp_path):
    path = _write(tmp_path, "CamError.csv", CAM_CSV)
    import_lsu_log(conn, path, family="Iris", rel_name="Iris LSU/CamError.csv")
    row = _case(conn, "LSU/Iris LSU/CamError/1")
    assert row["error_code_h"] == "-1306"
    assert row["investigation"].startswith("CamError")


def test_reimport_skips_unchanged_but_force_reruns(conn, tmp_path):
    path = _write(tmp_path, "Log2021_4.csv", JIG_CSV)
    first = import_lsu_log(conn, path, family="6thA3", rel_name="a/Log2021_4.csv")
    again = import_lsu_log(conn, path, family="6thA3", rel_name="a/Log2021_4.csv")
    assert again["status"] == "skipped"
    assert again["batch_id"] == first["batch_id"]
    assert store.count_cases(conn) == 2  # không nhân đôi

    forced = import_lsu_log(
        conn, path, family="6thA3", rel_name="a/Log2021_4.csv", force=True
    )
    assert forced["status"] == "imported"
    assert forced["batch_id"] == first["batch_id"]  # ghi lại vào đúng batch
    assert store.count_cases(conn) == 2  # upsert tại chỗ


def test_unknown_file_is_skipped_silently(conn, tmp_path):
    path = _write(tmp_path, "notes.csv", "a,b,c\n1,2,3\n")
    result = import_lsu_log(conn, path, family="X", rel_name="X/notes.csv")
    assert result["status"] == "skipped_unknown"
    assert result["rows_read"] == 0
    assert store.count_cases(conn) == 0


def test_tree_import_maps_families(conn, tmp_path):
    _write(tmp_path, "6thA3 LSU/Lỗi JIG BEAM/Log2021_4.csv", JIG_CSV)
    _write(tmp_path, "Iris LSU/log/CamError.csv", CAM_CSV)
    _write(tmp_path, "Sirius LSU/linearity/2025_02.csv", JUDGE_CSV)
    _write(tmp_path, "Sirius LSU/linearity/notes.csv", "a,b\n1,2\n")

    summary = import_lsu_tree(conn, tmp_path)
    assert summary["files_scanned"] == 4
    assert summary["files_imported"] == 3
    assert summary["files_skipped_unknown"] == 1
    assert summary["rows_imported"] == 2 + 2 + 2
    assert summary["by_family"]["6thA3"]["files"] == 1
    assert summary["by_family"]["Iris"]["files"] == 1
    assert summary["by_family"]["Sirius"]["files"] == 1
    lines = {
        row["line"] for row in conn.execute("SELECT DISTINCT line FROM error_cases")
    }
    assert lines == {"6thA3", "Iris", "Sirius"}


# ---------------------------------------------------------------------------
# Completeness over lsu_log rows
# ---------------------------------------------------------------------------

def test_completeness_lsu_log_measures_cause_fix_as_unfilled(conn, tmp_path):
    _write(tmp_path, "Log2021_4.csv", JIG_CSV)
    _write(tmp_path, "CamError.csv", CAM_CSV)
    import_lsu_tree(conn, tmp_path)

    result = measure_completeness(conn, format="lsu_log")
    assert result["total"] == 4  # 2 jig + 2 cam
    assert result["fields"]["no_dvd"]["rate"] == 100.0
    assert result["fields"]["machine_type"]["rate"] == 100.0
    assert result["fields"]["line"]["rate"] == 100.0
    assert result["fields"]["investigation"]["rate"] == 100.0
    assert result["fields"]["date"]["rate"] == 100.0
    # cause/fix: log không mang nguyên nhân/đối sách -> đo là 0%, không n/a.
    assert result["fields"]["cause"]["applicable"] == 4
    assert result["fields"]["cause"]["rate"] == 0.0
    assert result["fields"]["fix"]["rate"] == 0.0
    assert result["needs_f3b"] is True
    assert set(result["f3b_fields"]) == {"cause", "fix"}

    # format=None vẫn đếm các dòng này (không đổi hành vi cũ).
    overall = measure_completeness(conn)
    assert overall["total"] == 4
