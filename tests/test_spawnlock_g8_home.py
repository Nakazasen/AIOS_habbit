"""G8 ARCH-07+ (DESKTOP-SPEED-FIX-G8-SPAWNLOCK-HOME): Per-collection spawn/init lock tests.

Verifies that:
1. Worker initialization locks are segmented by collection/pipe (`pipe_name_for_config(config)`),
   allowing `tri_thuc` to initialize in parallel without waiting for `lsu`, `dieu_tra_loi`,
   or `tong_hop` to finish their multi-second `init` exchanges.
2. `self._persistent_spawn_init_lock` only wraps the short process-spawn bookkeeping in
   `_spawn_persistent_worker` and is NOT held during the `init` IPC exchange.
3. Concurrent callers targeting the SAME collection (both via the same client instance and
   via separate client instances) never spawn duplicate workers; only one worker is spawned
   and followers reuse the initialized worker (`reused=True`, identical `pid`).
4. Persistent worker lifecycle and self-healing invariants remain intact.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import threading
import time
from typing import Any

import pytest

from aios_habit.rag_v2.bge_subprocess_client import (
    BgeSubprocessWorkerClient,
    _get_persistent_spawn_init_lock,
)
from aios_habit.rag_v2.bge_worker_protocol import pipe_name_for_config
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec


def _make_collection_config(
    tmp_path: Path,
    collection_id: str,
    *,
    build_index: bool = False,
) -> RagV2DevConfig:
    col_root = tmp_path / "collections" / collection_id
    runtime_root = col_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    if build_index:
        doc = col_root / f"{collection_id}_doc.txt"
        doc.write_text(
            f"Noi dung kiem thu spawn lock G8 cho collection {collection_id}.",
            encoding="utf-8",
        )
        spec = SourceSpec(path=doc, source_id=f"s_{collection_id}", document_id=f"d_{collection_id}")
        write_cfg = RagV2DevConfig(
            runtime_root=runtime_root,
            index_filename="library.sqlite",
            retrieval_profile="lexical",
        )
        pipeline = RagV2DevPipeline(write_cfg)
        try:
            pipeline.ingest([spec])
        finally:
            pipeline.close()
    else:
        (runtime_root / "library.sqlite").write_bytes(b"g8-dummy-sqlite")

    return RagV2DevConfig(
        runtime_root=runtime_root,
        index_filename="library.sqlite",
        retrieval_profile="lexical",
        index_read_only=True,
        ensure_embeddings_on_open=False,
    )


@pytest.fixture
def persist_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setenv("AIOS_RAGV2_WORKER_PERSIST", "1")
    monkeypatch.setenv("AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS", "600")
    return monkeypatch


def test_g8_collection_spawn_init_locks_are_segmented_by_pipe(tmp_path: Path) -> None:
    """Different collections get distinct locks; same collection shares the same lock."""
    cfg_lsu = _make_collection_config(tmp_path, "lsu")
    cfg_dtl = _make_collection_config(tmp_path, "dieu_tra_loi")
    cfg_th = _make_collection_config(tmp_path, "tong_hop")
    cfg_tt = _make_collection_config(tmp_path, "tri_thuc")

    client_a = BgeSubprocessWorkerClient()
    client_b = BgeSubprocessWorkerClient()
    try:
        lock_lsu = client_a._get_collection_spawn_init_lock(cfg_lsu)
        lock_dtl = client_a._get_collection_spawn_init_lock(cfg_dtl)
        lock_th = client_a._get_collection_spawn_init_lock(cfg_th)
        lock_tt_a = client_a._get_collection_spawn_init_lock(cfg_tt)
        lock_tt_b = client_b._get_collection_spawn_init_lock(cfg_tt)

        assert lock_lsu is not lock_dtl
        assert lock_lsu is not lock_th
        assert lock_lsu is not lock_tt_a
        assert lock_dtl is not lock_th
        assert lock_dtl is not lock_tt_a
        assert lock_th is not lock_tt_a
        assert lock_tt_a is lock_tt_b
        assert lock_tt_a is _get_persistent_spawn_init_lock(pipe_name_for_config(cfg_tt))
    finally:
        client_a.close()
        client_b.close()


def test_g8_multi_collection_parallel_init_does_not_block_tri_thuc(
    persist_env: pytest.MonkeyPatch,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Scenario B regression test: tri_thuc init must not wait for lsu/dieu_tra_loi/tong_hop init."""
    configs = {
        col: _make_collection_config(tmp_path, col)
        for col in ("lsu", "dieu_tra_loi", "tong_hop", "tri_thuc")
    }
    client = BgeSubprocessWorkerClient()

    slow_entered = {
        "lsu": threading.Event(),
        "dieu_tra_loi": threading.Event(),
        "tong_hop": threading.Event(),
    }
    release_slow = threading.Event()
    exchange_starts: dict[str, float] = {}
    exchange_ends: dict[str, float] = {}
    spawn_lock_held_during_slow_exchange: list[bool] = []

    def fake_persistent_exchange(
        config: RagV2DevConfig,
        payload: dict[str, Any],
        *,
        timeout_s: float,
        connect_timeout_s: float | None = None,
        allow_spawn: bool = False,
    ) -> dict[str, Any]:
        assert payload.get("command") == "init"
        assert allow_spawn is True
        for col, cfg in configs.items():
            if cfg == config:
                col_id = col
                break
        else:
            raise AssertionError("Unknown config")

        exchange_starts[col_id] = time.perf_counter()
        if col_id in slow_entered:
            slow_entered[col_id].set()
            release_slow.wait(timeout=5.0)
        else:
            # Verify that the global _persistent_spawn_init_lock is NOT held while slow
            # collections are inside _persistent_exchange.
            acquired = client._persistent_spawn_init_lock.acquire(blocking=False)
            if acquired:
                client._persistent_spawn_init_lock.release()
            spawn_lock_held_during_slow_exchange.append(not acquired)
            time.sleep(0.03)

        exchange_ends[col_id] = time.perf_counter()
        return {
            "status": "ok",
            "reused": False,
            "readiness": {
                "ready": True,
                "alive": True,
                "configuration_matches": True,
                "reason": "",
                "pid": os.getpid(),
                "reused": False,
            },
        }

    monkeypatch.setattr(client, "_persistent_exchange", fake_persistent_exchange)

    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, BaseException] = {}

    def run_init(col_id: str) -> None:
        try:
            results[col_id] = client.initialize_worker(configs[col_id], timeout_s=10.0)
        except BaseException as exc:
            errors[col_id] = exc

    try:
        slow_threads = [
            threading.Thread(target=run_init, args=(col_id,), daemon=True)
            for col_id in ("lsu", "dieu_tra_loi", "tong_hop")
        ]
        for t in slow_threads:
            t.start()

        for col_id, ev in slow_entered.items():
            assert ev.wait(timeout=2.0), f"{col_id} did not enter _persistent_exchange in time"

        # Now all 3 slow collections are simultaneously inside _persistent_exchange("init").
        # Fire tri_thuc initialization and verify it completes BEFORE release_slow is set!
        t0 = time.perf_counter()
        tt_thread = threading.Thread(target=run_init, args=("tri_thuc",), daemon=True)
        tt_thread.start()
        tt_thread.join(timeout=1.0)
        tt_elapsed = time.perf_counter() - t0

        try:
            assert not tt_thread.is_alive(), "tri_thuc init was blocked by other collections' init locks!"
            assert "tri_thuc" not in errors, f"tri_thuc raised error: {errors.get('tri_thuc')}"
            assert results["tri_thuc"]["status"] == "ok"
            assert tt_elapsed < 0.45, f"tri_thuc init took {tt_elapsed:.3f}s instead of running immediately"
            assert spawn_lock_held_during_slow_exchange == [False]
            assert exchange_ends["tri_thuc"] <= time.perf_counter()
        finally:
            release_slow.set()
            for t in slow_threads:
                t.join(timeout=2.0)

        assert not errors
        for col_id in ("lsu", "dieu_tra_loi", "tong_hop", "tri_thuc"):
            assert results[col_id]["status"] == "ok"
            assert exchange_ends["tri_thuc"] < exchange_ends["lsu"]
            assert exchange_ends["tri_thuc"] < exchange_ends["dieu_tra_loi"]
            assert exchange_ends["tri_thuc"] < exchange_ends["tong_hop"]
    finally:
        client.close()


