"""Client manager for the BGE Subprocess Worker.

Manages spawning, lifecycle, IPC JSON-RPC requests, timeouts, and automatic restart/fail-closed
error handling for out-of-process BGE-M3 execution.
"""
from __future__ import annotations

from dataclasses import asdict
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any, Mapping, Optional, Sequence

from aios_habit.rag_v2.pipeline import RagV2DevConfig, SourceSpec
from aios_habit.rag_v2.bge_worker_protocol import (
    authkey_for_worker,
    persistent_worker_enabled,
    pipe_name_for_config,
)
from aios_habit.rag_v2.semantic import SemanticBackendError
from aios_habit.rag_v2.adaptive_retrieval import (
    ALLOWLISTED_REASON_CODES as _ADAPTIVE_ALLOWLISTED_REASON_CODES,
)

LOGGER = logging.getLogger(__name__)

# Model-tree verification and local model loading are a bounded startup
# operation, distinct from the per-document preparation SLA. CPU cold starts can
# exceed three minutes while still completing successfully, so retain a hard fail-closed
# process deadline.
# Căn cứ số đo init thực tế 246–302s (báo cáo chẩn đoán bge-worker-diag-home.md)
# trên CPU máy nhà h410asrock, nâng trần lên 420.0s (7 phút) để không bị timeout khi máy có tải nền.
_INIT_TIMEOUT_SECONDS = 420.0
_PREPARE_TIMEOUT_SECONDS = float(os.environ.get("AIOS_BGE_PREPARE_TIMEOUT", "300.0"))
_QUERY_TIMEOUT_ENV_VAR = "AIOS_BGE_QUERY_TIMEOUT"
_INIT_TIMEOUT_ENV_VAR = "AIOS_BGE_INIT_TIMEOUT"


def default_init_timeout_seconds() -> float:
    """Bounded worker init timeout, in seconds.

    The default 420.0 s matches the fail-closed cold-start deadline above. On
    slow CPU-only hosts the physical BGE-M3 init (dense + sparse preloads) can
    exceed 300 s (bge-worker-diag-home.md: 246–302 s on h410asrock CPU), which
    used to abandon the loading worker and respawn a fresh one per attempt.
    Operators may raise or lower this via ``AIOS_BGE_INIT_TIMEOUT``; it is
    clamped to a minimum of 1.0 s so a bad value cannot disable the budget.
    """
    try:
        value = float(os.environ[_INIT_TIMEOUT_ENV_VAR])
    except (KeyError, TypeError, ValueError):
        return _INIT_TIMEOUT_SECONDS
    return max(value, 1.0)


def default_query_timeout_seconds() -> float:
    """Interactive BGE worker query timeout, in seconds.

    The default 30.0 s keeps the fail-closed per-question budget. On slow
    CPU-only hosts where a cold ONNX retrieval legitimately exceeds that
    budget (see PC0575 field report 2026-09-30: ~211 s/question when the
    coverage gate full-scanned the embeddings table), operators may raise it
    via the ``AIOS_BGE_QUERY_TIMEOUT`` environment variable. The value is
    read at import time, like ``AIOS_BGE_PREPARE_TIMEOUT``; it is clamped to
    a minimum of 1.0 s so a bad value cannot disable the budget entirely.
    """
    try:
        value = float(os.environ.get(_QUERY_TIMEOUT_ENV_VAR, "30.0"))
    except (TypeError, ValueError):
        return 30.0
    return max(value, 1.0)


_QUERY_TIMEOUT_SECONDS = default_query_timeout_seconds()
_WORKER_PROTOCOL_VERSION = "1"
_PERSIST_PROBE_TIMEOUT_SECONDS = 4.0
# Bounded wait for detached persistent worker to spawn and open named pipe.
# Căn cứ số đo model_load ONNX fp32 trên CPU mất 188–214s trước khi mở named pipe
# (báo cáo chẩn đoán bge-worker-diag-home.md), nâng từ 120s lên 360s (6 phút)
# để client kiên nhẫn chờ worker hoàn tất nạp model.
_PERSIST_SPAWN_WAIT_SECONDS = 360.0
_PERSIST_QUERY_CONNECT_SECONDS = 20.0


def _current_interpreter_supports_bge_runtime() -> bool:
    """Return whether the interpreter running this client can load BGE's runtime.

    Streamlit can re-exec an application through a lightweight ``uv`` Python.
    That interpreter is sufficient for the UI, but it does not necessarily own
    the project's PyTorch/FlagEmbedding installation.  A worker spawned via
    ``sys.executable`` in that case fails before it can report useful BGE
    readiness.
    """
    return all(
        importlib.util.find_spec(package) is not None
        for package in ("torch", "FlagEmbedding")
    )


