"""Tests for error_cases.trend_analysis (Buoc 4: trend analysis & early warning).

DỮ LIỆU MÔ PHỎNG — SIMULATED DATA ONLY:
Mọi bản ghi trong file này đều được sinh ngẫu nhiên bằng random.Random với
seed cố định (SIMULATED_SEED) và KHÔNG phải dữ liệu sản xuất. Tuy nhiên,
GIÁ TRỊ DOMAIN (tên model/line/công đoạn/loại lỗi) được lấy từ dữ liệu
thật: file "Loi KDTPS.xlsx", sheet "History KDTPS" (15.737 dòng) tại
~/workspace/aios_data/dieu_tra_loi/Điều chỉnh/Lịch sử lỗi/ — ví dụ model
thật: Virgo, Iris2024, Iris2020, Sirius2, Libra; line thật: C33, C35, C21;
công đoạn thật: 調整A1, 調整A2; loại lỗi thật: ERROR, C CALL, JAM, 外観.
Số lượng bản ghi và phân bố thời gian là MÔ PHỎNG, không phản ánh thực tế.
Các hằng SIMULATED_* đánh dấu rõ nguồn dữ liệu.
"""

import importlib.util
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Dữ liệu mô phỏng (SIMULATED_*): load module trực tiếp từ file để tránh
# phụ thuộc xlrd của package error_cases trong môi trường test này.
# ---------------------------------------------------------------------------

# Giá trị domain THẬT trích từ Loi KDTPS.xlsx (History KDTPS, 15.737 dòng).
# Số lượng/phân bố do test tự sinh -> vẫn là DỮ LIỆU MÔ PHỎNG.
SIMULATED_SEED = 20260928
SIMULATED_MODELS = ["Virgo", "Iris2024", "Iris2020", "Sirius2", "Libra"]
SIMULATED_LINES = ["C33", "C35", "C21", "A23"]
SIMULATED_STAGES = ["調整A1", "調整A2", "調整A6", "調整A7"]
SIMULATED_ERRCATS = ["ERROR", "C CALL", "JAM", "外観", "画像"]
SIMULATED_SPIKE_MODEL = "Virgo"  # model thật có sản lượng lỗi cao nhất (2.808 vụ)
SIMULATED_START = datetime(2026, 7, 1)  # ngày bắt đầu dữ liệu mô phỏng

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src" / "aios_habit" / "error_cases" / "trend_analysis.py"
)
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "src" / "aios_habit" / "error_cases" / "schema.sql"
)


