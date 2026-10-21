# -*- coding: utf-8 -*-
"""Unit tests for citation_source_viewer module.

Validates ticket DESKTOP-HOME-CITATION-SOURCE-VIEWER:
- Extraction of historical DB error cases, reference documents, and RAG citations.
- Reliable existence checking against local databases without dead links.
- Lazy on-demand resolving of full DB 30,075 records (all fields A-Y).
- Continuous improvement loop metric logging in local_cases.
- Clean user-facing labels without forbidden jargon.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typing import Any, List

from aios_habit.citation_source_viewer import (
    CitationRef,
    SourceRecordField,
    SourceViewerPayload,
    extract_citations_from_text,
    check_citation_exists,
    resolve_citation_source,
    record_source_verification_event,
    get_source_verification_metrics,
    render_assistant_answer_with_citations,
    render_source_viewer_panel,
)


def test_extract_citations_from_kdtps_synthesized_answer():
    content = """
Dựa trên cơ sở dữ liệu **30.075 ca điều tra lịch sử KDTPS** và danh mục mã lỗi chuẩn, dưới đây là thông tin điều tra và xử lý cho mã lỗi **C6770**:

### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi
- **Mã lỗi:** `C6770`
- **Tên mã lỗi / Hiện tượng:** Lỗi nguồn điện thấp Fuser IH
- **Phân loại hệ thống:** C_CALL
- **Cơ chế phát sinh:** Sau khi bắt đầu gia nhiệt Fuser...
- **Tài liệu tham chiếu:** 02XC_自己診断表示一覧表-Iris2020 VN.xls

### 4. Danh sách các ca điều tra thực tế đối chiếu (DB 30.075 ca)
Tìm thấy **5** ca điều tra thực tế liên quan trực tiếp đến mã lỗi **C6770**:

**1. Phiếu 2025/1155** (Iris2024 Mono / C33)
- **Hiện tượng:** Panel画面 "An Error has occurred"表示
- **Nguyên nhân:** 不要
- **Đối sách:** Link(jp+vn)
- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9609`

**2. Phiếu 2025/2076** (Iris2024 上位 / C33)
- **Hiện tượng:** LCC画面にAn Error has ocurred表示
- **Nguyên nhân:** 不要
- **Đối sách:** Tiếp tục tổng hợp theo dõi hiệu quả đối sách.
- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 10530`

