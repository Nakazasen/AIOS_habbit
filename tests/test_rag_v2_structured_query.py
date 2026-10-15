from pathlib import Path

import openpyxl
import pytest

from aios_habit.rag_v2.structured_query import (
    StructuredAggregate,
    StructuredFilter,
    StructuredOrder,
    StructuredQueryBoundsError,
    StructuredQueryPlan,
    StructuredQueryValidationError,
    execute_excel_query,
)


def _workbook(path: Path, rows, *, sheet: str = "Sales") -> Path:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
    workbook.close()
    return path


def test_structured_query_normalizes_blank_and_duplicate_headers(tmp_path):
    path = _workbook(tmp_path / "headers.xlsx", [["Name", "", "Name"], ["A", 10, "North"]])
    result = execute_excel_query(path, StructuredQueryPlan(sheet="Sales", select_columns=("Name", "column_2", "Name_2")))
    assert result.columns == ("Name", "column_2", "Name_2")
    assert result.rows == (("A", 10, "North"),)
    assert result.source_name == "headers.xlsx"
    assert result.provenance[0].sheet == "Sales"
    assert result.provenance[0].cell_range == "A2:C2"


def test_structured_query_infers_numbers_and_applies_parameterized_filters(tmp_path):
    path = _workbook(tmp_path / "sales.xlsx", [["Region", "Revenue"], ["North", "10.5"], ["South", "7"], ["North", "bad"]])
    result = execute_excel_query(path, StructuredQueryPlan(select_columns=("Region", "Revenue"), filters=(StructuredFilter("Revenue", ">=", 8),), order_by=(StructuredOrder("Revenue", "desc"),)))
    assert result.rows == (("North", 10.5),)
    assert result.provenance[0].excel_rows == (2,)
    assert "North" in result.rendered_evidence
    assert "Sales!A1:B4" in result.rendered_evidence


def test_structured_query_groups_and_aggregates(tmp_path):
    path = _workbook(tmp_path / "aggregate.xlsx", [["Region", "Revenue"], ["North", 10], ["South", 7], ["North", 5]])
    result = execute_excel_query(path, StructuredQueryPlan(group_by=("Region",), aggregates=(StructuredAggregate("sum", "Revenue", "total_revenue"), StructuredAggregate("count", "*", "row_count")), order_by=(StructuredOrder("total_revenue", "desc"),)))
    assert result.columns == ("Region", "total_revenue", "row_count")
    assert result.rows == (("North", 15.0, 2), ("South", 7.0, 1))
    assert result.provenance[0].excel_rows == (2, 4)
    assert result.provenance[1].excel_rows == (3,)


def test_structured_query_rejects_identifier_and_operator_injection(tmp_path):
    path = _workbook(tmp_path / "safe.xlsx", [["Value"], [1]])
    with pytest.raises(StructuredQueryValidationError, match="Unknown column"):
        execute_excel_query(path, StructuredQueryPlan(select_columns=('Value"; DROP TABLE data; --',)))
    with pytest.raises(StructuredQueryValidationError, match="Unsupported filter operator"):
        execute_excel_query(path, StructuredQueryPlan(filters=(StructuredFilter("Value", "= 1; DROP TABLE data", 1),)))
    result = execute_excel_query(path, StructuredQueryPlan(filters=(StructuredFilter("Value", "=", "1' OR 1=1 --"),)))
    assert result.rows == ()


def test_structured_query_enforces_cell_and_result_bounds(tmp_path, monkeypatch):
    path = _workbook(tmp_path / "bounded.xlsx", [["A", "B"], [1, 2], [3, 4]])
    monkeypatch.setenv("AIOS_STRUCTURED_SQL_MAX_CELLS", "5")
    with pytest.raises(StructuredQueryBoundsError, match="cell limit"):
        execute_excel_query(path, StructuredQueryPlan())
    monkeypatch.setenv("AIOS_STRUCTURED_SQL_MAX_CELLS", "100")
    result = execute_excel_query(path, StructuredQueryPlan(limit=9999))
    assert result.row_count == 2
    assert result.truncated is False


def test_excel_engine_fails_soft_for_unsupported_path(tmp_path: Path):
    unsupported = execute_excel_query(
        tmp_path / "missing.csv",
        StructuredQueryPlan(select_columns=("x",)),
    )
    assert unsupported.applied is False
    assert unsupported.reason == "unsupported_or_missing_workbook"


