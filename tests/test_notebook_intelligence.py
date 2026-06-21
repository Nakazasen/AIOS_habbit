import pytest
from pathlib import Path
from aios_habit.workspace_models import Workspace, KnowledgeNotebook, save_workspace, save_notebook
from aios_habit.source_ingest import SourceDocument, save_source, ingest_source_document
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_store import save_case, save_evidence

from aios_habit.notebook_index import (
    SourceChunk,
    build_notebook_index,
    load_chunks,
    search_notebook_chunks
)
from aios_habit.notebook_qa import (
    build_notebook_question_prompt,
    build_study_pack_prompt
)
from aios_habit.notebook_graph import (
    build_notebook_mermaid_graph
)

@pytest.fixture(autouse=True)
def setup_mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.workspace_models.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.workspace_models.WORKSPACES_FILE", tmp_path / "workspaces.jsonl")
    monkeypatch.setattr("aios_habit.workspace_models.NOTEBOOKS_FILE", tmp_path / "notebooks.jsonl")
    
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")
    
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", tmp_path / "assets")
    
    monkeypatch.setattr("aios_habit.notebook_index.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_index.CHUNKS_FILE", tmp_path / "source_chunks.jsonl")
    monkeypatch.setattr("aios_habit.notebook_index.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")
    
    monkeypatch.setattr("aios_habit.notebook_qa.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_qa.QUESTIONS_FILE", tmp_path / "notebook_questions.jsonl")

# 1. test_build_notebook_index_from_preview
def test_build_notebook_index_from_preview():
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="test.txt",
        original_filename="test.txt",
        source_type="txt",
        title="Test Source",
        preview_text="This is a test preview text from source. Yes indeed.",
        privacy_level="local_only"
    )
    save_source(src)
    
    chunks = build_notebook_index("NB1")
    assert len(chunks) == 1
    assert chunks[0].source_id == "SRC-1"
    assert chunks[0].text == "This is a test preview text from source. Yes indeed."
    assert chunks[0].privacy_level == "local_only"
    assert "preview" in chunks[0].keywords

# 2. test_search_notebook_chunks_returns_relevant_source
def test_search_notebook_chunks_returns_relevant_source():
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="test.txt",
        original_filename="test.txt",
        source_type="txt",
        title="Shipping Process",
        preview_text="DHCP setting and FRPO initialization checklist.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    hits = search_notebook_chunks("NB1", "shipping", limit=5)
    assert len(hits) == 1
    assert hits[0].chunk.source_title == "Shipping Process"
    assert hits[0].score > 0.0

# 3. test_notebook_qa_cloud_redacts_local_only_chunk
def test_notebook_qa_cloud_redacts_local_only_chunk():
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="secret.txt",
        original_filename="secret.txt",
        source_type="txt",
        title="Secret Info",
        preview_text="This is a secret key 12345.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    prompt = build_notebook_question_prompt("NB1", "What is the key?", "gemini", "cloud_safe")
    assert "12345" not in prompt
    assert "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]" in prompt

# 4. test_notebook_qa_local_includes_local_chunk
def test_notebook_qa_local_includes_local_chunk():
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="secret.txt",
        original_filename="secret.txt",
        source_type="txt",
        title="Secret Info",
        preview_text="This is a secret key 12345.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    prompt = build_notebook_question_prompt("NB1", "What is the key?", "local_ai", "local")
    assert "12345" in prompt
    assert "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]" not in prompt

# 5. test_study_pack_cloud_redacts_local_only
def test_study_pack_cloud_redacts_local_only():
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="secret.txt",
        original_filename="secret.txt",
        source_type="txt",
        title="Secret Info",
        preview_text="This is a secret key 12345.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    prompt = build_study_pack_prompt("NB1", "gemini", "cloud_safe")
    assert "12345" not in prompt
    assert "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]" in prompt

# 6. test_notebook_graph_mermaid_escapes_labels
def test_notebook_graph_mermaid_escapes_labels():
    save_workspace(Workspace(workspace_id="WS1", name='Workspace "Quotes" [Brackets]'))
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="WS1", name="NB1"))
    
    graph = build_notebook_mermaid_graph(workspace_id="WS1")
    assert "Quotes" in graph
    assert "Workspace 'Quotes' (Brackets)" in graph

# 7. test_notebook_graph_links_case_to_notebook
def test_notebook_graph_links_case_to_notebook():
    save_workspace(Workspace(workspace_id="WS1", name="WS 1"))
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="WS1", name="NB 1"))
    
    case = Case(case_id="CASE1", title="Case 1", workspace_id="WS1", linked_notebook_ids=["NB1"])
    save_case(case)
    
    evidence = EvidenceItem(
        evidence_id="EVD1",
        case_id="CASE1",
        source_type="txt",
        source_path="manual",
        title="Ev 1"
    )
    save_evidence(evidence)
    
    graph = build_notebook_mermaid_graph(workspace_id="WS1")
    assert "CASE_CASE1" in graph
    assert "NB_NB1" in graph
    assert "EVD_EVD1" in graph
    # Replacing spaces to be robust to formatting variations
    flat_graph = graph.replace(" ", "")
    assert "CASE_CASE1-->NB_NB1" in flat_graph
