"""Client manager for the BGE Subprocess Worker.

Manages spawning, lifecycle, IPC JSON-RPC requests, timeouts, and automatic restart/fail-closed
error handling for out-of-process BGE-M3 execution.
"""
from __future__ import annotations

from dataclasses import asdict
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
from aios_habit.rag_v2.semantic import SemanticBackendError

LOGGER = logging.getLogger(__name__)

# Model-tree verification and local PyTorch model loading are a bounded startup
# operation, distinct from the per-document preparation SLA. CPU cold starts can
# exceed three minutes while still completing successfully, so allow five minutes
# but retain a hard fail-closed process deadline.
_INIT_TIMEOUT_SECONDS = 300.0
_PREPARE_TIMEOUT_SECONDS = 90.0
_QUERY_TIMEOUT_SECONDS = 30.0
_WORKER_PROTOCOL_VERSION = "1"

ALLOWLISTED_ROUTING_REASON_CODES = {
    "user_requested_deep",
    "user_preference_auto",
    "pre_fast",
    "pre_deep",
    "pre_uncertain",
    "post_sufficient",
    "post_insufficient",
    "post_uncertain",
    "multi_facet",
    "cross_source_intent",
    "comparison_intent",
    "verification_requested",
    "insufficient_structure_signal",
    "missing_facets",
    "missing_obligations",
    "low_evidence_coverage",
    "insufficient_source_diversity",
    "insufficient_candidates",
    "ranking_ambiguous",
    "retrieval_report_incomplete",
    "reranker_backend_unavailable",
    "reranker_backend_timeout",
    "reranker_backend_failed",
    "circuit_breaker_open",
    "structured_excel_handled",
    "structured_excel_bypass",
    "invalid_preference_fallback",
}


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
        self._python_executable = python_executable or sys.executable
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.RLock()
        self._active_config: RagV2DevConfig | None = None
        self._stderr_thread: threading.Thread | None = None
        self._last_failure_reason = "not_initialized"

    def readiness(self, config: RagV2DevConfig | None = None) -> dict[str, Any]:
        """Return bounded worker health without launching or exposing private data."""
        with self._lock:
            alive = self._process is not None and self._process.poll() is None
            matches = alive and (config is None or self._active_config == config)
            return {
                "ready": bool(matches),
                "alive": bool(alive),
                "configuration_matches": bool(matches),
                "reason": "" if matches else self._last_failure_reason,
                "pid": self._process.pid if matches and self._process is not None else None,
            }

    def is_ready(self, config: RagV2DevConfig) -> bool:
        return bool(self.readiness(config)["ready"])

    def is_alive(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def _start_worker_locked(
        self,
        config: RagV2DevConfig,
        *,
        timeout_s: float = _INIT_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Launch and initialize a fresh worker under the held lock."""
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
            res = self._send_request(
                {"command": "init", "config": _config_to_dict(config)},
                timeout_s=timeout_s,
                phase="init",
            )
            if res.get("status") != "ok":
                worker_phase = str(res.get("error_phase", "init"))
                safe_phase = worker_phase if worker_phase in {"model_verify", "model_load", "index_open", "init"} else "init"
                raise SemanticBackendError(f"bge_worker_{safe_phase}_failed")
            readiness = res.get("readiness")
            if not isinstance(readiness, dict):
                raise SemanticBackendError("bge_worker_init_invalid_response")
            self._active_config = config
            self._last_failure_reason = ""
            report = {
                "status": "ok",
                "reused": False,
                "init_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
                "readiness": readiness,
            }
            LOGGER.info("BGE worker initialized successfully (PID %s)", readiness.get("pid"))
            return report
        except Exception as exc:
            if isinstance(exc, SemanticBackendError):
                self._last_failure_reason = str(exc)
            else:
                self._last_failure_reason = "bge_worker_init_exception"
            self._close_internal(preserve_failure=True)
            if isinstance(exc, SemanticBackendError):
                raise
            raise SemanticBackendError(self._last_failure_reason) from exc

    def initialize_worker(
        self,
        config: RagV2DevConfig,
        *,
        timeout_s: float = _INIT_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Load the matching model worker before any source preparation begins."""
        with self._lock:
            if (
                self._process is not None
                and self._process.poll() is None
                and self._active_config == config
            ):
                return {"status": "ok", "reused": True, "init_latency_ms": 0.0}
            return self._start_worker_locked(config, timeout_s=timeout_s)

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
        with self._lock:
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
        with self._lock:
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

        with self._lock:
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
        with self._lock:
            if self._process is None or self._process.poll() is not None or self._active_config != config:
                self._start_worker_locked(config)

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
        with self._lock:
            self._close_internal()