def test_deterministic_planner_builds_grouped_average_plan():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    planned = plan_excel_query(
        "Tính trung bình Revenue theo Region, lấy top 3",
        (ExcelTableSchema("Sales", ("Region", "Revenue")),),
    )

    assert planned.applied is True
    assert planned.plan is not None
    assert planned.plan.sheet == "Sales"
    assert planned.plan.group_by == ("Region",)
    assert planned.plan.select_columns == ("Region",)
    assert planned.plan.aggregates[0].function == "avg"
    assert planned.plan.aggregates[0].column == "Revenue"
    assert planned.plan.order_by[0].direction == "desc"
    assert planned.plan.limit == 3


def test_deterministic_planner_rejects_raw_sql_and_falls_back_for_prose():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    schemas = (ExcelTableSchema("Sales", ("Region", "Revenue")),)
    raw_sql = plan_excel_query("SELECT * FROM Sales", schemas)
    prose = plan_excel_query("Hãy giải thích báo cáo này", schemas)

    assert raw_sql.applied is False
    assert raw_sql.reason == "raw_sql_rejected"
    assert prose.applied is False
    assert prose.reason == "unstructured_intent"


def test_structured_query_rejects_grouped_non_grouped_projection(tmp_path):
    path = _workbook(tmp_path / "grouped.xlsx", [["Region", "Revenue"], ["N", 1]])
    with pytest.raises(StructuredQueryValidationError, match="Grouped query selections"):
        execute_excel_query(path, StructuredQueryPlan(select_columns=("Revenue",), group_by=("Region",), aggregates=(StructuredAggregate("sum", "Revenue", "total"),)))


def test_planner_understands_vietnamese_synonyms_and_diacritics():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    planned = plan_excel_query(
        "Tính tổng doanh thu theo khu vực",
        (ExcelTableSchema("Báo Cáo", ("Region", "Revenue")),),
    )
    assert planned.applied is True
    assert planned.plan is not None
    assert planned.plan.sheet == "Báo Cáo"
    assert planned.plan.group_by == ("Region",)
    assert planned.plan.aggregates[0].function == "sum"
    assert planned.plan.aggregates[0].column == "Revenue"


def test_planner_parses_date_range_and_multi_conditions():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    planned = plan_excel_query(
        "Tổng doanh thu theo khu vực trong tháng 8/2026 và Region là North",
        (ExcelTableSchema("Sales", ("Region", "Revenue", "Date")),),
    )
    assert planned.applied is True
    assert planned.plan is not None
    assert len(planned.plan.filters) >= 3
    operators = [f.operator for f in planned.plan.filters]
    assert ">=" in operators
    assert "<=" in operators
    assert "=" in operators


def test_planner_rejects_or_filter_logic():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    planned = plan_excel_query(
        "Liệt kê doanh thu cho Region là North hoặc Region là South",
        (ExcelTableSchema("Sales", ("Region", "Revenue")),),
    )
    assert planned.applied is False
    assert "filter_validation_error" in planned.reason


def test_planner_selects_correct_sheet_and_fails_soft_on_ambiguity():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    schemas = (
        ExcelTableSchema("East", ("Region", "Revenue")),
        ExcelTableSchema("West", ("Branch", "Amount")),
    )
    planned = plan_excel_query("Tổng Revenue ở sheet East", schemas)
    assert planned.applied is True
    assert planned.plan.sheet == "East"

    ambiguous_schemas = (
        ExcelTableSchema("East", ("Region", "Revenue")),
        ExcelTableSchema("West", ("Region", "Sales")),
    )
    ambiguous = plan_excel_query("Tính tổng Revenue", ambiguous_schemas)
    assert ambiguous.applied is False
    assert ambiguous.reason == "ambiguous_sheet_table"


