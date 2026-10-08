from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from aios_habit.brain_gateway import SanitizedRouterPayload, SanitizedSourcePayload
from aios_habit.resilient_routing import ROUTE_SUCCESS, ROUTE_RETRY_LATER
from aios_habit.workspace_chat_router_adapter import (
    generate_answer_via_router,
    generate_answer_via_router_detailed,
    WorkspaceChatRouterAdapter,
)


@pytest.fixture
def sample_payload() -> SanitizedRouterPayload:
    return SanitizedRouterPayload(
        sanitized_question="Mã lỗi C7620 xử lý thế nào?",
        sanitized_sources=(
            SanitizedSourcePayload(
                source_id="src_1",
                source_scope="local_notebook",
                source_type="text",
                title="Sổ tay vận hành LSU",
                text="Lỗi C7620 phát sinh khi lệch trục quay quá 70 dot.",
                privacy_label="public",
            ),
        ),
        metadata={"source_set_hash": "test_hash_123"},
    )


def test_adapter_defaults_to_internal_pool_router(sample_payload, monkeypatch):
    """Adapter must route through internal aios_habit.ai_router by default reading AIOS_LOCAL_AI_*."""
    monkeypatch.setenv("AIOS_LOCAL_AI_ENDPOINT", "https://api.commandcode.ai/provider/v1/chat/completions")
    monkeypatch.setenv("AIOS_LOCAL_AI_API_KEY", "test_key_dummy_93_chars_long_pool_command_code_secret")
    monkeypatch.setenv("AIOS_LOCAL_AI_MODEL", "inclusionai/ling-3.1-flash:free")
    monkeypatch.setenv("AIOS_LOCAL_AI_FAILOVER_MODELS", "poolside/laguna-s-2.1-free")
    monkeypatch.delenv("AIOS_USE_LEGACY_NAKAZASEN_ROUTER", raising=False)

    # Ensure legacy router branch is NOT called in default mode
    mock_legacy_gen = MagicMock(side_effect=AssertionError("Should not call legacy router!"))
    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter._generate_via_legacy_router", mock_legacy_gen)

    # Mock low-level provider call in internal router
    def mock_answer_with_provider(question, source_context, config, deterministic_answer, *args, **kwargs):
        from aios_habit.ai_provider_bridge import ProviderResult
        assert "api.commandcode.ai" in config.endpoint_url
        assert config.model_name in ("inclusionai/ling-3.1-flash:free", "poolside/laguna-s-2.1-free")
        return ProviderResult(
            ok=True,
            answer_text="C7620 là lỗi lệch trục quay theo tài liệu [1].",
            provider_name=config.provider_type,
            model_name=config.model_name,
            used_fallback=False,
            safety_status="local_provider_ok",
        )

    monkeypatch.setattr("aios_habit.ai_router.answer_with_provider", mock_answer_with_provider)

    res = generate_answer_via_router_detailed(sample_payload)
    assert res.ok is True
    assert "C7620 là lỗi" in res.text
    assert res.route.status == ROUTE_SUCCESS
    assert res.route.effective_model == "inclusionai/ling-3.1-flash:free"
    assert not mock_legacy_gen.called

    # Check public wrapper functions
    ok, text = generate_answer_via_router(sample_payload)
    assert ok is True
    assert "C7620 là lỗi" in text

    adapter = WorkspaceChatRouterAdapter()
    ok_obj, text_obj = adapter.generate_answer(sample_payload)
    assert ok_obj is True
    assert "C7620 là lỗi" in text_obj


def test_adapter_legacy_rollback_via_env_flag(sample_payload, monkeypatch):
    """Setting AIOS_USE_LEGACY_NAKAZASEN_ROUTER=1 rolls back to external nakazasen_ai_router."""
    monkeypatch.setenv("AIOS_USE_LEGACY_NAKAZASEN_ROUTER", "1")

    from nakazasen_ai_router import AIRouteOutcome, AIResult

    class FakeExternalRouter:
        def __init__(self):
            self.called = False

        def route_outcome(self, request):
            self.called = True
            return AIRouteOutcome(
                status="success",
                result=AIResult(text="Trả lời từ router ngoài cũ.", provider_name="external_pkg"),
            )

    fake = FakeExternalRouter()
    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.create_router_from_env", lambda **kwargs: fake)

    res = generate_answer_via_router_detailed(sample_payload)
    assert res.ok is True
    assert res.text == "Trả lời từ router ngoài cũ."
    assert fake.called is True


def test_adapter_internal_router_failure_returns_clean_error(sample_payload, monkeypatch):
    """When internal router providers fail, adapter returns ok=False without crashing."""
    monkeypatch.setenv("AIOS_LOCAL_AI_ENDPOINT", "https://api.commandcode.ai/provider/v1/chat/completions")
    monkeypatch.setenv("AIOS_LOCAL_AI_API_KEY", "test_key")
    monkeypatch.setenv("AIOS_LOCAL_AI_MODEL", "inclusionai/ling-3.1-flash:free")
    monkeypatch.delenv("AIOS_USE_LEGACY_NAKAZASEN_ROUTER", raising=False)

    def mock_answer_fail(*args, **kwargs):
        from aios_habit.ai_provider_bridge import ProviderResult
        return ProviderResult(
            ok=False,
            answer_text="",
            provider_name="openai_compatible_local",
            model_name="inclusionai/ling-3.1-flash:free",
            error_message="HTTP 500 Server Error",
            used_fallback=True,
            safety_status="fallback_provider_error",
        )

    monkeypatch.setattr("aios_habit.ai_router.answer_with_provider", mock_answer_fail)

    res = generate_answer_via_router_detailed(sample_payload)
    assert res.ok is False
    assert "Dịch vụ AI chưa phản hồi" in res.text
    assert res.route.status == ROUTE_RETRY_LATER
