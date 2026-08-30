"""Feature-flagged Workspace Chat retrieval adapter for the local RAG v2 canary.

The adapter changes retrieval only. Answer generation still flows through
``generate_workspace_ai_answer`` and the Brain Gateway, which remain the owners
of consent, privacy authorization, outbound sanitization, and provider access.
"""
from __future__ import annotations

from collections import Counter
import concurrent.futures
from dataclasses import dataclass
import functools
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Any, Callable, Iterable, Mapping, Optional, Tuple
import unicodedata

from aios_habit.rag_v2.adaptive_retrieval import (
    AdaptiveRetrievalPolicy,
    PostDecision,
    PreDecision,
    decide_initial_route,
    post_retrieval_gate,
    pre_retrieval_gate,
)
from aios_habit.rag_v2.bge_subprocess_client import BgeSubprocessWorkerClient
from aios_habit.rag_v2.index import SearchSummary
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.query_planning import build_query_plan, coerce_query_plan
from aios_habit.rag_v2.semantic import (
    SemanticBackendError,
    SemanticBackendUnavailable,
)

from aios_habit.rag_v2.structured_query import (
    StructuredQueryError,
    execute_excel_query,
    inspect_excel_schemas,
    plan_excel_query,
)
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_rag_v2_deployment import (
    DeploymentManifestError,
    load_workspace_chat_rag_v2_deployment,
)

LOGGER = logging.getLogger(__name__)

_SUBPROCESS_CLIENT = BgeSubprocessWorkerClient()

PREPARATION_LEDGER_TABLE = "source_preparation_ledger"
PREPARATION_LEDGER_SCHEMA_VERSION = "1.0.0"

PREP_STATE_PENDING = "pending"
PREP_STATE_PROCESSING = "processing"
PREP_STATE_READY = "ready"
PREP_STATE_FAILED = "failed"
PREP_STATE_CANCELLED = "cancelled"

PREP_PRIORITY_INTERACTIVE = "interactive"
PREP_PRIORITY_NORMAL = "normal"
PREP_PRIORITY_BACKFILL = "backfill"

PREP_ACTIVE_STATES = frozenset({PREP_STATE_PENDING, PREP_STATE_PROCESSING})
PREP_ALL_STATES = frozenset({
    PREP_STATE_PENDING,
    PREP_STATE_PROCESSING,
    PREP_STATE_READY,
    PREP_STATE_FAILED,
    PREP_STATE_CANCELLED,
})

_PREPARATION_ACTIVE_STATES = PREP_ACTIVE_STATES
_PREPARATION_READY_STATE = PREP_STATE_READY


@dataclass(frozen=True)
class SourcePreparationLedgerRow:
    """Persistent ledger record for document preparation and embedding readiness."""

    source_scope: str
    source_id: str
    source_fingerprint: str
    model_id: str
    model_revision: str
    state: str
    priority: str = PREP_PRIORITY_NORMAL
    attempt_count: int = 0
    last_error: str = ""
    document_id: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0


_PREPARATION_REGISTRY: dict[str, dict[str, Any]] = {}
_PREPARATION_LOCK = threading.RLock()
_PREPARATION_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None
_DRAIN_RUNNING_LOCK = threading.Lock()
_DRAIN_IS_RUNNING = False
_SOURCE_CACHE_LOCK = threading.Lock()
_SOURCE_CACHE: dict[tuple[str, str], WorkspaceAIContextSource] = {}


def _get_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _PREPARATION_EXECUTOR
    with _PREPARATION_LOCK:
        if _PREPARATION_EXECUTOR is None:
            _PREPARATION_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="wsc_bg_prepare"
            )
        return _PREPARATION_EXECUTOR

CANARY_ENABLED_ENV = "AIOS_WORKSPACE_RAG_V2_CANARY_ENABLED"
LOCAL_PILOT_ENABLED_ENV = "AIOS_WORKSPACE_RAG_V2_LOCAL_PILOT_ENABLED"
PROFILE_ENV = "AIOS_WORKSPACE_RAG_V2_PROFILE"
RUNTIME_ROOT_ENV = "AIOS_WORKSPACE_RAG_V2_RUNTIME_ROOT"
BGE_MODEL_PATH_ENV = "AIOS_BGE_M3_MODEL_PATH"
BGE_MODEL_REVISION_ENV = "AIOS_BGE_M3_MODEL_REVISION"
BGE_MODEL_CHECKSUM_ENV = "AIOS_BGE_M3_MODEL_CHECKSUM"
RETRIEVAL_DEVICE_ENV = "AIOS_RETRIEVAL_DEVICE"
ADAPTIVE_ENABLED_ENV = "AIOS_WORKSPACE_RAG_V2_ADAPTIVE_ENABLED"
RERANKER_MODEL_PATH_ENV = "AIOS_BGE_RERANKER_MODEL_PATH"
RERANKER_MODEL_REVISION_ENV = "AIOS_BGE_RERANKER_MODEL_REVISION"
RERANKER_MODEL_CHECKSUM_ENV = "AIOS_BGE_RERANKER_MODEL_CHECKSUM"
DEEP_TIMEOUT_MS_ENV = "AIOS_WORKSPACE_RAG_V2_DEEP_TIMEOUT_MS"
DEEP_RERANK_LIMIT_ENV = "AIOS_WORKSPACE_RAG_V2_DEEP_RERANK_LIMIT"

# This preference deliberately lives next to the local Workspace Chat data,
# not in .env. It lets an owner enable or disable the optional CPU reranker
# from the UI without ever reading, exposing, or editing provider secrets.
DEEP_SEARCH_LOCAL_SETTINGS_FILENAME = "rag_v2_local_settings.json"
DEEP_SEARCH_LOCAL_SETTINGS_SCHEMA_VERSION = "1"
DEEP_SEARCH_LOCAL_SETTINGS_KEY = "deep_search_enabled"

_DEFAULT_RUNTIME_ROOT = Path("local_runs/workspace_chat_rag_v2_canary")
_ALLOWED_PROFILES = frozenset({"bge_m3_hybrid"})
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_SAFE_REASON = re.compile(r"[^a-z0-9_.-]+")
_SEMANTIC_SOURCE_STOP_WORDS = frozenset(
    {
        "cau", "hoi", "che", "do", "hoat", "dong", "nhu", "the", "nao",
        "giai", "thich", "giup", "toi",
        "lam", "sao", "what", "how", "does", "work", "operate", "the",
        "and", "for", "with", "this", "that", "are", "you",
    }
)
# Corpus sources vary substantially in extraction cost; keep every IPC request
# bounded to one document under the existing 90-second fail-closed deadline.
_PREPARATION_BATCH_SIZE = 1


def _deep_search_local_settings_path() -> Path:
    """Return the ignored local settings file used by the Workspace Chat UI."""
    # Import lazily so this adapter remains independent of chat persistence at
    # module import time and in isolated RAG tests.
    from aios_habit.workspace_chat_store import LOCAL_CHAT_DIR

    return Path(LOCAL_CHAT_DIR) / DEEP_SEARCH_LOCAL_SETTINGS_FILENAME


def _load_local_deep_search_override() -> Optional[bool]:
    """Read a user-owned local override, if one has been saved from the UI."""
    settings_path = _deep_search_local_settings_path()
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    enabled = payload.get(DEEP_SEARCH_LOCAL_SETTINGS_KEY)
    return enabled if isinstance(enabled, bool) else None


def get_workspace_chat_deep_search_enabled_preference() -> bool:
    """Return the effective machine-local deep-search preference for the UI."""
    saved_override = _load_local_deep_search_override()
    if saved_override is not None:
        return saved_override
    try:
        return WorkspaceChatRagV2CanaryConfig.from_env().adaptive_enabled
    except (DeploymentManifestError, ValueError):
        return False


