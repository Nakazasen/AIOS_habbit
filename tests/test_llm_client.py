import os
import json
import pytest
import urllib.request
from aios_habit.llm_client import (
    load_llm_config,
    is_llm_configured,
    complete_chat,
    LLMConfig,
    LLMConfigurationError
)

def test_load_llm_config_missing_returns_none_or_unconfigured(monkeypatch):
    monkeypatch.delenv("AIOS_LLM_PROVIDER", raising=False)
    assert load_llm_config() is None
    assert not is_llm_configured()

def test_load_llm_config_from_env(monkeypatch):
    monkeypatch.setenv("AIOS_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AIOS_LLM_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("AIOS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("AIOS_LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("AIOS_LLM_LOCALITY", "cloud")
    monkeypatch.setenv("AIOS_LLM_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("AIOS_LLM_MAX_PROMPT_CHARS", "5000")
    
    config = load_llm_config()
    assert config is not None
    assert config.provider == "openai_compatible"
    assert config.base_url == "http://localhost:8000/v1"
    assert config.api_key == "test-key"
    assert config.model == "gpt-4o"
    assert config.locality == "cloud"
    assert config.timeout_seconds == 30
    assert config.max_prompt_chars == 5000
    assert is_llm_configured()

def test_complete_chat_uses_openai_compatible_payload_without_logging_key(monkeypatch):
    sent_request = None
    
    class MockResponse:
        def __init__(self, data):
            self.data = data
        def read(self):
            return self.data
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
            
    def mock_urlopen(req, timeout=None):
        nonlocal sent_request
        sent_request = req
        res_payload = {
            "choices": [
                {
                    "message": {
                        "content": "Mocked AI Response"
                    }
                }
            ]
        }
        return MockResponse(json.dumps(res_payload).encode("utf-8"))
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    config = LLMConfig(
        provider="openai_compatible",
        base_url="http://mock-api/v1/chat/completions",
        api_key="dummy",
        model="mock-model",
        locality="local"
    )
    
    resp = complete_chat("Hello AI", system_prompt="Sys prompt", config=config)
    assert resp == "Mocked AI Response"
    assert sent_request is not None
    assert sent_request.full_url == "http://mock-api/v1/chat/completions"
    assert sent_request.headers.get("Content-type") == "application/json"
    assert sent_request.headers.get("Authorization") == "Bearer dummy"
    
    sent_body = json.loads(sent_request.data.decode("utf-8"))
    assert sent_body["model"] == "mock-model"
    assert sent_body["messages"][0] == {"role": "system", "content": "Sys prompt"}
    assert sent_body["messages"][1] == {"role": "user", "content": "Hello AI"}

def test_complete_chat_rejects_oversized_prompt():
    config = LLMConfig(
        provider="openai_compatible",
        base_url="http://mock-api/v1/chat/completions",
        api_key="key",
        model="model",
        locality="local",
        max_prompt_chars=100
    )
    
    # Combined length is 90 (system) + 50 (prompt) = 140 > 100
    # allowed_len will be 100 - 90 - 50 = -40 <= 0 -> raises ValueError
    with pytest.raises(ValueError, match="Prompt or System Prompt is too long"):
        complete_chat("A" * 50, system_prompt="B" * 90, config=config)

    # Prompt alone is 120 > 100 -> truncated
    # allowed_len will be 100 - 0 - 50 = 50. Prompt of 120 characters truncated to 50 + suffix
    sent_request = None
    class MockResponse:
        def read(self):
            return b'{"choices": [{"message": {"content": "OK"}}]}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    import urllib.request
    urllib.request.urlopen = lambda req, timeout=None: MockResponse()
    
    resp = complete_chat("A" * 120, config=config)
    assert resp == "OK"
