"""Unit and semantic equivalence tests for DESKTOP-SPEED-FIX-G3-PIPE-IPC-HOME.

Covers:
- ARCH-05: Cancellation/abort event in _persistent_exchange (_session thread);
  when caller times out, abort_event is set, connect loop is cancelled, and
  stale payload is NEVER sent via conn.send() after caller gives up.
  Includes busy/slow worker simulation proving no orphaned thread hijacks the pipe.
- ARCH-08: Periodic logging ([PIPE_CONNECT_WAIT]) when pipe connect wait exceeds
  1.0s, returning pipe_connect_ms / pipe_wait_ms / pipe_exec_ms, and propagating
  pipe_wait_ms into [RETRIEVAL_MICRO_TIMING].
- ARCH-13: Atomic status/heartbeat file (pid, initialized, config_fingerprint,
  timestamp) written when worker init completes; non-blocking readiness/is_ready
  via status file without contending on single-session Named Pipe when worker is
  busy; fallback to legacy pipe health probe when status file is absent/stale;
  strict preservation of true readiness semantics (live PID + matching config).
"""
from __future__ import annotations

import concurrent.futures
import json
import logging
import multiprocessing.connection as mpc
import os
from pathlib import Path
import threading
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from aios_habit.rag_v2.bge_subprocess_client import (
    BgeSubprocessWorkerClient,
    _is_worker_pid_alive,
)
from aios_habit.rag_v2.bge_worker_protocol import (
    authkey_for_worker,
    config_fingerprint_for_worker,
    pipe_name_for_config,
    remove_worker_status_file,
    status_file_for_config,
    write_worker_status_file,
)
from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2.semantic import SemanticBackendError


def _make_query_config(tmp_path: Path, **overrides: Any) -> RagV2DevConfig:
    params: dict[str, Any] = {
        "runtime_root": tmp_path / "runtime",
        "index_filename": "g3_test.sqlite",
        "retrieval_profile": "lexical",
        "index_read_only": True,
        "ensure_embeddings_on_open": False,
    }
    params.update(overrides)
    return RagV2DevConfig(**params)


@pytest.fixture
def persist_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setenv("AIOS_RAGV2_WORKER_PERSIST", "1")
    monkeypatch.setenv("AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS", "600")
    return monkeypatch


