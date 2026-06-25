from aios_habit.ai_router import RouterProviderConfig
from aios_habit.provider_health import (
    ProviderHealthStore,
    STATUS_COOLDOWN,
    STATUS_DISABLED,
    STATUS_HEALTHY,
    mask_key_id,
    provider_health_table_for_ui,
    vietnamese_health_note,
)


def cfg(value="demo-token-value"):
    return RouterProviderConfig(
        "groq",
        "Groq",
        "https://api.groq.com/openai/v1/chat/completions",
        "llama-test",
        value,
        True,
        False,
        10,
        5,
    )


def test_mask_key_id_hides_real_key():
    masked = mask_key_id("demo-token-value")
    assert "demo-token-value" not in masked
    assert masked.startswith("key-")
    assert mask_key_id("") == "khong-can-khoa"


def test_record_success_marks_key_healthy():
    store = ProviderHealthStore()
    key_id = mask_key_id("demo-token-value")
    state = store.record_success("groq", key_id)
    assert state.status == STATUS_HEALTHY
    assert state.success_count == 1


def test_auth_error_disables_key_for_session():
    store = ProviderHealthStore()
    key_id = mask_key_id("demo-token-value")
    state = store.record_failure("groq", key_id, "auth_error")
    assert state.status == STATUS_DISABLED
    assert not store.is_key_available("groq", key_id)


def test_rate_limit_timeout_and_server_error_trigger_cooldown():
    for error_type in ["rate_limited", "timeout", "server_error"]:
        store = ProviderHealthStore()
        key_id = mask_key_id(f"demo-token-value-{error_type}")
        state = store.record_failure("groq", key_id, error_type)
        assert state.status == STATUS_COOLDOWN
        assert state.cooldown_until > 0
        assert not store.is_key_available("groq", key_id)


def test_choose_next_key_skips_disabled_or_cooldown_key():
    store = ProviderHealthStore()
    first = "demo-token-value-one"
    second = "demo-token-value-two"
    store.record_failure("groq", mask_key_id(first), "auth_error")
    assert store.choose_next_key("groq", [first, second]) == second


def test_snapshot_never_contains_raw_key_and_has_vietnamese_note():
    store = ProviderHealthStore()
    key = "demo-token-value"
    store.record_success("groq", mask_key_id(key))
    snapshot = store.snapshot([cfg(key)])[0]
    assert key not in str(snapshot)
    assert snapshot.status == STATUS_HEALTHY
    assert "Nguồn AI" in vietnamese_health_note(snapshot)


def test_provider_health_table_for_ui_has_vietnamese_columns_and_no_raw_token():
    store = ProviderHealthStore()
    key = "demo-token-value"
    store.record_failure("groq", mask_key_id(key), "auth_error")
    rows = provider_health_table_for_ui([cfg(key)], store)
    joined = str(rows)
    assert "Nguồn AI" in joined
    assert "Bị tắt do lỗi xác thực" in joined
    assert "Chưa cấu hình" in joined
    assert key not in joined
