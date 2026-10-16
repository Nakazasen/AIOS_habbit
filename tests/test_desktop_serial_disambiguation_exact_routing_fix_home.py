import pytest
from aios_habit import index_domain
from aios_habit.rag_v2.index import _has_maintenance_date_or_column_range
from aios_habit.rag_v2.query_planning import (
    coerce_query_plan,
    extract_content_terms,
    _clean_clause,
)


def test_dtl19_report_serial_disambiguation():
    q_dtl19 = (
        "Trong báo cáo điều tra lỗi Không lên nguồn.xlsx trên máy Iris2024 "
        "(số hiệu 05-0469, Serial J3C0053Y4242), cụm nguồn UNIT LOW VOLTAGE "
        "bị lỗi có mã linh kiện và nhà cung cấp là gì?"
    )
    matched, missing = index_domain.match_named_documents(q_dtl19)
    assert len(matched) >= 1, f"Expected matched documents for DTL19, got: {matched}"
    top_doc_name = getattr(matched[0].path, "name", str(matched[0]))
    assert "05-0469" in top_doc_name, f"Rank 1 should contain report 05-0469, got: {top_doc_name}"
    assert "Không lên nguồn.xlsx" in top_doc_name, f"Rank 1 should match Không lên nguồn.xlsx, got: {top_doc_name}"


def test_maintenance_date_and_column_range_detection():
    # Maintenance date query
    q_0704 = (
        "Trong file Sirius 2 _ C7620_報告版 4.pptx, vào đợt bảo dưỡng khuôn ngày 14/2 "
        "thì màu nào (Magenta hay Black hay Cyan hay Yellow) có sự thay đổi kích thước Housing lớn nhất?"
    )
    assert _has_maintenance_date_or_column_range(q_0704) is True

    # Numeric column range with backticks
    q_1827_with = "Các cột `-8` đến `-3` và `+2` đến `+8` ghi `--`; phải xử lý thế nào?"
    assert _has_maintenance_date_or_column_range(q_1827_with) is True

    # Numeric column range without backticks
    q_1827_without = "Các cột -8 đến -3 và +2 đến +8 ghi --; phải xử lý thế nào?"
    assert _has_maintenance_date_or_column_range(q_1827_without) is True


def test_query_planning_preserves_signed_numbers_and_dashes():
    q = "Các cột `-8` đến `-3` và `+2` đến `+8` ghi `--`; phải xử lý thế nào?"
    terms = extract_content_terms(q)
    for expected in ["-8", "-3", "+2", "+8", "--"]:
        assert expected in terms, f"Expected {expected} in terms, got: {terms}"

    clause = _clean_clause("Các cột `-8` đến `-3` và `+2` đến `+8` ghi `--`")
    assert "--" in clause, f"Expected '--' preserved in cleaned clause, got: {clause}"

    plan = coerce_query_plan(q)
    assert len(plan.variants) >= 2
    variant_texts = [v.text for v in plan.variants]
    assert any("--" in text for text in variant_texts)
