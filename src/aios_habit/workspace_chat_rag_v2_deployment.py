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
SUPPORTED_SCHEMA_VERSIONS = (2, 3)
ACTIVATED_STATE = "activated"
STAGED_STATE = "staged"
ROLLED_BACK_STATE = "rolled_back"
EXPECTED_PROFILE = "bge_m3_hybrid"
# Evidence is an immutable result of a selected-profile qualification, not a
# calendar-bound constant.  The concrete run id and corpus fingerprint are
# carried by the activated manifest and must match the sealed report exactly.
SELECTED_EVIDENCE_RUN_PREFIX = "SELECTED-bge_m3_hybrid-"
EXPECTED_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
EXPECTED_MODEL_CHECKSUM = (
    "sha256:f8faedab99c4c901e5c2f311ea3f32786b3395b5cbb0c10a60c2b83970d64405"
)
EXPECTED_RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
EXPECTED_RERANKER_CHECKSUM = (
    "sha256:66ee82666f78ee4c16efa73de43586a00b1338bf9d96cb5cf891b7b705c873c7"
)
DEFAULT_POLICY_VERSION = "adaptive-reranking-v1"

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
    adaptive_enabled: bool = False
    reranker_path: Optional[Path] = None
    reranker_revision: str = ""
    reranker_checksum: str = ""
    policy_version: str = DEFAULT_POLICY_VERSION
    deep_timeout_ms: int = 300000
    deep_rerank_limit: int = 10

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
    corpus_fingerprint = _required_text(
        evidence,
        "corpus_fingerprint",
        "deployment_evidence_corpus_fingerprint_missing",
    )
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
        not run_id.startswith(SELECTED_EVIDENCE_RUN_PREFIX)
        or report.get("status") != "PASS"
        or report.get("qualification_passed") is not True
        or report.get("selected_profile") != EXPECTED_PROFILE
        or report.get("decision") != "ADVANCE_TO_CANARY"
        or report.get("canary_allowed") is not True
        or str(report.get("qualification_id", "")) != run_id
        or str(report.get("corpus_fingerprint", "")) != corpus_fingerprint
    ):
        raise DeploymentManifestError("deployment_evidence_not_qualified")
    return run_id


