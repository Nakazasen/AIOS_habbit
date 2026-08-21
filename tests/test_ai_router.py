import aios_habit.ai_router as router_module
from aios_habit.ai_router import *
from aios_habit.provider_health import ProviderHealthStore, mask_key_id
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
    assert configs[0].allow_model_auto_substitution is False
    assert configs[0].timeout_seconds == 30


def test_provider_catalog_model_allows_auto_substitution():
    configs = provider_configs_from_env({"DEEPSEEK_API_KEY": "fake-secret-value"})

    assert len(configs) == 1
    assert configs[0].model_name == "deepseek-v4-flash"
    assert configs[0].allow_model_auto_substitution is True


def test_model_discovery_uses_runtime_endpoint_base():
    config = RouterProviderConfig(
        "deepseek",
        "DeepSeek",
        "https://regional.example/v1/chat/completions",
        "retired-model",
    )

    assert router_module._model_discovery_base_url(config, "https://catalog.example") == "https://regional.example/v1"
    assert router_module._model_discovery_base_url(RouterProviderConfig("deepseek", "DeepSeek"), "https://catalog.example") == "https://catalog.example"


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


def test_provider_configs_from_env_loads_gemini_and_google_key_alias():
    configs = provider_configs_from_env({"GEMINI_API_KEY": "fake-gemini-key"})
    assert len(configs) == 1
    assert configs[0].provider_id == "gemini"
    assert configs[0].api_key == "fake-gemini-key"
    assert configs[0].endpoint_url.startswith("https://generativelanguage.googleapis.com")

    configs_alias = provider_configs_from_env({"GOOGLE_API_KEY": "fake-google-key"})
    assert len(configs_alias) == 1
    assert configs_alias[0].provider_id == "gemini"
    assert configs_alias[0].api_key == "fake-google-key"


def test_provider_configs_from_env_loads_github_token_and_api_key_alias():
    configs = provider_configs_from_env({"GITHUB_TOKEN": "fake-gh-token"})
    assert len(configs) == 1
    assert configs[0].provider_id == "github_models"
    assert configs[0].api_key == "fake-gh-token"

    configs_alias = provider_configs_from_env({"GITHUB_API_KEY": "fake-gh-key"})
    assert len(configs_alias) == 1
    assert configs_alias[0].provider_id == "github_models"
    assert configs_alias[0].api_key == "fake-gh-key"


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


def test_provider_success_records_health_store_success():
    store = ProviderHealthStore()
    config = RouterProviderConfig("groq", "Groq", "http://example.test/v1", "model", "fake-secret-value", True)
    result = route_answer(req(SAFETY_MODE_NORMAL), [config], store, lambda c, r: "provider answer")
    state = store.get_provider_state("groq")[mask_key_id("fake-secret-value")]
    assert result.answer_text == "provider answer"
    assert state.success_count == 1
    assert state.status == "healthy"


def test_first_key_rate_limited_rotates_to_second_key():
    store = ProviderHealthStore()
    config = RouterProviderConfig(
        "groq",
        "Groq",
        "http://example.test/v1",
        "model",
        "",
        True,
        api_keys=["fake-secret-value-one", "fake-secret-value-two"],
    )
    calls = []

    def client(c, r):
        calls.append(c.api_key)
        if c.api_key == "fake-secret-value-one":
            raise RuntimeError("429 rate limit")
        return "answer from second key"

    result = route_answer(req(SAFETY_MODE_NORMAL), [config], store, client)
    assert result.answer_text == "answer from second key"
    assert calls == ["fake-secret-value-one", "fake-secret-value-two"]
    assert store.get_provider_state("groq")[mask_key_id("fake-secret-value-one")].status == "cooldown"


def test_auth_error_disables_failed_key_in_health_store():
    store = ProviderHealthStore()
    config = RouterProviderConfig("groq", "Groq", "http://example.test/v1", "model", "fake-secret-value", True)
    result = route_answer(req(SAFETY_MODE_NORMAL), [config], store, lambda c, r: (_ for _ in ()).throw(RuntimeError("401 invalid api key")))
    state = store.get_provider_state("groq")[mask_key_id("fake-secret-value")]
    assert result.used_fallback
    assert state.status == "disabled"


def test_cooldown_key_is_skipped_before_provider_call():
    store = ProviderHealthStore()
    key_id = mask_key_id("fake-secret-value")
    store.record_failure("groq", key_id, "rate_limited")
    config = RouterProviderConfig("groq", "Groq", "http://example.test/v1", "model", "fake-secret-value", True)
    calls = []
    result = route_answer(req(SAFETY_MODE_NORMAL), [config], store, lambda c, r: calls.append(c.provider_id) or "bad")
    assert calls == []
    assert result.used_fallback
    assert result.attempts[-1].status == "cooldown"


def test_all_health_unavailable_falls_back_deterministic():
    store = ProviderHealthStore()
    store.record_failure("groq", mask_key_id("fake-secret-value"), "auth_error")
    config = RouterProviderConfig("groq", "Groq", "http://example.test/v1", "model", "fake-secret-value", True)
    result = route_answer(req(SAFETY_MODE_NORMAL), [config], store, lambda c, r: "bad")
    assert result.answer_text == "fallback"
    assert result.used_fallback


def test_company_cloud_block_happens_before_health_or_provider_call():
    store = ProviderHealthStore()
    config = RouterProviderConfig("openrouter", "OpenRouter", "http://example.test/v1", "model", "fake-secret-value", True)
    calls = []
    result = route_answer(req(SAFETY_MODE_COMPANY), [config], store, lambda c, r: calls.append(c.provider_id) or "bad")
    assert calls == []
    assert store.get_provider_state("openrouter") == {}
    assert result.attempts[0].status == "blocked"


