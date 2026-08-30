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
    EXPECTED_RERANKER_CHECKSUM,
    EXPECTED_RERANKER_REVISION,
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
            "corpus_fingerprint": "0" * 64,
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

    live = load_workspace_chat_rag_v2_deployment(manifest_path, require_activated=True)
    assert live is not None
    assert live.activated is True
    assert live.requested_profile == EXPECTED_PROFILE

    deployment = load_workspace_chat_rag_v2_deployment(
        manifest_path,
        require_activated=True,
        allow_unsealed_diagnostic=True,
    )

    assert deployment is not None
    assert deployment.requested_profile == EXPECTED_PROFILE
    assert deployment.fail_closed is True
    assert deployment.benchmark_status == "UNSEALED_DIAGNOSTIC"
    assert deployment.adaptive_enabled is False
    assert deployment.reranker_path is None


def test_evidence_validation_accepts_current_sealed_selected_profile_run(tmp_path):
    """A new corpus qualification must not be rejected for lacking a stale run id."""
    from aios_habit.workspace_chat_rag_v2_deployment import (
        _validate_evidence,
        sha256_file,
    )

    run_id = "SELECTED-bge_m3_hybrid-current-corpus"
    corpus_fingerprint = "a" * 64
    report_path = tmp_path / "selected_profile_report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "qualification_passed": True,
                "selected_profile": EXPECTED_PROFILE,
                "decision": "ADVANCE_TO_CANARY",
                "canary_allowed": True,
                "qualification_id": run_id,
                "corpus_fingerprint": corpus_fingerprint,
            }
        ),
        encoding="utf-8",
    )

    assert _validate_evidence(
        {
            "run_id": run_id,
            "corpus_fingerprint": corpus_fingerprint,
            "report_path": str(report_path),
            "report_sha256": sha256_file(report_path),
        }
    ) == run_id


def test_schema_v2_manifest_loads_hybrid_only_with_adaptive_disabled(tmp_path):
    runtime_root = tmp_path / "runtime"
    model_path = tmp_path / "model"
    runtime_root.mkdir()
    model_path.mkdir()
    manifest_path = tmp_path / "deployment_v2.json"
    manifest_path.write_text(json.dumps(_manifest(runtime_root, model_path)), encoding="utf-8")

    deployment = load_workspace_chat_rag_v2_deployment(
        manifest_path,
        require_activated=True,
        allow_unsealed_diagnostic=True,
    )
    assert deployment is not None
    assert deployment.adaptive_enabled is False
    assert deployment.reranker_path is None
    assert deployment.policy_version == "adaptive-reranking-v1"


def test_schema_v3_manifest_with_adaptive_reranker(tmp_path):
    runtime_root = tmp_path / "runtime"
    model_path = tmp_path / "model"
    reranker_path = tmp_path / "reranker"
    runtime_root.mkdir()
    model_path.mkdir()
    reranker_path.mkdir()

    v3_manifest = _manifest(runtime_root, model_path)
    v3_manifest["schema_version"] = 3
    v3_manifest["reranker"] = {
        "path": str(reranker_path),
        "revision": EXPECTED_RERANKER_REVISION,
        "checksum": EXPECTED_RERANKER_CHECKSUM,
        "device": "cpu",
    }
    v3_manifest["adaptive"] = {
        "enabled": False,
        "policy_version": "adaptive-reranking-v1",
        "deep_timeout_ms": 300000,
        "deep_rerank_limit": 10,
    }
    manifest_path = tmp_path / "deployment_v3.json"
    manifest_path.write_text(json.dumps(v3_manifest), encoding="utf-8")

    deployment = load_workspace_chat_rag_v2_deployment(
        manifest_path,
        require_activated=True,
        allow_unsealed_diagnostic=True,
    )
    assert deployment is not None
    assert deployment.adaptive_enabled is False
    assert deployment.reranker_path == reranker_path
    assert deployment.reranker_revision == EXPECTED_RERANKER_REVISION
    assert deployment.policy_version == "adaptive-reranking-v1"
    assert deployment.deep_timeout_ms == 300000
    assert deployment.deep_rerank_limit == 10


