# -*- coding: utf-8 -*-
"""Bo kiem thu toan dien cho Log Chart Builder (Ticket DESKTOP-LOG-CHART-BUILDER-HOME).

Kiem tra:
1. Nhan dien file & dau phan cach (sniff_delimiter)
2. Nhan dien dong tieu de va xu ly file xau / file khong tieu de (detect_header_row)
3. Phan loai kieu cot: datetime, categorical, numeric, result
4. Doc file thuc te: CSV LSU 572 cot, Excel xlsx, Log text pipe-delimited
5. Xep hang goi y thong minh (recommender)
6. Ve 10 kieu bieu do san xuat & 3 ket hop bat buoc (Pareto, Trend+SMA, SPC)
7. Sinh anh thu nho tu du lieu that (thumbnails)
8. Sua doi dac ta bang chat (update_spec_from_text)
9. Vong lap phan hoi & metric (feedback loop)
10. Tinh cach ly toc do: khong lam cham cac cau hoi thong thuong
"""

from __future__ import annotations

import io
import os
import tempfile
import time
from pathlib import Path

import openpyxl
import pytest

from aios_habit.chat_intent_router import classify_intent, HOI_TAI_LIEU, VE_BIEU_DO, XEM_PHAN_HOI
from aios_habit.log_chart.feedback import (
    RATING_CHUA_HUU_ICH,
    RATING_HUU_ICH,
    get_chart_feedback_summary_markdown,
    get_chart_metrics,
    record_chart_feedback,
    record_chart_render_event,
)
from aios_habit.log_chart.parser import (
    ColumnMeta,
    LogParseError,
    ParsedLogTable,
    ROLE_CATEGORICAL,
    ROLE_DATETIME,
    ROLE_NUMERIC,
    ROLE_RESULT,
    classify_column_role,
    detect_header_row,
    parse_log_file,
    sniff_delimiter,
)
from aios_habit.log_chart.recommender import build_initial_spec, recommend_chart_types
from aios_habit.log_chart.renderer import (
    render_chart_image,
    render_thumbnail_image,
)
from aios_habit.log_chart.spec import (
    ALL_CHART_TYPES,
    CHART_BOX_PLOT,
    CHART_DONUT,
    CHART_GROUPED_BAR,
    CHART_HEATMAP,
    CHART_HISTOGRAM,
    CHART_PARETO,
    CHART_SCATTER,
    CHART_SPC,
    CHART_STACKED_BAR,
    CHART_TREND,
    ChartSpec,
    update_spec_from_text,
)


# Fixture thuc te trong repo
LSU_CSV_FIXTURE = Path(r"D:\Sandbox\AIOS_habbit\tests\fixtures\lsu_iris\iris_log\unit_test\SYN_UnitTest_572cot.csv")
A17_LOG_FIXTURE = Path(r"D:\Sandbox\AIOS_habbit\tests\fixtures\agent_harness\factory_error\nhat_ky_lo_A17.log")


# =========================================================================
# 1. TEST DAU PHAN CACH & TIÊU ĐỀ
# =========================================================================

def test_sniff_delimiter_variants():
    """Kiem tra tu nhan dien cac dau phan cach: comma, tab, semicolon, pipe."""
    csv_lines = ["ID,NAME,VAL", "1,A,10.5", "2,B,20.1"]
    assert sniff_delimiter(csv_lines) == ","

    tsv_lines = ["ID\tNAME\tVAL", "1\tA\t10.5", "2\tB\t20.1"]
    assert sniff_delimiter(tsv_lines) == "\t"

    semi_lines = ["ID;NAME;VAL", "1;A;10.5", "2;B;20.1"]
    assert sniff_delimiter(semi_lines) == ";"

    pipe_lines = ["ID | NAME | VAL", "1 | A | 10.5", "2 | B | 20.1"]
    assert sniff_delimiter(pipe_lines) == "|"


def test_detect_header_row_with_metadata_prefix():
    """File xau co 3 dong chu thich/config truoc dong tieu de."""
    dirty_lines = [
        "# Log thiet bi JIG-04",
        "# Ngay tao: 2026-10-20",
        "---",
        "DATE,TIME,SERIAL,RESULT,SKEW[um]",
        "2026-10-20,08:00:00,SN001,OK,12.5",
        "2026-10-20,08:05:00,SN002,NG,-15.2",
    ]
    idx, cols = detect_header_row(dirty_lines, ",")
    assert idx == 3
    assert cols == ["DATE", "TIME", "SERIAL", "RESULT", "SKEW[um]"]


