"""Feature-flagged Workspace Chat retrieval adapter for the local RAG v2 canary.

The adapter changes retrieval only. Answer generation still flows through
``generate_workspace_ai_answer`` and the Brain Gateway, which remain the owners
of consent, privacy authorization, outbound sanitization, and provider access.
"""
from __future__ import annotations

from collections import Counter
import concurrent.futures
from dataclasses import dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable, Iterable, Mapping, Optional, Tuple

from aios_habit.rag_v2.bge_subprocess_client import BgeSubprocessWorkerClient
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.semantic import (
    SemanticBackendError,
    SemanticBackendUnavailable,
)
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_rag_v2_deployment import (
    DeploymentManifestError,
    load_workspace_chat_rag_v2_deployment,
)

LOGGER = logging.getLogger(__name__)

_SUBPROCESS_CLIENT = BgeSubprocessWorkerClient()

_PREPARATION_REGISTRY: dict[str, dict[str, Any]] = {}
_PREPARATION_LOCK = threading.RLock()
_PREPARATION_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None

_PREPARATION_ACTIVE_STATES = frozenset({"pending", "processing"})
_PREPARATION_READY_STATE = "ready"


def _get_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _PREPARATION_EXECUTOR
    with _PREPARATION_LOCK:
        if _PREPARATION_EXECUTOR is None:
            _PREPARATION_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="wsc_bg_prepare"
            )
        return _PREPARATION_EXECUTOR

CANARY_ENABLED_ENV = "AIOS_WORKSPACE_RAG_V2_CANARY_ENABLED"
PROFILE_ENV = "AIOS_WORKSPACE_RAG_V2_PROFILE"
RUNTIME_ROOT_ENV = "AIOS_WORKSPACE_RAG_V2_RUNTIME_ROOT"
BGE_MODEL_PATH_ENV = "AIOS_BGE_M3_MODEL_PATH"
BGE_MODEL_REVISION_ENV = "AIOS_BGE_M3_MODEL_REVISION"
BGE_MODEL_CHECKSUM_ENV = "AIOS_BGE_M3_MODEL_CHECKSUM"
RETRIEVAL_DEVICE_ENV = "AIOS_RETRIEVAL_DEVICE"

