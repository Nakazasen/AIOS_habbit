"""Feature-flagged Workspace Chat retrieval adapter for the local RAG v2 canary.

The adapter changes retrieval only. Answer generation still flows through
``generate_workspace_ai_answer`` and the Brain Gateway, which remain the owners
of consent, privacy authorization, outbound sanitization, and provider access.
"""
from __future__ import annotations

from collections import Counter
import concurrent.futures
import contextlib
from dataclasses import dataclass
import functools
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence, Tuple
import unicodedata

from aios_habit.rag_v2.adaptive_retrieval import (
    AdaptiveRetrievalPolicy,
    PostDecision,
    PreDecision,
    decide_initial_route,
    post_retrieval_gate,
    pre_retrieval_gate,
)
from aios_habit.rag_v2.bge_subprocess_client import (
    BgeSubprocessWorkerClient,
    _pipe_instance_available,
    default_init_timeout_seconds,
    default_query_timeout_seconds,
    pipe_name_for_config,
)
from aios_habit.rag_v2.index import SearchSummary
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.query_planning import (
    build_query_plan,
    coerce_query_plan,
    query_needs_broad_ready_retrieval,
)
from aios_habit.rag_v2.multilingual_query_expand import (
    expand_question_for_corpus_script,
    short_latin_codes,
)
from aios_habit.rag_v2.script_family import (
    corpus_needs_cjk_query_expansion,
    query_corpus_script_mismatch,
)
from aios_habit.rag_v2.semantic import (
    SemanticBackendError,
    SemanticBackendUnavailable,
)

from aios_habit.rag_v2.structured_query import (
    StructuredQueryError,
    execute_excel_query,
    inspect_excel_schemas,
    plan_excel_query,
    query_might_be_structured_excel,
)
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_models import (
    DEFAULT_COLLECTION_ID,
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY,
)
from aios_habit.workspace_chat_rag_v2_deployment import (
    DeploymentManifestError,
    load_workspace_chat_rag_v2_deployment,
)

LOGGER = logging.getLogger(__name__)


from aios_habit.streaming_markers import (
    _safe_print_streaming_marker,
    format_marker_timestamp,
)


_SUBPROCESS_CLIENT = BgeSubprocessWorkerClient()


class ReadOnlyIndexViolationError(RuntimeError):
    """Raised when an operation attempts to write or prepare sources for a read-only or sealed production index."""


def is_production_sealed_collection(collection_id: str | None) -> bool:
    """Return True if collection_id refers to the sealed production collection ('tri_thuc')."""
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
    from aios_habit.workspace_chat_store import load_collection

    normalized = str(collection_id or "").strip()
    if normalized in {DEFAULT_COLLECTION_ID, "tri_thuc"}:
        return True
    if not normalized:
        default = load_collection(DEFAULT_COLLECTION_ID)
        if default is not None and str(default.storage_root or "").strip():
            return True
    return False


def is_production_index_available(config: Optional[WorkspaceChatRagV2CanaryConfig] = None) -> bool:
    """Return True if the pinned unified production index (library.sqlite) exists on disk."""
    try:
        from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
        prod_pipe_cfg = _pipeline_config(resolved, "bge_m3_hybrid", read_only=True, collection_id=DEFAULT_COLLECTION_ID)
        return bool(prod_pipe_cfg.index_path.is_file())
    except Exception:
        return False


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


def _expected_backend_fingerprint(config: WorkspaceChatRagV2CanaryConfig) -> str:
    """Fingerprint of the embedding backend the E-chain currently selects.

    Mirrors exactly how ``rag_v2/pipeline.py`` constructs the embedding
    backend (``BGE_BACKEND`` env wins, otherwise the default ONNX fp32
    backend) and copies the ``SemanticModelDescriptor`` arguments 1:1 from
    ``OnnxInt8BgeM3Backend`` / ``BgeM3Backend``, so this matches the
    ``model_fingerprint`` stamped on vectors at embed time. The model itself
    is never loaded: only env, sidecar files, and package metadata are read.

    Returns "" when the expected fingerprint cannot be determined (missing
    pinned revision/checksum, unknown backend name, or model directory
    unavailable). Callers must treat "" as NOT READY (fail closed): the
    prepare gate must never claim vectors are trustworthy when the backend
    identity is unknown. A backend switch therefore marks sources pending
    and the worker re-embeds them (self-healing) instead of silently serving
    vectors produced by a different backend.
    """
    try:
        from aios_habit.rag_v2.bge_onnx_backend import (
            BGE_M3_DIMENSION,
            BGE_M3_MODEL_ID,
            DEFAULT_BGE_BACKEND,
            _onnxruntime_version,
            require_onnx_model_dir,
            resolve_bge_backend_name,
            resolve_onnx_checksum,
        )
        from aios_habit.rag_v2.semantic import SemanticModelDescriptor
    except Exception:
        return ""
    revision = (config.bge_m3_model_revision or "").strip()
    if not revision:
        return ""
    try:
        backend_name = resolve_bge_backend_name(DEFAULT_BGE_BACKEND)
    except Exception:
        return ""
    try:
        if backend_name in ("onnx", "onnx_int8"):
            # Same construction as pipeline.py -> OnnxInt8BgeM3Backend:
            # checksum comes from the ONNX sidecar, device is hardcoded.
            model_dir = require_onnx_model_dir(backend_name=backend_name)
            checksum = resolve_onnx_checksum(model_dir)
            descriptor = SemanticModelDescriptor(
                model_id=BGE_M3_MODEL_ID,
                revision=revision,
                runtime="onnxruntime-int8",
                runtime_version=_onnxruntime_version(),
                dimension=BGE_M3_DIMENSION,
                normalized=True,
                artifact_checksum=checksum,
                device="cpu",
            )
        elif backend_name == "pytorch":
            # Same construction as pipeline.py -> BgeM3Backend: the pinned
            # checksum IS the verified tree hash (verify_model_tree raises on
            # mismatch), device comes from the retrieval config.
            from aios_habit.rag_v2.retrieval_backends import _flag_embedding_version

            digest = (config.bge_m3_model_checksum or "").strip().removeprefix("sha256:")
            if len(digest) != 64 or any(
                c not in "0123456789abcdefABCDEF" for c in digest
            ):
                return ""
            descriptor = SemanticModelDescriptor(
                model_id=BGE_M3_MODEL_ID,
                revision=revision,
                runtime="flagembedding-pytorch",
                runtime_version=_flag_embedding_version(),
                dimension=BGE_M3_DIMENSION,
                normalized=True,
                artifact_checksum=f"sha256:{digest.lower()}",
                device=(config.retrieval_device or "cpu").strip() or "cpu",
            )
        else:
            return ""
        fingerprint = descriptor.fingerprint
    except Exception:
        return ""
    return fingerprint if len(fingerprint) == 64 else ""


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
    # Fingerprint of the embedding backend (see _expected_backend_fingerprint)
    # that produced the vectors. "" = stamped before the backend-aware gate.
    model_fingerprint: str = ""


_PREPARATION_REGISTRY: dict[str, dict[str, Any]] = {}
_PREPARATION_LOCK = threading.RLock()
_PREPARATION_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None
_DRAIN_RUNNING_LOCK = threading.Lock()
_DRAIN_IS_RUNNING = False
_PREPARATION_LEDGER_INIT_LOCK = threading.Lock()
_PREPARATION_LEDGER_INITIALIZED_PATHS: set[str] = set()
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
PER_DOCUMENT_LIMIT_ENV = "AIOS_WORKSPACE_RAG_V2_PER_DOCUMENT_LIMIT"

# This preference deliberately lives next to the local Workspace Chat data,
# not in .env. It lets an owner enable or disable the optional CPU reranker
# from the UI without ever reading, exposing, or editing provider secrets.
DEEP_SEARCH_LOCAL_SETTINGS_FILENAME = "rag_v2_local_settings.json"
DEEP_SEARCH_LOCAL_SETTINGS_SCHEMA_VERSION = "1"
DEEP_SEARCH_LOCAL_SETTINGS_KEY = "deep_search_enabled"