def test_structured_query_multi_region_execution(tmp_path):
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "East"
    ws1.append(["Region", "Revenue"])
    ws1.append(["North", 100])

    ws2 = wb.create_sheet(title="West")
    ws2.append(["Region", "Revenue"])
    ws2.append(["South", 200])

    path = tmp_path / "multi_region.xlsx"
    wb.save(path)
    wb.close()

    result = execute_excel_query(
        path,
        StructuredQueryPlan(
            target_regions=("East!A1:B2", "West!A1:B2"),
            aggregates=(StructuredAggregate("sum", "Revenue", "total_rev"),),
        ),
    )
    assert result.applied is True
    assert result.rows[0][0] == 300.0
    assert len(result.provenance) >= 1

    detail_result = execute_excel_query(
        path,
        StructuredQueryPlan(
            target_regions=("East!A1:B2", "West!A1:B2"),
            select_columns=("Region", "Revenue"),
        ),
    )
    assert detail_result.applied is True
    assert detail_result.rows == (("North", 100), ("South", 200))
    assert detail_result.provenance[0].sheet == "East"
    assert detail_result.provenance[1].sheet == "West"


def test_month_slash_year_extraction_preserves_year():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    planned = plan_excel_query(
        "Tổng doanh thu trong tháng 8/2025",
        (ExcelTableSchema("Sales", ("Revenue", "Date")),),
    )
    assert planned.applied is True
    assert planned.plan is not None
    filters = planned.plan.filters
    assert any(f.value == "2025-08-01" for f in filters)
    assert any(f.value == "2025-08-31" for f in filters)


def test_parse_iso_date_rejects_invalid_calendar_date():
    from aios_habit.rag_v2.structured_query import _parse_iso_date

    assert _parse_iso_date("2026-02-31") is None
    assert _parse_iso_date("2026-02-28") == "2026-02-28"


def test_identical_schema_ambiguity_rejected():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    ambiguous_schemas = (
        ExcelTableSchema("East", ("Region", "Revenue"), "A1:B2"),
        ExcelTableSchema("West", ("Region", "Revenue"), "A1:B2"),
    )
    ambiguous = plan_excel_query("Tính tổng Revenue", ambiguous_schemas)
    assert ambiguous.applied is False
    assert ambiguous.reason == "ambiguous_sheet_table"

    all_planned = plan_excel_query("Tính tổng Revenue trên tất cả các sheet", ambiguous_schemas)
    assert all_planned.applied is True
    assert all_planned.plan.target_regions == ("East!A1:B2", "West!A1:B2")

    no_range_schemas = (
        ExcelTableSchema("East", ("Region", "Revenue")),
        ExcelTableSchema("West", ("Region", "Revenue")),
    )
    no_range_all = plan_excel_query("Tổng Revenue trên tất cả các sheet", no_range_schemas)
    assert no_range_all.applied is True
    assert no_range_all.plan.target_regions == ("East", "West")


def test_quantity_listing_intent_selects_column_instead_of_count_aggregate():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    planned = plan_excel_query(
        "Liệt kê số lượng theo sản phẩm",
        (ExcelTableSchema("Inventory", ("Product", "Quantity")),),
    )
    assert planned.applied is True
    assert planned.plan is not None
    assert planned.plan.group_by == ("Product",)
    assert planned.plan.select_columns == ("Quantity", "Product") or "Quantity" in planned.plan.select_columns
    assert len(planned.plan.aggregates) == 0


def test_multi_sheet_aggregate_provenance_and_rendered_evidence(tmp_path):
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "East"
    ws1.append(["Region", "Revenue"])
    ws1.append(["North", 100])

    ws2 = wb.create_sheet(title="West")
    ws2.append(["Region", "Revenue"])
    ws2.append(["North", 200])

    path = tmp_path / "grouped_multi.xlsx"
    wb.save(path)
    wb.close()

    result = execute_excel_query(
        path,
        StructuredQueryPlan(
            target_regions=("East", "West"),
            group_by=("Region",),
            aggregates=(StructuredAggregate("sum", "Revenue", "total_rev"),),
        ),
    )
    assert result.applied is True
    assert result.rows == (("North", 300.0),)
    provenance_sheets = tuple(p.sheet for p in result.provenance)
    assert "East" in provenance_sheets
    assert "West" in provenance_sheets
    assert "multi-region (East, West)" in result.rendered_evidence
def test_planner_does_not_treat_all_substring_as_all_sheets_intent():
    from aios_habit.rag_v2.structured_query import ExcelTableSchema, plan_excel_query

    schemas = (
        ExcelTableSchema("East", ("Revenue",)),
        ExcelTableSchema("West", ("Revenue",)),
    )
    planned = plan_excel_query("smallest Revenue", schemas)

    assert planned.applied is False
    assert planned.reason == "ambiguous_sheet_table"


