"""Tests for provider_model_discovery module."""

from aios_habit.provider_model_discovery import (
    DiscoveredModel,
    ModelDiscoveryResult,
    ModelSubstitution,
    attempt_model_substitution,
    check_provider_models,
    clear_model_cache,
    discover_available_models,
    select_best_model,
    _parse_models_response,
    _set_cached,
    _get_cached,
    _cache_key,
)


# ---------------------------------------------------------------------------
# select_best_model
# ---------------------------------------------------------------------------

def test_select_best_model_exact_match():
    models = [DiscoveredModel("deepseek-v4-flash"), DiscoveredModel("deepseek-v4-pro")]
    assert select_best_model(models, ["deepseek-v4-flash"]) == "deepseek-v4-flash"


def test_select_best_model_case_insensitive():
    models = [DiscoveredModel("DeepSeek-V4-Flash")]
    assert select_best_model(models, ["deepseek-v4-flash"]) == "DeepSeek-V4-Flash"


def test_select_best_model_partial_match():
    models = [DiscoveredModel("deepseek-v4-flash"), DiscoveredModel("deepseek-v4-pro")]
    # "deepseek-chat" should partial-match "deepseek" in available models
    result = select_best_model(models, ["deepseek-chat"])
    assert result in ("deepseek-v4-flash", "deepseek-v4-pro")


def test_select_best_model_no_match():
    models = [DiscoveredModel("llama-3.3-70b")]
    assert select_best_model(models, ["deepseek-chat"]) is None


def test_select_best_model_preference_order():
    models = [
        DiscoveredModel("model-b"),
        DiscoveredModel("model-a"),
        DiscoveredModel("model-c"),
    ]
    assert select_best_model(models, ["model-a", "model-b"]) == "model-a"


def test_select_best_model_prefers_exact_catalog_choice_over_earlier_family_match():
    models = [DiscoveredModel("deepseek-v4-pro"), DiscoveredModel("deepseek-v4-flash")]

    assert select_best_model(models, ["deepseek-v4-flash", "deepseek-v4-pro"]) == "deepseek-v4-flash"


def test_select_best_model_empty_available():
    assert select_best_model([], ["deepseek-chat"]) is None


def test_select_best_model_empty_preferred():
    models = [DiscoveredModel("some-model")]
    assert select_best_model(models, []) is None


# ---------------------------------------------------------------------------
# _parse_models_response
# ---------------------------------------------------------------------------

def test_parse_models_response_valid():
    data = {
        "data": [
            {"id": "deepseek-v4-flash", "owned_by": "deepseek", "created": 1700000000},
            {"id": "deepseek-v4-pro", "owned_by": "deepseek"},
        ]
    }
    models = _parse_models_response(data)
    assert len(models) == 2
    assert models[0].model_id == "deepseek-v4-flash"
    assert models[0].owned_by == "deepseek"
    assert models[1].model_id == "deepseek-v4-pro"


def test_parse_models_response_empty():
    assert _parse_models_response({"data": []}) == []
    assert _parse_models_response({}) == []
    assert _parse_models_response("invalid") == []
    assert _parse_models_response(None) == []


def test_parse_models_response_skips_invalid_items():
    data = {
        "data": [
            {"id": "valid-model"},
            {"id": ""},  # empty id
            {"id": None},
            {"id": 123},
            {"id": "also-valid", "created": "not-a-number"},
            "not-a-dict",
        ]
    }
    models = _parse_models_response(data)
    assert len(models) == 2
    assert models[0].model_id == "valid-model"
    assert models[1].model_id == "also-valid"
    assert models[1].created == 0


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_cache_miss_returns_none():
    clear_model_cache()
    assert _get_cached("https://api.example.com/v1") is None


def test_cache_set_and_get():
    clear_model_cache()
    models = [DiscoveredModel("test-model")]
    _set_cached("https://api.example.com/v1", models)
    cached = _get_cached("https://api.example.com/v1")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].model_id == "test-model"


def test_cache_key_normalization():
    assert _cache_key("https://api.example.com/v1/") == _cache_key("https://api.example.com/v1")
    assert _cache_key("HTTPS://API.EXAMPLE.COM/V1") == _cache_key("https://api.example.com/v1")


# ---------------------------------------------------------------------------
# ModelSubstitution
# ---------------------------------------------------------------------------

def test_model_substitution_auto_timestamp():
    sub = ModelSubstitution("deepseek", "deepseek-chat", "deepseek-v4-flash", "test reason")
    assert sub.timestamp > 0
    assert sub.provider_id == "deepseek"
    assert sub.original_model == "deepseek-chat"
    assert sub.substituted_model == "deepseek-v4-flash"


# ---------------------------------------------------------------------------
# check_provider_models (unit with cache injection)
# ---------------------------------------------------------------------------

def test_check_provider_models_with_cache():
    clear_model_cache()
    # Pre-populate cache
    _set_cached("https://api.deepseek.com", [
        DiscoveredModel("deepseek-v4-flash"),
        DiscoveredModel("deepseek-v4-pro"),
    ])

    result = check_provider_models(
        "https://api.deepseek.com",
        "fake-key",
        ["deepseek-v4-flash", "deepseek-chat"],
    )

    assert result["status"] == "stale_models"
    assert "deepseek-v4-flash" in result["valid"]
    assert "deepseek-chat" in result["stale"]
    assert result["suggestion"] is not None
    clear_model_cache()


def test_check_provider_models_all_valid():
    clear_model_cache()
    _set_cached("https://api.example.com/v1", [
        DiscoveredModel("model-a"),
        DiscoveredModel("model-b"),
    ])

    result = check_provider_models(
        "https://api.example.com/v1",
        "fake-key",
        ["model-a", "model-b"],
    )

    assert result["status"] == "ok"
    assert result["stale"] == []
    assert len(result["valid"]) == 2
    clear_model_cache()


def test_attempt_substitution_refuses_unapproved_model():
    clear_model_cache()
    _set_cached("https://api.example.com", [DiscoveredModel("unrelated-model")])

    result = attempt_model_substitution(
        "example",
        "https://api.example.com",
        "retired-model",
        ("approved-model",),
        "fake-key",
    )

    assert result is None
    clear_model_cache()


# ---------------------------------------------------------------------------
# classify_provider_error integration
# ---------------------------------------------------------------------------

def test_classify_model_not_found():
    from aios_habit.ai_router import classify_provider_error

    assert classify_provider_error("supported api model names are deepseek-v4-pro") == "model_not_found"
    assert classify_provider_error("model_not_found: deepseek-chat") == "model_not_found"
    assert classify_provider_error("Model does not exist") == "model_not_found"
    assert classify_provider_error("model not found") == "model_not_found"
    assert classify_provider_error("No such model: llama3-8b") == "model_not_found"


def test_classify_still_detects_auth():
    from aios_habit.ai_router import classify_provider_error
    assert classify_provider_error("401 Unauthorized") == "auth_error"
    assert classify_provider_error("403 Forbidden") == "auth_error"


def test_classify_still_detects_rate_limit():
    from aios_habit.ai_router import classify_provider_error
    assert classify_provider_error("429 Too Many Requests") == "rate_limited"
