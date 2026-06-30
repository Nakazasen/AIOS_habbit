from aios_habit.final_answer_composer import compose_final_owner_answer
from aios_habit.rag_evidence import build_evidence_pack
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks


def _pack(privacy_mode="cloud_safe", query="export mapping", chunks=None):
    import sqlite3

    chunks = chunks or [
        RAGChunk("C1", "D1", ["e1"], "The procedure says check the dispatch record before release.", "Setup", "setup.pdf", "setup.pdf", "Setup p1", "pdf", ["text"], [1], [], [], [], [], [], privacy_mode),
        RAGChunk("C2", "D2", ["e2"], "Route code is blank in the shipping data table.", "Checklist", "check.xlsx", "check.xlsx", "Checklist Sheet1", "spreadsheet", ["row"], [], ["Sheet1"], [], [], ["2:2"], ["A2:C2"], privacy_mode),
    ]
    conn = sqlite3.connect(":memory:")
    try:
        create_rag_search_schema(conn)
        index_rag_chunks(conn, chunks)
        results = search_rag_chunks(conn, query, limit=5)
        return build_evidence_pack(query, results)
    finally:
        conn.close()


def test_final_answer_does_not_contain_local_draft_marker():
    answer = compose_final_owner_answer(_pack("local_only"))
    assert "Local draft for" not in answer.answer_text
    assert answer.final_answer is True
    assert answer.provider_call is False
    assert answer.notebooklm_call is False


def test_final_answer_directly_answers_question_with_required_sections():
    answer = compose_final_owner_answer(_pack(query="What should we check next?"))
    assert "Ket luan ngan" in answer.answer_text
    assert "Huong xu ly / kiem tra" in answer.answer_text
    assert "Khong duoc ket luan" in answer.answer_text


def test_table_answer_contains_fields_and_relationships():
    answer = compose_final_owner_answer(_pack(query="Explain Excel mapping fields and relationships"), target_source_type="xlsx")
    text = answer.answer_text.lower()
    assert "field" in text
    assert "key" in text
    assert answer.metadata["answer_profile"] == "extract_fields"


def test_pdf_answer_contains_procedure_boundaries():
    answer = compose_final_owner_answer(_pack(query="Explain procedure steps in the manual"), target_source_type="pdf")
    text = answer.answer_text.lower()
    assert "documented steps" in text
    assert "records or logs" in text
    assert answer.metadata["answer_profile"] == "procedure_steps"


def test_image_answer_separates_visible_and_inferred():
    answer = compose_final_owner_answer(_pack(query="What does screenshot show?"), target_source_type="png")
    text = answer.answer_text.lower()
    assert "visible" in text
    assert "infer" in text
    assert answer.metadata["answer_profile"] == "image_visible_facts"


def test_troubleshooting_answer_contains_step_by_step_actions():
    answer = compose_final_owner_answer(_pack(query="Give full troubleshooting path and missing evidence"))
    text = answer.answer_text.lower()
    assert "timeline" in text
    assert "missing evidence" in text
    assert "1." in text and "2." in text and "3." in text


def test_handover_answer_contains_general_next_actions():
    answer = compose_final_owner_answer(_pack(query="next actions and handover"))
    text = answer.answer_text.lower()
    assert "handover" in text
    assert "responsible party" in text
    assert answer.metadata["domain_playbook"] == "general"


def test_general_default_does_not_inject_manufacturing_terms():
    answer = compose_final_owner_answer(_pack(query="What should we check next?"))
    text = answer.answer_text.lower()
    for term in ["wms", "mom", "agv", "oricon", "supply line", "manufacturing workflow"]:
        assert term not in text


def test_manufacturing_playbook_requires_explicit_allowance():
    pack = _pack(query="MOM WMS AGV troubleshooting path")
    general_answer = compose_final_owner_answer(pack)
    manufacturing_answer = compose_final_owner_answer(
        pack,
        domain_playbook="manufacturing_mom_wms",
        allow_domain_assist=True,
    )
    assert general_answer.metadata["domain_playbook"] == "general"
    assert manufacturing_answer.metadata["domain_playbook"] == "manufacturing_mom_wms"
    assert "interface records" in manufacturing_answer.answer_text


def test_citations_are_used_in_actual_claims():
    answer = compose_final_owner_answer(_pack(query="Route code"), target_source_type="xlsx")
    assert "[E1]" in answer.answer_text
    assert "Why it matters" in answer.answer_text


def test_local_only_safety_remains():
    answer = compose_final_owner_answer(_pack("local_only"))
    assert answer.privacy_mode == "local_only"
    assert answer.provider_call is False
    assert any("local_only" in warning for warning in answer.warnings)