def test_aggregate_provenance_preserves_comma_in_excel_sheet_name(tmp_path):
    wb = openpyxl.Workbook()
    comma_sheet = wb.active
    comma_sheet.title = "East,West"
    comma_sheet.append(["Revenue"])
    comma_sheet.append([100])
    north_sheet = wb.create_sheet(title="North")
    north_sheet.append(["Revenue"])
    north_sheet.append([200])

    path = tmp_path / "comma_sheet.xlsx"
    wb.save(path)
    wb.close()
    result = execute_excel_query(
        path,
        StructuredQueryPlan(
            target_regions=("East,West", "North"),
            aggregates=(StructuredAggregate("sum", "Revenue", "total_revenue"),),
        ),
    )

    assert result.applied is True
    assert result.rows == ((300.0,),)
    assert tuple(provenance.sheet for provenance in result.provenance) == ("East,West", "North")


def _create_synthetic_structured_fixtures(tmp_path: Path) -> dict[str, Path]:
    """Create small, fully isolated synthetic data fixtures for all structured lane behaviors."""
    import csv

    # 1. BowOverAdjust CSV (20 records, dates 2026/08/01 to 2026/08/25, Yellow 10, Cyan 6, Magenta 4, Black 0)
    p_bow = tmp_path / "synthetic_bowoveradjust.csv"
    headers_bow = ["DATE", "TIME", "S/N", "Mode", "Abstract", "ErrColor"]
    rows_bow = []
    for i in range(10):
        rows_bow.append(["2026/08/01", f"10:{i:02d}:00", f"61CYEL00{i:02d}", "Adjust", "BowOverAdjustment", "Yellow"])
    for i in range(6):
        rows_bow.append(["2026/08/15", f"11:{i:02d}:00", f"61CCYN00{i:02d}", "Adjust", "BowOverAdjustment", "Cyan"])
    for i in range(4):
        rows_bow.append(["2026/08/25", f"12:{i:02d}:00", f"61CMAG00{i:02d}", "Adjust", "BowOverAdjustment", "Magenta"])
    with open(p_bow, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers_bow)
        w.writerows(rows_bow)

    # 2. Error CSV (8 records, dates 2026/08/11 [5 errors peak] and 2026/08/12 [3 errors], JigNumber #1, 4 unique serials)
    p_err = tmp_path / "synthetic_error.csv"
    headers_err = ["DATE", "TIME", "JigNumber", "S/N", "Mode"]
    rows_err = [
        ["2026/08/11", "08:00:00", "#1", "C9P001", "Error"],
        ["2026/08/11", "08:10:00", "#1", "C9P002", "Error"],
        ["2026/08/11", "08:20:00", "#1", "C9P003", "Error"],
        ["2026/08/11", "08:30:00", "#1", "C9P004", "Error"],
        ["2026/08/11", "08:40:00", "#1", "C9P001", "Error"],
        ["2026/08/12", "09:00:00", "#1", "C9P002", "Error"],
        ["2026/08/12", "09:10:00", "#1", "C9P003", "Error"],
        ["2026/08/12", "09:20:00", "#1", "C9P004", "Error"],
    ]
    with open(p_err, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers_err)
        w.writerows(rows_err)

    # 3. Spec CSV (6 records: 4 records Lower 370 / Upper 520, 2 records Lower 350 / Upper 500)
    p_spec = tmp_path / "synthetic_spec.csv"
    headers_spec = ["Item", "Lower", "Upper", "Unit"]
    rows_spec = [
        ["Current", "370", "520", "mA"],
        ["Current", "370", "520", "mA"],
        ["Current", "370", "520", "mA"],
        ["Current", "370", "520", "mA"],
        ["Current", "350", "500", "mA"],
        ["Current", "350", "500", "mA"],
    ]
    with open(p_spec, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers_spec)
        w.writerows(rows_spec)

    # 4. UnitTest CSV (Serial 61C1068E7022 across 2026/08/12 and 2026/08/13, TotalJudge NG, Black OK, Cyan NG)
    p_unit = tmp_path / "synthetic_unittest.csv"
    headers_unit = ["DATE", "TIME", "S/N", "Mode", "TotalJudge", "Judge:Black", "Judge:Cyan", "Judge:Magenta", "Judge:Yellow"]
    rows_unit = [
        ["2026/08/12", "10:00:00", "61C1068E7022", "UnitTest", "NG", "OK", "NG", "OK", "OK"],
        ["2026/08/13", "11:00:00", "61C1068E7022", "UnitTest", "NG", "OK", "NG", "OK", "OK"],
    ]
    with open(p_unit, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers_unit)
        w.writerows(rows_unit)

    # 5. Inspection sheet (Mount LD block with g1 and g2: nominal 13.81, +0.12 -0.05, 13.93/13.76, judge O)
    p_insp = tmp_path / "synthetic_inspection.xlsx"
    insp_rows = [
        ["●3V2ND19040-MOUNT LD BLOCK"],
        ["NO", "Vị trí bản vẽ", "Kích thước đo", "Column D", "Dung sai", "Column F", "Column G", "Điểm đo", "Dung sai trên", "Dung sai dưới", "Shot 1", "Shot 2", "Shot 3", "Shot 4", "Shot 5", "Shot 6", "Phán định kết quả"],
        ["50", "1D", "", 13.81, "+0.12 -0.05", 0.12, 0.05, "g1", "=E60+G60", "=E60-H60", 13.8492, 13.8457, 13.8455, 13.8508, 13.8465, 13.8458, "O"],
        ["", "1D", "", 13.81, "+0.12 -0.05", 0.12, 0.05, "g2", "=E61+G61", "=E61-H61", 13.8562, 13.8502, 13.8474, 13.8554, 13.8489, 13.8483, "O"],
    ]
    _workbook(p_insp, insp_rows, sheet="18.08.2026")

    return {
        "bowoveradjust": p_bow,
        "error": p_err,
        "spec": p_spec,
        "unittest": p_unit,
        "inspection": p_insp,
    }


