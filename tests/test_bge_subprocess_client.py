"""Unit tests for BGE subprocess client routing IPC and security invariants (T007)."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
import pytest

from aios_habit.rag_v2 import bge_subprocess_client as client_module
from aios_habit.rag_v2.bge_subprocess_client import BgeSubprocessWorkerClient
from aios_habit.rag_v2.pipeline import RagV2DevConfig, SourceSpec
from aios_habit.rag_v2.semantic import SemanticBackendError


def test_client_uses_project_venv_when_ui_interpreter_lacks_bge_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    project_python.parent.mkdir(parents=True)
    project_python.touch()
    monkeypatch.setattr(client_module, "_current_interpreter_supports_bge_runtime", lambda: False)
    monkeypatch.setattr(client_module, "_project_virtualenv_python", lambda: project_python)

    client = BgeSubprocessWorkerClient()

    assert client._python_executable == str(project_python)


def test_explicit_worker_interpreter_is_never_overridden() -> None:
    client = BgeSubprocessWorkerClient(python_executable="C:/custom/python.exe")

    assert client._python_executable == "C:/custom/python.exe"


def test_client_query_with_valid_routing_metadata(tmp_path: Path) -> None:
    doc_path = tmp_path / "doc.txt"
    doc_path.write_text("Dữ liệu thử nghiệm routing IPC", encoding="utf-8")
    config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
    spec = SourceSpec(path=doc_path, source_id="s1", document_id="d1")

    client = BgeSubprocessWorkerClient()
    try:
        client.initialize_worker(config)
        client.prepare_sources([spec], config)

        result = client.query(
            question="Dữ liệu thử nghiệm",
            specs=[spec],
            config=config,
            rerank_requested=False,
            routing_reason_codes=("pre_fast",),
            policy_version="adaptive-reranking-v1",
        )
        assert isinstance(result, dict)
        assert "routing" in result
        assert result["routing"]["reranker_requested"] is False
        assert result["routing"]["reranker_applied"] is False
        assert result["routing"]["effective_path"] in ("hybrid", "lexical")
        assert "doc.txt" not in str(result.get("routing"))
        assert "Dữ liệu thử nghiệm" not in str(result.get("routing"))
    finally:
        client.close()


def test_client_rejects_invalid_reason_codes_before_or_at_ipc(tmp_path: Path) -> None:
    doc_path = tmp_path / "doc.txt"
    doc_path.write_text("Test", encoding="utf-8")
    config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
    spec = SourceSpec(path=doc_path, source_id="s1", document_id="d1")

    client = BgeSubprocessWorkerClient()
    try:
        client.initialize_worker(config)
        client.prepare_sources([spec], config)

        # Invalid reason code that is not allow-listed
        with pytest.raises((SemanticBackendError, ValueError), match="(invalid_routing_reason_code|bge_worker_query_failed)"):
            client.query(
                question="Test",
                specs=[spec],
                config=config,
                rerank_requested=True,
                routing_reason_codes=("DISALLOWED_CODE_123",),
            )
    finally:
        client.close()


def test_client_enforces_bounded_deep_timeout(monkeypatch, tmp_path: Path) -> None:
    doc_path = tmp_path / "doc.txt"
    doc_path.write_text("Deep timeout test", encoding="utf-8")
    config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
    spec = SourceSpec(path=doc_path, source_id="s1", document_id="d1")

    client = BgeSubprocessWorkerClient()
    try:
        client.initialize_worker(config)
        client.prepare_sources([spec], config)

        # A valid budget must clear real lexical-query latency on the target
        # CPU-only host (measured 2.7-13.6 s/query on h410asrock, 2026-10-09;
        # the previous 5 s budget failed closed on valid queries).
        started = time.perf_counter()
        result = client.query(
            question="Deep timeout",
            specs=[spec],
            config=config,
            timeout_s=60.0,
            rerank_requested=False,
        )
        assert result is not None
        assert time.perf_counter() - started < 60.0

        # An impossible budget must fail closed within its bound instead of hanging.
        started = time.perf_counter()
        with pytest.raises(
            SemanticBackendError,
            match="bge_subprocess_worker_crashed|bge_worker_query_timeout",
        ):
            client.query(
                question="Deep timeout",
                specs=[spec],
                config=config,
                timeout_s=0.001,
                rerank_requested=False,
            )
        assert time.perf_counter() - started < 30.0
        assert client.is_alive() is False
    finally:
        client.close()