def set_workspace_chat_deep_search_enabled(enabled: bool) -> None:
    """Persist a non-secret, machine-local UI preference atomically.

    ``local_cases/`` is ignored by Git, so this records only the user's
    choice on this computer and never changes the repository or .env.
    """
    settings_path = _deep_search_local_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": DEEP_SEARCH_LOCAL_SETTINGS_SCHEMA_VERSION,
        DEEP_SEARCH_LOCAL_SETTINGS_KEY: bool(enabled),
    }
    temporary_path = settings_path.with_suffix(f"{settings_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, settings_path)


@dataclass(frozen=True)
class WorkspaceChatSourceScope:
    """A query-scoped source set that is safe to prepare in the background."""

    sources: Tuple[WorkspaceAIContextSource, ...]
    bounded: bool
    reason: str


@dataclass(frozen=True)
class WorkspaceChatRagV2CanaryConfig:
    """Local retrieval settings loaded from deployment state, env, or tests."""

    enabled: bool = False
    requested_profile: str = "bge_m3_hybrid"
    runtime_root: Path = _DEFAULT_RUNTIME_ROOT
    bge_m3_model_path: Optional[Path] = None
    bge_m3_model_revision: str = ""
    bge_m3_model_checksum: str = ""
    bge_m3_batch_size: int = 1
    bge_m3_max_length: int = 2048
    bge_m3_use_fp16: bool = False
    retrieval_device: str = "cpu"
    fail_closed_on_error: bool = True
    adaptive_enabled: bool = False
    bge_reranker_model_path: Optional[Path] = None
    bge_reranker_model_revision: str = ""
    bge_reranker_model_checksum: str = ""
    policy_version: str = "adaptive-reranking-v1"
    # A CPU-only BGE reranker needs materially longer than the normal Hybrid
    # request budget.  This is used only when reranking was explicitly chosen
    # by the policy or the user, never for the default fast path.
    deep_timeout_ms: int = 300000
    deep_rerank_limit: int = 10

    def __post_init__(self) -> None:
        profile = self.requested_profile.strip()
        if profile not in _ALLOWED_PROFILES:
            raise ValueError(f"requested_profile must be one of {sorted(_ALLOWED_PROFILES)}")
        root = Path(self.runtime_root)
        if root == Path("."):
            raise ValueError("runtime_root must be a dedicated directory")
        object.__setattr__(self, "requested_profile", profile)
        object.__setattr__(self, "runtime_root", root)
        if self.bge_m3_batch_size < 1:
            raise ValueError("bge_m3_batch_size must be positive")
        if self.bge_m3_max_length < 1:
            raise ValueError("bge_m3_max_length must be positive")
        if self.bge_m3_model_path is not None:
            object.__setattr__(self, "bge_m3_model_path", Path(self.bge_m3_model_path))
        if self.bge_reranker_model_path is not None:
            object.__setattr__(self, "bge_reranker_model_path", Path(self.bge_reranker_model_path))
        if not 1 <= self.deep_rerank_limit <= 15:
            raise ValueError("deep_rerank_limit must be between 1 and 15")
        if self.adaptive_enabled and not 15000 <= self.deep_timeout_ms <= 300000:
            raise ValueError("deep_timeout_ms must be between 15000 and 300000")


    @classmethod
    def from_env(
        cls,
        env: Optional[Mapping[str, str]] = None,
    ) -> "WorkspaceChatRagV2CanaryConfig":
        if env is None:
            try:
                from aios_habit.workspace_paths import load_env_file
                load_env_file()
            except Exception:
                pass
        values = os.environ if env is None else env
        # Explicit env mappings are used by tests and diagnostic tools, so
        # they must remain deterministic. Only the live application honours
        # a preference explicitly saved through its local UI.
        local_deep_search_override = (
            _load_local_deep_search_override() if env is None else None
        )
        try:
            deployment = load_workspace_chat_rag_v2_deployment(
                env=values,
                require_activated=True,
            )
        except DeploymentManifestError:
            # An invalid activated manifest must never silently become a
            # production deployment.  The only permitted recovery is an
            # owner-enabled local pilot, which is intentionally separate from
            # the historical canary flag and visibly remains unqualified.
            if not _env_bool(values.get(LOCAL_PILOT_ENABLED_ENV), default=False):
                raise
            deployment = None
        if deployment is not None:
            return cls(
                enabled=True,
                requested_profile=deployment.requested_profile,
                runtime_root=deployment.runtime_root,
                bge_m3_model_path=deployment.model_path,
                bge_m3_model_revision=deployment.model_revision,
                bge_m3_model_checksum=deployment.model_checksum,
                retrieval_device=deployment.retrieval_device,
                fail_closed_on_error=True,
                adaptive_enabled=(
                    local_deep_search_override
                    if local_deep_search_override is not None
                    else bool(getattr(deployment, "adaptive_enabled", False))
                ),
                bge_reranker_model_path=getattr(deployment, "reranker_path", None),
                bge_reranker_model_revision=str(getattr(deployment, "reranker_revision", "") or ""),
                bge_reranker_model_checksum=str(getattr(deployment, "reranker_checksum", "") or ""),
                policy_version=str(getattr(deployment, "policy_version", "adaptive-reranking-v1") or "adaptive-reranking-v1"),
                deep_timeout_ms=int(getattr(deployment, "deep_timeout_ms", 300000)),
                deep_rerank_limit=int(getattr(deployment, "deep_rerank_limit", 10)),
            )


        model_path = str(values.get(BGE_MODEL_PATH_ENV, "") or "").strip()
        reranker_path = str(values.get(RERANKER_MODEL_PATH_ENV, "") or "").strip()
        adaptive_enabled = (
            local_deep_search_override
            if local_deep_search_override is not None
            else _env_bool(values.get(ADAPTIVE_ENABLED_ENV), default=False)
        )
        return cls(
            enabled=_env_bool(values.get(CANARY_ENABLED_ENV), default=False),
            requested_profile=str(
                values.get(PROFILE_ENV, "bge_m3_hybrid") or "bge_m3_hybrid"
            ),
            runtime_root=Path(str(values.get(RUNTIME_ROOT_ENV, _DEFAULT_RUNTIME_ROOT))),
            bge_m3_model_path=Path(model_path) if model_path else None,
            bge_m3_model_revision=str(
                values.get(BGE_MODEL_REVISION_ENV, "") or ""
            ).strip(),
            bge_m3_model_checksum=str(
                values.get(BGE_MODEL_CHECKSUM_ENV, "") or ""
            ).strip(),
            retrieval_device=str(
                values.get(RETRIEVAL_DEVICE_ENV, "cpu") or "cpu"
            ).strip(),
            fail_closed_on_error=True,
            adaptive_enabled=adaptive_enabled,
            bge_reranker_model_path=Path(reranker_path) if reranker_path else None,
            bge_reranker_model_revision=str(
                values.get(RERANKER_MODEL_REVISION_ENV, "") or ""
            ).strip(),
            bge_reranker_model_checksum=str(
                values.get(RERANKER_MODEL_CHECKSUM_ENV, "") or ""
            ).strip(),
            deep_timeout_ms=int(
                values.get(DEEP_TIMEOUT_MS_ENV, 300000) or 300000
            ),
            deep_rerank_limit=int(
                values.get(DEEP_RERANK_LIMIT_ENV, 10) or 10
            ),
        )


@dataclass(frozen=True)
class WorkspaceChatDeepSearchAvailability:
    """Truthful availability state for the optional local reranking lane."""

    available: bool
    reason: str = ""


def get_workspace_chat_deep_search_availability(
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> WorkspaceChatDeepSearchAvailability:
    """Report whether the user-selectable deep-search promise can be honoured.

    Source embedding readiness is intentionally not part of this check: a
    source can be fully indexed for normal BGE-M3 hybrid search while the
    separately pinned reranker is disabled or unavailable.  The UI must not
    blame document preparation for that configuration state.
    """
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except (DeploymentManifestError, ValueError):
        return WorkspaceChatDeepSearchAvailability(False, "retrieval_unavailable")

    if not resolved.enabled:
        return WorkspaceChatDeepSearchAvailability(False, "retrieval_disabled")
    if not resolved.adaptive_enabled:
        return WorkspaceChatDeepSearchAvailability(False, "deep_disabled")
    reranker_path = resolved.bge_reranker_model_path
    if reranker_path is None:
        return WorkspaceChatDeepSearchAvailability(False, "reranker_not_configured")
    if not reranker_path.is_dir():
        return WorkspaceChatDeepSearchAvailability(False, "reranker_missing")
    if not resolved.bge_reranker_model_revision or not resolved.bge_reranker_model_checksum:
        return WorkspaceChatDeepSearchAvailability(False, "reranker_pin_missing")
    return WorkspaceChatDeepSearchAvailability(True)


@dataclass(frozen=True)
class _RuntimeEntry:
    pipeline: RagV2DevPipeline
    lock: threading.RLock


_RUNTIME_CACHE: dict[str, _RuntimeEntry] = {}
_RUNTIME_CACHE_LOCK = threading.RLock()


def _env_bool(value: Optional[str], *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().casefold() in _TRUE_VALUES


_ALLOWED_DEGRADED_REASONS = {
    "reranker_backend_failed",
    "reranker_oom",
    "reranker_backend_timeout",
    "reranker_backend_unavailable",
    "reranker_circuit_open",
    "reranker_disabled_by_policy",
    "reranker_model_missing",
    "reranker_device_error",
}

# Deep search first forms a wider local candidate pool, then keeps the normal
# evidence-pack size.  This is deliberately independent of the number of
# snippets shown to the provider; otherwise reranking a 10-item final pack
# cannot discover a better eleventh item.
_DEEP_RERANK_CANDIDATE_WINDOW = 30


def _sanitize_degraded_reason(reason: Any) -> str:
    """Sanitize degraded_reason against an allowlist to prevent secret or path leaks."""
    if not reason:
        return ""
    code = str(reason).strip().casefold()
    if code in _ALLOWED_DEGRADED_REASONS:
        return code
    return "reranker_backend_failed"


def _safe_reason(error: BaseException | str) -> str:
    """Return a bounded reason code without paths, content, or exception text."""
    raw = str(error) if isinstance(error, SemanticBackendError) else ""
    if raw.startswith("bge_worker_"):
        name = raw
    else:
        name = error if isinstance(error, str) else type(error).__name__
    folded = _SAFE_REASON.sub("_", str(name).casefold()).strip("_")
    return folded[:80] or "unknown_error"



def sanitize_citation_title(title: str) -> str:
    """Return a citation title without exposing an absolute filesystem path."""
    if not title:
        return "unnamed-source"
    value = str(title)
    return Path(value).name if "\\" in value or "/" in value else value


def _runtime_key(config: WorkspaceChatRagV2CanaryConfig, profile: str) -> str:
    payload = {
        "runtime_root": str(config.runtime_root.resolve()),
        "profile": profile,
        "model_path": (
            str(config.bge_m3_model_path.resolve()) if config.bge_m3_model_path else ""
        ),
        "model_revision": config.bge_m3_model_revision,
        "model_checksum": config.bge_m3_model_checksum,
        "device": config.retrieval_device,
        "batch_size": config.bge_m3_batch_size,
        "max_length": config.bge_m3_max_length,
        "use_fp16": config.bge_m3_use_fp16,
        "reranker_path": str(config.bge_reranker_model_path.resolve()) if config.bge_reranker_model_path else "",
        "reranker_revision": config.bge_reranker_model_revision,
        "reranker_checksum": config.bge_reranker_model_checksum,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pipeline_config(
    config: WorkspaceChatRagV2CanaryConfig,
    profile: str,
    *,
    read_only: bool = False,
    include_reranker: bool = False,
    collection_id: str | None = None,
) -> RagV2DevConfig:
    from aios_habit.workspace_chat_store import collection_runtime_layout

    profile_root = config.runtime_root / profile
    collection_root, index_filename = collection_runtime_layout(collection_id, profile_root)
    if not read_only:
        collection_root.mkdir(parents=True, exist_ok=True)
    common = {
        "runtime_root": collection_root,
        "index_filename": index_filename,
        "index_read_only": read_only,
        "ensure_embeddings_on_open": not read_only,
        "allowed_privacy_labels": (
            "local_only",
            "confidential",
            "cloud_safe",
            "public",
        ),
        "enable_network": False,
        "enable_provider_synthesis": False,
        "sqlite_check_same_thread": False,
    }
    if config.bge_m3_model_path is None:
        raise SemanticBackendUnavailable("pinned_bge_m3_model_path_missing")
    if not config.bge_m3_model_revision:
        raise SemanticBackendUnavailable("pinned_bge_m3_model_revision_missing")
    if not config.bge_m3_model_checksum:
        raise SemanticBackendUnavailable("pinned_bge_m3_model_checksum_missing")
    return RagV2DevConfig(
        # Deep is not merely a reordered Fast answer.  It reranks a wider
        # candidate window and retains adjacent local context for the winning
        # procedure chunks, so setup, execution, and safety steps can travel
        # together to the answer model.
        retrieval_profile=(
            "bge_m3_hybrid_rerank_expand"
            if include_reranker
            else "bge_m3_hybrid"
        ),
        strict_semantic=True,
        bge_m3_model_path=config.bge_m3_model_path,
        bge_m3_model_revision=config.bge_m3_model_revision,
        bge_m3_model_checksum=config.bge_m3_model_checksum,
        bge_m3_batch_size=config.bge_m3_batch_size,
        bge_m3_max_length=config.bge_m3_max_length,
        bge_m3_use_fp16=config.bge_m3_use_fp16,
        # The CPU reranker is intentionally cold until Deep is requested.
        # Loading it during Auto or source preparation turns every ordinary
        # question into a 50+ second model start.
        bge_reranker_model_path=(
            config.bge_reranker_model_path if include_reranker else None
        ),
        bge_reranker_model_revision=(
            config.bge_reranker_model_revision if include_reranker else ""
        ),
        bge_reranker_model_checksum=(
            config.bge_reranker_model_checksum if include_reranker else ""
        ),
        rerank_limit=(
            max(config.deep_rerank_limit, _DEEP_RERANK_CANDIDATE_WINDOW)
            if include_reranker
            else config.deep_rerank_limit
        ),
        retrieval_device=config.retrieval_device,
        **common,
    )



def _get_runtime(
    config: WorkspaceChatRagV2CanaryConfig,
    profile: str,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline],
) -> _RuntimeEntry:
    key = _runtime_key(config, profile)
    with _RUNTIME_CACHE_LOCK:
        existing = _RUNTIME_CACHE.get(key)
        if existing is not None:
            return existing
        pipeline = pipeline_factory(_pipeline_config(config, profile, read_only=True))
        entry = _RuntimeEntry(pipeline=pipeline, lock=threading.RLock())
        _RUNTIME_CACHE[key] = entry
        return entry


def close_workspace_chat_rag_v2_runtimes() -> None:
    """Close cached SQLite indexes and subprocess worker; used by orderly shutdown and tests."""
    global _PREPARATION_EXECUTOR
    with _PREPARATION_LOCK:
        executor = _PREPARATION_EXECUTOR
        _PREPARATION_EXECUTOR = None
    if executor is not None:
        executor.shutdown(wait=True)
    with _PREPARATION_LOCK:
        _PREPARATION_REGISTRY.clear()
    _SUBPROCESS_CLIENT.close()
    with _RUNTIME_CACHE_LOCK:
        entries = tuple(_RUNTIME_CACHE.values())
        _RUNTIME_CACHE.clear()
    for entry in entries:
        with entry.lock:
            entry.pipeline.close()
    _document_id.cache_clear()
    _source_fingerprint.cache_clear()


@functools.lru_cache(maxsize=4096)
def _document_id(source: WorkspaceAIContextSource) -> str:
    """Identify a library document by extracted text, not per-machine source id.

    Empty text cannot be matched across machines, so it stays local to
    ``source_scope:source_id``. Filename is never part of the identity.
    """
    text_bytes = (source.text or "").strip().encode("utf-8")
    if text_bytes:
        return f"wsc-{hashlib.sha256(text_bytes).hexdigest()[:24]}"
    identity = f"{source.source_scope}:{source.source_id}".encode("utf-8")
    return f"wsc-{hashlib.sha256(identity).hexdigest()[:24]}"


def _privacy_labels(source: WorkspaceAIContextSource) -> Tuple[str, ...]:
    label = (source.privacy_label or "").strip().casefold()
    if label in {"cloud_allowed", "cloud_safe", "machine_only", "normal"}:
        return ("cloud_safe",)
    if label == "public":
        return ("public",)
    if label == "confidential":
        return ("confidential",)
    return ("local_only",)


@functools.lru_cache(maxsize=4096)
def _source_fingerprint(source: WorkspaceAIContextSource) -> str:
    doc_id = _document_id(source)
    text_bytes = (source.text or "").strip().encode("utf-8")
    content_hash = hashlib.sha256(text_bytes).hexdigest()[:16]
    privacy = (source.privacy_label or "").strip().casefold()
    return f"{doc_id}:{content_hash}:{privacy}"


def _fold_semantic_terms(value: str) -> tuple[str, ...]:
    """Return stable, accent-insensitive local query terms for source gating."""
    folded = unicodedata.normalize("NFD", str(value or "").casefold())
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    folded = folded.replace("đ", "d")
    return tuple(re.findall(r"[a-z0-9]+", folded))


def _select_semantic_candidate_sources(
    question: str,
    sources: Tuple[WorkspaceAIContextSource, ...],
    *,
    limit: int = 3,
) -> Tuple[WorkspaceAIContextSource, ...]:
    """Narrow costly semantic preparation only when local lexical evidence is clear.

    This does not synthesize an answer or hide a source from a weak query: if
    the question has fewer than two specific terms, the complete source set is
    retained.  A precise operational question such as ``Manual Matecon ACR``
    instead prepares only the few documents that actually contain those terms.
    """
    terms = tuple(
        term for term in _fold_semantic_terms(question)
        if (len(term) >= 3 and term not in _SEMANTIC_SOURCE_STOP_WORDS)
    )
    unique_terms = tuple(dict.fromkeys(terms))
    if len(unique_terms) < 2:
        return sources

    manual_requested = "manual" in unique_terms
    matecon_requested = "matecon" in unique_terms
    ranked: list[tuple[int, int, WorkspaceAIContextSource]] = []
    for ordinal, source in enumerate(sources):
        haystack = set(_fold_semantic_terms(f"{source.title}\n{source.text}"))
        matched = sum(term in haystack for term in unique_terms)
        if matched >= 2:
            score = matched
            # The Vietnamese manual says "thủ công", while operators often
            # ask using the English UI label "Manual".  Treat them as the
            # same local retrieval concept, without expanding the answer.
            if manual_requested and (
                "manual" in haystack or {"thu", "cong"}.issubset(haystack)
            ):
                score += 1
            raw_title = str(source.title or "").casefold()
            # Prefer a source whose title names the requested system.  The
            # Japanese product label is deliberately included because the
            # authoritative Matecon manual is named that way.
            if matecon_requested and (
                "matecon" in raw_title or "マテコン" in raw_title
            ):
                score += 2
            if str(source.source_type or "").casefold() == "pdf":
                score += 1
            ranked.append((score, -ordinal, source))
    if not ranked:
        return sources
    ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
    best_score = ranked[0][0]
    return tuple(item[2] for item in ranked if item[0] == best_score)[:limit]


def select_workspace_chat_preparation_scope(
    question: str,
    sources: Tuple[WorkspaceAIContextSource, ...],
    *,
    limit: int = 3,
) -> WorkspaceChatSourceScope:
    """Select a small source set or explicitly refuse broad auto-preparation.

    Retrieval can safely inspect all already-ready sources.  Background
    embedding is different: silently scheduling a whole notebook from a vague
    question makes a normal chat action unexpectedly expensive.  The UI uses
    this contract to request a narrower question instead.
    """
    source_tuple = tuple(sources)
    selected = _select_semantic_candidate_sources(question, source_tuple, limit=limit)
    if len(source_tuple) <= limit:
        return WorkspaceChatSourceScope(selected, True, "small_source_set")

    terms = tuple(
        term for term in _fold_semantic_terms(question)
        if len(term) >= 3 and term not in _SEMANTIC_SOURCE_STOP_WORDS
    )
    if len(tuple(dict.fromkeys(terms))) < 2:
        return WorkspaceChatSourceScope((), False, "question_too_broad")
    if len(selected) > limit or len(selected) == len(source_tuple):
        return WorkspaceChatSourceScope((), False, "no_narrow_source_match")
    return WorkspaceChatSourceScope(selected, True, "matched_sources")


def _durable_semantic_coverage_ready(
    source: WorkspaceAIContextSource,
    config: WorkspaceChatRagV2CanaryConfig,
) -> bool:
    """Check an existing local BGE index without loading the model again."""
    from aios_habit.workspace_chat_store import collection_runtime_layout

    collection_id = _collection_id_for_sources((source,))
    profile_root = config.runtime_root / config.requested_profile
    collection_root, index_filename = collection_runtime_layout(collection_id, profile_root)
    index_path = collection_root / index_filename
    if not index_path.is_file() or not config.bge_m3_model_revision:
        return False
    document_id = _document_id(source)
    try:
        uri = f"file:{index_path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            retrievable = int(connection.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id=? AND retrievable=1",
                (document_id,),
            ).fetchone()[0])
            if retrievable <= 0:
                return False
            dense = int(connection.execute(
                """SELECT COUNT(DISTINCT c.chunk_id)
                   FROM chunks c JOIN chunk_embeddings e ON e.chunk_id=c.chunk_id
                   WHERE c.document_id=? AND c.retrievable=1
                     AND e.model_id='BAAI/bge-m3' AND e.model_revision=?""",
                (document_id, config.bge_m3_model_revision),
            ).fetchone()[0])
            sparse = int(connection.execute(
                """SELECT COUNT(DISTINCT c.chunk_id)
                   FROM chunks c
                   JOIN chunk_embeddings d ON d.chunk_id=c.chunk_id
                   JOIN chunk_sparse_embeddings s
                     ON s.chunk_id=c.chunk_id AND s.model_fingerprint=d.model_fingerprint
                   WHERE c.document_id=? AND c.retrievable=1
                     AND d.model_id='BAAI/bge-m3' AND d.model_revision=?""",
                (document_id, config.bge_m3_model_revision),
            ).fetchone()[0])
            return dense == retrievable and sparse == retrievable
        finally:
            connection.close()
    except (OSError, RuntimeError, sqlite3.Error):
        return False


def _semantic_readiness(
    sources: Sequence[WorkspaceAIContextSource],
    config: WorkspaceChatRagV2CanaryConfig,
) -> tuple[str, str]:
    """Check readiness of sources for semantic retrieval."""
    if not config.enabled:
        return "unavailable", "bge_m3_not_enabled"

    db_path = _get_ledger_db_path(config)
    ledger_rows = _load_all_ledger_rows(db_path) if db_path.is_file() else {}

    with _PREPARATION_LOCK:
        for source in sources:
            if not (source.text or "").strip():
                continue
            key = _preparation_key(config, source)
            entry = _PREPARATION_REGISTRY.get(key)
            if entry is not None and entry.get("status") == _PREPARATION_READY_STATE:
                continue

            row = ledger_rows.get((source.source_scope, source.source_id))
            if (
                row is not None
                and row.state == PREP_STATE_READY
                and row.source_fingerprint == _source_fingerprint(source)
                and row.model_revision == config.bge_m3_model_revision
                and _durable_semantic_coverage_ready(source, config)
            ):
                _PREPARATION_REGISTRY[key] = _preparation_entry(config, source, _PREPARATION_READY_STATE)
                continue

            if _durable_semantic_coverage_ready(source, config):
                _PREPARATION_REGISTRY[key] = _preparation_entry(config, source, _PREPARATION_READY_STATE)
                continue

            if entry is not None:
                st = entry.get("status", "pending")
                return st, entry.get("reason", "")
            if row is not None:
                return row.state, row.last_error
            return "pending", ""

    return _PREPARATION_READY_STATE, ""




def _preparation_key(
    config: WorkspaceChatRagV2CanaryConfig,
    source: WorkspaceAIContextSource,
) -> str:
    return f"{_runtime_key(config, config.requested_profile)}:{_source_fingerprint(source)}"


def _preparation_entry(
    config: WorkspaceChatRagV2CanaryConfig,
    source: WorkspaceAIContextSource,
    status: str,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "status": status,
        "runtime_key": _runtime_key(config, config.requested_profile),
        "document_id": _document_id(source),
        "source_id": source.source_id,
        "updated_at": time.time(),
        **metadata,
    }


def _preparation_batches(
    specs: tuple[SourceSpec, ...],
    *,
    batch_size: int = _PREPARATION_BATCH_SIZE,
) -> tuple[tuple[SourceSpec, ...], ...]:
    """Partition preparation deterministically into independently bounded IPC calls."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    return tuple(
        specs[offset : offset + batch_size]
        for offset in range(0, len(specs), batch_size)
    )


def _aggregate_preparation_reports(reports: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Combine safe per-batch worker counters without exposing source details."""
    rows = tuple(reports)
    if not rows:
        return {
            "converted_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "indexed_chunk_count": 0,
        }
    return {
        "converted_count": sum(int(row.get("converted_count", 0)) for row in rows),
        "skipped_count": sum(int(row.get("skipped_count", 0)) for row in rows),
        "failed_count": sum(int(row.get("failed_count", 0)) for row in rows),
        # The worker reports index cardinality after each incremental batch.
        "indexed_chunk_count": int(rows[-1].get("indexed_chunk_count", 0)),
    }


def _safe_init_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only phase timing and model identity safe for external telemetry."""
    readiness = report.get("readiness")
    safe_readiness: dict[str, Any] = {}
    if isinstance(readiness, Mapping):
        for key in ("protocol_version", "retrieval_profile"):
            value = readiness.get(key)
            if isinstance(value, str):
                safe_readiness[key] = value
        model = readiness.get("model")
        if isinstance(model, Mapping):
            for key in ("model_id", "revision", "fingerprint", "cache_identity"):
                value = model.get(key)
                if isinstance(value, str):
                    safe_readiness.setdefault("model", {})[key] = value
    return {
        "status": "ok",
        "reused": bool(report.get("reused", False)),
        "init_latency_ms": float(report.get("init_latency_ms", 0.0)),
        "readiness": safe_readiness,
    }


def _batch_failure_reason(batch_ordinal: int, batch: tuple[SourceSpec, ...], error: BaseException) -> str:
    """Return a deterministic diagnostic identifier without a filename, path, or text."""
    document_ids = "|".join(spec.document_id for spec in batch)
    opaque_document_id = hashlib.sha256(document_ids.encode("utf-8")).hexdigest()[:12]
    return f"preparation_batch_{batch_ordinal:03d}_document_{opaque_document_id}_{_safe_reason(error)}"


def initialize_workspace_chat_rag_v2_worker(
    config: WorkspaceChatRagV2CanaryConfig,
    *,
    timeout_s: float | None = None,
    pipe_config: RagV2DevConfig | None = None,
) -> dict[str, Any]:
    """Initialize the activated semantic worker before corpus materialization.

    Loading BGE-M3 must happen while the parent process remains lightweight. This
    isolates the bounded model-startup SLA from potentially expensive document
    extraction and preserves a phase-specific, fail-closed readiness error.
    """
    profile = config.requested_profile
    if not profile.startswith("bge_m3_"):
        return {"status": "not_required"}
    try:
        effective_config = pipe_config or _pipeline_config(config, profile)
        return _safe_init_report(
            _SUBPROCESS_CLIENT.initialize_worker(
                effective_config,
                **({"timeout_s": float(timeout_s)} if timeout_s is not None else {}),
            )
        )
    except Exception as exc:
        raise RuntimeError(f"preparation_init_{_safe_reason(exc)}") from exc


def _collection_id_for_sources(context_sources: Iterable[WorkspaceAIContextSource]) -> str | None:
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID, SOURCE_SCOPE_NOTEBOOK
    from aios_habit.workspace_chat_store import (
        load_collection,
        resolve_collection_id_from_notebook_source_id,
    )

    for source in context_sources:
        if getattr(source, "source_scope", "") != SOURCE_SCOPE_NOTEBOOK:
            continue
        return resolve_collection_id_from_notebook_source_id(source.source_id)
    default = load_collection(DEFAULT_COLLECTION_ID)
    if default is not None and str(default.storage_root or "").strip():
        return DEFAULT_COLLECTION_ID
    return None


def prepare_workspace_chat_sources(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline] = RagV2DevPipeline,
    completed_document_ids: Iterable[str] = (),
    progress_callback: Callable[[Mapping[str, int]], None] | None = None,
    source_timeout_s: float | None = None,
) -> dict[str, Any]:
    """Prepare sources outside the user-initiated query path.

    ``completed_document_ids`` is deliberately an opaque, caller-verified
    resume boundary.  It is used by the benchmark stager only; UI scheduling
    retains its in-process behavior.  Progress is emitted after a source has
    committed, never while source text is being materialized or embedded.
    """
    resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    sources = tuple(s for s in context_sources if (s.text or "").strip())
    if not sources:
        return {"status": "ok", "prepared_count": 0, "latency_ms": 0.0}
    if source_timeout_s is not None and float(source_timeout_s) <= 0:
        raise ValueError("source_timeout_s must be positive")

    profile = resolved.requested_profile
    pipe_config = _pipeline_config(
        resolved,
        profile,
        collection_id=_collection_id_for_sources(sources),
    )
    started = time.perf_counter()
    with _PREPARATION_LOCK:
        for source in sources:
            _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                _preparation_entry(resolved, source, "processing")
            )

    writer_lease = None
    try:
        init_report: dict[str, Any] | None = None
        use_semantic_worker = (
            profile.startswith("bge_m3_") and pipeline_factory is RagV2DevPipeline
        )
        # Establish the production semantic worker while the parent only holds
        # caller-provided references; extraction/materialization can be slow and
        # memory-intensive. Injected pipeline factories own their lifecycle.
        if use_semantic_worker:
            from aios_habit.workspace_chat_store import LibraryWriterLease

            writer_lease = LibraryWriterLease(Path(pipe_config.runtime_root))
            if not writer_lease.acquire():
                raise RuntimeError("library_writer_busy")
            init_report = initialize_workspace_chat_rag_v2_worker(
                resolved,
                pipe_config=pipe_config,
            )
        specs, originals = _materialize_sources(sources, resolved.runtime_root)
        if not specs:
            return {"status": "ok", "prepared_count": 0, "latency_ms": 0.0}
        completed_ids = {str(document_id) for document_id in completed_document_ids}
        known_ids = set(originals)
        if completed_ids - known_ids:
            raise ValueError("completed_document_ids_unknown")
        if completed_ids:
            with _PREPARATION_LOCK:
                for document_id in completed_ids:
                    source = originals[document_id]
                    _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                        _preparation_entry(
                            resolved,
                            source,
                            _PREPARATION_READY_STATE,
                            resumed_from_verified_checkpoint=True,
                        )
                    )
        if use_semantic_worker:
            pending_specs = tuple(spec for spec in specs if spec.document_id not in completed_ids)
            batches = _preparation_batches(pending_specs)
            batch_reports = []
            completed_count = len(completed_ids)
            for batch_ordinal, batch in enumerate(batches, start=1):
                try:
                    for spec in batch:
                        kwargs: dict[str, float] = {}
                        if source_timeout_s is not None:
                            kwargs["source_timeout_s"] = float(source_timeout_s)
                        source_report = _SUBPROCESS_CLIENT.prepare_staged_source(
                            spec,
                            pipe_config,
                            group_size=4,
                            **kwargs,
                        )
                        batch_reports.append(source_report)
                        completed_count += 1
                        source = originals[spec.document_id]
                        source_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
                        with _PREPARATION_LOCK:
                            _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                                _preparation_entry(
                                    resolved,
                                    source,
                                    _PREPARATION_READY_STATE,
                                    latency_ms=source_latency_ms,
                                    indexed_chunk_count=int(
                                        source_report.get("indexed_chunk_count", 0)
                                    ),
                                )
                            )
                        if progress_callback is not None:
                            progress_callback({
                                "document_id": spec.document_id,
                                "completed_count": completed_count,
                                "total_sources": len(specs),
                            })
                except Exception as exc:
                    raise RuntimeError(
                        _batch_failure_reason(batch_ordinal, batch, exc)
                    ) from exc
            report = _aggregate_preparation_reports(batch_reports)
            report["batch_count"] = len(batches)
            report["batch_size"] = _PREPARATION_BATCH_SIZE
            report["initialization"] = init_report
            if completed_ids:
                report["resumed_count"] = len(completed_ids)
        else:
            entry = _get_runtime(resolved, profile, pipeline_factory)
            with entry.lock:
                rep = entry.pipeline.ingest(specs)
                if rep.failed_count or rep.unsupported_count or rep.empty_count:
                    raise RuntimeError("rag_v2_ingestion_incomplete")
                report = {
                    "converted_count": rep.converted_count,
                    "skipped_count": rep.skipped_count,
                    "failed_count": rep.failed_count,
                    "indexed_chunk_count": rep.indexed_chunk_count,
                    "batch_count": 1,
                    "batch_size": len(specs),
                }

        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        indexed_chunk_count = int(report.get("indexed_chunk_count", 0))
        with _PREPARATION_LOCK:
            for source in sources:
                _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                    _preparation_entry(
                        resolved,
                        source,
                        _PREPARATION_READY_STATE,
                        latency_ms=latency_ms,
                        indexed_chunk_count=indexed_chunk_count,
                    )
                )
        return {
            "status": "ok",
            "prepared_count": len(sources),
            "resumed_count": len(completed_ids),
            "latency_ms": latency_ms,
            "report": report,
        }
    except Exception as exc:
        busy = str(exc) == "library_writer_busy"
        reason = "library_writer_busy" if busy else _safe_reason(exc)
        status = "pending" if busy else "failed"
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        with _PREPARATION_LOCK:
            for source in sources:
                key = _preparation_key(resolved, source)
                existing = _PREPARATION_REGISTRY.get(key)
                if existing and existing.get("status") == _PREPARATION_READY_STATE:
                    continue
                _PREPARATION_REGISTRY[key] = _preparation_entry(
                    resolved,
                    source,
                    status,
                    reason=reason,
                    latency_ms=latency_ms,
                )
        LOGGER.warning(
            "Background preparation failed for %d sources: %s",
            len(sources),
            reason,
        )
        raise
    finally:
        if writer_lease is not None:
            writer_lease.release()


def _get_ledger_db_path(config: WorkspaceChatRagV2CanaryConfig) -> Path:
    config.runtime_root.mkdir(parents=True, exist_ok=True)
    return config.runtime_root / "workspace_chat.sqlite"


def _init_preparation_ledger_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        with conn:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {PREPARATION_LEDGER_TABLE} (
                    source_scope TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_fingerprint TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    model_revision TEXT NOT NULL,
                    state TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT '{PREP_PRIORITY_NORMAL}',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    document_id TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (source_scope, source_id)
                )"""
            )
            conn.execute(
                f"""CREATE INDEX IF NOT EXISTS idx_prep_ledger_state_priority
                    ON {PREPARATION_LEDGER_TABLE} (state, priority, updated_at)"""
            )
            # Stale processing recovery on startup / init
            now = time.time()
            conn.execute(
                f"""UPDATE {PREPARATION_LEDGER_TABLE}
                    SET state = '{PREP_STATE_PENDING}', updated_at = ?
                    WHERE state = '{PREP_STATE_PROCESSING}'""",
                (now,),
            )
    finally:
        conn.close()