def test_structured_table_lane_targets(tmp_path):
    """Verify structured table lane intent routing and calculations against synthetic fixtures."""
    from aios_habit.rag_v2.structured_query import (
        query_might_be_structured_table,
        try_structured_table_evidence,
    )

    fixtures = _create_synthetic_structured_fixtures(tmp_path)

    q_targets = [
        ("2026年8月のBowOverAdjustエラー件数と期間を教えてください。", fixtures["bowoveradjust"], "20 record", "2026_08_Error_BowOverAdjust.csv"),
        ("BowOverAdjustエラーの各色（Yellow, Cyan, Magenta）の件数は？", fixtures["bowoveradjust"], "10件", "2026_08_Error_BowOverAdjust.csv"),
        ("BowOverAdjustエラーにBlackはありますか？", fixtures["bowoveradjust"], "0件", "2026_08_Error_BowOverAdjust.csv"),
        ("2026年8月でエラーが最も多い日はいつですか？件数も教えてください。", fixtures["error"], "5笔", "2026_08_Error.csv"),
        ("2026_08_Error.csvの統計を教えてください。", fixtures["error"], "8 Record", "2026_08_Error.csv"),
        ("Currentの規格値（LowerとUpper）で最も多い組み合わせは何ですか？", fixtures["spec"], "370 mA", "2026_08_Spec.csv"),
        ("シリアル「61C1068E7022」の8月12日と8月13日の判定結果を比較して、NG項目に変化はありますか？", fixtures["unittest"], "変わっていません", "2026_08_UnitTest.csv"),
        ("g1 và g2 có nominal và giới hạn nào?", fixtures["inspection"], "13.81", "3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx"),
    ]

    for question, custom_path, expected_kw, expected_doc in q_targets:
        assert query_might_be_structured_table(question) is True
        res = try_structured_table_evidence(question, custom_source_path=custom_path)
        assert res is not None, f"Failed for {question}"
        assert res["status"] == "structured_table_query"
        ans = res["local_synthesis"]["answer"]
        assert expected_kw in ans, f"Expected '{expected_kw}' in answer for {question}"
        assert expected_doc in ans, f"Expected citation '{expected_doc}' in answer for {question}"


