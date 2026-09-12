#!/usr/bin/env python3
"""CPU-only recall benchmark for Goal 011 (no model/GPU load)."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from aios_habit.feature_flags import override_feature_flags
from aios_habit.workspace_memory_models import WorkspaceMemoryRecallRequest
from aios_habit.workspace_memory_service import recall_workspace_memory


def _synthetic_records(count: int) -> list[dict]:
    records = []
    for index in range(count):
        records.append(
            {
                "memory_key": f"memory_unit:mu_{index}:v1",
                "source_kind": "memory_unit",
                "source_id": f"mu_{index}",
                "title": f"Bài học số {index} siết bu-lông",
                "statement": f"Nội dung bài học {index} về momen và an toàn vận hành.",
                "applies_when": "Bảo dưỡng máy",
                "does_not_apply_when": "",
                "scope": "workspace:ws_demo",
                "status": "verified",
                "evidence_refs": [f"ev_{index}"],
                "privacy_classification": "local_only",
                "export_allowed": False,
                "updated_at": "2026-08-01T00:00:00+00:00",
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=int, default=10000)
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    records = _synthetic_records(args.items)
    request = WorkspaceMemoryRecallRequest(
        question="Siết bu-lông nắp máy thế nào?",
        workspace_id="ws_demo",
        collection_id="col_demo",
        provider_mode="local",
        include_local_only=True,
    )
    durations_ms: list[float] = []
    import tracemalloc

    with override_feature_flags(adaptive_work_memory=True):
        tracemalloc.start()
        recall_workspace_memory(request, records=records)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        for _ in range(args.runs):
            started = time.perf_counter()
            recall_workspace_memory(request, records=records)
            durations_ms.append((time.perf_counter() - started) * 1000)
    durations_ms.sort()
    p95_index = max(0, int(round(0.95 * (len(durations_ms) - 1))))
    payload = {
        "items": args.items,
        "runs": args.runs,
        "p50_ms": statistics.median(durations_ms),
        "p95_ms": durations_ms[p95_index],
        "max_ms": max(durations_ms),
        "model_loaded": False,
        "gpu_loaded": False,
        "working_set_delta_mb": round(peak / (1024 * 1024), 2),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    if payload["p95_ms"] >= 500:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
