"""Shared, redacted resilience helpers for AI transport adapters.

AIOS owns privacy, consent, evidence and answer-validation policy. This module
only classifies safe transport outcomes and orders already policy-eligible
candidates; it never sees a prompt, evidence block, raw credential or source ID.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, MutableMapping, Sequence

from aios_habit.provider_health import ProviderHealthStore

ROUTE_SUCCESS = "success"
ROUTE_RETRY_LATER = "retry_later"
ROUTE_INFRASTRUCTURE_INVALID = "infrastructure_invalid"
ROUTE_POLICY_BLOCKED = "policy_blocked"
ROUTE_LOCAL_RENDERER = "local_renderer"

SCOPE_NONE = "none"
SCOPE_PROVIDER = "provider"
SCOPE_KEY = "key"
SCOPE_MODEL = "model"

_MODEL_ERRORS = frozenset({
    "model_not_found",
    "model_unsupported",
    "invalid_model",
    "invalid_output",
    "bad_response",
})
_KEY_ERRORS = frozenset({"auth_error", "rate_limited", "quota_exhausted"})
_PROVIDER_ERRORS = frozenset({"timeout", "server_error", "network_error"})
_RETRY_AFTER_RE = re.compile(r"(?:retry[- ]?after|retry in)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


@dataclass(frozen=True)
class ResilientRouteAttempt:
    provider_id: str
    model_id: str = ""
    key_id_masked: str = ""
    status: str = "skipped"
    error_type: str = ""
    failure_scope: str = SCOPE_NONE
    retry_after_seconds: float | None = None
    candidate_score: float | None = None
    latency_ms: float = 0.0


@dataclass(frozen=True)
class ResilientRouteOutcome:
    status: str
    error_type: str = ""
    attempts: tuple[ResilientRouteAttempt, ...] = ()
    effective_provider: str = ""
    effective_model: str = ""
    fallback_used: bool = False
    retry_after_seconds: float | None = None
    telemetry: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "error_type": self.error_type,
            "attempts": [asdict(attempt) for attempt in self.attempts],
            "effective_provider": self.effective_provider,
            "effective_model": self.effective_model,
            "fallback_used": self.fallback_used,
            "retry_after_seconds": self.retry_after_seconds,
            "telemetry": dict(self.telemetry),
        }


def classify_failure_scope(error_type: str) -> str:
    normalized = str(error_type or "").strip().lower()
    if normalized in _MODEL_ERRORS:
        return SCOPE_MODEL
    if normalized in _KEY_ERRORS:
        return SCOPE_KEY
    if normalized in _PROVIDER_ERRORS:
        return SCOPE_PROVIDER
    return SCOPE_NONE


def retry_after_from_error(error: Exception | str | Mapping[str, Any] | None) -> float | None:
    """Extract a bounded retry hint without retaining the raw external error."""
    if isinstance(error, Mapping):
        for name in ("retry_after_seconds", "retry_after", "retryAfter"):
            if name in error:
                try:
                    value = float(error[name])
                except (TypeError, ValueError):
                    continue
                return value if value > 0 else None
    for name in ("retry_after_seconds", "retry_after"):
        value = getattr(error, name, None)
        if value is not None:
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                parsed = 0.0
            if parsed > 0:
                return parsed
    matched = _RETRY_AFTER_RE.search(str(error or ""))
    return float(matched.group(1)) if matched else None


def opaque_session_key(
    session_id: str | None,
    *,
    task_type: str,
    query_language: str,
    privacy_label: str,
) -> str:
    value = str(session_id or "").strip()
    if not value:
        return ""
    material = "|".join((value, task_type, query_language, privacy_label))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def candidate_score(
    *,
    provider_id: str,
    key_id_masked: str,
    model_id: str,
    priority: int,
    query_language: str,
    supported_languages: Sequence[str] = (),
    health_store: ProviderHealthStore | None = None,
) -> tuple[float, dict[str, float]]:
    """Return a deterministic health score for a policy-eligible candidate."""
    del key_id_masked, model_id
    languages = {str(value).lower() for value in supported_languages}
    language_fit = 1.0 if query_language in {"", "unknown", "mixed"} or query_language in languages else 0.0
    reliability = 0.5
    latency = 0.0
    if health_store is not None:
        circuit = health_store.get_circuit_state(provider_id)
        reliability = (circuit.success_count + 1) / (circuit.success_count + circuit.failure_count + 2)
        latency = circuit.latency_ewma_ms
    priority_component = 1.0 / max(1, int(priority))
    latency_component = 1.0 / (1.0 + (latency / 1000.0))
    score = round((0.45 * reliability) + (0.30 * language_fit) + (0.15 * latency_component) + (0.10 * priority_component), 6)
    return score, {
        "reliability": round(reliability, 6),
        "language_fit": language_fit,
        "latency_component": round(latency_component, 6),
        "priority_component": round(priority_component, 6),
    }


def lkg_preference(
    affinity: MutableMapping[str, dict[str, Any]],
    *,
    session_key: str,
    now: float | None = None,
    ttl_seconds: float = 900.0,
) -> dict[str, Any] | None:
    if not session_key:
        return None
    now = time.time() if now is None else now
    record = affinity.get(session_key)
    if not record or float(record.get("expires_at", 0.0)) <= now:
        affinity.pop(session_key, None)
        return None
    return dict(record)


def record_lkg(
    affinity: MutableMapping[str, dict[str, Any]],
    *,
    session_key: str,
    provider_id: str,
    model_id: str,
    now: float | None = None,
    ttl_seconds: float = 900.0,
) -> None:
    if not session_key:
        return
    now = time.time() if now is None else now
    affinity[session_key] = {
        "provider_id": str(provider_id),
        "model_id": str(model_id),
        "expires_at": now + max(1.0, float(ttl_seconds)),
    }


def redact_delegated_attempt(attempt: Any) -> ResilientRouteAttempt:
    """Map external-router attempts to the AIOS safe telemetry schema."""
    if isinstance(attempt, Mapping):
        row = attempt
    else:
        try:
            row = asdict(attempt)
        except TypeError:
            row = vars(attempt) if hasattr(attempt, "__dict__") else {}
    error_type = str(row.get("error_type") or row.get("error") or "")
    raw_key = str(row.get("key_id_masked") or "")
    return ResilientRouteAttempt(
        provider_id=str(row.get("provider") or row.get("provider_id") or row.get("name") or ""),
        model_id=str(row.get("model") or row.get("model_id") or ""),
        key_id_masked=raw_key if raw_key.startswith("key-") else "",
        status=str(row.get("status") or "unknown"),
        error_type=error_type,
        failure_scope=classify_failure_scope(error_type),
        retry_after_seconds=retry_after_from_error(row),
        latency_ms=float(row.get("latency_ms") or 0.0),
    )