_DEFAULT_RUNTIME_ROOT = Path("local_runs/workspace_chat_rag_v2_canary")
_ALLOWED_PROFILES = frozenset({"bge_m3_hybrid"})
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_SAFE_REASON = re.compile(r"[^a-z0-9_.-]+")
# Corpus sources vary substantially in extraction cost; keep every IPC request
# bounded to one document under the existing 90-second fail-closed deadline.
_PREPARATION_BATCH_SIZE = 1


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

    @classmethod
    def from_env(
        cls,
        env: Optional[Mapping[str, str]] = None,
    ) -> "WorkspaceChatRagV2CanaryConfig":
        values = os.environ if env is None else env
        deployment = load_workspace_chat_rag_v2_deployment(
            env=values,
            require_activated=True,
        )
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
            )

        model_path = str(values.get(BGE_MODEL_PATH_ENV, "") or "").strip()
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
        )


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
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pipeline_config(
    config: WorkspaceChatRagV2CanaryConfig,
    profile: str,
    *,
    read_only: bool = False,
) -> RagV2DevConfig:
    profile_root = config.runtime_root / profile
    common = {
        "runtime_root": profile_root,
        "index_filename": "workspace_chat.sqlite",
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
        retrieval_profile="bge_m3_hybrid",
        strict_semantic=True,
        bge_m3_model_path=config.bge_m3_model_path,
        bge_m3_model_revision=config.bge_m3_model_revision,
        bge_m3_model_checksum=config.bge_m3_model_checksum,
        bge_m3_batch_size=config.bge_m3_batch_size,
        bge_m3_max_length=config.bge_m3_max_length,
        bge_m3_use_fp16=config.bge_m3_use_fp16,
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


def _document_id(source: WorkspaceAIContextSource) -> str:
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


def _source_fingerprint(source: WorkspaceAIContextSource) -> str:
    doc_id = _document_id(source)
    text_bytes = (source.text or "").strip().encode("utf-8")
    content_hash = hashlib.sha256(text_bytes).hexdigest()[:16]
    privacy = (source.privacy_label or "").strip().casefold()
    return f"{doc_id}:{content_hash}:{privacy}"


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
        return _safe_init_report(
            _SUBPROCESS_CLIENT.initialize_worker(
                _pipeline_config(config, profile),
                **({"timeout_s": float(timeout_s)} if timeout_s is not None else {}),
            )
        )
    except Exception as exc:
        raise RuntimeError(f"preparation_init_{_safe_reason(exc)}") from exc


def prepare_workspace_chat_sources(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline] = RagV2DevPipeline,
) -> dict[str, Any]:
    """Prepare sources outside the user-initiated query path."""
    resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    sources = tuple(s for s in context_sources if (s.text or "").strip())
    if not sources:
        return {"status": "ok", "prepared_count": 0, "latency_ms": 0.0}

    profile = resolved.requested_profile
    pipe_config = _pipeline_config(resolved, profile)
    started = time.perf_counter()
    with _PREPARATION_LOCK:
        for source in sources:
            _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                _preparation_entry(resolved, source, "processing")
            )

    try:
        init_report: dict[str, Any] | None = None
        # Establish the production semantic worker while the parent only holds
        # caller-provided references; extraction/materialization can be slow and
        # memory-intensive. Injected pipeline factories own their lifecycle.
        if profile.startswith("bge_m3_") and pipeline_factory is RagV2DevPipeline:
            init_report = initialize_workspace_chat_rag_v2_worker(resolved)
        specs, _ = _materialize_sources(sources, resolved.runtime_root)
        if not specs:
            return {"status": "ok", "prepared_count": 0, "latency_ms": 0.0}
        if profile.startswith("bge_m3_") and pipeline_factory is RagV2DevPipeline:
            batches = _preparation_batches(specs)
            batch_reports = []
            for batch_ordinal, batch in enumerate(batches, start=1):
                try:
                    for spec in batch:
                        batch_reports.append(
                            _SUBPROCESS_CLIENT.prepare_staged_source(
                                spec,
                                pipe_config,
                                group_size=4,
                            )
                        )
                except Exception as exc:
                    raise RuntimeError(
                        _batch_failure_reason(batch_ordinal, batch, exc)
                    ) from exc
            report = _aggregate_preparation_reports(batch_reports)
            report["batch_count"] = len(batches)
            report["batch_size"] = _PREPARATION_BATCH_SIZE
            report["initialization"] = init_report
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
            "latency_ms": latency_ms,
            "report": report,
        }
    except Exception as exc:
        reason = _safe_reason(exc)
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        with _PREPARATION_LOCK:
            for source in sources:
                _PREPARATION_REGISTRY[_preparation_key(resolved, source)] = (
                    _preparation_entry(
                        resolved,
                        source,
                        "failed",
                        reason=reason,
                        latency_ms=latency_ms,
                    )
                )
        LOGGER.warning(
            "Background preparation failed for %d sources: %s",
            len(sources),
            reason,
        )
        raise


