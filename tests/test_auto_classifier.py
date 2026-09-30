"""Step-5 tests: auto_classifier (phân loại tự động + cảnh báo tái phát).

====================================================================
DỮ LIỆU MÔ PHỎNG — SIMULATED DATA
--------------------------------------------------------------------
Mọi bản ghi, mã lỗi, hiện tượng và nội dung điều tra trong file này
đều do random tạo ra (seed cố định) hoặc viết tay cho mục đích kiểm thử,
được gắn mác SIMULATED_* rõ ràng. KHÔNG phải dữ liệu thật của công ty,
KHÔNG được dùng để huấn luyện hay đối chiếu sản xuất.
Nội dung fixture dựa trên từ vựng domain thật (Iris/Sirius LSU, JIG
BOWSKEW 4/2 BEAM, Ranks S, xưởng KDTVN, phân tích 4M từ file
AI_LSU_du_doan_loi.xlsx) để người trong ngành đọc thấy đúng chất.
====================================================================
"""
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from aios_habit.error_cases import auto_classifier as ac
from aios_habit.error_cases import init_db, init_glossary, start_batch, upsert_case

SIMULATED_SEED = 20260928
SIMULATED_SOURCE = "SIMULATED_buoc5_history.xls"


def _ts(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


@pytest.fixture()
def hist_conn():
    """In-memory error_cases store seeded with SIMULATED history rows."""
    rng = random.Random(SIMULATED_SEED)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    batch = start_batch(
        conn,
        source_file=SIMULATED_SOURCE,
        file_sha256="0" * 64,
        sheet_name="SIMULATED",
        sheet_type="Máy in",
        notes="SIMULATED seed data for step-5 tests",
    )
    machines = ["SIM_Iris-LSU", "SIM_Sirius-LSU"]  # model thật, mác SIMULATED
    lines = ["SIM_KDTVN-L1", "SIM_KDTVN-L2"]  # xưởng KDTVN thật, mác SIMULATED
    seed_rows = [
        # (no_dvd, code_c, code_h, investigation, machine, line, hours_ago)
        ("SIM-LSU/001", "C0030", "",
         "Hiệu chỉnh JIG BOWSKEW 4 BEAM, đo lại kích thước linh kiện lot (SIMULATED)",
         machines[0], lines[0], 2),
        ("SIM-LSU/002", "C0030", "",
         "Căn chỉnh lại JIG BOWSKEW 2 BEAM theo Ranks S (SIMULATED)",
         machines[0], lines[0], 5),
        ("SIM-LSU/003", "C0040", "", "Thay board mạch nguồn (SIMULATED)",
         machines[1], lines[1], 3),
        ("SIM-LSU/004", "", "6000",
         "Lấy giấy kẹt JAM 6000 ở cụm sấy Iris LSU (SIMULATED)",
         machines[0], lines[0], 30),  # outside the 12h window
    ]
    for no_dvd, code_c, code_h, inv, mach, line, ago in seed_rows:
        upsert_case(
            conn,
            batch_id=batch,
            source_row=rng.randint(1, 999),
            fields={
                "no_dvd": no_dvd,
                "sheet_type": "Máy in",
                "department": "Bảo trì",
                "machine_type": mach,
                "line": line,
                "error_code_c": code_c,
                "error_code_h": code_h,
                "investigation": inv,
            },
        )
        conn.execute(
            "UPDATE error_cases SET created_at = ? WHERE no_dvd = ?",
            (_ts(ago), no_dvd),
        )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def gloss_conn():
    """Tiny SIMULATED glossary (hand-written, not the real source files)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_glossary(conn)
    conn.execute(
        """INSERT INTO error_glossary
           (code_family, code, code_sub, name_vi, cause, remedy, source_file)
           VALUES ('C_CALL', 'C0030', '',
                   'SIMULATED: lỗi JIG điều chỉnh Ranks S (Iris LSU)',
                   'SIMULATED: hiệu suất JIG giảm sút',
                   'SIMULATED: hiệu chỉnh lại JIG theo Ranks S',
                   'SIMULATED_glossary.xls')"""
    )
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# 1. Rule-based classification on SIMULATED inputs
# ---------------------------------------------------------------------------

def test_classify_cause_groups_simulated():
    cases = [
        ("C0031", "Lỗi tái phát sau khi reset JIG, hiện tượng lặp lại nhiều lần",
         "lap_lai"),
        ("C0032", "Bản vẽ thiết kế linh kiện nhựa sai kích thước, dung sai không đạt",
         "thiet_ke"),
        ("C0033", "Sensor cảm biến hỏng, cần thay thế linh kiện mới",
         "linh_kien"),
        ("XYZ999", "Hiện tượng lạ chưa xác định, cần theo dõi thêm", "khac"),
    ]
    for code, phenomenon, expected in cases:
        result = ac.classify_error(code, phenomenon=phenomenon)
        assert result.nhom_nguyen_nhan == expected, (code, phenomenon)
        assert 0.0 < result.confidence <= 1.0
        assert result.reasons  # Vietnamese audit trail is never empty


def test_classify_unknown_code_falls_back_safely():
    result = ac.classify_error("???", phenomenon="???")
    assert result.nhom_nguyen_nhan == "khac"
    assert result.code_family is None
    assert result.confidence < 0.5


def test_classify_department_and_stage_simulated():
    result = ac.classify_error("C0034", phenomenon="Chập mạch điện gây mất nguồn")
    assert result.bo_phan == "Điện"
    result = ac.classify_error("6000", phenomenon="Kẹt giấy tại cụm sấy khi in ấn")
    assert result.cong_doan == "In ấn"


def test_glossary_lookup_enriches_classification(gloss_conn):
    result = ac.classify_error("C0030", glossary_conn=gloss_conn)
    assert result.code_family == "C_CALL"
    assert result.bo_phan == "Bảo trì"  # family default
    assert any("glossary" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# 2. History matching: 100% of new errors are compared
# ---------------------------------------------------------------------------

def test_match_history_ranks_exact_code_first(hist_conn):
    matches = ac.match_history(
        hist_conn, "C0030", machine_type="SIM_Iris-LSU", line="SIM_KDTVN-L1",
        investigation="JIG BOWSKEW 4 BEAM quá nhiệt",
    )
    assert matches, "expected similar SIMULATED records"
    assert matches[0].case["error_code_c"] == "C0030"
    assert "mã lỗi trùng khớp" in matches[0].matched_on
    scores = [m.score for m in matches]
    assert scores == sorted(scores, reverse=True)


def test_match_history_always_returns_list(hist_conn):
    # 100% đối chiếu: even unknown codes get a (possibly empty) list,
    # never None and never an exception.
    for code in ["C0030", "ZZZ999", "", "01"]:
        matches = ac.match_history(hist_conn, code)
        assert isinstance(matches, list), code


# ---------------------------------------------------------------------------
# 3. Recurrence detection
# ---------------------------------------------------------------------------

def test_detect_recurrence_fires_alert(hist_conn):
    alert = ac.detect_recurrence(hist_conn, "C0030", window_hours=12.0,
                                 threshold=2)
    assert alert is not None
    assert alert.code == "C0030"
    assert alert.count == 3  # 2 SIMULATED in-window + the new one
    assert "3 lần" in alert.message_vi
    assert "Đề xuất đối sách" in alert.message_vi
    assert alert.suggested_remedy is not None
    assert "SIMULATED" in alert.suggested_remedy


def test_detect_recurrence_ignores_records_outside_window():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    batch = start_batch(conn, source_file=SIMULATED_SOURCE,
                        file_sha256="1" * 64, sheet_name="SIMULATED",
                        sheet_type="Máy in")
    upsert_case(conn, batch_id=batch, source_row=1, fields={
        "no_dvd": "SIM/090", "sheet_type": "Máy in",
        "error_code_c": "C0099", "investigation": "SIMULATED old case",
    })
    conn.execute("UPDATE error_cases SET created_at = ?",
                 (_ts(30),))
    conn.commit()
    alert = ac.detect_recurrence(conn, "C0099", window_hours=12.0, threshold=2)
    assert alert is None  # only the new case itself -> not recurring
    conn.close()


def test_detect_recurrence_without_remedy_in_history():
    # SIMULATED record with an empty investigation -> the alert must fall
    # back to the "no remedy in history" message branch.
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    batch = start_batch(conn, source_file=SIMULATED_SOURCE,
                        file_sha256="2" * 64, sheet_name="SIMULATED",
                        sheet_type="Máy in")
    upsert_case(conn, batch_id=batch, source_row=1, fields={
        "no_dvd": "SIM/091", "sheet_type": "Máy in",
        "error_code_c": "C0098", "investigation": "",
    })
    conn.commit()
    alert = ac.detect_recurrence(conn, "C0098", window_hours=12.0, threshold=2)
    assert alert is not None
    assert alert.suggested_remedy is None
    assert "Chưa có đối sách trong lịch sử" in alert.message_vi
    conn.close()


def test_detect_recurrence_window_uses_occurred_at_simulated():
    """date-map: cửa sổ tái phát tính theo ngày phát sinh thật khi có."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    batch = start_batch(conn, source_file=SIMULATED_SOURCE,
                        file_sha256="3" * 64, sheet_name="SIMULATED",
                        sheet_type="Máy in")
    ref = datetime.now(timezone.utc)
    rows = [
        # (no_dvd, created_at, occurred_at)
        ("SIM-DATE/001", _ts(30), ref.strftime("%Y-%m-%d")),                 # nhập lâu, ngày thật hôm nay -> tính
        ("SIM-DATE/002", _ts(0), (ref - timedelta(days=200)).strftime("%Y-%m-%d")),  # nhập mới, ngày thật cũ -> không tính
        ("SIM-DATE/003", _ts(2), None),                                       # không có ngày thật -> fallback created_at -> tính
    ]
    for i, (no_dvd, created, occurred) in enumerate(rows, start=1):
        upsert_case(conn, batch_id=batch, source_row=i, fields={
            "no_dvd": no_dvd, "sheet_type": "Máy in",
            "error_code_c": "C0777", "investigation": f"SIMULATED {no_dvd}",
        })
        conn.execute(
            "UPDATE error_cases SET created_at = ?, occurred_at = ? WHERE no_dvd = ?",
            (created, occurred, no_dvd),
        )
    conn.commit()
    alert = ac.detect_recurrence(conn, "C0777", window_hours=12.0, threshold=2, now=ref)
    assert alert is not None
    assert alert.count == 3  # 001 + 003 + ca mới; 002 bị loại vì ngày thật nằm ngoài cửa sổ
    assert "3 lần" in alert.message_vi
    conn.close()


