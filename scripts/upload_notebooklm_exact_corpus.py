"""Upload the deterministic 70-source NotebookLM corpus with UTF-8-safe paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook-id", required=True)
    parser.add_argument("--conversion-manifest", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    args = parser.parse_args()
    conversion = json.loads(args.conversion_manifest.read_text(encoding="utf-8"))
    records = list(conversion["records"])
    progress = {
        "schema_version": 1,
        "status": "RUNNING",
        "notebook_id": args.notebook_id,
        "conversion_manifest_hash": conversion.get("conversion_manifest_hash", ""),
        "total": len(records),
        "completed": 0,
        "results": [],
    }
    if args.progress.exists():
        try:
            prior = json.loads(args.progress.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prior = {}
        if prior.get("notebook_id") == args.notebook_id and int(prior.get("total", 0) or 0) == len(records):
            progress["results"] = list(prior.get("results", []))
            progress["completed"] = int(prior.get("completed", 0) or 0)
    atomic_json(args.progress, progress)
    for index, record in enumerate(records, start=1):
        prior_row = next((row for row in progress["results"] if row.get("ordinal") == record["ordinal"]), None)
        if prior_row and prior_row.get("source_id"):
            continue
        started = time.perf_counter()
        command = [
            "nlm", "source", "add", args.notebook_id,
            "--file", str(record["upload_path"]),
            "--title", str(record["title"]),
            "--json",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        raw = completed.stdout.strip()
        try:
            response = json.loads(raw)
        except json.JSONDecodeError:
            response = {"status": "error", "error": raw[-2000:]}
        source_id = response.get("source_id") or response.get("id") or ""
        result = {
            "ordinal": record["ordinal"],
            "title": record["title"],
            "conversion": record["conversion"],
            "status": response.get("status", "error"),
            "source_id": source_id,
            "error": response.get("error", "") if isinstance(response, dict) else "",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        if source_id:
            # The CLI may return a source id while its status field is absent or
            # uses a version-specific label; the id is the durable success proof.
            result["status"] = "success"
        progress["results"].append(result)
        progress["completed"] = index
        progress["last_result"] = result
        progress["status"] = "RUNNING" if index < len(records) else "COMPLETED"
        atomic_json(args.progress, progress)
        print(json.dumps({"completed": index, "total": len(records), **result}, ensure_ascii=False), flush=True)
        if result["status"] not in {"success", "ok", "completed"}:
            progress["status"] = "FAILED"
            atomic_json(args.progress, progress)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
