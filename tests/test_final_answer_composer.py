from aios_habit.final_answer_composer import compose_final_owner_answer
from aios_habit.rag_evidence import build_evidence_pack
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks


def _pack(privacy_mode="cloud_safe", query="export mapping"):
    import sqlite3
    chunks = [
        RAGChunk("C1", "D1", ["e1"], "Export mapping missing before dispatch.", "Setup", "setup.pdf", "setup.pdf", "Setup p1", "pdf", ["text"], [1], [], [], [], [], [], privacy_mode),
        RAGChunk("C2", "D2", ["e2"], "Route code is blank in shipping master data.", "Checklist", "check.xlsx", "check.xlsx", "Checklist Sheet1", "spreadsheet", ["row"], [], ["Sheet1"], [], [], ["2:2"], ["A2:C2"], privacy_mode),
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
    answer = compose_final_owner_answer(_pack(query="What should owner check next?"))
    assert "Kết luận ngắn" in answer.answer_text
    assert "Hướng xử lý / kiểm tra" in answer.answer_text
    assert "Không được kết luận" in answer.answer_text


def test_excel_mapping_answer_contains_fields_and_relationships():
    answer = compose_final_owner_answer(_pack(query="Explain Excel mapping fields and relationships"), target_source_type="xlsx")
    text = answer.answer_text.lower()
    assert "mapping" in text
    assert "trường" in text
    assert "quan hệ" in text


def test_pdf_pptx_answer_contains_automatic_manual_boundary():
    answer = compose_final_owner_answer(_pack(query="Explain automatic/manual boundary"), target_source_type="pdf")
    text = answer.answer_text.lower()
    assert "tự động" in text
    assert "thủ công" in text


def test_screenshot_answer_separates_visible_and_inferred():
    answer = compose_final_owner_answer(_pack(query="What does screenshot show?"), target_source_type="png")
    text = answer.answer_text.lower()
    assert "nhìn thấy" in text
    assert "suy luận" in text


def test_mixed_troubleshooting_answer_contains_step_by_step_actions():
    answer = compose_final_owner_answer(_pack(query="Give full troubleshooting path and missing evidence"))
    text = answer.answer_text.lower()
    assert "timeline" in text
    assert "missing evidence" in text
    assert "1." in text and "2." in text and "3." in text


def test_handover_answer_contains_owner_next_actions():
    answer = compose_final_owner_answer(_pack(query="owner next actions and handover"))
    text = answer.answer_text.lower()
    assert "owner" in text
    assert "timeline" in text or "bàn giao" in text


def test_citations_are_used_in_actual_claims():
    answer = compose_final_owner_answer(_pack(query="export mapping"))
    assert "[E1]" in answer.answer_text
    assert "Vì sao quan trọng" in answer.answer_text


def test_local_only_safety_remains():
    answer = compose_final_owner_answer(_pack("local_only"))
    assert answer.privacy_mode == "local_only"
    assert answer.provider_call is False
    assert any("local_only" in warning for warning in answer.warnings)
