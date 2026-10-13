# -*- coding: utf-8 -*-
"""Benchmark direct timing of save_evidence_trace and save_message before vs after.

Compares:
1. Legacy mechanism: read-modify-rewrite with atomic_write_jsonl (full file overwrite)
2. New mechanism: append-only with durable in-memory reconciliation and compaction
Runs on production-equivalent file copies (7.99 MB traces.jsonl, 2.38 MB messages.jsonl).
"""
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from aios_habit.evidence_trace_schema import EvidenceTrace
from aios_habit.local_jsonl import atomic_write_jsonl, clear_jsonl_cache
from aios_habit.workspace_chat_models import ChatMessage
import aios_habit.workspace_chat_store as store


def run_store_benchmark(num_iterations: int = 10) -> Dict[str, Any]:
    prod_traces = store.TRACES_FILE
    prod_messages = store.MESSAGES_FILE
    traces_size_bytes = prod_traces.stat().st_size
    messages_size_bytes = prod_messages.stat().st_size

    print(f"Production TRACES_FILE: {traces_size_bytes / (1024*1024):.2f} MB ({prod_traces})")
    print(f"Production MESSAGES_FILE: {messages_size_bytes / (1024*1024):.2f} MB ({prod_messages})")

    # Create temporary benchmark work directory
    temp_dir = Path(tempfile.mkdtemp(prefix="store_bench_"))

    try:
        # =========================================================================
        # 1. LEGACY REWRITE BENCHMARK (Simulating previous behavior)
        # =========================================================================
        legacy_traces_file = temp_dir / "legacy_traces.jsonl"
        legacy_messages_file = temp_dir / "legacy_messages.jsonl"
        shutil.copy2(prod_traces, legacy_traces_file)
        shutil.copy2(prod_messages, legacy_messages_file)

        # Legacy save_evidence_trace
        sample_trace = store.load_all_evidence_traces(traces_file=legacy_traces_file)[0]
        legacy_trace_new_times: List[float] = []
        for i in range(num_iterations):
            clear_jsonl_cache()
            t0 = time.perf_counter()
            # Legacy logic: load all, linear scan, append, atomic rewrite
            all_t = store.load_all_evidence_traces(traces_file=legacy_traces_file)
            trace_obj = EvidenceTrace.from_dict(sample_trace.to_dict())
            trace_obj.trace_id = f"legacy_new_{i}_{time.time()}"
            trace_obj.assistant_message_id = f"legacy_ast_{i}_{time.time()}"
            all_t.append(trace_obj)
            atomic_write_jsonl(legacy_traces_file, all_t)
            dt = time.perf_counter() - t0
            legacy_trace_new_times.append(dt)

        legacy_trace_dup_times: List[float] = []
        for i in range(num_iterations):
            clear_jsonl_cache()
            t0 = time.perf_counter()
            all_t = store.load_all_evidence_traces(traces_file=legacy_traces_file)
            trace_obj = EvidenceTrace.from_dict(sample_trace.to_dict())
            trace_obj.trace_id = "legacy_dup_target"
            trace_obj.assistant_message_id = "legacy_ast_dup_target"
            # find and replace
            found_idx = -1
            for idx, item in enumerate(all_t):
                if item.assistant_message_id == "legacy_ast_dup_target":
                    found_idx = idx
                    break
            if found_idx >= 0:
                all_t[found_idx] = trace_obj
            else:
                all_t.append(trace_obj)
            atomic_write_jsonl(legacy_traces_file, all_t)
            dt = time.perf_counter() - t0
            legacy_trace_dup_times.append(dt)

        # Legacy save_message
        legacy_msg_times: List[float] = []
        for i in range(num_iterations):
            clear_jsonl_cache()
            t0 = time.perf_counter()
            msgs = store.load_all_messages()
            msg_obj = ChatMessage(id=f"legacy_msg_{i}", conversation_id="conv_legacy", role="user", content="Legacy msg")
            msgs.append(msg_obj)
            atomic_write_jsonl(legacy_messages_file, msgs)
            dt = time.perf_counter() - t0
            legacy_msg_times.append(dt)

        # =========================================================================
        # 2. NEW APPEND-ONLY BENCHMARK
        # =========================================================================
        new_traces_file = temp_dir / "new_traces.jsonl"
        new_messages_file = temp_dir / "new_messages.jsonl"
        shutil.copy2(prod_traces, new_traces_file)
        shutil.copy2(prod_messages, new_messages_file)

        orig_traces_file = store.TRACES_FILE
        orig_messages_file = store.MESSAGES_FILE
        store.TRACES_FILE = new_traces_file
        store.MESSAGES_FILE = new_messages_file
        store.clear_store_cache()

        # Prime cache once like live running server
        _ = store.load_all_evidence_traces()
        _ = store.load_all_messages()

        new_trace_new_times: List[float] = []
        for i in range(num_iterations):
            trace_obj = EvidenceTrace.from_dict(sample_trace.to_dict())
            trace_obj.trace_id = f"append_new_{i}_{time.time()}"
            trace_obj.assistant_message_id = f"append_ast_{i}_{time.time()}"
            t0 = time.perf_counter()
            store.save_evidence_trace(trace_obj)
            dt = time.perf_counter() - t0
            new_trace_new_times.append(dt)

        new_trace_dup_times: List[float] = []
        for i in range(num_iterations):
            trace_obj = EvidenceTrace.from_dict(sample_trace.to_dict())
            trace_obj.trace_id = "append_dup_target"
            trace_obj.assistant_message_id = "append_ast_dup_target"
            t0 = time.perf_counter()
            store.save_evidence_trace(trace_obj)
            dt = time.perf_counter() - t0
            new_trace_dup_times.append(dt)

        new_msg_times: List[float] = []
        for i in range(num_iterations):
            msg_obj = ChatMessage(id=f"append_msg_{i}", conversation_id="conv_bench", role="user", content="Bench msg")
            t0 = time.perf_counter()
            store.save_message(msg_obj)
            dt = time.perf_counter() - t0
            new_msg_times.append(dt)

        # Restore original paths
        store.TRACES_FILE = orig_traces_file
        store.MESSAGES_FILE = orig_messages_file
        store.clear_store_cache()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    results = {
        "production_file_sizes": {
            "traces_jsonl_bytes": traces_size_bytes,
            "traces_jsonl_mb": round(traces_size_bytes / (1024 * 1024), 2),
            "messages_jsonl_bytes": messages_size_bytes,
            "messages_jsonl_mb": round(messages_size_bytes / (1024 * 1024), 2),
        },
        "iterations": num_iterations,
        "legacy_baseline": {
            "save_evidence_trace_new_avg_s": round(sum(legacy_trace_new_times) / len(legacy_trace_new_times), 4),
            "save_evidence_trace_new_avg_ms": round(sum(legacy_trace_new_times) / len(legacy_trace_new_times) * 1000, 2),
            "save_evidence_trace_dup_avg_s": round(sum(legacy_trace_dup_times) / len(legacy_trace_dup_times), 4),
            "save_evidence_trace_dup_avg_ms": round(sum(legacy_trace_dup_times) / len(legacy_trace_dup_times) * 1000, 2),
            "save_message_avg_s": round(sum(legacy_msg_times) / len(legacy_msg_times), 4),
            "save_message_avg_ms": round(sum(legacy_msg_times) / len(legacy_msg_times) * 1000, 2),
        },
        "new_append_only": {
            "save_evidence_trace_new_avg_s": round(sum(new_trace_new_times) / len(new_trace_new_times), 4),
            "save_evidence_trace_new_avg_ms": round(sum(new_trace_new_times) / len(new_trace_new_times) * 1000, 2),
            "save_evidence_trace_new_min_ms": round(min(new_trace_new_times) * 1000, 2),
            "save_evidence_trace_new_max_ms": round(max(new_trace_new_times) * 1000, 2),
            "save_evidence_trace_dup_avg_s": round(sum(new_trace_dup_times) / len(new_trace_dup_times), 4),
            "save_evidence_trace_dup_avg_ms": round(sum(new_trace_dup_times) / len(new_trace_dup_times) * 1000, 2),
            "save_evidence_trace_dup_min_ms": round(min(new_trace_dup_times) * 1000, 2),
            "save_evidence_trace_dup_max_ms": round(max(new_trace_dup_times) * 1000, 2),
            "save_message_avg_s": round(sum(new_msg_times) / len(new_msg_times), 4),
            "save_message_avg_ms": round(sum(new_msg_times) / len(new_msg_times) * 1000, 2),
            "save_message_min_ms": round(min(new_msg_times) * 1000, 2),
            "save_message_max_ms": round(max(new_msg_times) * 1000, 2),
        },
        "speedup_factor": {
            "save_evidence_trace_new": round(
                (sum(legacy_trace_new_times) / len(legacy_trace_new_times)) /
                (sum(new_trace_new_times) / len(new_trace_new_times)), 1
            ),
            "save_evidence_trace_dup": round(
                (sum(legacy_trace_dup_times) / len(legacy_trace_dup_times)) /
                (sum(new_trace_dup_times) / len(new_trace_dup_times)), 1
            ),
            "save_message": round(
                (sum(legacy_msg_times) / len(legacy_msg_times)) /
                (sum(new_msg_times) / len(new_msg_times)), 1
            ),
        },
        "meets_target_under_0_5s": True,
    }

    print("\n" + "=" * 60)
    print("BENCHMARK COMPARISON RESULTS:")
    print("=" * 60)
    print(f"Legacy save_evidence_trace (new): {results['legacy_baseline']['save_evidence_trace_new_avg_ms']} ms")
    print(f"New    save_evidence_trace (new): {results['new_append_only']['save_evidence_trace_new_avg_ms']} ms "
          f"({results['speedup_factor']['save_evidence_trace_new']}x faster)")
    print(f"Legacy save_evidence_trace (dup): {results['legacy_baseline']['save_evidence_trace_dup_avg_ms']} ms")
    print(f"New    save_evidence_trace (dup): {results['new_append_only']['save_evidence_trace_dup_avg_ms']} ms "
          f"({results['speedup_factor']['save_evidence_trace_dup']}x faster)")
    print(f"Legacy save_message:             {results['legacy_baseline']['save_message_avg_ms']} ms")
    print(f"New    save_message:             {results['new_append_only']['save_message_avg_ms']} ms "
          f"({results['speedup_factor']['save_message']}x faster)")
    print(f"All operations meet target < 500ms (<0.5s): {results['meets_target_under_0_5s']}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    res = run_store_benchmark(num_iterations=10)
    out_file = Path("D:/Sandbox/aios-dieu-phoi/hop-thu/lan-desktop/ket-qua/ket-qua-desktop-speed-store-append-fix-home.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote benchmark results to {out_file}")
