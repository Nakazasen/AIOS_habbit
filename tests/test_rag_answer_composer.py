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
    assert "No extracted content evidence was available" in draft.answer_text
    assert draft.citation_ids == []


def test_compose_local_answer_local_only_privacy_warning():
    pack = _pack("local_only")
    draft = compose_local_answer(pack)
    assert draft.privacy_mode == "local_only"
    assert draft.allowed_external is False
    assert any("local_only" in warning for warning in draft.warnings)
    assert "must not be exported externally" in draft.answer_text


def test_compose_local_answer_metadata_only():
    import sqlite3
    chunks = [
        RAGChunk("C1", "D1", ["e1"], "metadata-only source record\nFile Path: doc.pdf\nSize: 100", "Metadata", "doc.pdf", "doc.pdf", "doc.pdf", "pdf", ["metadata"], [], [], [], [], [], [], "cloud_safe", metadata={"_is_metadata_only": "True"}),
    ]
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    index_rag_chunks(conn, chunks)
    results = search_rag_chunks(conn, "doc", limit=5)
    pack = build_evidence_pack("doc", results)
    
    draft = compose_local_answer(pack)
    assert pack.insufficient_evidence is True
    assert pack.confidence_label == "low"
    assert pack.metadata_only_evidence_count == 1
    assert draft.answer_kind == "local_evidence_draft"
    assert any("Only metadata was found" in warning for warning in draft.warnings)
    assert "No extracted content evidence was available" in draft.answer_text
    assert draft.citation_ids == []


def test_compose_local_answer_mixed_evidence():
    import sqlite3
    chunks = [
        RAGChunk("C1", "D1", ["e1"], "Real doc content here", "Content", "doc_file.txt", "doc_file.txt", "doc_file.txt", "txt", ["text"], [], [], [], [], [], [], "cloud_safe"),
        RAGChunk("C2", "D2", ["e2"], "metadata-only source record\nFile Path: doc.pdf\nSize: 100", "Metadata", "doc.pdf", "doc.pdf", "doc.pdf", "pdf", ["metadata"], [], [], [], [], [], [], "cloud_safe", metadata={"_is_metadata_only": "True"}),
    ]
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    index_rag_chunks(conn, chunks)
    results = search_rag_chunks(conn, "doc", limit=5)
    pack = build_evidence_pack("doc", results)
    
    draft = compose_local_answer(pack)
    assert draft.insufficient_evidence is False
    assert len(draft.citation_ids) == 1
    assert "Real doc content here" in draft.answer_text
    assert "Excluded 1 metadata-only results" in draft.answer_text

def test_strong_answer_via_fake_provider_returns_final_answer_true():
    from aios_habit.ai_provider_bridge import FakeProvider
    pack = _pack("cloud_safe")
    provider = FakeProvider()
    answer = provider.generate_answer("query", pack, "policy", "cloud_safe")
    
    assert answer.final_answer is True
    assert answer.answer_kind == "strong_model_answer"
    assert answer.provider_name == "fake_provider"
    assert answer.provider_call is True
    assert len(answer.citation_ids) > 0

def test_paste_back_answer_stores_metadata():
    from aios_habit.rag_answer_composer import PastedStrongModelAnswer
    pack = _pack("cloud_safe")
    
    answer = PastedStrongModelAnswer(
        draft_id="draft123",
        pack_id=pack.pack_id,
        query="query",
        answer_text="User pasted this",
        citation_ids=["CIT-1"],
        evidence_ids=["EVD-1"],
        privacy_mode="cloud_safe",
        allowed_external=True,
        insufficient_evidence=False,
        confidence_label="high",
        model_tool_name="chatgpt",
    )
    
    assert answer.final_answer is True
    assert answer.answer_kind == "pasted_strong_model_answer"
    assert answer.provider_call is False
    assert answer.model_tool_name == "chatgpt"
    assert answer.route_summary == "Manual paste-back by user"