def test_dynamic_table_computations_change_with_data(tmp_path):
    """Verify that dynamic calculations update deterministically across all behaviors when underlying data changes."""
    import csv
    from aios_habit.rag_v2.structured_query import try_structured_table_evidence

    def _write_csv(p, h, r):
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(h)
            w.writerows(r)

    # 1. Behavior: Record count, date range, and color breakdown (including single negative count mutation)
    csv_file1 = tmp_path / "test_bowoveradjust.csv"
    headers1 = ["DATE", "TIME", "S/N", "Mode", "Abstract", "ErrColor"]
    rows1 = [
        ["2026/08/01", "10:00:00", "61C1068E0001", "Adjust", "BowOverAdjustment", "Yellow"],
        ["2026/08/01", "10:05:00", "61C1068E0002", "Adjust", "BowOverAdjustment", "Yellow"],
        ["2026/08/02", "11:00:00", "61C1068E0003", "Adjust", "BowOverAdjustment", "Cyan"],
        ["2026/08/02", "11:05:00", "61C1068E0004", "Adjust", "BowOverAdjustment", "Magenta"],
    ]
    _write_csv(csv_file1, headers1, rows1)

    # Initial check
    res_cnt = try_structured_table_evidence("File có bao nhiêu record lỗi và phạm vi ngày nào?", custom_source_path=csv_file1)
    assert res_cnt is not None
    ans_cnt = res_cnt["local_synthesis"]["answer"]
    assert "4 record" in ans_cnt
    assert "2026/08/01" in ans_cnt
    assert "2026/08/02" in ans_cnt

    res_color = try_structured_table_evidence("BowOverAdjustエラーの各色（Yellow, Cyan, Magenta）の件数は？", custom_source_path=csv_file1)
    assert res_color is not None
    ans_color = res_color["local_synthesis"]["answer"]
    assert "Yellow**: **2件**" in ans_color
    assert "Cyan**: **1件**" in ans_color
    assert "Magenta**: **1件**" in ans_color

    res_black_0 = try_structured_table_evidence("BowOverAdjustエラーにBlackはありますか？", custom_source_path=csv_file1)
    assert res_black_0 is not None
    assert "0件" in res_black_0["local_synthesis"]["answer"]

    # Mutate data: add 5 new Magenta rows and 1 Black row on 2026/08/10
    for i in range(5):
        rows1.append(["2026/08/10", f"12:0{i}:00", f"61C1068E001{i}", "Adjust", "BowOverAdjustment", "Magenta"])
    rows1.append(["2026/08/10", "12:10:00", "61C1068E0099", "Adjust", "BowOverAdjustment", "Black"])
    _write_csv(csv_file1, headers1, rows1)

    # Mutated check: counts must change dynamically!
    res_cnt_mut = try_structured_table_evidence("File có bao nhiêu record lỗi và phạm vi ngày nào?", custom_source_path=csv_file1)
    assert res_cnt_mut is not None
    ans_cnt_mut = res_cnt_mut["local_synthesis"]["answer"]
    assert "10 record" in ans_cnt_mut
    assert "2026/08/10" in ans_cnt_mut

    res_color_mut = try_structured_table_evidence("BowOverAdjustエラーの各色（Yellow, Cyan, Magenta）の件数は？", custom_source_path=csv_file1)
    assert res_color_mut is not None
    ans_color_mut = res_color_mut["local_synthesis"]["answer"]
    assert "Magenta**: **6件**" in ans_color_mut
    assert "Yellow**: **2件**" in ans_color_mut

    # Mutated single color check: Black is now 1件, not 0件!
    res_black_mut = try_structured_table_evidence("BowOverAdjustエラーの各色 (Black) の件数は？", custom_source_path=csv_file1)
    assert res_black_mut is not None
    assert "Black**: **1件**" in res_black_mut["local_synthesis"]["answer"]

    # 2. Behavior: Peak date and overview count changes with data
    csv_file2 = tmp_path / "test_error.csv"
    headers2 = ["DATE", "TIME", "JigNumber", "S/N", "Mode"]
    rows2 = [
        ["2026/08/11", "08:00:00", "#1", "C9P001", "Error"],
        ["2026/08/11", "08:10:00", "#1", "C9P002", "Error"],
        ["2026/08/12", "09:00:00", "#1", "C9P003", "Error"],
    ]
    _write_csv(csv_file2, headers2, rows2)

    res_peak = try_structured_table_evidence("哪一天Error Record最多？", custom_source_path=csv_file2)
    assert res_peak is not None
    assert "2026/08/11" in res_peak["local_synthesis"]["answer"]
    assert "2笔" in res_peak["local_synthesis"]["answer"]

    res_stat = try_structured_table_evidence("2026_08_Error.csvの統計を教えてください。", custom_source_path=csv_file2)
    assert res_stat is not None
    assert "3 Record" in res_stat["local_synthesis"]["answer"]

    # Mutate data: add 5 errors on 2026/08/15
    for i in range(5):
        rows2.append(["2026/08/15", f"14:0{i}:00", "#1", f"C9P00{i+4}", "Error"])
    _write_csv(csv_file2, headers2, rows2)

    res_peak_mut = try_structured_table_evidence("哪一天Error Record最多？", custom_source_path=csv_file2)
    assert res_peak_mut is not None
    assert "2026/08/15" in res_peak_mut["local_synthesis"]["answer"]
    assert "5笔" in res_peak_mut["local_synthesis"]["answer"]

    res_stat_mut = try_structured_table_evidence("2026_08_Error.csvの統計を教えてください。", custom_source_path=csv_file2)
    assert res_stat_mut is not None
    assert "8 Record" in res_stat_mut["local_synthesis"]["answer"]

    # 3. Behavior: Serial lookup and comparison across dates
    csv_file3 = tmp_path / "test_unittest.csv"
    headers3 = ["DATE", "TIME", "S/N", "Mode", "TotalJudge", "Judge:Black", "Judge:Cyan", "Judge:Magenta", "Judge:Yellow"]
    rows3 = [
        ["2026/08/12", "10:00:00", "61CTEST00001", "UnitTest", "NG", "OK", "NG", "OK", "OK"],
        ["2026/08/13", "11:00:00", "61CTEST00001", "UnitTest", "NG", "OK", "NG", "OK", "OK"],
    ]
    _write_csv(csv_file3, headers3, rows3)

    q_sn = "シリアル「61CTEST00001」の8月12日と8月13日の判定結果を比較して、NG項目に変化はありますか？"
    res_sn = try_structured_table_evidence(q_sn, custom_source_path=csv_file3)
    assert res_sn is not None
    assert "変わっていません" in res_sn["local_synthesis"]["answer"]

    # Mutate data: day 2 passes OK
    rows3[1][4] = "OK"
    rows3[1][6] = "OK"
    _write_csv(csv_file3, headers3, rows3)

    res_sn_mut = try_structured_table_evidence(q_sn, custom_source_path=csv_file3)
    assert res_sn_mut is not None
    assert "có sự thay đổi" in res_sn_mut["local_synthesis"]["answer"]

    # 4. Behavior: Pair combination (Spec Lower & Upper)
    csv_file4 = tmp_path / "test_spec.csv"
    headers4 = ["Item", "Lower", "Upper", "Unit"]
    rows4 = [
        ["Current", "370", "520", "mA"],
        ["Current", "370", "520", "mA"],
        ["Current", "370", "520", "mA"],
        ["Current", "350", "500", "mA"],
    ]
    _write_csv(csv_file4, headers4, rows4)

    q_pair = "Currentの規格値（LowerとUpper）で最も多い組み合わせは何ですか？"
    res_pair = try_structured_table_evidence(q_pair, custom_source_path=csv_file4)
    assert res_pair is not None
    ans_pair = res_pair["local_synthesis"]["answer"]
    assert "370 mA" in ans_pair
    assert "520 mA" in ans_pair
    assert "3 record" in ans_pair

    # Mutate data: add 5 records of 400 mA / 600 mA
    for _ in range(5):
        rows4.append(["Current", "400", "600", "mA"])
    _write_csv(csv_file4, headers4, rows4)

    res_pair_mut = try_structured_table_evidence(q_pair, custom_source_path=csv_file4)
    assert res_pair_mut is not None
    ans_pair_mut = res_pair_mut["local_synthesis"]["answer"]
    assert "400 mA" in ans_pair_mut
    assert "600 mA" in ans_pair_mut
    assert "5 record" in ans_pair_mut

    # 5. Behavior: Nominal and limits from inspection sheet
    xlsx_file5 = tmp_path / "test_inspection.xlsx"
    rows_insp = [
        ["●3V2ND19040-MOUNT LD BLOCK"],
        ["NO", "Vị trí", "Kích thước", "Col D", "Dung sai", "Col F", "Col G", "Điểm đo", "Tol+", "Tol-", "S1", "S2", "S3", "S4", "S5", "S6", "Judge"],
        ["50", "1D", "", 13.81, "+0.12 -0.05", 0.12, 0.05, "g1", "", "", 13.85, 13.85, 13.85, 13.85, 13.85, 13.85, "O"],
        ["", "1D", "", 13.81, "+0.12 -0.05", 0.12, 0.05, "g2", "", "", 13.85, 13.85, 13.85, 13.85, 13.85, 13.85, "O"],
    ]
    _workbook(xlsx_file5, rows_insp, sheet="18.08.2026")

    q_insp = "g1 và g2 có nominal và giới hạn nào?"
    res_insp = try_structured_table_evidence(q_insp, custom_source_path=xlsx_file5)
    assert res_insp is not None
    ans_insp = res_insp["local_synthesis"]["answer"]
    assert "13.81" in ans_insp
    assert "13.93" in ans_insp
    assert "13.76" in ans_insp

    # Mutate data: change nominal to 15.50 with +0.20 / -0.10 (limits: 15.70 / 15.40)
    rows_insp_mut = [
        ["●3V2ND19040-MOUNT LD BLOCK"],
        ["NO", "Vị trí", "Kích thước", "Col D", "Dung sai", "Col F", "Col G", "Điểm đo", "Tol+", "Tol-", "S1", "S2", "S3", "S4", "S5", "S6", "Judge"],
        ["50", "1D", "", 15.50, "+0.20 -0.10", 0.20, 0.10, "g1", "", "", 15.55, 15.55, 15.55, 15.55, 15.55, 15.55, "O"],
        ["", "1D", "", 15.50, "+0.20 -0.10", 0.20, 0.10, "g2", "", "", 15.55, 15.55, 15.55, 15.55, 15.55, 15.55, "O"],
    ]
    _workbook(xlsx_file5, rows_insp_mut, sheet="18.08.2026")

    res_insp_mut = try_structured_table_evidence(q_insp, custom_source_path=xlsx_file5)
    assert res_insp_mut is not None
    ans_insp_mut = res_insp_mut["local_synthesis"]["answer"]
    assert "15.5" in ans_insp_mut
    assert "15.7" in ans_insp_mut
    assert "15.4" in ans_insp_mut


