"""Provider model auto-discovery and fallback selection.

When a configured model name is rejected by a provider (e.g. DeepSeek
renames ``deepseek-chat`` to ``deepseek-v4-flash``), this module probes
the provider's ``/v1/models`` endpoint and selects the best available
replacement automatically.

This prevents silent provider death when APIs evolve their model names.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredModel:
    """A model available on a provider."""
    model_id: str
    owned_by: str = ""
    created: int = 0


@dataclass
class ModelDiscoveryResult:
    """Result of probing a provider's /v1/models endpoint."""
    ok: bool
    models: list[DiscoveredModel] = field(default_factory=list)
    error: str = ""
    latency_ms: float = 0.0
    cached: bool = False


@dataclass
class ModelSubstitution:
    """Record of an automatic model substitution."""
    provider_id: str
    original_model: str
    substituted_model: str
    reason: str
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_MODEL_CACHE: dict[str, tuple[float, list[DiscoveredModel]]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _cache_key(base_url: str) -> str:
    return base_url.rstrip("/").lower()


def _get_cached(base_url: str) -> list[DiscoveredModel] | None:
    key = _cache_key(base_url)
    entry = _MODEL_CACHE.get(key)
    if entry is None:
        return None
    ts, models = entry
    if time.time() - ts > _CACHE_TTL_SECONDS:
        del _MODEL_CACHE[key]
        return None
    return models


def _set_cached(base_url: str, models: list[DiscoveredModel]) -> None:
    _MODEL_CACHE[_cache_key(base_url)] = (time.time(), models)


def clear_model_cache() -> None:
    """Clear all cached model lists."""
    _MODEL_CACHE.clear()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_available_models(
    base_url: str,
    api_key: str = "",
    timeout: int = 10,
) -> ModelDiscoveryResult:
    """Probe a provider's ``GET /v1/models`` endpoint.

    Returns the list of available model IDs.  Results are cached for 1 hour
    so repeated calls during a session are cheap.
    """
    cached = _get_cached(base_url)
    if cached is not None:
        return ModelDiscoveryResult(ok=True, models=cached, cached=True)

    url = base_url.rstrip("/")
    # Try common patterns: /v1/models, /models
    probe_urls = []
    if "/v1" in url:
        probe_urls.append(url.rstrip("/") + "/models")
    else:
        probe_urls.append(url.rstrip("/") + "/v1/models")
        probe_urls.append(url.rstrip("/") + "/models")

    last_error = ""
    t0 = time.perf_counter()

    for probe_url in probe_urls:
        try:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            req = urllib.request.Request(probe_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            models = _parse_models_response(data)
            latency = (time.perf_counter() - t0) * 1000

            if models:
                _set_cached(base_url, models)
                return ModelDiscoveryResult(ok=True, models=models, latency_ms=latency)
            else:
                last_error = "Empty model list from provider"

        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}"
        except Exception as e:
            last_error = str(e)[:200]

    latency = (time.perf_counter() - t0) * 1000
    return ModelDiscoveryResult(ok=False, error=last_error, latency_ms=latency)


def _parse_models_response(data: Any) -> list[DiscoveredModel]:
    """Parse the OpenAI-compatible /v1/models response."""
    if not isinstance(data, dict):
        return []

    items = data.get("data", [])
    if not isinstance(items, list):
        return []

    models: list[DiscoveredModel] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_model_id = item.get("id")
        if not isinstance(raw_model_id, str):
            continue
        model_id = raw_model_id.strip()
        if not model_id:
            continue
        raw_created = item.get("created", 0)
        try:
            created = int(raw_created or 0)
        except (TypeError, ValueError):
            created = 0
        models.append(DiscoveredModel(
            model_id=model_id,
            owned_by=str(item.get("owned_by") or ""),
            created=created,
        ))
    return models


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

_GENERIC_MODEL_TOKENS = {
    "api", "chat", "free", "instruct", "instruction", "latest", "model",
    "preview", "pro", "reasoner", "small", "tiny", "turbo", "flash", "v",
}


def _model_family_tokens(model_id: str) -> set[str]:
    """Return non-generic model family tokens used for safe fallback matching."""
    tokens = re.split(r"[^a-z0-9]+", model_id.lower())
    return {
        re.sub(r"\d+$", "", token)
        for token in tokens
        if len(token) > 2 and token not in _GENERIC_MODEL_TOKENS
    }


def select_best_model(
    available: list[DiscoveredModel],
    preferred: list[str] | tuple[str, ...],
) -> str | None:
    """Pick a catalog-approved available model in preference order.

    A partial match is accepted only when the identifiers share at least one
    non-generic model family token. This allows ``deepseek-chat`` to migrate
    to ``deepseek-v4-flash`` but refuses ``approved-model`` ->
    ``unrelated-model``.
    """
    available_ids = [model.model_id for model in available]
    available_lower = [model.model_id.lower() for model in available]

    # 1. Exact match, preserving catalog preference order.
    for preferred_model in preferred:
        if preferred_model in available_ids:
            return preferred_model
        preferred_lower = preferred_model.lower()
        for index, available_model in enumerate(available_lower):
            if preferred_lower == available_model:
                return available_ids[index]

    # 2. Safe family match.
    for preferred_model in preferred:
        preferred_family = _model_family_tokens(preferred_model)
        if not preferred_family:
            continue
        for index, available_model in enumerate(available_ids):
            if preferred_family.intersection(_model_family_tokens(available_model)):
                return available_model

    return None


def attempt_model_substitution(
    provider_id: str,
    base_url: str,
    configured_model: str,
    default_models: list[str] | tuple[str, ...],
    api_key: str = "",
) -> ModelSubstitution | None:
    """Try to find a working model when the configured one is rejected.

    Returns a ModelSubstitution if a replacement is found, None otherwise.
    """
    result = discover_available_models(base_url, api_key)
    if not result.ok or not result.models:
        return None

    available_ids = [m.model_id for m in result.models]

    # If configured model is actually available, no substitution needed
    if configured_model in available_ids:
        return None

    # Choose only a model that matches the provider's approved preference list.
    # An arbitrary first result could be an unsuitable, deprecated, or privileged model.
    replacement = select_best_model(result.models, default_models)

    if replacement and replacement != configured_model:
        return ModelSubstitution(
            provider_id=provider_id,
            original_model=configured_model,
            substituted_model=replacement,
            reason=f"Model '{configured_model}' không còn được hỗ trợ. "
                   f"Tự động thay bằng '{replacement}'.",
        )

    return None


# ---------------------------------------------------------------------------
# Provider health check summary
# ---------------------------------------------------------------------------

def check_provider_models(
    base_url: str,
    api_key: str,
    configured_models: list[str] | tuple[str, ...],
    timeout: int = 10,
    replacement_models: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Check configured models against provider availability.

    ``replacement_models`` is an optional catalog-approved preference order
    used only to suggest a safe replacement for a stale configured model.
    """
    result = discover_available_models(base_url, api_key, timeout)
    approved_replacements = replacement_models or configured_models

    if not result.ok:
        return {
            "status": "unreachable",
            "error": result.error,
            "latency_ms": round(result.latency_ms, 1),
            "configured": list(configured_models),
            "available": [],
            "stale": list(configured_models),
            "valid": [],
            "suggestion": None,
        }

    available_ids = {model.model_id for model in result.models}
    valid = [model for model in configured_models if model in available_ids]
    stale = [model for model in configured_models if model not in available_ids]

    suggestion = None
    if stale:
        suggestion = select_best_model(result.models, approved_replacements)

    return {
        "status": "ok" if not stale else "stale_models",
        "error": "",
        "latency_ms": round(result.latency_ms, 1),
        "configured": list(configured_models),
        "available": [model.model_id for model in result.models],
        "stale": stale,
        "valid": valid,
        "suggestion": suggestion,
    }
