import json

from aios_habit.ide_bridge import (
    build_ide_prompt_pack,
    ide_answer_to_dict,
    record_paste_back_answer,
    validate_prompt_export,
)
from aios_habit.rag_benchmark import (
    RAGBenchmarkConfig,
    RAGBenchmarkQuestion,
    format_benchmark_summary,
    run_rag_benchmark,
)
from aios_habit.rag_evidence import build_evidence_pack, format_evidence_pack_for_prompt
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import (
    RAGSearchFilter,
    create_rag_search_schema,
    index_rag_chunks,
    search_rag_chunks,
)


def _owner_chunks(privacy_mode="cloud_safe"):
    return [
        RAGChunk("OWN-PDF-1", "OWNER-DOC-PDF", ["p1"], "Line A shipping setup error occurs when export mapping is missing before dispatch.", "Owner pilot setup note", "owner_pilot/setup.pdf", "owner_pilot/setup.pdf", "Setup Note p1", "pdf", ["text"], [1], [], [], ["Issue"], [], [], privacy_mode),
        RAGChunk("OWN-XLS-1", "OWNER-DOC-XLS", ["sheet1-r2"], "Before retry, verify export mapping, route code, and shipping master data.", "Owner pilot checklist", "owner_pilot/checklist.xlsx", "owner_pilot/checklist.xlsx", "Checklist Sheet1", "spreadsheet", ["table_row"], [], ["Sheet1"], [], [], ["2:2"], ["A2:C2"], privacy_mode),
        RAGChunk("OWN-LOG-1", "OWNER-DOC-LOG", ["log1"], "ERROR Line A dispatch blocked: route code blank after export mapping validation.", "Owner pilot log", "owner_pilot/app.log", "owner_pilot/app.log", "App Log", "text", ["log"], [], [], [], [], [], [], privacy_mode),
    ]


def _search(chunks, query, filters=None):
    import sqlite3
    conn = sqlite3.connect(":memory:")
    try:
        create_rag_search_schema(conn)
        index_rag_chunks(conn, chunks)
        return search_rag_chunks(conn, query, filters=filters, limit=5)
    finally:
        conn.close()


def test_phase4_owner_pilot_cloud_safe_worklens_flow():
    chunks = _owner_chunks("cloud_safe")
    query = "export mapping"
    results = _search(chunks, query, RAGSearchFilter(privacy_modes=["cloud_safe"]))
    assert {r.chunk_id for r in results} >= {"OWN-PDF-1", "OWN-XLS-1", "OWN-LOG-1"}
    pack = build_evidence_pack(query, results)
    assert pack.privacy_mode == "cloud_safe"
    assert pack.allowed_external is True
    assert pack.insufficient_evidence is False
    assert all(not item.relative_path.startswith("D:") for item in pack.items)
    prompt_pack = build_ide_prompt_pack(pack, "Gemini Pro 3.1 High")
    assert validate_prompt_export(prompt_pack) is True
    assert prompt_pack.export_policy == "allowed_cloud_safe"
    assert prompt_pack.evidence_refs and prompt_pack.citation_ids
    assert "ONLY the provided Evidence Pack" in prompt_pack.prompt_text
    answer = record_paste_back_answer(
        prompt_pack,
        model_tool_name="Gemini Pro 3.1 High (manual paste-back)",
        answer_text="Likely cause: missing export mapping or blank route code. Check mapping, route code, and shipping master data.",
        route_summary="cloud_safe manual IDE bridge; evidence-only answer; no provider automation",
        confidence_label=pack.confidence_label,
    )
    assert answer.external_ai_used is True
    assert answer.evidence_refs == prompt_pack.evidence_refs
    assert answer.citation_ids == prompt_pack.citation_ids
    assert "manual IDE bridge" in answer.route_summary
    json.dumps(ide_answer_to_dict(answer))


def test_phase4_owner_pilot_local_only_blocks_external_export():
    chunks = _owner_chunks("local_only")
    query = "export mapping"
    results = _search(chunks, query, RAGSearchFilter(privacy_modes=["local_only"]))
    pack = build_evidence_pack(query, results)
    assert pack.privacy_mode == "local_only"
    assert pack.allowed_external is False
    prompt_pack = build_ide_prompt_pack(pack, "Gemini Pro 3.1 High")
    assert validate_prompt_export(prompt_pack) is False
    assert prompt_pack.export_policy == "blocked_local_only"
    assert "DO NOT EXPORT EXTERNALLY" in prompt_pack.prompt_text
    assert "External export NOT allowed" in prompt_pack.prompt_text


def test_phase4_owner_pilot_insufficient_and_benchmark_summary():
    chunks = _owner_chunks("cloud_safe")
    missing_query = "Ai phê duyệt ngân sách quảng cáo Q4?"
    results = _search(chunks, missing_query)
    pack = build_evidence_pack(missing_query, results)
    prompt_pack = build_ide_prompt_pack(pack, "Gemini Pro 3.1 High")
    prompt_text = format_evidence_pack_for_prompt(pack)
    assert pack.insufficient_evidence is True
    assert "Insufficient evidence" in prompt_text
    assert "abstain from guessing" in prompt_pack.prompt_text
    questions = [
        RAGBenchmarkQuestion("PILOT-Q1", "export mapping route code", "answerable", ["OWN-LOG-1"], ["OWNER-DOC-LOG"], ["App Log"], "cloud_safe"),
        RAGBenchmarkQuestion("PILOT-Q2", "shipping master data", "answerable", ["OWN-XLS-1"], ["OWNER-DOC-XLS"], ["Checklist Sheet1"], "cloud_safe"),
        RAGBenchmarkQuestion("PILOT-Q3", "line A shipping setup error dispatch", "answerable", ["OWN-PDF-1"], ["OWNER-DOC-PDF"], ["Setup Note p1"], "cloud_safe"),
        RAGBenchmarkQuestion("PILOT-Q4", missing_query, "insufficient", [], [], [], "cloud_safe"),
    ]
    summary = run_rag_benchmark(
        chunks, questions,
        RAGBenchmarkConfig(tier="custom", top_k=3, min_top_chunk_hit_rate=0.75, min_document_hit_rate=0.75, min_citation_hit_rate=0.75, min_insufficient_detection_rate=1.0, min_privacy_pass_rate=1.0),
    )
    formatted = format_benchmark_summary(summary)
    assert summary.question_count == 4
    assert summary.privacy_pass_rate == 1.0
    assert summary.insufficient_detection_rate == 1.0
    assert "retrieval/evidence only" in formatted
    assert "NOT an LLM generation parity claim vs NotebookLM" in formatted