def _validate_benchmark(
    benchmark: Mapping[str, Any],
    *,
    runtime_root: Path,
    adaptive_enabled: bool = False,
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

    status = str(benchmark.get("status", "") or "").strip().upper()
    if status != "PASS":
        raise DeploymentManifestError("deployment_benchmark_not_passed")

    if report.get("synthetic") or report.get("mock") or report.get("blocked") or report.get("overall_status") == "BLOCKED":
        raise DeploymentManifestError("deployment_benchmark_blocked_or_synthetic")

    if adaptive_enabled:
        if report.get("policy_version") != DEFAULT_POLICY_VERSION:
            raise DeploymentManifestError("deployment_adaptive_policy_mismatch")
        gates = report.get("gates")
        if not isinstance(gates, Mapping):
            raise DeploymentManifestError("deployment_adaptive_gates_missing")
        required_gates = (
            "route_accuracy",
            "explicit_deep_rate",
            "uncertain_to_deep_rate",
            "hard_mrr_gain",
            "recall_regression",
            "auto_fast_p95_regression",
            "deep_warm_p95",
            "available_ram_mb",
            "runtime_init_count",
            "zero_privacy_leakage",
            "degraded_fallback_safe",
            "legacy_compatibility",
            "rollback_verified",
        )
        for g in required_gates:
            g_data = gates.get(g)
            if not isinstance(g_data, Mapping) or g_data.get("status") != "PASS":
                raise DeploymentManifestError(f"deployment_adaptive_gate_failed_{g}")
    else:
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
    allow_unsealed_diagnostic: bool = False,
) -> Optional[WorkspaceChatRagV2Deployment]:
    """Load and validate a local deployment manifest.

    Missing manifests return ``None``. Activated manifests are always validated
    strictly; corrupt activation never silently enables retrieval. The explicit
    diagnostic escape hatch is for the benchmark CLI only: it retains approved
    model/profile/fail-closed validation but does not require historical report
    files that are unavailable on the current machine.
    """
    manifest_path = _manifest_path(path, env)
    if not manifest_path.is_file():
        return None
    payload = _read_json_object(manifest_path)
    schema_ver = payload.get("schema_version")
    if schema_ver not in SUPPORTED_SCHEMA_VERSIONS:
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

    # Parse optional reranker & adaptive configuration (schema v3)
    adaptive_payload = payload.get("adaptive")
    reranker_payload = payload.get("reranker")
    adaptive_enabled = False
    reranker_path: Optional[Path] = None
    reranker_revision = ""
    reranker_checksum = ""
    policy_version = DEFAULT_POLICY_VERSION
    deep_timeout_ms = 300000
    deep_rerank_limit = 10

    if isinstance(reranker_payload, Mapping):
        reranker_raw_path = str(reranker_payload.get("path", "") or "").strip()
        if reranker_raw_path:
            reranker_path = Path(reranker_raw_path)
        reranker_revision = str(reranker_payload.get("revision", "") or "").strip()
        reranker_checksum = str(reranker_payload.get("checksum", "") or "").strip()

    if isinstance(adaptive_payload, Mapping):
        adaptive_enabled = bool(adaptive_payload.get("enabled", False))
        policy_version = str(adaptive_payload.get("policy_version", DEFAULT_POLICY_VERSION) or DEFAULT_POLICY_VERSION).strip()
        deep_timeout_ms = int(adaptive_payload.get("deep_timeout_ms", 300000))
        deep_rerank_limit = int(adaptive_payload.get("deep_rerank_limit", 10))

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
        adaptive_enabled=adaptive_enabled,
        reranker_path=reranker_path,
        reranker_revision=reranker_revision,
        reranker_checksum=reranker_checksum,
        policy_version=policy_version,
        deep_timeout_ms=deep_timeout_ms,
        deep_rerank_limit=deep_rerank_limit,
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

    if deployment.adaptive_enabled:
        if deployment.reranker_path is None or not deployment.reranker_path.is_absolute() or not deployment.reranker_path.is_dir():
            raise DeploymentManifestError("deployment_reranker_model_unavailable")
        if deployment.reranker_revision != EXPECTED_RERANKER_REVISION:
            raise DeploymentManifestError("deployment_reranker_revision_not_approved")
        if deployment.reranker_checksum.casefold() != EXPECTED_RERANKER_CHECKSUM.casefold():
            raise DeploymentManifestError("deployment_reranker_checksum_not_approved")
        if deployment.policy_version != DEFAULT_POLICY_VERSION:
            raise DeploymentManifestError("deployment_adaptive_policy_not_approved")
        if not (15000 <= deployment.deep_timeout_ms <= 300000):
            raise DeploymentManifestError("deployment_adaptive_timeout_out_of_bounds")
        if not (1 <= deployment.deep_rerank_limit <= 15):
            raise DeploymentManifestError("deployment_adaptive_rerank_limit_out_of_bounds")

    if allow_unsealed_diagnostic:
        return WorkspaceChatRagV2Deployment(
            **{
                **deployment.__dict__,
                "benchmark_status": "UNSEALED_DIAGNOSTIC",
            }
        )

    run_id = _validate_evidence(evidence)
    status = _validate_benchmark(
        benchmark,
        runtime_root=deployment.runtime_root,
        adaptive_enabled=deployment.adaptive_enabled,
    )
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
        "retrieval_mode": "bge_m3_hybrid_adaptive" if deployment.adaptive_enabled else "bge_m3_hybrid_only",
        "adaptive_enabled": deployment.adaptive_enabled,
        "reranker_revision": deployment.reranker_revision if deployment.adaptive_enabled else None,
        "reranker_checksum": deployment.reranker_checksum if deployment.adaptive_enabled else None,
        "policy_version": deployment.policy_version if deployment.adaptive_enabled else None,
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