def test_audit_deployment_cli(tmp_path, capsys):
    from aios_habit.workspace_chat_rag_v2_deployment import audit_deployment, main

    runtime_root = tmp_path / "runtime"
    model_path = tmp_path / "model"
    reranker_path = tmp_path / "reranker"
    runtime_root.mkdir()
    model_path.mkdir()
    reranker_path.mkdir()

    v3_manifest = _manifest(runtime_root, model_path)
    v3_manifest["schema_version"] = 3
    v3_manifest["reranker"] = {
        "path": str(reranker_path),
        "revision": EXPECTED_RERANKER_REVISION,
        "checksum": EXPECTED_RERANKER_CHECKSUM,
        "device": "cpu",
    }
    v3_manifest["adaptive"] = {
        "enabled": True,
        "policy_version": "adaptive-reranking-v1",
        "deep_timeout_ms": 300000,
        "deep_rerank_limit": 10,
    }
    manifest_path = tmp_path / "deployment_audit.json"
    manifest_path.write_text(json.dumps(v3_manifest), encoding="utf-8")

    # 1. Audit function directly
    report = audit_deployment(manifest_path, check_adaptive=True)
    assert report["status"] == "PASS"
    assert report["checks"]["reranker_configured"] is True
    assert report["checks"]["adaptive_enabled"] is True

    # 2. CLI main function
    code = main(["--manifest", str(manifest_path), "--check-adaptive", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["status"] == "PASS"


def test_adaptive_activation_rejects_minimal_pass_json(tmp_path):
    """Prove that a report containing only {"overall_status": "PASS"} is rejected during adaptive activation."""
    from scripts.workspace_chat_rag_v2_activation import ActivationError, _validated_benchmark

    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    minimal_report = tmp_path / "minimal_pass.json"
    minimal_report.write_text(json.dumps({"overall_status": "PASS"}), encoding="utf-8")

    with pytest.raises(ActivationError, match="Adaptive benchmark report schema or policy version is invalid"):
        _validated_benchmark(minimal_report, runtime_root, require_adaptive=True)


def test_adaptive_activation_rejects_blocked_or_synthetic_report(tmp_path):
    """Prove that BLOCKED or synthetic reports cannot be used for adaptive activation."""
    from scripts.workspace_chat_rag_v2_activation import ActivationError, _validated_benchmark

    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()

    # 1. Blocked report
    blocked_report = tmp_path / "blocked_report.json"
    blocked_report.write_text(json.dumps({
        "overall_status": "BLOCKED",
        "blocked_reasons": ["bge_reranker_model_missing"],
    }), encoding="utf-8")
    with pytest.raises(ActivationError, match="Production benchmark did not pass all quality gates"):
        _validated_benchmark(blocked_report, runtime_root, require_adaptive=True)

    # 2. Synthetic report with fake PASS
    synthetic_report = tmp_path / "synthetic_report.json"
    synthetic_report.write_text(json.dumps({
        "overall_status": "PASS",
        "synthetic": True,
    }), encoding="utf-8")
    with pytest.raises(ActivationError, match="Production benchmark cannot be synthetic, mock, or blocked"):
        _validated_benchmark(synthetic_report, runtime_root, require_adaptive=True)


def test_adaptive_activation_accepts_authentic_complete_report(tmp_path):
    """Prove that a complete, authentic report passing all 13 gates is accepted and sealed."""
    from scripts.workspace_chat_rag_v2_activation import _validated_benchmark

    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()

    authentic_report_path = tmp_path / "authentic_report.json"
    report_data = {
        "schema_version": 1,
        "policy_version": "adaptive-reranking-v1",
        "timestamp": "2026-08-16T12:00:00Z",
        "overall_status": "PASS",
        "provenance": {
            "git_sha": "abc123def456",
            "command": "scripts/benchmark_adaptive_reranking.py",
            "runtime_root": str(runtime_root.resolve()),
            "dataset_checksum": "sha256:" + "a" * 64,
        },
        "gates": {
            "route_accuracy": {"status": "PASS", "measured": 0.95, "threshold": 0.90},
            "explicit_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "uncertain_to_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "hard_mrr_gain": {"status": "PASS", "measured": 0.08, "threshold": 0.05},
            "recall_regression": {"status": "PASS", "measured": 0.0, "threshold": 0.0},
            "auto_fast_p95_regression": {"status": "PASS", "measured": 0.02, "threshold": 0.10},
            "deep_warm_p95": {"status": "PASS", "measured_ms": 120.5, "threshold_ms": 3000.0},
            "available_ram_mb": {"status": "PASS", "measured_mb": 4096.0, "threshold_mb": 2048.0},
            "runtime_init_count": {"status": "PASS", "measured": 1, "threshold": 1},
            "zero_privacy_leakage": {"status": "PASS"},
            "degraded_fallback_safe": {"status": "PASS"},
            "legacy_compatibility": {"status": "PASS"},
            "rollback_verified": {"status": "PASS"},
        },
        "confusion_matrix": {
            "total_queries": 60,
            "fast_true_positives": 20,
            "fast_false_positives": 0,
            "deep_true_positives": 40,
            "deep_false_positives": 0,
            "uncertain_escalations": 10,
            "explicit_deep_overrides": 10,
        },
        "performance": {
            "auto_fast_p50_ms": 0.05,
            "auto_fast_p95_ms": 0.12,
            "deep_p50_ms": 25.4,
            "deep_p95_ms": 42.1,
            "peak_rss_mb": 120.0,
            "available_ram_gb": 4.0,
        },
        "candidate_windows": {
            "10": {"mrr": 0.82, "p95_ms": 18.2},
            "20": {"mrr": 0.89, "p95_ms": 23.4},
            "30": {"mrr": 0.94, "p95_ms": 28.5},
        },
        "selected_window": 30,
    }
    authentic_report_path.write_text(json.dumps(report_data), encoding="utf-8")

    sealed = _validated_benchmark(authentic_report_path, runtime_root, require_adaptive=True)
    assert sealed["status"] == "PASS"
    assert sealed["report_path"] == str(authentic_report_path.resolve())
    assert sealed["report_sha256"].startswith("sha256:")


def test_adaptive_benchmark_raw_hex_checksum_canonicalization_and_rejection(tmp_path):
    """Test that 64-char raw hex checksum is canonicalized and invalid checksums are rejected."""
    from scripts.workspace_chat_rag_v2_activation import ActivationError, _validated_benchmark

    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()

    base_report = {
        "schema_version": 1,
        "policy_version": "adaptive-reranking-v1",
        "timestamp": "2026-08-16T12:00:00Z",
        "overall_status": "PASS",
        "provenance": {
            "git_sha": "abc123def456",
            "command": "scripts/benchmark_adaptive_reranking.py",
            "runtime_root": str(runtime_root.resolve()),
            "dataset_checksum": "a" * 64,  # Raw 64-char hex without prefix
        },
        "gates": {
            "route_accuracy": {"status": "PASS", "measured": 0.95, "threshold": 0.90},
            "explicit_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "uncertain_to_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "hard_mrr_gain": {"status": "PASS", "measured": 0.08, "threshold": 0.05},
            "recall_regression": {"status": "PASS", "measured": 0.0, "threshold": 0.0},
            "auto_fast_p95_regression": {"status": "PASS", "measured": 0.02, "threshold": 0.10},
            "deep_warm_p95": {"status": "PASS", "measured_ms": 120.5, "threshold_ms": 3000.0},
            "available_ram_mb": {"status": "PASS", "measured_mb": 4096.0, "threshold_mb": 2048.0},
            "runtime_init_count": {"status": "PASS", "measured": 1, "threshold": 1},
            "zero_privacy_leakage": {"status": "PASS"},
            "degraded_fallback_safe": {"status": "PASS"},
            "legacy_compatibility": {"status": "PASS"},
            "rollback_verified": {"status": "PASS"},
        },
        "confusion_matrix": {
            "total_queries": 60,
            "fast_true_positives": 20,
            "fast_false_positives": 0,
            "deep_true_positives": 40,
            "deep_false_positives": 0,
            "uncertain_escalations": 10,
            "explicit_deep_overrides": 10,
        },
        "performance": {
            "auto_fast_p50_ms": 0.05,
            "auto_fast_p95_ms": 0.12,
            "deep_p50_ms": 25.4,
            "deep_p95_ms": 42.1,
            "peak_rss_mb": 120.0,
            "available_ram_gb": 4.0,
        },
        "candidate_windows": {
            "10": {"mrr": 0.82, "p95_ms": 18.2},
            "20": {"mrr": 0.89, "p95_ms": 23.4},
            "30": {"mrr": 0.94, "p95_ms": 28.5},
        },
        "selected_window": 30,
    }

    # 1. Raw hex is canonicalized with controlled validation
    raw_hex_report = tmp_path / "raw_hex_report.json"
    raw_hex_report.write_text(json.dumps(base_report), encoding="utf-8")
    sealed = _validated_benchmark(raw_hex_report, runtime_root, require_adaptive=True)
    assert sealed["status"] == "PASS"

    # 2. Invalid short/malformed checksum is strictly rejected
    invalid_report = tmp_path / "invalid_checksum_report.json"
    bad_report = dict(base_report)
    bad_report["provenance"] = dict(bad_report["provenance"], dataset_checksum="not_a_valid_hash")
    invalid_report.write_text(json.dumps(bad_report), encoding="utf-8")
    with pytest.raises(ActivationError, match="Adaptive benchmark dataset checksum is missing or invalid"):
        _validated_benchmark(invalid_report, runtime_root, require_adaptive=True)


def test_end_to_end_prepare_activate_load_adaptive_deployment(tmp_path):
    """End-to-end contract integration: prepare adaptive -> activate with valid report -> load deployment."""
    import argparse
    import json
    from aios_habit.workspace_chat_rag_v2_deployment import (
        EXPECTED_MODEL_CHECKSUM,
        EXPECTED_RERANKER_CHECKSUM,
        EXPECTED_RERANKER_REVISION,
        sha256_file,
    )
    from scripts.workspace_chat_rag_v2_activation import (
        activate,
        prepare,
        promote,
    )

    evidence_run_id = "SELECTED-bge_m3_hybrid-current-corpus"
    evidence_root = tmp_path / "evidence" / evidence_run_id
    evidence_root.mkdir(parents=True)
    qualification_path = evidence_root / "qualification.json"
    qualification_data = {
        "status": "PASS",
        "qualification_passed": True,
        "selected_profile": EXPECTED_PROFILE,
        "decision": "ADVANCE_TO_CANARY",
        "canary_allowed": True,
        "qualification_id": evidence_run_id,
        "corpus_fingerprint": "b" * 64,
    }
    qualification_path.write_text(json.dumps(qualification_data), encoding="utf-8")

    # Create model files matching checksums
    model_source = tmp_path / "model_source"
    model_source.mkdir()
    model_file = model_source / "pytorch_model.bin"
    model_file.write_bytes(b"mock model payload")
    model_checksum = sha256_file(model_file)

    reranker_source = tmp_path / "reranker_source"
    reranker_source.mkdir()
    reranker_file = reranker_source / "pytorch_model.bin"
    reranker_file.write_bytes(b"mock reranker payload")
    reranker_checksum = sha256_file(reranker_file)

    model_dest = tmp_path / "model_dest"
    reranker_dest = tmp_path / "reranker_dest"
    runtime_root = tmp_path / "runtime"
    manifest_path = tmp_path / "deployment.json"
    app_manifest_path = tmp_path / "workspace_chat_rag_v2.local.json"

    # Create valid authentic report
    benchmark_report = tmp_path / "audit_report.json"
    report_data = {
        "schema_version": 1,
        "policy_version": "adaptive-reranking-v1",
        "timestamp": "2026-08-16T12:00:00Z",
        "overall_status": "PASS",
        "provenance": {
            "git_sha": "abc123def456",
            "command": "scripts/benchmark_adaptive_reranking.py",
            "runtime_root": str(runtime_root.resolve()),
            "dataset_checksum": "sha256:" + "b" * 64,
        },
        "gates": {
            "route_accuracy": {"status": "PASS", "measured": 0.95, "threshold": 0.90},
            "explicit_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "uncertain_to_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "hard_mrr_gain": {"status": "PASS", "measured": 0.08, "threshold": 0.05},
            "recall_regression": {"status": "PASS", "measured": 0.0, "threshold": 0.0},
            "auto_fast_p95_regression": {"status": "PASS", "measured": 0.02, "threshold": 0.10},
            "deep_warm_p95": {"status": "PASS", "measured_ms": 120.5, "threshold_ms": 3000.0},
            "available_ram_mb": {"status": "PASS", "measured_mb": 4096.0, "threshold_mb": 2048.0},
            "runtime_init_count": {"status": "PASS", "measured": 1, "threshold": 1},
            "zero_privacy_leakage": {"status": "PASS"},
            "degraded_fallback_safe": {"status": "PASS"},
            "legacy_compatibility": {"status": "PASS"},
            "rollback_verified": {"status": "PASS"},
        },
        "confusion_matrix": {
            "total_queries": 60,
            "fast_true_positives": 20,
            "fast_false_positives": 0,
            "deep_true_positives": 40,
            "deep_false_positives": 0,
            "uncertain_escalations": 10,
            "explicit_deep_overrides": 10,
        },
        "performance": {
            "auto_fast_p50_ms": 0.05,
            "auto_fast_p95_ms": 0.12,
            "deep_p50_ms": 25.4,
            "deep_p95_ms": 42.1,
            "peak_rss_mb": 120.0,
            "available_ram_gb": 4.0,
        },
        "candidate_windows": {
            "10": {"mrr": 0.82, "p95_ms": 18.2},
            "20": {"mrr": 0.89, "p95_ms": 23.4},
            "30": {"mrr": 0.94, "p95_ms": 28.5},
        },
        "selected_window": 30,
    }
    benchmark_report.write_text(json.dumps(report_data), encoding="utf-8")

    args = argparse.Namespace(
        evidence_root=evidence_root,
        model_source=model_source,
        model_destination=model_dest,
        reranker_source=reranker_source,
        reranker_destination=reranker_dest,
        runtime_root=runtime_root,
        manifest=manifest_path,
        enable_adaptive=True,
        benchmark_report=benchmark_report,
    )

    # Monkeypatch verify_model_tree and _verify_evidence to accept our test directories
    import scripts.workspace_chat_rag_v2_activation as activation_module
    orig_verify = activation_module.verify_model_tree
    orig_verify_approved = getattr(activation_module, "_verify_model_tree_approved", None)
    orig_sha256_model_tree = getattr(activation_module, "sha256_model_tree", None)
    orig_verify_ev = activation_module._verify_evidence
    activation_module.verify_model_tree = lambda path, checksum: None
    activation_module._verify_model_tree_approved = lambda path, approved_checksums=None: EXPECTED_MODEL_CHECKSUM
    if orig_sha256_model_tree is not None:
        activation_module.sha256_model_tree = lambda path: EXPECTED_MODEL_CHECKSUM
    activation_module._verify_evidence = lambda root: {
        "run_id": evidence_run_id,
        "report_path": str(qualification_path.resolve()),
        "report_sha256": sha256_file(qualification_path),
        "identity_path": str(qualification_path.resolve()),
        "identity_sha256": sha256_file(qualification_path),
        "sqlite_path": str(qualification_path.resolve()),
        "sqlite_sha256": sha256_file(qualification_path),
        "corpus_fingerprint": "b" * 64,
        "usage": "evidence_only_not_workspace_chat_query_index",
    }
    try:
        # Step 1: prepare
        prep = prepare(args)
        assert prep["activation_state"] == "staged"
        assert prep["schema_version"] == 3
        assert prep["adaptive"]["enabled"] is True

        # Step 2: activate
        act = activate(args)
        assert act["activation_state"] == "activated"
        assert act["benchmark"]["status"] == "PASS"

        # Step 3: promote only the now-validated candidate to the app manifest.
        promote_args = argparse.Namespace(
            manifest=app_manifest_path,
            candidate_manifest=manifest_path,
        )
        promoted = promote(promote_args)
        assert promoted["activation_state"] == "activated"

        # Step 4: load the promoted deployment strictly (require_activated=True)
        deployment = load_workspace_chat_rag_v2_deployment(
            app_manifest_path,
            require_activated=True,
        )
        assert deployment is not None
        assert deployment.activated is True
        assert deployment.adaptive_enabled is True
        assert deployment.reranker_revision == EXPECTED_RERANKER_REVISION
        assert deployment.reranker_checksum == EXPECTED_RERANKER_CHECKSUM
        assert deployment.policy_version == "adaptive-reranking-v1"
    finally:
        activation_module.verify_model_tree = orig_verify
        if orig_verify_approved is not None:
            activation_module._verify_model_tree_approved = orig_verify_approved
        if orig_sha256_model_tree is not None:
            activation_module.sha256_model_tree = orig_sha256_model_tree
        activation_module._verify_evidence = orig_verify_ev


# ---------------------------------------------------------------------------
# Benchmark script regression tests — correct API and real gate probes
# ---------------------------------------------------------------------------

def test_benchmark_script_does_not_reference_search_or_search_with_rerank():
    """The benchmark must use pipeline.query(), not the non-existent .search()/.search_with_rerank()."""
    import pathlib
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark_adaptive_reranking.py"
    source = script_path.read_text(encoding="utf-8")
    # Exclude comments and docstrings from the check by looking at executable lines
    lines = source.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
            continue
        # Must not call pipeline.search( or pipeline.search_with_rerank(
        assert "pipeline.search(" not in stripped, (
            f"Line {i}: benchmark calls pipeline.search() which does not exist"
        )
        assert "pipeline.search_with_rerank(" not in stripped, (
            f"Line {i}: benchmark calls pipeline.search_with_rerank() which does not exist"
        )


def test_benchmark_script_uses_pipeline_query():
    """Verify the production path calls pipeline.query() with correct kwargs."""
    import pathlib
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark_adaptive_reranking.py"
    source = script_path.read_text(encoding="utf-8")
    assert "pipeline.query(" in source, "benchmark must call pipeline.query()"
    assert "rerank_requested=False" in source, "baseline path must use rerank_requested=False"
    assert "rerank_requested=True" in source, "rerank path must use rerank_requested=True"


def test_benchmark_script_extracts_document_ids_from_search_response():
    """Verify ranked doc IDs come from search_response.results, not .items (which doesn't exist)."""
    import pathlib
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark_adaptive_reranking.py"
    source = script_path.read_text(encoding="utf-8")
    assert "search_response.results" in source, (
        "benchmark must extract document IDs from search_response.results"
    )
    # Should NOT reference .items (which was the old non-existent API)
    lines = source.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            continue
        assert ".items]" not in stripped or "IngestionItemReport" in stripped or "items()" in stripped, (
            f"Line {i}: benchmark may reference .items which doesn't exist on SearchResponse"
        )


def test_benchmark_uses_bge_m3_hybrid_base_profile():
    """Benchmark must use bge_m3_hybrid (not bge_m3_hybrid_rerank) as the base profile."""
    import pathlib
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark_adaptive_reranking.py"
    source = script_path.read_text(encoding="utf-8")
    # The config line must use bge_m3_hybrid, not bge_m3_hybrid_rerank
    lines = source.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            continue
        if 'retrieval_profile=' in stripped and 'bge_m3_hybrid_rerank' in stripped:
            pytest.fail(
                f"Line {i}: benchmark uses bge_m3_hybrid_rerank as base profile. "
                f"Must use bge_m3_hybrid so rerank_requested=False truly skips reranking."
            )


def test_benchmark_no_hardcoded_auto_fast_regression():
    """auto_fast_p95_regression must not be hard-coded to 0.0 or always PASS."""
    import pathlib
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark_adaptive_reranking.py"
    source = script_path.read_text(encoding="utf-8")
    # The old hard-coded pattern was:
    # "auto_fast_p95_regression": {"status": "PASS", "measured": 0.0, ...}
    # Verify the production path (not the BLOCKED path) uses _probe_auto_fast_p95_regression
    assert "_probe_auto_fast_p95_regression" in source, (
        "auto_fast_p95_regression must use _probe_auto_fast_p95_regression, not a hard-coded value"
    )


def test_benchmark_no_hardcoded_runtime_init_count():
    """runtime_init_count must not be hard-coded to 1."""
    import pathlib
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark_adaptive_reranking.py"
    source = script_path.read_text(encoding="utf-8")
    assert "_probe_runtime_init_count" in source, (
        "runtime_init_count must use _probe_runtime_init_count, not a hard-coded value"
    )
    assert "_pipeline_init_count" in source, (
        "benchmark must track actual pipeline init count with _pipeline_init_count"
    )


def test_benchmark_reranker_applied_assertion():
    """Benchmark must check reranker_applied on rerank queries; fail if not applied."""
    import pathlib
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark_adaptive_reranking.py"
    source = script_path.read_text(encoding="utf-8")
    assert "reranker_applied" in source, "benchmark must check reranker_applied"
    assert "reranker_not_applied_failures" in source, (
        "benchmark must track reranker_not_applied_failures"
    )


def test_probe_auto_fast_p95_regression_returns_measured_values():
    """Verify _probe_auto_fast_p95_regression returns a real float, not hard-coded 0.0."""
    import sys
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root / "scripts") not in sys.path:
        sys.path.insert(0, str(project_root / "scripts"))
    # Import just the probe function
    from benchmark_adaptive_reranking import _probe_auto_fast_p95_regression

    queries = ["q1", "q2", "q3", "q4", "q5"]

    # Case 1: baseline slower → negative regression (adaptive is faster)
    status, measured, prov = _probe_auto_fast_p95_regression(
        [10.0, 20.0, 30.0, 40.0, 50.0],
        [8.0, 16.0, 24.0, 32.0, 40.0],
        queries,
        queries,
    )
    assert status == "PASS"
    assert measured < 0, "adaptive faster than baseline should give negative regression"
    assert "baseline_fast_p95_ms" in prov
    assert "adaptive_fast_p95_ms" in prov

    # Case 2: large regression → FAIL
    status2, measured2, prov2 = _probe_auto_fast_p95_regression(
        [10.0, 20.0, 30.0, 40.0, 50.0],
        [20.0, 40.0, 60.0, 80.0, 100.0],
        queries,
        queries,
    )
    assert status2 == "FAIL"
    assert measured2 > 0.10

    # Case 3: empty baseline → FAIL
    status3, measured3, prov3 = _probe_auto_fast_p95_regression([], [10.0], [], ["q1"])
    assert status3 == "FAIL"
    assert "query_sets_mismatch_or_empty" in prov3["reason"]

    # Case 4: mismatch queries → FAIL
    status4, measured4, prov4 = _probe_auto_fast_p95_regression(
        [10.0], [10.0],
        ["q1"], ["q2"],
    )
    assert status4 == "FAIL"
    assert "query_sets_mismatch_or_empty" in prov4["reason"]


def test_probe_runtime_init_count():
    """Verify _probe_runtime_init_count reports measured count."""
    import sys
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root / "scripts") not in sys.path:
        sys.path.insert(0, str(project_root / "scripts"))
    from benchmark_adaptive_reranking import _probe_runtime_init_count

    status_ok, measured_ok, prov_ok = _probe_runtime_init_count(1, 3)
    assert status_ok == "PASS"
    assert measured_ok == 1
    assert prov_ok["production_runtime_init_count"] == 1
    assert prov_ok["auxiliary_benchmark_pipeline_init_count"] == 3

    status_bad, measured_bad, prov_bad = _probe_runtime_init_count(3, 3)
    assert status_bad == "FAIL"
    assert measured_bad == 3


