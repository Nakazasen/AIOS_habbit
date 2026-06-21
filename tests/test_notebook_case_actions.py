import pytest
from aios_habit.case_models import Case
from aios_habit.case_store import load_cases, load_evidence
from aios_habit.notebook_case_actions import create_case_from_investigation_import
from aios_habit.notebook_import_store import NotebookBridgeImport

@pytest.fixture(autouse=True)
def setup_mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", tmp_path / "assets")

def test_create_case_from_investigation_import_creates_local_only_case():
    import_rec = NotebookBridgeImport(
        import_id="IMP-1",
        notebook_id="NB-123",
        workspace_id="WS-1",
        import_type="case_investigation_json",
        title="Test Investigation Title",
        raw_text="",
        parsed_json={
            "symptoms": ["Symptom A", "Symptom B"],
            "hypotheses": ["Hypothesis X"],
            "evidence_to_check": ["Check connection", "Check log file"]
        },
        mermaid_text=""
    )
    
    res = create_case_from_investigation_import(import_rec, workspace_id="WS-1")
    assert res["case_id"] is not None
    assert res["evidence_count"] == 2
    
    cases = load_cases()
    assert len(cases) == 1
    case = cases[0]
    assert case.case_id == res["case_id"]
    assert case.title == "Test Investigation Title"
    assert case.privacy_level == "local_only"
    assert "Symptom A" in case.current_situation
    assert "Hypothesis X" in case.current_situation
    assert "Check connection" in case.current_situation
    assert case.source_origin == "notebooklm_import"
    assert case.verification_status == "draft"
    
    evs = load_evidence()
    assert len(evs) == 2
    assert evs[0].case_id == case.case_id
    assert evs[0].source_type == "note"
    assert evs[0].privacy_level == "local_only"
    assert evs[0].source_origin == "notebooklm_import"
    assert evs[0].verification_status == "draft"
    assert evs[0].review_status == "raw"
    assert evs[0].extracted_text == "Check connection"
    assert evs[1].extracted_text == "Check log file"

def test_create_case_from_investigation_import_links_notebook():
    import_rec = NotebookBridgeImport(
        import_id="IMP-2",
        notebook_id="NB-ABC",
        workspace_id="WS-1",
        import_type="case_investigation_json",
        title="Linked Notebook Case",
        raw_text="",
        parsed_json={
            "symptoms": ["Anomaly detected"],
            "hypotheses": [],
            "evidence_to_check": []
        },
        mermaid_text=""
    )
    
    res = create_case_from_investigation_import(import_rec, workspace_id="WS-1")
    cases = load_cases()
    assert len(cases) == 1
    assert "NB-ABC" in cases[0].linked_notebook_ids

def test_create_case_from_investigation_import_handles_missing_fields():
    import_rec = NotebookBridgeImport(
        import_id="IMP-3",
        notebook_id="",
        workspace_id="WS-1",
        import_type="case_investigation_json",
        title="Minimal Case",
        raw_text="",
        parsed_json={},
        mermaid_text=""
    )
    
    res = create_case_from_investigation_import(import_rec, workspace_id="WS-1")
    assert res["evidence_count"] == 0
    
    cases = load_cases()
    assert len(cases) == 1
    assert cases[0].current_situation == ""
    assert cases[0].linked_notebook_ids == []
