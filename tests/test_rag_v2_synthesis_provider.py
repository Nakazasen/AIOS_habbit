"""Tests for the smart multi-provider RAG v2 synthesis adapter."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import os

import pytest

from aios_habit.ai_router import RouterProviderConfig, RouterResult, RouterAttempt
from aios_habit.rag_v2.evidence import EvidenceAnswerMode, PrivacySummary
from aios_habit.rag_v2.synthesis import ProviderSynthesisRequest, SynthesisPlan
from aios_habit.rag_v2_synthesis_provider import (
    RouterSynthesisProvider,
    SYNTHESIS_CLOUD_OPT_IN_ENV,
    _format_evidence_context,
    _format_question,
    create_synthesis_provider,
)


# ---------------------------------------------------------------------------
# Helpers — lightweight SimpleNamespace mocks avoid EvidencePack's many fields
# ---------------------------------------------------------------------------


def _make_item(
    citation_id: str = "C1",
    snippet: str = "Test evidence snippet",
    source_name: str = "doc.pdf",
    page: int | None = 1,
    sheet: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        evidence_id=f"ev_{citation_id}",
        citation_id=citation_id,
        source_name=source_name,
        snippet=snippet,
        page=page,
        sheet=sheet,
    )


def _make_pack(
    query: str = "What is the process?",
    cloud_allowed: bool = True,
    items: list | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        query=query,
        items=tuple(items or [_make_item()]),
        answer_mode=EvidenceAnswerMode.ANSWER,
        privacy_summary=PrivacySummary(
            overall_label="cloud_safe" if cloud_allowed else "local_only",
            local_only=not cloud_allowed,
            cloud_allowed=cloud_allowed,
            labels_present=("cloud_safe",) if cloud_allowed else ("local_only",),
        ),
    )


def _make_plan() -> SynthesisPlan:
    return SynthesisPlan(
        answer_shape="grounded_summary",
        max_claims=5,
        allowed_citation_ids=("C1",),
        required_facet_ids=(),
        missing_facet_ids=(),
        required_obligation_ids=(),
        missing_obligation_ids=(),
        limitation_reasons=(),
    )


def _make_request(
    cloud_allowed: bool = True,
    contract: str = "Answer with citations",
) -> ProviderSynthesisRequest:
    return ProviderSynthesisRequest(
        evidence_pack=_make_pack(cloud_allowed=cloud_allowed),
        plan=_make_plan(),
        contract=contract,
    )


def _make_router_result(
    answer: str = "The process involves step A [C1].",
    used_fallback: bool = False,
    provider: str = "groq",
    model: str = "llama-3.1-70b",
) -> RouterResult:
    return RouterResult(
        answer_text=answer,
        used_provider=provider,
        used_model=model,
        used_fallback=used_fallback,
        safety_status="external_allowed_normal_docs",
        attempts=[RouterAttempt(provider, provider, model, "success", "", 150)],
        terminal_status="success",
    )


MOCK_CONFIGS = [
    RouterProviderConfig(
        "groq", "Groq", "https://api.groq.com/v1/chat/completions",
        "llama-3.1-70b", "sk-test-groq", True, False, 100, 30,
    ),
    RouterProviderConfig(
        "deepseek", "DeepSeek", "https://api.deepseek.com/v1/chat/completions",
        "deepseek-chat", "sk-test-ds", True, False, 110, 30,
    ),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFormatting:
    def test_evidence_context_includes_citation_id_and_snippet(self):
        request = _make_request()
        ctx = _format_evidence_context(request)
        assert "[C1]" in ctx
        assert "Test evidence snippet" in ctx
        assert "doc.pdf" in ctx

    def test_evidence_context_includes_page_and_sheet(self):
        item = _make_item(page=3, sheet="Sheet1")
        pack = _make_pack(items=[item])
        request = ProviderSynthesisRequest(
            evidence_pack=pack, plan=_make_plan(), contract="test",
        )
        ctx = _format_evidence_context(request)
        assert "page 3" in ctx
        assert "sheet: Sheet1" in ctx

    def test_question_includes_contract(self):
        request = _make_request(contract="Must cite all sources")
        q = _format_question(request)
        assert "Must cite all sources" in q
        assert "What is the process?" in q

    def test_question_includes_repair_info(self):
        request = ProviderSynthesisRequest(
            evidence_pack=_make_pack(),
            plan=_make_plan(),
            contract="Answer with citations",
            repair_candidate="Bad answer",
            repair_errors=("missing_citation",),
        )
        q = _format_question(request)
        assert "Bad answer" in q
        assert "missing_citation" in q


class TestRouterSynthesisProvider:
    @pytest.fixture(autouse=True)
    def clean_cloud_opt_in(self, monkeypatch):
        monkeypatch.delenv("AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS", raising=False)

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_success_returns_answer_text(self, mock_route):
        mock_route.return_value = _make_router_result()
        provider = RouterSynthesisProvider(provider_configs=MOCK_CONFIGS)
        answer = provider(_make_request())
        assert "step A" in answer
        assert "[C1]" in answer
        mock_route.assert_called_once()

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_fallback_raises_runtime_error(self, mock_route):
        mock_route.return_value = _make_router_result(
            answer="", used_fallback=True,
        )
        provider = RouterSynthesisProvider(provider_configs=MOCK_CONFIGS)
        with pytest.raises(RuntimeError, match="All synthesis providers failed"):
            provider(_make_request())

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_fallback_error_message_carries_provider_error_types(self, mock_route):
        mock_route.return_value = RouterResult(
            answer_text="",
            used_provider="Dữ liệu cục bộ",
            used_model="",
            used_fallback=True,
            safety_status="fallback_local",
            attempts=[
                RouterAttempt(
                    "groq", "Groq", "llama-3.1-70b", "failed", "", 120, "bad_response",
                )
            ],
            terminal_status="local_renderer",
        )
        provider = RouterSynthesisProvider(provider_configs=MOCK_CONFIGS)
        with pytest.raises(RuntimeError, match="error_types=bad_response"):
            provider(_make_request())

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_privacy_filters_cloud_providers(self, mock_route):
        """When evidence is local_only, only trusted_internal providers survive."""
        local_config = RouterProviderConfig(
            "ollama_local", "Ollama Local",
            "http://localhost:11434/v1/chat/completions",
            "llama3.1", "", True, True, 10, 30,
        )
        all_configs = MOCK_CONFIGS + [local_config]
        mock_route.return_value = _make_router_result(provider="ollama_local")

        provider = RouterSynthesisProvider(provider_configs=all_configs)
        request = _make_request(cloud_allowed=False)
        provider(request)

        # Verify route_answer was called with only local configs
        call_args = mock_route.call_args
        passed_configs = call_args[0][1]
        assert all(c.trusted_internal for c in passed_configs)
        assert len(passed_configs) == 1

    def test_no_providers_raises_with_privacy_reason(self):
        """No cloud providers + local_only evidence = clear error."""
        provider = RouterSynthesisProvider(provider_configs=MOCK_CONFIGS)
        request = _make_request(cloud_allowed=False)
        with pytest.raises(RuntimeError, match="privacy_blocked"):
            provider(request)

    def test_no_providers_raises_with_config_reason(self):
        """Empty config list = clear error."""
        provider = RouterSynthesisProvider(provider_configs=[])
        with pytest.raises(RuntimeError, match="no_providers_configured"):
            provider(_make_request())

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_timeout_override_applied(self, mock_route):
        mock_route.return_value = _make_router_result()
        provider = RouterSynthesisProvider(
            provider_configs=MOCK_CONFIGS, timeout_seconds=60,
        )
        provider(_make_request())
        call_args = mock_route.call_args
        passed_configs = call_args[0][1]
        assert all(c.timeout_seconds == 60 for c in passed_configs)

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_task_type_is_rag_v2_synthesis(self, mock_route):
        mock_route.return_value = _make_router_result()
        provider = RouterSynthesisProvider(provider_configs=MOCK_CONFIGS)
        provider(_make_request())
        router_request = mock_route.call_args[0][0]
        assert router_request.task_type == "rag_v2_synthesis"

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_session_id_passed_through(self, mock_route):
        mock_route.return_value = _make_router_result()
        provider = RouterSynthesisProvider(
            provider_configs=MOCK_CONFIGS, session_id="sess-123",
        )
        provider(_make_request())
        router_request = mock_route.call_args[0][0]
        assert router_request.session_id == "sess-123"


    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_safety_mode_label_normal_when_cloud_allowed(self, mock_route):
        """RouterRequest must carry an explicit safety mode, never AUTO.

        Regression: with the AUTO default the router blocks every provider
        (auto:blocked) and synthesis falls back to an empty answer.
        """
        from aios_habit.safety_modes import SAFETY_MODE_NORMAL

        mock_route.return_value = _make_router_result()
        provider = RouterSynthesisProvider(provider_configs=MOCK_CONFIGS)
        provider(_make_request(cloud_allowed=True))
        router_request = mock_route.call_args[0][0]
        assert router_request.safety_mode_label == SAFETY_MODE_NORMAL

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_safety_mode_label_company_when_local_only(self, mock_route):
        from aios_habit.safety_modes import SAFETY_MODE_COMPANY

        local_config = RouterProviderConfig(
            "ollama_local", "Ollama Local",
            "http://localhost:11434/v1/chat/completions",
            "llama3.1", "", True, True, 10, 30,
        )
        mock_route.return_value = _make_router_result()
        provider = RouterSynthesisProvider(provider_configs=[local_config])
        provider(_make_request(cloud_allowed=False))
        router_request = mock_route.call_args[0][0]
        assert router_request.safety_mode_label == SAFETY_MODE_COMPANY

    @patch("aios_habit.rag_v2_synthesis_provider.route_answer")
    def test_opt_in_keeps_cloud_providers_for_local_only(self, mock_route, monkeypatch):
        """Owner opt-in: local_only pack keeps cloud configs, NORMAL label."""
        from aios_habit.safety_modes import SAFETY_MODE_NORMAL

        monkeypatch.setenv(SYNTHESIS_CLOUD_OPT_IN_ENV, "1")
        mock_route.return_value = _make_router_result()
        provider = RouterSynthesisProvider(provider_configs=MOCK_CONFIGS)
        provider(_make_request(cloud_allowed=False))
        passed_configs = mock_route.call_args[0][1]
        assert len(passed_configs) == len(MOCK_CONFIGS)
        router_request = mock_route.call_args[0][0]
        assert router_request.safety_mode_label == SAFETY_MODE_NORMAL


class TestCreateSynthesisProvider:
    @patch("aios_habit.rag_v2_synthesis_provider.provider_configs_from_env")
    def test_returns_none_when_no_keys(self, mock_env):
        mock_env.return_value = []
        assert create_synthesis_provider() is None

    @patch("aios_habit.rag_v2_synthesis_provider.provider_configs_from_env")
    def test_fail_closed_with_keys_but_no_opt_in(self, mock_env):
        """P1.4: env keys alone must NOT build a cloud provider."""
        mock_env.return_value = MOCK_CONFIGS
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SYNTHESIS_CLOUD_OPT_IN_ENV, None)
            assert create_synthesis_provider() is None

    @patch("aios_habit.rag_v2_synthesis_provider.provider_configs_from_env")
    def test_returns_provider_when_explicitly_allowed(self, mock_env):
        mock_env.return_value = MOCK_CONFIGS
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SYNTHESIS_CLOUD_OPT_IN_ENV, None)
            provider = create_synthesis_provider(allow_cloud=True)
        assert provider is not None
        assert isinstance(provider, RouterSynthesisProvider)

    @patch("aios_habit.rag_v2_synthesis_provider.provider_configs_from_env")
    def test_returns_provider_when_env_opt_in(self, mock_env):
        mock_env.return_value = MOCK_CONFIGS
        with patch.dict(os.environ, {SYNTHESIS_CLOUD_OPT_IN_ENV: "1"}):
            provider = create_synthesis_provider()
        assert provider is not None
        assert isinstance(provider, RouterSynthesisProvider)

    @patch("aios_habit.rag_v2_synthesis_provider.provider_configs_from_env")
    def test_returns_none_when_opt_in_but_no_keys(self, mock_env):
        mock_env.return_value = []
        assert create_synthesis_provider(allow_cloud=True) is None
