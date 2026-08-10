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

from aios_habit.rag_v2.retrieval_backends import verify_model_tree
from aios_habit.workspace_chat_rag_v2_deployment import sha256_file

SCHEMA_VERSION = 2
PROFILE = "bge_m3_hybrid"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
MODEL_CHECKSUM = "sha256:f8faedab99c4c901e5c2f311ea3f32786b3395b5cbb0c10a60c2b83970d64405"
CORPUS_FINGERPRINT = "78957a109269e9c6272f8dfec97e9eaebce0b0252b8e7e2094d8d013b9e03056"
EVIDENCE_RUN_ID = "SELECTED-bge_m3_hybrid-1785169154-e33e5670"
DEFAULT_MODEL_SOURCE = Path(
    r"D:\Sandbox\AIOS_habbit_gate_h\local_runs\retrieval_models\bge-m3-5617a9f"
)
DEFAULT_MODEL_DESTINATION = PROJECT_ROOT / "local_runs/retrieval_models/bge-m3-5617a9f"
DEFAULT_EVIDENCE_ROOT = (
    PROJECT_ROOT / "local_runs/gate_h_selected_profile" / EVIDENCE_RUN_ID
)
DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "local_runs/workspace_chat_rag_v2_production"
DEFAULT_MANIFEST = PROJECT_ROOT / "config/workspace_chat_rag_v2.local.json"


class ActivationError(RuntimeError):
    """Bounded operator-facing activation failure."""


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
    if (
        report.get("status") != "PASS"
        or report.get("qualification_passed") is not True
        or report.get("qualification_id") != EVIDENCE_RUN_ID
        or report.get("selected_profile") != PROFILE
        or report.get("decision") != "ADVANCE_TO_CANARY"
        or report.get("canary_allowed") is not True
        or report.get("corpus_fingerprint") != CORPUS_FINGERPRINT
    ):
        raise ActivationError("Gate H selected-profile evidence is not qualified")
    if (
        identity.get("corpus_fingerprint") != CORPUS_FINGERPRINT
        or model.get("bge_m3_model_revision") != MODEL_REVISION
        or model.get("bge_m3_model_checksum") != MODEL_CHECKSUM
        or model.get("retrieval_device") != "cpu"
    ):
        raise ActivationError("Gate H identity does not match production pins")
    _verify_sqlite(sqlite_path)
    return {
        "run_id": EVIDENCE_RUN_ID,
        "report_path": str(report_path.resolve()),
        "report_sha256": sha256_file(report_path),
        "identity_path": str(identity_path.resolve()),
        "identity_sha256": sha256_file(identity_path),
        "identity_hash": str(identity_envelope.get("identity_hash", "")),
        "corpus_fingerprint": CORPUS_FINGERPRINT,
        "sealed_runtime_path": str(sqlite_path.resolve()),
        "sealed_runtime_sha256": sha256_file(sqlite_path),
        "usage": "evidence_only_not_workspace_chat_query_index",
    }


def _install_model(source: Path, destination: Path) -> None:
    if destination.is_dir():
        verify_model_tree(destination, MODEL_CHECKSUM)
        return
    if destination.exists():
        raise ActivationError("Stable model destination exists but is not a directory")
    verify_model_tree(source, MODEL_CHECKSUM)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f"{destination.name}.staging-{os.getpid()}")
    if staging.exists():
        shutil.rmtree(staging)
    try:
        shutil.copytree(source, staging, copy_function=shutil.copy2)
        verify_model_tree(staging, MODEL_CHECKSUM)
        os.replace(staging, destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def _base_manifest(args: argparse.Namespace, evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "activation_state": "staged",
        "requested_profile": PROFILE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "id": "BAAI/bge-m3",
            "path": str(args.model_destination.resolve()),
            "revision": MODEL_REVISION,
            "checksum": MODEL_CHECKSUM,
            "device": "cpu",
            "use_fp16": False,
            "reranker_enabled": False,
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


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    evidence = _verify_evidence(args.evidence_root)
    _install_model(args.model_source, args.model_destination)
    args.runtime_root.mkdir(parents=True, exist_ok=True)
    payload = _base_manifest(args, evidence)
    if args.manifest.is_file():
        current = _read_object(args.manifest)
        if current.get("activation_state") == "activated":
            if (
                current.get("model", {}).get("checksum") != MODEL_CHECKSUM
                or current.get("requested_profile") != PROFILE
            ):
                raise ActivationError("Active deployment has different immutable pins")
            return current
    _atomic_write_json(args.manifest, payload)
    return payload


def _validated_benchmark(path: Path, runtime_root: Path) -> dict[str, Any]:
    report = _read_object(path)
    required = {
        "status": "PASS",
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
        "report_path": str(path.resolve()),
        "report_sha256": sha256_file(path),
    }


def activate(args: argparse.Namespace) -> dict[str, Any]:
    if not args.manifest.is_file():
        raise ActivationError("Run prepare before activate")
    payload = _read_object(args.manifest)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ActivationError("Deployment manifest schema is unsupported")
    _verify_evidence(args.evidence_root)
    verify_model_tree(args.model_destination, MODEL_CHECKSUM)
    benchmark = _validated_benchmark(args.benchmark_report, args.runtime_root)
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


def status(args: argparse.Namespace) -> dict[str, Any]:
    if not args.manifest.is_file():
        return {"activation_state": "not_prepared", "manifest": str(args.manifest)}
    payload = _read_object(args.manifest)
    return {
        "activation_state": payload.get("activation_state", "unknown"),
        "requested_profile": payload.get("requested_profile", ""),
        "benchmark_status": payload.get("benchmark", {}).get("status", ""),
        "model_installed": args.model_destination.is_dir(),
        "manifest": str(args.manifest.resolve()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "activate", "rollback", "status"))
    parser.add_argument("--model-source", type=Path, default=DEFAULT_MODEL_SOURCE)
    parser.add_argument("--model-destination", type=Path, default=DEFAULT_MODEL_DESTINATION)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
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
