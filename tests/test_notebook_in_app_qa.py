import pytest
import json
import urllib.request
from pathlib import Path
from aios_habit.workspace_models import Workspace, KnowledgeNotebook, save_notebook
from aios_habit.source_ingest import SourceDocument, save_source
from aios_habit.notebook_index import build_notebook_index
from aios_habit.notebook_qa import answer_notebook_question, NotebookAnswerResult

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

# Helper to configure LLM
def mock_llm_env(monkeypatch, provider="openai_compatible", url="http://localhost:11434/v1", key="test", model="model", locality="local"):
    monkeypatch.setenv("AIOS_LLM_PROVIDER", provider)
    monkeypatch.setenv("AIOS_LLM_BASE_URL", url)
    monkeypatch.setenv("AIOS_LLM_API_KEY", key)
    monkeypatch.setenv("AIOS_LLM_MODEL", model)
    monkeypatch.setenv("AIOS_LLM_LOCALITY", locality)

def test_in_app_qa_blocks_cloud_local_export(monkeypatch):
    mock_llm_env(monkeypatch, locality="cloud")
    
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="secret.txt",
        original_filename="secret.txt",
        source_type="txt",
        title="Secret Info",
        preview_text="Secret key 12345.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    # target=gemini, export_mode=local
    res = answer_notebook_question("NB1", "What is the key?", "gemini", "local")
    assert res.blocked
    assert "Không thể gửi dữ liệu local_only" in res.block_reason
    assert "12345" not in res.answer_text

def test_in_app_qa_cloud_uses_redacted_prompt(monkeypatch):
    mock_llm_env(monkeypatch, locality="cloud")
    
    sent_prompt = None
    
    class MockResponse:
        def read(self):
            return b'{"choices": [{"message": {"content": "Mock Answer"}}]}'
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    def mock_urlopen(req, timeout=None):
        nonlocal sent_prompt
        body = json.loads(req.data.decode("utf-8"))
        sent_prompt = body["messages"][1]["content"]
        return MockResponse()
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="secret.txt",
        original_filename="secret.txt",
        source_type="txt",
        title="Secret Info",
        preview_text="Secret key 12345.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    # Cloud provider with cloud_safe mode
    res = answer_notebook_question("NB1", "What is the key?", "gemini", "cloud_safe")
    assert not res.blocked
    assert res.answer_text == "Mock Answer"
    assert "12345" not in sent_prompt
    assert "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]" in sent_prompt

def test_in_app_qa_local_can_include_local_only(monkeypatch):
    mock_llm_env(monkeypatch, locality="local")
    
    sent_prompt = None
    
    class MockResponse:
        def read(self):
            return b'{"choices": [{"message": {"content": "Mock Answer"}}]}'
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    def mock_urlopen(req, timeout=None):
        nonlocal sent_prompt
        body = json.loads(req.data.decode("utf-8"))
        sent_prompt = body["messages"][1]["content"]
        return MockResponse()
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    save_notebook(KnowledgeNotebook(notebook_id="NB1", workspace_id="default", name="NB 1"))
    src = SourceDocument(
        source_id="SRC-1",
        notebook_id="NB1",
        filename="secret.txt",
        original_filename="secret.txt",
        source_type="txt",
        title="Secret Info",
        preview_text="Secret key 12345.",
        privacy_level="local_only"
    )
    save_source(src)
    build_notebook_index("NB1")
    
    # Local provider with local mode -> raw content included
    res = answer_notebook_question("NB1", "What is the key?", "local_ai", "local")
    assert not res.blocked
    assert "12345" in sent_prompt
    assert "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]" not in sent_prompt

def test_in_app_qa_missing_config_returns_clear_block_or_error(monkeypatch):
    monkeypatch.delenv("AIOS_LLM_PROVIDER", raising=False)
    
    res = answer_notebook_question("NB1", "test?", "gemini", "local")
    assert res.blocked
    assert "AI provider chưa được cấu hình" in res.block_reason

def test_in_app_qa_does_not_call_provider_when_question_empty(monkeypatch):
    mock_llm_env(monkeypatch)
    
    called = False
    def mock_urlopen(req, timeout=None):
        nonlocal called
        called = True
        raise RuntimeError("Should not be called")
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    res = answer_notebook_question("NB1", "  ", "gemini", "local")
    assert res.blocked
    assert "Câu hỏi đang trống" in res.block_reason
    assert not called
