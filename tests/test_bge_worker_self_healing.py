"""Unit tests for BGE worker timeout constants and self-healing retry behavior (BGE-WORKER-FIX-HOME)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from aios_habit.rag_v2 import bge_subprocess_client as client_module
from aios_habit.rag_v2.bge_subprocess_client import BgeSubprocessWorkerClient
from aios_habit.rag_v2.pipeline import RagV2DevConfig, SourceSpec
from aios_habit.rag_v2.semantic import SemanticBackendError
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit import workspace_chat_rag_v2_adapter as adapter


def test_bge_worker_timeout_constants_nơi_trần_theo_số_đo() -> None:
    """Requirement 3a: Verify new timeout constants match diagnostic benchmark measurements."""
    assert client_module._INIT_TIMEOUT_SECONDS == 420.0
    assert client_module._PERSIST_SPAWN_WAIT_SECONDS == 360.0
    assert client_module.default_init_timeout_seconds() == 420.0


def test_bge_subprocess_client_clear_failure_reason() -> None:
    """Verify BgeSubprocessWorkerClient can track and clear failure reasons."""
    client = BgeSubprocessWorkerClient()
    client._last_failure_reason = "bge_worker_init_timeout"
    assert client._last_failure_reason == "bge_worker_init_timeout"

    client.clear_failure_reason()
    assert client._last_failure_reason == ""


def test_bge_worker_self_healing_retry_client_level(tmp_path: Path) -> None:
    """Requirement 3b: Client level retry: Attempt 1 times out -> Attempt 2 succeeds."""
    config = RagV2DevConfig(runtime_root=tmp_path / "runtime", retrieval_profile="lexical")
    client = BgeSubprocessWorkerClient()

    attempt = 0

    def mock_persistent_exchange(cfg, payload, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise SemanticBackendError("bge_worker_persist_timeout")
        return {
            "status": "ok",
            "readiness": {"pid": 9999, "initialized": True, "reused": False},
        }

    with patch.object(client, "_persistent_applies", return_value=True):
        with patch.object(client, "_persistent_exchange", side_effect=mock_persistent_exchange):
            # Attempt 1: times out
            with pytest.raises(SemanticBackendError, match="bge_worker_persist_timeout"):
                client.initialize_worker(config)
            assert client._last_failure_reason == "bge_worker_persist_timeout"

            # Self-healing: clear failure reason
            client.clear_failure_reason()
            assert client._last_failure_reason == ""

            # Attempt 2: succeeds and clears failure reason
            res = client.initialize_worker(config)
            assert res["status"] == "ok"
            assert res["readiness"]["pid"] == 9999
            assert client._last_failure_reason == ""


def test_adapter_self_healing_reconciles_timeout_errors(tmp_path: Path, monkeypatch) -> None:
    """Requirement 3c: Reconcile retries worker timeout errors and resets them to pending."""
    manifest_path = tmp_path / "deployment_manifest.json"
    manifest_path.write_text(
        '{"schema_version": "1", "activated_at": "2026-10-07T00:00:00Z", '
        '"retrieval_profile": "bge_m3_hybrid", "bge_m3_model_revision": "rev1", '
        '"bge_m3_model_path": "models/bge", "bge_m3_model_checksum": "sha", '
        '"runtime_root": "' + str(tmp_path).replace("\\", "/") + '"}',
        encoding="utf-8",
    )
    monkeypatch.setenv(adapter.LOCAL_PILOT_ENABLED_ENV, "1")
    monkeypatch.setenv(adapter.RUNTIME_ROOT_ENV, str(tmp_path))

    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        runtime_root=tmp_path,
        bge_m3_model_path=tmp_path / "model",
        bge_m3_model_revision="rev1",
        bge_m3_model_checksum="sha",
    )

    db_path = adapter._get_ledger_db_path(config)
    adapter._init_preparation_ledger_db(db_path)

    timeout_source = WorkspaceAIContextSource(
        source_id="src_timeout_1",
        # Temporary sources are the ones the ledger still prepares (notebook
        # sources are pre-indexed production documents and are marked ready
        # without enqueueing since APP-SOURCE-MODEL-PC0575 chang 2b).
        source_scope="temporary",
        source_type="plain_text",
        title="Doc with previous timeout",
        privacy_label="local_only",
        text="Content for test",
        included_chars=16,
        truncated=False,
    )

    # Insert row with worker persist timeout
    adapter._upsert_ledger_row(
        db_path,
        adapter.SourcePreparationLedgerRow(
            source_scope=timeout_source.source_scope,
            source_id=timeout_source.source_id,
            source_fingerprint=adapter._source_fingerprint(timeout_source),
            model_id="BAAI/bge-m3",
            model_revision=config.bge_m3_model_revision,
            state=adapter.PREP_STATE_FAILED,
            priority=adapter.PREP_PRIORITY_NORMAL,
            attempt_count=1,
            last_error="preparation_init_bge_worker_persist_timeout",
            document_id=adapter._document_id(timeout_source),
            created_at=10.0,
            updated_at=10.0,
        ),
    )

    # Reconcile should NOT skip it, but re-enqueue it as PENDING
    enqueued = adapter.reconcile_and_enqueue_workspace_chat_sources((timeout_source,), config=config)
    assert enqueued == 1
    row = adapter._load_ledger_row(db_path, timeout_source.source_scope, timeout_source.source_id)
    assert row is not None
    assert row.state == adapter.PREP_STATE_PENDING
    assert row.last_error == ""


def test_adapter_query_retry_after_worker_init_timeout(tmp_path: Path, monkeypatch) -> None:
    """Requirement 3b: Query turn 1 fails cleanly on worker timeout -> Query turn 2 retries and succeeds."""
    manifest_path = tmp_path / "deployment_manifest.json"
    manifest_path.write_text(
        '{"schema_version": "1", "activated_at": "2026-10-07T00:00:00Z", '
        '"retrieval_profile": "bge_m3_hybrid", "bge_m3_model_revision": "rev1", '
        '"bge_m3_model_path": "models/bge", "bge_m3_model_checksum": "sha", '
        '"runtime_root": "' + str(tmp_path).replace("\\", "/") + '"}',
        encoding="utf-8",
    )
    monkeypatch.setenv(adapter.LOCAL_PILOT_ENABLED_ENV, "1")
    monkeypatch.setenv(adapter.RUNTIME_ROOT_ENV, str(tmp_path))

    source = WorkspaceAIContextSource(
        source_id="src_ready_1",
        source_scope="notebook",
        source_type="plain_text",
        title="Ready Doc",
        privacy_label="local_only",
        text="Thông tin lỗi C7620 Magenta Black 70 dot.",
        included_chars=40,
        truncated=False,
    )

    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        runtime_root=tmp_path,
        bge_m3_model_path=tmp_path / "model",
        bge_m3_model_revision="rev1",
        bge_m3_model_checksum="sha",
    )

    db_path = adapter._get_ledger_db_path(config)
    adapter._init_preparation_ledger_db(db_path)
    adapter._upsert_ledger_row(
        db_path,
        adapter.SourcePreparationLedgerRow(
            source_scope=source.source_scope,
            source_id=source.source_id,
            source_fingerprint=adapter._source_fingerprint(source),
            model_id="BAAI/bge-m3",
            model_revision=config.bge_m3_model_revision,
            state=adapter.PREP_STATE_READY,
            priority=adapter.PREP_PRIORITY_NORMAL,
            attempt_count=0,
            last_error="",
            document_id=adapter._document_id(source),
            created_at=10.0,
            updated_at=10.0,
            model_fingerprint=adapter._expected_backend_fingerprint(config),
        ),
    )

    # Monkeypatch semantic readiness to return READY
    monkeypatch.setattr(adapter, "_semantic_readiness", lambda sources, cfg: (adapter._PREPARATION_READY_STATE, ""))

    attempt = 0

    def mock_init_worker(cfg, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise RuntimeError("preparation_init_bge_worker_persist_timeout")
        return {"status": "ok", "readiness": {"pid": 8888}}

    monkeypatch.setattr(adapter, "initialize_workspace_chat_rag_v2_worker", mock_init_worker)

    def mock_query_ready(*args, **kwargs):
        return {
            "items": [
                {
                    "text": "C7620 Magenta vs Black 70 dot",
                    "document_id": adapter._document_id(source),
                    "source_id": source.source_id,
                    "score": 0.95,
                    "page": None,
                    "sheet": None,
                    "cell_range": None,
                    "section_path": [],
                }
            ],
            "retrieved_context_sources": [source.source_id],
            "query_plan": {"question": "C7620"},
            "telemetry": {},
            "synthesis": {
                "answer": "Ngưỡng sai màu C7620 là 70 dot.",
                "grounded": True,
            },
        }

    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "query_ready", mock_query_ready)

    # Turn 1: Worker init times out -> returns quality_search_unavailable with specific timeout reason
    res1 = adapter.retrieve_workspace_chat_evidence(
        "C7620 ngưỡng bao nhiêu?",
        (source,),
        config=config,
    )
    assert res1["status"] == "quality_search_unavailable"
    assert res1["rag_v2_canary"]["fallback_reason"] == "preparation_init_bge_worker_persist_timeout"
    # Ensure failure reason on client was cleared for self-healing
    assert adapter._SUBPROCESS_CLIENT._last_failure_reason == ""

    # Turn 2: Worker succeeds on retry -> returns normal answers with evidence
    res2 = adapter.retrieve_workspace_chat_evidence(
        "C7620 ngưỡng bao nhiêu?",
        (source,),
        config=config,
    )
    assert res2.get("retrieval_applied") is True
    assert len(res2["evidence_items"]) > 0
    assert "70 dot" in res2["local_synthesis"]["answer"]
