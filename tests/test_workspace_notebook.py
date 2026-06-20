import pytest
from pathlib import Path
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.workspace_models import Workspace, KnowledgeNotebook, save_workspace, save_notebook, load_workspaces, load_notebooks
from aios_habit.source_ingest import SourceDocument, ingest_source_document, load_sources, save_source
from aios_habit.case_prompt import build_prompt_pack
from aios_habit.case_audit import audit_case_cockpit_state

def test_workspace_notebook_defaults():
    ws = Workspace(workspace_id="WS1", name="My Workspace")
    assert ws.workspace_id == "WS1"
    assert ws.name == "My Workspace"
    assert ws.default_privacy == "local_only"
    
    nb = KnowledgeNotebook(notebook_id="NB1", workspace_id="WS1", name="My Notebook")
    assert nb.notebook_id == "NB1"
    assert nb.workspace_id == "WS1"
    assert nb.privacy_level == "local_only"

def test_save_load_workspace_notebook_source(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.workspace_models.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.workspace_models.WORKSPACES_FILE", tmp_path / "workspaces.jsonl")
    monkeypatch.setattr("aios_habit.workspace_models.NOTEBOOKS_FILE", tmp_path / "notebooks.jsonl")
    
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")

    # Save and load Workspace
    ws = Workspace(workspace_id="WS_TEST", name="Test WS")
    save_workspace(ws)
    workspaces = load_workspaces()
    assert len(workspaces) == 1
    assert workspaces[0].workspace_id == "WS_TEST"
    
    # Save and load Notebook
    nb = KnowledgeNotebook(notebook_id="NB_TEST", workspace_id="WS_TEST", name="Test Notebook")
    save_notebook(nb)
    notebooks = load_notebooks()
    assert len(notebooks) == 1
    assert notebooks[0].notebook_id == "NB_TEST"
    
    # Ingest source document
    src = ingest_source_document(
        notebook_id="NB_TEST",
        original_filename="sample.txt",
        file_bytes=b"Hello workspace, this is a plain text source document.",
        title="Sample Document"
    )
    assert src.source_id.startswith("SRC-")
    assert src.original_filename == "sample.txt"
    assert src.preview_text == "Hello workspace, this is a plain text source document."
    
    sources = load_sources()
    assert len(sources) == 1
    assert sources[0].title == "Sample Document"

def test_source_upload_filename_safety(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")

    # Mock safe_asset_filename to return a traversal path to trigger our Path.is_relative_to containment check
    monkeypatch.setattr("aios_habit.source_ingest.safe_asset_filename", lambda x: "../../traversal.txt")
    with pytest.raises(ValueError, match="Invalid target path: directory traversal attempt detected."):
        ingest_source_document("NB_X", "traversal.txt", b"traversal", "Traversal Title")

def test_notebook_id_traversal_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")

    malicious_notebook_ids = [
        "../../escape_nb",
        "..\\..\\escape_nb",
        "/tmp/escape_nb",
        "C:\\escape_nb",
        "abc/def",
        "abc\\def",
    ]

    for notebook_id in malicious_notebook_ids:
        with pytest.raises(ValueError, match="Invalid notebook_id"):
            ingest_source_document(notebook_id, "x.txt", b"SECRET", "Traversal Title")

    assert not (tmp_path / "escape_nb").exists()
    assert not (tmp_path.parent / "escape_nb").exists()

def test_case_linked_notebooks_backward_compatibility():
    # Old case dict representation lacking workspace_id and linked_notebook_ids
    old_data = {
        "case_id": "CASE_OLD",
        "title": "Old Case Title",
        "status": "open",
        "priority": "normal",
        "privacy_level": "local_only"
    }
    c_old = Case(**old_data)
    assert c_old.workspace_id == "default"
    assert isinstance(c_old.linked_notebook_ids, list)
    assert len(c_old.linked_notebook_ids) == 0

def test_notebook_source_not_treated_as_case_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    
    monkeypatch.setattr("aios_habit.workspace_models.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.workspace_models.WORKSPACES_FILE", tmp_path / "workspaces.jsonl")
    monkeypatch.setattr("aios_habit.workspace_models.NOTEBOOKS_FILE", tmp_path / "notebooks.jsonl")
    
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")

    # Create Case and Evidence
    case = Case(case_id="C_1", title="Case 1", workspace_id="WS_1")
    save_workspace(Workspace(workspace_id="WS_1", name="WS 1"))
    save_notebook(KnowledgeNotebook(notebook_id="NB_1", workspace_id="WS_1", name="NB 1"))
    
    # Ingest Notebook Source
    ingest_source_document(notebook_id="NB_1", original_filename="source.txt", file_bytes=b"This is a notebook source document", title="Notebook Source")
    
    # Ingest Case Evidence
    ev = EvidenceItem(evidence_id="EVD_1", case_id="C_1", source_type="txt", source_path="manual", title="Case Evidence Text", extracted_text="This is case evidence")
    from aios_habit.case_store import save_evidence, load_evidence
    save_evidence(ev)
    
    # Load and verify no cross-contamination
    all_evidence = load_evidence()
    assert len(all_evidence) == 1
    assert all_evidence[0].evidence_id == "EVD_1"
    
    all_sources = load_sources()
    assert len(all_sources) == 1
    assert all_sources[0].original_filename == "source.txt"
    
    # Verify the notebook source is not loaded as case evidence
    evidence_ids = [e.evidence_id for e in all_evidence]
    assert "source.txt" not in evidence_ids

def test_sentinel_privacy_leak_protection(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.workspace_models.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.workspace_models.NOTEBOOKS_FILE", tmp_path / "notebooks.jsonl")
    monkeypatch.setattr("aios_habit.workspace_models.WORKSPACES_FILE", tmp_path / "workspaces.jsonl")
    
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")
    
    # Save workspace and notebook
    save_workspace(Workspace(workspace_id="WS_S", name="Workspace"))
    save_notebook(KnowledgeNotebook(notebook_id="NB_S", workspace_id="WS_S", name="Notebook", privacy_level="local_only"))
    
    # Ingest local_only source containing the sentinel string
    sentinel = "SECRET_NOTEBOOK_SOURCE_LOCAL_ONLY_DO_NOT_LEAK"
    ingest_source_document(
        notebook_id="NB_S",
        original_filename="secret.txt",
        file_bytes=sentinel.encode("utf-8"),
        title="Secret Source",
        privacy_level="local_only"
    )
    
    case = Case(case_id="C_S", title="Case Sentinel Test", workspace_id="WS_S", linked_notebook_ids=["NB_S"])
    
    # Build prompt pack for cloud targets: gemini, gpt, copilot, notebooklm_safe
    for target in ("notebooklm_safe", "gemini", "gpt", "copilot"):
        prompt = build_prompt_pack(case, [], target, include_local_only=False)
        assert sentinel not in prompt, f"Sentinel leaked to target '{target}'!"
        assert "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]" in prompt

    # Verify audit reports a failure if the sentinel is leaked manually
    outputs = {"gemini": f"Some prompt content: {sentinel}"}
    audit_res = audit_case_cockpit_state(case, [], outputs)
    assert audit_res["status"] == "FAIL"
    assert any("rò rỉ" in err for err in audit_res["errors"])