def audit_deployment(
    manifest_path: Optional[str | Path] = None,
    *,
    env: Optional[Mapping[str, str]] = None,
    check_adaptive: bool = False,
) -> dict[str, Any]:
    """Audit the machine-local deployment manifest and artifact integrity."""
    path = _manifest_path(manifest_path, env)
    report: dict[str, Any] = {
        "manifest_path": str(path),
        "manifest_exists": path.is_file(),
        "status": "PASS",
        "checks": {},
        "warnings": [],
        "errors": [],
    }
    if not path.is_file():
        report["status"] = "FAIL"
        report["errors"].append("manifest_file_not_found")
        return report

    try:
        payload = _read_json_object(path)
        version = payload.get("schema_version", 2)
        report["schema_version"] = version
        state = payload.get("activation_state", "unknown")
        report["activation_state"] = state

        deployment = load_workspace_chat_rag_v2_deployment(
            path,
            env=env,
            require_activated=False,
            allow_unsealed_diagnostic=True,
        )
        if deployment is None:
            report["status"] = "FAIL"
            report["errors"].append("deployment_load_failed")
            return report

        report["checks"]["model_path_exists"] = deployment.model_path.is_dir()
        report["checks"]["profile_match"] = deployment.requested_profile == EXPECTED_PROFILE
        report["checks"]["model_revision_match"] = deployment.model_revision == EXPECTED_MODEL_REVISION
        report["checks"]["fail_closed"] = deployment.fail_closed
        report["checks"]["adaptive_enabled"] = deployment.adaptive_enabled

        if check_adaptive:
            report["checks"]["reranker_configured"] = bool(
                deployment.reranker_path and deployment.reranker_path.is_dir()
            )
            report["checks"]["reranker_revision_match"] = bool(
                deployment.reranker_revision == EXPECTED_RERANKER_REVISION
            )
            if deployment.adaptive_enabled and not report["checks"]["reranker_configured"]:
                report["status"] = "FAIL"
                report["errors"].append("reranker_model_missing_for_adaptive_mode")

        if state != ACTIVATED_STATE:
            report["warnings"].append(f"deployment_not_activated (current: {state})")

        if not report["checks"]["model_path_exists"]:
            report["status"] = "FAIL"
            report["errors"].append("base_model_path_missing")

    except Exception as exc:
        report["status"] = "FAIL"
        report["errors"].append(str(exc))

    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point for Workspace Chat RAG v2 deployment audit."""
    import argparse
    parser = argparse.ArgumentParser(description="Audit Workspace Chat RAG v2 Deployment")
    parser.add_argument("--manifest", type=str, default=None, help="Path to deployment manifest")
    parser.add_argument("--check-adaptive", action="store_true", help="Audit adaptive reranker artifacts")
    parser.add_argument("--json", action="store_true", help="Output audit report as JSON")
    args = parser.parse_args(argv)

    report = audit_deployment(args.manifest, check_adaptive=args.check_adaptive)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=== Workspace Chat RAG v2 Deployment Audit ===")
        print(f"Manifest: {report['manifest_path']}")
        print(f"Status: {report['status']}")
        print(f"Activation State: {report.get('activation_state', 'unknown')}")
        print("--- Checks ---")
        for check, passed in report.get("checks", {}).items():
            symbol = "✓" if passed else "✗"
            print(f"  [{symbol}] {check}: {passed}")
        if report.get("warnings"):
            print("--- Warnings ---")
            for w in report["warnings"]:
                print(f"  ! {w}")
        if report.get("errors"):
            print("--- Errors ---")
            for e in report["errors"]:
                print(f"  ✗ {e}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
