import pytest
import sqlite3
import json
from aios_habit.rag_evidence import (
    RAGEvidenceItem, RAGEvidencePack, EvidencePackConfig,
    build_evidence_pack, stable_pack_id, stable_evidence_id,
    make_snippet, format_evidence_pack_for_prompt, evidence_pack_to_dict
)
from aios_habit.rag_search import RAGSearchResult, create_rag_search_schema, index_rag_chunks, search_rag_chunks
from aios_habit.rag_ingest import RAGChunk

def _create_mock_results(count: int, privacy="cloud_safe"):
    results = []
    for i in range(count):
        results.append(RAGSearchResult(
            chunk_id=f"c{i}",
            document_id=f"d{i%2}",
            text=f"Test content {i} with lots of interesting facts.",
            score=10.0 - i,
            rank=i+1,
            citation_label=f"doc{i}.txt",
            source_title=f"Doc {i}",
            relative_path=f"folder/doc{i}.txt",
            file_type=".txt",
            privacy_mode=privacy,
            page_numbers=[i],
            sheet_names=[],
            slide_numbers=[],
            element_types=["text"],
            metadata={}
        ))
    return results

def test_basic_pack():
    results = _create_mock_results(3)
    pack = build_evidence_pack("test query", results)
    
    assert pack.pack_id is not None
    assert pack.query == "test query"
    assert len(pack.items) == 3
    assert pack.items[0].citation_id == "[1]"
    assert pack.items[1].citation_id == "[2]"
    assert pack.source_count == 3
    assert pack.document_count == 2
    assert pack.privacy_mode == "cloud_safe"
    assert pack.allowed_external is True
    assert pack.insufficient_evidence is False
    assert pack.confidence_label in ["high", "medium"]

def test_privacy_normalization():
    res_cloud = _create_mock_results(2, "cloud_safe")
    res_local = _create_mock_results(1, "local_only")
    results = res_cloud + res_local
    
    pack = build_evidence_pack("mixed", results)
    assert pack.privacy_mode == "local_only"
    assert pack.allowed_external is False
    assert pack.route_hint == "local_only"

def test_insufficient_evidence():
    config = EvidencePackConfig(min_items_for_sufficient=2, min_top_score=5.0)
    
    # Too few items
    res1 = _create_mock_results(1)
    pack1 = build_evidence_pack("q", res1, config)
    assert pack1.insufficient_evidence is True
    assert "Found only 1 items" in pack1.missing_evidence_warnings[0]
    
    # Empty
    pack2 = build_evidence_pack("q", [], config)
    assert pack2.insufficient_evidence is True
    
    # Low score
    res3 = _create_mock_results(2)
    for r in res3:
        r.score = 1.0
    pack3 = build_evidence_pack("q", res3, config)
    assert pack3.insufficient_evidence is True
    assert "Top score" in pack3.missing_evidence_warnings[0]

def test_snippet_and_path_safety():
    res = _create_mock_results(1)
    res[0].text = "A" * 2000
    res[0].relative_path = "C:/secrets/passwords.txt"
    res[0].citation_label = "passwords.txt"
    
    config = EvidencePackConfig(max_snippet_chars=100)
    pack = build_evidence_pack("q", res, config)
    
    assert len(pack.items[0].snippet) == 103 # 100 + "..."
    
    prompt = format_evidence_pack_for_prompt(pack)
    assert "C:/secrets" not in prompt
    assert "passwords.txt" in prompt

def test_json_serialization():
    res = _create_mock_results(2)
    pack = build_evidence_pack("q", res)
    d = evidence_pack_to_dict(pack)
    
    assert d["query"] == "q"
    assert len(d["items"]) == 2
    assert d["privacy_mode"] == "cloud_safe"
    assert json.dumps(d)

def test_search_integration():
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    
    chunks = [
        RAGChunk(
            chunk_id="c1", document_id="d1", element_ids=[], text="Alpha wolf",
            source_title="T1", source_path="p1", relative_path="p1", citation_label="p1",
            file_type=".txt", element_types=[], page_numbers=[], sheet_names=[], slide_numbers=[],
            section_labels=[], row_ranges=[], cell_ranges=[], privacy_mode="cloud_safe"
        ),
        RAGChunk(
            chunk_id="c2", document_id="d2", element_ids=[], text="Beta wolf",
            source_title="T2", source_path="p2", relative_path="p2", citation_label="p2",
            file_type=".txt", element_types=[], page_numbers=[], sheet_names=[], slide_numbers=[],
            section_labels=[], row_ranges=[], cell_ranges=[], privacy_mode="local_only"
        )
    ]
    index_rag_chunks(conn, chunks)
    
    results = search_rag_chunks(conn, "wolf")
    pack = build_evidence_pack("wolf", results)
    
    assert len(pack.items) == 2
    assert pack.privacy_mode == "local_only"
    assert pack.allowed_external is False