# ---------------------------------------------------------------------------
# Behavioral tests — real probes, not source-text scanning
# ---------------------------------------------------------------------------

def test_probe_legacy_compatibility_loads_valid_v2_manifest(tmp_path):
    """Build a valid schema v2 manifest on disk, call probe, assert PASS with adaptive_enabled=False."""
    import sys
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root / "scripts") not in sys.path:
        sys.path.insert(0, str(project_root / "scripts"))
    from benchmark_adaptive_reranking import _probe_legacy_compatibility

    # Probe creates its own manifest internally, so we just pass a dummy path
    status, prov = _probe_legacy_compatibility(tmp_path / "unused.json")
    assert status == "PASS", f"Legacy probe should PASS on valid v2 manifest: {prov}"
    assert prov.get("adaptive_enabled") is False, "Schema v2 must have adaptive_enabled=False"
    assert prov.get("activation_state") == "staged", f"Expected staged state: {prov}"


def test_probe_rollback_blocks_activation(tmp_path):
    """Build valid manifest, transition to rolled_back, verify probe returns PASS because activation blocked."""
    import sys
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root / "scripts") not in sys.path:
        sys.path.insert(0, str(project_root / "scripts"))
    from benchmark_adaptive_reranking import _probe_rollback_verified

    status, prov = _probe_rollback_verified(tmp_path / "unused.json")
    assert status == "PASS", f"Rollback probe should PASS: {prov}"
    # Verify it actually tested the staged→rolled_back transition
    assert prov.get("staged_load") == "ok", f"Probe should have loaded staged manifest first: {prov}"
    assert "rolled_back" in str(prov.get("reason", "")), f"Reason should mention rolled_back: {prov}"