def schedule_workspace_chat_source_preparation(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> None:
    """Schedule preparation once without blocking a Streamlit rerun."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return
    if not resolved.enabled:
        return

    needed: list[WorkspaceAIContextSource] = []
    with _PREPARATION_LOCK:
        for source in context_sources:
            if not (source.text or "").strip():
                continue
            key = _preparation_key(resolved, source)
            entry = _PREPARATION_REGISTRY.get(key)
            if entry is None:
                _PREPARATION_REGISTRY[key] = _preparation_entry(
                    resolved, source, "pending"
                )
                needed.append(source)

    if needed:
        _get_executor().submit(
            prepare_workspace_chat_sources,
            context_sources=tuple(needed),
            config=resolved,
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
    schedule_workspace_chat_source_preparation(sources, config=resolved)


def get_workspace_chat_source_preparation_status(
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
) -> dict[str, str]:
    """Return bounded readiness states for owner-facing UI gates."""
    try:
        resolved = config or WorkspaceChatRagV2CanaryConfig.from_env()
    except Exception:
        return {
            f"{source.source_scope}:{source.source_id}": "failed"
            for source in context_sources
            if (source.text or "").strip()
        }
    if not resolved.enabled:
        return {
            f"{source.source_scope}:{source.source_id}": "ready"
            for source in context_sources
        }

    statuses: dict[str, str] = {}
    with _PREPARATION_LOCK:
        for source in context_sources:
            identity = f"{source.source_scope}:{source.source_id}"
            if not (source.text or "").strip():
                statuses[identity] = "ready"
                continue
            entry = _PREPARATION_REGISTRY.get(_preparation_key(resolved, source))
            statuses[identity] = (
                str(entry.get("status", "not_prepared"))
                if entry is not None
                else "not_prepared"
            )
    return statuses


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

    telemetry = {
        "canary_enabled": True,
        "backend": "rag_v2_subprocess",
        "requested_profile": requested_profile,
        "effective_profile": effective_profile,
        "fallback_applied": bool(fallback_reason),
        "fallback_reason": fallback_reason,
        "latency_ms": round(latency_ms, 3),
        "candidate_count": candidate_count,
        "returned_count": returned_count,
        "filtered_as_stale_count": filtered_as_stale_count,
        "insufficiency_reasons": insufficiency_reasons,
    }
    return {
        "retrieval_applied": True,
        "evidence_items": evidence_items,
        "retrieved_context_sources": tuple(retrieved_sources),
        "summary_count": summary_count,
        "citations": citations,
        "safe_owner_message": (
            f"Đã dùng {summary_count} đoạn liên quan từ {distinct_sources} nguồn."
        ),
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
) -> dict[str, Any]:
    started = time.perf_counter()
    pipe_config = _pipeline_config(config, profile, read_only=False)
    specs, originals = _materialize_sources(sources, config.runtime_root)
    if not specs:
        raise ValueError("no_non_empty_sources")

    not_ready = []
    with _PREPARATION_LOCK:
        for source in sources:
            if not (source.text or "").strip():
                continue
            state = _PREPARATION_REGISTRY.get(
                _preparation_key(config, source), {}
            ).get("status")
            if state != _PREPARATION_READY_STATE:
                not_ready.append(source.source_id)

    if not_ready:
        raise RuntimeError("sources_not_ready")

    # query() is deliberately non-starting. Worker lifecycle belongs to
    # startup/background preparation, never to an interactive request.
    query_res_dict = _SUBPROCESS_CLIENT.query_ready(question, specs, pipe_config)
    mapped = _map_serialized_query_result(
        query_res_dict,
        originals,
        requested_profile=config.requested_profile,
        effective_profile=profile,
        fallback_reason=fallback_reason,
        latency_ms=(time.perf_counter() - started) * 1000.0,
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


def retrieve_workspace_chat_evidence(
    question: str,
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    config: Optional[WorkspaceChatRagV2CanaryConfig] = None,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline] = RagV2DevPipeline,
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

    schedule_workspace_chat_source_preparation(sources, config=resolved)
    semantic_status, semantic_reason = _semantic_readiness(sources, resolved)
    if semantic_status != _PREPARATION_READY_STATE:
        return _quality_search_unavailable(semantic_reason or semantic_status)

    try:
        return _run_profile(
            question,
            sources,
            resolved,
            "bge_m3_hybrid",
            fallback_reason="",
            pipeline_factory=pipeline_factory,
        )
    except Exception as error:
        reason = _safe_reason(error)
        LOGGER.warning("Workspace Chat BGE-M3 retrieval unavailable: %s", reason)
        return _quality_search_unavailable(reason)