# =========================================================================
# 2. TEST PHAN LOAI KIEU COT (COLUMN CLASSIFICATION)
# =========================================================================

def test_classify_column_roles():
    """Kiem tra phan loai 4 kieu cot: datetime, result, numeric, categorical."""
    # Datetime
    assert classify_column_role("Timestamp", ["2026-10-20 08:00:00", "2026-10-20 08:05:00"]) == ROLE_DATETIME
    assert classify_column_role("Gio_do", ["08:15:30", "08:20:00"]) == ROLE_DATETIME

    # Result OK/NG
    assert classify_column_role("RESULT", ["OK", "NG", "OK", "OK"]) == ROLE_RESULT
    assert classify_column_role("Status", ["PASS", "FAIL", "PASS"]) == ROLE_RESULT

    # Numeric
    assert classify_column_role("SKEW[um]", ["12.5", "-4.2", "0.0", "15.8"]) == ROLE_NUMERIC
    assert classify_column_role("Power_mW", [150.2, 149.8, 151.0]) == ROLE_NUMERIC

    # Categorical
    assert classify_column_role("Line", ["Line 1", "Line 2", "Line 1"]) == ROLE_CATEGORICAL
    assert classify_column_role("Defect_Code", ["E101", "E102", "E101"]) == ROLE_CATEGORICAL


# =========================================================================
# 3. TEST DOC FILE THUC TE (PARSER)
# =========================================================================

def test_parse_real_csv_master_lsu():
    """Doc file CSV Master LSU that 572 cot."""
    assert LSU_CSV_FIXTURE.exists()
    table = parse_log_file(LSU_CSV_FIXTURE)
    assert table.total_rows == 3
    assert len(table.columns) == 572
    dt_cols = table.get_columns_by_role(ROLE_DATETIME)
    res_cols = table.get_columns_by_role(ROLE_RESULT)
    num_cols = table.get_columns_by_role(ROLE_NUMERIC)

    assert "DATE" in [c.name for c in dt_cols]
    assert "RESULT" in [c.name for c in res_cols]
    assert any("SKEW" in c.name for c in num_cols)


def test_parse_real_text_log_pipe_delimited():
    """Doc file log text phan cach bang dau pipe (|)."""
    assert A17_LOG_FIXTURE.exists()
    table = parse_log_file(A17_LOG_FIXTURE)
    assert table.total_rows >= 5
    assert len(table.columns) >= 3
    assert table.delimiter == "|"


