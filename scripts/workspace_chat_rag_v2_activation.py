#!/usr/bin/env python3
"""Prepare, activate, inspect, or roll back Workspace Chat BGE-M3 retrieval.

This operator command is offline and fail closed. ``prepare`` installs and
verifies the pinned model plus sealed Gate H evidence, but does not enable the
runtime. ``activate`` requires a machine-local production benchmark PASS.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aios_habit.rag_v2.retrieval_backends import sha256_model_tree, verify_model_tree
from aios_habit.workspace_chat_rag_v2_deployment import (
    APPROVED_MODEL_CHECKSUMS,
    load_workspace_chat_rag_v2_deployment,
    sha256_file,
)

SCHEMA_VERSION = 3
PROFILE = "bge_m3_hybrid"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
MODEL_CHECKSUM = "sha256:f8faedab99c4c901e5c2f311ea3f32786b3395b5cbb0c10a60c2b83970d64405"
RERANKER_MODEL_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
RERANKER_MODEL_CHECKSUM = "sha256:66ee82666f78ee4c16efa73de43586a00b1338bf9d96cb5cf891b7b705c873c7"
DEFAULT_MODEL_SOURCE = (
    PROJECT_ROOT / "local_runs/retrieval_models/bge-m3-5617a9f"
)
DEFAULT_MODEL_DESTINATION = (
    PROJECT_ROOT / "local_runs/retrieval_models/bge-m3-5617a9f"
)
DEFAULT_RERANKER_SOURCE = (
    PROJECT_ROOT / "local_runs/retrieval_models/bge-reranker-v2-m3"
)
DEFAULT_RERANKER_DESTINATION = (
    PROJECT_ROOT / "local_runs/retrieval_models/bge-reranker-v2-m3"
)
# An evidence root is deliberately supplied by the operator.  Pinning a
# historical run here would make a successfully qualified current corpus
# impossible to activate, or worse, encourage rebinding it to stale evidence.
DEFAULT_EVIDENCE_ROOT: Path | None = None
DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "local_runs/workspace_chat_rag_v2_production"
DEFAULT_MANIFEST = PROJECT_ROOT / "config/workspace_chat_rag_v2.local.json"


class ActivationError(RuntimeError):
    """Bounded operator-facing activation failure."""


def _verify_model_tree_approved(path: Path, approved_checksums: frozenset[str] = APPROVED_MODEL_CHECKSUMS) -> str:
    actual = sha256_model_tree(path)
    if actual.casefold() not in {c.casefold() for c in approved_checksums}:
        raise ActivationError(
            f"local model checksum mismatch: {actual} not in approved checksums {sorted(approved_checksums)}"
        )
    return actual


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ActivationError(f"Cannot read required JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise ActivationError(f"Required JSON is not an object: {path.name}")
    return value


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _verify_sqlite(path: Path) -> None:
    if not path.is_file():
        raise ActivationError("Sealed Gate H SQLite evidence is missing")
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        try:
            row = connection.execute("PRAGMA quick_check").fetchone()
            chunk_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM chunks WHERE retrievable = 1"
                ).fetchone()[0]
            )
            dense_count = int(
                connection.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0]
            )
            sparse_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM chunk_sparse_embeddings"
                ).fetchone()[0]
            )
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise ActivationError("Sealed Gate H SQLite evidence is unreadable") from error
    if not row or row[0] != "ok":
        raise ActivationError("Sealed Gate H SQLite integrity check failed")
    if chunk_count <= 0 or dense_count < chunk_count or sparse_count < chunk_count:
        raise ActivationError("Sealed Gate H embedding coverage is incomplete")


def _verify_evidence(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise ActivationError("Sealed Gate H evidence root is missing")
    report_path = root / "selected_profile_report.json"
    identity_path = root / "ablation_run_identity.json"
    sqlite_path = root / "bge_m3_hybrid_runtime/rag_v2_dev.sqlite"
    report = _read_object(report_path)
    identity_envelope = _read_object(identity_path)
    identity = identity_envelope.get("identity")
    if not isinstance(identity, Mapping):
        raise ActivationError("Gate H identity envelope is invalid")
    model = identity.get("model_config")
    if not isinstance(model, Mapping):
        raise ActivationError("Gate H model identity is invalid")
    run_id = root.name
    corpus_fingerprint = str(report.get("corpus_fingerprint") or "").strip()
    if (
        report.get("status") != "PASS"
        or report.get("qualification_passed") is not True
        or report.get("qualification_id") != run_id
        or report.get("selected_profile") != PROFILE
        or report.get("decision") != "ADVANCE_TO_CANARY"
        or report.get("canary_allowed") is not True
        or not corpus_fingerprint
    ):
        raise ActivationError("Gate H selected-profile evidence is not qualified")
    if (
        identity.get("corpus_fingerprint") != corpus_fingerprint
        or model.get("bge_m3_model_revision") != MODEL_REVISION
        or str(model.get("bge_m3_model_checksum", "")).casefold() not in {c.casefold() for c in APPROVED_MODEL_CHECKSUMS}
        or model.get("retrieval_device") != "cpu"
    ):
        raise ActivationError("Gate H identity does not match production pins")
    _verify_sqlite(sqlite_path)
    return {
        "run_id": run_id,
        "report_path": str(report_path.resolve()),
        "report_sha256": sha256_file(report_path),
        "identity_path": str(identity_path.resolve()),
        "identity_sha256": sha256_file(identity_path),
        "identity_hash": str(identity_envelope.get("identity_hash", "")),
        "corpus_fingerprint": corpus_fingerprint,
        "sealed_runtime_path": str(sqlite_path.resolve()),
        "sealed_runtime_sha256": sha256_file(sqlite_path),
        "usage": "evidence_only_not_workspace_chat_query_index",
    }


def _install_model(source: Path, destination: Path, expected_checksum: str = MODEL_CHECKSUM) -> None:
    if destination.is_dir():
        _verify_model_tree_approved(destination)
        return
    if destination.exists():
        raise ActivationError("Stable model destination exists but is not a directory")
    _verify_model_tree_approved(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f"{destination.name}.staging-{os.getpid()}")
    if staging.exists():
        shutil.rmtree(staging)
    try:
        shutil.copytree(source, staging, copy_function=shutil.copy2)
        _verify_model_tree_approved(staging)
        os.replace(staging, destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def _base_manifest(args: argparse.Namespace, evidence: Mapping[str, Any]) -> dict[str, Any]:
    adaptive_on = bool(getattr(args, "enable_adaptive", False))
    actual_model_checksum = (
        sha256_model_tree(args.model_destination)
        if args.model_destination.is_dir()
        else (
            sha256_model_tree(args.model_source)
            if args.model_source.is_dir()
            else MODEL_CHECKSUM
        )
    )
    manifest = {
        "schema_version": 3 if adaptive_on else 2,
        "activation_state": "staged",
        "requested_profile": PROFILE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "id": "BAAI/bge-m3",
            "path": str(args.model_destination.resolve()),
            "revision": MODEL_REVISION,
            "checksum": actual_model_checksum,
            "device": "cpu",
            "use_fp16": False,
            "reranker_enabled": adaptive_on,
        },
        "runtime": {
            "root": str(args.runtime_root.resolve()),
            "index_role": "dynamic_workspace_chat_sources",
            "index_filename": "workspace_chat.sqlite",
        },
        "evidence": dict(evidence),
        "benchmark": {
            "status": "NOT_RUN",
            "effective_profile": "",
            "fallback_applied": None,
            "warm_p95_ms": None,
            "runtime_init_count": None,
            "memory_safe": None,
        },
        "policy": {
            "fail_closed": True,
            "lexical_fallback_enabled": False,
            "semantic_progressive": False,
            "user_mode_selector": False,
        },
    }
    if adaptive_on:
        manifest["reranker"] = {
            "id": "BAAI/bge-reranker-v2-m3",
            "path": str(args.reranker_destination.resolve()),
            "revision": RERANKER_MODEL_REVISION,
            "checksum": RERANKER_MODEL_CHECKSUM,
            "device": "cpu",
            "use_fp16": False,
        }
        manifest["adaptive"] = {
            "enabled": True,
            "policy_version": "adaptive-reranking-v1",
            "deep_timeout_ms": 300000,
            "deep_rerank_limit": 10,
        }
    return manifest


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    if args.evidence_root is None:
        raise ActivationError("--evidence-root is required for prepare")
    evidence = _verify_evidence(args.evidence_root)
    _install_model(args.model_source, args.model_destination, MODEL_CHECKSUM)
    if getattr(args, "enable_adaptive", False):
        if getattr(args, "reranker_source", None) and args.reranker_source.is_dir():
            _install_model(args.reranker_source, args.reranker_destination, RERANKER_MODEL_CHECKSUM)
    args.runtime_root.mkdir(parents=True, exist_ok=True)
    payload = _base_manifest(args, evidence)
    if args.manifest.is_file():
        current = _read_object(args.manifest)
        if current.get("activation_state") == "activated":
            raise ActivationError(
                "Active deployment cannot be overwritten; prepare a distinct candidate manifest"
            )
    _atomic_write_json(args.manifest, payload)
    return payload


ADAPTIVE_REQUIRED_GATES = (
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


def _validated_benchmark(path: Path, runtime_root: Path, require_adaptive: bool = False) -> dict[str, Any]:
    report = _read_object(path)
    status_val = report.get("overall_status") or report.get("status")
    if status_val != "PASS":
        raise ActivationError("Production benchmark did not pass all quality gates")

    if report.get("synthetic") or report.get("mock") or report.get("blocked"):
        raise ActivationError("Production benchmark cannot be synthetic, mock, or blocked")

    if require_adaptive:
        schema_v = report.get("schema_version")
        policy_v = report.get("policy_version")
        if schema_v is None or policy_v != "adaptive-reranking-v1":
            raise ActivationError("Adaptive benchmark report schema or policy version is invalid")

        provenance = report.get("provenance")
        if not isinstance(provenance, Mapping):
            raise ActivationError("Adaptive benchmark provenance is missing")
        dataset_checksum = str(provenance.get("dataset_checksum") or "").strip()
        if not dataset_checksum:
            raise ActivationError("Adaptive benchmark dataset checksum is missing or invalid")
        if not dataset_checksum.startswith("sha256:"):
            if len(dataset_checksum) == 64 and all(c in "0123456789abcdefABCDEF" for c in dataset_checksum):
                dataset_checksum = f"sha256:{dataset_checksum.lower()}"
            else:
                raise ActivationError("Adaptive benchmark dataset checksum is missing or invalid")
        bench_root = Path(str(provenance.get("runtime_root") or "")).resolve()
        if bench_root != runtime_root.resolve():
            raise ActivationError("Adaptive benchmark was not run against the target production runtime root")

        gates = report.get("gates")
        if not isinstance(gates, Mapping):
            raise ActivationError("Adaptive benchmark gates mapping is missing")
        for gate_name in ADAPTIVE_REQUIRED_GATES:
            gate_data = gates.get(gate_name)
            if not isinstance(gate_data, Mapping) or gate_data.get("status") != "PASS":
                raise ActivationError(f"Adaptive benchmark gate '{gate_name}' is not PASS")

        cm = report.get("confusion_matrix")
        if not isinstance(cm, Mapping) or int(cm.get("total_queries", 0)) <= 0:
            raise ActivationError("Adaptive benchmark confusion matrix has no queries")

        perf = report.get("performance")
        if not isinstance(perf, Mapping) or perf.get("deep_p95_ms") is None or float(perf.get("deep_p95_ms")) > 3000.0:
            raise ActivationError("Adaptive benchmark performance metrics are missing or exceed latency bounds")

        cw = report.get("candidate_windows")
        if not isinstance(cw, Mapping) or not cw:
            raise ActivationError("Adaptive benchmark candidate window measurements are missing")
    else:
        required = {
            "effective_profile": PROFILE,
            "fallback_applied": False,
            "memory_safe": True,
        }
        if any(report.get(key) != value for key, value in required.items()):
            raise ActivationError("Production benchmark did not pass all quality gates")
        try:
            warm_p95 = float(report["warm_p95_ms"])
            init_count = int(report["runtime_init_count"])
        except (KeyError, TypeError, ValueError) as error:
            raise ActivationError("Production benchmark metrics are incomplete") from error
        if warm_p95 > 3000.0 or init_count != 1:
            raise ActivationError("Production benchmark latency or runtime reuse gate failed")
        if Path(str(report.get("runtime_root", ""))).resolve() != runtime_root.resolve():
            raise ActivationError("Benchmark was not run against the production runtime")

    return {
        **report,
        "status": "PASS",
        "report_path": str(path.resolve()),
        "report_sha256": sha256_file(path),
    }



def activate(args: argparse.Namespace) -> dict[str, Any]:
    if not args.manifest.is_file():
        raise ActivationError("Run prepare before activate")
    payload = _read_object(args.manifest)
    schema_v = payload.get("schema_version")
    if schema_v not in {2, 3}:
        raise ActivationError("Deployment manifest schema is unsupported")
    is_adaptive = bool(payload.get("adaptive", {}).get("enabled", False) or getattr(args, "enable_adaptive", False))
    if args.evidence_root is None:
        raise ActivationError("--evidence-root is required for activate")
    _verify_evidence(args.evidence_root)
    _verify_model_tree_approved(args.model_destination)
    if is_adaptive:
        reranker_dest = Path(payload.get("reranker", {}).get("path") or args.reranker_destination)
        if not reranker_dest.is_dir():
            raise ActivationError("Reranker model directory is missing for adaptive activation")
        verify_model_tree(reranker_dest, RERANKER_MODEL_CHECKSUM)
    benchmark = _validated_benchmark(args.benchmark_report, args.runtime_root, require_adaptive=is_adaptive)
    updated = {
        **payload,
        "activation_state": "activated",
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": benchmark,
    }
    _atomic_write_json(args.manifest, updated)
    return updated


def rollback(args: argparse.Namespace) -> dict[str, Any]:
    if not args.manifest.is_file():
        raise ActivationError("Deployment manifest does not exist")
    payload = _read_object(args.manifest)
    updated = {
        **payload,
        "activation_state": "rolled_back",
        "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write_json(args.manifest, updated)
    return updated


def promote(args: argparse.Namespace) -> dict[str, Any]:
    """Atomically promote a separately validated candidate to the app manifest."""
    candidate_path = getattr(args, "candidate_manifest", None)
    if candidate_path is None:
        raise ActivationError("--candidate-manifest is required for promote")
    candidate_path = Path(candidate_path)
    if candidate_path.resolve() == args.manifest.resolve():
        raise ActivationError("Candidate manifest must differ from the app manifest")

    try:
        deployment = load_workspace_chat_rag_v2_deployment(
            candidate_path,
            require_activated=True,
        )
    except Exception as error:
        raise ActivationError("Candidate manifest is not a validated active deployment") from error
    if deployment is None:
        raise ActivationError("Candidate manifest is not activated")

    payload = _read_object(candidate_path)
    if args.manifest.is_file():
        backup = args.manifest.with_suffix(f"{args.manifest.suffix}.previous")
        shutil.copy2(args.manifest, backup)
    _atomic_write_json(args.manifest, payload)
    return payload


def status(args: argparse.Namespace) -> dict[str, Any]:
    if not args.manifest.is_file():
        return {"activation_state": "not_prepared", "manifest": str(args.manifest)}
    payload = _read_object(args.manifest)
    return {
        "activation_state": payload.get("activation_state", "unknown"),
        "requested_profile": payload.get("requested_profile", ""),
        "benchmark_status": payload.get("benchmark", {}).get("status", ""),
        "model_installed": args.model_destination.is_dir(),
        "adaptive_enabled": bool(payload.get("adaptive", {}).get("enabled", False)),
        "manifest": str(args.manifest.resolve()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "activate", "promote", "rollback", "status"))
    parser.add_argument("--model-source", type=Path, default=DEFAULT_MODEL_SOURCE)
    parser.add_argument("--model-destination", type=Path, default=DEFAULT_MODEL_DESTINATION)
    parser.add_argument("--reranker-source", type=Path, default=DEFAULT_RERANKER_SOURCE)
    parser.add_argument("--reranker-destination", type=Path, default=DEFAULT_RERANKER_DESTINATION)
    parser.add_argument("--enable-adaptive", action="store_true", help="Prepare or activate with adaptive reranking")
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--candidate-manifest", type=Path)
    parser.add_argument("--benchmark-report", type=Path)
    return parser



def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.action == "prepare":
            result = prepare(args)
        elif args.action == "activate":
            if args.benchmark_report is None:
                raise ActivationError("--benchmark-report is required for activate")
            result = activate(args)
        elif args.action == "promote":
            result = promote(args)
        elif args.action == "rollback":
            result = rollback(args)
        else:
            result = status(args)
    except (ActivationError, OSError, RuntimeError) as error:
        print(json.dumps({"status": "BLOCK", "reason": str(error)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": "OK",
                "activation_state": result.get("activation_state", "unknown"),
                "manifest": str(args.manifest),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
