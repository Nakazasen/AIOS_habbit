"""Reconcile uploaded NotebookLM source IDs with the canonical 70-file corpus.

The upload CLI may ignore ``--title`` for file uploads and resumable retries can
leave duplicate source IDs in the local checkpoint.  This script uses the live
notebook list as the authority, chooses one currently-existing ID per logical
ordinal, renames it to the canonical raw title, and emits a metadata-only
reconciliation record.  It never stores source contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_json(args: list[str]) -> object:
    out = subprocess.check_output(args, text=True, encoding="utf-8")
    return json.loads(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook", required=True)
    ap.add_argument("--corpus-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ns = ap.parse_args()

    corpus_dir = ns.corpus_dir.resolve()
    conversion = json.loads(
        (corpus_dir / "conversion_manifest.json").read_text(encoding="utf-8")
    )
    progress = json.loads(
        (corpus_dir / "upload_progress.json").read_text(encoding="utf-8")
    )
    live = run_json(["nlm", "source", "list", ns.notebook, "--full", "--json"])
    live_by_id = {row["id"]: row for row in live}
    records = {int(row["ordinal"]): row for row in conversion["records"]}
    candidates: dict[int, list[str]] = {ordinal: [] for ordinal in records}
    for row in progress.get("results", []):
        ordinal = row.get("ordinal")
        source_id = row.get("source_id")
        if ordinal in candidates and source_id in live_by_id:
            if source_id not in candidates[ordinal]:
                candidates[ordinal].append(source_id)

    missing = [ordinal for ordinal, ids in candidates.items() if not ids]
    if missing:
        raise SystemExit(f"no live source ID for ordinal(s): {missing}")

    # Prefer the last live ID recorded for a retried ordinal.  There should be
    # one after duplicate cleanup; ambiguity is retained in audit metadata.
    selected = {ordinal: ids[-1] for ordinal, ids in candidates.items()}
    if len(set(selected.values())) != len(selected):
        raise SystemExit("a live source ID is selected for more than one ordinal")

    renames = []
    for ordinal in sorted(selected):
        source_id = selected[ordinal]
        title = records[ordinal]["title"]
        current_title = live_by_id[source_id].get("title")
        status = "already_canonical" if current_title == title else "renamed"
        if status == "renamed":
            subprocess.check_call(
                [
                    "nlm",
                    "source",
                    "rename",
                    source_id,
                    title,
                    "--notebook",
                    ns.notebook,
                ]
            )
        renames.append(
            {
                "ordinal": ordinal,
                "source_id": source_id,
                "title": title,
                "previous_title": current_title,
                "status": status,
                "raw_sha256": records[ordinal]["raw_sha256"],
                "upload_sha256": records[ordinal]["upload_sha256"],
            }
        )

    final_live = run_json(["nlm", "source", "list", ns.notebook, "--full", "--json"])
    final_by_id = {row["id"]: row for row in final_live}
    wrong = [
        row
        for row in renames
        if final_by_id.get(row["source_id"], {}).get("title") != row["title"]
    ]
    if wrong:
        raise SystemExit(f"rename verification failed for ordinal(s): {[r['ordinal'] for r in wrong]}")

    payload = {
        "schema_version": 1,
        "status": "VERIFIED",
        "notebook_id": ns.notebook,
        "logical_source_count": len(records),
        "live_source_count": len(final_live),
        "ready_source_count": sum(row.get("status") == 2 for row in final_live),
        "conversion_manifest_hash": conversion["conversion_manifest_hash"],
        "selected_source_ids": selected,
        "renames": renames,
        "duplicate_candidate_ordinals": {
            str(ordinal): ids for ordinal, ids in candidates.items() if len(ids) > 1
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    payload["reconciliation_sha256"] = sha256_bytes(canonical)
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "logical_source_count": payload["logical_source_count"],
        "live_source_count": payload["live_source_count"],
        "ready_source_count": payload["ready_source_count"],
        "renamed_count": sum(row["status"] == "renamed" for row in renames),
        "duplicate_candidate_ordinals": payload["duplicate_candidate_ordinals"],
        "reconciliation_sha256": payload["reconciliation_sha256"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
