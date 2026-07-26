"""Manage the local immutable NotebookLM reference registry.

This evaluation-only CLI never queries NotebookLM or another provider.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aios_habit.benchmark_reference_registry import (  # noqa: E402
    ReferenceRegistryError,
    export_snapshot,
    import_snapshot,
    initialize_registry,
    list_snapshots,
    verify_registry,
)


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenceRegistryError(f"Portable reference JSON is invalid: {exc}") from exc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluation-only immutable benchmark reference registry"
    )
    parser.add_argument("--registry", required=True, help="SQLite registry path under local_runs/")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create or validate the registry schema")

    importer = commands.add_parser("import-json", help="Atomically import and seal a snapshot")
    importer.add_argument("--input", required=True, help="Portable reference JSON")

    verifier = commands.add_parser("verify", help="Verify schema, FK and snapshot hashes")
    verifier.add_argument("--capture-id", default="", help="Optional immutable capture ID")

    commands.add_parser("list", help="List provenance without raw answers")

    exporter = commands.add_parser("export-json", help="Export one portable reference snapshot")
    exporter.add_argument("--capture-id", required=True)
    exporter.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    registry = Path(args.registry)
    try:
        if args.command == "init":
            result = initialize_registry(registry)
        elif args.command == "import-json":
            result = import_snapshot(registry, _load_json(Path(args.input)))
        elif args.command == "verify":
            result = verify_registry(registry, args.capture_id or None)
        elif args.command == "list":
            result = {
                "status": "PASS",
                "registry": str(registry),
                "captures": list_snapshots(registry),
            }
        elif args.command == "export-json":
            payload = export_snapshot(registry, args.capture_id)
            destination = Path(args.output)
            _atomic_write_json(destination, payload)
            result = {
                "status": "PASS",
                "capture_id": args.capture_id,
                "output": str(destination),
            }
        else:  # pragma: no cover - argparse enforces the command set.
            raise ReferenceRegistryError(f"Unsupported command: {args.command}")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ReferenceRegistryError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
