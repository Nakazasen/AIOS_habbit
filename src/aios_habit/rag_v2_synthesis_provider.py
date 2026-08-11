"""Smart multi-provider synthesis adapter for RAG v2 evidence packs.

Bridges the ``ProviderSynthesisProvider`` protocol to the existing
``ai_router.route_answer()`` infrastructure, inheriting health tracking,
failover, model auto-substitution, session affinity, and privacy gating
without reimplementing any of them.
"""
from __future__ import annotations

import logging
from typing import Optional

from aios_habit.ai_router import (
    RouterProviderConfig,
    RouterRequest,
    provider_configs_from_env,
    route_answer,
)
from aios_habit.provider_health import ProviderHealthStore
from aios_habit.rag_v2.synthesis import ProviderSynthesisRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a precise document assistant. You MUST answer ONLY using the "
    "evidence provided below. Every factual claim MUST include a citation "
    "in [citation_id] format. If the evidence is insufficient, say so "
    "explicitly. Do NOT invent information."
)


def _format_evidence_context(request: ProviderSynthesisRequest) -> str:
    """Build the source_context string from an evidence pack for the AI router."""
    pack = request.evidence_pack
    parts: list[str] = []
    for item in pack.items:
        header = f"[{item.citation_id}] {item.source_name}"
        if item.page is not None:
            header += f" (page {item.page})"
        if item.sheet:
            header += f" (sheet: {item.sheet})"
        parts.append(f"{header}\n{item.snippet}")
    return "\n\n---\n\n".join(parts)


def _format_question(request: ProviderSynthesisRequest) -> str:
    """Build the question string with synthesis contract instructions."""
    pack = request.evidence_pack
    lines: list[str] = []
    lines.append(f"Question: {pack.query}")
    if request.contract:
        lines.append("")
        lines.append("=== ANSWER CONTRACT ===")
        lines.append(request.contract)
    if request.repair_candidate:
        lines.append("")
        lines.append("=== PREVIOUS ANSWER (needs repair) ===")
        lines.append(request.repair_candidate)
        if request.repair_errors:
            lines.append("")
            lines.append("Errors to fix:")
            for error in request.repair_errors:
                lines.append(f"  - {error}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------


class RouterSynthesisProvider:
    """Adapts the AI router to the ``ProviderSynthesisProvider`` protocol.

    Parameters
    ----------
    provider_configs : list of RouterProviderConfig, optional
        Explicit provider list.  Falls back to ``provider_configs_from_env()``.
    health_store : ProviderHealthStore, optional
        Shared health tracker.  A fresh ephemeral store is created when omitted.
    max_attempts : int
        How many providers to try before giving up (default 3).
    timeout_seconds : int, optional
        Override per-provider timeout.  ``None`` keeps each provider's own default.
    session_id : str
        Opaque session key for LKG affinity.
    """

    def __init__(
        self,
        provider_configs: Optional[list[RouterProviderConfig]] = None,
        health_store: Optional[ProviderHealthStore] = None,
        *,
        max_attempts: int = 3,
        timeout_seconds: Optional[int] = None,
        session_id: str = "",
    ) -> None:
        self._configs = provider_configs
        self._health_store = health_store or ProviderHealthStore()
        self._max_attempts = max_attempts
        self._timeout_override = timeout_seconds
        self._session_id = session_id

    # -- helpers --------------------------------------------------------

    def _resolve_configs(
        self,
        cloud_allowed: bool,
    ) -> list[RouterProviderConfig]:
        """Return usable provider configs, filtering by privacy."""
        configs = self._configs if self._configs is not None else provider_configs_from_env()
        if self._timeout_override is not None:
            from dataclasses import replace
            configs = [replace(c, timeout_seconds=self._timeout_override) for c in configs]
        if not cloud_allowed:
            configs = [c for c in configs if c.trusted_internal]
        return configs

    # -- protocol -------------------------------------------------------

    def __call__(self, request: ProviderSynthesisRequest) -> str:
        """Implement ``ProviderSynthesisProvider.__call__``."""
        pack = request.evidence_pack
        cloud_allowed = pack.privacy_summary.cloud_allowed
        configs = self._resolve_configs(cloud_allowed)

        if not configs:
            privacy_reason = "privacy_blocked" if not cloud_allowed else "no_providers_configured"
            raise RuntimeError(
                f"No synthesis providers available ({privacy_reason})"
            )

        source_context = _format_evidence_context(request)
        question = _format_question(request)

        # Build a deterministic local answer as fallback text for the router.
        # The router uses this when all providers fail; but synthesis.py already
        # handles that fallback, so we pass an empty string to avoid the router
        # returning its own deterministic text.
        router_request = RouterRequest(
            question=question,
            source_context=f"{_SYSTEM_PROMPT}\n\n{source_context}",
            deterministic_answer="",
            max_attempts=self._max_attempts,
            privacy_label="cloud_safe" if cloud_allowed else "local_only",
            session_id=self._session_id,
            task_type="rag_v2_synthesis",
        )

        result = route_answer(
            router_request,
            configs,
            health_state=self._health_store,
        )

        if result.used_fallback or not result.answer_text.strip():
            reasons = [
                f"{a.provider_id}:{a.status}({a.error_type or a.reason_vi})"
                for a in result.attempts
            ]
            logger.warning(
                "All synthesis providers failed: %s",
                "; ".join(reasons) or "no_candidates",
            )
            raise RuntimeError(
                f"All synthesis providers failed "
                f"(terminal={result.terminal_status}, "
                f"attempts={len(result.attempts)})"
            )

        logger.info(
            "Synthesis via %s/%s in %dms",
            result.used_provider,
            result.used_model,
            sum(a.latency_ms for a in result.attempts if a.status == "success"),
        )
        return result.answer_text


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_synthesis_provider(
    *,
    session_id: str = "",
    health_store: Optional[ProviderHealthStore] = None,
    max_attempts: int = 3,
) -> Optional[RouterSynthesisProvider]:
    """Create a provider if any API keys are configured; return None otherwise.

    This is the intended entry point for wiring synthesis into the pipeline.
    Returning ``None`` preserves the current local-only behavior when no
    providers are available.
    """
    configs = provider_configs_from_env()
    if not configs:
        return None
    return RouterSynthesisProvider(
        provider_configs=configs,
        health_store=health_store,
        max_attempts=max_attempts,
        session_id=session_id,
    )
