"""Schema validation tests for adaptive reranking benchmark & audit reports."""
from __future__ import annotations

import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path("tests/fixtures/adaptive_reranking_report_schema.json")
CASES_PATH = Path("tests/fixtures/adaptive_routing_cases.json")


def test_adaptive_reranking_report_schema_is_valid_draft7():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_synthetic_valid_report_passes_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    sample_report = {
        "schema_version": 1,
        "policy_version": "adaptive-reranking-v1",
        "dataset_checksum": "e2698883157c1d3d108df372174a573a95cb1620fd689871a6f6223830641da6",
        "timestamp": "2026-08-16T04:00:00Z",
        "overall_status": "PASS",
        "gates": {
            "route_accuracy": {"status": "PASS", "measured": 1.0, "threshold": 0.90},
            "explicit_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "uncertain_to_deep_rate": {"status": "PASS", "measured": 1.0, "threshold": 1.0},
            "hard_mrr_gain": {"status": "PASS", "measured": 0.15, "threshold": 0.05},
            "recall_regression": {"status": "PASS", "measured": 0.0, "threshold": 0.0},
            "auto_fast_p95_regression": {"status": "PASS", "measured": 0.02, "threshold": 0.10},
            "deep_warm_p95": {"status": "PASS", "measured_ms": 25.0, "threshold_ms": 3000.0},
            "available_ram_mb": {"status": "PASS", "measured_mb": 5000.0, "threshold_mb": 2048.0},
            "runtime_init_count": {"status": "PASS", "measured": 1, "threshold": 1},
            "zero_privacy_leakage": {"status": "PASS", "leaks_detected": 0},
            "degraded_fallback_safe": {"status": "PASS"},
            "legacy_compatibility": {"status": "PASS"},
            "rollback_verified": {"status": "PASS"},
        },
        "confusion_matrix": {
            "total_queries": 60,
            "fast_true_positives": 10,
            "fast_false_positives": 0,
            "deep_true_positives": 50,
            "deep_false_positives": 0,
            "uncertain_escalations": 10,
            "explicit_deep_overrides": 10,
        },
        "performance": {
            "auto_fast_p50_ms": 13.5,
            "auto_fast_p95_ms": 14.5,
            "deep_p50_ms": 22.0,
            "deep_p95_ms": 28.5,
            "peak_rss_mb": 512.0,
            "available_ram_gb": 5.8,
        },
        "candidate_windows": {
            "10": {"mrr": 0.85, "p95_ms": 18.0},
            "30": {"mrr": 0.92, "p95_ms": 28.5},
        },
        "selected_window": 30,
    }


    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(sample_report))
    assert not errors, f"Validation errors: {errors}"


def test_generated_audit_report_conforms_to_schema(tmp_path):
    from aios_habit.rag_v2.eval_harness import generate_adaptive_audit_report

    out_json = tmp_path / "audit_report.json"
    report = generate_adaptive_audit_report(
        fixtures_path=CASES_PATH,
        output_path=out_json,
        policy_version="adaptive-reranking-v1",
    )

    assert report["overall_status"] in {"PASS", "BLOCKED"}
    assert out_json.is_file()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(report))
    assert not errors, f"Validation errors on generated report: {errors}"
