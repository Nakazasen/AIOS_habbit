import pytest
from aios_habit.citation_answer import (
    build_citation_index,
    format_inline_citation,
    build_source_traceability_table,
    extract_visible_vs_inferred_claims,
    score_citation_coverage,
    compose_citation_first_answer,
    CitationRef
)

class MockEvidenceItem:
    def __init__(self, chunk_id, text, source_title, file_type, privacy_mode, page_numbers=None, sheet_names=None):
        self.chunk_id = chunk_id
        self.text = text
        self.source_title = source_title
        self.file_type = file_type
        self.privacy_mode = privacy_mode
        if page_numbers:
            self.page_numbers = page_numbers
        if sheet_names:
            self.sheet_names = sheet_names

def test_citation_index_creates_stable_refs():
    items = [
        MockEvidenceItem("CH-1", "Text A", "Doc A", "pdf", "local_only", page_numbers=[1, 2]),
        MockEvidenceItem("CH-2", "Text B", "Doc B", "html", "cloud_safe")
    ]
    refs = build_citation_index(items)
    assert len(refs) == 2
    assert refs[0].ref_id == "[E1]"
    assert refs[0].location == "Page 1,2"
    assert refs[1].ref_id == "[E2]"
    assert refs[1].location == "Toàn bộ"

def test_source_traceability_table():
    refs = [
        CitationRef("[E1]", "Pic.png", "png", "local_only", "Toàn bộ", "CH-1", "snippet1"),
        CitationRef("[E2]", "Spec.pdf", "pdf", "cloud_safe", "Page 3", "CH-2", "snippet2")
    ]
    table = build_source_traceability_table(refs)
    assert "| [E1] | Pic.png | PNG | Toàn bộ | Chỉ nhìn thấy ảnh" in table
    assert "| [E2] | Spec.pdf | PDF | Page 3 | Mô tả quy trình lý tưởng" in table

def test_citation_first_answer_format():
    refs = [CitationRef("[E1]", "Doc", "pdf", "cloud_safe", "Toàn bộ", "CH-1", "snippet")]
    draft = "Short answer.\n\nMore details."
    ans = compose_citation_first_answer("Q?", refs, draft, "pdf")
    
    assert "### Trả lời ngắn" in ans
    assert "Short answer." in ans
    assert "### Bằng chứng chính" in ans
    assert "### Phân tích" in ans
    assert "### Không được suy luận quá mức" in ans
    assert "### Việc cần làm tiếp" in ans
    assert "### Bảng nguồn" in ans
    assert "| [E1]" in ans

def test_screenshot_visible_vs_inferred_warning():
    refs = [CitationRef("[E1]", "Pic", "png", "cloud_safe", "Toàn bộ", "CH-1", "snippet")]
    ans = compose_citation_first_answer("Q?", refs, "Draft", "screenshot")
    assert "Nhìn thấy trực tiếp" in ans
    assert "Có thể dùng làm bằng chứng" in ans
    assert "Không được suy luận logic nghiệp vụ" in ans

def test_pdf_automatic_vs_manual_boundary():
    refs = [CitationRef("[E1]", "Spec", "pdf", "cloud_safe", "Toàn bộ", "CH-1", "snippet")]
    ans = compose_citation_first_answer("Q?", refs, "Draft", "pdf")
    assert "Tự động xử lý" in ans
    assert "Cần xử lý thủ công / owner review" in ans

def test_citation_coverage_metric():
    refs = [
        CitationRef("[E1]", "A", "pdf", "cloud_safe", "L1", "C1", "S1"),
        CitationRef("[E2]", "B", "pdf", "cloud_safe", "L2", "C2", "S2")
    ]
    ans_text = "Dựa trên [E1], ta thấy X. Không được suy luận."
    metrics = score_citation_coverage(ans_text, refs)
    assert metrics["citation_count"] == 1
    assert metrics["cited_evidence_count"] == 1
    assert metrics["uncited_evidence_count"] == 1
    assert metrics["unsupported_claim_warning_count"] == 1
    assert metrics["coverage_ratio"] == 0.5
