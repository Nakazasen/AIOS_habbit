"""Finish a production-bound battle after its RAG phase was checkpointed.

The normal battle deliberately separates the BGE-M3 RAG runtime from the
Workspace worker.  On long Windows runs the parent shell can time out after
the first phase has sealed all question checkpoints.  This utility resumes
only the missing Workspace phase, verifies the immutable stage identity, and
materializes the same reports/blind bundle as the normal runner.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import battle_notebooklm_rag_v2 as runner


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError(f"invalid JSONL row: {path}")
            rows.append(value)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--production-manifest", type=Path, required=True)
    ap.add_argument("--stage-manifest", type=Path, required=True)
    ap.add_argument("--api-key-file", type=Path, required=True)
    ap.add_argument("--reference-json", type=Path, required=True)
    ns = ap.parse_args()

    run_dir = ns.run_dir.resolve()
    preflight = read_json(run_dir / "preflight.json")
    questions = read_jsonl(run_dir / "questions.jsonl")
    checkpoints = run_dir / "checkpoints"
    checkpoint_rows: dict[str, dict[str, Any]] = {}
    for question in questions:
        qid = str(question["id"])
        row = read_json(checkpoints / f"{qid}.json")
        if str(row.get("question_id")) != qid:
            raise RuntimeError(f"checkpoint question mismatch: {qid}")
        if row.get("rag_v2", {}).get("status") != "success":
            raise RuntimeError(f"RAG checkpoint is not successful: {qid}")
        checkpoint_rows[qid] = row
    if len(checkpoint_rows) != len(questions):
        raise RuntimeError("RAG checkpoint set is incomplete or duplicated")

    local = preflight["local_manifest"]
    corpus_audit = preflight["corpus_audit"]
    matrix = {str(row["question_id"]): row["systems"] for row in preflight["workflow_matrix"]}
    rag_results = [checkpoint_rows[str(q["id"])] ["rag_v2"] for q in questions]
    nlm_results = [checkpoint_rows[str(q["id"])] ["notebooklm"] for q in questions]

    sources, workspace_ingestion = runner.ingest_workspace_sources(
        ns.source_root.resolve(), local, privacy_label="cloud_safe"
    )
    production_identity = preflight["candidate"]["production_identity"]
    stage = runner.load_verified_workspace_stage(
        str(ns.stage_manifest),
        local_manifest=local,
        production_identity=production_identity,
        sources=sources,
    )
    config = runner.workspace_production_adapter_config(
        str(ns.production_manifest),
        # The verified stage root is the read-only prepared index.  Binding a
        # fresh runtime root here would make the semantic worker report
        # ``no_indexed_chunks`` despite a valid staging manifest.
        benchmark_runtime_root=stage["root"],
    )
    workspace_preparation: dict[str, Any] = {
        "status": "verified_read_only_staging",
        "stage_manifest": str(ns.stage_manifest.resolve()),
        "stage_key": stage["identity"]["stage_key"],
    }
    workspace_results: list[dict[str, Any]] = []
    try:
        readiness = runner._json_ready(runner.initialize_workspace_chat_rag_v2_worker(config))
        runner.seed_workspace_chat_source_preparation(
            sources,
            config=config,
            expected_source_fingerprints=stage["source_fingerprints"],
        )
        workspace_preparation["initialization"] = readiness
        with runner.ProgressHeartbeat(
            run_dir / "workspace_progress.json",
            stage="workspace_questions",
            total=len(questions),
        ) as progress:
            for ordinal, question in enumerate(questions):
                qid = str(question["id"])
                applicability = matrix.get(qid, {})
                if applicability.get("workspace_chat", {}).get("applicable"):
                    workspace = runner.answer_workspace_one(
                        sources,
                        runner.production_question_payload(question),
                        api_key_file=ns.api_key_file,
                        do_synthesis=True,
                        production_config=config,
                    )
                else:
                    workspace = {
                        "question_id": qid,
                        "status": "not_applicable",
                        "answer": "",
                        "reason": applicability.get("workspace_chat", {}).get("reason", ""),
                    }
                workspace["question_id"] = qid
                workspace_results.append(workspace)
                old = checkpoint_rows[qid]
                runner.atomic_write_json(
                    checkpoints / f"{qid}.json",
                    {
                        "question_id": qid,
                        "applicability": applicability,
                        "rag_v2": old["rag_v2"],
                        "workspace_chat": workspace,
                        "notebooklm": old["notebooklm"],
                    },
                )
                progress.update(completed=ordinal + 1, current=qid)
    finally:
        runner.close_workspace_chat_rag_v2_runtimes()

    runner.atomic_write_json(run_dir / "workspace_production_preparation.json", workspace_preparation)
    runner.write_jsonl(run_dir / "rag_v2_answers.jsonl", rag_results)
    runner.write_jsonl(run_dir / "workspace_chat_answers.jsonl", workspace_results)
    runner.write_jsonl(run_dir / "notebooklm_answers.jsonl", nlm_results)
    runner.write_jsonl(run_dir / "workspace_chat_outbound_manifests.jsonl", runner.build_outbound_manifest_rows(workspace_results))

    shared_questions = [
        question
        for question in questions
        if all(bool(matrix.get(str(question["id"]), {}).get(system, {}).get("applicable")) for system in ("rag_v2", "workspace_chat", "notebooklm"))
    ]
    results_by_system = {"rag_v2": rag_results, "workspace_chat": workspace_results, "notebooklm": nlm_results}
    bundle, assignment = runner.make_blind_bundle(shared_questions, results_by_system, str(preflight["question_set_hash"]))
    runner.write_jsonl(run_dir / "blind_bundle.jsonl", bundle)
    runner.atomic_write_json(run_dir / "blind_assignment.json", assignment)

    reference_snapshot = read_json(ns.reference_json.resolve())
    reference_summary = preflight.get("reference", {})
    metadata = {
        "battle_id": run_dir.name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "notebook_id": preflight["notebook"]["notebook_id"],
        "source_root_name": "tailieugoc",
        "corpus_fingerprint": local.get("corpus_fingerprint"),
        "question_set_hash": preflight["question_set_hash"],
        "candidate": preflight.get("candidate"),
        "selected_question_ids": [str(q["id"]) for q in questions],
        "corpus_audit_hash": corpus_audit.get("audit_hash"),
        "corpus_bucket_counts": corpus_audit.get("counts"),
        "router": preflight.get("router"),
        "rag_v2_ingestion": {k: v for k, v in read_json(run_dir / "rag_v2_ingestion_coverage.json").items() if k != "files"},
        "workspace_ingestion": {k: v for k, v in workspace_ingestion.items() if k != "files"},
        "workspace_production_protocol": runner.WORKSPACE_PRODUCTION_PROTOCOL,
        "workspace_production_preparation": workspace_preparation,
        "production_arm": "workspace_chat",
        "candidate_arm": "rag_v2",
        "comparison_arm": "notebooklm",
        "reference_mode": "registry_reference",
        "reference_capture_id": reference_snapshot["reference_capture_id"],
        "reference_manifest_hash": reference_snapshot["notebook_manifest_hash"],
        "reference_question_set_hash": reference_snapshot["question_set_hash"],
        "reference_corpus_fingerprint": reference_snapshot["corpus_fingerprint"],
        "reference_registry_schema_version": reference_summary.get("registry_schema_version"),
        "reference_snapshot_digest": reference_summary.get("registry_snapshot_digest", ""),
        "reference_registry_file_sha256": reference_summary.get("registry_file_sha256", ""),
        "live_arms": ["rag_v2", "workspace_chat"],
        "notebook_query_count": 0,
        "mode": "run",
        "rag_v2_runtime_cache": read_json(run_dir / "rag_v2_runtime_cache.json"),
        "resumed_from_checkpoints": True,
    }
    applicability = {
        str(q["id"]): {system: bool(matrix.get(str(q["id"]), {}).get(system, {}).get("applicable")) for system in ("rag_v2", "workspace_chat", "notebooklm")}
        for q in questions
    }
    runner.generate_report(run_dir, metadata=metadata, questions=questions, results_by_system=results_by_system, applicability_by_question=applicability)
    runner.generate_report(run_dir / "algorithm_comparison", metadata={**metadata, "comparison_scope": "rag_v2_vs_workspace_chat"}, questions=questions, results_by_system={"rag_v2": rag_results, "workspace_chat": workspace_results}, applicability_by_question={qid: {s: vals[s] for s in ("rag_v2", "workspace_chat")} for qid, vals in applicability.items()})
    runner.atomic_write_json(run_dir / "run_metadata.json", metadata)
    print(json.dumps({
        "status": "PASS",
        "run_dir": str(run_dir),
        "question_count": len(questions),
        "workspace_statuses": {s: sum(row.get("status") == s for row in workspace_results) for s in sorted({str(row.get("status")) for row in workspace_results})},
        "blind_bundle_rows": len(bundle),
        "workspace_preparation_status": workspace_preparation.get("status"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