def test_arch05_timeout_sets_abort_and_never_sends_stale_payload(
    persist_env: pytest.MonkeyPatch,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ARCH-05: When caller times out waiting for busy pipe, _session aborts and never calls conn.send."""
    cfg = _make_query_config(tmp_path)
    client = BgeSubprocessWorkerClient()

    sent_payloads: list[dict[str, Any]] = []
    closed_count = 0
    connect_calls = 0
    allow_connect_event = threading.Event()

    class _FakeConn:
        def send(self, obj: Any) -> None:
            sent_payloads.append(dict(obj))

        def recv(self) -> dict[str, Any]:
            return {"status": "ok", "query_result": {"summary": {}, "items": []}}

        def close(self) -> None:
            nonlocal closed_count
            closed_count += 1

    def _fake_mpc_client(address: str, family: str = "AF_PIPE", authkey: bytes | None = None) -> _FakeConn:
        nonlocal connect_calls
        connect_calls += 1
        if not allow_connect_event.is_set():
            raise OSError(231, "All pipe instances are busy")
        return _FakeConn()

    monkeypatch.setattr(mpc, "Client", _fake_mpc_client)

    # Caller 1 times out after 0.15s while pipe is busy (connect_timeout_s=5.0s)
    t0 = time.perf_counter()
    with pytest.raises(SemanticBackendError, match="bge_worker_persist_timeout"):
        client._persistent_exchange(
            cfg,
            {"command": "query", "question": "stale_question_after_timeout"},
            timeout_s=0.15,
            connect_timeout_s=5.0,
            allow_spawn=False,
        )
    elapsed_s = time.perf_counter() - t0
    assert elapsed_s < 0.8
    calls_at_timeout = connect_calls
    assert calls_at_timeout >= 1

    # Now pipe becomes free 0.15s after caller gave up; orphaned thread must ALREADY be dead
    # and must NEVER connect or send the stale payload.
    allow_connect_event.set()
    time.sleep(0.25)

    assert sent_payloads == [], "Stale payload must NEVER be sent after caller timeout"
    assert connect_calls <= calls_at_timeout + 1

    # Subsequent fresh caller succeeds immediately and sends only its own payload
    fresh_resp = client._persistent_exchange(
        cfg,
        {"command": "query", "question": "fresh_question"},
        timeout_s=2.0,
        connect_timeout_s=2.0,
        allow_spawn=False,
    )
    assert fresh_resp["status"] == "ok"
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["question"] == "fresh_question"


@pytest.mark.skipif(os.name != "nt", reason="Windows named pipe test")
def test_arch05_busy_slow_worker_real_named_pipe_no_orphan_hijack(
    persist_env: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ARCH-05: Real Windows Named Pipe simulation with slow worker proves timed-out caller
    does not leave an orphan thread occupying the pipe or sending stale commands.
    """
    cfg = _make_query_config(tmp_path)
    pipe_name = pipe_name_for_config(cfg)
    authkey = authkey_for_worker()
    client = BgeSubprocessWorkerClient()

    received_questions: list[str] = []
    server_stop = threading.Event()
    server_ready = threading.Event()

    def _pipe_server() -> None:
        listener = mpc.Listener(pipe_name, family="AF_PIPE", authkey=authkey)
        server_ready.set()
        try:
            while not server_stop.is_set():
                try:
                    conn = listener.accept()
                except Exception:
                    break
                try:
                    req = conn.recv()
                    if isinstance(req, dict):
                        cmd = req.get("command")
                        if cmd == "shutdown":
                            conn.send({"status": "ok"})
                            break
                        q_text = str(req.get("question", ""))
                        received_questions.append(q_text)
                        if q_text == "slow_q1":
                            time.sleep(0.55)
                        conn.send(
                            {
                                "status": "ok",
                                "query_result": {
                                    "summary": {
                                        "returned_count": 1,
                                        "candidate_count": 1,
                                        "indexed_chunk_count": 1,
                                    },
                                    "items": [{"document_id": "d1", "text": f"ans:{q_text}", "score": 1.0}],
                                },
                            }
                        )
                except (EOFError, OSError):
                    pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        finally:
            try:
                listener.close()
            except Exception:
                pass

    server_thread = threading.Thread(target=_pipe_server, daemon=True)
    server_thread.start()
    assert server_ready.wait(timeout=5.0)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            # 1. Start slow query Q1 (occupies worker for ~0.55s)
            fut_q1 = pool.submit(
                client._persistent_exchange,
                cfg,
                {"command": "query", "question": "slow_q1"},
                timeout_s=3.0,
                connect_timeout_s=3.0,
                allow_spawn=False,
            )
            time.sleep(0.08)

            # 2. While worker is busy with Q1, Caller 2 sends Q2 with short timeout (0.15s)
            with pytest.raises(SemanticBackendError, match="bge_worker_persist_timeout"):
                client._persistent_exchange(
                    cfg,
                    {"command": "query", "question": "abandoned_q2"},
                    timeout_s=0.15,
                    connect_timeout_s=5.0,
                    allow_spawn=False,
                )

            # 3. Wait for Q1 to complete
            res_q1 = fut_q1.result(timeout=3.0)
            assert res_q1["status"] == "ok"

            # 4. Immediately send Q3; pipe must be free without Q2 hijacking it
            t_q3 = time.perf_counter()
            res_q3 = client._persistent_exchange(
                cfg,
                {"command": "query", "question": "fast_q3"},
                timeout_s=2.0,
                connect_timeout_s=2.0,
                allow_spawn=False,
            )
            q3_elapsed_ms = (time.perf_counter() - t_q3) * 1000.0

        assert res_q3["status"] == "ok"
        assert q3_elapsed_ms < 250.0
        # Worker must NEVER have received "abandoned_q2"!
        assert received_questions == ["slow_q1", "fast_q3"]
    finally:
        server_stop.set()
        try:
            client._persistent_exchange(
                cfg,
                {"command": "shutdown"},
                timeout_s=1.0,
                connect_timeout_s=1.0,
                allow_spawn=False,
            )
        except Exception:
            pass
        server_thread.join(timeout=2.0)


def test_arch08_periodic_pipe_wait_logging_and_micro_timing_propagation(
    persist_env: pytest.MonkeyPatch,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """ARCH-08: Waiting >1s on pipe connection logs [PIPE_CONNECT_WAIT] periodically,
    returns pipe_connect_ms, and propagates pipe_wait_ms into [RETRIEVAL_MICRO_TIMING].
    """
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
    from aios_habit.workspace_chat_rag_v2_adapter import (
        WorkspaceChatRagV2CanaryConfig,
        _run_profile,
    )

    cfg = _make_query_config(tmp_path)
    client = BgeSubprocessWorkerClient()

    start_Clock = time.perf_counter()

    class _FakeConn:
        def send(self, obj: Any) -> None:
            pass

        def recv(self) -> dict[str, Any]:
            return {
                "status": "ok",
                "query_result": {
                    "summary": {
                        "filtered_as_stale_count": 0,
                        "candidate_count": 4,
                        "returned_count": 2,
                        "indexed_chunk_count": 20,
                        "dense_latency_ms": 50.0,
                        "sparse_latency_ms": 20.0,
                        "fusion_latency_ms": 5.0,
                        "embed_latency_ms": 120.0,
                        "embed_wait_ms": 0.0,
                        "embed_compute_ms": 120.0,
                        "dense_load_latency_ms": 0.0,
                        "dense_resident": True,
                    },
                    "items": [],
                    "routing": {},
                    "synthesis": {},
                },
            }

        def close(self) -> None:
            pass

    def _busy_then_connect(address: str, family: str = "AF_PIPE", authkey: bytes | None = None) -> _FakeConn:
        if (time.perf_counter() - start_Clock) < 1.15:
            raise OSError(231, "All pipe instances are busy")
        return _FakeConn()

    monkeypatch.setattr(mpc, "Client", _busy_then_connect)

    with caplog.at_level(logging.INFO):
        q_res = client.query_ready(
            "Câu hỏi kiểm tra pipe_connect_ms?",
            [SourceSpec(path=tmp_path / "doc.txt", source_id="s1", document_id="d1")],
            cfg,
            timeout_s=5.0,
        )

    assert "pipe_connect_ms" in q_res
    assert "pipe_wait_ms" in q_res
    assert q_res["pipe_connect_ms"] >= 1100.0
    assert q_res["pipe_wait_ms"] == q_res["pipe_connect_ms"]
    assert q_res["summary"]["pipe_wait_ms"] >= 1100.0

    wait_logs = [rec.message for rec in caplog.records if "[PIPE_CONNECT_WAIT]" in rec.message]
    assert len(wait_logs) >= 1, f"Expected [PIPE_CONNECT_WAIT] log when wait > 1s, got: {caplog.text}"
    assert "command=query" in wait_logs[0]
    assert "wait_ms=" in wait_logs[0]

    # Verify propagation into [RETRIEVAL_MICRO_TIMING] in adapter._run_profile
    printed_markers: list[str] = []
    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter._safe_print_streaming_marker",
        lambda msg: printed_markers.append(msg),
    )
    mock_adapter_client = MagicMock()
    mock_adapter_client._persistent_applies.return_value = False
    mock_adapter_client.query_ready.return_value = q_res
    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter._SUBPROCESS_CLIENT",
        mock_adapter_client,
    )
    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.initialize_workspace_chat_rag_v2_worker",
        lambda *a, **kw: {"status": "ok"},
    )

    dummy_model = tmp_path / "dummy_bge_m3"
    dummy_model.mkdir(exist_ok=True)
    canary_cfg = WorkspaceChatRagV2CanaryConfig(
        bge_m3_model_path=dummy_model,
        bge_m3_model_revision="rev1",
        bge_m3_model_checksum="sha256:dummy",
    )
    src = WorkspaceAIContextSource(
        source_id="S-ARCH08",
        source_scope="notebook",
        source_type="plain_text",
        title="Doc ARCH08",
        privacy_label="local_only",
        text="Nội dung thử nghiệm ARCH-08",
        included_chars=27,
        truncated=False,
    )

    mapped = _run_profile(
        question="Câu hỏi kiểm tra pipe_connect_ms?",
        sources=(src,),
        config=canary_cfg,
        profile="bge_m3_hybrid",
        fallback_reason="",
        pipeline_factory=MagicMock(),
        domain_collection_id="lsu",
    )
    assert mapped["rag_v2_canary"]["pipe_wait_ms"] >= 1100.0
    micro_markers = [m for m in printed_markers if "[RETRIEVAL_MICRO_TIMING]" in m]
    assert len(micro_markers) == 1
    assert f"pipe_wait_ms={q_res['pipe_wait_ms']:.2f}" in micro_markers[0]


