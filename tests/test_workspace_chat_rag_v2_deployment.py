"""Deployment manifest behavior for normal and explicitly unsealed diagnostics."""
from __future__ import annotations

import json

import pytest

from aios_habit.workspace_chat_rag_v2_deployment import (
    ACTIVATED_STATE,
    DEPLOYMENT_SCHEMA_VERSION,
    EXPECTED_MODEL_CHECKSUM,
    EXPECTED_MODEL_REVISION,
    EXPECTED_PROFILE,
    DeploymentManifestError,
    load_workspace_chat_rag_v2_deployment,
)


def _manifest(runtime_root, model_path):
    return {
        "schema_version": DEPLOYMENT_SCHEMA_VERSION,
        "activation_state": ACTIVATED_STATE,
        "requested_profile": EXPECTED_PROFILE,
        "runtime": {"root": str(runtime_root)},
        "model": {
            "path": str(model_path),
            "revision": EXPECTED_MODEL_REVISION,
            "checksum": EXPECTED_MODEL_CHECKSUM,
            "device": "cpu",
        },
        "policy": {
            "fail_closed": True,
            "lexical_fallback_enabled": False,
            "semantic_progressive": False,
        },
        "evidence": {
            "run_id": "missing-sealed-evidence",
            "report_path": str(runtime_root / "missing-evidence.json"),
            "report_sha256": "sha256:" + "0" * 64,
        },
        "benchmark": {
            "status": "NOT_RUN",
            "report_path": str(runtime_root / "missing-benchmark.json"),
            "report_sha256": "sha256:" + "0" * 64,
        },
    }


def test_explicit_unsealed_diagnostic_bypasses_only_historical_artifact_checks(tmp_path):
    runtime_root = tmp_path / "runtime"
    model_path = tmp_path / "model"
    runtime_root.mkdir()
    model_path.mkdir()
    manifest_path = tmp_path / "deployment.json"
    manifest_path.write_text(json.dumps(_manifest(runtime_root, model_path)), encoding="utf-8")

    with pytest.raises(DeploymentManifestError, match="deployment_evidence_report_unavailable"):
        load_workspace_chat_rag_v2_deployment(manifest_path, require_activated=True)

    deployment = load_workspace_chat_rag_v2_deployment(
        manifest_path,
        require_activated=True,
        allow_unsealed_diagnostic=True,
    )

    assert deployment is not None
    assert deployment.requested_profile == EXPECTED_PROFILE
    assert deployment.fail_closed is True
    assert deployment.benchmark_status == "UNSEALED_DIAGNOSTIC"