def _load_ledger_row(db_path: Path, source_scope: str, source_id: str) -> SourcePreparationLedgerRow | None:
    if not db_path.is_file():
        return None
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cur = conn.execute(
            f"""SELECT source_scope, source_id, source_fingerprint, model_id, model_revision,
                       state, priority, attempt_count, last_error, document_id, created_at, updated_at
                FROM {PREPARATION_LEDGER_TABLE}
                WHERE source_scope = ? AND source_id = ?""",
            (source_scope, source_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return SourcePreparationLedgerRow(*row)
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _load_all_ledger_rows(db_path: Path) -> dict[tuple[str, str], SourcePreparationLedgerRow]:
    if not db_path.is_file():
        return {}
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cur = conn.execute(
            f"""SELECT source_scope, source_id, source_fingerprint, model_id, model_revision,
                       state, priority, attempt_count, last_error, document_id, created_at, updated_at
                FROM {PREPARATION_LEDGER_TABLE}"""
        )
        rows = {}
        for r in cur.fetchall():
            row_obj = SourcePreparationLedgerRow(*r)
            rows[(row_obj.source_scope, row_obj.source_id)] = row_obj
        return rows
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


def _upsert_ledger_row(db_path: Path, row: SourcePreparationLedgerRow) -> None:
    _init_preparation_ledger_db(db_path)
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        with conn:
            conn.execute(
                f"""INSERT INTO {PREPARATION_LEDGER_TABLE} (
                    source_scope, source_id, source_fingerprint, model_id, model_revision,
                    state, priority, attempt_count, last_error, document_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_scope, source_id) DO UPDATE SET
                    source_fingerprint=excluded.source_fingerprint,
                    model_id=excluded.model_id,
                    model_revision=excluded.model_revision,
                    state=excluded.state,
                    priority=excluded.priority,
                    attempt_count=excluded.attempt_count,
                    last_error=excluded.last_error,
                    document_id=excluded.document_id,
                    updated_at=excluded.updated_at""",
                (
                    row.source_scope,
                    row.source_id,
                    row.source_fingerprint,
                    row.model_id,
                    row.model_revision,
                    row.state,
                    row.priority,
                    row.attempt_count,
                    row.last_error,
                    row.document_id,
                    row.created_at,
                    row.updated_at,
                ),
            )
    finally:
        conn.close()


def _claim_next_preparation_item(db_path: Path, model_id: str, model_revision: str) -> SourcePreparationLedgerRow | None:
    if not db_path.is_file():
        return None
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        with conn:
            # Check if there is already a processing item (strict single CPU worker)
            cur = conn.execute(
                f"""SELECT source_scope, source_id, source_fingerprint, model_id, model_revision,
                           state, priority, attempt_count, last_error, document_id, created_at, updated_at
                    FROM {PREPARATION_LEDGER_TABLE}
                    WHERE state = '{PREP_STATE_PROCESSING}'
                    LIMIT 1"""
            )
            existing_proc = cur.fetchone()
            if existing_proc:
                return SourcePreparationLedgerRow(*existing_proc)

            cur = conn.execute(
                f"""SELECT source_scope, source_id, source_fingerprint, model_id, model_revision,
                           state, priority, attempt_count, last_error, document_id, created_at, updated_at
                    FROM {PREPARATION_LEDGER_TABLE}
                    WHERE state = '{PREP_STATE_PENDING}' AND model_id = ? AND model_revision = ?
                    ORDER BY CASE priority
                        WHEN '{PREP_PRIORITY_INTERACTIVE}' THEN 0
                        WHEN '{PREP_PRIORITY_NORMAL}' THEN 1
                        WHEN '{PREP_PRIORITY_BACKFILL}' THEN 2
                        ELSE 3 END ASC,
                        updated_at ASC
                    LIMIT 1""",
                (model_id, model_revision),
            )
            row = cur.fetchone()
            if not row:
                return None

            now = time.time()
            source_scope, source_id = row[0], row[1]
            cur_upd = conn.execute(
                f"""UPDATE {PREPARATION_LEDGER_TABLE}
                    SET state = '{PREP_STATE_PROCESSING}',
                        attempt_count = attempt_count + 1,
                        updated_at = ?
                    WHERE source_scope = ? AND source_id = ? AND state = '{PREP_STATE_PENDING}'""",
                (now, source_scope, source_id),
            )
            if cur_upd.rowcount == 1:
                return SourcePreparationLedgerRow(
                    source_scope=row[0],
                    source_id=row[1],
                    source_fingerprint=row[2],
                    model_id=row[3],
                    model_revision=row[4],
                    state=PREP_STATE_PROCESSING,
                    priority=row[6],
                    attempt_count=row[7] + 1,
                    last_error=row[8],
                    document_id=row[9],
                    created_at=row[10],
                    updated_at=now,
                )
            return None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _commit_preparation_result(
    db_path: Path,
    source_scope: str,
    source_id: str,
    state: str,
    error_reason: str = "",
) -> None:
    if not db_path.is_file():
        return
    now = time.time()
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        with conn:
            conn.execute(
                f"""UPDATE {PREPARATION_LEDGER_TABLE}
                    SET state = ?, last_error = ?, updated_at = ?
                    WHERE source_scope = ? AND source_id = ?""",
                (state, error_reason, now, source_scope, source_id),
            )
    except sqlite3.Error:
        pass
    finally:
        conn.close()


def _delete_ledger_rows(db_path: Path, source_keys: Iterable[tuple[str, str]]) -> int:
    if not db_path.is_file():
        return 0
    keys = tuple(source_keys)
    if not keys:
        return 0
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        with conn:
            deleted = 0
            for scope, sid in keys:
                cur = conn.execute(
                    f"DELETE FROM {PREPARATION_LEDGER_TABLE} WHERE source_scope = ? AND source_id = ?",
                    (scope, sid),
                )
                deleted += cur.rowcount
            return deleted
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def get_workspace_chat_preparation_summary(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> dict[str, Any]:
    """Return compact aggregate progress and per-source readiness for UI."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        resolved = None

    sources = tuple(s for s in context_sources if (s.text or "").strip())
    total_count = len(sources)
    if resolved is None or not resolved.enabled:
        statuses = {
            f"{s.source_scope}:{s.source_id}": "unavailable"
            for s in context_sources
        }
        return {
            "total": total_count,
            "ready": 0,
            "processing": 0,
            "pending": 0,
            "failed": 0,
            "current_source_title": None,
            "statuses": statuses,
            "errors": {},
            "bge_available": False,
        }

    db_path = _get_ledger_db_path(resolved)
    _init_preparation_ledger_db(db_path)
    ledger_rows = _load_all_ledger_rows(db_path)

    statuses: dict[str, str] = {}
    errors: dict[str, str] = {}
    ready_count = 0
    processing_count = 0
    pending_count = 0
    failed_count = 0
    current_source_title: str | None = None

    for source in sources:
        key = (source.source_scope, source.source_id)
        identity = f"{source.source_scope}:{source.source_id}"
        row = ledger_rows.get(key)

        with _PREPARATION_LOCK:
            mem_entry = _PREPARATION_REGISTRY.get(_preparation_key(resolved, source))
            mem_status = str(mem_entry.get("status", "")) if mem_entry else ""

        # Authority for ready: SQLite ledger when a ledger row exists.
        # If a ledger row exists in pending/processing, in-memory registry ready MUST NOT preempt uncommitted ledger.
        # If no ledger row exists, in-memory registry or durable coverage applies.
        if row is not None:
            if row.state == PREP_STATE_READY and row.source_fingerprint == _source_fingerprint(source) and row.model_revision == resolved.bge_m3_model_revision:
                state = PREP_STATE_READY
            elif row.state == PREP_STATE_FAILED:
                state = PREP_STATE_FAILED
            elif row.state == PREP_STATE_PROCESSING:
                state = PREP_STATE_PROCESSING
            else:
                # Ledger is pending or stale fingerprint/revision
                if mem_status == PREP_STATE_PROCESSING:
                    state = PREP_STATE_PROCESSING
                elif mem_status == PREP_STATE_FAILED:
                    state = PREP_STATE_FAILED
                else:
                    state = PREP_STATE_PENDING
        elif _durable_semantic_coverage_ready(source, resolved):
            state = PREP_STATE_READY
        else:
            if mem_status in PREP_ALL_STATES:
                state = mem_status
            else:
                state = "not_prepared"

        statuses[identity] = state
        if row and row.last_error:
            errors[identity] = row.last_error
        elif mem_entry and mem_entry.get("reason"):
            errors[identity] = mem_entry["reason"]

        if state == PREP_STATE_READY:
            ready_count += 1
        elif state == PREP_STATE_PROCESSING:
            processing_count += 1
            if current_source_title is None:
                current_source_title = source.title
        elif state == PREP_STATE_PENDING:
            pending_count += 1
        elif state == PREP_STATE_FAILED:
            failed_count += 1

    return {
        "total": total_count,
        "ready": ready_count,
        "processing": processing_count,
        "pending": pending_count,
        "failed": failed_count,
        "current_source_title": current_source_title,
        "statuses": statuses,
        "errors": errors,
        "bge_available": True,
    }


def reconcile_and_enqueue_workspace_chat_sources(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    priority: str = PREP_PRIORITY_NORMAL,
) -> int:
    """Reconcile and queue eligible sources without re-embedding matching ready fingerprints."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return 0
    if not resolved.enabled:
        return 0

    sources = tuple(s for s in context_sources if (s.text or "").strip())
    if not sources:
        return 0

    db_path = _get_ledger_db_path(resolved)
    _init_preparation_ledger_db(db_path)
    existing_rows = _load_all_ledger_rows(db_path)

    enqueued_count = 0
    now = time.time()

    with _SOURCE_CACHE_LOCK:
        for s in sources:
            _SOURCE_CACHE[(s.source_scope, s.source_id)] = s

    for source in sources:
        key = (source.source_scope, source.source_id)
        current_fp = _source_fingerprint(source)
        doc_id = _document_id(source)
        row = existing_rows.get(key)

        with _PREPARATION_LOCK:
            mem_entry = _PREPARATION_REGISTRY.get(_preparation_key(resolved, source))
            if mem_entry and mem_entry.get("status") == PREP_STATE_READY:
                continue

        if (
            row is not None
            and row.state == PREP_STATE_READY
            and row.source_fingerprint == current_fp
            and row.model_revision == resolved.bge_m3_model_revision
        ):
            with _PREPARATION_LOCK:
                _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                    _preparation_entry(resolved, source, PREP_STATE_READY)
                )
            continue

        if _durable_semantic_coverage_ready(source, resolved):
            with _PREPARATION_LOCK:
                _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                    _preparation_entry(resolved, source, PREP_STATE_READY)
                )
            ready_row = SourcePreparationLedgerRow(
                source_scope=source.source_scope,
                source_id=source.source_id,
                source_fingerprint=current_fp,
                model_id="BAAI/bge-m3",
                model_revision=resolved.bge_m3_model_revision,
                state=PREP_STATE_READY,
                priority=priority,
                attempt_count=0,
                last_error="",
                document_id=doc_id,
                created_at=now,
                updated_at=now,
            )
            _upsert_ledger_row(db_path, ready_row)
            continue

        if (
            row is not None
            and row.state == PREP_STATE_FAILED
            and row.source_fingerprint == current_fp
            and priority != PREP_PRIORITY_INTERACTIVE
        ):
            continue

        if row is not None and row.state in (PREP_STATE_PENDING, PREP_STATE_PROCESSING):
            if priority == PREP_PRIORITY_INTERACTIVE and row.priority != PREP_PRIORITY_INTERACTIVE:
                upd_row = SourcePreparationLedgerRow(
                    source_scope=source.source_scope,
                    source_id=source.source_id,
                    source_fingerprint=current_fp,
                    model_id="BAAI/bge-m3",
                    model_revision=resolved.bge_m3_model_revision,
                    state=row.state,
                    priority=PREP_PRIORITY_INTERACTIVE,
                    attempt_count=row.attempt_count,
                    last_error=row.last_error,
                    document_id=doc_id,
                    created_at=row.created_at,
                    updated_at=now,
                )
                _upsert_ledger_row(db_path, upd_row)
            enqueued_count += 1
            continue

        new_row = SourcePreparationLedgerRow(
            source_scope=source.source_scope,
            source_id=source.source_id,
            source_fingerprint=current_fp,
            model_id="BAAI/bge-m3",
            model_revision=resolved.bge_m3_model_revision,
            state=PREP_STATE_PENDING,
            priority=priority,
            attempt_count=0,
            last_error="",
            document_id=doc_id,
            created_at=now,
            updated_at=now,
        )
        _upsert_ledger_row(db_path, new_row)
        with _PREPARATION_LOCK:
            _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                _preparation_entry(resolved, source, PREP_STATE_PENDING)
            )
        enqueued_count += 1

    if enqueued_count > 0:
        start_workspace_chat_background_drain(resolved, sources)
    return enqueued_count