def test_arch13_atomic_status_file_nonblocking_readiness_and_fallback_equivalence(
    persist_env: pytest.MonkeyPatch,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ARCH-13: Verify atomic status file write, non-blocking readiness while pipe is busy,
    config mismatch detection, dead-PID detection, and fallback to legacy probe when status file is missing.
    """
    cfg = _make_query_config(tmp_path)
    cfg_mismatch = _make_query_config(tmp_path, retrieval_limit=99)
    client = BgeSubprocessWorkerClient()

    exchange_calls: list[dict[str, Any]] = []

    def _mock_exchange(c: RagV2DevConfig, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        exchange_calls.append(dict(payload))
        return {
            "status": "ok",
            "initialized": True,
            "configuration_matches": (c == cfg),
            "pid": os.getpid(),
            "readiness": {"pid": os.getpid(), "protocol_version": "1", "retrieval_profile": c.retrieval_profile},
        }

    monkeypatch.setattr(client, "_persistent_exchange", _mock_exchange)

    # 1. Without status file: falls back to legacy pipe probe
    status_path = status_file_for_config(cfg)
    remove_worker_status_file(cfg)
    assert not status_path.exists()

    legacy_probe = client.readiness(cfg)
    assert len(exchange_calls) == 1
    assert legacy_probe == {
        "ready": True,
        "alive": True,
        "configuration_matches": True,
        "reason": "",
        "pid": os.getpid(),
    }
    # And status file was atomically populated
    assert status_path.is_file()
    raw_status = json.loads(status_path.read_text(encoding="utf-8"))
    assert raw_status["pid"] == os.getpid()
    assert raw_status["initialized"] is True
    assert raw_status["config_fingerprint"] == config_fingerprint_for_worker(cfg)
    assert isinstance(raw_status["timestamp"], float)

    # 2. With valid status file: readiness() and is_ready() do NOT touch _persistent_exchange
    # even if _persistent_exchange would fail/block on a busy pipe!
    def _fail_if_pipe_touched(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Named Pipe must NOT be touched when valid status file exists!")

    monkeypatch.setattr(client, "_persistent_exchange", _fail_if_pipe_touched)

    t0 = time.perf_counter()
    fast_probe = client.readiness(cfg)
    fast_elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert fast_elapsed_ms < 25.0
    # Semantic equivalence: fast_probe dict is 100% identical to legacy_probe dict
    assert fast_probe == legacy_probe
    assert client.is_ready(cfg) is True

    # Also initialize_worker(cfg) returns reused=True immediately without touching pipe
    init_res = client.initialize_worker(cfg, timeout_s=5.0)
    assert init_res["status"] == "ok"
    assert init_res["reused"] is True
    assert init_res["readiness"]["pid"] == os.getpid()

    # 3. Config fingerprint mismatch in status file -> reports ready=False, configuration_matches=False
    status_data = json.loads(status_path.read_text(encoding="utf-8"))
    status_data["config_fingerprint"] = config_fingerprint_for_worker(cfg_mismatch)
    status_path.write_text(json.dumps(status_data), encoding="utf-8")

    mismatch_probe = client.readiness(cfg)
    assert mismatch_probe == {
        "ready": False,
        "alive": True,
        "configuration_matches": False,
        "reason": "bge_worker_configuration_mismatch",
        "pid": os.getpid(),
    }
    assert client.is_ready(cfg) is False

    # 4. Dead PID in status file -> cleans up stale status file and falls back to pipe probe
    status_data["config_fingerprint"] = config_fingerprint_for_worker(cfg)
    status_data["pid"] = 99999999  # non-existent PID
    assert _is_worker_pid_alive(99999999) is False
    status_path.write_text(json.dumps(status_data), encoding="utf-8")

    fallback_called = False

    def _fallback_exchange(c: RagV2DevConfig, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        nonlocal fallback_called
        fallback_called = True
        raise SemanticBackendError("bge_worker_persist_unavailable")

    monkeypatch.setattr(client, "_persistent_exchange", _fallback_exchange)
    dead_probe = client.readiness(cfg)
    assert fallback_called is True
    assert not status_path.exists(), "Stale status file for dead PID must be unlinked"
    assert dead_probe["ready"] is False
    assert dead_probe["alive"] is False


@pytest.mark.skipif(os.name != "nt", reason="Windows persistent worker test")
def test_arch13_real_persistent_worker_writes_status_file_and_nonblocking_when_pipe_busy(
    persist_env: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ARCH-13 + ARCH-08 E2E: Real persistent worker process writes status file on init;
    readiness/is_ready returns <10ms even while single-session Named Pipe is held busy.
    """
    doc = tmp_path / "doc_e2e.txt"
    doc.write_text("Kiểm tra lỗi C7620 hệ thống quang học LSU.", encoding="utf-8")
    spec = SourceSpec(path=doc, source_id="s_e2e", document_id="d_e2e")

    write_cfg = RagV2DevConfig(
        runtime_root=tmp_path / "runtime",
        index_filename="g3_test.sqlite",
        retrieval_profile="lexical",
    )
    pipeline = RagV2DevPipeline(write_cfg)
    try:
        pipeline.ingest([spec])
    finally:
        pipeline.close()

    cfg = _make_query_config(tmp_path)
    client = BgeSubprocessWorkerClient()
    status_path = status_file_for_config(cfg)
    try:
        init_report = client.initialize_worker(cfg, timeout_s=120.0)
        assert init_report["status"] == "ok"
        worker_pid = init_report["readiness"]["pid"]
        assert isinstance(worker_pid, int) and worker_pid > 0

        # Worker must have atomically written the status file upon init completion
        assert status_path.is_file()
        status_json = json.loads(status_path.read_text(encoding="utf-8"))
        assert status_json["pid"] == worker_pid
        assert status_json["initialized"] is True
        assert status_json["config_fingerprint"] == config_fingerprint_for_worker(cfg)
        assert status_json["timestamp"] > 0

        # Hold the single-session Named Pipe open from a raw client connection to simulate a busy worker
        pipe_name = pipe_name_for_config(cfg)
        busy_conn = mpc.Client(pipe_name, family="AF_PIPE", authkey=authkey_for_worker())
        try:
            # While busy_conn holds the single-session pipe, client.readiness(cfg) and client.is_ready(cfg)
            # must complete non-blockingly via status file in < 25ms (instead of blocking 4.0s on pipe!)
            t0 = time.perf_counter()
            probe_while_busy = client.readiness(cfg)
            busy_probe_ms = (time.perf_counter() - t0) * 1000.0
            assert busy_probe_ms < 25.0
            assert probe_while_busy == {
                "ready": True,
                "alive": True,
                "configuration_matches": True,
                "reason": "",
                "pid": worker_pid,
            }
            assert client.is_ready(cfg) is True
        finally:
            busy_conn.close()

        # Query worker and verify pipe_connect_ms / pipe_wait_ms metrics are returned
        q_res = client.query_ready("Lỗi C7620 là gì?", [spec], cfg, timeout_s=60.0)
        assert q_res["summary"]["returned_count"] >= 1
        assert "pipe_connect_ms" in q_res
        assert "pipe_wait_ms" in q_res
        assert "pipe_exec_ms" in q_res
        assert q_res["summary"]["pipe_wait_ms"] >= 0.0
    finally:
        client.shutdown_persistent_worker(cfg)
        client.close()
        assert not status_path.exists()

