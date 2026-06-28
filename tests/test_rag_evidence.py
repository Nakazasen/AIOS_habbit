import pytest
import sqlite3
import json
from aios_habit.rag_evidence import (
    EvidencePackConfig,
    build_evidence_pack, stable_evidence_id,
    format_evidence_pack_for_prompt, evidence_pack_to_dict
)
from aios_habit.rag_search import RAGSearchResult, create_rag_search_schema, index_rag_chunks, search_rag_chunks
from aios_habit.rag_ingest import RAGChunk
from aios_habit.notebook_index import SourceChunk, search_notebook_chunks

def _create_mock_results(count: int, privacy="cloud_safe"):
    results = []
    for i in range(count):
        results.append(RAGSearchResult(
            chunk_id=f"c{i}", document_id=f"d{i%2}", text=f"Test content {i} with lots of interesting facts.",
            score=10.0 - i, rank=i+1, citation_label=f"doc{i}.txt", source_title=f"Doc {i}",
            relative_path=f"folder/doc{i}.txt", file_type=".txt", privacy_mode=privacy,
            page_numbers=[i], sheet_names=[], slide_numbers=[], element_types=["text"], metadata={}
        ))
    return results

def test_basic_pack():
    pack = build_evidence_pack("test query", _create_mock_results(3))
    assert pack.pack_id.startswith("PACK-")
    assert len(pack.items) == 3
    assert pack.items[0].citation_id == "[1]"
    assert pack.source_count == 3
    assert pack.document_count == 2
    assert pack.privacy_mode == "cloud_safe"
    assert pack.allowed_external is True
    assert pack.insufficient_evidence is False

def test_stable_ids_and_order_sensitivity():
    results = _create_mock_results(3)
    pack1 = build_evidence_pack("test query", results)
    pack2 = build_evidence_pack("test query", results)
    pack3 = build_evidence_pack("test query", [results[1], results[0], results[2]])
    pack4 = build_evidence_pack("different query", results)
    assert pack1.pack_id == pack2.pack_id
    assert [i.evidence_id for i in pack1.items] == [i.evidence_id for i in pack2.items]
    assert pack1.pack_id != pack3.pack_id
    assert pack1.pack_id != pack4.pack_id
    assert stable_evidence_id(pack1.pack_id, results[0].chunk_id, 1) == pack1.items[0].evidence_id

def test_privacy_normalization_and_external_guard():
    mixed = build_evidence_pack("mixed", _create_mock_results(2, "cloud_safe") + _create_mock_results(1, "local_only"))
    assert mixed.privacy_mode == "local_only"
    assert mixed.allowed_external is False
    assert mixed.route_hint == "local_only"
    allowed = build_evidence_pack("q", _create_mock_results(2, "cloud_safe"), EvidencePackConfig(allow_external_for_cloud_safe=True))
    blocked = build_evidence_pack("q", _create_mock_results(2, "cloud_safe"), EvidencePackConfig(allow_external_for_cloud_safe=False))
    assert allowed.allowed_external is True
    assert allowed.route_hint == "cloud_safe_allowed"
    assert blocked.allowed_external is False
    assert blocked.route_hint == "redacted_export_required"

def test_insufficient_evidence_and_coverage_threshold():
    config = EvidencePackConfig(min_items_for_sufficient=2, min_top_score=5.0)
    assert "Found only 1 items" in build_evidence_pack("q", _create_mock_results(1), config).missing_evidence_warnings[0]
    empty = build_evidence_pack("q", [], config)
    assert empty.insufficient_evidence is True
    assert empty.privacy_mode == "local_only"
    low = _create_mock_results(2)
    for r in low:
        r.score = 1.0
    assert "Top score" in build_evidence_pack("q", low, config).missing_evidence_warnings[0]
    low_coverage = build_evidence_pack("q", _create_mock_results(1), EvidencePackConfig(min_coverage_score=1.1))
    assert low_coverage.insufficient_evidence is True
    assert "Coverage score" in low_coverage.missing_evidence_warnings[0]
    assert low_coverage.confidence_label == "insufficient"

