"""Focused tests for provider-free Workspace Chat Stage A staging."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from scripts import battle_notebooklm_rag_v2 as battle


def _source(index: int) -> WorkspaceAIContextSource:
    text = f"local evidence {index}"
    return WorkspaceAIContextSource(
        source_id=f"source-{index}",
        source_scope="test",
        source_type="pasted_text",
        title=f"private-{index}.txt",
        privacy_label="local_only",
        text=text,
        included_chars=len(text),
        truncated=False,
    )


def _args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        production_deployment_manifest=str(tmp_path / "activated.json"),
        source_root=str(tmp_path / "corpus"),
        privacy_label="local_only",
        allow_partial=False,
        workspace_stage_cache_dir=str(tmp_path / "stage-cache"),
        workspace_stage_init_timeout=30.0,
        workspace_stage_source_timeout=12.0,
    )


def _patch_stage_dependencies(monkeypatch: pytest.MonkeyPatch, sources: tuple[WorkspaceAIContextSource, ...]) -> None:
    monkeypatch.setattr(
        battle,
        "build_local_manifest",
        lambda *_args, **_kwargs: {"corpus_fingerprint": "corpus-hash"},
    )
    monkeypatch.setattr(
        battle,
        "_bound_production_identity",
        lambda *_args, **_kwargs: {"identity_sha256": "candidate-hash"},
    )
    monkeypatch.setattr(battle, "ingest_workspace_sources", lambda *_args, **_kwargs: (sources, {}))
    monkeypatch.setattr(battle, "workspace_production_adapter_config", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        battle,
        "initialize_workspace_chat_rag_v2_worker",
        lambda *_args, **_kwargs: {"status": "ok", "readiness": {}},
    )
    monkeypatch.setattr(battle, "close_workspace_chat_rag_v2_runtimes", lambda: None)


def test_workspace_stage_resumes_exact_checkpoint_without_repreparing_commits(monkeypatch, tmp_path):
    sources = (_source(0), _source(1), _source(2))
    _patch_stage_dependencies(monkeypatch, sources)
    calls: list[tuple[str, ...]] = []

    def interrupted_prepare(_sources, **kwargs):
        calls.append(tuple(kwargs["completed_document_ids"]))
        kwargs["progress_callback"]({
            "document_id": battle.workspace_stage_document_ids(sources)[0],
            "completed_count": 1,
            "total_sources": 3,
        })
        raise RuntimeError("preparation_batch_002_document_abc123_runtimeerror")

    monkeypatch.setattr(battle, "prepare_workspace_chat_sources", interrupted_prepare)
    args = _args(tmp_path)

    with pytest.raises(battle.BenchmarkError, match="document preparation failed"):
        battle.run_workspace_stage(args, tmp_path / "output")

    identity = battle.workspace_stage_identity(
        {"corpus_fingerprint": "corpus-hash"},
        {"identity_sha256": "candidate-hash"},
        battle.workspace_stage_source_fingerprints(sources),
    )
    checkpoint = tmp_path / "stage-cache" / identity["stage_key"] / "workspace_stage_checkpoint.json"
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["completed_document_ids"] == [battle.workspace_stage_document_ids(sources)[0]]
    assert "private-0" not in checkpoint.read_text(encoding="utf-8")

    def resumed_prepare(_sources, **kwargs):
        calls.append(tuple(kwargs["completed_document_ids"]))
        for index, document_id in enumerate(battle.workspace_stage_document_ids(sources)[1:], start=2):
            kwargs["progress_callback"]({
                "document_id": document_id,
                "completed_count": index,
                "total_sources": 3,
            })
        return {"status": "ok", "prepared_count": 3}

    monkeypatch.setattr(battle, "prepare_workspace_chat_sources", resumed_prepare)
    result = battle.run_workspace_stage(args, tmp_path / "output")

    assert calls == [(), (battle.workspace_stage_document_ids(sources)[0],)]
    assert result["status"] == "PASS"
    assert result["cache_status"] == "resumed"
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["status"] == "ready"


def test_workspace_stage_deadline_failure_is_checkpointed_and_never_ready(monkeypatch, tmp_path):
    sources = (_source(0),)
    _patch_stage_dependencies(monkeypatch, sources)
    received: dict[str, object] = {}

    def timed_out_prepare(_sources, **kwargs):
        received.update(kwargs)
        raise RuntimeError("preparation_batch_001_document_abc123_bge_worker_source_deadline_exceeded")

    monkeypatch.setattr(battle, "prepare_workspace_chat_sources", timed_out_prepare)
    args = _args(tmp_path)

    with pytest.raises(battle.BenchmarkError, match="document preparation failed"):
        battle.run_workspace_stage(args, tmp_path / "output")

    identity = battle.workspace_stage_identity(
        {"corpus_fingerprint": "corpus-hash"},
        {"identity_sha256": "candidate-hash"},
        battle.workspace_stage_source_fingerprints(sources),
    )
    stage_root = tmp_path / "stage-cache" / identity["stage_key"]
    checkpoint = json.loads((stage_root / "workspace_stage_checkpoint.json").read_text(encoding="utf-8"))
    assert received["source_timeout_s"] == 12.0
    assert checkpoint["status"] == "failed"
    assert checkpoint["last_error"] == "source_deadline_exceeded"
    assert not (stage_root / "workspace_stage_manifest.json").exists()


def test_workspace_stage_rejects_checkpoint_with_different_frozen_identity(tmp_path):
    checkpoint = tmp_path / "workspace_stage_checkpoint.json"
    document_ids = ("wsc-opaque",)
    battle.atomic_write_json(
        checkpoint,
        battle._workspace_stage_checkpoint(
            status="failed",
            identity={"stage_key": "old"},
            document_ids=document_ids,
            completed_document_ids=(),
        ),
    )

    with pytest.raises(battle.BenchmarkError, match="stale or identity-mismatched"):
        battle._load_workspace_stage_checkpoint(
            checkpoint,
            identity={"stage_key": "new"},
            document_ids=document_ids,
        )


def test_workspace_production_adapter_config_is_semantic_and_has_no_lexical_fallback(monkeypatch, tmp_path):
    deployment = SimpleNamespace(
        requested_profile="bge_m3_hybrid",
        runtime_root=tmp_path / "activated-runtime",
        model_path=tmp_path / "pinned-bge-m3",
        model_revision="test-revision",
        model_checksum="sha256:" + "a" * 64,
        retrieval_device="cpu",
        fail_closed=True,
        lexical_fallback_enabled=False,
    )
    monkeypatch.setattr(
        battle,
        "load_workspace_chat_rag_v2_deployment",
        lambda *_args, **_kwargs: deployment,
    )

    config = battle.workspace_production_adapter_config(
        str(tmp_path / "activated.json"),
        benchmark_runtime_root=tmp_path / "stage-runtime",
    )

    assert config.enabled is True
    assert config.requested_profile == "bge_m3_hybrid"
    assert config.fail_closed_on_error is True
    assert config.runtime_root == tmp_path / "stage-runtime"