_DEFAULT_RUNTIME_ROOT = Path("local_runs/workspace_chat_rag_v2_canary")
_ALLOWED_PROFILES = frozenset({"bge_m3_hybrid"})
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
DRAIN_DURABLE_FALLBACK_FLAG = "AIOS_RAG_V2_DRAIN_DURABLE_FALLBACK"
_SAFE_REASON = re.compile(r"[^a-z0-9_.-]+")
_SAFE_PREPARATION_REASON_PREFIXES = (
    "bge_worker_",
    "preparation_init_",
    "preparation_batch_",
)
_SAFE_PREPARATION_REASON_CODES = frozenset({
    "library_writer_busy",
    "rag_v2_ingestion_incomplete",
})
_LEGACY_UNDIAGNOSED_PREPARATION_ERROR = "runtimeerror"
_RETRYABLE_PREPARATION_ERRORS = frozenset({
    _LEGACY_UNDIAGNOSED_PREPARATION_ERROR,
    "preparation_init_bge_worker_model_load_failed",
    "semanticbackendunavailable",
    "source_text_unavailable",
    # BGE-WORKER-FIX-HOME: Bổ sung các mã lỗi timeout / kết nối worker để tự phục hồi,
    # không ghim cờ lỗi vĩnh viễn cho nguồn hay độc phiên hỏi đáp.
    "bge_worker_init_timeout",
    "bge_worker_persist_timeout",
    "bge_worker_persist_unavailable",
    "bge_worker_init_spawn_failed",
    "preparation_init_bge_worker_init_timeout",
    "preparation_init_bge_worker_persist_timeout",
    "preparation_init_bge_worker_persist_unavailable",
    "preparation_init_bge_worker_init_spawn_failed",
    "preparation_init_worker_busy",
})
_SEMANTIC_SOURCE_STOP_WORDS = frozenset(
    {
        "cau", "hoi", "che", "do", "hoat", "dong", "nhu", "the", "nao",
        "giai", "thich", "giup", "toi",
        "lam", "sao", "what", "how", "does", "work", "operate", "the",
        "and", "for", "with", "this", "that", "are", "you",
        "trong", "bang", "quy", "doi", "va", "lan", "luot", "co", "gia", "tri",
        "bao", "nhieu", "la", "cua", "cho", "cac", "nhung", "duoc", "khi",
        "theo", "ve", "tai", "tu", "voi", "ra", "vao", "den",
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
    bge_m3_batch_size: int = 8
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
    per_document_limit: int = 3

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
        if self.per_document_limit < 1:
            raise ValueError("per_document_limit must be at least 1")


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
                env=env,
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
            per_document_limit=int(
                values.get(PER_DOCUMENT_LIMIT_ENV, values.get("AIOS_RETRIEVAL_DOC_DIVERSITY_CAP", 3)) or 3
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
    "reranker_not_configured",
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
    raw = str(error) if isinstance(error, (SemanticBackendError, RuntimeError)) else ""
    if raw.startswith(_SAFE_PREPARATION_REASON_PREFIXES) or raw in _SAFE_PREPARATION_REASON_CODES:
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
    base = Path(value).name if "\\" in value or "/" in value else value
    try:
        from aios_habit.index_domain import load_domain_document_alias_map
        alias_map = load_domain_document_alias_map()
        if base in alias_map:
            return alias_map[base]
        stem = Path(base).stem
        if stem in alias_map:
            return alias_map[stem]
        from aios_habit.document_canonical_keys import normalize_document_key
        base_canon = normalize_document_key(base)
        if base_canon:
            for target in alias_map.values():
                if normalize_document_key(target) == base_canon:
                    return target
    except Exception:
        pass
    return base


def _runtime_key(config: WorkspaceChatRagV2CanaryConfig, profile: str) -> str:
    # G2: the backend name is part of the runtime identity. A backend switch
    # (onnx <-> pytorch) must invalidate cached pipelines and in-memory READY
    # entries, otherwise the gate would report READY for vectors the current
    # backend cannot use.
    try:
        from aios_habit.rag_v2.bge_onnx_backend import (
            DEFAULT_BGE_BACKEND,
            resolve_bge_backend_name,
        )

        backend_name = resolve_bge_backend_name(DEFAULT_BGE_BACKEND)
    except Exception:
        backend_name = ""
    payload = {
        "runtime_root": str(config.runtime_root.resolve()),
        "profile": profile,
        "bge_backend": backend_name,
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
    read_only: bool = True,
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
    global _PREPARATION_EXECUTOR, _WARMUP_LAST_ATTEMPT_MONO
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
    with _WARMUP_LOCK:
        _WARMUP_LAST_ATTEMPT_MONO = 0.0


def _safe_source_text(source: Any) -> str:
    """Extract source text safely across WorkspaceAIContextSource, NotebookSource, or duck-typed objects."""
    text = getattr(source, "text", None)
    if text is not None:
        return str(text)
    content_text = getattr(source, "content_text", None)
    if content_text is not None and str(content_text).strip():
        return str(content_text)
    content_preview = getattr(source, "content_preview", None)
    if content_preview is not None:
        return str(content_preview)
    return ""


def _safe_source_scope(source: Any) -> str:
    """Extract source scope safely across models."""
    scope = getattr(source, "source_scope", None)
    if scope:
        return str(scope)
    if hasattr(source, "notebook_id"):
        return SOURCE_SCOPE_NOTEBOOK
    return SOURCE_SCOPE_TEMPORARY


def _safe_source_id(source: Any) -> str:
    """Extract source id safely across models."""
    sid = getattr(source, "source_id", None)
    if sid:
        return str(sid)
    sid = getattr(source, "id", None)
    if sid:
        return str(sid)
    return ""


def _coerce_context_source(source: Any) -> WorkspaceAIContextSource:
    """Ensure a source is a WorkspaceAIContextSource with all expected attributes."""
    if isinstance(source, WorkspaceAIContextSource):
        return source
    text = _safe_source_text(source)
    source_id = _safe_source_id(source)
    source_scope = _safe_source_scope(source)
    title = str(getattr(source, "title", "") or source_id or "Untitled")
    source_type = str(getattr(source, "source_type", "") or "plain_text")
    privacy_label = str(getattr(source, "privacy_label", "") or "local_only")
    managed_path = str(getattr(source, "managed_path", "") or "")
    truncated = bool(getattr(source, "truncated", False))
    return WorkspaceAIContextSource(
        source_id=source_id,
        source_scope=source_scope,
        source_type=source_type,
        title=title,
        privacy_label=privacy_label,
        text=text,
        included_chars=len(text),
        truncated=truncated,
        managed_path=managed_path,
    )


@functools.lru_cache(maxsize=4096)
def _document_id_cached(source: WorkspaceAIContextSource) -> str:
    if getattr(source, "document_id", ""):
        return str(source.document_id).strip()
    if getattr(source, "source_id", "") and str(source.source_id).startswith("wsc-"):
        return str(source.source_id).strip()
    text_bytes = (getattr(source, "text", "") or "").strip().encode("utf-8")
    if text_bytes:
        return f"wsc-{hashlib.sha256(text_bytes).hexdigest()[:24]}"
    identity = f"{getattr(source, 'source_scope', '')}:{getattr(source, 'source_id', '')}".encode("utf-8")
    return f"wsc-{hashlib.sha256(identity).hexdigest()[:24]}"


def _document_id(source: Any) -> str:
    """Identify a library document by extracted text, not per-machine source id.

    Empty text cannot be matched across machines, so it stays local to
    ``source_scope:source_id``. Filename is never part of the identity.
    """
    coerced = _coerce_context_source(source)
    return _document_id_cached(coerced)


_document_id.cache_clear = _document_id_cached.cache_clear


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
def _source_fingerprint_cached(source: WorkspaceAIContextSource) -> str:
    doc_id = _document_id(source)
    text_bytes = (source.text or "").strip().encode("utf-8")
    content_hash = hashlib.sha256(text_bytes).hexdigest()[:16]
    privacy = (source.privacy_label or "").strip().casefold()
    return f"{doc_id}:{content_hash}:{privacy}"


def _source_fingerprint(source: Any) -> str:
    coerced = _coerce_context_source(source)
    return _source_fingerprint_cached(coerced)


_source_fingerprint.cache_clear = _source_fingerprint_cached.cache_clear


def _fold_semantic_terms(value: str) -> tuple[str, ...]:
    """Return stable, accent-insensitive local query terms for source gating."""
    folded = unicodedata.normalize("NFD", str(value or "").casefold())
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    folded = folded.replace("đ", "d")
    return tuple(re.findall(r"[a-z0-9]+", folded))


def _identity_query_terms(question: str) -> tuple[str, ...]:
    """Casefolded Latin codes the user typed, including two-letter codes."""
    return tuple(dict.fromkeys(token.casefold() for token in short_latin_codes(question)))


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
    identity_terms = _identity_query_terms(question)
    terms = tuple(
        term for term in _fold_semantic_terms(question)
        if (len(term) >= 3 and term not in _SEMANTIC_SOURCE_STOP_WORDS)
    )
    unique_terms = tuple(dict.fromkeys((*identity_terms, *terms)))
    if len(unique_terms) < 2:
        return sources

    manual_requested = "manual" in unique_terms
    matecon_requested = "matecon" in unique_terms
    ranked: list[tuple[int, int, WorkspaceAIContextSource]] = []
    for ordinal, raw_source in enumerate(sources):
        source = _coerce_context_source(raw_source)
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
    if identity_terms:
        identity_ranked = [
            item for item in ranked
            if all(
                term in set(_fold_semantic_terms(f"{item[2].title}\n{item[2].text}"))
                for term in identity_terms
            )
        ]
        if identity_ranked:
            ranked = identity_ranked
        else:
            return sources
    ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
    best_score = ranked[0][0]
    return tuple(item[2] for item in ranked if item[0] == best_score)[:limit]


_BRIDGE_UNAVAILABLE_UNTIL: float = 0.0
_BRIDGE_COOLDOWN_SECONDS: float = 10.0


def _reset_cjk_bridge_fuse() -> None:
    """Reset the CJK query expansion bridge fuse."""
    global _BRIDGE_UNAVAILABLE_UNTIL
    _BRIDGE_UNAVAILABLE_UNTIL = 0.0


def _maybe_expand_latin_query_for_cjk_corpus(
    question: str,
    sources: Tuple[WorkspaceAIContextSource, ...],
) -> Optional[Mapping[str, Any]]:
    """Question-only CJK expansion. Skips when Gemini Web is not already up."""
    global _BRIDGE_UNAVAILABLE_UNTIL
    if os.environ.get("AIOS_AI_BACKEND", "").strip().lower() == "local":
        return None
    corpus_texts = tuple(
        f"{getattr(source, 'title', '')}\n{(_safe_source_text(source) or '')[:160]}" for source in sources[:80]
    )
    if not corpus_needs_cjk_query_expansion(question, corpus_texts):
        return None
    now = time.monotonic()
    if now < _BRIDGE_UNAVAILABLE_UNTIL:
        return None
    try:
        from aios_habit.antigravity_bridge import get_antigravity_bridge_health

        health = get_antigravity_bridge_health()
        if not health.is_direct_ready:
            _BRIDGE_UNAVAILABLE_UNTIL = time.monotonic() + _BRIDGE_COOLDOWN_SECONDS
            return None
        expanded = expand_question_for_corpus_script(
            question,
            corpus_script="cjk",
            gemini_ready=True,
        )
        if not expanded or not expanded.get("variants"):
            _BRIDGE_UNAVAILABLE_UNTIL = time.monotonic() + _BRIDGE_COOLDOWN_SECONDS
            return None
        return expanded
    except Exception:
        _BRIDGE_UNAVAILABLE_UNTIL = time.monotonic() + _BRIDGE_COOLDOWN_SECONDS
        LOGGER.debug("CJK query expansion skipped", exc_info=True)
        return None


def _retrieval_source_window(
    question: str,
    sources: Tuple[WorkspaceAIContextSource, ...],
) -> Tuple[WorkspaceAIContextSource, ...]:
    """Keep the preparation cap; search every ready source when the query script diverges."""
    plan = coerce_query_plan(question)
    if query_needs_broad_ready_retrieval(plan):
        return sources
    if short_latin_codes(question) and len(sources) > 3:
        return sources
    corpus_texts = tuple(f"{getattr(source, 'title', '')}\n{(_safe_source_text(source) or '')[:800]}" for source in sources)
    if len(sources) > 3 and query_corpus_script_mismatch(question, corpus_texts):
        return sources
    return _select_semantic_candidate_sources(question, sources)


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

    identity_terms = _identity_query_terms(question)
    terms = tuple(
        term for term in (*identity_terms, *_fold_semantic_terms(question))
        if term not in _SEMANTIC_SOURCE_STOP_WORDS
        and (len(term) >= 3 or term in identity_terms)
    )
    if len(tuple(dict.fromkeys(terms))) < 2:
        return WorkspaceChatSourceScope((), False, "question_too_broad")
    if len(selected) > limit or len(selected) == len(source_tuple):
        return WorkspaceChatSourceScope((), False, "no_narrow_source_match")
    return WorkspaceChatSourceScope(selected, True, "matched_sources")


# Coverage queries for the durable-index prepare gate. ``CROSS JOIN`` is
# deliberate: it pins the join order so SQLite drives from ``chunks`` (tens
# of rows via ``idx_chunks_document_id``) into the embedding tables by
# ``chunk_id`` (PRIMARY KEY / model index) instead of scanning the whole
# 100k+ row embeddings table on ``model_fingerprint`` first. Measured on
# PC0575 (2026-09-30): the unpinned dense query planned a full scan of
# ``chunk_embeddings`` and took 71.9 s for a 15-chunk document; the same
# check against the sparse table planned correctly at 0.01 s.
_DENSE_COVERAGE_SQL = """SELECT COUNT(DISTINCT c.chunk_id)
   FROM chunks c CROSS JOIN chunk_embeddings e ON e.chunk_id = c.chunk_id
   WHERE c.document_id = ? AND c.retrievable = 1
     AND e.model_id = 'BAAI/bge-m3' AND e.model_revision = ?
     AND e.model_fingerprint = ?"""

_SPARSE_COVERAGE_SQL = """SELECT COUNT(DISTINCT c.chunk_id)
   FROM chunks c
   CROSS JOIN chunk_embeddings d ON d.chunk_id = c.chunk_id
   CROSS JOIN chunk_sparse_embeddings s
     ON s.chunk_id = c.chunk_id AND s.model_fingerprint = d.model_fingerprint
   WHERE c.document_id = ? AND c.retrievable = 1
     AND d.model_id = 'BAAI/bge-m3' AND d.model_revision = ?
     AND d.model_fingerprint = ?"""

# Session-scoped cache for the per-source coverage check, invalidated whenever
# the SQLite index file's (mtime_ns, size) changes on disk. Fail-closed: only
# successful lookups are cached; exceptions are never cached and still return False.
_COVERAGE_CACHE_TTL_SECONDS = 3600.0
_COVERAGE_CACHE: dict[tuple[str, str, str, str], tuple[float, bool]] = {}
_COVERAGE_CACHE_LOCK = threading.Lock()


def _cached_coverage_result(
    key: tuple[str, str, str, str],
) -> bool | None:
    with _COVERAGE_CACHE_LOCK:
        entry = _COVERAGE_CACHE.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del _COVERAGE_CACHE[key]
            return None
        return value


def _store_coverage_result(key: tuple[str, str, str, str], value: bool) -> None:
    with _COVERAGE_CACHE_LOCK:
        _COVERAGE_CACHE[key] = (time.monotonic() + _COVERAGE_CACHE_TTL_SECONDS, value)


_ENSURED_SOURCE_NAME_INDEX_PATHS: set[str] = set()
_ENSURED_SOURCE_NAME_INDEX_LOCK = threading.Lock()


def _ensure_source_name_index(index_path: Path) -> None:
    """Auto-create idx_chunks_retrievable_source_name on an existing index if missing."""
    resolved_str = index_path.resolve().as_posix()
    with _ENSURED_SOURCE_NAME_INDEX_LOCK:
        if resolved_str in _ENSURED_SOURCE_NAME_INDEX_PATHS:
            return
        _ENSURED_SOURCE_NAME_INDEX_PATHS.add(resolved_str)
    try:
        from aios_habit.rag_v2.index import ensure_index_source_name_index
        ensure_index_source_name_index(index_path)
    except Exception:
        pass


_CATALOG_TITLE_MAP: dict[tuple[str, int, int], dict[str, str]] = {}
_CATALOG_TITLE_LOCK = threading.Lock()


def _get_catalog_title_map(index_path: Path, st: os.stat_result) -> dict[str, str]:
    key = (index_path.resolve().as_posix(), st.st_mtime_ns, st.st_size)
    with _CATALOG_TITLE_LOCK:
        cached = _CATALOG_TITLE_MAP.get(key)
        if cached is not None:
            return cached
    try:
        from aios_habit import index_domain
        catalog_specs = index_domain.load_all_index_specs(index_path)
        title_map = {}
        for spec in catalog_specs:
            spec_title = (getattr(spec, "title", "") or "").strip()
            if spec_title and spec_title not in title_map:
                title_map[spec_title] = str(spec.document_id)
    except Exception:
        title_map = {}
    with _CATALOG_TITLE_LOCK:
        _CATALOG_TITLE_MAP[key] = title_map
    return title_map


def _durable_semantic_coverage_ready(    source: WorkspaceAIContextSource,
    config: WorkspaceChatRagV2CanaryConfig,
) -> bool:
    """Check an existing local BGE index without loading the model again.

    G2 backend-aware prepare gate: vectors only count when their
    ``model_fingerprint`` matches the embedding backend the E-chain currently
    selects. A backend switch therefore fails closed here instead of silently
    trusting vectors produced by a different backend.
    """
    from aios_habit.workspace_chat_store import collection_runtime_layout

    collection_id = _collection_id_for_sources((source,))
    profile_root = config.runtime_root / config.requested_profile
    collection_root, index_filename = collection_runtime_layout(collection_id, profile_root)
    index_path = collection_root / index_filename
    if not index_path.is_file() or not config.bge_m3_model_revision:
        return False
    expected_fingerprint = _expected_backend_fingerprint(config)
    if not expected_fingerprint:
        return False
    document_id = _document_id(source)
    try:
        st = index_path.stat()
        index_cache_id = f"{index_path.resolve().as_posix()}@{st.st_mtime_ns}:{st.st_size}"
    except OSError:
        index_cache_id = index_path.resolve().as_posix()
    cache_key = (
        index_cache_id,
        document_id,
        config.bge_m3_model_revision,
        expected_fingerprint,
    )
    cached = _cached_coverage_result(cache_key)
    if cached is not None:
        return cached
    _ensure_source_name_index(index_path)
    try:
        uri = f"file:{index_path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            has_source_state = bool(
                connection.execute("PRAGMA table_info(source_state)").fetchone()
            )

            def _doc_retrievable_count(doc_id: str) -> int:
                if has_source_state:
                    row = connection.execute(
                        "SELECT chunk_count FROM source_state WHERE document_id=?",
                        (doc_id,),
                    ).fetchone()
                    return int(row[0] or 0) if row is not None else 0
                return int(
                    connection.execute(
                        "SELECT COUNT(*) FROM chunks WHERE document_id=? AND retrievable=1",
                        (doc_id,),
                    ).fetchone()[0]
                )

            retrievable = _doc_retrievable_count(document_id)
            if retrievable <= 0 and getattr(source, "source_id", ""):
                src_id = str(source.source_id).strip()
                if src_id.startswith("wsc-"):
                    cnt = _doc_retrievable_count(src_id)
                    if cnt > 0:
                        document_id = src_id
                        retrievable = cnt
            if retrievable <= 0:
                candidate_title = (getattr(source, "title", "") or "").strip()
                if candidate_title:
                    matched_doc_id: Optional[str] = None
                    try:
                        title_map = _get_catalog_title_map(index_path, st)
                        matched_doc_id = title_map.get(candidate_title)
                        if matched_doc_id is None and "C7620" in candidate_title:
                            for spec_title, doc_id in title_map.items():
                                if "C7620" in spec_title:
                                    matched_doc_id = doc_id
                                    break
                    except Exception:
                        matched_doc_id = None
                    if matched_doc_id is not None:
                        cnt = _doc_retrievable_count(matched_doc_id)
                        if cnt > 0:
                            document_id = matched_doc_id
                            retrievable = cnt
                    if retrievable <= 0:
                        found = connection.execute(
                            "SELECT document_id FROM chunks WHERE source_name=? AND retrievable=1 LIMIT 1",
                            (candidate_title,),
                        ).fetchone()
                        if not found and "C7620" in candidate_title:
                            found = connection.execute(
                                "SELECT document_id FROM chunks WHERE source_name LIKE '%C7620%' AND retrievable=1 LIMIT 1"
                            ).fetchone()
                        if found:
                            fallback_doc_id = str(found[0])
                            cnt = _doc_retrievable_count(fallback_doc_id)
                            if cnt > 0:
                                document_id = fallback_doc_id
                                retrievable = cnt
            if retrievable <= 0:
                _store_coverage_result(cache_key, False)
                return False
            params = (document_id, config.bge_m3_model_revision, expected_fingerprint)
            dense = int(connection.execute(_DENSE_COVERAGE_SQL, params).fetchone()[0])
            sparse = int(connection.execute(_SPARSE_COVERAGE_SQL, params).fetchone()[0])
            result = dense == retrievable and sparse == retrievable
            _store_coverage_result(cache_key, result)
            return result
        finally:
            connection.close()
    except (OSError, RuntimeError, sqlite3.Error):
        return False


def _backfill_ledger_fingerprint(
    db_path: Path,
    row: SourcePreparationLedgerRow,
    fingerprint: str,
) -> None:
    """Stamp a legacy ledger row after the index itself validated its vectors.

    Best-effort: failures leave the row unstamped and the next gate call
    simply re-validates against the index.
    """
    if not fingerprint:
        return
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        try:
            with conn:
                conn.execute(
                    f"""UPDATE {PREPARATION_LEDGER_TABLE}
                        SET model_fingerprint=?, updated_at=?
                        WHERE source_scope=? AND source_id=?
                          AND (model_fingerprint IS NULL OR model_fingerprint='')""",
                    (fingerprint, time.time(), row.source_scope, row.source_id),
                )
        finally:
            conn.close()
    except sqlite3.Error:
        pass


def _ledger_fingerprint_ready(
    *,
    db_path: Path,
    row: SourcePreparationLedgerRow,
    source: WorkspaceAIContextSource,
    config: WorkspaceChatRagV2CanaryConfig,
    expected_fingerprint: str,
) -> bool:
    """Backend-aware READY check for one ledger row (G2 prepare gate).

    A row counts as ready only when its vectors were produced by the embedding
    backend the E-chain currently selects. ``expected_fingerprint`` is computed
    once per gate call; "" means the backend identity is unknown -> never
    ready (fail closed).

    Rows written before this gate existed carry an empty ``model_fingerprint``.
    For those, the index itself is the authority: ``_durable_semantic_coverage_ready``
    (now fingerprint-aware) validates the vectors and the stamp is backfilled,
    so the next call takes the fast path. A backend switch therefore marks
    sources pending and the worker re-embeds them (self-healing) instead of
    serving vectors from the wrong backend.
    """
    if not expected_fingerprint:
        return False
    if row.model_fingerprint == expected_fingerprint:
        return True
    if row.model_fingerprint:
        # Stamped by a different backend -> stale, needs re-embedding.
        return False
    # Legacy row: validate against the index, then backfill the stamp.
    if _durable_semantic_coverage_ready(source, config):
        _backfill_ledger_fingerprint(db_path, row, expected_fingerprint)
        return True
    return False




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
    phase_timings = _safe_phase_timings(readiness)
    if phase_timings:
        safe_readiness = {**safe_readiness, "phases_ms": phase_timings}
    return {
        "status": "ok",
        "reused": bool(report.get("reused", False)),
        "init_latency_ms": float(report.get("init_latency_ms", 0.0)),
        "readiness": safe_readiness,
    }


def _safe_phase_timings(readiness: Any) -> dict[str, float]:
    """Keep numeric init phase timings only (no paths, no model text)."""
    if not isinstance(readiness, Mapping):
        return {}
    raw = readiness.get("phases_ms")
    if not isinstance(raw, Mapping):
        return {}
    timings: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, (int, float)):
            timings[key] = float(value)
    return timings


def _batch_failure_reason(batch_ordinal: int, batch: tuple[SourceSpec, ...], error: BaseException) -> str:
    """Return a deterministic diagnostic identifier without a filename, path, or text."""
    document_ids = "|".join(spec.document_id for spec in batch)
    opaque_document_id = hashlib.sha256(document_ids.encode("utf-8")).hexdigest()[:12]
    return f"preparation_batch_{batch_ordinal:03d}_document_{opaque_document_id}_{_safe_reason(error)}"


def _warmup_collection_id() -> str | None:
    """Production collection that knowledge questions resolve to, if any.

    Warm-up used to omit the collection id, so it initialized the legacy
    profile-root index while real questions ran on ``collections/<id>``; the
    two configs never matched and every question respawned the worker (PC0575
    SPEED-APP finding, 2026-10-02).
    """
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
    from aios_habit.workspace_chat_store import load_collection

    if load_collection(DEFAULT_COLLECTION_ID) is not None:
        return DEFAULT_COLLECTION_ID
    return None


def _warmup_pipeline_config(
    config: WorkspaceChatRagV2CanaryConfig,
) -> RagV2DevConfig:
    """Read-only pipeline config identical to the interactive query path."""
    return _pipeline_config(
        config,
        config.requested_profile,
        read_only=True,
        collection_id=_warmup_collection_id(),
    )


def _resolve_target_pipe_config(
    config: WorkspaceChatRagV2CanaryConfig,
    *,
    pipe_config: Optional[RagV2DevConfig] = None,
    collection_id: Optional[str] = None,
) -> RagV2DevConfig:
    """Deterministically resolve the target worker pipeline config without global fallback state."""
    if pipe_config is not None:
        return pipe_config
    norm_col = normalize_knowledge_collection(collection_id)
    if norm_col and norm_col not in ("auto", "tri_thuc"):
        return _pipeline_config(
            config,
            config.requested_profile,
            read_only=True,
            collection_id=norm_col,
        )
    return _warmup_pipeline_config(config)


def initialize_workspace_chat_rag_v2_worker(
    config: WorkspaceChatRagV2CanaryConfig,
    *,
    timeout_s: float | None = None,
    pipe_config: RagV2DevConfig | None = None,
    collection_id: str | None = None,
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
        effective_config = _resolve_target_pipe_config(
            config,
            pipe_config=pipe_config,
            collection_id=collection_id,
        )
        return _safe_init_report(
            _SUBPROCESS_CLIENT.initialize_worker(
                effective_config,
                **({"timeout_s": float(timeout_s)} if timeout_s is not None else {}),
            )
        )
    except Exception as exc:
        # BGE-WORKER-FIX-HOME: Tự phục hồi: giải phóng cờ lỗi client để lượt gọi sau có thể thử lại
        _SUBPROCESS_CLIENT.clear_failure_reason()
        raise RuntimeError(f"preparation_init_{_safe_reason(exc)}") from exc


_WARMUP_LOCK = threading.Lock()
_WARMUP_LAST_ATTEMPT_MONO = 0.0
_WARMUP_TTL_SECONDS = 90.0
_WARMUP_ATTEMPTS: dict[str, float] = {}
_WARMUP_IN_QUEUE: set[str] = set()
_WARMUP_RUNNING_KEYS: set[str] = set()


def is_workspace_chat_worker_warmed(
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    pipe_config: Optional[RagV2DevConfig] = None,
    collection_id: Optional[str] = None,
) -> bool:
    """Return whether the local BGE worker subprocess is already usable."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except (DeploymentManifestError, ValueError):
        return False
    if not resolved.enabled or not resolved.requested_profile.startswith("bge_m3_"):
        return False
    try:
        target_pipe_config = _resolve_target_pipe_config(
            resolved,
            pipe_config=pipe_config,
            collection_id=collection_id,
        )
    except (SemanticBackendUnavailable, ValueError, OSError):
        return False
    try:
        if (
            target_pipe_config is not None
            and _SUBPROCESS_CLIENT._persistent_applies(target_pipe_config)
        ):
            flight_key = pipe_name_for_config(target_pipe_config)
            status_probe = _SUBPROCESS_CLIENT._read_persistent_status_file(target_pipe_config)
            if status_probe is not None:
                return bool(status_probe.get("ready", False))
            with _WARMUP_LOCK:
                warming_active = (
                    flight_key in _WARMUP_RUNNING_KEYS
                    or flight_key in _WARMUP_IN_QUEUE
                )
            if warming_active:
                return False
            with _SUBPROCESS_CLIENT._persistent_init_lock:
                if flight_key in _SUBPROCESS_CLIENT._pending_persistent_inits:
                    return False
            if not _pipe_instance_available(flight_key):
                return False
        return bool(_SUBPROCESS_CLIENT.is_ready(target_pipe_config))
    except Exception:
        return False


def get_workspace_chat_worker_progress(
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    pipe_config: Optional[WorkspaceChatBgeSubprocessPipelineConfig] = None,
    collection_id: Optional[str] = None,
) -> dict[str, Any]:
    """Return lightweight snapshot of worker progress for the chat wait loop."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        resolved = None

    target_pipe_config = pipe_config
    if target_pipe_config is None and resolved is not None:
        try:
            target_pipe_config = _resolve_target_pipe_config(
                resolved,
                pipe_config=pipe_config,
                collection_id=collection_id,
            )
        except Exception:
            target_pipe_config = None

    try:
        if target_pipe_config is not None and _SUBPROCESS_CLIENT._persistent_applies(target_pipe_config):
            flight_key = pipe_name_for_config(target_pipe_config)
            with _SUBPROCESS_CLIENT._persistent_init_lock:
                flight = _SUBPROCESS_CLIENT._pending_persistent_inits.get(flight_key)
                pending = flight is not None
                flight_started = flight.get("started", 0.0) if flight else 0.0
            with _WARMUP_LOCK:
                warmup_queued_or_running = (
                    flight_key in _WARMUP_RUNNING_KEYS
                    or flight_key in _WARMUP_IN_QUEUE
                )
            pending = bool(pending or warmup_queued_or_running)

            status_probe = _SUBPROCESS_CLIENT._read_persistent_status_file(target_pipe_config)
            if status_probe is not None:
                p_ready = status_probe
            elif pending:
                p_ready = {
                    "ready": False,
                    "alive": True,
                    "pid": None,
                    "reason": "bge_worker_init_pending",
                }
            elif not _pipe_instance_available(flight_key):
                p_ready = {
                    "ready": False,
                    "alive": False,
                    "pid": None,
                    "reason": "bge_worker_persist_unavailable",
                }
            else:
                p_ready = _SUBPROCESS_CLIENT.readiness(target_pipe_config)
            ready = bool(p_ready.get("ready", False))
            alive = bool(p_ready.get("alive", False)) or pending
            pid = p_ready.get("pid")
            exit_code = None
            last_reason = _SUBPROCESS_CLIENT._last_failure_reason or p_ready.get("reason", "")

            stderr_size = -1
            stderr_mtime = 0.0
            try:
                logs_dir = Path(target_pipe_config.runtime_root) / "logs"
                for fname in ("bge_worker_daemon.stderr.log", "bge_worker.stderr.log"):
                    p = logs_dir / fname
                    if p.is_file():
                        st = p.stat()
                        stderr_size = max(stderr_size, st.st_size)
                        stderr_mtime = max(stderr_mtime, st.st_mtime)
            except Exception:
                pass

            if pending and flight_started > 0.0:
                stderr_mtime = max(stderr_mtime, round(time.time(), 1))
                stderr_size = max(stderr_size, 1)

            return {
                "alive": bool(alive),
                "pid": pid,
                "exit_code": exit_code,
                "pending": bool(pending),
                "ready": bool(ready),
                "reason": ("bge_worker_init_pending" if pending else last_reason),
                "stderr_size": stderr_size,
                "stderr_mtime": stderr_mtime,
            }
        else:
            proc = _SUBPROCESS_CLIENT._process
            alive = proc is not None and proc.poll() is None
            pid = proc.pid if proc is not None else None
            exit_code = proc.poll() if proc is not None else None
            pending = alive and _SUBPROCESS_CLIENT._pending_init is not None
            last_reason = _SUBPROCESS_CLIENT._last_failure_reason
            ready = is_workspace_chat_worker_warmed(
                config=resolved or config,
                pipe_config=target_pipe_config,
                collection_id=collection_id,
            )

            stderr_size = -1
            stderr_mtime = 0.0
            try:
                if target_pipe_config is not None:
                    stderr_path = Path(target_pipe_config.runtime_root) / "logs" / "bge_worker.stderr.log"
                    if stderr_path.is_file():
                        st = stderr_path.stat()
                        stderr_size = st.st_size
                        stderr_mtime = st.st_mtime
            except Exception:
                pass

            return {
                "alive": bool(alive),
                "pid": pid,
                "exit_code": exit_code,
                "pending": bool(pending),
                "ready": bool(ready),
                "reason": ("bge_worker_init_pending" if pending else last_reason),
                "stderr_size": stderr_size,
                "stderr_mtime": stderr_mtime,
            }
    except Exception:
        return {
            "alive": False,
            "pid": None,
            "exit_code": None,
            "pending": False,
            "ready": False,
            "reason": "unavailable",
            "stderr_size": -1,
            "stderr_mtime": 0.0,
        }


_MAX_WARM_COLLECTION_EXECUTORS = 4
_MAX_USER_TARGET_WARM_WORKERS = 2
_BACKGROUND_WARM_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None
_COLLECTION_WARM_EXECUTORS: dict[str, concurrent.futures.ThreadPoolExecutor] = {}
_USER_TARGET_WARM_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None
_BACKGROUND_WARM_LOCK = threading.Lock()

_USER_RETRIEVAL_PRIORITY_LOCK = threading.RLock()
_USER_RETRIEVAL_PRIORITY_CONDITION = threading.Condition(_USER_RETRIEVAL_PRIORITY_LOCK)
_ACTIVE_USER_RETRIEVAL_COLLECTIONS: set[str] = set()
_ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS: dict[str, int] = {}
_ACTIVE_USER_RETRIEVAL_COUNT: int = 0
_PROCEEDED_WARM_COLLECTIONS: set[str] = set()


def normalize_knowledge_collection(collection_id: str | None) -> str | None:
    """Normalize collection alias: tri_thuc, default, legacy all refer to tri_thuc."""
    if not collection_id:
        return None
    c = str(collection_id).strip().lower()
    if c in ("default", "tri_thuc", "legacy"):
        return "tri_thuc"
    return c


def _collection_matches_active(target_col: str | None, active_collections: set[str]) -> bool:
    """Check if target collection matches any currently active user retrieval collection."""
    if not target_col or not active_collections:
        return False
    t_clean = target_col.strip().lower()
    t_canon = normalize_knowledge_collection(t_clean)
    for a in active_collections:
        a_clean = a.strip().lower()
        if t_clean == a_clean:
            return True
        if t_canon and t_canon == normalize_knowledge_collection(a_clean):
            return True
        if t_clean in ("default", "tri_thuc") and a_clean in ("default", "tri_thuc"):
            return True
    return False


def set_user_retrieval_active(collection_id: str | None = None) -> None:
    """Register that a user turn is actively waiting for or executing retrieval.

    When active, background warming for collections OTHER than collection_id
    must yield until the user retrieval finishes (DESKTOP-SPEED-WARM-PRIORITY-FIX-HOME).
    """
    global _ACTIVE_USER_RETRIEVAL_COUNT
    with _USER_RETRIEVAL_PRIORITY_LOCK:
        _ACTIVE_USER_RETRIEVAL_COUNT += 1
        if _ACTIVE_USER_RETRIEVAL_COUNT == 1:
            _PROCEEDED_WARM_COLLECTIONS.clear()
        cols_to_add: set[str] = set()
        if collection_id:
            col_clean = str(collection_id).strip().lower()
            cols_to_add.add(col_clean)
            canon = normalize_knowledge_collection(col_clean)
            if canon:
                cols_to_add.add(canon)
            if col_clean in ("default", "tri_thuc"):
                cols_to_add.add("default")
                cols_to_add.add("tri_thuc")
        for c in cols_to_add:
            _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS[c] = (
                _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS.get(c, 0) + 1
            )
            _ACTIVE_USER_RETRIEVAL_COLLECTIONS.add(c)
        LOGGER.info(
            "[WARM_PRIORITY] User retrieval active: count=%d collections=%s",
            _ACTIVE_USER_RETRIEVAL_COUNT,
            sorted(_ACTIVE_USER_RETRIEVAL_COLLECTIONS),
        )
        _USER_RETRIEVAL_PRIORITY_CONDITION.notify_all()


def set_user_retrieval_finished(collection_id: str | None = None) -> None:
    """Mark that a user turn finished its retrieval phase."""
    global _ACTIVE_USER_RETRIEVAL_COUNT
    with _USER_RETRIEVAL_PRIORITY_LOCK:
        if _ACTIVE_USER_RETRIEVAL_COUNT > 0:
            _ACTIVE_USER_RETRIEVAL_COUNT -= 1
        cols_to_remove: set[str] = set()
        if collection_id:
            col_clean = str(collection_id).strip().lower()
            cols_to_remove.add(col_clean)
            canon = normalize_knowledge_collection(col_clean)
            if canon:
                cols_to_remove.add(canon)
            if col_clean in ("default", "tri_thuc"):
                cols_to_remove.add("default")
                cols_to_remove.add("tri_thuc")
        for c in cols_to_remove:
            if c in _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS:
                _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS[c] -= 1
                if _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS[c] <= 0:
                    _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS.pop(c, None)
                    _ACTIVE_USER_RETRIEVAL_COLLECTIONS.discard(c)
            else:
                _ACTIVE_USER_RETRIEVAL_COLLECTIONS.discard(c)
        if _ACTIVE_USER_RETRIEVAL_COUNT == 0:
            _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS.clear()
            _ACTIVE_USER_RETRIEVAL_COLLECTIONS.clear()
            _PROCEEDED_WARM_COLLECTIONS.clear()
        LOGGER.info(
            "[WARM_PRIORITY] User retrieval finished: count=%d remaining=%s",
            _ACTIVE_USER_RETRIEVAL_COUNT,
            sorted(_ACTIVE_USER_RETRIEVAL_COLLECTIONS),
        )
        _USER_RETRIEVAL_PRIORITY_CONDITION.notify_all()


def update_user_retrieval_collection(collection_id: str | None) -> None:
    """Update or add active collection for the current user retrieval."""
    if not collection_id:
        return
    col_clean = str(collection_id).strip().lower()
    cols_to_add: set[str] = {col_clean}
    canon = normalize_knowledge_collection(col_clean)
    if canon:
        cols_to_add.add(canon)
    if col_clean in ("default", "tri_thuc"):
        cols_to_add.add("default")
        cols_to_add.add("tri_thuc")
    with _USER_RETRIEVAL_PRIORITY_LOCK:
        for c in cols_to_add:
            _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS[c] = (
                _ACTIVE_USER_RETRIEVAL_COLLECTION_COUNTS.get(c, 0) + 1
            )
            _ACTIVE_USER_RETRIEVAL_COLLECTIONS.add(c)
        _USER_RETRIEVAL_PRIORITY_CONDITION.notify_all()


@contextlib.contextmanager
def user_retrieval_priority_scope(collection_id: str | None = None):
    """Context manager to scope user retrieval priority."""
    set_user_retrieval_active(collection_id)
    try:
        yield
    finally:
        set_user_retrieval_finished(collection_id)


def _collection_id_from_pipe_config(pipe_config: RagV2DevConfig | None) -> str | None:
    """Extract clean collection id from RagV2DevConfig or mock object."""
    if pipe_config is None:
        return None
    col = getattr(pipe_config, "collection_id", None)
    if col:
        c_str = str(col).strip().lower()
        if c_str in ("default", "tri_thuc"):
            return "tri_thuc"
        return c_str
    runtime_root = getattr(pipe_config, "runtime_root", None)
    if runtime_root:
        p = Path(runtime_root)
        name_lower = p.name.lower()
        if name_lower in ("lsu", "dieu_tra_loi", "tong_hop", "tri_thuc", "default"):
            return "tri_thuc" if name_lower in ("tri_thuc", "default") else name_lower
        if p.parent.name.lower() == "collections":
            return "tri_thuc" if name_lower in ("tri_thuc", "default") else name_lower
    index_path = getattr(pipe_config, "index_path", None)
    if index_path:
        p = Path(index_path)
        parent_lower = p.parent.name.lower()
        if parent_lower in ("lsu", "dieu_tra_loi", "tong_hop", "tri_thuc", "default"):
            return "tri_thuc" if parent_lower in ("tri_thuc", "default") else parent_lower
    return None


def _check_and_yield_background_warming(
    target_col: str | None,
    target_pipe_config: RagV2DevConfig | None,
    max_yield_timeout_s: float = 60.0,
) -> None:
    """Yield background warming if a user query is currently waiting for retrieval on another collection."""
    yielded = False
    last_yield_log_mono = 0.0
    while True:
        with _USER_RETRIEVAL_PRIORITY_LOCK:
            if _ACTIVE_USER_RETRIEVAL_COUNT <= 0:
                if yielded:
                    col_name = target_col or "unknown"
                    resume_msg = (
                        f"[WARM_PRIORITY_RESUME] Luot truy hoi nguoi dung da xong, khoi '{col_name}' "
                        f"tiep tuc lam am nen timestamp={format_marker_timestamp()}"
                    )
                    LOGGER.info(resume_msg)
                    _safe_print_streaming_marker(resume_msg)
                return

            if _collection_matches_active(target_col, _ACTIVE_USER_RETRIEVAL_COLLECTIONS):
                col_name = target_col or "unknown"
                if col_name not in _PROCEEDED_WARM_COLLECTIONS:
                    _PROCEEDED_WARM_COLLECTIONS.add(col_name)
                    proceed_msg = (
                        f"[WARM_PRIORITY_PROCEED] Khoi '{col_name}' trung voi luot nguoi dung dang cho truy hoi, "
                        f"tien hanh lam am ngay timestamp={format_marker_timestamp()}"
                    )
                    LOGGER.info(proceed_msg)
                    _safe_print_streaming_marker(proceed_msg)
                return

            # Nhường quyền cho lượt người dùng:
            # Cơ chế chọn (DESKTOP-SPEED-PRIORITY-SCOPE-FIX-HOME):
            # Bỏ cơ chế hết hạn cưỡng bức trong lúc lượt người dùng còn đang chờ truy hồi.
            # Trong lúc _ACTIVE_USER_RETRIEVAL_COUNT > 0, các khối không liên quan tiếp tục nhường quyền,
            # KHÔNG tự khởi động lại chỉ vì hết timeout 60s để tránh tranh chấp CPU và I/O.
            col_name = target_col or "unknown"
            active_cols = sorted(_ACTIVE_USER_RETRIEVAL_COLLECTIONS)
            now_mono = time.monotonic()
            if not yielded or (now_mono - last_yield_log_mono >= 10.0):
                now_str = format_marker_timestamp()
                yield_msg = (
                    f"[WARM_PRIORITY_YIELD] Khoi '{col_name}' nhuong cho luot nguoi dung dang cho truy hoi "
                    f"(active_collections={active_cols}) timestamp={now_str}"
                )
                LOGGER.info(yield_msg)
                _safe_print_streaming_marker(yield_msg)
                last_yield_log_mono = now_mono
                yielded = True

            _USER_RETRIEVAL_PRIORITY_CONDITION.wait(timeout=1.0)


def _normalize_warm_executor_key(collection_id: str | None) -> str:
    norm = normalize_knowledge_collection(collection_id)
    if norm in ("tri_thuc", "tong_hop", "lsu", "dieu_tra_loi"):
        return norm
    if norm and norm != "auto":
        return norm
    return "tri_thuc"


def _get_background_warm_executor(
    collection_id: str | None = None,
) -> concurrent.futures.ThreadPoolExecutor:
    """Return a bounded per-collection background warm executor (max_workers=1 per collection)."""
    global _BACKGROUND_WARM_EXECUTOR
    col_key = _normalize_warm_executor_key(collection_id)
    with _BACKGROUND_WARM_LOCK:
        existing = _COLLECTION_WARM_EXECUTORS.get(col_key)
        if existing is not None and not getattr(existing, "_shutdown", False):
            return existing
        if existing is not None:
            _COLLECTION_WARM_EXECUTORS.pop(col_key, None)
        if len(_COLLECTION_WARM_EXECUTORS) < _MAX_WARM_COLLECTION_EXECUTORS:
            executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=f"wsc_bge_warmup_{col_key}",
            )
            _COLLECTION_WARM_EXECUTORS[col_key] = executor
            if col_key == "tri_thuc" and (
                _BACKGROUND_WARM_EXECUTOR is None
                or getattr(_BACKGROUND_WARM_EXECUTOR, "_shutdown", False)
            ):
                _BACKGROUND_WARM_EXECUTOR = executor
            return executor
        if _BACKGROUND_WARM_EXECUTOR is None or getattr(_BACKGROUND_WARM_EXECUTOR, "_shutdown", False):
            _BACKGROUND_WARM_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="wsc_bge_warmup_seq",
            )
        return _BACKGROUND_WARM_EXECUTOR


def _get_user_target_warm_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Return dedicated bounded executor for the active user target collection."""
    global _USER_TARGET_WARM_EXECUTOR
    with _BACKGROUND_WARM_LOCK:
        if _USER_TARGET_WARM_EXECUTOR is None or getattr(_USER_TARGET_WARM_EXECUTOR, "_shutdown", False):
            _USER_TARGET_WARM_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                max_workers=_MAX_USER_TARGET_WARM_WORKERS,
                thread_name_prefix="wsc_bge_warmup_target",
            )
        return _USER_TARGET_WARM_EXECUTOR


def ensure_workspace_chat_worker_warming(
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    blocking: bool = False,
    timeout_s: float | None = None,
    pipe_config: RagV2DevConfig | None = None,
    collection_id: str | None = None,
    verify_probe: bool = False,
    probe_query: str = "touch panel specification",
    probe_domain: str | None = None,
) -> bool:
    """Warm the BGE worker once; throttled so Streamlit reruns stay cheap.

    Non-blocking mode never raises and never blocks a UI rerun. Blocking mode
    returns True only when the worker reports ready. The warm-up uses the same
    read-only production-collection config as the query path, and waits for an
    in-flight init instead of spawning a duplicate when ``timeout_s`` is left
    at its default (``AIOS_BGE_INIT_TIMEOUT`` or 300 s).
    """
    global _WARMUP_LAST_ATTEMPT_MONO, _WARMUP_ATTEMPTS
    now = time.monotonic()

    effective_pipe_config = pipe_config
    if effective_pipe_config is None and collection_id is not None:
        try:
            _tmp_resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
            if _tmp_resolved.enabled and _tmp_resolved.requested_profile.startswith("bge_m3_"):
                effective_pipe_config = _resolve_target_pipe_config(
                    _tmp_resolved,
                    pipe_config=None,
                    collection_id=collection_id,
                )
        except Exception:
            effective_pipe_config = None

    if (
        not blocking
        and effective_pipe_config is not None
        and _SUBPROCESS_CLIENT._persistent_applies(effective_pipe_config)
    ):
        flight_key = pipe_name_for_config(effective_pipe_config)
        with _SUBPROCESS_CLIENT._persistent_init_lock:
            if flight_key in _SUBPROCESS_CLIENT._pending_persistent_inits:
                return True

    warmup_key = "__default__"
    if effective_pipe_config is not None:
        try:
            warmup_key = pipe_name_for_config(effective_pipe_config)
        except Exception:
            warmup_key = str(getattr(effective_pipe_config, "collection_id", None) or "custom")
    elif collection_id is not None:
        norm_col = normalize_knowledge_collection(collection_id)
        if norm_col and norm_col not in ("auto", "tri_thuc"):
            warmup_key = f"__col__:{norm_col}"

    hint_col = (
        _collection_id_from_pipe_config(effective_pipe_config)
        or normalize_knowledge_collection(collection_id)
        or "tri_thuc"
    )
    with _USER_RETRIEVAL_PRIORITY_LOCK:
        is_priority_target = _collection_matches_active(
            hint_col, _ACTIVE_USER_RETRIEVAL_COLLECTIONS
        )

    with _WARMUP_LOCK:
        if _WARMUP_LAST_ATTEMPT_MONO == 0.0 and warmup_key == "__default__":
            _WARMUP_ATTEMPTS.pop(warmup_key, None)
        last_attempt = _WARMUP_ATTEMPTS.get(warmup_key, 0.0)
        if warmup_key == "__default__":
            last_attempt = max(last_attempt, _WARMUP_LAST_ATTEMPT_MONO)
        if not blocking and (now - last_attempt) < _WARMUP_TTL_SECONDS:
            pipe_present = (
                _pipe_instance_available(warmup_key)
                if (warmup_key != "__default__" and warmup_key.startswith("\\\\.\\pipe\\"))
                else False
            )
            if warmup_key == "__default__" or pipe_present:
                return False
        if not blocking and warmup_key in _WARMUP_RUNNING_KEYS:
            return True
        if not blocking and warmup_key in _WARMUP_IN_QUEUE and not is_priority_target:
            return True
        _WARMUP_ATTEMPTS[warmup_key] = now
        if warmup_key == "__default__":
            _WARMUP_LAST_ATTEMPT_MONO = now

    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except (DeploymentManifestError, ValueError):
        return False
    if not resolved.enabled or not resolved.requested_profile.startswith("bge_m3_"):
        return False

    def _warm() -> bool:
        claimed_running = False
        if not blocking:
            with _WARMUP_LOCK:
                if warmup_key in _WARMUP_RUNNING_KEYS:
                    return True
                _WARMUP_RUNNING_KEYS.add(warmup_key)
                claimed_running = True
        try:
            target_pipe_config = effective_pipe_config
            if target_pipe_config is None:
                try:
                    target_pipe_config = _resolve_target_pipe_config(
                        resolved,
                        pipe_config=pipe_config,
                        collection_id=collection_id,
                    )
                except (SemanticBackendUnavailable, ValueError, OSError):
                    target_pipe_config = None
            actual_timeout = timeout_s if blocking else (timeout_s or default_init_timeout_seconds())

            target_col = (
                _collection_id_from_pipe_config(target_pipe_config)
                or normalize_knowledge_collection(collection_id)
            )
            status_probe = (
                _SUBPROCESS_CLIENT._read_persistent_status_file(target_pipe_config)
                if (
                    target_pipe_config is not None
                    and _SUBPROCESS_CLIENT._persistent_applies(target_pipe_config)
                )
                else None
            )
            is_already_ready = bool(status_probe and status_probe.get("ready"))
            if not is_already_ready:
                if blocking:
                    with _USER_RETRIEVAL_PRIORITY_LOCK:
                        if _collection_matches_active(target_col, _ACTIVE_USER_RETRIEVAL_COLLECTIONS):
                            col_name = target_col or "tri_thuc"
                            if col_name not in _PROCEEDED_WARM_COLLECTIONS:
                                _PROCEEDED_WARM_COLLECTIONS.add(col_name)
                                proceed_msg = (
                                    f"[WARM_PRIORITY_PROCEED] Khoi '{col_name}' trung voi luot nguoi dung dang cho truy hoi, "
                                    f"tien hanh lam am ngay timestamp={format_marker_timestamp()}"
                                )
                                LOGGER.info(proceed_msg)
                                _safe_print_streaming_marker(proceed_msg)
                else:
                    _check_and_yield_background_warming(target_col, target_pipe_config)

            initialize_workspace_chat_rag_v2_worker(
                resolved,
                timeout_s=actual_timeout,
                pipe_config=target_pipe_config,
            )
            if (
                target_pipe_config is not None
                and getattr(target_pipe_config, "index_path", None)
                and Path(target_pipe_config.index_path).is_file()
            ):
                with _USER_RETRIEVAL_PRIORITY_LOCK:
                    no_active_user = _ACTIVE_USER_RETRIEVAL_COUNT <= 0
                if no_active_user or blocking:
                    try:
                        from aios_habit import index_domain

                        index_domain.load_all_index_specs(target_pipe_config.index_path)
                        _get_covered_source_fingerprints(
                            target_pipe_config.index_path,
                            read_only=True,
                        )
                    except Exception:
                        pass
            if verify_probe:
                coll_name = (
                    getattr(target_pipe_config, "collection_id", None)
                    or (Path(target_pipe_config.runtime_root).name if target_pipe_config else None)
                    or target_col
                )
                probe_res = probe_workspace_chat_worker(
                    question=probe_query,
                    config=resolved,
                    domain=probe_domain or coll_name,
                )
                return bool(probe_res.get("ready", False))
            return True
        except Exception:
            with _WARMUP_LOCK:
                _WARMUP_ATTEMPTS.pop(warmup_key, None)
            LOGGER.debug("Workspace Chat BGE worker warm-up failed", exc_info=True)
            return False
        finally:
            if not blocking and claimed_running:
                with _WARMUP_LOCK:
                    _WARMUP_RUNNING_KEYS.discard(warmup_key)
                    _WARMUP_IN_QUEUE.discard(warmup_key)

    if blocking:
        return _warm()
    with _WARMUP_LOCK:
        if warmup_key in _WARMUP_RUNNING_KEYS:
            return True
        if warmup_key in _WARMUP_IN_QUEUE and not is_priority_target:
            return True
        _WARMUP_IN_QUEUE.add(warmup_key)
    executor = (
        _get_user_target_warm_executor()
        if is_priority_target
        else _get_background_warm_executor(hint_col)
    )
    executor.submit(_warm)
    return True


def _infer_notebook_domain_collection(nb: Any, default_col: str) -> str:
    """Resolve a notebook's effective collection ID, inferring split domain from title/description when collection_id is default tri_thuc."""
    nb_col = str(getattr(nb, "collection_id", "") or "").strip().lower()
    norm_col = normalize_knowledge_collection(nb_col) if (nb_col and nb_col != "auto") else default_col
    if norm_col and norm_col != default_col:
        return norm_col
    try:
        from aios_habit import index_domain

        title_desc = f"{getattr(nb, 'title', '') or ''} {getattr(nb, 'description', '') or ''}".strip()
        if title_desc:
            detected = index_domain.detect_domain_from_question(title_desc)
            if (
                detected is not None
                and getattr(detected, "confidence", 0.0) >= index_domain.CONFIDENCE_LOW_THRESHOLD
                and detected.domain in ("lsu", "dieu_tra_loi", "tong_hop")
            ):
                return detected.domain
    except Exception:
        pass
    return norm_col or default_col


def resolve_active_notebook_collection_id(
    *,
    active_notebook_id: Optional[str] = None,
    active_collection_id: Optional[str] = None,
) -> str:
    """Resolve the single target collection ID to warm on startup or notebook open.

    Requirements (DESKTOP-SPEED-LAZY-WARM-HOME):
    - Only warm the collection of the currently opened/default notebook on startup.
    - Never eagerly warm all 4 collections at once.
    """
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID

    raw_col = str(active_collection_id or "").strip().lower()
    norm_explicit = normalize_knowledge_collection(raw_col) if (raw_col and raw_col != "auto") else None
    if norm_explicit and norm_explicit != DEFAULT_COLLECTION_ID:
        return norm_explicit

    try:
        from aios_habit.workspace_chat_store import load_active_notebooks, load_notebook

        nb_id = str(active_notebook_id or "").strip()
        if nb_id:
            nb = load_notebook(nb_id)
            if nb is None:
                nb = next((n for n in load_active_notebooks() if n.id == nb_id), None)
            if nb is not None:
                return _infer_notebook_domain_collection(nb, DEFAULT_COLLECTION_ID)

        if norm_explicit:
            return norm_explicit

        notebooks = load_active_notebooks()
        if notebooks:
            return _infer_notebook_domain_collection(notebooks[0], DEFAULT_COLLECTION_ID)
    except Exception:
        pass

    return norm_explicit or DEFAULT_COLLECTION_ID


def ensure_workspace_chat_startup_warming(
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    collections: Optional[Sequence[str]] = None,
    active_notebook_id: Optional[str] = None,
    active_collection_id: Optional[str] = None,
) -> dict[str, bool]:
    """Trigger background non-blocking warming for startup collection(s).

    Requirements (DESKTOP-SPEED-LAZY-WARM-HOME):
    - By default (collections=None), ONLY warm the collection of the active/default
      notebook (active_notebook_id / active_collection_id), and DO NOT warm the
      remaining 3 collections on startup.
    - When ``collections`` is explicitly passed (legacy multi-collection tests),
      warms the requested collections in background (blocking=False).
    - An error warming one collection must NOT crash the app or block others.
    """
    results: dict[str, bool] = {}

    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception as exc:
        LOGGER.warning("Could not resolve canary config for startup warming: %s", exc)
        return results

    if not resolved.enabled or not resolved.requested_profile.startswith("bge_m3_"):
        return results

    profile = resolved.requested_profile

    if collections is None:
        target_col = resolve_active_notebook_collection_id(
            active_notebook_id=active_notebook_id,
            active_collection_id=active_collection_id,
        )
        if target_col in ("tri_thuc", "default"):
            try:
                tri_thuc_pipe_cfg = _warmup_pipeline_config(resolved)
                results["tri_thuc"] = ensure_workspace_chat_worker_warming(
                    config=resolved,
                    blocking=False,
                    pipe_config=tri_thuc_pipe_cfg,
                    collection_id="tri_thuc",
                )
            except Exception as exc:
                LOGGER.warning("Startup warming failed for tri_thuc: %s", exc)
                results["tri_thuc"] = False
        else:
            try:
                p_cfg = _pipeline_config(
                    resolved,
                    profile,
                    read_only=True,
                    collection_id=target_col,
                )
                if getattr(p_cfg, "index_path", None) and p_cfg.index_path.is_file():
                    started = ensure_workspace_chat_worker_warming(
                        config=resolved,
                        blocking=False,
                        pipe_config=p_cfg,
                        collection_id=target_col,
                    )
                    results[target_col] = started
                else:
                    LOGGER.info("Startup warming skipped for '%s': index file not found", target_col)
                    results[target_col] = False
            except Exception as exc:
                LOGGER.warning("Startup warming failed for collection '%s': %s", target_col, exc)
                results[target_col] = False
        return results

    explicit_cols = [str(c).strip() for c in collections if str(c).strip()]
    include_tri_thuc = (
        "tri_thuc" in explicit_cols
        or "default" in explicit_cols
        or set(explicit_cols) == {"tong_hop", "lsu", "dieu_tra_loi"}
    )
    for col_id in explicit_cols:
        if col_id in ("tri_thuc", "default"):
            continue
        try:
            p_cfg = _pipeline_config(
                resolved,
                profile,
                read_only=True,
                collection_id=col_id,
            )
            if getattr(p_cfg, "index_path", None) and p_cfg.index_path.is_file():
                started = ensure_workspace_chat_worker_warming(
                    config=resolved,
                    blocking=False,
                    pipe_config=p_cfg,
                    collection_id=col_id,
                )
                results[col_id] = started
            else:
                LOGGER.info("Startup warming skipped for '%s': index file not found", col_id)
                results[col_id] = False
        except Exception as exc:
            LOGGER.warning("Startup warming failed for collection '%s': %s", col_id, exc)
            results[col_id] = False

    if include_tri_thuc:
        try:
            tri_thuc_pipe_cfg = _warmup_pipeline_config(resolved)
            results["tri_thuc"] = ensure_workspace_chat_worker_warming(
                config=resolved,
                blocking=False,
                pipe_config=tri_thuc_pipe_cfg,
                collection_id="tri_thuc",
            )
        except Exception as exc:
            LOGGER.warning("Startup warming failed for tri_thuc: %s", exc)
            results["tri_thuc"] = False

    return results


def probe_workspace_chat_worker(
    question: str = "touch panel specification",
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    domain: Optional[str] = None,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Execute an honest retrieval probe against the BGE worker subprocess.

    Requirements (DESKTOP-SPEED-WORKER-INIT-GUARD-HOME & DESKTOP-SPEED-WARM-ALIGNMENT-FIX-HOME):
    - Probe returning 0 chunks MUST NOT report worker ready (ready=False, ok=False).
    - Probe under persistent mode MUST verify from turn perspective (named pipe exists + is_ready True)
      before reporting worker ready (ready=True, ok=True).
    - Logs distinguish 'worker song nhung probe rong' (alive but empty probe)
      vs 'worker san sang that' (truly ready with >= 1 chunks).
    """
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        resolved = None

    if resolved is None or not resolved.enabled or not resolved.requested_profile.startswith("bge_m3_"):
        LOGGER.warning("Worker probe skipped: config not enabled for bge_m3")
        return {
            "ok": False,
            "ready": False,
            "alive": False,
            "chunks": 0,
            "domain": domain,
            "reason": "bge_not_enabled",
            "message": "worker song nhung probe rong",
        }

    target_pipe_config = None
    try:
        if domain is not None:
            target_pipe_config = _pipeline_config(resolved, resolved.requested_profile, read_only=True, collection_id=domain)
        else:
            target_pipe_config = _warmup_pipeline_config(resolved)
    except Exception:
        pass
    is_alive = False
    try:
        if target_pipe_config and _SUBPROCESS_CLIENT._persistent_applies(target_pipe_config):
            readiness = _SUBPROCESS_CLIENT.readiness(target_pipe_config)
            is_alive = bool(readiness.get("alive", False))
        else:
            is_alive = _SUBPROCESS_CLIENT.is_alive()
    except Exception:
        is_alive = False

    try:
        probe_res = retrieve_workspace_chat_evidence(
            question,
            (),
            forced_domain=domain,
        )
        chunk_count = int(probe_res.get("summary_count", 0))
        status = str(probe_res.get("status", ""))
    except Exception as exc:
        chunk_count = 0
        status = f"error_{type(exc).__name__}"

    turn_perspective_ready = True
    turn_perspective_reason = ""
    if target_pipe_config is not None and _SUBPROCESS_CLIENT._persistent_applies(target_pipe_config):
        p_name = pipe_name_for_config(target_pipe_config)
        pipe_ok = _pipe_instance_available(p_name)
        client_ready = bool(_SUBPROCESS_CLIENT.is_ready(target_pipe_config))
        turn_perspective_ready = bool(pipe_ok and client_ready)
        if not turn_perspective_ready:
            turn_perspective_reason = f"pipe_exists={pipe_ok}, is_ready={client_ready}"

    if chunk_count > 0 and status != "quality_search_unavailable" and turn_perspective_ready:
        LOGGER.info(
            "BGE worker warm probe ready: worker san sang that (chunks=%d, domain=%s)",
            chunk_count,
            domain or "auto",
        )
        _safe_print_streaming_marker(
            f"[WORKER_PROBE] status=ready chunks={chunk_count} domain={domain or 'auto'} worker san sang that"
        )
        return {
            "ok": True,
            "ready": True,
            "alive": True,
            "chunks": chunk_count,
            "domain": domain,
            "reason": "worker san sang that",
            "message": "worker san sang that",
        }
    else:
        fail_reason = "worker song nhung probe rong"
        if not turn_perspective_ready:
            fail_reason = f"worker probe tra ve nhung duong luot chua san sang ({turn_perspective_reason})"
        LOGGER.warning(
            "BGE worker warm probe not ready: %s (chunks=%d, domain=%s, status=%s)",
            fail_reason,
            chunk_count,
            domain or "auto",
            status,
        )
        _safe_print_streaming_marker(
            f"[WORKER_PROBE] status={'empty' if chunk_count == 0 else 'unaligned'} chunks={chunk_count} domain={domain or 'auto'} {fail_reason}"
        )
        return {
            "ok": False,
            "ready": False,
            "alive": is_alive,
            "chunks": chunk_count,
            "domain": domain,
            "reason": fail_reason,
            "message": fail_reason,
        }


def _collection_id_for_sources(context_sources: Iterable[WorkspaceAIContextSource]) -> str | None:
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID, SOURCE_SCOPE_NOTEBOOK
    from aios_habit.workspace_chat_store import (
        load_collection,
        resolve_collection_id_from_notebook_source_id,
    )

    for raw_source in context_sources:
        source = _coerce_context_source(raw_source)
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
    coerced_context_sources = tuple(_coerce_context_source(s) for s in context_sources)
    sources = tuple(s for s in coerced_context_sources if (s.text or "").strip())
    if not sources:
        return {"status": "ok", "prepared_count": 0, "latency_ms": 0.0}
    if source_timeout_s is not None and float(source_timeout_s) <= 0:
        raise ValueError("source_timeout_s must be positive")

    target_collection_id = _collection_id_for_sources(sources)
    if is_production_sealed_collection(target_collection_id):
        raise ReadOnlyIndexViolationError(
            f"Chặn ghi vào kho production đã đóng dấu '{target_collection_id or 'tri_thuc'}'. "
            "Chỉ mục production là chỉ đọc tuyệt đối và không nhận nguồn chuẩn bị mới."
        )

    profile = resolved.requested_profile
    pipe_config = _pipeline_config(
        resolved,
        profile,
        # Explicit read_only=False: preparing and ingesting source chunks and
        # embeddings for eligible non-production collections. The sealed
        # production collection ('tri_thuc') is strictly guarded above.
        read_only=False,
        collection_id=target_collection_id,
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
                            group_size=16,
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
        if "timeout" in reason or "bge_worker" in reason:
            _SUBPROCESS_CLIENT.clear_failure_reason()
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
    """Create the ledger and reclaim interrupted work once per app process.

    Streamlit re-runs the UI frequently.  Reclaiming every ``processing`` row
    during each read made a healthy background worker appear paused.  A fresh
    Python process still reclaims work left by a previous process, but normal
    UI refreshes now leave an active worker alone.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_identity = str(db_path.resolve())
    with _PREPARATION_LEDGER_INIT_LOCK:
        recover_interrupted_work = ledger_identity not in _PREPARATION_LEDGER_INITIALIZED_PATHS
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
                # G2 backend-aware prepare gate: older ledgers lack the column.
                try:
                    existing_columns = {
                        info[1]
                        for info in conn.execute(
                            f"PRAGMA table_info({PREPARATION_LEDGER_TABLE})"
                        ).fetchall()
                    }
                    if "model_fingerprint" not in existing_columns:
                        conn.execute(
                            f"""ALTER TABLE {PREPARATION_LEDGER_TABLE}
                                ADD COLUMN model_fingerprint TEXT NOT NULL DEFAULT ''"""
                        )
                except sqlite3.Error:
                    pass
                if recover_interrupted_work:
                    # Only a newly started application can reclaim a row left
                    # behind by an interrupted earlier process.
                    conn.execute(
                        f"""UPDATE {PREPARATION_LEDGER_TABLE}
                            SET state = '{PREP_STATE_PENDING}', updated_at = ?
                            WHERE state = '{PREP_STATE_PROCESSING}'""",
                        (time.time(),),
                    )
            _PREPARATION_LEDGER_INITIALIZED_PATHS.add(ledger_identity)
        finally:
            conn.close()


def _background_preparation_is_running() -> bool:
    """Return whether this application process currently owns the queue drain."""
    with _DRAIN_RUNNING_LOCK:
        return _DRAIN_IS_RUNNING


def _load_ledger_row(db_path: Path, source_scope: str, source_id: str) -> SourcePreparationLedgerRow | None:
    if not db_path.is_file():
        return None
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cur = conn.execute(
            f"""SELECT source_scope, source_id, source_fingerprint, model_id, model_revision,
                       state, priority, attempt_count, last_error, document_id, created_at, updated_at,
                       model_fingerprint
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
                       state, priority, attempt_count, last_error, document_id, created_at, updated_at,
                       model_fingerprint
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
                    state, priority, attempt_count, last_error, document_id, created_at, updated_at,
                    model_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_scope, source_id) DO UPDATE SET
                    source_fingerprint=excluded.source_fingerprint,
                    model_id=excluded.model_id,
                    model_revision=excluded.model_revision,
                    state=excluded.state,
                    priority=excluded.priority,
                    attempt_count=excluded.attempt_count,
                    last_error=excluded.last_error,
                    document_id=excluded.document_id,
                    updated_at=excluded.updated_at,
                    model_fingerprint=excluded.model_fingerprint""",
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
                    row.model_fingerprint,
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
            # A second drainer must never receive work already owned by the
            # current worker.  It exits and lets the owner commit the result.
            cur = conn.execute(
                f"""SELECT source_scope, source_id, source_fingerprint, model_id, model_revision,
                           state, priority, attempt_count, last_error, document_id, created_at, updated_at,
                           model_fingerprint
                    FROM {PREPARATION_LEDGER_TABLE}
                    WHERE state = '{PREP_STATE_PROCESSING}'
                    LIMIT 1"""
            )
            existing_proc = cur.fetchone()
            if existing_proc:
                return None

            cur = conn.execute(
                f"""SELECT source_scope, source_id, source_fingerprint, model_id, model_revision,
                           state, priority, attempt_count, last_error, document_id, created_at, updated_at,
                           model_fingerprint
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
                    model_fingerprint=row[12] if len(row) > 12 else "",
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
    *,
    model_fingerprint: str = "",
) -> None:
    if not db_path.is_file():
        return
    now = time.time()
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        with conn:
            if state == PREP_STATE_READY and model_fingerprint:
                conn.execute(
                    f"""UPDATE {PREPARATION_LEDGER_TABLE}
                        SET state = ?, model_fingerprint = ?, last_error = ?, updated_at = ?
                        WHERE source_scope = ? AND source_id = ?""",
                    (state, model_fingerprint, error_reason, now, source_scope, source_id),
                )
            else:
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

    coerced_context_sources = tuple(_coerce_context_source(s) for s in context_sources)
    sources = tuple(s for s in coerced_context_sources if (s.text or "").strip())
    total_count = len(sources)
    if resolved is None or not resolved.enabled:
        statuses = {
            f"{s.source_scope}:{s.source_id}": "unavailable"
            for s in coerced_context_sources
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
            "worker_running": False,
            "preparation_state": "unavailable",
            "completed": 0,
            "progress_percent": 0,
        }

    db_path = _get_ledger_db_path(resolved)
    _init_preparation_ledger_db(db_path)
    ledger_rows = _load_all_ledger_rows(db_path)
    # G2 backend-aware prepare gate, computed once per summary call.
    expected_fingerprint = _expected_backend_fingerprint(resolved)

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
            content_ready = (
                row.state == PREP_STATE_READY
                and row.source_fingerprint == _source_fingerprint(source)
                and row.model_revision == resolved.bge_m3_model_revision
            )
            if content_ready and _ledger_fingerprint_ready(
                db_path=db_path,
                row=row,
                source=source,
                config=resolved,
                expected_fingerprint=expected_fingerprint,
            ):
                state = PREP_STATE_READY
            elif row.state == PREP_STATE_FAILED:
                state = PREP_STATE_FAILED
            elif row.state == PREP_STATE_PROCESSING:
                state = PREP_STATE_PROCESSING
            elif content_ready:
                # Ledger says READY but the vectors were not produced by the
                # backend the E-chain currently selects: report pending so the
                # scheduler (reconcile) re-prepares them; never the memory
                # fast path.
                state = PREP_STATE_PENDING
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
        else:
            # A source with no durable row is still waiting for preparation.
            pending_count += 1

    worker_running = _background_preparation_is_running()
    # The progress bar represents documents ready for trustworthy search, not
    # attempts that ended in an error.  A failed document must never make the
    # library look 100% ready.
    completed = ready_count
    progress_percent = int(round((completed * 100) / total_count)) if total_count else 0
    if ready_count == total_count:
        preparation_state = "ready"
    elif worker_running and (processing_count > 0 or pending_count > 0):
        preparation_state = "running"
    elif failed_count > 0:
        preparation_state = "needs_attention"
    else:
        preparation_state = "paused"

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
        "worker_running": worker_running,
        "preparation_state": preparation_state,
        "completed": completed,
        "progress_percent": progress_percent,
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

    coerced_context_sources = tuple(_coerce_context_source(s) for s in context_sources)
    sources = tuple(s for s in coerced_context_sources if (s.text or "").strip())
    if not sources:
        return 0

    db_path = _get_ledger_db_path(resolved)
    _init_preparation_ledger_db(db_path)
    existing_rows = _load_all_ledger_rows(db_path)

    # G2 backend-aware prepare gate: only a row stamped with the backend the
    # E-chain currently selects counts as prepared. Rows stamped by another
    # backend (or legacy rows whose vectors do not match) are re-prepared, so a
    # backend switch self-recovers instead of serving stale vectors.
    expected_fingerprint = _expected_backend_fingerprint(resolved)

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

        if getattr(source, "source_scope", "") == SOURCE_SCOPE_NOTEBOOK:
            # APP-SOURCE-MODEL: Tài liệu notebook trong kho production đã được index sẵn.
            # Đánh dấu ready tức thì, không đưa vào hàng đợi chuẩn bị lại.
            with _PREPARATION_LOCK:
                _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                    _preparation_entry(resolved, source, PREP_STATE_READY)
                )
            continue

        if (
            row is not None
            and row.state == PREP_STATE_READY
            and row.source_fingerprint == current_fp
            and row.model_revision == resolved.bge_m3_model_revision
        ):
            if _ledger_fingerprint_ready(
                db_path=db_path,
                row=row,
                source=source,
                config=resolved,
                expected_fingerprint=expected_fingerprint,
            ):
                with _PREPARATION_LOCK:
                    _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                        _preparation_entry(resolved, source, PREP_STATE_READY)
                    )
                continue
            if not expected_fingerprint:
                # Backend identity unknown: preserve the row untouched (the
                # worker cannot validate or rebuild it), but do not claim
                # ready. The summary gate reports pending (fail closed).
                continue
            # Stale backend (or legacy row the index cannot validate):
            # fall through and re-enqueue for self-healing.

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
                # _durable_semantic_coverage_ready only passes when the index
                # vectors match the current backend, so the stamp is valid.
                model_fingerprint=expected_fingerprint,
            )
            _upsert_ledger_row(db_path, ready_row)
            continue

        if (
            row is not None
            and row.state == PREP_STATE_FAILED
            and row.source_fingerprint == current_fp
            and priority != PREP_PRIORITY_INTERACTIVE
            and row.last_error not in _RETRYABLE_PREPARATION_ERRORS
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


def resolve_drain_durable_fallback() -> bool:
    """Return whether a cache miss may reload text from the durable source record."""
    raw = str(os.environ.get(DRAIN_DURABLE_FALLBACK_FLAG, "") or "").strip().casefold()
    return raw in _TRUE_VALUES


def _context_source_from_durable_record(source_scope: str, record: Any) -> Optional[WorkspaceAIContextSource]:
    text = str(getattr(record, "content_text", "") or getattr(record, "content_preview", "") or "").strip()
    if not text:
        return None
    return WorkspaceAIContextSource(
        source_id=str(getattr(record, "id", "") or ""),
        source_scope=source_scope,
        source_type=str(getattr(record, "source_type", "") or "plain_text"),
        title=str(getattr(record, "title", "") or getattr(record, "id", "") or ""),
        privacy_label=str(getattr(record, "privacy_label", "") or "local_only"),
        text=text,
        included_chars=len(text),
        truncated=False,
        managed_path=str(getattr(record, "managed_path", "") or ""),
    )


def _load_durable_context_source(source_scope: str, source_id: str) -> Optional[WorkspaceAIContextSource]:
    """Reload extracted text from the durable chat store. Does not use the RAM cache."""
    from aios_habit.workspace_chat_models import SOURCE_SCOPE_NOTEBOOK, SOURCE_SCOPE_TEMPORARY
    from aios_habit.workspace_chat_store import get_notebook_source, load_all_temporary_sources

    scope = str(source_scope or "")
    wanted = str(source_id or "")
    if not wanted:
        return None
    if scope == SOURCE_SCOPE_NOTEBOOK:
        record = get_notebook_source(wanted)
    elif scope == SOURCE_SCOPE_TEMPORARY:
        record = next((item for item in load_all_temporary_sources() if item.id == wanted), None)
    else:
        return None
    if record is None:
        return None
    return _context_source_from_durable_record(scope, record)


def _source_for_drain_item(source_scope: str, source_id: str) -> Optional[WorkspaceAIContextSource]:
    """Prefer the RAM cache. The durable store is consulted only when the flag is on."""
    source_key = (source_scope, source_id)
    with _SOURCE_CACHE_LOCK:
        cached = _SOURCE_CACHE.get(source_key)
    if cached is not None and (cached.text or "").strip():
        return cached
    if not resolve_drain_durable_fallback():
        return None
    durable = _load_durable_context_source(source_scope, source_id)
    if durable is None or not (durable.text or "").strip():
        return None
    with _SOURCE_CACHE_LOCK:
        _SOURCE_CACHE[source_key] = durable
    LOGGER.info(
        "rag_v2.drain durable_fallback scope=%s source_id=%s chars=%s",
        source_scope,
        source_id,
        len(durable.text),
    )
    return durable


def _drain_preparation_queue(config: WorkspaceChatRagV2CanaryConfig) -> None:
    global _DRAIN_IS_RUNNING
    db_path = _get_ledger_db_path(config)
    # G2 backend-aware prepare gate: stamp READY rows with the backend that
    # actually produced the vectors (computed once per drain run).
    drain_fingerprint = _expected_backend_fingerprint(config)
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

            source = _source_for_drain_item(item.source_scope, item.source_id)

            if source is None or not (source.text or "").strip():
                _commit_preparation_result(
                    db_path,
                    item.source_scope,
                    item.source_id,
                    PREP_STATE_FAILED,
                    error_reason="source_text_unavailable",
                )
                continue

            target_collection = _collection_id_for_sources((source,))
            if is_production_sealed_collection(target_collection):
                # Guard against writing to sealed production collection 'tri_thuc'.
                # Existing documents from 889 corpus must be recognized as READY without preparation.
                if _durable_semantic_coverage_ready(source, config):
                    _commit_preparation_result(
                        db_path,
                        item.source_scope,
                        item.source_id,
                        PREP_STATE_READY,
                        model_fingerprint=drain_fingerprint,
                    )
                    with _PREPARATION_LOCK:
                        _PREPARATION_REGISTRY[_preparation_key(config, source)] = (
                            _preparation_entry(config, source, PREP_STATE_READY)
                        )
                    continue
                else:
                    err_msg = (
                        f"readonly_index_violation: cannot prepare sources for sealed production collection "
                        f"'{target_collection or 'tri_thuc'}'"
                    )
                    LOGGER.error(
                        "rag_v2.drain %s scope=%s source_id=%s",
                        err_msg,
                        item.source_scope,
                        item.source_id,
                    )
                    _commit_preparation_result(
                        db_path,
                        item.source_scope,
                        item.source_id,
                        PREP_STATE_FAILED,
                        error_reason="readonly_index_violation",
                    )
                    with _PREPARATION_LOCK:
                        _PREPARATION_REGISTRY[_preparation_key(config, source)] = (
                            _preparation_entry(config, source, PREP_STATE_FAILED, reason=err_msg)
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
                    model_fingerprint=drain_fingerprint,
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
                    import time
                    time.sleep(1.0)
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
    sources = tuple(_coerce_context_source(s) for s in context_sources)
    if not sources:
        return
    db_path = _get_ledger_db_path(resolved)
    # A stale page can race an active worker.  Never delete its processing
    # claim; failed rows can safely be queued behind the active item instead.
    retryable_sources = []
    for source in sources:
        row = _load_ledger_row(db_path, source.source_scope, source.source_id)
        if row is None or row.state != PREP_STATE_PROCESSING:
            retryable_sources.append(source)
    if not retryable_sources:
        return
    with _PREPARATION_LOCK:
        for source in retryable_sources:
            _PREPARATION_REGISTRY.pop(_preparation_key(resolved, source), None)
    _delete_ledger_rows(
        db_path,
        [(source.source_scope, source.source_id) for source in retryable_sources],
    )
    reconcile_and_enqueue_workspace_chat_sources(
        tuple(retryable_sources),
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
    coerced_context_sources = tuple(_coerce_context_source(s) for s in context_sources)
    sources = tuple(source for source in coerced_context_sources if (source.text or "").strip())
    if sources:
        with _SOURCE_CACHE_LOCK:
            for source in sources:
                _SOURCE_CACHE[(source.source_scope, source.source_id)] = source
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
    sources = tuple(_coerce_context_source(s) for s in context_sources)
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
    coerced_context_sources = tuple(_coerce_context_source(source) for source in context_sources)
    actual_sources = tuple(source for source in coerced_context_sources if (source.text or "").strip())
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
    for raw_source in sources:
        source = _coerce_context_source(raw_source)
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
    per_document_limit: int | None = None,
    question: str | None = None,
    is_named_document_query: bool = False,
) -> dict[str, Any]:

    evidence_items = []
    retrieved_sources = []
    citations = []
    per_source_counts: Counter[str] = Counter()
    doc_chunk_counts: Counter[str] = Counter()
    summary_dict = query_result.get("summary", {})
    insufficiency_reasons = query_result.get("insufficiency_reasons", [])

    effective_doc_cap = (
        per_document_limit
        if per_document_limit is not None and per_document_limit > 0
        else int(os.environ.get(PER_DOCUMENT_LIMIT_ENV, os.environ.get("AIOS_RETRIEVAL_DOC_DIVERSITY_CAP", "3")) or "3")
    )
    is_single_source = len(originals) <= 1

    for item in query_result.get("items", []):
        original = originals.get(item.get("document_id", ""))
        if original is None:
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        raw_title = (original.title or "").strip()
        doc_key = (
            raw_title.split(" (")[0].strip().casefold()
            if raw_title
            else (
                Path(original.managed_path).name.strip().casefold()
                if original.managed_path
                else str(item.get("document_id") or original.source_id or "").strip().casefold()
            )
        )
        is_named_doc = bool(
            is_single_source
            or is_named_document_query
            or (
                question
                and (
                    (raw_title and raw_title.casefold() in question.casefold())
                    or (original.source_id and original.source_id.casefold() in question.casefold())
                    or (item.get("document_id") and str(item.get("document_id")).casefold() in question.casefold())
                )
            )
        )
        if not is_named_doc and doc_chunk_counts[doc_key] >= effective_doc_cap:
            LOGGER.info(
                "adapter.diversity_cap_triggered doc_key=%s limit=%d chunk_id=%s",
                doc_key,
                effective_doc_cap,
                item.get("evidence_id") or item.get("citation_id"),
            )
            continue
        doc_chunk_counts[doc_key] += 1

        title = sanitize_citation_title(original.title)
        location = _serialized_location(item)
        score = float(item.get("score", 0.0))
        citation_id = str(item.get("citation_id", ""))
        evidence_id = str(item.get("evidence_id", ""))
        index = len(evidence_items) + 1

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
    returned_count = summary_count
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
        "lexical_latency_ms": float(summary_dict.get("lexical_latency_ms", 0.0) or 0.0),
        "context_expansion_latency_ms": float(summary_dict.get("context_expansion_latency_ms", 0.0) or 0.0),
        "dense_latency_ms": float(summary_dict.get("dense_latency_ms", 0.0) or 0.0),
        "sparse_latency_ms": float(summary_dict.get("sparse_latency_ms", 0.0) or 0.0),
        "fusion_latency_ms": float(summary_dict.get("fusion_latency_ms", 0.0) or 0.0),
        "embed_latency_ms": float(summary_dict.get("embed_latency_ms", 0.0) or 0.0),
        "dense_load_latency_ms": float(summary_dict.get("dense_load_latency_ms", 0.0) or 0.0),
        "dense_resident": bool(summary_dict.get("dense_resident", True)),
        "coverage_verify_ms": float(summary_dict.get("coverage_verify_ms", 0.0) or 0.0),
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
        "line_log_attached": False,
    }


_INDEX_FINGERPRINT_CACHE: dict[tuple[str, int, int], dict[str, Optional[str]]] = {}
_INDEX_FINGERPRINT_FULL_SCANNED: set[tuple[str, int, int]] = set()
_INDEX_COVERED_DOC_IDS_CACHE: dict[tuple[str, int, int], set[str]] = {}
_INDEX_COVERED_DOC_STATUS_CACHE: dict[tuple[str, int, int], dict[str, bool]] = {}
_INDEX_COVERED_FULL_SCANNED: set[tuple[str, int, int]] = set()
_DOMAIN_SPECS_QUERY_CACHE: dict[tuple[str, str, int, int, tuple[str, ...]], tuple[Any, ...]] = {}
_PREWARMING_DOMAIN_SPECS_KEYS: set[tuple[str, str, tuple[str, ...]]] = set()
_INDEX_FINGERPRINT_LOCK = threading.Lock()


def clear_covered_source_fingerprints_cache() -> None:
    """Clear the in-memory cache of index document fingerprints."""
    with _INDEX_FINGERPRINT_LOCK:
        _INDEX_FINGERPRINT_CACHE.clear()
        _INDEX_FINGERPRINT_FULL_SCANNED.clear()
        _INDEX_COVERED_DOC_IDS_CACHE.clear()
        _INDEX_COVERED_DOC_STATUS_CACHE.clear()
        _INDEX_COVERED_FULL_SCANNED.clear()
        _DOMAIN_SPECS_QUERY_CACHE.clear()
        _PREWARMING_DOMAIN_SPECS_KEYS.clear()


def _get_cached_specs_for_domain(
    target_domain: Optional[str],
    spec_index_path: Path | str,
    question: Optional[str] = None,
) -> tuple[Any, ...]:
    """Return domain SourceSpecs with an in-memory cache keyed by index file stat and exact mechanical IDs."""
    from aios_habit import index_domain

    resolved_path = Path(spec_index_path).resolve()
    if not resolved_path.is_file():
        return tuple(index_domain.get_specs_for_domain(target_domain, spec_index_path, question=question))
    try:
        stat = resolved_path.stat()
    except OSError:
        return tuple(index_domain.get_specs_for_domain(target_domain, spec_index_path, question=question))

    matched_named_ids: tuple[str, ...] = ()
    if question:
        try:
            matched_named, _ = index_domain.match_named_documents(question, db_path=resolved_path)
            if matched_named:
                matched_named_ids = tuple(sorted(s.document_id for s in matched_named))
        except Exception:
            pass
    exact_ids = tuple(index_domain.extract_exact_mechanical_identifiers(str(question or "")))
    cache_key = (
        str(target_domain or "").strip().lower(),
        str(resolved_path),
        stat.st_mtime_ns,
        stat.st_size,
        exact_ids,
        matched_named_ids,
    )
    with _INDEX_FINGERPRINT_LOCK:
        cached = _DOMAIN_SPECS_QUERY_CACHE.get(cache_key)
        if cached is not None:
            return cached

    specs = tuple(
        index_domain.get_specs_for_domain(
            target_domain,
            resolved_path,
            question=question,
        )
    )
    with _INDEX_FINGERPRINT_LOCK:
        _DOMAIN_SPECS_QUERY_CACHE[cache_key] = specs
    return specs


def _prewarm_domain_specs_async(
    target_domain: Optional[str],
    spec_index_path: Path | str,
    question: Optional[str] = None,
) -> None:
    """Pre-warm domain specs and read-only covered doc_ids in background while worker is initializing."""
    from aios_habit import index_domain

    try:
        resolved_path = Path(spec_index_path).resolve()
        if not resolved_path.is_file():
            return
    except Exception:
        return

    exact_ids = tuple(index_domain.extract_exact_mechanical_identifiers(str(question or "")))
    dedup_key = (
        str(target_domain or "").strip().lower(),
        str(resolved_path),
        exact_ids,
    )
    with _INDEX_FINGERPRINT_LOCK:
        if dedup_key in _PREWARMING_DOMAIN_SPECS_KEYS:
            return
        _PREWARMING_DOMAIN_SPECS_KEYS.add(dedup_key)

    def _run_prewarm() -> None:
        try:
            specs = _get_cached_specs_for_domain(target_domain, resolved_path, question=question)
            cand_ids = [s.document_id for s in specs if getattr(s, "document_id", None)]
            _get_covered_source_fingerprints(
                resolved_path,
                candidate_doc_ids=cand_ids or None,
                read_only=True,
            )
        except Exception:
            pass
        finally:
            with _INDEX_FINGERPRINT_LOCK:
                _PREWARMING_DOMAIN_SPECS_KEYS.discard(dedup_key)

    threading.Thread(
        target=_run_prewarm,
        name="wsc_prewarm_domain_specs",
        daemon=True,
    ).start()


def _chunk_sequence(seq: Sequence[Any], n: int) -> Iterator[Sequence[Any]]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _load_source_state_sidecar(
    resolved_path: Path, mtime_ns: int, size: int
) -> Optional[dict[str, str]]:
    sidecar = resolved_path.parent / f".{resolved_path.name}.source_state.local.json"
    if not sidecar.is_file():
        return None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        if (
            isinstance(payload, dict)
            and payload.get("mtime_ns") == mtime_ns
            and payload.get("size") == size
            and isinstance(payload.get("fingerprints"), dict)
        ):
            return {str(k): str(v or "") for k, v in payload["fingerprints"].items()}
    except Exception:
        return None
    return None


def _save_source_state_sidecar(
    resolved_path: Path, mtime_ns: int, size: int, fingerprints: Mapping[str, str]
) -> None:
    sidecar = resolved_path.parent / f".{resolved_path.name}.source_state.local.json"
    try:
        payload = {
            "mtime_ns": mtime_ns,
            "size": size,
            "fingerprints": {str(k): str(v or "") for k, v in fingerprints.items()},
        }
        sidecar.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    except Exception:
        pass


def _get_covered_source_fingerprints(
    index_path: Path | str,
    candidate_doc_ids: Optional[Iterable[str]] = None,
    *,
    read_only: bool = False,
) -> dict[str, str]:
    """Retrieve mapping of document_id -> source_fingerprint for retrievable chunks.

    Optimized for DESKTOP-SPEED-FIX-G9-HOSTFP-HOME, DESKTOP-SPEED-PROFILE-QUERY-FIX-HOME & ARCH-11:
    1. Caches results in-memory keyed by (resolved_path, mtime_ns, size) and shares covered
       document state between read_only=False and read_only=True so repeat calls within the
       same turn or across turns do not re-query SQLite.
    2. Reads O(1) document metadata from the ``source_state`` table when present instead of
       scanning the ``chunks`` table.
    3. Falls back safely to covering-index / batched queries when ``source_state`` is absent,
       preserving 100% semantic equivalence with the legacy query.
    """
    resolved_path = Path(index_path).resolve()
    if not resolved_path.is_file():
        return {}
    try:
        stat = resolved_path.stat()
    except OSError:
        return {}
    cache_key = (str(resolved_path), stat.st_mtime_ns, stat.st_size)

    candidate_list = (
        tuple(dict.fromkeys(str(d) for d in candidate_doc_ids if d))
        if candidate_doc_ids is not None
        else None
    )

    if read_only:
        if candidate_list is not None and not candidate_list:
            return {}
        with _INDEX_FINGERPRINT_LOCK:
            if cache_key not in _INDEX_COVERED_DOC_STATUS_CACHE:
                stale_ro_keys = [
                    k
                    for k in (
                        set(_INDEX_COVERED_DOC_IDS_CACHE)
                        | set(_INDEX_COVERED_DOC_STATUS_CACHE)
                        | set(_INDEX_COVERED_FULL_SCANNED)
                    )
                    if k[0] == cache_key[0] and k != cache_key
                ]
                for k in stale_ro_keys:
                    _INDEX_COVERED_DOC_IDS_CACHE.pop(k, None)
                    _INDEX_COVERED_DOC_STATUS_CACHE.pop(k, None)
                    _INDEX_COVERED_FULL_SCANNED.discard(k)
                _INDEX_COVERED_DOC_STATUS_CACHE[cache_key] = {}

            # Share state if read_only=False already populated _INDEX_FINGERPRINT_CACHE
            if cache_key in _INDEX_FINGERPRINT_FULL_SCANNED and cache_key not in _INDEX_COVERED_FULL_SCANNED:
                fp_map = _INDEX_FINGERPRINT_CACHE.get(cache_key, {})
                cov_from_fp = {doc_id for doc_id, fp_val in fp_map.items() if fp_val is not None}
                _INDEX_COVERED_DOC_IDS_CACHE[cache_key] = cov_from_fp
                ro_status = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                for doc_id, fp_val in fp_map.items():
                    ro_status[doc_id] = fp_val is not None
                _INDEX_COVERED_FULL_SCANNED.add(cache_key)
            elif cache_key in _INDEX_FINGERPRINT_CACHE:
                fp_map = _INDEX_FINGERPRINT_CACHE[cache_key]
                ro_status = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                cov_set = _INDEX_COVERED_DOC_IDS_CACHE.setdefault(cache_key, set())
                for doc_id, fp_val in fp_map.items():
                    if doc_id not in ro_status:
                        ro_status[doc_id] = fp_val is not None
                        if fp_val is not None:
                            cov_set.add(doc_id)

            status_map = _INDEX_COVERED_DOC_STATUS_CACHE[cache_key]
            is_ro_full = cache_key in _INDEX_COVERED_FULL_SCANNED

            if candidate_list is None:
                if is_ro_full:
                    covered_set = _INDEX_COVERED_DOC_IDS_CACHE.get(cache_key, set())
                    return {d: "" for d in covered_set}
                ro_missing_ids: Optional[list[str]] = None
            else:
                if is_ro_full:
                    covered_set = _INDEX_COVERED_DOC_IDS_CACHE.get(cache_key, set())
                    return {d: "" for d in candidate_list if d in covered_set}
                ro_missing_ids = [d for d in candidate_list if d not in status_map]
                if not ro_missing_ids:
                    return {d: "" for d in candidate_list if status_map.get(d, False)}

        uri = resolved_path.as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            has_source_state = bool(
                conn.execute("PRAGMA table_info(source_state)").fetchone()
            )
            if ro_missing_ids is None:
                if has_source_state:
                    rows = conn.execute(
                        "SELECT document_id FROM source_state WHERE chunk_count > 0"
                    ).fetchall()
                else:
                    index_names = {
                        str(r[1])
                        for r in conn.execute("PRAGMA index_list(chunks)").fetchall()
                        if len(r) > 1
                    }
                    if "idx_chunks_retrievable" in index_names:
                        rows = conn.execute(
                            """
                            WITH RECURSIVE docs(doc_id) AS (
                                SELECT MIN(document_id) FROM chunks WHERE retrievable = 1
                                UNION ALL
                                SELECT (
                                    SELECT MIN(document_id)
                                    FROM chunks
                                    WHERE retrievable = 1 AND document_id > docs.doc_id
                                )
                                FROM docs
                                WHERE docs.doc_id IS NOT NULL
                            )
                            SELECT doc_id FROM docs WHERE doc_id IS NOT NULL
                            """
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            "SELECT DISTINCT document_id FROM chunks WHERE retrievable = 1"
                        ).fetchall()
                covered_set = {str(r[0]) for r in rows if r and r[0] is not None}
                with _INDEX_FINGERPRINT_LOCK:
                    _INDEX_COVERED_DOC_IDS_CACHE[cache_key] = covered_set
                    status_map = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                    for d in covered_set:
                        status_map[d] = True
                    _INDEX_COVERED_FULL_SCANNED.add(cache_key)
                    return {d: "" for d in covered_set}
            else:
                found_docs: set[str] = set()
                for chunk in _chunk_sequence(ro_missing_ids, 500):
                    placeholders = ",".join("?" for _ in chunk)
                    if has_source_state:
                        rows = conn.execute(
                            f"""
                            SELECT document_id
                            FROM source_state
                            WHERE chunk_count > 0 AND document_id IN ({placeholders})
                            """,
                            chunk,
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            f"""
                            SELECT DISTINCT document_id
                            FROM chunks
                            WHERE retrievable = 1 AND document_id IN ({placeholders})
                            """,
                            chunk,
                        ).fetchall()
                    for row in rows:
                        if row and row[0] is not None:
                            found_docs.add(str(row[0]))
                with _INDEX_FINGERPRINT_LOCK:
                    covered_set = _INDEX_COVERED_DOC_IDS_CACHE.setdefault(cache_key, set())
                    covered_set.update(found_docs)
                    status_map = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                    for d in ro_missing_ids:
                        status_map[d] = d in found_docs
                    return {d: "" for d in candidate_list if status_map.get(d, False)}

    with _INDEX_FINGERPRINT_LOCK:
        if cache_key not in _INDEX_FINGERPRINT_CACHE:
            stale_keys = [k for k in _INDEX_FINGERPRINT_CACHE if k[0] == cache_key[0]]
            for k in stale_keys:
                _INDEX_FINGERPRINT_CACHE.pop(k, None)
                _INDEX_FINGERPRINT_FULL_SCANNED.discard(k)
            _INDEX_FINGERPRINT_CACHE[cache_key] = {}

        cached_map = _INDEX_FINGERPRINT_CACHE[cache_key]
        is_full = cache_key in _INDEX_FINGERPRINT_FULL_SCANNED

        if candidate_list is None:
            if is_full:
                return {k: v for k, v in cached_map.items() if v is not None}
            missing_ids = None
        else:
            if is_full:
                return {d: cached_map[d] for d in candidate_list if cached_map.get(d) is not None}
            missing_ids = [d for d in candidate_list if d not in cached_map]
            if not missing_ids:
                return {d: cached_map[d] for d in candidate_list if cached_map.get(d) is not None}

    uri = resolved_path.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        has_source_state = bool(
            conn.execute("PRAGMA table_info(source_state)").fetchone()
        )
        if has_source_state:
            if missing_ids is None:
                rows = conn.execute(
                    """
                    SELECT document_id,
                           COALESCE(min_fingerprint, source_fingerprint, '') AS min_fp,
                           COALESCE(max_fingerprint, source_fingerprint, '') AS max_fp
                    FROM source_state
                    WHERE chunk_count > 0
                    """
                ).fetchall()
                with _INDEX_FINGERPRINT_LOCK:
                    cached_map = _INDEX_FINGERPRINT_CACHE.setdefault(cache_key, {})
                    covered_set = _INDEX_COVERED_DOC_IDS_CACHE.setdefault(cache_key, set())
                    ro_status = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                    for row in rows:
                        doc_id = str(row[0])
                        fp_str = str(row[1] or "")
                        cached_map[doc_id] = fp_str
                        covered_set.add(doc_id)
                        ro_status[doc_id] = True
                    _INDEX_FINGERPRINT_FULL_SCANNED.add(cache_key)
                    _INDEX_COVERED_FULL_SCANNED.add(cache_key)
                    return {k: v for k, v in cached_map.items() if v is not None}
            else:
                fetched: dict[str, str] = {}
                for chunk in _chunk_sequence(missing_ids, 500):
                    placeholders = ",".join("?" for _ in chunk)
                    rows = conn.execute(
                        f"""
                        SELECT document_id,
                               COALESCE(min_fingerprint, source_fingerprint, '') AS min_fp,
                               COALESCE(max_fingerprint, source_fingerprint, '') AS max_fp
                        FROM source_state
                        WHERE chunk_count > 0 AND document_id IN ({placeholders})
                        """,
                        chunk,
                    ).fetchall()
                    for row in rows:
                        fetched[str(row[0])] = str(row[1] or "")
                with _INDEX_FINGERPRINT_LOCK:
                    cached_map = _INDEX_FINGERPRINT_CACHE.setdefault(cache_key, {})
                    covered_set = _INDEX_COVERED_DOC_IDS_CACHE.setdefault(cache_key, set())
                    ro_status = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                    for d in missing_ids:
                        val = fetched.get(d)
                        cached_map[d] = val
                        ro_status[d] = val is not None
                        if val is not None:
                            covered_set.add(d)
                    return {d: cached_map[d] for d in candidate_list if cached_map.get(d) is not None}

        # Fallback when source_state table is not present in SQLite
        index_names = {
            str(r[1])
            for r in conn.execute("PRAGMA index_list(chunks)").fetchall()
            if len(r) > 1
        }
        has_fp_cov_idx = "idx_chunks_retrievable_doc_fp" in index_names
        if not has_fp_cov_idx and stat.st_size >= 32 * 1024 * 1024:
            sidecar_fps = _load_source_state_sidecar(
                resolved_path, stat.st_mtime_ns, stat.st_size
            )
            if sidecar_fps is None:
                if "idx_chunks_retrievable" in index_names:
                    doc_rows = conn.execute(
                        """
                        WITH RECURSIVE docs(doc_id) AS (
                            SELECT MIN(document_id) FROM chunks WHERE retrievable = 1
                            UNION ALL
                            SELECT (
                                SELECT MIN(document_id)
                                FROM chunks
                                WHERE retrievable = 1 AND document_id > docs.doc_id
                            )
                            FROM docs
                            WHERE docs.doc_id IS NOT NULL
                        )
                        SELECT doc_id FROM docs WHERE doc_id IS NOT NULL
                        """
                    ).fetchall()
                else:
                    doc_rows = conn.execute(
                        "SELECT DISTINCT document_id FROM chunks WHERE retrievable = 1"
                    ).fetchall()
                all_cov_docs = [str(r[0]) for r in doc_rows if r and r[0] is not None]
                sidecar_fps = {}
                for chunk in _chunk_sequence(all_cov_docs, 500):
                    values_sql = ",".join("(?)" for _ in chunk)
                    fp_rows = conn.execute(
                        f"""
                        WITH req(doc_id) AS (VALUES {values_sql})
                        SELECT req.doc_id AS document_id,
                               (SELECT c.source_fingerprint
                                FROM chunks AS c
                                WHERE c.retrievable = 1
                                  AND c.document_id = req.doc_id
                                  AND c.source_fingerprint IS NOT NULL
                                LIMIT 1) AS min_fp
                        FROM req
                        """,
                        chunk,
                    ).fetchall()
                    for r in fp_rows:
                        sidecar_fps[str(r[0])] = str(r[1] or "")
                _save_source_state_sidecar(
                    resolved_path, stat.st_mtime_ns, stat.st_size, sidecar_fps
                )
            with _INDEX_FINGERPRINT_LOCK:
                cached_map = _INDEX_FINGERPRINT_CACHE.setdefault(cache_key, {})
                covered_set = _INDEX_COVERED_DOC_IDS_CACHE.setdefault(cache_key, set())
                ro_status = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                for doc_id, fp_str in sidecar_fps.items():
                    cached_map[doc_id] = fp_str
                    covered_set.add(doc_id)
                    ro_status[doc_id] = True
                _INDEX_FINGERPRINT_FULL_SCANNED.add(cache_key)
                _INDEX_COVERED_FULL_SCANNED.add(cache_key)
                if candidate_list is None:
                    return {k: v for k, v in cached_map.items() if v is not None}
                for d in candidate_list:
                    if d not in cached_map:
                        cached_map[d] = None
                        ro_status[d] = False
                return {d: cached_map[d] for d in candidate_list if cached_map.get(d) is not None}

        if missing_ids is None:
            rows = conn.execute(
                """
                SELECT document_id,
                       MIN(source_fingerprint) AS min_fp,
                       MAX(source_fingerprint) AS max_fp
                FROM chunks
                WHERE retrievable = 1
                GROUP BY document_id
                """
            ).fetchall()
            with _INDEX_FINGERPRINT_LOCK:
                cached_map = _INDEX_FINGERPRINT_CACHE.setdefault(cache_key, {})
                covered_set = _INDEX_COVERED_DOC_IDS_CACHE.setdefault(cache_key, set())
                ro_status = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                for row in rows:
                    doc_id = str(row[0])
                    fp_str = str(row[1] or "")
                    cached_map[doc_id] = fp_str
                    covered_set.add(doc_id)
                    ro_status[doc_id] = True
                _INDEX_FINGERPRINT_FULL_SCANNED.add(cache_key)
                _INDEX_COVERED_FULL_SCANNED.add(cache_key)
                return {k: v for k, v in cached_map.items() if v is not None}
        else:
            fetched = {}
            for chunk in _chunk_sequence(missing_ids, 500):
                placeholders = ",".join("?" for _ in chunk)
                rows = conn.execute(
                    f"""
                    SELECT document_id,
                           MIN(source_fingerprint) AS min_fp,
                           MAX(source_fingerprint) AS max_fp
                    FROM chunks
                    WHERE retrievable = 1 AND document_id IN ({placeholders})
                    GROUP BY document_id
                    """,
                    chunk,
                ).fetchall()
                for row in rows:
                    fetched[str(row[0])] = str(row[1] or "")
            with _INDEX_FINGERPRINT_LOCK:
                cached_map = _INDEX_FINGERPRINT_CACHE.setdefault(cache_key, {})
                covered_set = _INDEX_COVERED_DOC_IDS_CACHE.setdefault(cache_key, set())
                ro_status = _INDEX_COVERED_DOC_STATUS_CACHE.setdefault(cache_key, {})
                for d in missing_ids:
                    val = fetched.get(d)
                    cached_map[d] = val
                    ro_status[d] = val is not None
                    if val is not None:
                        covered_set.add(d)
                return {d: cached_map[d] for d in candidate_list if cached_map.get(d) is not None}


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
    domain_collection_id: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    from aios_habit.rag_v2.pipeline import SourceSpec
    if any(not isinstance(s, SourceSpec) for s in sources):
        if is_production_index_available(config=config):
            temp_sources = tuple(
                s for s in sources
                if not isinstance(s, SourceSpec) and _safe_source_scope(s) == SOURCE_SCOPE_TEMPORARY
            )
            temp_statuses = (
                get_workspace_chat_source_preparation_status(temp_sources, config=config)
                if temp_sources
                else {}
            )
            ready_subset = tuple(
                s for s in sources
                if isinstance(s, SourceSpec)
                or _safe_source_scope(s) != SOURCE_SCOPE_TEMPORARY
                or temp_statuses.get(f"{_safe_source_scope(s)}:{_safe_source_id(s)}") == _PREPARATION_READY_STATE
            )
        else:
            statuses = get_workspace_chat_source_preparation_status(tuple(sources), config=config)
            ready_subset = tuple(
                s for s in sources
                if isinstance(s, SourceSpec)
                or statuses.get(f"{_safe_source_scope(s)}:{_safe_source_id(s)}") == _PREPARATION_READY_STATE
            )
        if ready_subset:
            sources = ready_subset

    pipe_config = _pipeline_config(
        config,
        profile,
        # Sources have passed the preparation/coverage gate already.  A query
        # must never open the shared index in write mode: doing so lets a
        # fresh worker silently embed every unrelated legacy chunk.
        read_only=True,
        include_reranker=rerank_requested,
        # Domain routing (feature-flagged) overrides the collection with the
        # question's knowledge-domain collection; otherwise the legacy
        # source-based collection resolution applies.
        collection_id=domain_collection_id or _collection_id_for_sources(sources),
    )
    rag_specs = []
    rag_originals = {}
    regular_sources = []
    for s in sources:
        if isinstance(s, SourceSpec):
            rag_specs.append(s)
            rag_originals[s.document_id] = WorkspaceAIContextSource(
                source_id=s.source_id,
                source_scope=SOURCE_SCOPE_NOTEBOOK,
                source_type="plain_text",
                title=Path(s.path).name,
                privacy_label="local_only",
                text="",
                included_chars=0,
                managed_path=str(s.path),
                truncated=False,
            )
        else:
            regular_sources.append(s)
    if regular_sources:
        mat_specs, mat_orig = _materialize_sources(regular_sources, config.runtime_root)
        rag_specs.extend(mat_specs)
        rag_originals.update(mat_orig)

    specs = tuple(rag_specs)
    originals = rag_originals
    if not specs:
        raise ValueError("no_non_empty_sources")

    if not pipe_config.index_read_only:
        sem_state, sem_reason = _semantic_readiness(sources, config)
        if sem_state != _PREPARATION_READY_STATE:
            raise RuntimeError(sem_reason or "sources_not_ready")

    # A durable index can survive an application restart while the isolated
    # BGE worker cannot.  Re-open that worker once before querying; this only
    # loads pinned local models and never re-materializes or embeds a source.
    # The normal preparation path has already done this, so the client reports
    # a cheap reused initialization in the common case.
    if pipeline_factory is RagV2DevPipeline:
        if _SUBPROCESS_CLIENT._persistent_applies(pipe_config):
            if not _SUBPROCESS_CLIENT.is_ready(pipe_config):
                LOGGER.info(
                    "BGE worker not ready for persistent collection '%s'; deferring to warm loop",
                    getattr(pipe_config, "collection_id", None) or Path(pipe_config.runtime_root).name,
                )
                try:
                    ensure_workspace_chat_worker_warming(
                        config=config,
                        blocking=False,
                        pipe_config=pipe_config,
                        collection_id=domain_collection_id,
                    )
                except Exception:
                    pass
                raise RuntimeError("bge_worker_warming_in_progress")
        else:
            initialize_workspace_chat_rag_v2_worker(
                config,
                timeout_s=default_init_timeout_seconds(),
                pipe_config=pipe_config,
            )

    if pipe_config.index_path.is_file():
        try:
            from aios_habit.rag_v2.pipeline import _file_fingerprint

            candidate_doc_ids = [s.document_id for s in specs if getattr(s, "document_id", None)]
            covered = _get_covered_source_fingerprints(
                pipe_config.index_path,
                candidate_doc_ids=candidate_doc_ids,
                read_only=bool(pipe_config.index_read_only),
            )
            indexed_specs = []
            for spec in specs:
                stored = covered.get(spec.document_id)
                if stored is None:
                    continue
                if pipe_config.index_read_only:
                    indexed_specs.append(spec)
                elif Path(spec.path).is_file():
                    try:
                        actual = _file_fingerprint(Path(spec.path))
                        if not stored or actual == stored:
                            indexed_specs.append(spec)
                    except OSError:
                        pass
            if domain_collection_id:
                specs = tuple(indexed_specs) if indexed_specs else specs
            elif indexed_specs:
                specs = tuple(indexed_specs)
        except Exception:
            pass
    if not specs:
        raise ValueError("no_non_empty_sources")

    query_res_dict = _SUBPROCESS_CLIENT.query_ready(
        question,
        specs,
        pipe_config,
        expansion=expansion,
        rerank_requested=rerank_requested,
        routing_reason_codes=routing_reason_codes,
        policy_version=policy_version,
        timeout_s=(config.deep_timeout_ms / 1000.0 if rerank_requested else default_query_timeout_seconds()),
    )
    is_named_doc_query = False
    try:
        from aios_habit import index_domain
        matched_named, _ = index_domain.match_named_documents(question)
        if matched_named:
            is_named_doc_query = True
    except Exception:
        pass
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
        per_document_limit=getattr(config, "per_document_limit", None),
        question=question,
        is_named_document_query=is_named_doc_query or (len(specs) == 1),
    )
    LOGGER.info(
        "workspace_chat_rag_v2 %s",
        json.dumps(mapped["rag_v2_canary"], sort_keys=True),
    )
    summary_dict = query_res_dict.get("summary", {}) if isinstance(query_res_dict, dict) else {}
    pipe_wait_ms = float(
        summary_dict.get(
            "pipe_wait_ms",
            summary_dict.get(
                "pipe_connect_ms",
                (
                    query_res_dict.get("pipe_wait_ms", query_res_dict.get("pipe_connect_ms", 0.0))
                    if isinstance(query_res_dict, dict)
                    else 0.0
                ),
            ),
        )
        or 0.0
    )
    embed_ms = float(summary_dict.get("embed_latency_ms", 0.0) or 0.0)
    embed_wait_ms = float(summary_dict.get("embed_wait_ms", 0.0) or 0.0)
    embed_compute_ms = float(summary_dict.get("embed_compute_ms", embed_ms) or embed_ms)
    lexical_ms = float(summary_dict.get("lexical_latency_ms", 0.0) or 0.0)
    context_expand_ms = float(summary_dict.get("context_expansion_latency_ms", 0.0) or 0.0)
    dense_ms = float(summary_dict.get("dense_latency_ms", 0.0) or 0.0)
    sparse_ms = float(summary_dict.get("sparse_latency_ms", 0.0) or 0.0)
    fuse_ms = float(summary_dict.get("fusion_latency_ms", 0.0) or 0.0)
    dense_resident = bool(summary_dict.get("dense_resident", True))
    dense_load_ms = float(summary_dict.get("dense_load_latency_ms", 0.0) or 0.0)
    coverage_verify_ms = float(summary_dict.get("coverage_verify_ms", 0.0) or 0.0)
    target_collection = str(domain_collection_id or getattr(pipe_config, "collection_id", "") or "default")
    resident_str = "thuong_tru" if dense_resident else "nap_trong_lan_goi"
    timestamp = format_marker_timestamp()
    if isinstance(mapped.get("rag_v2_canary"), dict):
        mapped["rag_v2_canary"]["pipe_wait_ms"] = round(pipe_wait_ms, 2)
        mapped["rag_v2_canary"]["coverage_verify_ms"] = round(coverage_verify_ms, 2)
        mapped["rag_v2_canary"]["lexical_latency_ms"] = round(lexical_ms, 2)
        mapped["rag_v2_canary"]["context_expansion_latency_ms"] = round(context_expand_ms, 2)

    marker_msg = (
        f"[RETRIEVAL_MICRO_TIMING] collection={target_collection} "
        f"pipe_wait_ms={pipe_wait_ms:.2f} "
        f"coverage_verify_ms={coverage_verify_ms:.2f} "
        f"lexical_ms={lexical_ms:.2f} "
        f"embed_ms={embed_ms:.2f} embed_wait_ms={embed_wait_ms:.2f} embed_compute_ms={embed_compute_ms:.2f} "
        f"dense_ms={dense_ms:.2f} sparse_ms={sparse_ms:.2f} fuse_ms={fuse_ms:.2f} "
        f"context_expand_ms={context_expand_ms:.2f} "
        f"dense_resident={dense_resident} dense_state={resident_str} "
        f"dense_load_ms={dense_load_ms:.2f} timestamp={timestamp}"
    )
    _safe_print_streaming_marker(marker_msg)
    try:
        LOGGER.info(marker_msg)
    except Exception:
        pass
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
    sources: Tuple[WorkspaceAIContextSource, ...] | Sequence[WorkspaceAIContextSource],
    config: WorkspaceChatRagV2CanaryConfig,
) -> tuple[str, str]:
    """Return the aggregate BGE-M3 preparation state."""
    if not sources:
        return "unavailable", "no_sources"
    statuses = get_workspace_chat_source_preparation_status(tuple(sources), config=config)
    values = tuple(statuses.values())
    if values and any(state == _PREPARATION_READY_STATE for state in values):
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
    forced_domain: Optional[str] = None,
) -> dict[str, Any] | None:
    """Use bounded SQL analytics only for deterministic, allow-listed plans."""
    from aios_habit.rag_v2.structured_query import try_structured_table_evidence
    table_result = try_structured_table_evidence(
        question, sources, forced_domain=forced_domain
    )
    if table_result is not None:
        if not table_result.get("retrieved_context_sources") and sources and table_result.get("evidence_items"):
            ev = table_result["evidence_items"][0]
            for s in sources:
                name = getattr(s, "title", None) or Path(getattr(s, "path", "")).name
                if name.casefold() == ev.get("title", "").casefold():
                    ret_src = WorkspaceAIContextSource(
                        source_id=ev.get("source_id", s.source_id),
                        source_scope=ev.get("source_scope", s.source_scope),
                        source_type=ev.get("source_type", s.source_type),
                        title=f"{ev.get('title')} ({ev.get('location_info')})",
                        privacy_label=s.privacy_label,
                        text=ev.get("text", ""),
                        original_chars=len(ev.get("text", "")),
                        included_chars=len(ev.get("text", "")),
                        truncated=False,
                        managed_path=str(_managed_workbook_path(s) or getattr(s, "managed_path", "")),
                    )
                    table_result["retrieved_context_sources"] = (ret_src,)
                    break
        return table_result

    if not query_might_be_structured_excel(question):
        return None
    excel_sources = tuple(s for s in sources if _managed_workbook_path(s) is not None)
    if len(excel_sources) > 3:
        scope = select_workspace_chat_preparation_scope(question, excel_sources, limit=3)
        if not scope.bounded or not scope.sources:
            return None
        excel_sources = scope.sources
    for source in excel_sources:
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

        title = sanitize_citation_title(getattr(source, 'title', None) or Path(getattr(source, 'path', '')).name)
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


def _attach_line_log_evidence(
    question: str,
    result: dict[str, Any],
    collection_id: str | None,
) -> dict[str, Any]:
    """Merge a bounded suspected log slice into retrieval evidence."""
    from aios_habit.line_log_parser import match_line_events_for_question

    matched = match_line_events_for_question(question, collection_id)
    events = matched.get("events") or ()
    text = str(matched.get("owner_text") or "").strip()
    if not events or not text:
        result.setdefault("line_log_attached", False)
        return result
    payload = dict(result)
    items = list(payload.get("evidence_items") or [])
    citations = list(payload.get("citations") or [])
    sources = list(payload.get("retrieved_context_sources") or ())
    evidence_id = "line-log-suspected"
    title = "Log điều tra (nghi ngờ, chưa chẩn đoán)"
    items.append(
        {
            "snippet_index": len(items) + 1,
            "source_id": "line-events",
            "source_scope": "collection",
            "source_type": "line_log",
            "title": title,
            "text": text,
            "location_info": "line_events.sqlite",
            "score": 0.0,
            "retrieval_score": 0.0,
            "citation_id": evidence_id,
            "evidence_id": evidence_id,
        }
    )
    citations.append(
        {
            "title": title,
            "snippet": text[:150] + ("..." if len(text) > 150 else ""),
            "location": "kho log",
            "citation_id": evidence_id,
        }
    )
    sources.append(
        WorkspaceAIContextSource(
            source_id="line-events",
            source_scope="collection",
            source_type="line_log",
            title=title,
            privacy_label="local_only",
            text=text,
            included_chars=len(text),
            truncated=False,
        )
    )
    payload["evidence_items"] = items
    payload["citations"] = citations
    payload["retrieved_context_sources"] = tuple(sources)
    payload["summary_count"] = len(items)
    payload["line_log_attached"] = True
    payload["retrieval_applied"] = True
    message = str(payload.get("safe_owner_message") or "").strip()
    extra = "Đã kèm sự kiện log nghi ngờ, chưa phải chẩn đoán."
    payload["safe_owner_message"] = f"{message} {extra}".strip() if message else extra
    return payload


def _domain_index_ready(config: WorkspaceChatRagV2CanaryConfig, collection_id: str) -> bool:
    """Return whether the app can open this collection's library.sqlite.

    Domain split mounts live beside the legacy index at
    ``<profile>/collections/<id>/library.sqlite`` (including NTFS junctions).
    A non-empty ``storage_root`` still wins via ``collection_runtime_layout``.
    A registry row with an empty storage root is not enough: the file must exist.
    """
    from aios_habit.workspace_chat_store import collection_runtime_layout

    profile_root = Path(config.runtime_root) / str(config.requested_profile)
    runtime_root, index_name = collection_runtime_layout(collection_id, profile_root)
    try:
        return (Path(runtime_root) / index_name).is_file()
    except OSError:
        return False


def workspace_chat_domain_block_status() -> tuple[dict[str, Any], ...]:
    """Read-only readiness of the shared knowledge blocks (sidebar).

    Never raises: a missing deployment config or index only reports
    ``ready=False`` so the sidebar can state the block status honestly.
    """
    from aios_habit.index_domain import KNOWLEDGE_BLOCKS, DOMAIN_DISPLAY
    from aios_habit.workspace_chat_store import collection_runtime_layout

    profile_root: Optional[Path] = None
    try:
        config = WorkspaceChatRagV2CanaryConfig.from_env()
        profile_root = Path(config.runtime_root) / str(config.requested_profile)
    except Exception:
        profile_root = None

    blocks: list[dict[str, Any]] = []
    for domain in KNOWLEDGE_BLOCKS:
        ready = False
        size_bytes = 0
        if profile_root is not None:
            try:
                runtime_root, index_name = collection_runtime_layout(domain, profile_root)
                index_path = Path(runtime_root) / index_name
                ready = index_path.is_file()
                if ready:
                    size_bytes = int(index_path.stat().st_size)
            except Exception:
                ready, size_bytes = False, 0
        blocks.append(
            {
                "domain": domain,
                "display": DOMAIN_DISPLAY.get(domain, domain),
                "ready": ready,
                "size_bytes": size_bytes,
            }
        )
    return tuple(blocks)


def _select_domain_route(
    question: str,
    sources: Tuple["WorkspaceAIContextSource", ...],
    config: WorkspaceChatRagV2CanaryConfig,
    forced_domain: Optional[str] = None,
):
    """Pick a domain collection for the question (feature-flagged).

    ``forced_domain`` is the knowledge block the user explicitly picked in the
    composer. It wins over question detection and the routing flag (the user
    asked for that block) and is whitelisted to all knowledge blocks (including
    ``tong_hop``).

    Returns an ``index_domain.DomainRoute`` or ``None`` when routing is
    disabled. Never raises: a classification failure must not break
    retrieval, it only falls back to the legacy collection.
    """
    try:
        from aios_habit import index_domain

        base_collection_id = _collection_id_for_sources(sources)
        effective_base = base_collection_id or (
            DEFAULT_COLLECTION_ID if not sources else None
        )
        forced = str(forced_domain or "").strip().lower()
        if forced and forced != "auto":
            if forced not in index_domain.KNOWLEDGE_BLOCKS:
                return None
            detected = index_domain.Classification(
                forced,
                1.0,
                "người dùng chọn khối %s" % index_domain.DOMAIN_DISPLAY.get(forced, forced),
            )
            target = index_domain.DOMAIN_COLLECTION_IDS.get(forced)
            if target is None:
                return None
            if not _domain_index_ready(config, target):
                if _domain_index_ready(config, effective_base):
                    # Kho hợp nhất library.sqlite chứa toàn bộ các khối tri thức.
                    # Lọc phạm vi qua trường document_id trong library.sqlite thay vì tách rời file DB.
                    return index_domain.DomainRoute(
                        effective_base,
                        forced,
                        True,
                        "người dùng chọn khối %s (lọc qua chỉ mục)" % index_domain.DOMAIN_DISPLAY.get(forced, forced),
                        detected,
                    )
                return index_domain.DomainRoute(
                    effective_base,
                    forced,
                    False,
                    "khối được chọn chưa có kho trên máy này",
                    detected,
                )
            return index_domain.DomainRoute(
                target, forced, True, "người dùng chọn khối", detected
            )

        detected = index_domain.detect_domain_from_question(question, sources=sources)
        is_named_doc = bool(detected and getattr(detected, "confidence", 0.0) == 1.0)

        if not is_named_doc and forced != "auto" and not index_domain.domain_routing_enabled():
            return None
        if (
            detected is None
            or getattr(detected, "confidence", 0.0) < index_domain.CONFIDENCE_LOW_THRESHOLD
        ):
            return index_domain.DomainRoute(
                effective_base,
                detected.domain if detected is not None else index_domain.FALLBACK_DOMAIN,
                False,
                "câu hỏi không rõ lĩnh vực: giữ nguyên kho hiện tại",
                detected,
            )

        def _collection_exists(collection_id: str) -> bool:
            return _domain_index_ready(config, collection_id)

        if (forced == "auto" or is_named_doc) and not index_domain.domain_routing_enabled():
            if effective_base != index_domain.LEGACY_COLLECTION_ID:
                return index_domain.DomainRoute(
                    effective_base,
                    detected.domain,
                    False,
                    "không phải kho tri_thuc: giữ nguyên kho hiện tại",
                    detected,
                )
            target = index_domain.DOMAIN_COLLECTION_IDS.get(detected.domain)
            if target is not None and _collection_exists(target):
                return index_domain.DomainRoute(
                    target, detected.domain, True, "chọn kho lĩnh vực", detected
                )
            if _domain_index_ready(config, effective_base):
                return index_domain.DomainRoute(
                    effective_base,
                    detected.domain,
                    True,
                    "tu dong chon khoi %s (loc qua chi muc)" % index_domain.DOMAIN_DISPLAY.get(detected.domain, detected.domain),
                    detected,
                )
            return index_domain.DomainRoute(
                effective_base,
                detected.domain,
                False,
                "kho lĩnh vực chưa tồn tại: dùng kho tri_thuc cũ",
                detected,
            )

        route = index_domain.select_domain_collection(
            detected, effective_base, collection_exists=_collection_exists
        )
        if (
            route is not None
            and not route.applied
            and detected is not None
            and getattr(detected, "confidence", 0.0) >= index_domain.CONFIDENCE_LOW_THRESHOLD
            and _domain_index_ready(config, effective_base)
        ):
            # Kho hop nhat library.sqlite chua toan bo cac khoi tri thuc.
            # Loc pham vi qua truong document_id trong library.sqlite thay vi tach roi file DB.
            return index_domain.DomainRoute(
                effective_base,
                route.domain,
                True,
                "tu dong chon khoi %s (loc qua chi muc)" % index_domain.DOMAIN_DISPLAY.get(route.domain, route.domain),
                detected,
            )
        return route
    except Exception as error:  # routing must never break retrieval
        LOGGER.warning("Domain routing skipped: %s", _safe_reason(error))
        return None


def _domain_routing_payload(route) -> dict[str, Any] | None:
    """Render a DomainRoute into the retrieval payload for UI transparency."""
    if route is None:
        return None
    from aios_habit import index_domain

    detected = route.detected
    confidence = float(detected.confidence) if detected is not None else 0.0
    return {
        "enabled": True,
        "applied": bool(route.applied),
        "domain": route.domain,
        "domain_display": index_domain.DOMAIN_DISPLAY.get(route.domain, route.domain),
        "confidence": round(confidence, 3),
        "reason": detected.reason if detected is not None else "",
        "ambiguous": confidence < index_domain.CONFIDENCE_LOW_THRESHOLD,
        "collection_id": route.collection_id,
        "note": route.note,
    }


def retrieve_workspace_chat_evidence(
    question: str,
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline] = RagV2DevPipeline,
    expansion: Optional[Mapping[str, Any]] = None,
    search_preference: str = "auto",
    forced_domain: Optional[str] = None,
) -> dict[str, Any]:
    """Retrieve evidence only through the pinned local BGE-M3 hybrid pipeline."""
    sources = tuple(context_sources)
    collection_id = _collection_id_for_sources(sources)
    domain_route = None

    def _finish(payload: dict[str, Any]) -> dict[str, Any]:
        domain_payload = _domain_routing_payload(domain_route)
        if domain_payload is not None:
            payload = {**payload, "domain_routing": domain_payload}
        if payload.get("status") in {"structured_table_query", "structured_excel_query"}:
            return payload
        return _attach_line_log_evidence(question, payload, collection_id)

    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except (DeploymentManifestError, ValueError) as error:
        reason = _safe_reason(error)
        LOGGER.error("Workspace Chat BGE-M3 deployment unavailable: %s", reason)
        return _finish(_quality_search_unavailable(reason))

    if not resolved.enabled:
        return _finish(_quality_search_unavailable("feature_flag_disabled"))

    # Operate strictly on ready sources so pending documents in notebook do not block retrieval
    if is_production_index_available(config=resolved):
        temp_sources = tuple(s for s in sources if _safe_source_scope(s) == SOURCE_SCOPE_TEMPORARY)
        temp_statuses = (
            get_workspace_chat_source_preparation_status(temp_sources, config=resolved)
            if temp_sources
            else {}
        )
        ready_subset = tuple(
            s for s in sources
            if _safe_source_scope(s) != SOURCE_SCOPE_TEMPORARY
            or temp_statuses.get(f"{_safe_source_scope(s)}:{_safe_source_id(s)}") == _PREPARATION_READY_STATE
        )
    else:
        statuses = get_workspace_chat_source_preparation_status(sources, config=resolved)
        ready_subset = tuple(
            s for s in sources
            if statuses.get(f"{_safe_source_scope(s)}:{_safe_source_id(s)}") == _PREPARATION_READY_STATE
        )
    if ready_subset:
        sources = ready_subset
        collection_id = _collection_id_for_sources(sources)

    # When a named document does not match exactly: fall back to normal retrieval
    # (dense + BM25) with logging; do not block with Honest Refusal.
    try:
        from aios_habit import index_domain
        matched_specs, missing_names = index_domain.match_named_documents(question, sources=sources)
        if missing_names and not matched_specs:
            missing_doc = missing_names[0]
            LOGGER.warning(
                "[named_doc_fallback] Tài liệu '%s' nêu đích danh không khớp catalog, hạ xuống truy hồi thường (dense + BM25)",
                missing_doc,
            )
    except Exception as exc:
        LOGGER.warning("[named_doc_check_error] %s", exc)

    # Domain routing (feature-flagged): detect the question's knowledge domain
    # and search that domain's collection instead of the legacy mixed one.
    # A block explicitly chosen in the composer (forced_domain) overrides
    # detection; if that block has no index, fail with an honest reason instead
    # of silently searching the mixed legacy library.
    domain_route = _select_domain_route(question, sources, resolved, forced_domain)
    if (
        str(forced_domain or "").strip()
        and str(forced_domain or "").strip().lower() != "auto"
        and domain_route is not None
        and not domain_route.applied
    ):
        return _finish(_quality_search_unavailable("domain_block_missing"))
    domain_collection_id = (
        domain_route.collection_id
        if domain_route is not None and domain_route.applied
        else None
    )

    # Domain routing already picked one block. Search every ready source that
    # lives in that block; the narrow lexical window would hide them.
    from aios_habit import index_domain
    prod_pipe_cfg = None
    is_prod_index = False
    try:
        prod_pipe_cfg = _pipeline_config(resolved, "bge_m3_hybrid", read_only=True, collection_id=DEFAULT_COLLECTION_ID)
        is_prod_index = prod_pipe_cfg.index_path.is_file()
    except Exception:
        pass
    has_notebook_sources = any(getattr(s, "source_scope", "") == SOURCE_SCOPE_NOTEBOOK for s in sources)
    has_forced_domain = bool(forced_domain and str(forced_domain).strip().lower() != "auto")
    use_prod_domain_specs = bool(is_prod_index and prod_pipe_cfg)
    target_domain = (
        forced_domain
        if has_forced_domain
        else (domain_route.domain if domain_route and getattr(domain_route, "applied", False) else None)
    )
    effective_domain_collection_id = (
        domain_collection_id or (DEFAULT_COLLECTION_ID if use_prod_domain_specs else None)
    )
    active_retrieval_col = domain_collection_id or target_domain or "tri_thuc"
    if active_retrieval_col:
        update_user_retrieval_collection(active_retrieval_col)

    target_pipe_cfg = None
    try:
        target_pipe_cfg = _pipeline_config(
            resolved,
            "bge_m3_hybrid",
            read_only=True,
            collection_id=domain_collection_id or DEFAULT_COLLECTION_ID,
        )
    except Exception:
        target_pipe_cfg = prod_pipe_cfg

    spec_index_path = (
        target_pipe_cfg.index_path
        if (
            target_pipe_cfg is not None
            and getattr(target_pipe_cfg, "index_path", None)
            and target_pipe_cfg.index_path.is_file()
        )
        else (prod_pipe_cfg.index_path if prod_pipe_cfg is not None else None)
    )

    if (
        use_prod_domain_specs
        and pipeline_factory is RagV2DevPipeline
        and target_pipe_cfg is not None
        and not query_might_be_structured_excel(question)
        and str(search_preference or "auto").casefold() != "deep"
        and _SUBPROCESS_CLIENT._persistent_applies(target_pipe_cfg)
        and not _SUBPROCESS_CLIENT.is_ready(target_pipe_cfg)
    ):
        with user_retrieval_priority_scope(active_retrieval_col):
            try:
                ensure_workspace_chat_worker_warming(
                    config=resolved,
                    blocking=False,
                    pipe_config=target_pipe_cfg,
                    collection_id=active_retrieval_col,
                )
            except Exception:
                pass
        if spec_index_path is not None:
            try:
                flight_key = pipe_name_for_config(target_pipe_cfg)
                with _SUBPROCESS_CLIENT._persistent_init_lock:
                    target_pending = flight_key in _SUBPROCESS_CLIENT._pending_persistent_inits
                if target_pending or bool(_SUBPROCESS_CLIENT.readiness(target_pipe_cfg).get("alive")):
                    _prewarm_domain_specs_async(target_domain, spec_index_path, question=question)
            except Exception:
                pass
        return _finish(_quality_search_unavailable("bge_worker_warming_in_progress"))

    if use_prod_domain_specs and prod_pipe_cfg and spec_index_path is not None:
        domain_specs = _get_cached_specs_for_domain(
            target_domain, spec_index_path, question=question
        )
        temp_sources = tuple(s for s in sources if getattr(s, "source_scope", "") == SOURCE_SCOPE_TEMPORARY)
        semantic_sources = tuple(domain_specs) + temp_sources
    else:
        semantic_sources = (
            sources
            if domain_collection_id
            else _retrieval_source_window(question, sources)
        )

    # Scope every retrieval lane before it does any potentially expensive work.
    # In particular, an operational Manual question must not inspect (or ask a
    # planner about) every enabled workbook before it reaches the selected PDF.
    structured_result = _try_structured_excel_evidence(
        question,
        semantic_sources,
        forced_domain=target_domain,
    )
    if structured_result is not None:
        target_coll = str(target_domain or domain_collection_id or "structured")
        timestamp = format_marker_timestamp()
        marker_msg = (
            f"[RETRIEVAL_MICRO_TIMING] collection={target_coll} "
            f"pipe_wait_ms=0.00 "
            f"coverage_verify_ms=0.00 "
            f"embed_ms=0.00 embed_wait_ms=0.00 embed_compute_ms=0.00 "
            f"dense_ms=0.00 sparse_ms=0.00 fuse_ms=0.00 "
            f"dense_resident=True dense_state=thuong_tru dense_load_ms=0.00 timestamp={timestamp}"
        )
        _safe_print_streaming_marker(marker_msg)
        try:
            LOGGER.info(marker_msg)
        except Exception:
            pass
        return _finish(structured_result)

    pref_str = str(search_preference or "auto").casefold()

    if pref_str == "deep" and not resolved.adaptive_enabled:
        return _finish(_quality_search_unavailable("deep_search_unavailable"))

    # APP-SOURCE-MODEL: Chỉ chuẩn bị tài liệu tạm (temporary), không lên lịch chuẩn bị lại cho tài liệu production
    temp_prep_targets = tuple(s for s in semantic_sources if getattr(s, "source_scope", "") == SOURCE_SCOPE_TEMPORARY)
    if temp_prep_targets:
        schedule_workspace_chat_source_preparation(temp_prep_targets, config=resolved)

    if not use_prod_domain_specs:
        schedule_workspace_chat_source_preparation(semantic_sources, config=resolved)
        semantic_status, semantic_reason = _semantic_readiness(semantic_sources, resolved)
        if semantic_status != _PREPARATION_READY_STATE:
            return _finish(_quality_search_unavailable(semantic_reason or semantic_status))

    if expansion is None:
        expansion = _maybe_expand_latin_query_for_cjk_corpus(question, semantic_sources)

    plan = (
        build_query_plan(question, expansion)
        if expansion is not None
        else coerce_query_plan(question)
    )
    policy = AdaptiveRetrievalPolicy(
        version=resolved.policy_version,
        enabled=resolved.adaptive_enabled,
        deep_timeout_ms=resolved.deep_timeout_ms,
        reranker_configured=(resolved.bge_reranker_model_path is not None),
    )

    rerank_requested = False
    routing_reason_codes: Sequence[str] = ()
    pre_dec = None
    init_routing = None

    if resolved.adaptive_enabled or pref_str == "deep":
        pre_dec = pre_retrieval_gate(plan, user_preference=pref_str, policy=policy)
        init_routing = decide_initial_route(pre_dec, user_preference=pref_str, policy=policy)
        rerank_requested = init_routing.reranker_requested
        routing_reason_codes = init_routing.reason_codes

    try:
        with user_retrieval_priority_scope(active_retrieval_col):
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
                domain_collection_id=effective_domain_collection_id,
            )

        if init_routing is not None and init_routing.degraded:
            canary = initial_result.setdefault("rag_v2_canary", {})
            canary["degraded"] = True
            canary["degraded_reason"] = _sanitize_degraded_reason(init_routing.degraded_reason)
            canary["effective_path"] = str(getattr(init_routing.effective_path, "value", init_routing.effective_path))
            canary["fallback_applied"] = True
            canary["fallback_reason"] = canary["degraded_reason"]

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
                    domain_collection_id=effective_domain_collection_id,
                )
                return _finish(escalated_result)

        return _finish(initial_result)
    except Exception as error:
        reason = _safe_reason(error)
        LOGGER.warning("Workspace Chat BGE-M3 retrieval unavailable: %s", reason, exc_info=True)
        # BGE-WORKER-FIX-HOME: Tự phục hồi: khi gặp lỗi timeout hoặc worker không sẵn sàng,
        # xóa cờ lỗi client để lượt hỏi tiếp theo có thể thử kích hoạt lại worker thay vì fail-fast 0.01s.
        if "timeout" in reason or "unavailable" in reason or "bge_worker" in reason:
            _SUBPROCESS_CLIENT.clear_failure_reason()
        return _finish(_quality_search_unavailable(reason))


def close_workspace_chat_rag_v2_runtimes(*, timeout_s: float | None = 10.0) -> None:
    """Close and evict cached in-process and background preparation runtimes."""
    global _PREPARATION_EXECUTOR, _DRAIN_IS_RUNNING, _BACKGROUND_WARM_EXECUTOR, _USER_TARGET_WARM_EXECUTOR
    with _WARMUP_LOCK:
        _WARMUP_IN_QUEUE.clear()
        _WARMUP_RUNNING_KEYS.clear()
    with _BACKGROUND_WARM_LOCK:
        for col_exec in list(_COLLECTION_WARM_EXECUTORS.values()):
            try:
                col_exec.shutdown(wait=False)
            except Exception:
                pass
        _COLLECTION_WARM_EXECUTORS.clear()
        if _USER_TARGET_WARM_EXECUTOR is not None:
            try:
                _USER_TARGET_WARM_EXECUTOR.shutdown(wait=False)
            except Exception:
                pass
            _USER_TARGET_WARM_EXECUTOR = None
        if _BACKGROUND_WARM_EXECUTOR is not None:
            try:
                _BACKGROUND_WARM_EXECUTOR.shutdown(wait=False)
            except Exception:
                pass
            _BACKGROUND_WARM_EXECUTOR = None

    with _PREPARATION_LOCK:
        prep_executor = _PREPARATION_EXECUTOR
        _PREPARATION_EXECUTOR = None
    if prep_executor is not None:
        try:
            prep_executor.shutdown(wait=True)
        except Exception:
            pass
    with _PREPARATION_LOCK:
        _PREPARATION_REGISTRY.clear()
    with _COVERAGE_CACHE_LOCK:
        _COVERAGE_CACHE.clear()

    with _DRAIN_RUNNING_LOCK:
        _DRAIN_IS_RUNNING = False

    with _SOURCE_CACHE_LOCK:
        _SOURCE_CACHE.clear()

    try:
        _SUBPROCESS_CLIENT.close()
    except Exception:
        pass

    with _RUNTIME_CACHE_LOCK:
        entries = tuple(_RUNTIME_CACHE.values())
        _RUNTIME_CACHE.clear()
    for entry in entries:
        try:
            with entry.lock:
                entry.pipeline.close()
        except Exception:
            pass
    _document_id.cache_clear()
    _source_fingerprint.cache_clear()