def _load_trend_analysis():
    import sys
    spec = importlib.util.spec_from_file_location("trend_analysis_sim", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["trend_analysis_sim"] = mod  # dataclass cần tra sys.modules
    spec.loader.exec_module(mod)
    return mod


ta = _load_trend_analysis()


def make_simulated_records(n=600, seed=SIMULATED_SEED, spike_weeks=2):
    """Sinh n bản ghi mô phỏng.

    Model Virgo (thật, sản lượng lỗi cao nhất) được bơm tỉ lệ cao bất
    thường trong ``spike_weeks`` tuần cuối để kiểm tra cảnh báo ngưỡng.
    Toàn bộ số lượng/phân bố là mô phỏng, không phải số liệu thật.
    """
    rng = random.Random(seed)
    records = []
    for i in range(n):
        day_offset = rng.randrange(0, 56)  # 8 tuần dữ liệu mô phỏng
        occurred = SIMULATED_START + timedelta(
            days=day_offset, hours=rng.randrange(0, 24))
        # spike: tuần cuối ưu tiên Virgo
        if day_offset >= 56 - 7 * spike_weeks and rng.random() < 0.55:
            model = SIMULATED_SPIKE_MODEL
        else:
            model = rng.choice(SIMULATED_MODELS)
        records.append({
            "model": model,
            "line": rng.choice(SIMULATED_LINES),
            "stage": rng.choice(SIMULATED_STAGES),
            "paper": "SIM-PAPER",
            "machine": "SIM-MACHINE-1",
            "error_code": rng.choice(SIMULATED_ERRCATS),
            "occurred_at": occurred,
        })
    return records


def make_tiny_records():
    """Bộ dữ liệu mô phỏng nhỏ, tính tay được, để kiểm tra công thức."""
    return [
        {"model": "A", "line": "L1", "stage": "S", "paper": "P", "machine": "M",
         "occurred_at": datetime(2026, 9, 1)},
        {"model": "A", "line": "L1", "stage": "S", "paper": "P", "machine": "M",
         "occurred_at": datetime(2026, 9, 2)},
        {"model": "B", "line": "L1", "stage": "S", "paper": "P", "machine": "M",
         "occurred_at": datetime(2026, 9, 2)},
        {"model": "B", "line": "L2", "stage": "S", "paper": "P", "machine": "M",
         "occurred_at": datetime(2026, 9, 8)},
    ]


# --- grouping & bucketing ----------------------------------------------------

def test_group_by_dimension_counts_simulated():
    records = make_tiny_records()
    groups = ta.group_by_dimension(records, "model")
    assert set(groups) == {"A", "B"}
    assert len(groups["A"]) == 2
    assert len(groups["B"]) == 2


def test_group_by_dimension_rejects_unknown():
    with pytest.raises(ValueError):
        ta.group_by_dimension(make_tiny_records(), "khong-co-chieu-nay")


def test_bucketize_week_sorted_simulated():
    records = make_tiny_records()
    buckets = ta.bucketize(records, "week")
    keys = list(buckets.keys())
    assert keys == sorted(keys)
    # 2026-09-01/02 -> ISO week 36, 2026-09-08 -> week 37
    assert keys == ["2026-W36", "2026-W37"]
    assert len(buckets["2026-W36"]) == 3


def test_bucket_key_periods():
    dt = datetime(2026, 9, 28, 15, 30)
    assert ta.bucket_key(dt, "day") == "2026-09-28"
    assert ta.bucket_key(dt, "week") == "2026-W40"
    assert ta.bucket_key(dt, "month") == "2026-09"
    with pytest.raises(ValueError):
        ta.bucket_key(dt, "year")


# --- incidence rates ---------------------------------------------------------

def test_incidence_rate_known_values_simulated():
    table = ta.incidence_table(make_tiny_records(), "model", period="week")
    w36 = table["2026-W36"]
    # tuần 36: A=2/3, B=1/3
    assert w36["A"]["count"] == 2
    assert w36["B"]["count"] == 1
    assert w36["A"]["rate"] == pytest.approx(2 / 3)
    assert w36["B"]["rate"] == pytest.approx(1 / 3)
    # tuần 37: chỉ B
    assert table["2026-W37"]["B"]["rate"] == pytest.approx(1.0)


def test_incidence_rates_sum_to_one_per_bucket_simulated():
    table = ta.incidence_table(make_simulated_records(), "model", period="week")
    assert len(table) > 0
    for bucket, cell in table.items():
        assert sum(v["rate"] for v in cell.values()) == pytest.approx(1.0)


def test_empty_records_yield_empty_table():
    assert ta.incidence_table([], "model") == {}
    assert ta.check_thresholds({}, "model", 0.2) == []


# --- threshold alerts --------------------------------------------------------

def test_check_thresholds_fires_for_spike_group_simulated():
    records = make_simulated_records(n=800, spike_weeks=2)
    table = ta.incidence_table(records, "model", period="week")
    alerts = ta.check_thresholds(table, "model", 0.2)
    assert alerts, "nhóm Virgo spike (dữ liệu mô phỏng) phải vượt ngưỡng 20%"
    assert any(a.group == SIMULATED_SPIKE_MODEL for a in alerts)
    hit = next(a for a in alerts if a.group == SIMULATED_SPIKE_MODEL)
    assert hit.rate > 0.2
    assert "vượt ngưỡng" in hit.message  # thông báo tiếng Việt


def test_check_thresholds_quiet_below_threshold_simulated():
    records = make_simulated_records(n=800, spike_weeks=0)
    table = ta.incidence_table(records, "model", period="week")
    alerts = ta.check_thresholds(table, "model", 0.99)
    assert alerts == []


def test_check_thresholds_per_group_mapping_simulated():
    table = ta.incidence_table(make_tiny_records(), "model", period="week")
    alerts = ta.check_thresholds(table, "model", {"A": 0.5, "B": 0.9})
    groups = {a.group for a in alerts}
    # tuần 36: A=66.7% > 50% -> báo; B=33.3% < 90% -> không
    assert "A" in groups
    assert not any(a.group == "B" and a.bucket == "2026-W36" for a in alerts)


def test_detect_rising_trend_simulated():
    # dựng dữ liệu mô phỏng tăng dần rõ rệt cho nhóm R
    records = []
    base = datetime(2026, 8, 3)  # thứ Hai
    for week in range(4):
        for i in range(week + 1):  # 1,2,3,4 lỗi/tuần
            records.append({
                "model": "R", "line": "L", "stage": "S", "paper": "P",
                "machine": "M",
                "occurred_at": base + timedelta(weeks=week, days=i % 7),
            })
        for _ in range(10):  # nền cố định để tỉ lệ tăng thật
            records.append({
                "model": "N", "line": "L", "stage": "S", "paper": "P",
                "machine": "M",
                "occurred_at": base + timedelta(weeks=week),
            })
    table = ta.incidence_table(records, "model", period="week")
    alerts = ta.detect_rising_trend(table, "model", min_buckets=3)
    assert any(a.group == "R" for a in alerts)
    assert "tăng" in alerts[0].message


# --- report ------------------------------------------------------------------

def test_generate_report_markdown_sections_simulated():
    records = make_simulated_records(n=300)
    table = ta.incidence_table(records, "line", period="week")
    alerts = ta.check_thresholds(table, "line", 0.2)
    md = ta.generate_report(table, "line", "week", alerts)
    assert md.startswith("# Báo cáo xu hướng lỗi")
    assert "## Bảng tỉ lệ phát sinh" in md
    assert "## Cảnh báo" in md
    assert "| Kỳ | Nhóm | Số lỗi | Tỉ lệ |" in md
    assert "C33" in md


def test_generate_report_empty_data_vietnamese():
    md = ta.generate_report({}, "model", "week", [])
    assert "không có dữ liệu" in md
    assert "Không có cảnh báo" in md


def test_run_periodic_report_end_to_end_simulated():
    records = make_simulated_records(n=500)
    md = ta.run_periodic_report(
        records, dimensions=("model", "line"), period="week", thresholds=0.2)
    assert "Model" in md and "Line" in md
    assert SIMULATED_SPIKE_MODEL in md  # nhóm spike mô phỏng xuất hiện


# --- SQLite adapter ----------------------------------------------------------

def _simulated_db():
    """Tạo DB :memory: từ schema.sql thật, chèn dữ liệu mô phỏng."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
        " VALUES ('SIMULATED_file.xlsx', 'simulated-sha', 'Sheet1')"
    )
    rows = [
        (1, 2, "SIM-001", "Máy in", "Virgo", "C33", "C0030",
         "2026-09-01 10:00:00", '{"stage": "調整A1"}'),
        (1, 3, "SIM-002", "Máy in", "Virgo", "C33", "C0120",
         "2026-09-02 11:00:00", '{"stage": "調整A2"}'),
        (1, 4, "SIM-003", "KIT", "Iris2024", "C35", "F000",
         "2026-09-08 09:00:00", '{}'),
    ]
    conn.executemany(
        "INSERT INTO error_cases (batch_id, source_row, no_dvd, sheet_type,"
        " machine_type, line, error_code_c, created_at, raw_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return conn


def test_fetch_records_maps_schema_columns_simulated():
    conn = _simulated_db()
    try:
        records = ta.fetch_records(conn)
        assert len(records) == 3
        assert records[0]["model"] == "Virgo"
        assert records[0]["line"] == "C33"
        assert records[0]["stage"] == "調整A1"  # từ raw_json
        assert records[2]["stage"] == ta.MISSING_GROUP  # thiếu -> placeholder
        assert records[0]["error_code"] == "C0030"
    finally:
        conn.close()


def test_fetch_records_since_until_filter_simulated():
    conn = _simulated_db()
    try:
        records = ta.fetch_records(conn, since="2026-09-08", until="2026-09-09")
        assert len(records) == 1
        assert records[0]["model"] == "Iris2024"
    finally:
        conn.close()


def test_run_periodic_report_from_sqlite_simulated():
    conn = _simulated_db()
    try:
        md = ta.run_periodic_report(
            conn, dimensions=("model",), period="week", thresholds=0.9)
        assert "Virgo" in md
        assert "2026-W36" in md
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# date-map (ticket): trend buckets by the real occurrence date
# ---------------------------------------------------------------------------

def _simulated_db_with_occurrence():
    """DB :memory: có occurred_at thật (SIMULATED), created_at khác xa."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
        " VALUES ('SIMULATED_date.xlsx', 'simulated-sha-date', 'Sheet1')"
    )
    conn.execute(
        "INSERT INTO error_cases (batch_id, source_row, no_dvd, sheet_type,"
        " machine_type, line, error_code_c, created_at, occurred_at, raw_json)"
        " VALUES (1, 2, 'SIM-D/001', 'Máy in', 'Virgo', 'C33', 'C0030',"
        " '2026-09-01 10:00:00', '2023-05-05', '{}')"
    )
    conn.commit()
    return conn


def test_fetch_records_prefers_occurred_at_simulated():
    conn = _simulated_db_with_occurrence()
    try:
        records = ta.fetch_records(conn)
        assert records[0]["occurred_at"] == "2023-05-05"  # không phải created_at
        assert list(ta.bucketize(records, "week")) == ["2023-W18"]
    finally:
        conn.close()


def test_fetch_records_since_until_filters_on_occurrence_simulated():
    conn = _simulated_db_with_occurrence()
    try:
        inside = ta.fetch_records(conn, since="2023-05-01", until="2023-06-01")
        assert len(inside) == 1
        outside = ta.fetch_records(conn, since="2026-09-01", until="2026-09-02")
        assert outside == []  # created_at (import time) không còn quyết định
    finally:
        conn.close()
