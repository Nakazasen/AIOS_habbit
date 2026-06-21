import pytest
import json
from pathlib import Path
from aios_habit.notebook_import_store import (
    NotebookBridgeImport,
    load_bridge_imports,
    save_bridge_import,
    get_bridge_import,
    delete_bridge_import
)
from aios_habit.notebook_bridge import (
    detect_bridge_import_type,
    parse_bridge_import,
    summarize_bridge_import,
    graph_json_to_mermaid
)

@pytest.fixture(autouse=True)
def setup_mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.notebook_import_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_import_store.IMPORTS_FILE", tmp_path / "notebook_bridge_imports.jsonl")

# 1. test_save_load_bridge_import
def test_save_load_bridge_import():
    imp = NotebookBridgeImport(
        import_id="IMP-1",
        notebook_id="NB-1",
        workspace_id="WS-1",
        import_type="study_pack_json",
        title="Test Study Pack",
        raw_text='{"summary": "Test Summary"}',
        parsed_json={"summary": "Test Summary"},
        mermaid_text="",
        privacy_level="local_only",
        status="draft"
    )
    save_bridge_import(imp)
    
    loaded = load_bridge_imports()
    assert len(loaded) == 1
    assert loaded[0].import_id == "IMP-1"
    assert loaded[0].title == "Test Study Pack"
    assert loaded[0].parsed_json["summary"] == "Test Summary"

# 2. test_bridge_import_defaults_local_only_draft
def test_bridge_import_defaults_local_only_draft():
    imp = NotebookBridgeImport(
        import_id="IMP-1",
        notebook_id="NB-1",
        workspace_id="WS-1",
        import_type="mermaid_graph",
        title="Mermaid Graph",
        raw_text="graph TD\n    A --> B",
        parsed_json={},
        mermaid_text="graph TD\n    A --> B"
    )
    save_bridge_import(imp)
    
    loaded = get_bridge_import("IMP-1")
    assert loaded is not None
    assert loaded.privacy_level == "local_only"
    assert loaded.status == "draft"
    assert loaded.source == "notebooklm_bridge"

# 3. test_load_bridge_imports_filters_by_notebook
def test_load_bridge_imports_filters_by_notebook():
    imp1 = NotebookBridgeImport(
        import_id="IMP-1",
        notebook_id="NB-1",
        workspace_id="WS-1",
        import_type="mermaid_graph",
        title="NB1 Graph",
        raw_text="",
        parsed_json={},
        mermaid_text=""
    )
    imp2 = NotebookBridgeImport(
        import_id="IMP-2",
        notebook_id="NB-2",
        workspace_id="WS-1",
        import_type="mermaid_graph",
        title="NB2 Graph",
        raw_text="",
        parsed_json={},
        mermaid_text=""
    )
    save_bridge_import(imp1)
    save_bridge_import(imp2)
    
    nb1_imports = load_bridge_imports("NB-1")
    assert len(nb1_imports) == 1
    assert nb1_imports[0].import_id == "IMP-1"
    
    nb2_imports = load_bridge_imports("NB-2")
    assert len(nb2_imports) == 1
    assert nb2_imports[0].import_id == "IMP-2"

# 4. test_parse_and_summarize_graph_import
def test_parse_and_summarize_graph_import():
    raw_json = """
    ```json
    {
      "nodes": [
        {"id": "A", "label": "Node A", "type": "system"},
        {"id": "B", "label": "Node B", "type": "process"}
      ],
      "edges": [
        {"from": "A", "to": "B", "relation": "causes"}
      ]
    }
    ```
    """
    import_type = detect_bridge_import_type(raw_json)
    assert import_type == "knowledge_graph_json"
    
    parsed = parse_bridge_import(raw_json)
    assert "nodes" in parsed
    assert len(parsed["nodes"]) == 2
    
    summary = summarize_bridge_import(parsed, import_type)
    assert summary["node_count"] == 2
    assert summary["edge_count"] == 1

# 5. test_parse_and_summarize_study_pack_import
def test_parse_and_summarize_study_pack_import():
    raw_json = """
    {
      "summary": "This is a study summary.",
      "glossary": [
        {"term": "T1", "meaning": "M1", "source_ref": "S1"}
      ],
      "flashcards": [
        {"front": "Q1", "back": "A1", "source_ref": "S1"},
        {"front": "Q2", "back": "A2", "source_ref": "S2"}
      ],
      "review_questions": [],
      "unknowns": ["U1"]
    }
    """
    import_type = detect_bridge_import_type(raw_json)
    assert import_type == "study_pack_json"
    
    parsed = parse_bridge_import(raw_json)
    assert parsed["summary"] == "This is a study summary."
    
    summary = summarize_bridge_import(parsed, import_type)
    assert summary["glossary_count"] == 1
    assert summary["flashcard_count"] == 2
    assert summary["review_question_count"] == 0
    assert summary["unknown_count"] == 1

# 6. test_parse_invalid_json_controlled_error
def test_parse_invalid_json_controlled_error():
    invalid_raw = "{invalid json}"
    import_type = detect_bridge_import_type(invalid_raw)
    assert import_type == "unknown"
    
    parsed = parse_bridge_import(invalid_raw)
    assert parsed == {}
    
    summary = summarize_bridge_import(parsed, import_type)
    assert summary == {}

# 7. test_graph_import_mermaid_roundtrip
def test_graph_import_mermaid_roundtrip():
    data = {
        "nodes": [
            {"id": "A", "label": "Concept A"},
            {"id": "B", "label": "Concept B"}
        ],
        "edges": [
            {"from": "A", "to": "B", "relation": "depends_on"}
        ]
    }
    mermaid = graph_json_to_mermaid(data)
    assert "graph TD" in mermaid
    assert 'A["Concept A"]' in mermaid
    assert 'B["Concept B"]' in mermaid
    assert 'A -->|"depends_on"| B' in mermaid or 'A -->|"depends_on"| B' in mermaid.replace(" ", "")
