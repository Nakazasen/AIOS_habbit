"""Summary-first routing stays off unless the operator opts in."""

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import LocalChunkIndex
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.query_planning import (
    apply_summary_first_to_plan,
    build_query_plan,
    detect_retrieval_mode,
    identity_query_plan,
    resolve_summary_first_routing,
)


OVERVIEW_SAMPLES = (
    "Tóm tắt các tài liệu đã nạp",
    "Tổng quan hệ thống",
    "What is this corpus about?",
    "Giới thiệu các tài liệu",
    "Overview of the collected manuals",
)
DETAILED_SAMPLES = (
    "What is the exact cell range for SKU-123?",
    "Kiểm tra lỗi C001 trên máy A",
    "Làm thế nào để reset máy X200?",
    "Compare version 1 and version 2 of SOP-ABC",
    "How does data flow between the tank system and the pump controller?",
)


def test_flag_off_keeps_identity_plan_and_variant_budget(monkeypatch):
    monkeypatch.delenv("AIOS_RAG_V2_SUMMARY_FIRST", raising=False)
    assert resolve_summary_first_routing(False) is False
    query = "Tóm tắt các tài liệu đã nạp"
    plan = identity_query_plan(query)
    assert plan.retrieval_mode == "full"
    assert len(plan.variants) == len(identity_query_plan(query).variants)
    expanded = build_query_plan(query, {"variants": [
        {"text": f"extra variant {index}", "origin": "expansion"}
        for index in range(6)
    ]})
    assert len(expanded.variants) == 7
    assert expanded.retrieval_mode == "full"


def test_sample_questions_split_overview_from_detailed():
    for query in OVERVIEW_SAMPLES:
        assert detect_retrieval_mode(query) == "overview", query
    for query in DETAILED_SAMPLES[:4]:
        assert detect_retrieval_mode(query) == "full", query
    assert detect_retrieval_mode(DETAILED_SAMPLES[4]) == "focused"


def test_summary_first_caps_overview_variants_and_leaves_procedure_full():
    vague = identity_query_plan("Tóm tắt các tài liệu đã nạp")
    expanded = build_query_plan(vague.original_query, {"variants": [
        {"text": f"extra variant {index}", "origin": "expansion"}
        for index in range(6)
    ]})
    routed = apply_summary_first_to_plan(expanded, overview_max=3, focused_max=3, full_max=8)
    assert routed.retrieval_mode == "overview"
    assert len(routed.variants) == 3

    procedure = apply_summary_first_to_plan(identity_query_plan("Làm thế nào để reset máy X200?"))
    assert procedure.retrieval_mode == "full"
    assert procedure.intent_category == "procedure"


def test_summary_search_ignores_body_chunks(tmp_path):
    body = DocumentChunk(
        chunk_id="body-1",
        document_id="doc-a",
        source_path="a.txt",
        source_name="a.txt",
        file_type="txt",
        text="Body only: valve schedule for line seven.",
        normalized_text="body only: valve schedule for line seven.",
        element_ids=("e1",),
        element_types=("text",),
        metadata={},
    )
    summary = DocumentChunk(
        chunk_id="doc-a-summary",
        document_id="doc-a",
        source_path="a.txt",
        source_name="a.txt",
        file_type="document_summary",
        text="[DOCUMENT ARCHITECTURE & SUMMARY]\nPump station moves water between tanks.",
        normalized_text="[document architecture & summary]\npump station moves water between tanks.",
        element_ids=("summary-001",),
        element_types=("text",),
        metadata={"is_document_summary": True},
    )
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([body, summary])
        response = index.search_summaries_with_summary("Tổng quan hệ thống", limit=10)
    assert [item.chunk_id for item in response.results] == ["doc-a-summary"]
    assert response.summary.candidate_backend == "summary_only"


def _summary_chunk(row, text: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"{row['document_id']}-summary",
        document_id=row["document_id"],
        source_path=row["source_path"],
        source_name=row["source_name"],
        file_type="document_summary",
        text=text,
        normalized_text=text.lower(),
        element_ids=("summary-001",),
        element_types=("text",),
        privacy_labels=("local_only",),
        source_fingerprint=row["source_fingerprint"],
        metadata={"is_document_summary": True},
    )


def test_pipeline_overview_answers_from_summaries_only_when_enabled(tmp_path, monkeypatch):
    alpha = tmp_path / "alpha.txt"
    beta = tmp_path / "beta.txt"
    alpha.write_text("Alpha body records valve schedule SKU-123 on line seven.", encoding="utf-8")
    beta.write_text("Beta body records pump controller fault C001 after reset.", encoding="utf-8")
    sources = [SourceSpec(alpha), SourceSpec(beta)]
    config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
    question = "Tổng quan hệ thống"
    with RagV2DevPipeline(config) as pipeline:
        pipeline.ingest(sources)
        rows = pipeline.index._conn.execute(
            "SELECT document_id, source_path, source_name, source_fingerprint FROM chunks"
        ).fetchall()
        pipeline.index.upsert_chunks([
            _summary_chunk(rows[0], "[DOCUMENT ARCHITECTURE & SUMMARY]\nValve schedule for line seven."),
            _summary_chunk(rows[1], "[DOCUMENT ARCHITECTURE & SUMMARY]\nPump controller watches tank level."),
        ])
        monkeypatch.delenv("AIOS_RAG_V2_SUMMARY_FIRST", raising=False)
        off = pipeline.query(question, sources)
        monkeypatch.setenv("AIOS_RAG_V2_SUMMARY_FIRST", "1")
        on = pipeline.query(question, sources)
        detailed = pipeline.query("What is the exact cell range for SKU-123?", sources)

        focused = pipeline.query(
            "How does data flow between the tank system and the pump controller?",
            sources,
        )
    assert focused.query_plan.retrieval_mode == "focused"
    assert focused.effective_path == "lexical"
    assert focused.search_response.results
    assert {item.document_id for item in focused.search_response.results} == {rows[1]["document_id"]}
    assert off.query_plan.retrieval_mode == "full"
    assert off.effective_path == "lexical"
    assert on.query_plan.retrieval_mode == "overview"
    assert on.effective_path == "summary_only"
    assert on.synthesis_result.abstained is False
    assert "trả lời ở mức tổng quan" in on.synthesis_result.answer.casefold()
    assert all(item.file_type == "document_summary" for item in on.search_response.results)
    assert detailed.query_plan.retrieval_mode == "full"
    assert detailed.effective_path == "lexical"
    assert "trả lời ở mức tổng quan" not in detailed.synthesis_result.answer.casefold()
