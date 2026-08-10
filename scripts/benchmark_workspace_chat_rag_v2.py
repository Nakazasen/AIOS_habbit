#!/usr/bin/env python3
"""Benchmark staged BGE-M3 through the real Workspace Chat retrieval adapter."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aios_habit.rag_v2.pipeline import RagV2DevPipeline
from aios_habit.rag_v2.retrieval_backends import verify_model_tree
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    close_workspace_chat_rag_v2_runtimes,
    retrieve_workspace_chat_evidence,
)
from aios_habit.workspace_chat_rag_v2_deployment import (
    EXPECTED_PROFILE,
    load_workspace_chat_rag_v2_deployment,
)

DEFAULT_MANIFEST = PROJECT_ROOT / "config/workspace_chat_rag_v2.local.json"
DEFAULT_REPORT = (
    PROJECT_ROOT / "local_runs/workspace_chat_rag_v2_production/benchmark_report.json"
)
GIB = 1024**3
MAX_WARM_P95_MS = 3000.0
MAX_PEAK_RSS_BYTES = 8 * GIB
MIN_AVAILABLE_MEMORY_BYTES = 1536 * 1024**2


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _memory_snapshot() -> dict[str, int]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    get_current_process = kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = wintypes.HANDLE
    get_process_memory_info = psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
        wintypes.DWORD,
    ]
    get_process_memory_info.restype = wintypes.BOOL
    global_memory_status = kernel32.GlobalMemoryStatusEx
    global_memory_status.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    global_memory_status.restype = wintypes.BOOL

    process = PROCESS_MEMORY_COUNTERS_EX()
    process.cb = ctypes.sizeof(process)
    handle = get_current_process()
    if not get_process_memory_info(handle, ctypes.byref(process), process.cb):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    system = MEMORYSTATUSEX()
    system.dwLength = ctypes.sizeof(system)
    if not global_memory_status(ctypes.byref(system)):
        raise OSError(ctypes.get_last_error(), "GlobalMemoryStatusEx failed")
    return {
        "working_set_bytes": int(process.WorkingSetSize),
        "peak_working_set_bytes": int(process.PeakWorkingSetSize),
        "private_bytes": int(process.PrivateUsage),
        "total_physical_bytes": int(system.ullTotalPhys),
        "available_physical_bytes": int(system.ullAvailPhys),
        "memory_load_percent": int(system.dwMemoryLoad),
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sources() -> tuple[WorkspaceAIContextSource, ...]:
    texts = (
        (
            "benchmark-vietnamese",
            "Ghi chú hồ sơ: mã ORCHID-731 cần được kiểm tra vào thứ Hai. "
            "Người phụ trách là Minh và trạng thái hiện tại là đang chờ xác nhận. "
            "Không sử dụng mã cũ ALPHA-440 cho hồ sơ này."
        ),
        (
            "benchmark-japanese",
            "会議メモ: プロジェクトコードは SAKURA-882 です。担当者は田中さんです。"
            "次の確認日は火曜日で、現在の状態は承認待ちです。"
        ),
        (
            "benchmark-english",
            "Operations note: ticket NEBULA-515 has a Thursday review deadline. "
            "Its owner is Alex and the current state is pending evidence review."
        ),
    )
    return tuple(
        WorkspaceAIContextSource(
            source_id=source_id,
            source_scope="temporary",
            source_type="pasted_text",
            title=f"{source_id}.txt",
            privacy_label="local_only",
            text=text,
            included_chars=len(text),
            truncated=False,
        )
        for source_id, text in texts
    )


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999999) - 1))
    return ordered[index]


def run_benchmark(manifest: Path, warm_runs: int) -> dict[str, Any]:
    deployment = load_workspace_chat_rag_v2_deployment(manifest)
    if deployment is None or deployment.activation_state != "staged":
        raise RuntimeError("benchmark requires a staged deployment manifest")
    verify_model_tree(deployment.model_path, deployment.model_checksum)
    config = WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        requested_profile=deployment.requested_profile,
        runtime_root=deployment.runtime_root,
        bge_m3_model_path=deployment.model_path,
        bge_m3_model_revision=deployment.model_revision,
        bge_m3_model_checksum=deployment.model_checksum,
        retrieval_device=deployment.retrieval_device,
        fail_closed_on_error=True,
    )
    sources = _sources()
    questions = (
        "Mã ORCHID-731 cần làm gì và vào ngày nào?",
        "プロジェクトコードと担当者は誰ですか？",
        "Who owns ticket NEBULA-515 and when is its review?",
        "Trạng thái hiện tại của hồ sơ do Minh phụ trách là gì?",
        "次の確認日はいつですか？",
    )
    init_count = 0

    def counting_factory(pipeline_config):
        nonlocal init_count
        init_count += 1
        return RagV2DevPipeline(pipeline_config)

    close_workspace_chat_rag_v2_runtimes()
    before = _memory_snapshot()
    started = time.perf_counter()
    cold = retrieve_workspace_chat_evidence(
        questions[0], sources, config=config, pipeline_factory=counting_factory
    )
    cold_ms = (time.perf_counter() - started) * 1000.0
    warm_latencies: list[float] = []
    warm_results: list[dict[str, Any]] = []
    for index in range(warm_runs):
        started = time.perf_counter()
        result = retrieve_workspace_chat_evidence(
            questions[index % len(questions)],
            sources,
            config=config,
            pipeline_factory=counting_factory,
        )
        warm_latencies.append((time.perf_counter() - started) * 1000.0)
        warm_results.append(result)
    after = _memory_snapshot()
    all_results = [cold, *warm_results]
    telemetry = [result.get("rag_v2_canary", {}) for result in all_results]
    effective_profile = telemetry[-1].get("effective_profile", "")
    fallback_applied = any(item.get("fallback_applied") is not False for item in telemetry)
    retrieval_passed = all(
        result.get("summary_count", 0) > 0
        and result.get("status") != "quality_search_unavailable"
        for result in all_results
    )
    profile_passed = all(
        item.get("backend") == "rag_v2"
        and item.get("effective_profile") == EXPECTED_PROFILE
        and item.get("fallback_applied") is False
        for item in telemetry
    )
    warm_p95_ms = _p95(warm_latencies)
    peak_rss = max(before["peak_working_set_bytes"], after["peak_working_set_bytes"])
    available = after["available_physical_bytes"]
    memory_safe = (
        peak_rss <= MAX_PEAK_RSS_BYTES
        and available >= MIN_AVAILABLE_MEMORY_BYTES
        and after["total_physical_bytes"] >= 12 * GIB
    )
    passed = (
        retrieval_passed
        and profile_passed
        and not fallback_applied
        and init_count == 1
        and warm_p95_ms <= MAX_WARM_P95_MS
        and memory_safe
    )
    return {
        "schema_version": 1,
        "status": "PASS" if passed else "BLOCK",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "runtime_root": str(deployment.runtime_root.resolve()),
        "manifest_path": str(manifest.resolve()),
        "requested_profile": deployment.requested_profile,
        "effective_profile": effective_profile,
        "fallback_applied": fallback_applied,
        "retrieval_passed": retrieval_passed,
        "profile_passed": profile_passed,
        "runtime_init_count": init_count,
        "cold_ms": round(cold_ms, 3),
        "warm_runs": warm_runs,
        "warm_latencies_ms": [round(value, 3) for value in warm_latencies],
        "warm_mean_ms": round(statistics.fmean(warm_latencies), 3),
        "warm_p95_ms": round(warm_p95_ms, 3),
        "latency_limit_ms": MAX_WARM_P95_MS,
        "memory_safe": memory_safe,
        "memory": {
            "before": before,
            "after": after,
            "max_peak_rss_bytes": MAX_PEAK_RSS_BYTES,
            "min_available_memory_bytes": MIN_AVAILABLE_MEMORY_BYTES,
        },
        "network_enabled": False,
        "provider_synthesis_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--warm-runs", type=int, default=8)
    args = parser.parse_args()
    if args.warm_runs < 5:
        parser.error("--warm-runs must be at least 5")
    try:
        report = run_benchmark(args.manifest, args.warm_runs)
        _atomic_write_json(args.report, report)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "cold_ms": report["cold_ms"],
                    "warm_p95_ms": report["warm_p95_ms"],
                    "runtime_init_count": report["runtime_init_count"],
                    "memory_safe": report["memory_safe"],
                    "report": str(args.report),
                },
                ensure_ascii=False,
            )
        )
        return 0 if report["status"] == "PASS" else 2
    except Exception as error:
        failure = {
            "schema_version": 1,
            "status": "BLOCK",
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "reason_code": type(error).__name__.casefold(),
            "runtime_root": "",
            "effective_profile": "",
            "fallback_applied": True,
            "runtime_init_count": 0,
            "warm_p95_ms": None,
            "memory_safe": False,
        }
        _atomic_write_json(args.report, failure)
        print(json.dumps({"status": "BLOCK", "reason": failure["reason_code"]}))
        return 2
    finally:
        close_workspace_chat_rag_v2_runtimes()


if __name__ == "__main__":
    raise SystemExit(main())