# ---------------------------------------------------------------------------
# 4. Accuracy is measurable on a SIMULATED labeled set
# ---------------------------------------------------------------------------

SIMULATED_LABELED = [
    {"error_code": "C0031",
     "phenomenon": "Lỗi tái phát sau khi reset JIG, hiện tượng lặp lại nhiều lần",
     "expected": {"nhom_nguyen_nhan": "lap_lai",
                  "cong_doan": None, "bo_phan": None}},
    {"error_code": "C0032",
     "phenomenon": "Bản vẽ thiết kế linh kiện nhựa sai kích thước, dung sai không đạt",
     "expected": {"nhom_nguyen_nhan": "thiet_ke",
                  "cong_doan": None, "bo_phan": "Thiết kế"}},
    {"error_code": "C0033",
     "phenomenon": "Sensor cảm biến hỏng, cần thay thế linh kiện mới",
     "expected": {"nhom_nguyen_nhan": "linh_kien",
                  "cong_doan": None, "bo_phan": "Điện"}},
    {"error_code": "XYZ999",
     "phenomenon": "Hiện tượng lạ chưa xác định, cần theo dõi thêm",
     "expected": {"nhom_nguyen_nhan": "khac",
                  "cong_doan": None, "bo_phan": None}},
    {"error_code": "C0034",
     "phenomenon": "Chập mạch điện board nguồn gây mất nguồn đột ngột",
     "expected": {"nhom_nguyen_nhan": "linh_kien",
                  "cong_doan": None, "bo_phan": "Điện"}},
    {"error_code": "C0035",
     "phenomenon": "Vít lỏng, bánh răng mòn gây rung",
     "expected": {"nhom_nguyen_nhan": "linh_kien",
                  "cong_doan": None, "bo_phan": "Cơ khí"}},
    {"error_code": "C0036",
     "phenomenon": "Thao tác vận hành sai quy trình chuẩn",
     "expected": {"nhom_nguyen_nhan": "khac",
                  "cong_doan": "Vận hành", "bo_phan": "Vận hành"}},
    {"error_code": "6000",
     "phenomenon": "Kẹt giấy tại cụm sấy khi in ấn",
     "expected": {"nhom_nguyen_nhan": "khac",
                  "cong_doan": "In ấn", "bo_phan": "Vận hành"}},
    {"error_code": "01",
     "phenomenon": "Lỗi điều chỉnh JIG Ranks S tự động, cần căn chỉnh lại",
     "expected": {"nhom_nguyen_nhan": "khac",
                  "cong_doan": "Điều chỉnh", "bo_phan": "Kỹ thuật"}},
    {"error_code": "F1001",
     "phenomenon": "Board mạch cháy, chập điện",
     "expected": {"nhom_nguyen_nhan": "linh_kien",
                  "cong_doan": None, "bo_phan": "Điện"}},
    {"error_code": "C0041",
     "phenomenon": "Lỗi tái phát, hiện tượng lặp lại đúng như lần trước",
     "expected": {"nhom_nguyen_nhan": "lap_lai",
                  "cong_doan": None, "bo_phan": None}},
    {"error_code": "C0042",
     "phenomenon": "Bảo dưỡng định kỳ, vệ sinh máy",
     "expected": {"nhom_nguyen_nhan": "khac",
                  "cong_doan": "Bảo trì", "bo_phan": "Bảo trì"}},
]


