from aios_habit.ai_router import *
from aios_habit.safety_modes import SAFETY_MODE_AUTO, SAFETY_MODE_COMPANY, SAFETY_MODE_NORMAL


def req(mode=SAFETY_MODE_NORMAL):
    return RouterRequest("hỏi", "ctx", "fallback", [{"source_file":"a.md"}], mode, "Sổ", max_attempts=3)


def cfg(pid, name=None, priority=10, enabled=True, trusted=False):
    return RouterProviderConfig(pid, name or pid, "http://example.test/v1", "model", "", enabled, trusted, priority, 5)


def test_normal_docs_uses_first_configured_provider():
    result = route_answer(req(), [cfg("gemini", "Gemini")], {}, lambda c, r: "answer from gemini")
    assert result.answer_text == "answer from gemini"
    assert result.used_provider == "Gemini"
    assert not result.used_fallback


def test_normal_docs_fallback_to_second_provider_if_first_fails():
    calls=[]
    def client(c, r):
        calls.append(c.provider_id)
        if c.provider_id == "gemini": raise RuntimeError("429 quota")
        return "answer from groq"
    health={}
    result = route_answer(req(), [cfg("gemini", "Gemini", 1), cfg("groq", "Groq", 2)], health, client)
    assert result.answer_text == "answer from groq"
    assert calls == ["gemini", "groq"]
    assert health["gemini"].status == "cooldown"


def test_normal_docs_fallback_deterministic_if_all_fail():
    result = route_answer(req(), [cfg("gemini", "Gemini")], {}, lambda c, r: (_ for _ in ()).throw(RuntimeError("500 server error")))
    assert result.answer_text == "fallback"
    assert result.used_fallback
    assert "dữ liệu cục bộ" in result.route_summary_vi


def test_company_secret_blocks_cloud_provider_and_falls_back():
    result = route_answer(req(SAFETY_MODE_COMPANY), [cfg("gemini", "Gemini")], {}, lambda c, r: "should not call")
    assert result.answer_text == "fallback"
    assert result.attempts[0].status == "blocked"
    assert "Không gửi ra ngoài" in result.route_summary_vi


def test_company_secret_can_use_local_internal_provider():
    result = route_answer(req(SAFETY_MODE_COMPANY), [cfg("ollama", "Ollama", trusted=True)], {}, lambda c, r: "local answer")
    assert result.answer_text == "local answer"
    assert result.used_provider == "Ollama"


def test_unknown_auto_does_not_silently_cloud_route():
    result = route_answer(req(SAFETY_MODE_AUTO), [cfg("gemini", "Gemini")], {}, lambda c, r: "cloud")
    assert result.answer_text == "fallback"
    assert result.used_fallback
    assert result.attempts[0].status == "blocked"


def test_rate_limit_triggers_cooldown():
    health={}
    route_answer(req(), [cfg("gemini", "Gemini")], health, lambda c, r: (_ for _ in ()).throw(RuntimeError("429 rate limit")))
    assert health["gemini"].status == "cooldown"
    assert health["gemini"].cooldown_until > 0


def test_auth_error_disables_for_current_run():
    health={}
    route_answer(req(), [cfg("gemini", "Gemini")], health, lambda c, r: (_ for _ in ()).throw(RuntimeError("401 invalid api key")))
    assert health["gemini"].status == "disabled"
    assert health["gemini"].last_error_type == "auth_error"


def test_timeout_and_bad_answer_handling():
    assert classify_provider_error("request timed out") == "timeout"
    assert classify_provider_error("empty answer") == "bad_response"
    result = route_answer(req(), [cfg("gemini", "Gemini")], {}, lambda c, r: "")
    assert result.used_fallback
    assert result.attempts[-1].error_type == "bad_response"


def test_route_summary_vietnamese_and_no_raw_labels():
    result = route_answer(req(), [cfg("groq", "Groq")], {}, lambda c, r: "ok")
    summary = result.route_summary_vi
    assert "Nhật ký AI đã dùng" in summary
    assert "Có gửi ra ngoài không" in summary
    assert "Tự đổi nguồn" in summary
    assert "cloud_allowed" not in summary
    assert "local_only" not in summary
    assert "provider policy" not in summary.lower()
    assert "route policy" not in summary.lower()


def test_provider_configs_from_env_uses_openai_compatible_without_printing_secret(capsys):
    env = {
        "GROQ_API_KEY": "fake-secret-value",
        "AIOS_GROQ_MODEL": "llama-test",
        "AIOS_PROVIDER_TIMEOUT_SECONDS": "bad",
    }
    configs = provider_configs_from_env(env)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert len(configs) == 1
    assert configs[0].provider_id == "groq"
    assert configs[0].api_key == "fake-secret-value"
    assert configs[0].endpoint_url.endswith("/chat/completions")
    assert configs[0].model_name == "llama-test"
    assert configs[0].timeout_seconds == 30


def test_provider_env_presence_does_not_return_secret_values():
    presence = provider_env_presence({
        "OPENROUTER_API_KEY": "fake-secret-value",
        "AIOS_PROVIDER_CUSTOM": "also-secret",
    })
    assert presence["OPENROUTER_API_KEY"] is True
    assert presence["AIOS_PROVIDER_CUSTOM"] is True
    assert "fake-secret-value" not in str(presence)
    assert "also-secret" not in str(presence)


def test_missing_key_env_loader_returns_no_cloud_config():
    assert provider_configs_from_env({}) == []


def test_company_secret_blocks_env_cloud_config_even_with_key():
    configs = provider_configs_from_env({"OPENROUTER_API_KEY": "fake-secret-value"})
    called = []
    result = route_answer(req(SAFETY_MODE_COMPANY), configs, {}, lambda c, r: called.append(c.provider_id) or "bad")
    assert called == []
    assert result.used_fallback
    assert all(a.status == "blocked" for a in result.attempts)


def test_normal_docs_env_config_can_use_mock_provider():
    configs = provider_configs_from_env({"DEEPSEEK_API_KEY": "fake-secret-value"})
    result = route_answer(req(SAFETY_MODE_NORMAL), configs, {}, lambda c, r: "real-compatible mock answer")
    assert result.answer_text == "real-compatible mock answer"
    assert result.used_provider == "DeepSeek"
    assert not result.used_fallback
    assert "fake-secret-value" not in result.route_summary_vi


def test_route_log_does_not_include_secret_like_provider_errors():
    configs = provider_configs_from_env({"OPENROUTER_API_KEY": "fake-secret-value"})
    result = route_answer(
        req(SAFETY_MODE_NORMAL),
        configs,
        {},
        lambda c, r: (_ for _ in ()).throw(RuntimeError("401 invalid api key fake-secret-value")),
    )
    assert result.used_fallback
    assert "fake-secret-value" not in result.route_summary_vi