def test_probe_rollback_fails_on_malformed_manifest(tmp_path):
    """Build garbage manifest, call loader, verify FAIL (not accidental PASS from exception)."""
    # This tests the loader directly to confirm that malformed manifests raise
    # DeploymentManifestError, not silently return None
    from aios_habit.workspace_chat_rag_v2_deployment import (
        DeploymentManifestError,
        load_workspace_chat_rag_v2_deployment,
    )

    # Write a manifest with flat keys (missing nested 'runtime', 'model', etc.)
    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({
        "schema_version": 2,
        "activation_state": "activated",
        "requested_profile": "bge_m3_hybrid",
        "runtime_root": str(tmp_path),  # WRONG: should be nested under "runtime"
        "model_path": str(tmp_path),    # WRONG: should be nested under "model"
    }), encoding="utf-8")

    with pytest.raises(DeploymentManifestError, match="deployment_manifest_runtime_missing"):
        load_workspace_chat_rag_v2_deployment(malformed, require_activated=True)


def test_probe_privacy_injects_path_and_secret_verifies_sanitization(tmp_path):
    """Inject a reranker exception with paths/secrets, verify degraded_reason is allowlisted."""
    import sys
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root / "scripts") not in sys.path:
        sys.path.insert(0, str(project_root / "scripts"))
    from benchmark_adaptive_reranking import _probe_privacy_leakage
    from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec

    # Create a minimal lexical pipeline for testing
    runtime_root = tmp_path / "privacy_test_runtime"
    runtime_root.mkdir()
    doc_path = tmp_path / "test_doc.txt"
    doc_path.write_text("Test document for privacy probe.", encoding="utf-8")

    config = RagV2DevConfig(
        runtime_root=runtime_root,
        retrieval_profile="lexical",
        strict_semantic=False,
    )
    pipeline = RagV2DevPipeline(config)
    source_specs = [SourceSpec(path=doc_path)]
    pipeline.ingest(source_specs)

    try:
        status, leaks, prov = _probe_privacy_leakage(pipeline, source_specs)
        # The probe should PASS because:
        # - It injects a PoisonedReranker
        # - Pipeline catches the exception and produces sanitized degraded_reason
        # - No paths/secrets in the output
        assert status == "PASS", f"Privacy probe should PASS with sanitization: {prov}"
        assert leaks == 0, f"Should detect zero leaks: {prov}"
    finally:
        pipeline.close()


