"""Unit tests for the BGE Subprocess Worker and Client."""
from __future__ import annotations

from pathlib import Path
import tempfile
import pytest

from aios_habit.rag_v2 import bge_subprocess_client as worker_client_module
from aios_habit.rag_v2.bge_subprocess_client import BgeSubprocessWorkerClient
from aios_habit.rag_v2.pipeline import RagV2DevConfig, SourceSpec
from aios_habit.rag_v2.semantic import SemanticBackendError



def test_bge_worker_cold_start_has_five_minute_fail_closed_deadline() -> None:
    assert worker_client_module._INIT_TIMEOUT_SECONDS == 300.0


def test_bge_subprocess_worker_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        doc_path = tmp_path / "sample.txt"
        doc_path.write_text("Minh phu trach ticket ORCHID-731 va can kiem tra vao thu Hai.", encoding="utf-8")

        config = RagV2DevConfig(
            runtime_root=tmp_path / "runtime",
            retrieval_profile="lexical",
        )
        spec = SourceSpec(path=doc_path, source_id="src1", document_id="doc1")

        client = BgeSubprocessWorkerClient()
        try:
            assert client.is_alive() is False

            result = client.ingest_and_query(
                question="Ai phu trach ORCHID-731?",
                specs=[spec],
                config=config,
            )

            assert client.is_alive() is True
            assert isinstance(result, dict)
            assert "summary" in result
            assert "items" in result
            assert len(result["items"]) > 0

        finally:
            client.close()
            assert client.is_alive() is False


def test_bge_subprocess_worker_prepare_then_query() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        doc_path = tmp_path / "prepared.txt"
        doc_path.write_text(
            "PREP-202 duoc lap chi muc truoc khi nguoi dung dat cau hoi.",
            encoding="utf-8",
        )
        config = RagV2DevConfig(
            runtime_root=tmp_path / "runtime",
            retrieval_profile="lexical",
        )
        spec = SourceSpec(path=doc_path, source_id="prepared", document_id="prepared-doc")
        client = BgeSubprocessWorkerClient()
        try:
            readiness = client.initialize_worker(config)
            report = client.prepare_sources([spec], config)
            result = client.query("Ma PREP-202 la gi?", [spec], config)

            assert readiness["status"] == "ok"
            assert readiness["reused"] is False
            assert readiness["readiness"]["protocol_version"] == "1"
            assert "path" not in str(readiness["readiness"])
            assert "PREP-202" not in str(readiness["readiness"])
            assert report["failed_count"] == 0
            assert report["indexed_chunk_count"] >= 1
            assert result["summary"]["returned_count"] >= 1
            assert any("PREP-202" in item["text"] for item in result["items"])
        finally:
            client.close()


def test_prepare_requires_explicit_initialization() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        document = tmp_path / "source.txt"
        document.write_text("Bounded preparation must not hide cold start.", encoding="utf-8")
        config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
        spec = SourceSpec(path=document, source_id="source", document_id="source")
        client = BgeSubprocessWorkerClient()
        try:
            with pytest.raises(SemanticBackendError, match="bge_worker_prepare_not_initialized"):
                client.prepare_sources([spec], config)
            assert client.is_alive() is False
        finally:
            client.close()


def test_staged_prepare_enforces_one_deadline_across_worker_calls(monkeypatch, tmp_path) -> None:
    document = tmp_path / "source.txt"
    document.write_text("deadline test", encoding="utf-8")
    config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
    spec = SourceSpec(path=document, source_id="safe", document_id="safe-doc")
    client = BgeSubprocessWorkerClient()

    class AliveProcess:
        def poll(self):
            return None

    client._process = AliveProcess()  # type: ignore[assignment]
    client._active_config = config
    clock = iter((10.0, 10.0, 11.1))
    calls: list[tuple[str, float]] = []

    def send(request, *, timeout_s, phase):
        calls.append((phase, timeout_s))
        if phase == "stage":
            return {"status": "ok", "staged": {"status": "ready"}}
        return {"status": "ok"}

    monkeypatch.setattr(worker_client_module.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(client, "_send_request", send)
    monkeypatch.setattr(client, "_close_internal", lambda *args, **kwargs: None)

    with pytest.raises(SemanticBackendError, match="bge_worker_source_deadline_exceeded"):
        client.prepare_staged_source(spec, config, source_timeout_s=1.0)

    assert calls[0] == ("stage", 1.0)


def test_bge_subprocess_worker_crash_handling() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = RagV2DevConfig(
            runtime_root=tmp_path / "runtime",
            retrieval_profile="lexical",
        )
        client = BgeSubprocessWorkerClient()
        try:
            client.start_worker(config)
            assert client.is_alive() is True

            # Force terminate the underlying process to simulate a native crash / SIGKILL
            if client._process is not None:
                client._process.kill()
                client._process.wait()

            doc_path = tmp_path / "doc.txt"
            doc_path.write_text("Test content", encoding="utf-8")
            spec = SourceSpec(path=doc_path, source_id="src1", document_id="doc1")

            # Interactive query must fail fast; recovery belongs to startup/background work.
            with pytest.raises(SemanticBackendError, match="bge_worker_query_not_ready"):
                client.query(question="Test query", specs=[spec], config=config)
            assert client.is_alive() is False
        finally:
            client.close()


def test_query_never_starts_worker_and_reuses_explicit_worker(monkeypatch, tmp_path) -> None:
    document = tmp_path / "source.txt"
    document.write_text("WARM-101 is indexed before query.", encoding="utf-8")
    config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
    spec = SourceSpec(path=document, source_id="source", document_id="source")
    client = BgeSubprocessWorkerClient()
    starts = 0
    original_start = client._start_worker_locked

    def counted_start(*args, **kwargs):
        nonlocal starts
        starts += 1
        return original_start(*args, **kwargs)

    monkeypatch.setattr(client, "_start_worker_locked", counted_start)
    try:
        with pytest.raises(SemanticBackendError, match="bge_worker_query_not_ready"):
            client.query("WARM-101?", [spec], config)
        assert starts == 0

        client.initialize_worker(config)
        client.prepare_sources([spec], config)
        pid = client.readiness(config)["pid"]
        first = client.query("WARM-101?", [spec], config)
        second = client.query("WARM-101?", [spec], config)

        assert starts == 1
        assert client.readiness(config)["pid"] == pid
        assert first["summary"]["returned_count"] >= 1
        assert second["summary"]["returned_count"] >= 1
    finally:
        client.close()
