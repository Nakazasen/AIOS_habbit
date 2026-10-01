"""B4 tests: periodic trend report + threshold alerts + chart by mail.

DỮ LIỆU MÔ PHỎNG — SIMULATED DATA ONLY (SIMULATED_*):
mọi bản ghi trong file này đều do test tự dựng, KHÔNG phải dữ liệu sản
xuất. GIÁ TRỊ DOMAIN là thật, trích từ sheet "History KDTPS" của file
Loi KDTPS.xlsx (15.737 dòng) tại ~/workspace/aios_data/dieu_tra_loi/ —
model thật: Virgo, Iris2024, Iris2020, Sirius2, Libra; line thật: C33,
C35, C21; công đoạn thật: 調整A1, 調整A2; thiết bị thật: "PWB MAIN ASSY
WITH SOFTWARE", "LCD OPERATION"; phân loại thật: ERROR, C CALL, JAM,
外観. Số lượng, phân bố thời gian và các đợt spike đều là MÔ PHỎNG.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from aios_habit.error_cases import trend_notify as tn
from aios_habit.error_cases.trend_analysis import (
    MISSING_GROUP,
    fetch_records,
    incidence_table,
)

# --- giá trị domain THẬT (History KDTPS, Loi KDTPS.xlsx) ----------------------
SIMULATED_MODELS = ["Virgo", "Iris2024", "Iris2020", "Sirius2", "Libra"]
SIMULATED_LINES = ["C33", "C35", "C21"]
SIMULATED_STAGES = ["調整A1", "調整A2"]
SIMULATED_MACHINES = ["PWB MAIN ASSY WITH SOFTWARE", "LCD OPERATION"]

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "src" / "aios_habit" / "error_cases" / "schema.sql"
)


def make_tiny_trend_records():
    """Mẫu mô phỏng nhỏ, tính tay được (2 tuần ISO).

    Tuần 36: A=2/3, B=1/3. Tuần 37: A=1/4, B=3/4.
    """
    recs = []

    def add(model, day, n):
        for _ in range(n):
            recs.append({
                "model": model,
                "line": "C33",
                "stage": "調整A1",
                "paper": MISSING_GROUP,
                "machine": "PWB MAIN ASSY WITH SOFTWARE",
                "occurred_at": datetime(2026, 9, day),
            })

    add("A", 1, 2)
    add("B", 2, 1)
    add("A", 8, 1)
    add("B", 8, 3)
    return recs


def make_spike_records():
    """Mô phỏng: model Virgo vượt ngưỡng 50% ở tuần cuối (dữ liệu mô phỏng)."""
    recs = []
    for day in (1, 2, 3):
        for _ in range(2):
            recs.append({
                "model": "Iris2024", "line": "C33", "stage": "調整A1",
                "paper": MISSING_GROUP, "machine": "LCD OPERATION",
                "occurred_at": datetime(2026, 9, day),
            })
    for day in (8, 9, 10):
        for _ in range(4):  # Virgo 4/5 = 80% tuần 37
            recs.append({
                "model": "Virgo", "line": "C35", "stage": "調整A2",
                "paper": MISSING_GROUP, "machine": "PWB MAIN ASSY WITH SOFTWARE",
                "occurred_at": datetime(2026, 9, day),
            })
        recs.append({
            "model": "Iris2024", "line": "C35", "stage": "調整A2",
            "paper": MISSING_GROUP, "machine": "PWB MAIN ASSY WITH SOFTWARE",
            "occurred_at": datetime(2026, 9, day),
        })
    return recs


# --- tỉ lệ tính tay -----------------------------------------------------------

def test_tiny_rates_match_hand_computation():
    table = incidence_table(make_tiny_trend_records(), "model", period="week")
    assert table["2026-W36"]["A"]["rate"] == pytest.approx(2 / 3)
    assert table["2026-W36"]["B"]["rate"] == pytest.approx(1 / 3)
    assert table["2026-W37"]["A"]["rate"] == pytest.approx(1 / 4)
    assert table["2026-W37"]["B"]["rate"] == pytest.approx(3 / 4)
    assert table["2026-W36"]["A"]["count"] == 2


def test_spike_group_rate_matches_hand_computation():
    table = incidence_table(make_spike_records(), "model", period="week")
    assert table["2026-W37"]["Virgo"]["rate"] == pytest.approx(4 / 5)
    # Virgo không xuất hiện tuần 36 -> vắng mặt (không phải tỉ lệ 0)
    assert "Virgo" not in table["2026-W36"]


# --- kho ngưỡng (người dùng thiết lập, lưu ngoài Git) --------------------------

def test_threshold_store_roundtrip_tmp(tmp_path):
    path = tmp_path / "nguong.json"
    store = {"model": {"Virgo": 0.35, "__default__": 0.2}, "line": {}}
    tn.save_thresholds(store, path)
    assert json.loads(path.read_text(encoding="utf-8"))["model"]["Virgo"] == 0.35
    assert tn.load_thresholds(path) == {"model": {"Virgo": 0.35, "__default__": 0.2}}


def test_load_thresholds_fail_soft_tmp(tmp_path):
    assert tn.load_thresholds(tmp_path / "khong-co.json") == {}
    bad = tmp_path / "hong.json"
    bad.write_text("{khong phai json", encoding="utf-8")
    assert tn.load_thresholds(bad) == {}
    dirty = tmp_path / "ban.json"
    dirty.write_text(json.dumps({"model": {"A": "cao", "B": 1.5, "C": 0.4}}),
                     encoding="utf-8")
    assert tn.load_thresholds(dirty) == {"model": {"C": 0.4}}


def test_threshold_for_fallbacks():
    store = {"model": {"Virgo": 0.35, "__default__": 0.2}}
    assert tn.threshold_for(store, "model", "Virgo") == pytest.approx(0.35)
    assert tn.threshold_for(store, "model", "Libra") == pytest.approx(0.2)
    assert tn.threshold_for(store, "line", "C33") == pytest.approx(1.0)  # không bắn
    assert tn.threshold_for({}, "model", "Virgo") == pytest.approx(1.0)


# --- fetch_records: cột chữ cái của history_29 ---------------------------------

def _simulated_letter_db(with_process_stage=True):
    conn = sqlite3.connect(":memory:")
    if with_process_stage:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        cols = ("batch_id, source_row, no_dvd, sheet_type, machine_type, line,"
                " error_code_c, created_at, occurred_at, raw_json")
    else:  # DB trước migration B0-FORM: không có cột process_stage
        conn.execute(
            "CREATE TABLE error_cases (id INTEGER PRIMARY KEY,"
            " machine_type TEXT, line TEXT, error_code_c TEXT, error_code_h TEXT,"
            " investigation TEXT, created_at TEXT,"
            " raw_json TEXT NOT NULL, occurred_at TEXT)")
        conn.execute(
            "CREATE TABLE import_batches (id INTEGER PRIMARY KEY)")
        cols = ("machine_type, line, error_code_c, error_code_h, investigation,"
                " created_at, occurred_at, raw_json")
    conn.execute(
        "INSERT INTO import_batches (id, source_file, file_sha256, sheet_name)"
        " VALUES (1, 'SIMULATED.xlsx', 'simulated-sha', 'Sheet1')"
        if with_process_stage else
        "INSERT INTO import_batches (id) VALUES (1)")
    conn.commit()
    return conn


def _insert_letter_rows(conn, with_process_stage):
    if with_process_stage:
        conn.execute(
            "INSERT INTO error_cases (batch_id, source_row, no_dvd, sheet_type,"
            " machine_type, line, error_code_c, created_at, occurred_at, raw_json,"
            " process_stage) VALUES"
            " (1, 2, 'SIM/001', 'Máy in', 'Virgo', 'C33', 'C0030',"
            "  '2026-09-01 10:00:00', '2026-09-01',"
            "  '{\"F\": \"調整A1\", \"R\": \"PWB MAIN ASSY WITH SOFTWARE\"}', NULL),"
            " (1, 3, 'SIM/002', 'Máy in', 'Iris2024', 'C35', 'C0120',"
            "  '2026-09-02 10:00:00', '2026-09-02',"
            "  '{\"F\": \"調整A2\", \"R\": \"ー\"}', NULL)")
    else:
        conn.execute(
            "INSERT INTO error_cases (machine_type, line, error_code_c,"
            " error_code_h, investigation, created_at, occurred_at, raw_json)"
            " VALUES"
            " ('Virgo', 'C33', 'C0030', 'ERROR', '', '2026-09-01 10:00:00',"
            "  '2026-09-01',"
            "  '{\"F\": \"調整A1\", \"R\": \"PWB MAIN ASSY WITH SOFTWARE\"}'),"
            " ('Iris2024', 'C35', 'C0120', 'ERROR', '', '2026-09-02 10:00:00',"
            "  '2026-09-02', '{\"F\": \"調整A2\", \"R\": \"ー\"}')")
    conn.commit()


def test_fetch_records_resolves_letter_columns_simulated():
    conn = _simulated_letter_db(with_process_stage=True)
    try:
        _insert_letter_rows(conn, True)
        records = fetch_records(conn)
        assert records[0]["stage"] == "調整A1"  # cột F (công đoạn)
        assert records[0]["machine"] == "PWB MAIN ASSY WITH SOFTWARE"  # cột R
        assert records[1]["stage"] == "調整A2"
        assert records[1]["machine"] == MISSING_GROUP  # "ー" -> thiếu
    finally:
        conn.close()


def test_fetch_records_tolerates_missing_process_stage_column():
    conn = _simulated_letter_db(with_process_stage=False)
    try:
        _insert_letter_rows(conn, False)
        records = fetch_records(conn)  # không nổ dù thiếu cột B0-FORM
        assert len(records) == 2
        assert records[0]["stage"] == "調整A1"
    finally:
        conn.close()


# --- biểu đồ xu hướng (tái dùng engine JIG) -------------------------------------

def test_render_trend_chart_png_simulated(tmp_path):
    table = incidence_table(make_tiny_trend_records(), "model", period="week")
    out = tn.render_trend_chart(table, "model", "A", tmp_path / "trend.png",
                                threshold=0.5)
    data = out.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) > 5000


def test_render_trend_chart_empty_table_raises():
    with pytest.raises(ValueError, match="Không có dữ liệu"):
        tn.render_trend_chart({}, "model", "A", "/tmp/khong-dung.png")


# --- báo cáo định kỳ + mail (stub, KHÔNG gửi thật) ------------------------------

def _parts_by_type(msg):
    found = {}
    for part in msg.walk():
        ctype = part.get_content_type()
        found.setdefault(ctype, []).append(part)
    return found


def test_scheduled_report_mail_stub_captures(tmp_path):
    sent = []
    result = tn.run_scheduled_report(
        make_spike_records(),
        dimensions=("model",),
        period="week",
        thresholds={"model": {"Virgo": 0.5}},
        recipients=["test@example.com"],
        send_fn=sent.append,
        report_dir=tmp_path,
        generated_at="2026-10-01 15:00",
    )
    assert result.send_status == tn.DA_GUI
    assert len(sent) == 1
    msg = sent[0]
    assert "Xu hướng lỗi" in msg["Subject"]
    assert msg["To"] == "test@example.com"
    parts = _parts_by_type(msg)
    assert "image/png" in parts  # biểu đồ đính kèm
    md_parts = [p for p in parts.get("text/plain", [])
                if p.get_filename() == "bao_cao_chi_tiet.md"]
    assert md_parts  # báo cáo markdown đính kèm
    assert any(a.group == "Virgo" for a in result.alerts)  # bắn đúng ngưỡng test
    assert result.report_path and Path(result.report_path).is_file()
    assert "Báo cáo xu hướng lỗi" in Path(result.report_path).read_text(
        encoding="utf-8")
    assert result.chart_paths and all(
        Path(p).is_file() for p in result.chart_paths)


def test_no_send_fn_never_touches_network(monkeypatch):
    import smtplib

    def no_smtp(*a, **k):
        raise AssertionError("không được mở kết nối SMTP")

    monkeypatch.setattr(smtplib, "SMTP", no_smtp)
    result = tn.run_scheduled_report(
        make_spike_records(),
        dimensions=("model",),
        period="week",
        thresholds={"model": {"Virgo": 0.5}},
        recipients=["test@example.com"],
        report_dir="/tmp",
        generated_at="2026-10-01 15:00",
    )
    assert result.send_status == tn.CHUA_GUI  # thư soạn xong, không gửi
    assert result.mail is not None
    assert "chưa cấu hình hàm gửi" in result.send_note


def test_cooldown_suppresses_second_send(tmp_path):
    from aios_habit.production_prediction.alert_mailer import AlertCooldownTracker

    sent = []
    tracker = AlertCooldownTracker(cooldown_seconds=3600)
    kwargs = dict(
        dimensions=("model",), period="week",
        thresholds={"model": {"Virgo": 0.5}},
        recipients=["test@example.com"], send_fn=sent.append,
        report_dir=tmp_path, generated_at="2026-10-01 15:00",
        cooldown=tracker,
    )
    first = tn.run_scheduled_report(make_spike_records(), **kwargs)
    second = tn.run_scheduled_report(make_spike_records(), **kwargs)
    assert first.send_status == tn.DA_GUI
    assert second.send_status == tn.KHONG_GUI
    assert len(sent) == 1  # chỉ gửi 1 lần


def test_no_recipients_skips_mail_but_writes_report(tmp_path):
    result = tn.run_scheduled_report(
        make_spike_records(),
        dimensions=("model",),
        period="week",
        thresholds={"model": {"Virgo": 0.5}},
        recipients=(),
        report_dir=tmp_path,
        generated_at="2026-10-01 15:00",
    )
    assert result.send_status == tn.KHONG_GUI
    assert result.mail is None
    assert Path(result.report_path).is_file()  # file báo cáo vẫn sinh


def test_empty_data_report_vietnamese(tmp_path):
    result = tn.run_scheduled_report(
        [],
        dimensions=("model",),
        period="week",
        recipients=(),
        report_dir=tmp_path,
        generated_at="2026-10-01 15:00",
    )
    assert result.alerts == []
    assert result.chart_paths == []
    text = Path(result.report_path).read_text(encoding="utf-8")
    assert "không có dữ liệu" in text