def test_structured_table_lane_clean_machine_simulation(monkeypatch, tmp_path):
    """Simulate a completely clean CI machine with zero production files."""
    import aios_habit.rag_v2.structured_query as sq

    # 1. Force find_structured_source_path to return None as on clean CI
    monkeypatch.setattr(sq, "find_structured_source_path", lambda *args, **kwargs: None)

    # 2. Fail-closed without custom source path
    assert sq.try_structured_table_evidence("2026年8月のBowOverAdjustエラー件数と期間を教えてください。") is None
    assert sq.try_structured_table_evidence("g1 và g2 có nominal và giới hạn nào?") is None
    assert sq.try_structured_table_evidence("Currentの規格値（LowerとUpper）で最も多い組み合わせは何ですか？") is None

    # 3. Succeeds deterministically with synthetic fixtures
    fixtures = _create_synthetic_structured_fixtures(tmp_path)
    res = sq.try_structured_table_evidence(
        "2026年8月のBowOverAdjustエラー件数と期間を教えてください。",
        custom_source_path=fixtures["bowoveradjust"],
    )
    assert res is not None
    assert "20 record" in res["local_synthesis"]["answer"]


def test_try_structured_table_evidence_named_doc_non_hijack():
    """Named PDF or missing doc must never be hijacked by structured table lane."""
    from aios_habit.rag_v2.structured_query import try_structured_table_evidence

    q_named_pdf = (
        "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), "
        "điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
    )
    assert try_structured_table_evidence(q_named_pdf, forced_domain="auto") is None
    assert try_structured_table_evidence(q_named_pdf, forced_domain=None) is None

    q_missing = "Theo tài liệu khong_ton_tai_123.pdf, nhiệt độ bảo quản là bao nhiêu?"
    assert try_structured_table_evidence(q_missing, forced_domain="auto") is None
    assert try_structured_table_evidence(q_missing, forced_domain=None) is None




