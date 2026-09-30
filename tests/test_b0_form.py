"""B0-FORM tests: standard Step-0 entry form (12 fields) -> straight to DB.

Acceptance for B0-FORM:
- a new report submitted through the form lands in the DB with all 12
  fields, no intermediate file is created;
- missing required field -> blocked; duplicate -> warning, not inserted;
  unknown error code -> warning, still inserted;
- the chat action renders the blank template and accepts a filled form
  inside the answer area (one input box + one answer area, no extra UI).

Fixture values marked REAL come from the real workbook
`Loi KDTPS.xlsx` (sheet "History KDTPS", data rows 5-7); values prefixed
SIMULATED_ are invented for the test.
"""

import json
import sqlite3

import pytest

from aios_habit import chat_action
from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_case_form import (
    ACTION_NAME,
    _handler,
    register,
    resolve_db_path,
)
from aios_habit.error_cases import (
    CASE_FORM_FIELDS,
    connect,
    count_cases,
    ensure_form_schema,
    find_duplicate_case,
    init_db,
    init_glossary,
    lookup_error_code,
    looks_like_filled_form,
    parse_form_text,
    read_case,
    render_blank_form,
    split_error_code,
    submit_form_case,
    validate_form,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# REAL: History KDTPS row 5 (model/line/process/phenomenon/cause/dept/date).
REAL_FORM = {
    "model": "6th Next",
    "line": "A15",
    "cong_doan": "画像A4.2",
    "ten_loi": "LCD báo Close top cover",
    "error_code": "C0030",
    "hien_tuong": 'LCD画面に"Close top cover"表示',
    "noi_dung_dieu_tra": "Máy đã được lineout ra ngoài để liên lạc với kỹ thuật điện.",
    "nguyen_nhan": "部品要因(電気)",
    "doi_sach": "Thay PWB ENGINE ASSY.",
    "bo_phan_pt": "電気技術",
    "ngay_phat_sinh": "2023-01-05",
    "ngay_dong": "2023-01-10",
    "link_bao_cao": "https://example.invalid/bao-cao/2023-001",
}


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "form_test.db"
    conn = connect(path)
    init_db(conn)
    init_glossary(conn)
    # Glossary entries for the codes used below (test setup, not real data).
    conn.execute(
        "INSERT INTO error_glossary "
        "(code_family, code, name_vi, source_file) VALUES "
        "('C_CALL', 'C0030', 'Mã C-call mẫu', 'test'),"
        "('F_SYSTEM', 'F000', 'Mã F mẫu', 'test')"
    )
    conn.commit()
    yield conn
    conn.close()


def _row_dict(conn, case_id):
    return read_case(conn, case_id)


# ---------------------------------------------------------------------------
# Core: submit happy path
# ---------------------------------------------------------------------------

def test_submit_happy_path_stores_all_12_fields(db):
    result = submit_form_case(db, dict(REAL_FORM))
    assert result["status"] == "inserted", result
    assert result["no_dvd"].startswith("FORM-")

    row = _row_dict(db, result["case_id"])
    assert row is not None
    # Mapped columns.
    assert row["machine_type"] == "6th Next"          # Model
    assert row["line"] == "A15"                       # Line
    assert row["department"] == "電気技術"             # Bo phan PT
    assert "lineout" in (row["investigation"] or "")  # Noi dung dieu tra
    assert row["occurred_at"] == "2023-01-05"          # Ngay phat sinh
    # New form columns.
    assert row["process_stage"] == "画像A4.2"          # Cong doan
    assert row["error_name"] == "LCD báo Close top cover"
    assert row["phenomenon"] == 'LCD画面に"Close top cover"表示'
    assert row["cause"] == "部品要因(電気)"
    assert row["countermeasure"] == "Thay PWB ENGINE ASSY."
    assert row["closed_at"] == "2023-01-10"            # Ngay dong
    assert row["report_link"] == "https://example.invalid/bao-cao/2023-001"
    # Error code split: C-code -> column G slot.
    assert row["error_code_c"] == "C0030"
    assert row["error_code_h"] is None
    # Full-fidelity snapshot in raw_json.
    raw = json.loads(row["raw_json"])
    assert raw["format"] == "form"
    assert raw["form"]["nguyen_nhan"] == "部品要因(電気)"
    # Provenance: shared manual-entry batch.
    batch = db.execute(
        "SELECT source_file, sheet_name FROM import_batches WHERE id = ?",
        (row["batch_id"],),
    ).fetchone()
    assert batch["source_file"] == "FORM-nhap-lieu"
    assert batch["sheet_name"] == "form"


def test_error_code_split_f_code_goes_to_h_column(db):
    data = dict(REAL_FORM, error_code="F000")
    result = submit_form_case(db, data)
    assert result["status"] == "inserted", result
    row = _row_dict(db, result["case_id"])
    assert row["error_code_c"] is None
    assert row["error_code_h"] == "F000"


def test_no_dvd_unique_across_submits(db):
    first = submit_form_case(db, dict(REAL_FORM))
    second = submit_form_case(
        db, dict(REAL_FORM, line="SIMULATED_LINE_B", ngay_phat_sinh="2023-02-01", ngay_dong="2023-02-05")
    )
    assert first["status"] == "inserted"
    assert second["status"] == "inserted"
    assert first["no_dvd"] != second["no_dvd"]


def test_form_batch_is_shared(db):
    submit_form_case(db, dict(REAL_FORM))
    submit_form_case(
        db, dict(REAL_FORM, line="SIMULATED_LINE_C", ngay_phat_sinh="2023-03-01", ngay_dong="2023-03-02")
    )
    batches = db.execute(
        "SELECT COUNT(*) AS n FROM import_batches WHERE source_file = 'FORM-nhap-lieu'"
    ).fetchone()["n"]
    assert batches == 1


# ---------------------------------------------------------------------------
# Validation: required fields block
# ---------------------------------------------------------------------------

REQUIRED_LABELS = {
    "cong_doan": "Công đoạn",
    "error_code": "Error code",
    "hien_tuong": "Hiện tượng",
    "nguyen_nhan": "Nguyên nhân",
    "doi_sach": "Đối sách",
}


@pytest.mark.parametrize("key,label", sorted(REQUIRED_LABELS.items()))
def test_missing_required_field_blocks(db, key, label):
    data = dict(REAL_FORM)
    data[key] = "   "
    before = count_cases(db)
    result = submit_form_case(db, data)
    assert result["status"] == "blocked"
    assert any(label in e for e in result["errors"]), result["errors"]
    assert count_cases(db) == before


def test_validate_form_reports_all_missing_at_once(db):
    result = validate_form({}, db)
    assert len(result.errors) == 5


# ---------------------------------------------------------------------------
# Validation: dates
# ---------------------------------------------------------------------------

def test_ngay_dong_before_ngay_phat_sinh_blocks(db):
    data = dict(REAL_FORM, ngay_phat_sinh="2023-01-10", ngay_dong="2023-01-05")
    result = submit_form_case(db, data)
    assert result["status"] == "blocked"
    assert any("Ngày đóng" in e for e in result["errors"])


def test_ngay_dong_equal_ngay_phat_sinh_ok(db):
    data = dict(REAL_FORM, ngay_dong="2023-01-05")
    result = submit_form_case(db, data)
    assert result["status"] == "inserted", result


def test_unparseable_date_blocks(db):
    data = dict(REAL_FORM, ngay_phat_sinh="SIMULATED-not-a-date")
    result = submit_form_case(db, data)
    assert result["status"] == "blocked"


def test_optional_fields_may_be_blank(db):
    data = dict(
        REAL_FORM,
        ten_loi="",
        noi_dung_dieu_tra="",
        bo_phan_pt="",
        link_bao_cao="",
        ngay_dong="",
    )
    result = submit_form_case(db, data)
    assert result["status"] == "inserted", result


# ---------------------------------------------------------------------------
# Glossary: unknown code warns, never blocks
# ---------------------------------------------------------------------------

def test_unknown_error_code_warns_but_inserts(db):
    data = dict(REAL_FORM, error_code="SIMULATED_Z9999")
    result = submit_form_case(db, data)
    assert result["status"] == "inserted", result
    assert any("lạ" in w for w in result["warnings"]), result["warnings"]


def test_known_error_code_no_warning(db):
    result = submit_form_case(db, dict(REAL_FORM))
    assert result["status"] == "inserted", result
    assert result["warnings"] == []


def test_missing_glossary_table_warns_without_crashing(tmp_path):
    path = tmp_path / "no_glossary.db"
    conn = connect(path)
    init_db(conn)  # no init_glossary -> no error_glossary table
    try:
        assert lookup_error_code(conn, "C0030") is None
        result = submit_form_case(conn, dict(REAL_FORM))
        assert result["status"] == "inserted"
        assert any("lạ" in w for w in result["warnings"])
    finally:
        conn.close()


def test_glossary_wildcard_f_system(tmp_path):
    path = tmp_path / "wildcard.db"
    conn = connect(path)
    init_db(conn)
    init_glossary(conn)
    conn.execute(
        "INSERT INTO error_glossary (code_family, code, name_vi, source_file)"
        " VALUES ('F_SYSTEM', 'F10X', 'F10x mẫu', 'test')"
    )
    conn.commit()
    try:
        assert lookup_error_code(conn, "F100") is not None
        assert lookup_error_code(conn, "SIMULATED_Q9") is None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

def test_duplicate_warns_and_is_not_inserted(db):
    first = submit_form_case(db, dict(REAL_FORM))
    assert first["status"] == "inserted"
    before = count_cases(db)
    second = submit_form_case(db, dict(REAL_FORM))
    assert second["status"] == "duplicate"
    assert second["no_dvd"] == first["no_dvd"]
    assert any("Trùng" in w for w in second["warnings"])
    assert count_cases(db) == before


def test_same_key_different_date_is_not_duplicate(db):
    submit_form_case(db, dict(REAL_FORM))
    result = submit_form_case(db, dict(REAL_FORM, ngay_phat_sinh="2023-06-01", ngay_dong="2023-06-02"))
    assert result["status"] == "inserted", result


def test_same_key_different_line_is_not_duplicate(db):
    submit_form_case(db, dict(REAL_FORM))
    result = submit_form_case(db, dict(REAL_FORM, line="SIMULATED_LINE_D"))
    assert result["status"] == "inserted", result


def test_find_duplicate_helper(db):
    inserted = submit_form_case(db, dict(REAL_FORM))
    dup = find_duplicate_case(
        db,
        model="6th Next",
        line="A15",
        error_code="C0030",
        ngay_phat_sinh="2023-01-05",
    )
    assert dup is not None
    assert dup["no_dvd"] == inserted["no_dvd"]
    assert (
        find_duplicate_case(
            db,
            model="SIMULATED_OTHER_MODEL",
            line="A15",
            error_code="C0030",
            ngay_phat_sinh="2023-01-05",
        )
        is None
    )


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------

def test_migration_idempotent_on_old_db(tmp_path):
    """Old DBs (without the form columns) gain them exactly once."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE error_cases (id INTEGER PRIMARY KEY, no_dvd TEXT)"
    )
    conn.commit()
    ensure_form_schema(conn)
    ensure_form_schema(conn)  # second run must not fail
    cols = [r[1] for r in conn.execute("PRAGMA table_info(error_cases)")]
    for name, _ddl in (
        ("process_stage", "TEXT"),
        ("error_name", "TEXT"),
        ("phenomenon", "TEXT"),
        ("cause", "TEXT"),
        ("countermeasure", "TEXT"),
        ("closed_at", "TEXT"),
        ("report_link", "TEXT"),
    ):
        assert cols.count(name) == 1
    conn.close()


def test_split_error_code():
    assert split_error_code("C0030") == ("C0030", None)
    assert split_error_code("ｃ００３０") == ("C0030", None)  # full-width
    assert split_error_code("F000") == (None, "F000")
    assert split_error_code("6000") == (None, "6000")  # JAM hex


# ---------------------------------------------------------------------------
# Chat action
# ---------------------------------------------------------------------------

def _request(question, db_path):
    return ChatActionRequest(
        question=question, context={"error_cases_db": str(db_path)}
    )


def test_action_registered():
    chat_action.reset_actions()
    register()
    names = [a.name for a in chat_action.registered_actions()]
    assert ACTION_NAME in names


def test_action_renders_blank_template(tmp_path):
    db_file = tmp_path / "tpl.db"
    conn = connect(db_file)
    init_db(conn)
    conn.close()
    chat_action.reset_actions()
    register()
    req = _request("nhập báo cáo lỗi", db_file)
    outcome = _handler(req)
    assert outcome is not None
    text = outcome.blocks[0].text
    for f in CASE_FORM_FIELDS:
        assert f["label"] in text
    assert "nộp báo cáo" in text


def test_action_accepts_filled_form(tmp_path):
    path = tmp_path / "action.db"
    conn = connect(path)
    init_db(conn)
    init_glossary(conn)
    conn.execute(
        "INSERT INTO error_glossary (code_family, code, name_vi, source_file)"
        " VALUES ('C_CALL', 'C0030', 'mẫu', 'test')"
    )
    conn.commit()
    conn.close()

    chat_action.reset_actions()
    register()
    filled = """nộp báo cáo
Model: 6th Next
Line: A15
Công đoạn: 画像A4.2
Tên lỗi: LCD báo Close top cover
Error code: C0030
Hiện tượng: LCD画面に"Close top cover"表示
Nội dung điều tra: lineout kiểm tra
Nguyên nhân: 部品要因(電気)
Đối sách: Thay PWB ENGINE ASSY.
Bộ phận PT: 電気技術
Ngày phát sinh: 2023-01-05
Ngày đóng: 2023-01-10
Link báo cáo: https://example.invalid/bao-cao/2023-001
"""
    outcome = _handler(_request(filled, path))
    assert outcome is not None
    text = outcome.blocks[0].text
    assert "Đã ghi nhận" in text
    assert "FORM-" in text

    conn = connect(path)
    try:
        assert count_cases(conn) == 1
        row = conn.execute("SELECT * FROM error_cases").fetchone()
        assert row["phenomenon"] == 'LCD画面に"Close top cover"表示'
        assert row["cause"] == "部品要因(電気)"
    finally:
        conn.close()


def test_action_shows_validation_errors_without_insert(tmp_path):
    path = tmp_path / "action2.db"
    conn = connect(path)
    init_db(conn)
    conn.close()

    chat_action.reset_actions()
    register()
    filled = """nộp báo cáo
Model: 6th Next
Line: A15
Công đoạn: 画像A4.2
Error code: C0030
Hiện tượng: màn hình báo lỗi
"""
    # Missing: Nguyên nhân, Đối sách (required).
    outcome = _handler(_request(filled, path))
    assert outcome is not None
    text = outcome.blocks[0].text
    assert "Chưa ghi được" in text
    assert "Nguyên nhân" in text
    assert "Đối sách" in text

    conn = connect(path)
    try:
        assert count_cases(conn) == 0
    finally:
        conn.close()


def test_action_no_db_returns_none_and_creates_nothing(tmp_path):
    missing = tmp_path / "khong-co-db.db"
    chat_action.reset_actions()
    register()
    assert _handler(_request("nhập báo cáo lỗi", missing)) is None
    assert not missing.exists()


def test_action_duplicate_warns(tmp_path):
    path = tmp_path / "action3.db"
    conn = connect(path)
    init_db(conn)
    conn.close()

    chat_action.reset_actions()
    register()
    filled = """nộp báo cáo
Model: 6th Next
Line: A15
Công đoạn: 調整A1.1
Error code: C0030
Hiện tượng: LCD báo lỗi
Nguyên nhân: 部品要因(電気)
Đối sách: kiểm tra lại
Ngày phát sinh: 2023-01-05
"""
    first = _handler(_request(filled, path))
    assert "Đã ghi nhận" in first.blocks[0].text
    second = _handler(_request(filled, path))
    assert "Không nhập đúp" in second.blocks[0].text

    conn = connect(path)
    try:
        assert count_cases(conn) == 1
    finally:
        conn.close()


def test_resolve_db_path_prefers_context(tmp_path):
    ctx_path = tmp_path / "ctx.db"
    ctx_path.touch()
    req = _request("nhập báo cáo", ctx_path)
    assert resolve_db_path(req) == ctx_path


def test_parse_form_text_handles_aliases_and_noise():
    parsed = parse_form_text(
        "nộp báo cáo\n"
        "- Model: 6th Next\n"
        "Line : A15\n"
        "Mã lỗi: C0030\n"
        "Hiện tượng: màn hình đen\n"
        "dòng này không có hai chấm nên bị bỏ qua\n"
        "Nguyên nhân: chập điện\n"
        "Đối sách: thay board\n"
        "Công đoạn: 調整A1.1\n"
    )
    assert parsed["model"] == "6th Next"
    assert parsed["line"] == "A15"
    assert parsed["error_code"] == "C0030"
    assert parsed["hien_tuong"] == "màn hình đen"
    assert parsed["nguyen_nhan"] == "chập điện"
    assert parsed["doi_sach"] == "thay board"
    assert parsed["cong_doan"] == "調整A1.1"


def test_looks_like_filled_form():
    assert looks_like_filled_form("Model: a\nLine: b\nError code: C0030\n")
    assert not looks_like_filled_form("nhập báo cáo lỗi giúp tôi")
    assert not looks_like_filled_form("Model: a\nLine: b\n")


def test_render_blank_form_lists_all_labels_and_marks_required():
    text = render_blank_form()
    for f in CASE_FORM_FIELDS:
        assert f["label"] in text
        if f["required"]:
            assert f"**{f['label']}** *" in text
