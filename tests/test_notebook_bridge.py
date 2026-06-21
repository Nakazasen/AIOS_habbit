import pytest
import json
from aios_habit.notebook_bridge import build_notebooklm_bridge_prompt, graph_json_to_mermaid

@pytest.fixture(autouse=True)
def setup_mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.workspace_models.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.workspace_models.WORKSPACES_FILE", tmp_path / "workspaces.jsonl")
    monkeypatch.setattr("aios_habit.workspace_models.NOTEBOOKS_FILE", tmp_path / "notebooks.jsonl")

def test_build_notebooklm_graph_prompt_contains_schema():
    prompt = build_notebooklm_bridge_prompt("NB1", "knowledge_graph_json")
    assert "stable_id" in prompt
    assert "depends_on" in prompt
    assert "source_ref" in prompt

def test_build_notebooklm_study_prompt_contains_schema():
    prompt = build_notebooklm_bridge_prompt("NB1", "study_pack_json")
    assert "summary" in prompt
    assert "glossary" in prompt
    assert "flashcards" in prompt
    assert "review_questions" in prompt

def test_parse_valid_graph_json_to_mermaid():
    data = {
        "nodes": [
            {"id": "N1", "label": "Concept A", "type": "system"},
            {"id": "N2", "label": "Concept B", "type": "process"}
        ],
        "edges": [
            {"from": "N1", "to": "N2", "relation": "depends_on"}
        ]
    }
    mermaid = graph_json_to_mermaid(data)
    assert "graph TD" in mermaid
    assert 'N1["Concept A"]' in mermaid
    assert 'N2["Concept B"]' in mermaid
    assert 'N1 -->|"depends_on"| N2' in mermaid.replace(" ", "") or "N1 -->|\"depends_on\"| N2" in mermaid

def test_parse_invalid_json_returns_error_or_raises_controlled():
    # Calling with None or invalid dict
    mermaid1 = graph_json_to_mermaid(None)
    assert "Dữ liệu đồ thị không hợp lệ" in mermaid1
    
    mermaid2 = graph_json_to_mermaid([])
    assert "Dữ liệu đồ thị không hợp lệ" in mermaid2

def test_graph_json_to_mermaid_escapes_labels():
    data = {
        "nodes": [
            {"id": "N1", "label": 'Concept "A" [Brackets]'}
        ],
        "edges": []
    }
    mermaid = graph_json_to_mermaid(data)
    assert "Concept 'A' (Brackets)" in mermaid

def test_graph_json_to_mermaid_skips_invalid_edges():
    data = {
        "nodes": [
            {"id": "N1", "label": "Concept A"}
        ],
        "edges": [
            # N2 is not in nodes, so this edge should be skipped
            {"from": "N1", "to": "N2", "relation": "depends_on"}
        ]
    }
    mermaid = graph_json_to_mermaid(data)
    assert "N1 -->" not in mermaid
    assert "N2" not in mermaid