def _project_virtualenv_python() -> Path | None:
    """Find this checkout's Windows virtual-environment interpreter, if any."""
    project_root = Path(__file__).resolve().parents[3]
    candidate = project_root / ".venv" / "Scripts" / "python.exe"
    return candidate if candidate.is_file() else None


def _default_worker_python_executable() -> str:
    """Choose an interpreter that can actually load the local BGE runtime."""
    if _current_interpreter_supports_bge_runtime():
        return sys.executable
    project_python = _project_virtualenv_python()
    if project_python is not None:
        LOGGER.info(
            "BGE worker is using the project virtual environment because the UI interpreter lacks the BGE runtime"
        )
        return str(project_python)
    return sys.executable

# Single source of truth lives in adaptive_retrieval (the producer of these
# codes). This used to be a hand-copied set that drifted: pre_retrieval_gate
# can emit causality_intent / contradiction_intent / temporal_change_intent /
# multi_part_query, which the stale copy rejected with
# invalid_routing_reason_code (E1 blocked, 2026-10-01).
ALLOWLISTED_ROUTING_REASON_CODES = frozenset(_ADAPTIVE_ALLOWLISTED_REASON_CODES)


def _config_to_dict(config: RagV2DevConfig) -> dict[str, Any]:
    raw = asdict(config)
    for key, value in list(raw.items()):
        if isinstance(value, Path):
            raw[key] = str(value)
        elif isinstance(value, tuple):
            raw[key] = list(value)
    return raw


def _spec_to_dict(spec: SourceSpec) -> dict[str, Any]:
    return {
        "path": str(spec.path),
        "source_id": spec.source_id,
        "document_id": spec.document_id,
        "privacy_labels": list(spec.privacy_labels),
        "enabled": spec.enabled,
        "owner_consent": spec.owner_consent,
        "language_hints": list(spec.language_hints),
    }