**3. Phiếu 2025/1464** (Iris2024 Mono / C33)
- **Hiện tượng:** パネル画面 An Error has ocurred表示
- **Nguyên nhân:** 不要
- **Đối sách:** LK phát sinh sử dụng lot tháng 6 . Đối tác cải tiến tiếp mát JIG dự kiện lot tháng 7 . khi lk mới về KTĐ sẽ ban hành ĐUKC để sx , khi sx tiếp tục theo dõi
- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9918`
"""
    cites = extract_citations_from_text(content)
    assert len(cites) == 4

    # 1. Reference document
    doc_cite = cites[0]
    assert doc_cite.ref_type == "glossary_document"
    assert "02XC_自己診断表示一覧表-Iris2020 VN.xls" in doc_cite.source_file
    assert doc_cite.code == "C6770"

    # 2. Historical case 1 (row 9609)
    case_1 = cites[1]
    assert case_1.ref_type == "db_error_case"
    assert case_1.source_row == 9609
    assert "Loi KDTPS.xlsx" in case_1.source_file
    assert "History KDTPS" in case_1.sheet_name

    # 3. Historical case 2 (row 10530)
    case_2 = cites[2]
    assert case_2.ref_type == "db_error_case"
    assert case_2.source_row == 10530

    # 4. Historical case 3 (row 9918)
    case_3 = cites[3]
    assert case_3.ref_type == "db_error_case"
    assert case_3.source_row == 9918


def test_extract_citations_from_rag_answer():
    content = """
## Bang chung chinh
- [E1] [Primary] quy_trinh_bao_tri_may_in.pdf: Thao tác vệ sinh sấy cần thực hiện sau khi tắt nguồn 15 phút.
- [E2] [Supporting] so_tay_van_hanh.docx: Kiểm tra cảm biến nhiệt độ định kỳ mỗi tuần.

## Bang nguon
| Ref | Role | Source | Type | Location | Limitation |
|---|---|---|---|---|---|
| [E1] | Primary | quy_trinh_bao_tri_may_in.pdf | pdf | Trang 12 | extracted snippet |
| [E2] | Supporting | so_tay_van_hanh.docx | docx | Mục 4.2 | narrow evidence scope |
"""
    cites = extract_citations_from_text(content)
    assert len(cites) == 2
    assert cites[0].ref_type == "library_document"
    assert "quy_trinh_bao_tri_may_in.pdf" in cites[0].source_file
    assert cites[1].ref_type == "library_document"
    assert "so_tay_van_hanh.docx" in cites[1].source_file


def test_check_citation_exists_against_db():
    # Existing row in 30,075 DB
    ref_exist = CitationRef(
        id="case_9609",
        ref_type="db_error_case",
        label="Loi KDTPS.xlsx › History KDTPS › dòng 9609",
        source_file="Loi KDTPS.xlsx",
        sheet_name="History KDTPS",
        source_row=9609,
    )
    assert check_citation_exists(ref_exist) is True

    # Non-existent row (Requirement 2.3)
    ref_missing = CitationRef(
        id="case_999999",
        ref_type="db_error_case",
        label="Loi KDTPS.xlsx › History KDTPS › dòng 999999",
        source_file="Loi KDTPS.xlsx",
        sheet_name="History KDTPS",
        source_row=999999,
    )
    assert check_citation_exists(ref_missing) is False

    # Existing reference document in glossary
    ref_doc = CitationRef(
        id="doc_02xc",
        ref_type="glossary_document",
        label="02XC_自己診断表示一覧表-Iris2020 VN.xls",
        source_file="02XC_自己診断表示一覧表-Iris2020 VN.xls",
        code="C6770",
    )
    assert check_citation_exists(ref_doc) is True


def test_resolve_citation_source_db_error_case_all_fields_a_to_y():
    ref = CitationRef(
        id="case_9609",
        ref_type="db_error_case",
        label="Loi KDTPS.xlsx › History KDTPS › dòng 9609",
        source_file="Loi KDTPS.xlsx",
        sheet_name="History KDTPS",
        source_row=9609,
    )
    payload = resolve_citation_source(ref)
    assert payload.found is True
    assert payload.source_type == "db_error_case"
    assert "2025/1155" in payload.title
    assert "dòng 9609" in payload.identifier

    # Check that fields from A to Y are present
    col_letters = [f.column_letter for f in payload.fields]
    assert "A-B" in col_letters  # Phiếu
    assert "C" in col_letters    # Ngày
    assert "D" in col_letters    # Máy/Model
    assert "E" in col_letters    # Line
    assert "F" in col_letters    # Công đoạn
    assert "G" in col_letters    # Serial
    assert "H-I" in col_letters  # Mã lỗi
    assert "I" in col_letters    # Hiện tượng
    assert "AA" in col_letters   # Nguyên nhân
    assert "AB" in col_letters   # Đối sách

    # Check raw_json fidelity
    assert isinstance(payload.raw_json, dict)
    assert payload.raw_json.get("A") == 2025 or payload.raw_json.get("A") == "2025"
    assert payload.raw_json.get("B") == 1155 or payload.raw_json.get("B") == "1155"


def test_resolve_citation_source_glossary_reference_doc():
    ref = CitationRef(
        id="doc_02xc",
        ref_type="glossary_document",
        label="02XC_自己診断表示一覧表-Iris2020 VN.xls",
        source_file="02XC_自己診断表示一覧表-Iris2020 VN.xls",
        code="C6770",
    )
    payload = resolve_citation_source(ref)
    assert payload.found is True
    assert payload.source_type == "glossary_document"
    assert "C6770" in payload.identifier
    assert "Lỗi  nguồn điện thấp Fuser IH" in payload.excerpt_text
    assert "Sau khi bắt đầu gia nhiệt Fuser" in payload.excerpt_text
    assert "VI 1. Xác nhận kết nối" in payload.excerpt_text


def test_resolve_citation_source_missing_record():
    ref = CitationRef(
        id="case_missing",
        ref_type="db_error_case",
        label="Loi KDTPS.xlsx › History KDTPS › dòng 888888",
        source_file="Loi KDTPS.xlsx",
        sheet_name="History KDTPS",
        source_row=888888,
    )
    payload = resolve_citation_source(ref)
    assert payload.found is False
    assert "Không tìm thấy" in payload.error_message


def test_continuous_improvement_metric_logging(tmp_path: Path):
    ref = CitationRef(
        id="case_9609",
        ref_type="db_error_case",
        label="Loi KDTPS.xlsx › History KDTPS › dòng 9609",
        source_file="Loi KDTPS.xlsx",
        sheet_name="History KDTPS",
        source_row=9609,
    )

    # Record two verification events
    ev1 = record_source_verification_event("CONV-1", "MSG-1", ref, found=True, base_cases_dir=tmp_path)
    assert ev1["found"] is True
    assert ev1["source_row"] == 9609

    ref_bad = CitationRef(
        id="case_bad",
        ref_type="db_error_case",
        label="Loi KDTPS.xlsx › History KDTPS › dòng 999999",
        source_file="Loi KDTPS.xlsx",
        source_row=999999,
    )
    ev2 = record_source_verification_event("CONV-1", "MSG-1", ref_bad, found=False, base_cases_dir=tmp_path)
    assert ev2["found"] is False

    metrics = get_source_verification_metrics(base_cases_dir=tmp_path)
    assert metrics["total_views"] == 2
    assert metrics["successful_resolutions"] == 1
    assert metrics["missing_resolutions"] == 1
    assert metrics["views_by_type"].get("db_error_case") == 2


class _MockStreamlit:
    """Mock Streamlit interface for testing UI bubble rendering."""
    def __init__(self):
        self.rendered_markdowns: List[str] = []
        self.rendered_buttons: List[str] = []
        self.session_state: dict = {}
        self.rerun_called = False

    def markdown(self, text: str, **kwargs):
        self.rendered_markdowns.append(text)

    def button(self, label: str, key: str = "", **kwargs) -> bool:
        self.rendered_buttons.append(label)
        return False

    def caption(self, text: str, **kwargs):
        self.rendered_markdowns.append(text)

    def container(self, border: bool = False):
        return self

    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [self for _ in range(n)]

    def divider(self):
        pass

    def info(self, text: str):
        self.rendered_markdowns.append(text)

    def warning(self, text: str):
        self.rendered_markdowns.append(text)

    def error(self, text: str):
        self.rendered_markdowns.append(text)

    def expander(self, label: str, expanded: bool = False):
        return self

    def json(self, data: Any):
        pass

    def download_button(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_render_assistant_answer_with_citations_creates_buttons():
    mock_st = _MockStreamlit()
    answer = """
### 1. Định nghĩa kỹ thuật
- **Mã lỗi:** `C6770`
- **Tài liệu tham chiếu:** 02XC_自己診断表示一覧表-Iris2020 VN.xls

### 4. Ca lỗi thực tế
- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9609`
- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 999999`
"""
    render_assistant_answer_with_citations(
        st_module=mock_st,
        content=answer,
        conversation_id="CONV-TEST",
        message_id="MSG-TEST",
        notebook_id="NB-LAZY-DTL",
    )

    # Verify buttons are created for valid sources
    button_labels = " ".join(mock_st.rendered_buttons)
    assert "Mở nguồn tài liệu" in button_labels
    assert "02XC_自己診断表示一覧表-Iris2020 VN.xls" in button_labels
    assert "Xem hồ sơ gốc" in button_labels
    assert "dòng 9609" in button_labels

    # Verify invalid source is clearly marked not found in-place (Requirement 2.3)
    markdown_output = " ".join(mock_st.rendered_markdowns)
    assert "không tìm thấy nguồn gốc" in markdown_output
    assert "999999" in markdown_output
