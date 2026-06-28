import json

from aios_habit.rag_answer_composer import compose_local_answer, local_answer_draft_to_dict
from aios_habit.rag_evidence import EvidencePackConfig, build_evidence_pack
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


def test_compose_local_answer_preserves_citations_and_is_deterministic():
    pack = _pack("cloud_safe")
    first = compose_local_answer(pack)
    second = compose_local_answer(pack)
    assert first.draft_id == second.draft_id
    assert first.provider_call is False
    assert first.notebooklm_call is False
    assert first.citation_ids == [item.citation_id for item in pack.items]
    assert first.evidence_ids == [item.evidence_id for item in pack.items]
    assert "Evidence-grounded points" in first.answer_text
    assert all(citation in first.answer_text for citation in first.citation_ids)
    json.dumps(local_answer_draft_to_dict(first))


def test_compose_local_answer_insufficient_evidence_warning():
    pack = build_evidence_pack("unknown approval", [], EvidencePackConfig())
    draft = compose_local_answer(pack)
    assert draft.insufficient_evidence is True
    assert any("Insufficient evidence" in warning for warning in draft.warnings)
    assert "No cited evidence was available" in draft.answer_text
    assert draft.citation_ids == []


def test_compose_local_answer_local_only_privacy_warning():
    pack = _pack("local_only")
    draft = compose_local_answer(pack)
    assert draft.privacy_mode == "local_only"
    assert draft.allowed_external is False
    assert any("local_only" in warning for warning in draft.warnings)
    assert "must not be exported externally" in draft.answer_text
