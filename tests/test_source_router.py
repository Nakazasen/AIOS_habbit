from aios_habit.rag_evidence import RAGEvidenceItem
from aios_habit.source_router import classify_query_profile, route_evidence_by_profile


def _item(evidence_id, file_type):
    return RAGEvidenceItem(
        evidence_id=evidence_id,
        chunk_id=evidence_id,
        document_id=evidence_id,
        citation_id=f"[{evidence_id}]",
        citation_label=file_type,
        source_title=file_type,
        relative_path="",
        file_type=file_type,
        privacy_mode="local_only",
        text="content",
        snippet="content",
        score=1.0,
        rank=1,
    )


def test_image_visible_facts_prefers_png_and_demotes_html():
    profile = classify_query_profile("what does screenshot show")
    items = [_item("1", "html"), _item("2", "png")]
    routed = route_evidence_by_profile(items, profile, "png")
    assert profile.profile_id == "image_visible_facts"
    assert any(i.file_type == "png" for i in routed.primary_items)
    assert any(i.file_type == "html" for i in routed.rejected_or_demoted_items)


def test_procedure_steps_prefers_document_sources():
    profile = classify_query_profile("explain the procedure steps in the manual")
    items = [_item("1", "xlsx"), _item("2", "pdf")]
    routed = route_evidence_by_profile(items, profile, "")
    assert profile.profile_id == "procedure_steps"
    assert any(i.file_type == "pdf" for i in routed.primary_items)
    assert any(i.file_type == "xlsx" for i in routed.supporting_items)


def test_handover_intent_beats_export_mapping_keyword():
    profile = classify_query_profile("next actions and handover process for missing export route")
    assert profile.profile_id == "handover_general"


def test_troubleshooting_intent_beats_mapping_keyword():
    profile = classify_query_profile("Give full troubleshooting path for export mapping failure")
    assert profile.profile_id == "troubleshooting_general"


def test_explicit_table_mapping_routes_to_extract_fields():
    profile = classify_query_profile("Explain Excel mapping fields and relationships")
    assert profile.profile_id == "extract_fields"