def test_snippet_prompt_and_path_safety():
    res = _create_mock_results(1, privacy="local_only")
    res[0].text = "A" * 2000
    res[0].relative_path = "D:/Sandbox/AIOS_habbit/secret/passwords.txt"
    res[0].citation_label = "D:/Sandbox/AIOS_habbit/secret/passwords.txt"
    pack = build_evidence_pack("q", res, EvidencePackConfig(max_snippet_chars=100))
    assert len(pack.items[0].snippet) == 103
    assert pack.items[0].citation_label == "passwords.txt"
    prompt = format_evidence_pack_for_prompt(pack)
    assert "D:/" not in prompt
    assert "Sandbox" not in prompt
    assert "passwords.txt" in prompt
    assert "External export NOT allowed" in prompt
    assert "local_only" in prompt

def test_json_serialization_and_prompt_sections():
    pack = build_evidence_pack("what happened", _create_mock_results(2))
    assert json.dumps(evidence_pack_to_dict(pack))
    prompt = format_evidence_pack_for_prompt(pack)
    assert "what happened" in prompt
    assert "Citation ID: [1]" in prompt
    assert "Snippet:" in prompt
    assert "PRIVACY NOTICE" in prompt
    assert "Confidence:" in prompt

def test_search_integration():
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    chunks = [
        RAGChunk(chunk_id="c1", document_id="d1", element_ids=[], text="Alpha wolf", source_title="T1", source_path="p1", relative_path="p1", citation_label="p1", file_type=".txt", element_types=[], page_numbers=[], sheet_names=[], slide_numbers=[], section_labels=[], row_ranges=[], cell_ranges=[], privacy_mode="cloud_safe"),
        RAGChunk(chunk_id="c2", document_id="d2", element_ids=[], text="Beta wolf", source_title="T2", source_path="p2", relative_path="p2", citation_label="p2", file_type=".txt", element_types=[], page_numbers=[], sheet_names=[], slide_numbers=[], section_labels=[], row_ranges=[], cell_ranges=[], privacy_mode="local_only"),
    ]
    index_rag_chunks(conn, chunks)
    pack = build_evidence_pack("wolf", search_rag_chunks(conn, "wolf"))
    assert len(pack.items) == 2
    assert pack.privacy_mode == "local_only"
    assert pack.allowed_external is False

def test_old_search_notebook_chunks_compatibility(monkeypatch):
    chunk = SourceChunk(chunk_id="old-1", notebook_id="nb", source_id="src", source_title="Legacy Guide", original_filename="legacy.txt", text="legacy notebook search still works", chunk_index=0, privacy_level="local_only", keywords=[], created_at="2026-01-01T00:00:00")
    import aios_habit.notebook_index as notebook_index; monkeypatch.setattr(notebook_index, "load_chunks", lambda notebook_id: [chunk]); hits = search_notebook_chunks("nb", "legacy")
    assert len(hits) == 1
    assert hits[0].chunk.chunk_id == "old-1"

def test_metadata_only_evidence():
    import sqlite3
    chunks = [
        RAGChunk("C1", "D1", ["e1"], "metadata-only source record\nFile Path: doc.pdf\nSize: 100", "Metadata", "doc.pdf", "doc.pdf", "doc.pdf", "pdf", ["metadata"], [], [], [], [], [], [], "cloud_safe", metadata={"_is_metadata_only": "True"}),
    ]
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    index_rag_chunks(conn, chunks)
    results = search_rag_chunks(conn, "doc", limit=5)
    
    # Force high scores
    for r in results:
        r.score = 10.0
        
    pack = build_evidence_pack("doc", results)
    
    assert pack.insufficient_evidence is True
    assert pack.confidence_label == "low"
    assert pack.metadata_only_evidence_count == 1
    assert pack.content_evidence_count == 0
    assert pack.evidence_quality == "metadata_only"