def test_g8_same_collection_concurrent_init_spawns_once_and_reuses(
    persist_env: pytest.MonkeyPatch,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Concurrent callers for the SAME collection must never spawn duplicate workers."""
    cfg_tt = _make_collection_config(tmp_path, "tri_thuc")

    # Test with multiple distinct BgeSubprocessWorkerClient instances hitting the same collection
    # concurrently so both single-flight and per-collection lock + status re-check are exercised.
    clients = [BgeSubprocessWorkerClient() for _ in range(4)]
    exchange_call_count = 0
    exchange_lock = threading.Lock()
    barrier = threading.Barrier(len(clients))

    def fake_persistent_exchange(
        config: RagV2DevConfig,
        payload: dict[str, Any],
        *,
        timeout_s: float,
        connect_timeout_s: float | None = None,
        allow_spawn: bool = False,
    ) -> dict[str, Any]:
        nonlocal exchange_call_count
        with exchange_lock:
            exchange_call_count += 1
        time.sleep(0.12)
        readiness = {
            "ready": True,
            "alive": True,
            "configuration_matches": True,
            "reason": "",
            "pid": os.getpid(),
            "reused": False,
        }
        return {
            "status": "ok",
            "reused": False,
            "readiness": readiness,
        }

    for c in clients:
        monkeypatch.setattr(c, "_persistent_exchange", fake_persistent_exchange)

    results: list[dict[str, Any]] = [{} for _ in clients]
    errors: list[BaseException] = []

    def worker_call(idx: int) -> None:
        try:
            barrier.wait(timeout=2.0)
            results[idx] = clients[idx].initialize_worker(cfg_tt, timeout_s=5.0)
        except BaseException as exc:
            errors.append(exc)

    try:
        threads = [threading.Thread(target=worker_call, args=(i,), daemon=True) for i in range(len(clients))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert not errors, f"Unexpected errors: {errors}"
        # Only the first client that acquires the per-collection lock executes _persistent_exchange;
        # the remaining 3 clients see the status file written inside the per-collection lock and reuse it!
        assert exchange_call_count == 1, f"Expected exactly 1 init exchange for same collection, got {exchange_call_count}"
        reused_flags = [bool(r.get("reused")) for r in results]
        assert reused_flags.count(False) == 1
        assert reused_flags.count(True) == len(clients) - 1
        pids = {r["readiness"]["pid"] for r in results}
        assert pids == {os.getpid()}
    finally:
        for c in clients:
            c.close()


def test_g8_spawn_persistent_worker_bookkeeping_lock_serializes_spawn_check(
    persist_env: pytest.MonkeyPatch,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """_spawn_persistent_worker serializes pid_file/pipe checks under _persistent_spawn_init_lock."""
    cfg_tt = _make_collection_config(tmp_path, "tri_thuc")
    pipe_name = pipe_name_for_config(cfg_tt)
    client = BgeSubprocessWorkerClient()

    popen_calls: list[list[str]] = []
    pipe_ready = False
    barrier = threading.Barrier(4)

    class DummyProc:
        pid = os.getpid()

    def fake_pipe_available(_p: str) -> bool:
        return pipe_ready

    def fake_popen(cmd: list[str], **kwargs: Any) -> DummyProc:
        nonlocal pipe_ready
        popen_calls.append(cmd)
        pipe_ready = True
        return DummyProc()

    monkeypatch.setattr("aios_habit.rag_v2.bge_subprocess_client._pipe_instance_available", fake_pipe_available)
    monkeypatch.setattr("subprocess.Popen", fake_popen)

    def call_spawn() -> None:
        barrier.wait(timeout=2.0)
        client._spawn_persistent_worker(cfg_tt, pipe_name)

    try:
        threads = [threading.Thread(target=call_spawn, daemon=True) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(popen_calls) == 1
    finally:
        client.close()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Named Pipe daemon test")
def test_g8_real_named_pipe_parallel_two_collections_and_reuse(
    persist_env: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """End-to-end Windows persistent worker test across 2 collections concurrently + reuse."""
    cfg_a = _make_collection_config(tmp_path, "col_a", build_index=True)
    cfg_b = _make_collection_config(tmp_path, "col_b", build_index=True)
    client = BgeSubprocessWorkerClient()
    client2 = BgeSubprocessWorkerClient()

    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, BaseException] = {}

    def init_col(key: str, cfg: RagV2DevConfig) -> None:
        try:
            results[key] = client.initialize_worker(cfg, timeout_s=180.0)
        except BaseException as exc:
            errors[key] = exc

    try:
        t_a = threading.Thread(target=init_col, args=("a", cfg_a), daemon=True)
        t_b = threading.Thread(target=init_col, args=("b", cfg_b), daemon=True)
        t_a.start()
        t_b.start()
        t_a.join(timeout=185.0)
        t_b.join(timeout=185.0)

        assert not errors, f"Real worker init errors: {errors}"
        assert results["a"]["status"] == "ok"
        assert results["b"]["status"] == "ok"
        pid_a = results["a"]["readiness"]["pid"]
        pid_b = results["b"]["readiness"]["pid"]
        assert isinstance(pid_a, int) and pid_a > 0
        assert isinstance(pid_b, int) and pid_b > 0
        assert pid_a != pid_b

        # Second client must reuse both workers immediately without respawning
        reuse_a = client2.initialize_worker(cfg_a, timeout_s=30.0)
        reuse_b = client2.initialize_worker(cfg_b, timeout_s=30.0)
        assert reuse_a["reused"] is True
        assert reuse_b["reused"] is True
        assert reuse_a["readiness"]["pid"] == pid_a
        assert reuse_b["readiness"]["pid"] == pid_b
    finally:
        client.shutdown_persistent_worker(cfg_a)
        client.shutdown_persistent_worker(cfg_b)
        client.close()
        client2.close()