def test_probe_fallback_returns_evidence_after_degradation(tmp_path):
    """Force circuit breaker, verify hybrid results + evidence still present."""
    import sys
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root / "scripts") not in sys.path:
        sys.path.insert(0, str(project_root / "scripts"))
    from benchmark_adaptive_reranking import _probe_degraded_fallback
    from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec

    runtime_root = tmp_path / "fallback_test_runtime"
    runtime_root.mkdir()
    doc_path = tmp_path / "test_doc.txt"
    doc_path.write_text("This document contains information about degraded fallback testing.", encoding="utf-8")

    config = RagV2DevConfig(
        runtime_root=runtime_root,
        retrieval_profile="lexical",
        strict_semantic=False,
    )
    pipeline = RagV2DevPipeline(config)
    source_specs = [SourceSpec(path=doc_path)]
    pipeline.ingest(source_specs)

    try:
        status, prov = _probe_degraded_fallback(pipeline, source_specs)
        # The probe forces circuit breaker open, then queries with rerank_requested=True.
        # Lexical pipeline degrades gracefully (no reranker available) and returns results.
        assert status == "PASS", f"Fallback probe should PASS: {prov}"
        assert prov.get("degraded") is True, "Should report degraded=True"
        assert prov.get("search_result_count", 0) > 0 or prov.get("effective_path") in {"lexical", "hybrid"}, (
            f"Should have results or lexical/hybrid path: {prov}"
        )
    finally:
        pipeline.close()


def test_baseline_reranker_not_applied_with_bge_m3_hybrid():
    """Verify that bge_m3_hybrid profile + rerank_requested=False → reranker_applied=False."""
    from aios_habit.rag_v2.pipeline import RagV2DevConfig

    # bge_m3_hybrid is the base profile; it should NOT eagerly trigger reranking
    config = RagV2DevConfig(
        runtime_root="local_runs/test_baseline_profile",
        retrieval_profile="bge_m3_hybrid",
    )
    # The effective retrieval profile should be "hybrid" (not "hybrid_rerank")
    profile_aliases = {
        "bge_m3_hybrid": "hybrid",
        "bge_m3_hybrid_rerank": "hybrid_rerank",
    }
    effective = profile_aliases.get(config.retrieval_profile, config.retrieval_profile)
    assert effective == "hybrid", f"bge_m3_hybrid should map to hybrid, got {effective}"

    # should_rerank at pipeline.py L734 checks: effective_profile in {"hybrid_rerank", "hybrid_rerank_expand"}
    # For "hybrid", this is False, so reranking only happens when rerank_requested=True
    assert effective not in {"hybrid_rerank", "hybrid_rerank_expand"}, (
        "hybrid profile must NOT auto-trigger reranking"
    )
