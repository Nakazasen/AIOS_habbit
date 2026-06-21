import pytest
from aios_habit.source_ingest import SourceDocument, save_source
from aios_habit.notebook_index import SourceChunk
from aios_habit.notebook_import_store import NotebookBridgeImport, save_bridge_import
from aios_habit.case_models import Case
from aios_habit.case_store import save_case
from aios_habit.daily_next_actions import suggest_next_actions
import json

@pytest.fixture(autouse=True)
def setup_mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")
    
    monkeypatch.setattr("aios_habit.notebook_index.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_index.CHUNKS_FILE", tmp_path / "source_chunks.jsonl")
    
    monkeypatch.setattr("aios_habit.notebook_import_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_import_store.IMPORTS_FILE", tmp_path / "notebook_bridge_imports.jsonl")
    
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", tmp_path / "assets")

def test_next_actions_no_sources():
    actions = suggest_next_actions("default", "NB-123")
    assert "Nạp tài liệu nguồn vào Sổ tri thức." in actions

def test_next_actions_sources_no_chunks(tmp_path):
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB-123",
        filename="manual.txt",
        original_filename="manual.txt",
        source_type="txt",
        title="Manual Doc",
        preview_text="Some text here"
    )
    save_source(src)
    
    actions = suggest_next_actions("default", "NB-123")
    assert "Bấm Cập nhật chỉ mục." in actions

def test_next_actions_case_import_suggests_case_draft():
    # 1. Save a source document
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB-123",
        filename="manual.txt",
        original_filename="manual.txt",
        source_type="txt",
        title="Manual Doc",
        preview_text="Some text here"
    )
    save_source(src)
    
    # 2. Add a chunk manually to bypass indexing
    chunk = SourceChunk(
        chunk_id="SRC-1-CH000",
        notebook_id="NB-123",
        source_id="SRC-1",
        chunk_index=0,
        text="Some text here",
        keywords=["text"],
        privacy_level="local_only",
        source_title="Manual Doc",
        original_filename="manual.txt",
        created_at="2026-06-21T13:00:00"
    )
    from aios_habit.notebook_index import CHUNKS_FILE
    with open(CHUNKS_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(chunk.__dict__) + '\n')
        
    # 3. Save case investigation import but no Case draft yet
    imp = NotebookBridgeImport(
        import_id="IMP-1",
        notebook_id="NB-123",
        workspace_id="default",
        import_type="case_investigation_json",
        title="Investigation A",
        raw_text="",
        parsed_json={"symptoms": ["Anomaly"], "hypotheses": [], "evidence_to_check": []},
        mermaid_text=""
    )
    save_bridge_import(imp)
    
    actions = suggest_next_actions("default", "NB-123")
    assert "Tạo Case nháp từ kết quả điều tra đã lưu." in actions
    
    # 4. Now save a case linked to this notebook
    case = Case(
        case_id="CASE-XYZ",
        title="Case draft",
        workspace_id="default",
        linked_notebook_ids=["NB-123"]
    )
    save_case(case)
    
    actions = suggest_next_actions("default", "NB-123")
    assert "Tạo Case nháp từ kết quả điều tra đã lưu." not in actions