def promote_workspace_chat_source_priority(
    source_scope: str,
    source_id: str,
    priority: str = PREP_PRIORITY_INTERACTIVE,
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> bool:
    """Elevate priority of an existing pending source."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return False
    if not resolved.enabled:
        return False
    db_path = _get_ledger_db_path(resolved)
    row = _load_ledger_row(db_path, source_scope, source_id)
    if not row or row.state not in (PREP_STATE_PENDING, PREP_STATE_PROCESSING):
        return False
    now = time.time()
    upd_row = SourcePreparationLedgerRow(
        source_scope=row.source_scope,
        source_id=row.source_id,
        source_fingerprint=row.source_fingerprint,
        model_id=row.model_id,
        model_revision=row.model_revision,
        state=row.state,
        priority=priority,
        attempt_count=row.attempt_count,
        last_error=row.last_error,
        document_id=row.document_id,
        created_at=row.created_at,
        updated_at=now,
    )
    _upsert_ledger_row(db_path, upd_row)
    start_workspace_chat_background_drain(resolved)
    return True


def start_workspace_chat_background_drain(
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    sources: Iterable[WorkspaceAIContextSource] | None = None,
) -> None:
    """Trigger background queue drain if not already running."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return
    if not resolved.enabled:
        return

    if sources:
        with _SOURCE_CACHE_LOCK:
            for s in sources:
                if (s.text or "").strip():
                    _SOURCE_CACHE[(s.source_scope, s.source_id)] = s

    global _DRAIN_IS_RUNNING
    with _DRAIN_RUNNING_LOCK:
        if not _DRAIN_IS_RUNNING:
            _DRAIN_IS_RUNNING = True
            _get_executor().submit(_drain_preparation_queue, config=resolved)


def _drain_preparation_queue(config: WorkspaceChatRagV2CanaryConfig) -> None:
    global _DRAIN_IS_RUNNING
    db_path = _get_ledger_db_path(config)
    try:
        while True:
            item = _claim_next_preparation_item(
                db_path,
                model_id="BAAI/bge-m3",
                model_revision=config.bge_m3_model_revision,
            )
            if item is None:
                # Under the running lock, double-check if any new items were enqueued just now
                with _DRAIN_RUNNING_LOCK:
                    item = _claim_next_preparation_item(
                        db_path,
                        model_id="BAAI/bge-m3",
                        model_revision=config.bge_m3_model_revision,
                    )
                    if item is None:
                        _DRAIN_IS_RUNNING = False
                        break

            source_key = (item.source_scope, item.source_id)
            with _SOURCE_CACHE_LOCK:
                source = _SOURCE_CACHE.get(source_key)

            if source is None or not (source.text or "").strip():
                _commit_preparation_result(
                    db_path,
                    item.source_scope,
                    item.source_id,
                    PREP_STATE_FAILED,
                    error_reason="source_text_unavailable",
                )
                continue

            with _PREPARATION_LOCK:
                _PREPARATION_REGISTRY[_preparation_key(config, source)] = (
                    _preparation_entry(config, source, PREP_STATE_PROCESSING)
                )

            try:
                prepare_workspace_chat_sources(
                    [source],
                    config=config,
                )
                _commit_preparation_result(
                    db_path,
                    item.source_scope,
                    item.source_id,
                    PREP_STATE_READY,
                )
            except Exception as exc:
                if str(exc) == "library_writer_busy":
                    _commit_preparation_result(
                        db_path,
                        item.source_scope,
                        item.source_id,
                        PREP_STATE_PENDING,
                        error_reason="library_writer_busy",
                    )
                    continue
                err_reason = _safe_reason(exc)
                _commit_preparation_result(
                    db_path,
                    item.source_scope,
                    item.source_id,
                    PREP_STATE_FAILED,
                    error_reason=err_reason,
                )
    finally:
        with _DRAIN_RUNNING_LOCK:
            _DRAIN_IS_RUNNING = False


def schedule_workspace_chat_source_preparation(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> None:
    """Schedule preparation once without blocking a Streamlit rerun."""
    reconcile_and_enqueue_workspace_chat_sources(
        context_sources,
        config=config,
        priority=PREP_PRIORITY_NORMAL,
    )


def retry_workspace_chat_source_preparation(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> None:
    """Explicitly retry current failed/not-prepared source fingerprints."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return
    sources = tuple(context_sources)
    with _PREPARATION_LOCK:
        for source in sources:
            _PREPARATION_REGISTRY.pop(_preparation_key(resolved, source), None)

    db_path = _get_ledger_db_path(resolved)
    _delete_ledger_rows(db_path, [(s.source_scope, s.source_id) for s in sources])
    global _DRAIN_IS_RUNNING
    with _DRAIN_RUNNING_LOCK:
        _DRAIN_IS_RUNNING = False
    reconcile_and_enqueue_workspace_chat_sources(
        sources,
        config=resolved,
        priority=PREP_PRIORITY_INTERACTIVE,
    )


def resume_workspace_chat_source_preparation(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> None:
    """Wake a durable pending queue after an interrupted UI/session run."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return
    sources = tuple(source for source in context_sources if (source.text or "").strip())
    reconcile_and_enqueue_workspace_chat_sources(sources, config=resolved)
    if sources:
        with _SOURCE_CACHE_LOCK:
            for source in sources:
                _SOURCE_CACHE[(source.source_scope, source.source_id)] = source
        global _DRAIN_IS_RUNNING
        with _DRAIN_RUNNING_LOCK:
            _DRAIN_IS_RUNNING = False
        schedule_workspace_chat_source_preparation(sources, config=resolved)


def forget_workspace_chat_sources(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> int:
    """Remove deleted source text, readiness state, and local retrieval chunks.

    Deletion is best-effort for a stopped semantic worker, but it is always
    fail-closed at the application layer because the source record and its
    selection are removed before a future query can be built.
    """
    sources = tuple(context_sources)
    if not sources:
        return 0
    document_ids = {_document_id(source) for source in sources}
    with _PREPARATION_LOCK:
        stale_keys = [
            key for key, entry in _PREPARATION_REGISTRY.items()
            if entry.get("document_id") in document_ids
        ]
        for key in stale_keys:
            _PREPARATION_REGISTRY.pop(key, None)

    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return 0

    db_path = _get_ledger_db_path(resolved)
    _delete_ledger_rows(db_path, [(s.source_scope, s.source_id) for s in sources])

    removed_chunks = 0
    materialized_root = resolved.runtime_root / "materialized_sources"
    for document_id in document_ids:
        try:
            (materialized_root / f"{document_id}.txt").unlink(missing_ok=True)
        except OSError:
            LOGGER.warning("Could not remove materialized Workspace Chat source", exc_info=True)

    with _RUNTIME_CACHE_LOCK:
        runtime_entries = tuple(_RUNTIME_CACHE.values())
    for entry in runtime_entries:
        with entry.lock:
            for document_id in document_ids:
                try:
                    removed_chunks += entry.pipeline.index.delete_document(document_id)
                except Exception:
                    LOGGER.warning("Could not remove source from in-process retrieval index", exc_info=True)

    try:
        removed_chunks += _SUBPROCESS_CLIENT.delete_documents(tuple(document_ids))
    except Exception:
        LOGGER.warning("Could not remove source from subprocess retrieval index", exc_info=True)
    return removed_chunks


def get_workspace_chat_source_preparation_status(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> dict[str, str]:
    """Return bounded readiness states for owner-facing UI gates."""
    summary = get_workspace_chat_preparation_summary(context_sources, config=config)
    return summary["statuses"]


def seed_workspace_chat_source_preparation(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: WorkspaceChatRagV2CanaryConfig,
    expected_source_fingerprints: Iterable[str],
) -> None:
    """Seed in-memory readiness from a verified, separately staged index.

    The caller owns verification of the durable staging manifest.  This helper
    never prepares, materializes, encodes, or writes documents; it only enables
    a read-only query process to use an already prepared runtime.
    """
    expected = frozenset(str(value) for value in expected_source_fingerprints)
    actual_sources = tuple(source for source in context_sources if (source.text or "").strip())
    actual = frozenset(_source_fingerprint(source) for source in actual_sources)
    if actual != expected:
        raise RuntimeError("prepared_source_fingerprint_mismatch")
    with _PREPARATION_LOCK:
        for source in actual_sources:
            _PREPARATION_REGISTRY[_preparation_key(config, source)] = _preparation_entry(
                config,
                source,
                _PREPARATION_READY_STATE,
                seeded_from_verified_staging=True,
            )


def _atomic_write_text(path: Path, text: str) -> None:
    """Write only changed bytes so unchanged sources keep stable fingerprints."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode("utf-8")
    if path.is_file() and path.read_bytes() == encoded:
        return
    temporary = path.with_suffix(f"{path.suffix}.tmp-{threading.get_ident()}")
    temporary.write_bytes(encoded)
    os.replace(temporary, path)


def _materialize_sources(
    sources: Iterable[WorkspaceAIContextSource],
    runtime_root: Path,
) -> tuple[Tuple[SourceSpec, ...], dict[str, WorkspaceAIContextSource]]:
    specs = []
    originals = {}
    source_root = runtime_root / "materialized_sources"
    for source in sources:
        text = (source.text or "").strip()
        if not text:
            continue
        document_id = _document_id(source)
        path = source_root / f"{document_id}.txt"
        _atomic_write_text(path, text)
        specs.append(
            SourceSpec(
                path=path,
                source_id=f"{source.source_scope}:{source.source_id}",
                document_id=document_id,
                privacy_labels=_privacy_labels(source),
                enabled=True,
                owner_consent=True,
                language_hints=("vi", "ja", "en"),
            )
        )
        originals[document_id] = source
    return tuple(specs), originals


def _location(item: Any) -> str:
    if item.page is not None:
        return f"Trang {item.page}"
    if item.sheet:
        location = f"Sheet: {item.sheet}"
        if item.cell_range:
            location += f", ô {item.cell_range}"
        elif item.row_range:
            location += f", hàng {item.row_range[0]}-{item.row_range[1]}"
        return location
    if item.slide is not None:
        return f"Slide {item.slide}"
    if item.section_path:
        return " > ".join(item.section_path)
    return ""


def _map_serialized_query_result(
    query_result: dict[str, Any],
    originals: Mapping[str, WorkspaceAIContextSource],
    *,
    requested_profile: str,
    effective_profile: str,
    fallback_reason: str,
    latency_ms: float,
    search_preference: str = "auto",
    pre_decision: str = "fast",
    pre_reason_codes: Sequence[str] = (),
    post_decision: str = "not_run",
    post_reason_codes: Sequence[str] = (),
) -> dict[str, Any]:

    evidence_items = []
    retrieved_sources = []
    citations = []
    per_source_counts: Counter[str] = Counter()
    summary_dict = query_result.get("summary", {})
    insufficiency_reasons = query_result.get("insufficiency_reasons", [])

    for index, item in enumerate(query_result.get("items", []), 1):
        original = originals.get(item.get("document_id", ""))
        if original is None:
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        title = sanitize_citation_title(original.title)
        location = _serialized_location(item)
        score = float(item.get("score", 0.0))
        citation_id = str(item.get("citation_id", ""))
        evidence_id = str(item.get("evidence_id", ""))

        evidence_items.append(
            {
                "snippet_index": index,
                "source_id": original.source_id,
                "source_scope": original.source_scope,
                "source_type": original.source_type,
                "title": title,
                "text": text,
                "location_info": location,
                "score": score,
                "retrieval_score": score,
                "citation_id": citation_id,
                "evidence_id": evidence_id,
            }
        )
        virtual_title = f"{title} ({location})" if location else title
        retrieved_sources.append(
            WorkspaceAIContextSource(
                source_id=original.source_id,
                source_scope=original.source_scope,
                source_type=original.source_type,
                title=virtual_title,
                privacy_label=original.privacy_label,
                text=text,
                included_chars=len(text),
                truncated=bool(original.truncated),
            )
        )
        citations.append(
            {
                "title": title,
                "snippet": f"{text[:150]}..." if len(text) > 150 else text,
                "location": location,
                "citation_id": citation_id,
            }
        )
        per_source_counts[original.source_id] += 1

    summary_count = len(evidence_items)
    distinct_sources = len(per_source_counts)
    candidate_count = int(summary_dict.get("candidate_count", 0))
    returned_count = int(summary_dict.get("returned_count", 0))
    filtered_as_stale_count = int(summary_dict.get("filtered_as_stale_count", 0))
    indexed_chunk_count = int(summary_dict.get("indexed_chunk_count", 0))
    synthesis_dict = query_result.get("synthesis", {})

    routing = query_result.get("routing", {})
    reranker_requested = bool(routing.get("reranker_requested", False))
    reranker_applied = bool(routing.get("reranker_applied", False))
    effective_path = str(routing.get("effective_path", effective_profile))
    degraded = bool(routing.get("degraded", False))
    raw_degraded_reason = str(routing.get("degraded_reason", ""))
    degraded_reason = _sanitize_degraded_reason(raw_degraded_reason) if (degraded or raw_degraded_reason) else ""
    policy_version = str(routing.get("policy_version", "adaptive-reranking-v1"))
    safe_fb_reason = _safe_reason(fallback_reason) if fallback_reason else ""
    telemetry = {
        "canary_enabled": True,
        "backend": "rag_v2_subprocess",
        "requested_profile": requested_profile,
        "effective_profile": effective_profile,
        "search_preference": search_preference,
        "pre_decision": pre_decision,
        "pre_reason_codes": list(pre_reason_codes or routing.get("reason_codes", ())),
        "post_decision": post_decision,
        "post_reason_codes": list(post_reason_codes),
        "fallback_applied": bool(safe_fb_reason) or degraded,
        "fallback_reason": safe_fb_reason or degraded_reason,
        "latency_ms": round(latency_ms, 3),
        "candidate_count": candidate_count,
        "returned_count": returned_count,
        "filtered_as_stale_count": filtered_as_stale_count,
        "insufficiency_reasons": insufficiency_reasons,
        "reranker_requested": reranker_requested,
        "reranker_applied": reranker_applied,
        "effective_path": effective_path,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "rerank_latency_ms": float(summary_dict.get("rerank_latency_ms", 0.0) or routing.get("rerank_latency_ms", 0.0) or 0.0),
        "policy_version": policy_version,
    }


    if reranker_applied:
        safe_owner_message = (
            f"Đã tìm kỹ và dùng {summary_count} đoạn liên quan từ {distinct_sources} nguồn."
        )
    else:
        safe_owner_message = (
            f"Đã dùng {summary_count} đoạn liên quan từ {distinct_sources} nguồn."
        )

    return {
        "retrieval_applied": True,
        "evidence_items": evidence_items,
        "retrieved_context_sources": tuple(retrieved_sources),
        "summary_count": summary_count,
        "summary": summary_dict,
        "citations": citations,
        "safe_owner_message": safe_owner_message,
        "eligible_source_count": len(originals),
        "indexed_source_count": len(originals),
        "indexed_chunk_count": indexed_chunk_count,
        "candidate_count": candidate_count,
        "distinct_source_count": distinct_sources,
        "per_source_result_counts": dict(sorted(per_source_counts.items())),
        "filtered_as_stale_count": filtered_as_stale_count,
        "local_synthesis": {
            "answer": str(synthesis_dict.get("answer", "") or ""),
            "citation_ids": list(synthesis_dict.get("citation_ids", ())),
            "grounded": bool(synthesis_dict.get("grounded", False)),
            "abstained": bool(synthesis_dict.get("abstained", False)),
            "answer_mode": str(synthesis_dict.get("answer_mode", "")),
            "limitation_reasons": list(synthesis_dict.get("limitation_reasons", ())),
        },
        "rag_v2_canary": telemetry,
    }


def _run_profile(
    question: str,
    sources: Tuple[WorkspaceAIContextSource, ...],
    config: WorkspaceChatRagV2CanaryConfig,
    profile: str,
    *,
    fallback_reason: str,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline],
    expansion: Optional[Mapping[str, Any]] = None,
    rerank_requested: bool = False,
    routing_reason_codes: Sequence[str] = (),
    policy_version: str = "adaptive-reranking-v1",
    search_preference: str = "auto",
    pre_decision: str = "fast",
    pre_reason_codes: Sequence[str] = (),
    post_decision: str = "not_run",
    post_reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    started = time.perf_counter()
    pipe_config = _pipeline_config(
        config,
        profile,
        # Sources have passed the preparation/coverage gate already.  A query
        # must never open the shared index in write mode: doing so lets a
        # fresh worker silently embed every unrelated legacy chunk.
        read_only=True,
        include_reranker=rerank_requested,
        collection_id=_collection_id_for_sources(sources),
    )
    specs, originals = _materialize_sources(sources, config.runtime_root)
    if not specs:
        raise ValueError("no_non_empty_sources")

    sem_state, sem_reason = _semantic_readiness(sources, config)
    if sem_state != _PREPARATION_READY_STATE:
        raise RuntimeError(sem_reason or "sources_not_ready")

    # A durable index can survive an application restart while the isolated
    # BGE worker cannot.  Re-open that worker once before querying; this only
    # loads pinned local models and never re-materializes or embeds a source.
    # The normal preparation path has already done this, so the client reports
    # a cheap reused initialization in the common case.
    if pipeline_factory is RagV2DevPipeline:
        initialize_workspace_chat_rag_v2_worker(
            config,
            timeout_s=120.0,
            pipe_config=pipe_config,
        )
    query_res_dict = _SUBPROCESS_CLIENT.query_ready(
        question,
        specs,
        pipe_config,
        expansion=expansion,
        rerank_requested=rerank_requested,
        routing_reason_codes=routing_reason_codes,
        policy_version=policy_version,
        timeout_s=(config.deep_timeout_ms / 1000.0 if rerank_requested else 30.0),
    )
    mapped = _map_serialized_query_result(
        query_res_dict,
        originals,
        requested_profile=config.requested_profile,
        effective_profile=profile,
        fallback_reason=fallback_reason,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        search_preference=search_preference,
        pre_decision=pre_decision,
        pre_reason_codes=pre_reason_codes,
        post_decision=post_decision,
        post_reason_codes=post_reason_codes,
    )
    LOGGER.info(
        "workspace_chat_rag_v2 %s",
        json.dumps(mapped["rag_v2_canary"], sort_keys=True),
    )
    return mapped


def _serialized_location(item: Mapping[str, Any]) -> str:
    page = item.get("page")
    if page is not None:
        return f"Trang {page}"
    sheet = item.get("sheet")
    if sheet:
        location = f"Sheet: {sheet}"
        cell_range = item.get("cell_range")
        row_range = item.get("row_range")
        if cell_range:
            location += f", ô {cell_range}"
        elif row_range and isinstance(row_range, (list, tuple)) and len(row_range) >= 2:
            location += f", hàng {row_range[0]}-{row_range[1]}"
        return location
    slide = item.get("slide")
    if slide is not None:
        return f"Slide {slide}"
    section_path = item.get("section_path")
    if section_path:
        return " > ".join(section_path)
    return ""


def _semantic_readiness(
    sources: Tuple[WorkspaceAIContextSource, ...],
    config: WorkspaceChatRagV2CanaryConfig,
) -> tuple[str, str]:
    """Return the aggregate BGE-M3 preparation state."""
    statuses = get_workspace_chat_source_preparation_status(sources, config=config)
    values = tuple(statuses.values())
    if values and all(state == _PREPARATION_READY_STATE for state in values):
        return _PREPARATION_READY_STATE, ""
    if any(state == "failed" for state in values):
        return "failed", "semantic_preparation_failed"
    if any(state in _PREPARATION_ACTIVE_STATES for state in values):
        return "processing", "semantic_preparing"
    return "pending", "semantic_preparing"


def _quality_search_unavailable(reason: str) -> dict[str, Any]:
    """Return no evidence so a provider cannot synthesize from degraded retrieval."""
    safe_reason = _safe_reason(reason)
    return {
        "retrieval_applied": False,
        "retrieval_available": False,
        "status": "quality_search_unavailable",
        "evidence_items": [],
        "retrieved_context_sources": (),
        "summary_count": 0,
        "citations": [],
        "safe_owner_message": (
            "Tìm kiếm tài liệu chất lượng cao đang tạm thời chưa sẵn sàng. "
            "Vui lòng thử lại."
        ),
        "eligible_source_count": 0,
        "indexed_source_count": 0,
        "indexed_chunk_count": 0,
        "candidate_count": 0,
        "distinct_source_count": 0,
        "per_source_result_counts": {},
        "filtered_as_stale_count": 0,
        "rag_v2_canary": {
            "canary_enabled": True,
            "backend": "unavailable",
            "requested_profile": "bge_m3_hybrid",
            "effective_profile": "unavailable",
            "fallback_applied": False,
            "fallback_reason": safe_reason,
        },
    }


def _managed_workbook_path(source: WorkspaceAIContextSource) -> Path | None:
    raw_path = str(getattr(source, "managed_path", "") or "").strip()
    if not raw_path:
        return None
    extension = Path(raw_path).suffix.lower()
    if extension not in {".xlsx", ".xlsm", ".xls"}:
        return None
    try:
        from aios_habit.workspace_chat_source_ingest import MANAGED_WORKBOOK_ROOT
        root = MANAGED_WORKBOOK_ROOT.resolve()
        resolved = Path(raw_path).resolve()
    except (OSError, RuntimeError):
        return None
    if root not in resolved.parents or not resolved.is_file():
        return None
    return resolved


def _try_structured_excel_evidence(
    question: str,
    sources: Tuple[WorkspaceAIContextSource, ...],
) -> dict[str, Any] | None:
    """Use bounded SQL analytics only for deterministic, allow-listed plans."""
    for source in sources:
        path = _managed_workbook_path(source)
        if path is None:
            continue
        document_id = _document_id(source)
        schemas = inspect_excel_schemas(path, document_id=document_id)
        planning = plan_excel_query(question, schemas)
        plan_to_execute = planning.plan

        if not planning.applied or plan_to_execute is None:
            from aios_habit.query_planner import plan_excel_query_via_llm
            from aios_habit.rag_v2.structured_query import parse_llm_excel_plan
            import json
            schemas_text = json.dumps([{"sheet": s.sheet, "columns": s.columns} for s in schemas], ensure_ascii=False)
            llm_plan_dict = plan_excel_query_via_llm(question, schemas_text)
            if llm_plan_dict:
                plan_to_execute = parse_llm_excel_plan(llm_plan_dict)

        if plan_to_execute is None:
            continue

        try:
            result = execute_excel_query(path, plan_to_execute, document_id=document_id)
        except (StructuredQueryError, ValueError, OverflowError) as error:
            LOGGER.warning("Structured Excel query unavailable: %s", _safe_reason(error))
            continue
        if not result.applied or not result.rendered_evidence.strip():
            continue

        title = sanitize_citation_title(source.title)
        sheets = tuple(dict.fromkeys(p.sheet for p in result.provenance if p.sheet))
        if len(sheets) > 1:
            location = f"Sheets: {', '.join(sheets)}"
        elif result.sheet:
            location = f"Sheet: {result.sheet}"
            if result.cell_range:
                location += f", ô {result.cell_range}"
        else:
            location = "Excel"
        text = result.rendered_evidence.strip()
        evidence_id = hashlib.sha256(
            f"structured:{document_id}:{result.sheet}:{result.cell_range}:{text}".encode("utf-8")
        ).hexdigest()[:24]
        evidence_item = {
            "snippet_index": 1,
            "source_id": source.source_id,
            "source_scope": source.source_scope,
            "source_type": source.source_type,
            "title": title,
            "text": text,
            "location_info": location,
            "score": 1.0,
            "retrieval_score": 1.0,
            "citation_id": evidence_id,
            "evidence_id": evidence_id,
            "retrieval_lane": "structured_excel_sql",
        }

        retrieved_source = WorkspaceAIContextSource(
            source_id=source.source_id,
            source_scope=source.source_scope,
            source_type=source.source_type,
            title=f"{title} ({location})",
            privacy_label=source.privacy_label,
            text=text,
            original_chars=len(text),
            included_chars=len(text),
            truncated=result.truncated,
            managed_path=str(path),
        )
        return {
            "retrieval_applied": True,
            "retrieval_available": True,
            "status": "structured_excel_query",
            "evidence_items": [evidence_item],
            "retrieved_context_sources": (retrieved_source,),
            "summary_count": 1,
            "citations": [{
                "title": title,
                "snippet": f"{text[:150]}..." if len(text) > 150 else text,
                "location": location,
                "citation_id": evidence_id,
            }],
            "safe_owner_message": (
                f"Đã truy vấn bảng Excel cục bộ và dùng {result.row_count} dòng kết quả có nguồn gốc."
            ),
            "eligible_source_count": 1,
            "indexed_source_count": 1,
            "indexed_chunk_count": 0,
            "candidate_count": result.row_count,
            "distinct_source_count": 1,
            "per_source_result_counts": {source.source_id: 1},
            "filtered_as_stale_count": 0,
            "local_synthesis": {
                "answer": "", "citation_ids": [evidence_id], "grounded": True,
                "abstained": False, "answer_mode": "structured_excel_sql",
                "limitation_reasons": [],
            },
            "rag_v2_canary": {
                "canary_enabled": True,
                "backend": "structured_excel_sqlite",
                "requested_profile": "structured_excel_sql",
                "effective_profile": "structured_excel_sql",
                "fallback_applied": False,
                "fallback_reason": "",
            },
        }
    return None


def retrieve_workspace_chat_evidence(
    question: str,
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline] = RagV2DevPipeline,
    expansion: Optional[Mapping[str, Any]] = None,
    search_preference: str = "auto",
) -> dict[str, Any]:
    """Retrieve evidence only through the pinned local BGE-M3 hybrid pipeline."""
    sources = tuple(context_sources)
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except (DeploymentManifestError, ValueError) as error:
        reason = _safe_reason(error)
        LOGGER.error("Workspace Chat BGE-M3 deployment unavailable: %s", reason)
        return _quality_search_unavailable(reason)

    if not resolved.enabled:
        return _quality_search_unavailable("feature_flag_disabled")

    semantic_sources = _select_semantic_candidate_sources(question, sources)

    # Scope every retrieval lane before it does any potentially expensive work.
    # In particular, an operational Manual question must not inspect (or ask a
    # planner about) every enabled workbook before it reaches the selected PDF.
    structured_result = _try_structured_excel_evidence(question, semantic_sources)
    if structured_result is not None:
        return structured_result

    pref_str = str(search_preference or "auto").casefold()

    # "Deep" is a user promise, not a cosmetic label.  Do not start a base
    # hybrid preparation job when the separately pinned reranker is absent.
    # Returning no evidence makes the caller stop before it forwards an
    # arbitrary leading slice of the full document to a provider.
    if pref_str == "deep" and (
        not resolved.adaptive_enabled
        or resolved.bge_reranker_model_path is None
    ):
        return _quality_search_unavailable("deep_search_unavailable")

    schedule_workspace_chat_source_preparation(semantic_sources, config=resolved)
    semantic_status, semantic_reason = _semantic_readiness(semantic_sources, resolved)
    if semantic_status != _PREPARATION_READY_STATE:
        return _quality_search_unavailable(semantic_reason or semantic_status)

    plan = coerce_query_plan(question)
    policy = AdaptiveRetrievalPolicy(
        version=resolved.policy_version,
        enabled=resolved.adaptive_enabled,
        deep_timeout_ms=resolved.deep_timeout_ms,
    )

    rerank_requested = False
    routing_reason_codes: Sequence[str] = ()
    pre_dec = None

    if resolved.adaptive_enabled or pref_str == "deep":
        pre_dec = pre_retrieval_gate(plan, user_preference=pref_str, policy=policy)
        init_routing = decide_initial_route(pre_dec, user_preference=pref_str, policy=policy)
        rerank_requested = init_routing.reranker_requested
        routing_reason_codes = init_routing.reason_codes

    try:
        initial_result = _run_profile(
            question,
            semantic_sources,
            resolved,
            "bge_m3_hybrid",
            fallback_reason="",
            pipeline_factory=pipeline_factory,
            expansion=expansion,
            rerank_requested=rerank_requested,
            routing_reason_codes=routing_reason_codes,
            policy_version=resolved.policy_version,
            search_preference=pref_str,
            pre_decision=pre_dec.classification.value if pre_dec else "fast",
            pre_reason_codes=pre_dec.reason_codes if pre_dec else ("pre_fast",),
        )

        if (
            resolved.adaptive_enabled
            and not rerank_requested
            and resolved.bge_reranker_model_path is not None
        ):
            summary_data = initial_result.get("summary", {})
            post_summary = SearchSummary(
                query=question,
                indexed_chunk_count=int(initial_result.get("indexed_chunk_count", 0)),
                eligible_chunk_count=int(initial_result.get("indexed_chunk_count", 0)),
                candidate_count=int(initial_result.get("candidate_count", 0)),
                returned_count=int(initial_result.get("summary_count", 0)),
                evidence_set_term_coverage=float(summary_data.get("evidence_set_term_coverage", 0.0) or 0.0),
                planned_facet_ids=tuple(summary_data.get("planned_facet_ids", ())),
                covered_facet_ids=tuple(summary_data.get("covered_facet_ids", ())),
                missing_facet_ids=tuple(summary_data.get("missing_facet_ids", ())),
                planned_obligation_ids=tuple(summary_data.get("planned_obligation_ids", ())),
                covered_obligation_ids=tuple(summary_data.get("covered_obligation_ids", ())),
                missing_obligation_ids=tuple(summary_data.get("missing_obligation_ids", ())),
                diversity_limited_count=int(summary_data.get("diversity_limited_count", 0)),
            )
            post_dec = post_retrieval_gate(
                post_summary,
                plan,
                distinct_source_count=int(initial_result.get("distinct_source_count", 0)),
                policy=policy,
            )
            initial_result["rag_v2_canary"]["post_decision"] = post_dec.classification.value
            initial_result["rag_v2_canary"]["post_reason_codes"] = list(post_dec.reason_codes)

            # A procedure with a populated, bounded evidence window can have
            # harmless term-coverage uncertainty.  Do not turn that into an
            # automatic CPU reranker load; Deep remains an explicit choice.
            if post_dec.classification == PostDecision.INSUFFICIENT:
                combined_reasons = tuple(
                    dict.fromkeys(list(routing_reason_codes) + list(post_dec.reason_codes))
                )
                escalated_result = _run_profile(
                    question,
                    semantic_sources,
                    resolved,
                    "bge_m3_hybrid",
                    fallback_reason="",
                    pipeline_factory=pipeline_factory,
                    expansion=expansion,
                    rerank_requested=True,
                    routing_reason_codes=combined_reasons,
                    policy_version=resolved.policy_version,
                    search_preference=pref_str,
                    pre_decision=pre_dec.classification.value if pre_dec else "fast",
                    pre_reason_codes=pre_dec.reason_codes if pre_dec else ("pre_fast",),
                    post_decision=post_dec.classification.value,
                    post_reason_codes=post_dec.reason_codes,
                )
                return escalated_result

        return initial_result
    except Exception as error:
        reason = _safe_reason(error)
        LOGGER.warning("Workspace Chat BGE-M3 retrieval unavailable: %s", reason, exc_info=True)
        return _quality_search_unavailable(reason)


def close_workspace_chat_rag_v2_runtimes(*, timeout_s: float | None = 10.0) -> None:
    """Close and evict cached in-process and background preparation runtimes."""
    global _PREPARATION_EXECUTOR, _DRAIN_IS_RUNNING
    with _PREPARATION_LOCK:
        if _PREPARATION_EXECUTOR is not None:
            try:
                _PREPARATION_EXECUTOR.shutdown(wait=True)
            except Exception:
                pass
            _PREPARATION_EXECUTOR = None
        _PREPARATION_REGISTRY.clear()

    with _DRAIN_RUNNING_LOCK:
        _DRAIN_IS_RUNNING = False

    with _SOURCE_CACHE_LOCK:
        _SOURCE_CACHE.clear()

    with _RUNTIME_CACHE_LOCK:
        for entry in _RUNTIME_CACHE.values():
            try:
                entry.pipeline.close()
            except Exception:
                pass
        _RUNTIME_CACHE.clear()
