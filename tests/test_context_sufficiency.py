import pytest
from aios_habit.workspace_models import KnowledgeNotebook, save_notebook
from aios_habit.source_ingest import SourceDocument, save_source
from aios_habit.notebook_index import build_notebook_index
from aios_habit.notebook_qa import evaluate_context_sufficiency

@pytest.fixture(autouse=True)
def setup_mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.workspace_models.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.workspace_models.WORKSPACES_FILE", tmp_path / "workspaces.jsonl")
    monkeypatch.setattr("aios_habit.workspace_models.NOTEBOOKS_FILE", tmp_path / "notebooks.jsonl")
    
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")
    
    monkeypatch.setattr("aios_habit.notebook_index.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_index.CHUNKS_FILE", tmp_path / "source_chunks.jsonl")
    monkeypatch.setattr("aios_habit.notebook_index.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")
    
    monkeypatch.setattr("aios_habit.notebook_qa.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_qa.QUESTIONS_FILE", tmp_path / "notebook_questions.jsonl")
    monkeypatch.setattr("aios_habit.notebook_qa.ANSWERS_FILE", tmp_path / "notebook_answers.jsonl")

def mock_llm_env(monkeypatch, provider="local_ai", locality="local"):
    monkeypatch.setenv("AIOS_LLM_PROVIDER", provider)
    monkeypatch.setenv("AIOS_LLM_LOCALITY", locality)

def test_context_sufficiency_no_chunks(monkeypatch):
    mock_llm_env(monkeypatch)
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    
    res = evaluate_context_sufficiency("NB1", "test query", "Hỏi cloud bằng context được phép", "cloud_safe")
    assert res["total_chunks_found"] == 0
    assert res["recommendation"] == "Chưa đủ nguồn. Hãy cập nhật chỉ mục hoặc đổi từ khóa."

def test_context_sufficiency_cloud_redacted_warns(monkeypatch):
    mock_llm_env(monkeypatch, locality="cloud")
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="test.txt",
        original_filename="test.txt",
        source_type="txt",
        title="Secret Doc",
        preview_text="Some private info here to query.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    res = evaluate_context_sufficiency("NB1", "private info", "Hỏi cloud bằng context được phép", "cloud_safe")
    assert res["total_chunks_found"] > 0
    assert res["redacted_chunks_count"] > 0
    assert res["recommendation"] == "Cloud AI có thể không đủ dữ liệu để trả lời chính xác. Nên dùng Local AI hoặc NotebookLM Bridge."

def test_context_sufficiency_local_ready(monkeypatch):
    mock_llm_env(monkeypatch, locality="local")
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="test.txt",
        original_filename="test.txt",
        source_type="txt",
        title="Local Doc",
        preview_text="Some local text to search.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    res = evaluate_context_sufficiency("NB1", "local text", "Hỏi bằng AIOS local context", "local")
    assert res["total_chunks_found"] > 0
    assert res["recommendation"] == "Có thể hỏi trong AIOS bằng dữ liệu local."

def test_context_sufficiency_notebooklm_bridge_message(monkeypatch):
    mock_llm_env(monkeypatch)
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="test.txt",
        original_filename="test.txt",
        source_type="txt",
        title="Local Doc",
        preview_text="Some local text to search.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    res = evaluate_context_sufficiency("NB1", "local text", "NotebookLM Bridge", "cloud_safe")
    assert res["total_chunks_found"] > 0
    assert res["recommendation"] == "AIOS không gửi source. Hãy bảo đảm NotebookLM đã chứa tài liệu."
