from aios_habit.source_router import classify_query_profile, route_evidence_by_profile, get_base_source_type, QueryProfile
from aios_habit.rag_evidence import RAGEvidenceItem

def test_screenshot_prefers_png():
    profile = classify_query_profile("what does screenshot show")
    items = [
        RAGEvidenceItem(evidence_id="1", chunk_id="1", document_id="1", citation_id="[E1]", citation_label="html", source_title="", relative_path="", file_type="html", privacy_mode="", text="", snippet="", score=1.0, rank=1),
        RAGEvidenceItem(evidence_id="2", chunk_id="2", document_id="2", citation_id="[E2]", citation_label="png", source_title="", relative_path="", file_type="png", privacy_mode="", text="", snippet="", score=1.0, rank=2)
    ]
    routed = route_evidence_by_profile(items, profile, "png")
    assert any(i.file_type == "png" for i in routed.primary_items)
    # html is explicitly demoted for screenshot profiles
    assert any(i.file_type == "html" for i in routed.rejected_or_demoted_items)

def test_process_prefers_pdf():
    profile = classify_query_profile("quy trình automatic manual boundary")
    items = [
        RAGEvidenceItem(evidence_id="1", chunk_id="1", document_id="1", citation_id="[E1]", citation_label="excel", source_title="", relative_path="", file_type="xlsx", privacy_mode="", text="", snippet="", score=1.0, rank=1),
        RAGEvidenceItem(evidence_id="2", chunk_id="2", document_id="2", citation_id="[E2]", citation_label="pdf", source_title="", relative_path="", file_type="pdf", privacy_mode="", text="", snippet="", score=1.0, rank=2)
    ]
    routed = route_evidence_by_profile(items, profile, "")
    assert any(i.file_type == "pdf" for i in routed.primary_items)
    assert any(i.file_type == "xlsx" for i in routed.supporting_items)


def test_handover_intent_beats_export_mapping_keyword():
    profile = classify_query_profile("Owner next actions and handover process for missing export route")
    assert profile.profile_id == "owner_handover"


def test_troubleshooting_intent_beats_mapping_keyword():
    profile = classify_query_profile("Give full troubleshooting path for export mapping failure")
    assert profile.profile_id == "mixed_troubleshooting"


def test_explicit_excel_mapping_still_routes_to_spreadsheet():
    profile = classify_query_profile("Explain Excel mapping fields and relationships")
    assert profile.profile_id == "excel_mapping"