def test_parse_excel_file(tmp_path: Path):
    """Doc file Excel hop le tao bang openpyxl."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LogDieuChinh"
    # Metadata dong 1
    ws.append(["# Nhat ky hieu chinh cong doan LSU", None, None, None])
    # Tieu de dong 2
    ws.append(["Thoi_gian", "Line", "Ma_loi", "Do_lech_um"])
    # Du lieu
    ws.append(["2026-10-20 08:00:00", "Line 1", "E101", 12.4])
    ws.append(["2026-10-20 08:15:00", "Line 2", "E102", -8.5])
    ws.append(["2026-10-20 08:30:00", "Line 1", "E101", 15.1])

    xlsx_path = tmp_path / "test_dieu_chinh.xlsx"
    wb.save(xlsx_path)

    table = parse_log_file(xlsx_path)
    assert table.total_rows == 3
    assert "Do_lech_um" in table.get_column_names()
    assert table.get_column_meta("Do_lech_um").role == ROLE_NUMERIC


def test_parse_empty_and_corrupt_files(tmp_path: Path):
    """Kiem tra ben vung: file rong hoac hong phai bao loi ro rang, khong sap app."""
    empty_f = tmp_path / "empty.csv"
    empty_f.write_text("", encoding="utf-8")
    with pytest.raises(LogParseError) as exc_info:
        parse_log_file(empty_f)
    assert "rong" in str(exc_info.value).lower()

    corrupt_f = tmp_path / "corrupt.xlsx"
    corrupt_f.write_bytes(b"not an excel file header")
    with pytest.raises(LogParseError) as exc_info2:
        parse_log_file(corrupt_f)
    assert "khong the mo" in str(exc_info2.value).lower()


# =========================================================================
# 4. TEST XEP HANG GOI Y THONG MINH (RECOMMENDER)
# =========================================================================

def test_recommend_ranking_logic():
    """Kiem tra quy tac xep hang thong minh theo kieu cot."""
    # Truong hop 1: Co cot ket qua / ma loi -> Pareto len dau
    cols_err = [
        ColumnMeta(name="Defect_Code", role=ROLE_CATEGORICAL, sample_values=["E101", "E102"]),
        ColumnMeta(name="Result", role=ROLE_RESULT, sample_values=["OK", "NG"]),
    ]
    t_err = ParsedLogTable("err.csv", 10, cols_err, [{"Defect_Code": "E101", "Result": "NG"}])
    rec_err = recommend_chart_types(t_err)
    assert rec_err[0][0] == CHART_PARETO

    # Truong hop 2: Co cot thoi gian -> Trend / SPC len dau
    cols_time = [
        ColumnMeta(name="Timestamp", role=ROLE_DATETIME, sample_values=["2026-10-20 08:00:00"]),
        ColumnMeta(name="Voltage", role=ROLE_NUMERIC, sample_values=["5.1"]),
    ]
    t_time = ParsedLogTable("time.csv", 10, cols_time, [{"Timestamp": "2026-10-20 08:00:00", "Voltage": 5.1}])
    rec_time = recommend_chart_types(t_time)
    top_two = [rec_time[0][0], rec_time[1][0]]
    assert CHART_TREND in top_two or CHART_SPC in top_two

    # Truong hop 3: Hai cot so do -> Scatter plot & Box plot
    cols_scatter = [
        ColumnMeta(name="Laser_Power", role=ROLE_NUMERIC, sample_values=["120.0"]),
        ColumnMeta(name="Beam_Width", role=ROLE_NUMERIC, sample_values=["65.2"]),
    ]
    t_sc = ParsedLogTable("scatter.csv", 10, cols_scatter, [{"Laser_Power": 120.0, "Beam_Width": 65.2}])
    rec_sc = recommend_chart_types(t_sc)
    top_three = [r[0] for r in rec_sc[:3]]
    assert CHART_SCATTER in top_three or CHART_BOX_PLOT in top_three


# =========================================================================
# 5. TEST VE 10 KIEU BIEU DO & 3 KET HOP BAT BUOC (RENDERER)
# =========================================================================

def test_render_all_10_charts_and_thumbnails():
    """Kiem tra ve du 10 kieu bieu do va anh thu nho tu du lieu thuc."""
    table = parse_log_file(LSU_CSV_FIXTURE)
    assert len(ALL_CHART_TYPES) == 10

    for ctype in ALL_CHART_TYPES:
        spec = ChartSpec(file_name=table.file_name, chart_type=ctype)
        # Ve full PNG
        png_data = render_chart_image(spec, table)
        assert isinstance(png_data, bytes)
        assert len(png_data) > 1000
        assert png_data.startswith(b"\x89PNG")

        # Ve thumbnail
        thumb_data = render_thumbnail_image(ctype, spec, table)
        assert isinstance(thumb_data, bytes)
        assert len(thumb_data) > 500
        assert thumb_data.startswith(b"\x89PNG")


def test_three_mandatory_combinations():
    """Ba ket hop bat buoc phai chay duoc:

    1. Cot + duong (Pareto)
    2. Duong + SMA(20) (Trend)
    3. Duong + hai duong gioi han UCL/LCL (SPC)
    """
    table = parse_log_file(LSU_CSV_FIXTURE)

    # 1. Pareto
    p_spec = ChartSpec(file_name=table.file_name, chart_type=CHART_PARETO)
    p_png = render_chart_image(p_spec, table)
    assert len(p_png) > 1000

    # 2. Trend + SMA(20)
    t_spec = ChartSpec(file_name=table.file_name, chart_type=CHART_TREND, options={"show_sma": True, "sma_window": 2})
    t_png = render_chart_image(t_spec, table)
    assert len(t_png) > 1000

    # 3. SPC + UCL/LCL
    s_spec = ChartSpec(file_name=table.file_name, chart_type=CHART_SPC)
    s_png = render_chart_image(s_spec, table)
    assert len(s_png) > 1000


# =========================================================================
# 6. TEST CONVERSATIONAL REFINEMENT (UPDATE SPEC FROM TEXT)
# =========================================================================

def test_conversational_refinement():
    """Hoi tiep bang loi de sua dac ta bieu do."""
    table = parse_log_file(LSU_CSV_FIXTURE)
    spec = build_initial_spec(table)

    # Them duong SMA(15)
    spec2, msg2 = update_spec_from_text(spec, "thêm đường SMA(15)", table)
    assert spec2.options["show_sma"] is True
    assert spec2.options["sma_window"] == 15
    assert "SMA(15)" in msg2

    # Tat SMA
    spec3, msg3 = update_spec_from_text(spec2, "tắt SMA đi", table)
    assert spec3.options["show_sma"] is False

    # Chuyen sang Pareto
    spec4, msg4 = update_spec_from_text(spec3, "chuyển sang biểu đồ Pareto", table)
    assert spec4.chart_type == CHART_PARETO

    # Loc chi dong NG
    spec5, msg5 = update_spec_from_text(spec4, "chỉ dòng NG", table)
    assert spec5.filter_op == "only_ng"
    assert spec5.filter_val == "NG"

    # Bo loc
    spec6, msg6 = update_spec_from_text(spec5, "xem tất cả dòng", table)
    assert spec6.filter_col is None
    assert spec6.filter_op == "all"


# =========================================================================
# 7. TEST VONG LAP PHAN HOI & METRICS (FEEDBACK LOOP)
# =========================================================================

def test_feedback_loop_and_metrics():
    """Kiem tra luu phan hoi huu ich / chua huu ich kem ly do va doc metric."""
    # 1. Ghi nhan render event
    record_chart_render_event(CHART_PARETO, success=True, duration_ms=45.2, file_name="test.csv")
    record_chart_render_event(CHART_TREND, success=True, duration_ms=38.1, file_name="test.csv")

    # 2. Ghi nhan feedback tot
    r1 = record_chart_feedback("CONV-01", "SPEC-01", CHART_PARETO, RATING_HUU_ICH, file_name="test.csv")
    assert r1["ok"] is True

    # 3. Ghi nhan feedback che khong co ly do -> bat buoc loi
    r_bad_no_reason = record_chart_feedback("CONV-01", "SPEC-01", CHART_PARETO, RATING_CHUA_HUU_ICH, reason="")
    assert r_bad_no_reason["ok"] is False
    assert "bắt buộc" in r_bad_no_reason["error_vi"]

    # 4. Ghi nhan feedback che co ly do -> thanh cong
    r2 = record_chart_feedback(
        "CONV-01", "SPEC-01", CHART_PARETO, RATING_CHUA_HUU_ICH,
        reason="Sai kiểu biểu đồ không phù hợp mục đích", file_name="test.csv"
    )
    assert r2["ok"] is True

    # 5. Kiem tra metric
    metrics = get_chart_metrics()
    assert metrics["total_renders"] >= 2
    assert metrics["render_success_rate_pct"] > 0
    assert metrics["feedback_counts"][RATING_HUU_ICH] >= 1
    assert metrics["feedback_counts"][RATING_CHUA_HUU_ICH] >= 1

    # 6. Kiem tra review surface markdown
    summary_md = get_chart_feedback_summary_markdown()
    assert "Bề mặt xem lại" in summary_md
    assert "Pareto" in summary_md or "pareto" in summary_md


# =========================================================================
# 8. TEST CACH LY TOC DO (SPEED ISOLATION)
# =========================================================================

def test_speed_isolation_on_regular_queries():
    """Chung minh cac cau hoi thong thuong khong bi anh huong hay lam cham (Requirement 2f)."""
    regular_queries = [
        "Quy trình điều tra 4M trong nhà máy gồm những bước nào?",
        "Máy C7620 bị lệch tâm thì xử lý ra sao?",
        "Xin chào trợ lý AIOS",
        "Có bao nhiêu biên bản lỗi trong kho?",
    ]

    # Khoi dong am ham phan loai y dinh
    _ = classify_intent("warmup query khoi dong")

    t0 = time.perf_counter()
    for q in regular_queries:
        intent = classify_intent(q)
        # Cac cau hoi nay tuyet doi KHONG bi phan nham vao VE_BIEU_DO
        assert intent != VE_BIEU_DO
    elapsed = time.perf_counter() - t0

    # Phai duoi 50ms cho ca 4 cau o steady-state (thuc te < 1ms)
    assert elapsed < 0.05, f"Phan loai y dinh qua cham: {elapsed*1000:.2f}ms"