def test_model_not_found_retries_with_discovered_model(monkeypatch):
    config = RouterProviderConfig(
        "deepseek",
        "DeepSeek",
        "https://api.deepseek.com/chat/completions",
        "deepseek-chat",
        "fake-secret-value",
        True,
    )
    substitution = router_module.ModelSubstitution(
        "deepseek",
        "deepseek-chat",
        "deepseek-v4-flash",
        "Model tự thay cho kiểm thử.",
    )
    monkeypatch.setattr(router_module, "_try_model_substitution", lambda _cfg: substitution)
    calls = []

    def client(cfg, _request):
        calls.append(cfg.model_name)
        if cfg.model_name == "deepseek-chat":
            raise RuntimeError("supported API model names are deepseek-v4-flash")
        return "answer from discovered model"

    result = route_answer(req(), [config], ProviderHealthStore(), client)

    assert calls == ["deepseek-chat", "deepseek-v4-flash"]
    assert result.answer_text == "answer from discovered model"
    assert result.used_model == "deepseek-v4-flash"
    assert result.attempts[0].error_type == "model_not_found"
    assert result.attempts[-1].status == "success"
    assert "Model tự thay" in result.attempts[-1].reason_vi


def test_model_substitution_is_not_used_for_explicit_model_override(monkeypatch):
    config = RouterProviderConfig(
        "deepseek",
        "DeepSeek",
        "https://api.deepseek.com/chat/completions",
        "owner-pinned-model",
        "fake-secret-value",
        True,
        allow_model_auto_substitution=False,
    )
    monkeypatch.setattr(
        router_module,
        "_try_model_substitution",
        lambda _cfg: (_ for _ in ()).throw(AssertionError("must not auto-substitute an explicit override")),
    )

    result = route_answer(
        req(),
        [config],
        ProviderHealthStore(),
        lambda _cfg, _request: (_ for _ in ()).throw(RuntimeError("model not found")),
    )

    assert result.used_fallback
    assert result.attempts[-1].error_type == "model_not_found"


def test_failed_substitution_records_retry_error_and_falls_back(monkeypatch):
    config = RouterProviderConfig(
        "deepseek",
        "DeepSeek",
        "https://api.deepseek.com/chat/completions",
        "deepseek-chat",
        "fake-secret-value",
        True,
    )
    monkeypatch.setattr(
        router_module,
        "_try_model_substitution",
        lambda _cfg: router_module.ModelSubstitution(
            "deepseek", "deepseek-chat", "deepseek-v4-flash", "Model tự thay cho kiểm thử."
        ),
    )

    def client(cfg, _request):
        if cfg.model_name == "deepseek-chat":
            raise RuntimeError("model not found")
        raise RuntimeError("429 rate limit")

    store = ProviderHealthStore()
    result = route_answer(req(), [config], store, client)

    state = store.get_provider_state("deepseek")[mask_key_id("fake-secret-value")]
    assert result.used_fallback
    assert [attempt.error_type for attempt in result.attempts] == ["model_not_found", "rate_limited"]
    assert state.status == "cooldown"
    assert state.last_error_type == "rate_limited"


def test_provider_circuit_opens_without_disabling_key_and_fails_over():
    store = ProviderHealthStore(circuit_failure_threshold=1)
    primary = RouterProviderConfig("groq", "Groq", "http://example.test", "model", "first-key", True, priority=1)
    secondary = RouterProviderConfig("deepseek", "DeepSeek", "http://example.test", "model", "second-key", True, priority=20)
    calls = []

    def client(config, _request):
        calls.append(config.provider_id)
        if config.provider_id == "groq":
            raise RuntimeError("503 server error")
        return "second provider answer"

    result = route_answer(req(), [primary, secondary], store, client)

    assert result.answer_text == "second provider answer"
    assert calls == ["groq", "deepseek"]
    assert store.get_circuit_state("groq").status == "open"
    assert store.is_key_available("groq", mask_key_id("first-key"))
    assert result.attempts[0].failure_scope == "provider"


def test_bad_response_locks_only_current_model_not_key():
    store = ProviderHealthStore()
    config = RouterProviderConfig("groq", "Groq", "http://example.test", "model-a", "shared-key", True)
    result = route_answer(req(), [config], store, lambda _config, _request: "")
    key_id = mask_key_id("shared-key")

    assert result.used_fallback
    assert store.is_key_available("groq", key_id)
    assert not store.is_model_available("groq", key_id, "model-a")
    assert result.attempts[-1].failure_scope == "model"


def test_retry_after_is_honored_for_rate_limited_key():
    clock = [1000.0]
    store = ProviderHealthStore(_clock=lambda: clock[0])
    key_id = mask_key_id("rate-key")
    store.record_failure("groq", key_id, "rate_limited", retry_after_seconds=37)

    assert int(store.get_key_state("groq", key_id).cooldown_until - clock[0]) == 37


def test_language_fit_selects_matching_provider_before_priority():
    japanese = RouterProviderConfig(
        "groq", "Groq", "http://example.test", "model", "jp-key", True,
        priority=20, supported_languages=("ja",),
    )
    english = RouterProviderConfig(
        "deepseek", "DeepSeek", "http://example.test", "model", "en-key", True,
        priority=1, supported_languages=("en",),
    )
    request = RouterRequest("生産履歴の登録手順", "ctx", "fallback", safety_mode_label=SAFETY_MODE_NORMAL)
    used = []
    result = route_answer(request, [english, japanese], ProviderHealthStore(), lambda config, _request: used.append(config.provider_id) or "ok")

    assert result.answer_text == "ok"
    assert used == ["groq"]
    assert result.attempts[-1].key_id_masked != "jp-key"
    assert "jp-key" not in result.route_summary_vi