def test_evaluate_accuracy_is_measurable():
    acc = ac.evaluate_accuracy(SIMULATED_LABELED)
    assert acc["n"] == len(SIMULATED_LABELED)
    for field in ("nhom_nguyen_nhan", "cong_doan", "bo_phan"):
        assert field in acc
        assert 0.0 <= acc[field] <= 1.0, field
    # The SIMULATED set is designed with clear keywords; the rule-based
    # classifier should get most of them right.
    assert acc["nhom_nguyen_nhan"] >= 0.75


# ---------------------------------------------------------------------------
# 5. Full pipeline
# ---------------------------------------------------------------------------

def test_classify_new_error_full_pipeline(hist_conn, gloss_conn):
    out = ac.classify_new_error(
        hist_conn, "C0030",
        phenomenon="JIG BOWSKEW 4 BEAM quá nhiệt, sensor báo lỗi",
        machine_type="SIM_Iris-LSU", line="SIM_KDTVN-L1",
        glossary_conn=gloss_conn,
    )
    assert out["history_checked"] is True
    cls = out["classification"]
    assert cls.error_code == "C0030"
    assert cls.code_family == "C_CALL"
    assert isinstance(out["history_matches"], list)
    assert out["history_matches"], "SIMULATED history has C0030 records"
    alert = out["recurrence_alert"]
    assert alert is not None
    assert "lần" in alert.message_vi


def test_classify_new_error_unknown_code_no_crash(hist_conn):
    out = ac.classify_new_error(hist_conn, "ZZZ999", phenomenon="lạ")
    assert out["history_checked"] is True
    assert out["classification"].nhom_nguyen_nhan == "khac"
    assert isinstance(out["history_matches"], list)
