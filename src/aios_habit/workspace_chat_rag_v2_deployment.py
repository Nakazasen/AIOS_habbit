"""Machine-local deployment manifest for Workspace Chat RAG v2.

Only an ``activated`` manifest that passes every production gate may enable
BGE-M3 in normal Workspace Chat. Staged, malformed, or incomplete manifests
leave the existing path unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

DEPLOYMENT_MANIFEST_ENV = "AIOS_WORKSPACE_RAG_V2_MANIFEST"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEPLOYMENT_MANIFEST = PROJECT_ROOT / "config/workspace_chat_rag_v2.local.json"
DEPLOYMENT_SCHEMA_VERSION = 2
ACTIVATED_STATE = "activated"
STAGED_STATE = "staged"
ROLLED_BACK_STATE = "rolled_back"
EXPECTED_PROFILE = "bge_m3_hybrid"
EXPECTED_EVIDENCE_RUN_ID = "SELECTED-bge_m3_hybrid-1785169154-e33e5670"
EXPECTED_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
EXPECTED_MODEL_CHECKSUM = (
    "sha256:f8faedab99c4c901e5c2f311ea3f32786b3395b5cbb0c10a60c2b83970d64405"
)
MAX_WARM_P95_MS = 3000.0


class DeploymentManifestError(RuntimeError):
    """Raised when an activated deployment manifest is not trustworthy."""


@dataclass(frozen=True)
class WorkspaceChatRagV2Deployment:
    """Validated machine-local settings for one production deployment."""

    manifest_path: Path
    activation_state: str
    requested_profile: str
    runtime_root: Path
    model_path: Path
    model_revision: str
    model_checksum: str
    retrieval_device: str
    fail_closed: bool
    evidence_run_id: str
    benchmark_status: str

    @property
    def activated(self) -> bool:
        return self.activation_state == ACTIVATED_STATE


def _manifest_path(
    path: Optional[str | Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Path:
    if path is not None:
        return Path(path)
    values = os.environ if env is None else env
    override = str(values.get(DEPLOYMENT_MANIFEST_ENV, "") or "").strip()
    return Path(override) if override else DEFAULT_DEPLOYMENT_MANIFEST


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DeploymentManifestError("deployment_manifest_unreadable") from error
    if not isinstance(value, dict):
        raise DeploymentManifestError("deployment_manifest_not_an_object")
    return value


def sha256_file(path: str | Path) -> str:
    """Return a prefixed SHA-256 digest for a regular file."""
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def _required_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise DeploymentManifestError(f"deployment_manifest_{key}_missing")
    return value


def _required_text(payload: Mapping[str, Any], key: str, reason: str) -> str:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        raise DeploymentManifestError(reason)
    return value


def _validate_evidence(evidence: Mapping[str, Any]) -> str:
    run_id = _required_text(evidence, "run_id", "deployment_evidence_run_id_missing")
    report_path = Path(
        _required_text(evidence, "report_path", "deployment_evidence_report_missing")
    )
    expected_digest = _required_text(
        evidence, "report_sha256", "deployment_evidence_digest_missing"
    )
    if not report_path.is_file():
        raise DeploymentManifestError("deployment_evidence_report_unavailable")
    if sha256_file(report_path) != expected_digest:
        raise DeploymentManifestError("deployment_evidence_report_changed")
    report = _read_json_object(report_path)
    if (
        run_id != EXPECTED_EVIDENCE_RUN_ID
        or report.get("status") != "PASS"
        or report.get("qualification_passed") is not True
        or report.get("selected_profile") != EXPECTED_PROFILE
        or report.get("decision") != "ADVANCE_TO_CANARY"
        or report.get("canary_allowed") is not True
        or str(report.get("qualification_id", "")) != run_id
    ):
        raise DeploymentManifestError("deployment_evidence_not_qualified")
    return run_id


def _validate_benchmark(
    benchmark: Mapping[str, Any],
    *,
    runtime_root: Path,
) -> str:
    report_path = Path(
        _required_text(
            benchmark,
            "report_path",
            "deployment_benchmark_report_missing",
        )
    )
    expected_digest = _required_text(
        benchmark,
        "report_sha256",
        "deployment_benchmark_digest_missing",
    )
    if not report_path.is_file():
        raise DeploymentManifestError("deployment_benchmark_report_unavailable")
    if sha256_file(report_path) != expected_digest:
        raise DeploymentManifestError("deployment_benchmark_report_changed")
    report = _read_json_object(report_path)
    gate_fields = (
        "status",
        "runtime_root",
        "effective_profile",
        "fallback_applied",
        "warm_p95_ms",
        "runtime_init_count",
        "memory_safe",
    )
    if any(report.get(key) != benchmark.get(key) for key in gate_fields):
        raise DeploymentManifestError("deployment_benchmark_manifest_mismatch")
    try:
        benchmark_runtime_root = Path(str(benchmark.get("runtime_root", ""))).resolve()
    except (OSError, RuntimeError) as error:
        raise DeploymentManifestError("deployment_benchmark_runtime_invalid") from error
    if benchmark_runtime_root != runtime_root.resolve():
        raise DeploymentManifestError("deployment_benchmark_runtime_mismatch")

    status = str(benchmark.get("status", "") or "").strip().upper()
    if status != "PASS":
        raise DeploymentManifestError("deployment_benchmark_not_passed")
    try:
        warm_p95_ms = float(benchmark.get("warm_p95_ms"))
        init_count = int(benchmark.get("runtime_init_count"))
    except (TypeError, ValueError) as error:
        raise DeploymentManifestError("deployment_benchmark_metrics_invalid") from error
    if warm_p95_ms > MAX_WARM_P95_MS:
        raise DeploymentManifestError("deployment_benchmark_latency_blocked")
    if init_count != 1:
        raise DeploymentManifestError("deployment_benchmark_runtime_reuse_blocked")
    if benchmark.get("effective_profile") != EXPECTED_PROFILE:
        raise DeploymentManifestError("deployment_benchmark_profile_mismatch")
    if benchmark.get("fallback_applied") is not False:
        raise DeploymentManifestError("deployment_benchmark_degraded")
    if benchmark.get("memory_safe") is not True:
        raise DeploymentManifestError("deployment_benchmark_memory_blocked")
    return status


def load_workspace_chat_rag_v2_deployment(
    path: Optional[str | Path] = None,
    *,
    env: Optional[Mapping[str, str]] = None,
    require_activated: bool = False,
) -> Optional[WorkspaceChatRagV2Deployment]:
    """Load and validate a local deployment manifest.

    Missing manifests return ``None``. Activated manifests are always validated
    strictly; corrupt activation never silently enables retrieval.
    """
    manifest_path = _manifest_path(path, env)
    if not manifest_path.is_file():
        return None
    payload = _read_json_object(manifest_path)
    if payload.get("schema_version") != DEPLOYMENT_SCHEMA_VERSION:
        raise DeploymentManifestError("deployment_manifest_schema_unsupported")

    state = str(payload.get("activation_state", "") or "").strip().casefold()
    if state not in {STAGED_STATE, ACTIVATED_STATE, ROLLED_BACK_STATE}:
        raise DeploymentManifestError("deployment_manifest_state_invalid")
    if state != ACTIVATED_STATE and require_activated:
        return None

    profile = str(payload.get("requested_profile", "") or "").strip()
    runtime = _required_mapping(payload, "runtime")
    model = _required_mapping(payload, "model")
    policy = _required_mapping(payload, "policy")
    evidence = _required_mapping(payload, "evidence")
    benchmark = _required_mapping(payload, "benchmark")

    deployment = WorkspaceChatRagV2Deployment(
        manifest_path=manifest_path,
        activation_state=state,
        requested_profile=profile,
        runtime_root=Path(_required_text(runtime, "root", "deployment_runtime_root_missing")),
        model_path=Path(_required_text(model, "path", "deployment_model_path_missing")),
        model_revision=_required_text(model, "revision", "deployment_model_revision_missing"),
        model_checksum=_required_text(model, "checksum", "deployment_model_checksum_missing"),
        retrieval_device=str(model.get("device", "cpu") or "cpu").strip(),
        fail_closed=bool(policy.get("fail_closed", False)),
        evidence_run_id=str(evidence.get("run_id", "") or "").strip(),
        benchmark_status=str(benchmark.get("status", "") or "").strip().upper(),
    )

    if state != ACTIVATED_STATE:
        if require_activated:
            return None
        return deployment
    if profile != EXPECTED_PROFILE:
        raise DeploymentManifestError("deployment_profile_not_approved")
    if not deployment.runtime_root.is_absolute():
        raise DeploymentManifestError("deployment_runtime_root_not_absolute")
    if not deployment.model_path.is_absolute() or not deployment.model_path.is_dir():
        raise DeploymentManifestError("deployment_model_unavailable")
    if deployment.model_revision != EXPECTED_MODEL_REVISION:
        raise DeploymentManifestError("deployment_model_revision_not_approved")
    if deployment.model_checksum.casefold() != EXPECTED_MODEL_CHECKSUM.casefold():
        raise DeploymentManifestError("deployment_model_checksum_not_approved")
    if deployment.retrieval_device.casefold() != "cpu":
        raise DeploymentManifestError("deployment_device_not_approved")
    if (
        not deployment.fail_closed
        or policy.get("lexical_fallback_enabled") is not False
        or policy.get("semantic_progressive") is not False
    ):
        raise DeploymentManifestError("deployment_bge_only_policy_required")

    run_id = _validate_evidence(evidence)
    status = _validate_benchmark(benchmark, runtime_root=deployment.runtime_root)
    return WorkspaceChatRagV2Deployment(
        **{
            **deployment.__dict__,
            "evidence_run_id": run_id,
            "benchmark_status": status,
        }
    )


def production_candidate_identity(
    deployment: WorkspaceChatRagV2Deployment,
) -> dict[str, Any]:
    """Return a read-only, path-redacted identity for evaluation manifests."""
    if not deployment.activated:
        raise DeploymentManifestError("deployment_identity_requires_activated_manifest")
    identity = {
        "schema_version": DEPLOYMENT_SCHEMA_VERSION,
        "activation_state": deployment.activation_state,
        "requested_profile": deployment.requested_profile,
        "model_revision": deployment.model_revision,
        "model_checksum": deployment.model_checksum,
        "retrieval_device": deployment.retrieval_device,
        "retrieval_mode": "bge_m3_hybrid_only",
        "fail_closed": deployment.fail_closed,
        "evidence_run_id": deployment.evidence_run_id,
        "benchmark_status": deployment.benchmark_status,
        "manifest_sha256": sha256_file(deployment.manifest_path),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        **identity,
        "identity_sha256": f"sha256:{hashlib.sha256(encoded).hexdigest()}",
    }