class BgeSubprocessWorkerClient:
    """Thread-safe client managing an isolated BGE-M3 worker process."""

    def __init__(self, python_executable: str | None = None) -> None:
        self._python_executable = python_executable or _default_worker_python_executable()
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.RLock()
        self._active_config: RagV2DevConfig | None = None
        self._stderr_thread: threading.Thread | None = None
        self._last_failure_reason = "not_initialized"
        # In-flight or completed-but-unconsumed init request. Keeping this lets
        # a caller that timed out wait for the same loading worker instead of
        # killing it and spawning a duplicate (PC0575 cold-start finding).
        self._pending_init: dict[str, Any] | None = None

    def readiness(self, config: RagV2DevConfig | None = None) -> dict[str, Any]:
        """Return bounded worker health without launching or exposing private data."""
        if config is not None and self._persistent_applies(config):
            return self._persistent_readiness(config)
        if not self._lock.acquire(timeout=0.5):
            return {"ready": False, "alive": True, "configuration_matches": False, "reason": "worker_busy", "pid": None}
        try:
            alive = self._process is not None and self._process.poll() is None
            pending = (
                alive
                and self._pending_init is not None
                and (config is None or self._pending_init["config"] == config)
            )
            matches = alive and (config is None or self._active_config == config)
            return {
                "ready": bool(matches),
                "alive": bool(alive),
                "configuration_matches": bool(matches),
                "reason": (
                    ""
                    if matches
                    else ("bge_worker_init_pending" if pending else self._last_failure_reason)
                ),
                "pid": self._process.pid if matches and self._process is not None else None,
            }
        finally:
            self._lock.release()

    def is_ready(self, config: RagV2DevConfig) -> bool:
        return bool(self.readiness(config)["ready"])

    def is_alive(self) -> bool:
        if not self._lock.acquire(timeout=0.5):
            return True
        try:
            return self._process is not None and self._process.poll() is None
        finally:
            self._lock.release()

    def clear_failure_reason(self) -> None:
        """Clear cached failure reason to allow fresh retry on subsequent attempts."""
        with self._lock:
            self._last_failure_reason = ""

    def _start_worker_locked(self, config: RagV2DevConfig) -> None:
        """Track an init request for ``config``: keep a pending one or spawn.

        Called with the lock held. Waiting happens in ``_await_pending_init``
        OUTSIDE the lock so concurrent callers (UI warm-up thread + question
        thread) can wait on the same loading worker instead of failing with
        ``worker_busy``.
        """
        pending = self._pending_init
        if (
            pending is not None
            and pending["config"] == config
            and pending["process"] is self._process
            and self._process is not None
            and self._process.poll() is None
        ):
            return

        self._close_internal()
        cmd = [
            self._python_executable,
            "-X",
            "faulthandler",
            "-m",
            "aios_habit.rag_v2.bge_subprocess_worker",
        ]
        stderr_path = Path(config.runtime_root) / "logs" / "bge_worker.stderr.log"
        try:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
            env["OMP_NUM_THREADS"] = "1"
            env["MKL_NUM_THREADS"] = "1"
            env["OPENBLAS_NUM_THREADS"] = "1"
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                cwd=str(Path(config.runtime_root).parent.parent.resolve() if Path(config.runtime_root).is_absolute() else Path.cwd()),
            )
            proc = self._process

            def consume_stderr() -> None:
                try:
                    with stderr_path.open("w", encoding="utf-8") as log_handle:
                        if proc.stderr is not None:
                            for line in proc.stderr:
                                log_handle.write(line)
                                log_handle.flush()
                except Exception as exc:
                    LOGGER.warning("BGE worker stderr capture failed: %s", type(exc).__name__)

            self._stderr_thread = threading.Thread(
                target=consume_stderr,
                name="bge-worker-stderr",
                daemon=True,
            )
            self._stderr_thread.start()
        except Exception as exc:
            self._last_failure_reason = "bge_worker_init_spawn_failed"
            LOGGER.error("Failed to spawn BGE subprocess worker: %s", type(exc).__name__)
            raise SemanticBackendError(self._last_failure_reason) from exc

        started = time.perf_counter()
        try:
            if proc.stdin is None:
                raise SemanticBackendError("bge_worker_process_not_available")
            proc.stdin.write(json.dumps({"command": "init", "config": _config_to_dict(config)}) + "\n")
            proc.stdin.flush()
        except Exception as exc:
            self._last_failure_reason = "bge_worker_stdin_closed"
            self._close_internal(preserve_failure=True)
            raise SemanticBackendError(self._last_failure_reason) from exc

        init_result: list[tuple[str, Any]] = []

        def await_init_response() -> None:
            try:
                line = proc.stdout.readline() if proc.stdout is not None else ""
                if not line:
                    init_result.append(("eof", None))
                    return
                init_result.append(("response", json.loads(line.strip())))
            except Exception as exc:  # defensive: reader failures surface as init errors
                init_result.append(("error", exc))

        init_reader = threading.Thread(
            target=await_init_response,
            name="bge-worker-init",
            daemon=True,
        )
        self._pending_init = {
            "config": config,
            "thread": init_reader,
            "result": init_result,
            "started": started,
            "process": proc,
        }
        init_reader.start()

    def _await_pending_init(
        self,
        *,
        timeout_s: float | None,
        config: RagV2DevConfig,
    ) -> dict[str, Any]:
        """Wait for a tracked worker init; keep it alive on timeout.

        The join happens WITHOUT holding the client lock; finalization runs
        under the lock so concurrent waiters converge on one outcome.
        """
        timeout = default_init_timeout_seconds() if timeout_s is None else float(timeout_s)
        if not self._lock.acquire(timeout=10.0):
            raise SemanticBackendError("worker_busy")
        try:
            pending = self._pending_init
            if (
                pending is None
                or pending["config"] != config
                or pending["process"] is not self._process
            ):
                if (
                    self._active_config == config
                    and self._process is not None
                    and self._process.poll() is None
                ):
                    return {"status": "ok", "reused": True, "init_latency_ms": 0.0}
                raise SemanticBackendError("bge_worker_init_not_pending")
        finally:
            self._lock.release()
        thread = pending["thread"]
        thread.join(timeout=max(0.0, timeout))
        if thread.is_alive():
            # Do not kill the loading process; a later caller resumes waiting.
            self._last_failure_reason = "bge_worker_init_timeout"
            raise SemanticBackendError(self._last_failure_reason)
        if not self._lock.acquire(timeout=10.0):
            raise SemanticBackendError("worker_busy")
        try:
            if self._pending_init is not pending:
                # Another waiter consumed this init first.
                if (
                    self._active_config == config
                    and self._process is not None
                    and self._process.poll() is None
                ):
                    return {"status": "ok", "reused": True, "init_latency_ms": 0.0}
                raise SemanticBackendError(
                    self._last_failure_reason or "bge_worker_init_superseded"
                )
            self._pending_init = None
            result = pending["result"]
            if not result:
                self._close_internal(preserve_failure=True)
                self._last_failure_reason = "bge_worker_init_no_response"
                raise SemanticBackendError(self._last_failure_reason)
            kind, payload = result[0]
            if kind != "response":
                self._close_internal(preserve_failure=True)
                self._last_failure_reason = (
                    "bge_worker_init_exception" if kind == "error" else "bge_worker_init_stdout_eof"
                )
                raise SemanticBackendError(self._last_failure_reason)
            res = payload if isinstance(payload, dict) else {}
            if res.get("status") != "ok":
                worker_phase = str(res.get("error_phase", "init"))
                safe_phase = worker_phase if worker_phase in {"model_verify", "model_load", "index_open", "init"} else "init"
                self._close_internal(preserve_failure=True)
                self._last_failure_reason = f"bge_worker_{safe_phase}_failed"
                raise SemanticBackendError(self._last_failure_reason)
            readiness = res.get("readiness")
            if not isinstance(readiness, dict):
                self._close_internal(preserve_failure=True)
                self._last_failure_reason = "bge_worker_init_invalid_response"
                raise SemanticBackendError(self._last_failure_reason)
            self._active_config = config
            self._last_failure_reason = ""
            report = {
                "status": "ok",
                "reused": False,
                "init_latency_ms": round((time.perf_counter() - pending["started"]) * 1000.0, 3),
                "readiness": readiness,
            }
            LOGGER.info("BGE worker initialized successfully (PID %s)", readiness.get("pid"))
            return report
        finally:
            self._lock.release()

    def initialize_worker(
        self,
        config: RagV2DevConfig,
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """Load the matching model worker before any source preparation begins."""
        if self._persistent_applies(config):
            return self._initialize_worker_persistent(config, timeout_s=timeout_s)
        if not self._lock.acquire(timeout=0.5):
            raise SemanticBackendError("worker_busy")
        try:
            if (
                self._process is not None
                and self._process.poll() is None
                and self._active_config == config
            ):
                return {"status": "ok", "reused": True, "init_latency_ms": 0.0}
            self._start_worker_locked(config)
        finally:
            self._lock.release()
        return self._await_pending_init(timeout_s=timeout_s, config=config)

    def start_worker(self, config: RagV2DevConfig) -> None:
        """Backward-compatible explicit worker startup entry point."""
        self.initialize_worker(config)

    def ensure_started(self, config: RagV2DevConfig) -> None:
        """Backward-compatible explicit initialization alias."""
        self.initialize_worker(config)

    def prepare_sources(
        self,
        specs: Sequence[SourceSpec],
        config: RagV2DevConfig,
        timeout_s: float = _PREPARE_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Prepare sources only on an already initialized matching worker."""
        if not self._lock.acquire(timeout=0.5):
            raise SemanticBackendError("worker_busy")
        try:
            if self._process is None or self._process.poll() is not None:
                raise SemanticBackendError("bge_worker_prepare_not_initialized")
            if self._active_config != config:
                raise SemanticBackendError("bge_worker_prepare_configuration_mismatch")

            req = {
                "command": "prepare_sources",
                "specs": [_spec_to_dict(s) for s in specs],
            }
            try:
                res = self._send_request(req, timeout_s=timeout_s, phase="prepare")
            except Exception as exc:
                LOGGER.warning("BGE worker prepare_sources failed: %s", exc)
                self._close_internal()
                if isinstance(exc, SemanticBackendError):
                    raise
                raise SemanticBackendError("bge_worker_prepare_exception") from exc

            if res.get("status") != "ok":
                raise RuntimeError("bge_worker_prepare_failed")

            ingest_report = res.get("ingest_report")
            if not isinstance(ingest_report, dict):
                raise RuntimeError("invalid_worker_response_schema")
            return ingest_report
        finally:
            self._lock.release()

    def prepare_staged_source(
        self,
        spec: SourceSpec,
        config: RagV2DevConfig,
        *,
        group_size: int = 4,
        timeout_s: float = _PREPARE_TIMEOUT_SECONDS,
        source_timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """Prepare one source through bounded worker-local embedding groups.

        The worker publishes chunks only after every retrievable staged chunk has
        a vector, keeping an existing indexed document visible on any failure.
        """
        if group_size < 1:
            raise ValueError("group_size must be positive")
        if source_timeout_s is not None and float(source_timeout_s) <= 0:
            raise ValueError("source_timeout_s must be positive")
        if not self._lock.acquire(timeout=0.5):
            raise SemanticBackendError("worker_busy")
        try:
            if self._process is None or self._process.poll() is not None:
                raise SemanticBackendError("bge_worker_prepare_not_initialized")
            if self._active_config != config:
                raise SemanticBackendError("bge_worker_prepare_configuration_mismatch")
            document_id = spec.document_id
            deadline_at = (
                time.monotonic() + float(source_timeout_s)
                if source_timeout_s is not None
                else None
            )

            def bounded_timeout() -> float:
                if deadline_at is None:
                    return timeout_s
                remaining = deadline_at - time.monotonic()
                if remaining <= 0:
                    raise SemanticBackendError("bge_worker_source_deadline_exceeded")
                return min(timeout_s, remaining)

            try:
                staged = self._send_request(
                    {"command": "stage_source", "spec": _spec_to_dict(spec)},
                    timeout_s=bounded_timeout(),
                    phase="stage",
                )
                if staged.get("status") != "ok" or not isinstance(staged.get("staged"), dict):
                    raise SemanticBackendError("bge_worker_stage_invalid_response")
                stage_report = staged["staged"]
                if stage_report.get("status") == "unchanged":
                    return {
                        "converted_count": 0,
                        "skipped_count": 1,
                        "failed_count": 0,
                        "indexed_chunk_count": 0,
                    }
                while True:
                    progress = self._send_request(
                        {
                            "command": "embed_staged_chunk_group",
                            "document_id": document_id,
                            "group_size": group_size,
                        },
                        timeout_s=bounded_timeout(),
                        phase="prepare",
                    )
                    details = progress.get("progress")
                    if progress.get("status") != "ok" or not isinstance(details, dict):
                        raise SemanticBackendError("bge_worker_staged_embed_invalid_response")
                    if int(details.get("remaining_count", -1)) == 0:
                        break
                committed = self._send_request(
                    {"command": "commit_staged_source", "document_id": document_id},
                    timeout_s=bounded_timeout(),
                    phase="commit",
                )
                report = committed.get("ingest_report")
                if committed.get("status") != "ok" or not isinstance(report, dict):
                    raise SemanticBackendError("bge_worker_staged_commit_invalid_response")
                return report
            except Exception as exc:
                LOGGER.warning("BGE worker staged source preparation failed: %s", exc)
                try:
                    self._send_request(
                        {"command": "abort_staged_source", "document_id": document_id},
                        timeout_s=2.0,
                        phase="abort",
                    )
                except Exception:
                    pass
                self._close_internal()
                if isinstance(exc, SemanticBackendError):
                    raise
                raise SemanticBackendError("bge_worker_staged_prepare_exception") from exc
        finally:
            self._lock.release()

    def delete_documents(
        self,
        document_ids: Sequence[str],
        *,
        timeout_s: float = _QUERY_TIMEOUT_SECONDS,
    ) -> int:
        """Remove indexed chunks for deleted Workspace Chat documents."""
        normalized_ids = [str(document_id).strip() for document_id in document_ids if str(document_id).strip()]
        if not normalized_ids:
            return 0
        if not self._lock.acquire(timeout=0.5):
            raise SemanticBackendError("worker_busy")
        try:
            if self._process is None or self._process.poll() is not None:
                return 0
            response = self._send_request(
                {"command": "delete_documents", "document_ids": normalized_ids},
                timeout_s=timeout_s,
                phase="delete",
            )
        finally:
            self._lock.release()
        if response.get("status") != "ok":
            raise SemanticBackendError("bge_worker_delete_failed")
        return int(response.get("removed_chunk_count", 0))

    def query_ready(
        self,
        question: str,
        specs: Sequence[SourceSpec],
        config: RagV2DevConfig,
        timeout_s: float = _QUERY_TIMEOUT_SECONDS,
        expansion: Optional[Mapping[str, Any]] = None,
        rerank_requested: bool = False,
        routing_reason_codes: Sequence[str] = (),
        policy_version: str = "adaptive-reranking-v1",
    ) -> dict[str, Any]:
        """Query an already-ready worker; never spawn or load a model here."""
        for code in routing_reason_codes:
            if not isinstance(code, str) or code not in ALLOWLISTED_ROUTING_REASON_CODES or len(code) > 48:
                raise SemanticBackendError("invalid_routing_reason_code")
        if len(routing_reason_codes) > 8:
            raise SemanticBackendError("invalid_routing_reason_code_count")
        if len(policy_version) > 64:
            raise SemanticBackendError("invalid_policy_version_length")

        if self._persistent_applies(config):
            return self._query_ready_persistent(
                question,
                specs,
                config,
                timeout_s=timeout_s,
                expansion=expansion,
                rerank_requested=rerank_requested,
                routing_reason_codes=routing_reason_codes,
                policy_version=policy_version,
            )

        if not self._lock.acquire(timeout=0.5):
            raise SemanticBackendError("worker_busy")
        try:
            if self._process is None:
                self._last_failure_reason = "bge_worker_query_not_ready"
                raise SemanticBackendError(self._last_failure_reason)
            if self._process.poll() is not None:
                self._close_internal(preserve_failure=True)
                self._last_failure_reason = "bge_worker_query_not_ready"
                raise SemanticBackendError(self._last_failure_reason)
            if self._active_config != config:
                self._last_failure_reason = "bge_worker_query_configuration_mismatch"
                raise SemanticBackendError(self._last_failure_reason)

            req: dict[str, Any] = {
                "command": "query",
                "question": question,
                "specs": [_spec_to_dict(s) for s in specs],
                "routing": {
                    "schema_version": 1,
                    "rerank_requested": bool(rerank_requested),
                    "reason_codes": list(routing_reason_codes),
                    "policy_version": str(policy_version),
                },
            }
            if expansion is not None:
                req["expansion"] = expansion
            try:
                res = self._send_request(req, timeout_s=timeout_s, phase="query")
            except Exception as exc:
                LOGGER.warning("BGE worker query failed/crashed: %s", type(exc).__name__)
                self._last_failure_reason = "bge_subprocess_worker_crashed"
                self._close_internal(preserve_failure=True)
                raise SemanticBackendError(self._last_failure_reason) from exc

            if res.get("status") != "ok":
                self._last_failure_reason = "bge_worker_query_failed"
                raise SemanticBackendError(self._last_failure_reason)

            query_result = res.get("query_result")
            if not isinstance(query_result, dict):
                raise RuntimeError("invalid_worker_response_schema")
            return query_result
        finally:
            self._lock.release()

    def query(
        self,
        question: str,
        specs: Sequence[SourceSpec],
        config: RagV2DevConfig,
        timeout_s: float = _QUERY_TIMEOUT_SECONDS,
        expansion: Optional[Mapping[str, Any]] = None,
        rerank_requested: bool = False,
        routing_reason_codes: Sequence[str] = (),
        policy_version: str = "adaptive-reranking-v1",
    ) -> dict[str, Any]:
        """Backward-compatible alias for the non-starting interactive query."""
        return self.query_ready(
            question,
            specs,
            config,
            timeout_s=timeout_s,
            expansion=expansion,
            rerank_requested=rerank_requested,
            routing_reason_codes=routing_reason_codes,
            policy_version=policy_version,
        )


    def ingest_and_query(
        self,
        question: str,
        specs: Sequence[SourceSpec],
        config: RagV2DevConfig,
        timeout_s: float = 90.0,
        expansion: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Send ingest_and_query request to worker, auto-relaunching if worker died."""
        if not self._lock.acquire(timeout=0.5):
            raise SemanticBackendError("worker_busy")
        try:
            if self._process is None or self._process.poll() is not None or self._active_config != config:
                self._start_worker_locked(config)
                self._await_pending_init(timeout_s=None, config=config)

            req = {
                "command": "ingest_and_query",
                "question": question,
                "specs": [_spec_to_dict(s) for s in specs],
            }
            if expansion is not None:
                req["expansion"] = expansion
            try:
                res = self._send_request(req, timeout_s=timeout_s, phase="ingest")
            except Exception as exc:
                LOGGER.warning("BGE worker process request failed/crashed: %s", exc)
                self._close_internal()
                raise SemanticBackendError("bge_subprocess_worker_crashed") from exc

            if res.get("status") != "ok":
                err = str(res.get("error", "unknown_worker_error"))
                raise RuntimeError(err)

            query_result = res.get("query_result")
            if not isinstance(query_result, dict):
                raise RuntimeError("invalid_worker_response_schema")
            return query_result
        finally:
            self._lock.release()

    def _send_request(
        self,
        payload: dict[str, Any],
        timeout_s: float,
        *,
        phase: str,
    ) -> dict[str, Any]:
        """Internal helper to write to stdin and read single JSON line response from stdout."""
        proc = self._process
        if proc is None or proc.stdin is None or proc.stdout is None:
            raise SemanticBackendError("bge_worker_process_not_available")

        request_line = json.dumps(payload) + "\n"
        try:
            proc.stdin.write(request_line)
            proc.stdin.flush()
        except (OSError, ValueError) as exc:
            raise SemanticBackendError("bge_worker_stdin_closed") from exc

        result_container: list[dict[str, Any] | Exception] = []

        def _reader() -> None:
            try:
                line = proc.stdout.readline()  # type: ignore[union-attr]
                if not line:
                    result_container.append(
                        SemanticBackendError(f"bge_worker_{phase}_stdout_eof")
                    )
                    return
                result_container.append(json.loads(line.strip()))
            except Exception as err:
                result_container.append(err)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()
        reader_thread.join(timeout=timeout_s)

        if reader_thread.is_alive():
            raise SemanticBackendError(f"bge_worker_{phase}_timeout")

        if not result_container:
            raise SemanticBackendError(f"bge_worker_{phase}_no_response")

        res = result_container[0]
        if isinstance(res, Exception):
            raise res
        return res

    def _close_internal(self, *, preserve_failure: bool = False) -> None:
        proc = self._process
        self._process = None
        self._active_config = None
        self._pending_init = None
        if not preserve_failure:
            self._last_failure_reason = "not_initialized"
        if proc is not None:
            try:
                if proc.poll() is None:
                    if proc.stdin is not None:
                        try:
                            proc.stdin.write(json.dumps({"command": "close"}) + "\n")
                            proc.stdin.flush()
                        except Exception:
                            pass
                    proc.wait(timeout=1.5)
            except Exception:
                pass
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=1.0)
            except Exception:
                pass
            try:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=1.0)
            except Exception:
                pass
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
        stderr_thread = self._stderr_thread
        self._stderr_thread = None
        if stderr_thread is not None and stderr_thread is not threading.current_thread():
            stderr_thread.join(timeout=1.0)

    def close(self) -> None:
        acquired = self._lock.acquire(timeout=2.0)
        try:
            self._close_internal()
        finally:
            if acquired:
                self._lock.release()

    # ------------------------------------------------------------------
    # Persistent named-pipe worker transport (SPEED-COLDSTART-PC0575).
    # Enabled by AIOS_RAGV2_WORKER_PERSIST; read-only query configs only, so a
    # warm worker outlives Streamlit restarts while write-mode preparation
    # keeps using the legacy ephemeral subprocess.
    # ------------------------------------------------------------------

    def _persistent_applies(self, config: RagV2DevConfig | None) -> bool:
        return bool(
            config is not None
            and getattr(config, "index_read_only", False)
            and persistent_worker_enabled()
            and os.name == "nt"
        )

    def _persistent_readiness(self, config: RagV2DevConfig) -> dict[str, Any]:
        try:
            response = self._persistent_exchange(
                config,
                {"command": "health", "config": _config_to_dict(config)},
                timeout_s=_PERSIST_PROBE_TIMEOUT_SECONDS,
                connect_timeout_s=_PERSIST_PROBE_TIMEOUT_SECONDS,
                allow_spawn=False,
            )
        except Exception as exc:
            return {
                "ready": False,
                "alive": False,
                "configuration_matches": False,
                "reason": str(exc) or "bge_worker_persist_unavailable",
                "pid": None,
            }
        initialized = bool(response.get("initialized"))
        matches = bool(response.get("configuration_matches"))
        ready = initialized and matches
        return {
            "ready": ready,
            "alive": True,
            "configuration_matches": matches,
            "reason": (
                ""
                if ready
                else (
                    "worker_not_initialized"
                    if not initialized
                    else "bge_worker_configuration_mismatch"
                )
            ),
            "pid": response.get("pid"),
        }

    def _initialize_worker_persistent(
        self,
        config: RagV2DevConfig,
        *,
        timeout_s: float | None,
    ) -> dict[str, Any]:
        timeout = default_init_timeout_seconds() if timeout_s is None else float(timeout_s)
        started = time.perf_counter()
        try:
            response = self._persistent_exchange(
                config,
                {"command": "init", "config": _config_to_dict(config)},
                timeout_s=timeout,
                connect_timeout_s=min(timeout, _PERSIST_SPAWN_WAIT_SECONDS),
                allow_spawn=True,
            )
        except SemanticBackendError as exc:
            self._last_failure_reason = str(exc)
            raise
        except Exception as exc:
            self._last_failure_reason = "bge_worker_persist_init_exception"
            raise SemanticBackendError(self._last_failure_reason) from exc
        if response.get("status") != "ok":
            self._last_failure_reason = str(response.get("error", "bge_worker_init_failed"))
            raise SemanticBackendError(self._last_failure_reason)
        readiness = response.get("readiness")
        if not isinstance(readiness, dict):
            self._last_failure_reason = "bge_worker_init_invalid_response"
            raise SemanticBackendError(self._last_failure_reason)
        self._last_failure_reason = ""
        return {
            "status": "ok",
            "reused": bool(readiness.get("reused", False)),
            "init_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "readiness": readiness,
        }

    def _query_ready_persistent(
        self,
        question: str,
        specs: Sequence[SourceSpec],
        config: RagV2DevConfig,
        *,
        timeout_s: float,
        expansion: Optional[Mapping[str, Any]],
        rerank_requested: bool,
        routing_reason_codes: Sequence[str],
        policy_version: str,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "command": "query",
            "question": question,
            "specs": [_spec_to_dict(s) for s in specs],
            "routing": {
                "schema_version": 1,
                "rerank_requested": bool(rerank_requested),
                "reason_codes": list(routing_reason_codes),
                "policy_version": str(policy_version),
            },
        }
        if expansion is not None:
            request["expansion"] = expansion
        try:
            response = self._persistent_exchange(
                config,
                request,
                timeout_s=timeout_s,
                connect_timeout_s=min(float(timeout_s), _PERSIST_QUERY_CONNECT_SECONDS),
                allow_spawn=False,
            )
        except SemanticBackendError:
            raise
        except Exception as exc:
            raise SemanticBackendError("bge_worker_persist_query_exception") from exc
        if response.get("status") != "ok":
            raise SemanticBackendError("bge_worker_query_failed")
        query_result = response.get("query_result")
        if not isinstance(query_result, dict):
            raise RuntimeError("invalid_worker_response_schema")
        return query_result

    def shutdown_persistent_worker(self, config: RagV2DevConfig) -> bool:
        """Ask the persistent worker to exit (test/maintenance helper)."""
        if not self._persistent_applies(config):
            return False
        try:
            response = self._persistent_exchange(
                config,
                {"command": "shutdown"},
                timeout_s=10.0,
                connect_timeout_s=2.0,
                allow_spawn=False,
            )
        except Exception:
            return False
        return response.get("status") == "ok"

    def _persistent_exchange(
        self,
        config: RagV2DevConfig,
        payload: Mapping[str, Any],
        *,
        timeout_s: float,
        connect_timeout_s: float,
        allow_spawn: bool,
    ) -> dict[str, Any]:
        """One request/response over the config-bound named pipe.

        The whole session (optional detached spawn, connect, send, receive)
        runs in a helper thread joined with ``timeout_s``; waiting never holds
        the client lock, so concurrent callers can queue behind one loading
        worker instead of failing with ``worker_busy``.
        """
        pipe_name = pipe_name_for_config(config)
        authkey = authkey_for_worker()
        result: list[tuple[str, Any]] = []

        def _session() -> None:
            try:
                import multiprocessing.connection as mpc

                spawned = False
                connect_deadline = time.monotonic() + max(float(connect_timeout_s), 0.5)
                while True:
                    try:
                        conn = mpc.Client(pipe_name, family="AF_PIPE", authkey=authkey)
                        break
                    except OSError as exc:
                        if (
                            allow_spawn
                            and not spawned
                            and not _pipe_instance_available(pipe_name)
                        ):
                            self._spawn_persistent_worker(config, pipe_name)
                            spawned = True
                        if (
                            not allow_spawn
                            and not _pipe_instance_available(pipe_name)
                        ):
                            raise SemanticBackendError(
                                "bge_worker_persist_unavailable"
                            ) from exc
                        if time.monotonic() >= connect_deadline:
                            raise SemanticBackendError(
                                "bge_worker_persist_unavailable"
                            ) from exc
                        time.sleep(0.25)
                try:
                    conn.send(dict(payload))
                    response = conn.recv()
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
                result.append(("ok", response))
            except Exception as exc:
                result.append(("error", exc))

        thread = threading.Thread(target=_session, name="bge-worker-pipe", daemon=True)
        thread.start()
        thread.join(timeout=max(0.0, float(timeout_s)))
        if thread.is_alive():
            raise SemanticBackendError("bge_worker_persist_timeout")
        if not result:
            raise SemanticBackendError("bge_worker_persist_no_response")
        kind, value = result[0]
        if kind == "error":
            if isinstance(value, SemanticBackendError):
                raise value
            raise SemanticBackendError("bge_worker_persist_failed") from value
        if not isinstance(value, dict):
            raise SemanticBackendError("bge_worker_persist_invalid_response")
        return value

    def _spawn_persistent_worker(self, config: RagV2DevConfig, pipe_name: str) -> None:
        """Start the detached named-pipe worker; it outlives this process."""
        logs_dir = Path(config.runtime_root) / "logs"
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        log_path = logs_dir / "bge_worker_daemon.stderr.log"
        cmd = [
            self._python_executable,
            "-X",
            "faulthandler",
            "-m",
            "aios_habit.rag_v2.bge_subprocess_worker",
            "--serve",
            "--pipe",
            pipe_name,
        ]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        cwd = (
            str(Path(config.runtime_root).parent.parent.resolve())
            if Path(config.runtime_root).is_absolute()
            else str(Path.cwd())
        )
        try:
            with log_path.open("a", encoding="utf-8") as log_handle:
                subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=log_handle,
                    env=env,
                    cwd=cwd,
                    creationflags=creationflags,
                    close_fds=True,
                )
        except Exception as exc:
            LOGGER.warning("Persistent BGE worker spawn failed: %s", type(exc).__name__)


def _pipe_instance_available(pipe_name: str) -> bool:
    """Windows WaitNamedPipe probe; False when the pipe is absent (or busy)."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        probe = kernel32.WaitNamedPipeW
        probe.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        probe.restype = ctypes.c_int
        return bool(probe(pipe_name, 0))
    except Exception:
        return False
