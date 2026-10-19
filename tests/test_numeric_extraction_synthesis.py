"""Regression tests for numeric extraction, tolerance specification, and header demotion in synthesis.

Ticket: DESKTOP-SYNTHESIS-NUMERIC-EXTRACTION-IMPROVE-HOME
Criteria:
- Table data rows with numeric measurements/tolerances are prioritized over table headers / section titles.
- Asymmetric tolerances (+0.08 / -0.05) are extracted and compute limits (38.95 ~ 39.08).
- Pure table/section headers without data are demoted.
- Document metadata rows (author, version, date) are preserved and selected when asked.
"""
from aios_habit.rag_v2.evidence import build_evidence_pack
from aios_habit.rag_v2.query_planning import coerce_query_plan
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.synthesis import (
    synthesize_evidence,
    _is_pure_header,
)


def _make_result(
    chunk_id: str,
    doc_id: str,
    score: float,
    text: str,
    source_name: str = "document.xlsx",
    file_type: str = "xlsx",
    metadata: dict = None,
    matched_terms: tuple = ("measurement",),
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        document_id=doc_id,
        source_path=f"/workspace/{source_name}",
        source_name=source_name,
        file_type=file_type,
        metadata=metadata or {},
        privacy_labels=("allowed",),
        ranking_signals={"lexical": score, "dense": score},
        matched_terms=matched_terms,
        term_coverage=1.0,
        matched_query_facets=(),
        matched_obligations=(),
    )


def test_numeric_data_row_beats_pure_table_header():
    """Verify numeric data rows beat column headers and section titles in synthesis answer."""
    header_chunk = (
        "Section: LDブラケット測定/ Đo độ lệch Bracket\n"
        "Columns: Điểm đo | Dung sai trên | Dung sai dưới | Tiêu chuẩn đo\n"
        "Kích thước đo — Điểm đo — Dung sai trên — Dung sai dưới"
    )
    data_chunk = (
        "Section: Đo độ lệch Bracket\n"
        "Columns: Nhóm | Điểm đo No.1-3 | Điểm đo No.2-4 | Dung sai\n"
        "Row 87: _NG UNIT | -0.002 | 0.015 | 0.043 | -0.011\n"
        "Row 88: _OK UNIT | 0.001 | 0.003 | 0.002 | 0.001"
    )

    query = "Giá trị đo độ lệch Bracket là bao nhiêu?"
    plan = coerce_query_plan(query)

    resp = SearchResponse(
        results=(
            _make_result("c_hdr", "doc1", 9.0, header_chunk, source_name="measurement.xlsx", matched_terms=plan.target_terms),
            _make_result("c_dat", "doc1", 8.5, data_chunk, source_name="measurement.xlsx", matched_terms=plan.target_terms),
        ),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=2,
            eligible_chunk_count=2,
            candidate_count=2,
            returned_count=2,
            best_term_coverage=1.0,
        ),
    )
    pack = build_evidence_pack(plan, resp)
    res = synthesize_evidence(pack)

    assert res.grounded is True
    assert "0.002" in res.answer or "-0.002" in res.answer
    assert "0.015" in res.answer


def test_asymmetric_tolerance_specifications_extracted():
    """Verify asymmetric tolerances compute nominal, bounds, and are selected."""
    spec_chunk = (
        "Sheet: 18.08.2026\n"
        "Columns: NO | Vị trí bản vẽ | Kích thước đo | Dung sai | Điểm đo | Dung sai trên | Dung sai dưới\n"
        "Row 24: 48 | 21C | 39 | +0.08 -0.05 | Y73 | 0.08 | 0.05\n"
        "Row 55: 49 | 21C | 39 | +0.08 -0.05 | Y104 | 0.08 | 0.05"
    )
    query = "Kích thước tại các điểm Y73–Y104 có giới hạn bao nhiêu?"
    plan = coerce_query_plan(query)

    resp = SearchResponse(
        results=(
            _make_result("c_spec", "doc_tol", 9.0, spec_chunk, source_name="mount_ld_block.xlsx", matched_terms=plan.target_terms),
        ),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=1,
            eligible_chunk_count=1,
            candidate_count=1,
            returned_count=1,
            best_term_coverage=1.0,
        ),
    )
    pack = build_evidence_pack(plan, resp)
    res = synthesize_evidence(pack)

    assert res.grounded is True
    assert "39" in res.answer
    assert "+0.08 / -0.05" in res.answer or "+0.08 -0.05" in res.answer
    assert "39.08" in res.answer
    assert "38.95" in res.answer


def test_pure_header_detection():
    """Test _is_pure_header accurately distinguishes headers from data."""
    assert _is_pure_header("Section: LDブラケット測定/ Đo độ lệch Bracket") is True
    assert _is_pure_header("Columns: Điểm đo | Dung sai trên | Dung sai dưới") is True
    assert _is_pure_header("Kích thước đo — Điểm đo — Dung sai trên — Dung sai dưới") is True
    assert _is_pure_header("Header row 86: NO | Item | Value") is True

    # Real data rows MUST NOT be classified as pure headers
    assert _is_pure_header("Row 87: _NG UNIT (No.1-3: -0.002, No.2-4: 0.015)") is False
    assert _is_pure_header("Row 24: điểm đo Y73: kích thước 39, dung sai +0.08 / -0.05, giới hạn 38.95 ~ 39.08") is False
    assert _is_pure_header("Được tạo bởi: Kazuma Tsutsumi") is False
    assert _is_pure_header("Phiên bản: 0.01 ngày 2026/05/01") is False


def test_metadata_author_and_version_selection():
    """Verify author and version metadata rows beat generic overview text for creator questions."""
    doc_summary_chunk = (
        "File Excel: マテコン操作手順書_v001_生産技術_TV.xlsx\n"
        "Mô tả quy trình đăng ký xe tự hành AGV và cấu hình hệ thống giao tiếp."
    )
    meta_chunk = (
        "Tên tài liệu: Giao diện truyền thông bảng điều khiển\n"
        "Phiên bản: 0.01\n"
        "Ngày hiệu lực: 2026-05-01\n"
        "Được tạo bởi: Kazuma Tsutsumi"
    )
    query = "Tài liệu Giao diện truyền thông phiên bản 0.01 được tạo bởi ai?"
    plan = coerce_query_plan(query)

    resp = SearchResponse(
        results=(
            _make_result("c_sum", "doc_matecon", 9.0, doc_summary_chunk, source_name="matecon.xlsx", metadata={"representation_role": "summary"}, matched_terms=plan.target_terms),
            _make_result("c_meta", "doc_matecon", 8.8, meta_chunk, source_name="matecon.xlsx", matched_terms=plan.target_terms),
        ),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=2,
            eligible_chunk_count=2,
            candidate_count=2,
            returned_count=2,
            best_term_coverage=1.0,
        ),
    )
    pack = build_evidence_pack(plan, resp)
    res = synthesize_evidence(pack)

    assert res.grounded is True
    assert "Kazuma Tsutsumi" in res.answer
    assert "0.01" in res.answer
    assert "2026/05/01" in res.answer or "2026-05-01" in res.answer
