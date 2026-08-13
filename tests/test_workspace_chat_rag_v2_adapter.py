from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
import aios_habit.workspace_chat_rag_v2_adapter as adapter
import aios_habit.workspace_chat_rag_v2_deployment as deployment_module


def _source(text: str, *, privacy_label: str = "local_only") -> WorkspaceAIContextSource:
    return WorkspaceAIContextSource(
        source_id="source-1",
        source_scope="temporary",
        source_type="pasted_text",
        title="owner-notes.txt",
        privacy_label=privacy_label,
        text=text,
        included_chars=len(text),
        truncated=False,
    )


@pytest.fixture(autouse=True)
def _close_canary_runtimes():
    adapter.close_workspace_chat_rag_v2_runtimes()
    yield
    adapter.close_workspace_chat_rag_v2_runtimes()


def test_canary_config_defaults_off_and_requires_explicit_enablement(monkeypatch):
    monkeypatch.setattr(
        adapter,
        "load_workspace_chat_rag_v2_deployment",
        lambda **_kwargs: None,
    )
    config = adapter.WorkspaceChatRagV2CanaryConfig.from_env({})

    assert config.enabled is False
    assert config.requested_profile == "bge_m3_hybrid"
    assert config.fail_closed_on_error is True
    assert not hasattr(config, "lexical_fallback_enabled")
    assert not hasattr(config, "semantic_progressive")


def test_feature_flag_off_returns_no_evidence(tmp_path: Path):
    source = _source("Nội dung chủ sở hữu chỉ xử lý cục bộ.")
    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=False,
        runtime_root=tmp_path,
    )

    result = adapter.retrieve_workspace_chat_evidence(
        "Câu hỏi",
        (source,),
        config=config,
    )

    assert result["retrieval_available"] is False
    assert result["summary_count"] == 0
    assert result["evidence_items"] == []
    assert result["rag_v2_canary"]["backend"] == "unavailable"


def test_missing_bge_pins_fail_closed_and_schedule_preparation(monkeypatch, tmp_path: Path):
    source = _source("ORCHID-731 là mã duy nhất của hồ sơ này.")
    executor = _ImmediateExecutor()
    monkeypatch.setattr(adapter, "_get_executor", lambda: executor)
    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        runtime_root=tmp_path,
    )

    result = adapter.retrieve_workspace_chat_evidence(
        "Mã dự án ORCHID-731 là gì?",
        (source,),
        config=config,
    )

    assert len(executor.submissions) == 1
    assert result["retrieval_available"] is False
    assert result["summary_count"] == 0
    assert result["rag_v2_canary"]["effective_profile"] == "unavailable"
    assert result["rag_v2_canary"]["fallback_applied"] is False
    assert not (tmp_path / "bge_m3_hybrid" / "workspace_chat.sqlite").exists()


def test_unprepared_query_remains_fail_closed_across_threads(monkeypatch, tmp_path: Path):
    source = _source("THREAD-882 là mã kiểm tra.")
    config = _semantic_config(tmp_path)
    executor = _ImmediateExecutor()
    monkeypatch.setattr(adapter, "_get_executor", lambda: executor)

    first = adapter.retrieve_workspace_chat_evidence("THREAD-882?", (source,), config=config)
    with ThreadPoolExecutor(max_workers=1) as callers:
        second = callers.submit(
            adapter.retrieve_workspace_chat_evidence,
            "THREAD-882?",
            (source,),
            config=config,
        ).result()

    assert first["retrieval_available"] is False
    assert second["retrieval_available"] is False
    assert len(executor.submissions) == 1
    assert adapter._RUNTIME_CACHE == {}


def test_changed_source_content_changes_preparation_key(tmp_path: Path):
    config = _semantic_config(tmp_path)
    first = _source("ALPHA-440 là trạng thái cũ.")
    updated = _source("BETA-991 là trạng thái mới.")

    assert adapter._preparation_key(config, first) != adapter._preparation_key(config, updated)


def test_runtime_cleanup_closes_and_evicts_cached_pipeline():
    assert adapter._RUNTIME_CACHE == {}
    adapter.close_workspace_chat_rag_v2_runtimes()
    assert adapter._RUNTIME_CACHE == {}


def test_runtime_cleanup_waits_for_background_preparation(monkeypatch):
    class RecordingExecutor:
        def __init__(self):
            self.wait = None

        def shutdown(self, *, wait):
            self.wait = wait

    executor = RecordingExecutor()
    monkeypatch.setattr(adapter, "_PREPARATION_EXECUTOR", executor)

    adapter.close_workspace_chat_rag_v2_runtimes()

    assert executor.wait is True
    assert adapter._PREPARATION_EXECUTOR is None


def test_failure_telemetry_does_not_expose_exception_text_or_paths(
    tmp_path: Path,
):
    secret_path = r"C:\private\owner\document.txt"
    source = _source("private owner text")
    config = _semantic_config(tmp_path)
    adapter.seed_workspace_chat_source_preparation(
        (source,),
        config=config,
        expected_source_fingerprints=[adapter._source_fingerprint(source)],
    )

    def failing_factory(_config):
        raise OSError(f"cannot open {secret_path}")

    result = adapter.retrieve_workspace_chat_evidence(
        "question",
        (source,),
        config=config,
        pipeline_factory=failing_factory,
    )

    telemetry = result["rag_v2_canary"]
    assert result["retrieval_available"] is False
    assert result["summary_count"] == 0
    assert telemetry["effective_profile"] == "unavailable"
    assert telemetry["fallback_applied"] is False
    assert secret_path not in str(telemetry)
    assert "private owner text" not in str(telemetry)


def test_adapter_keeps_provider_and_consent_outside_retrieval_boundary():
    source = Path("src/aios_habit/workspace_chat_rag_v2_adapter.py").read_text(
        encoding="utf-8"
    )
    app = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    assert "RealWorkspaceAIProviderClient" not in source
    assert "BrainGateway" not in source
    assert "provider_client" not in source
    assert "retrieve_workspace_chat_evidence as retrieve_local_evidence" in app
    assert "retrieve_local_evidence(q_text, packed_sources)" in app
    assert app.index("retrieve_local_evidence(q_text, packed_sources)") < app.index(
        "generate_workspace_ai_answer(req, RealWorkspaceAIProviderClient())"
    )


def test_activated_manifest_is_authoritative_over_legacy_environment(
    monkeypatch,
    tmp_path: Path,
):
    model_path = tmp_path / "approved-model"
    model_path.mkdir()
    deployment = SimpleNamespace(
        activated=True,
        requested_profile="bge_m3_hybrid",
        runtime_root=tmp_path / "production-runtime",
        model_path=model_path,
        model_revision="approved-revision",
        model_checksum="sha256:" + "a" * 64,
        retrieval_device="cpu",
    )
    monkeypatch.setattr(
        adapter,
        "load_workspace_chat_rag_v2_deployment",
        lambda **_kwargs: deployment,
    )

    config = adapter.WorkspaceChatRagV2CanaryConfig.from_env(
        {
            adapter.CANARY_ENABLED_ENV: "0",
            adapter.PROFILE_ENV: "lexical_baseline",
            adapter.BGE_MODEL_CHECKSUM_ENV: "sha256:" + "b" * 64,
        }
    )

    assert config.enabled is True
    assert config.requested_profile == "bge_m3_hybrid"
    assert config.bge_m3_model_checksum == deployment.model_checksum
    assert config.fail_closed_on_error is True


def test_invalid_activated_manifest_returns_no_evidence_without_legacy(
    monkeypatch,
):
    def fail_manifest(**_kwargs):
        raise adapter.DeploymentManifestError(
            r"checksum mismatch at C:\private\owner\model"
        )

    monkeypatch.setattr(adapter, "load_workspace_chat_rag_v2_deployment", fail_manifest)
    result = adapter.retrieve_workspace_chat_evidence(
        "question",
        (_source("private source contents"),),
    )

    assert result["summary_count"] == 0
    assert result["retrieval_available"] is False
    assert result["rag_v2_canary"]["backend"] == "unavailable"
    assert result["rag_v2_canary"]["fallback_applied"] is False
    assert "private" not in str(result["rag_v2_canary"])


def test_activated_runtime_failure_never_falls_back(tmp_path: Path):
    config = _semantic_config(tmp_path)
    source = _source("private source contents")
    adapter.seed_workspace_chat_source_preparation(
        (source,),
        config=config,
        expected_source_fingerprints=[adapter._source_fingerprint(source)],
    )

    def failing_factory(_config):
        raise OSError(r"cannot open C:\private\owner\model")

    result = adapter.retrieve_workspace_chat_evidence(
        "question",
        (source,),
        config=config,
        pipeline_factory=failing_factory,
    )

    assert result["summary_count"] == 0
    assert result["retrieval_available"] is False
    assert result["rag_v2_canary"]["effective_profile"] == "unavailable"
    assert result["rag_v2_canary"]["fallback_applied"] is False
    assert "private" not in str(result["rag_v2_canary"])


def test_staged_manifest_is_inert_even_before_all_activation_fields_exist(
    tmp_path: Path,
):
    manifest = tmp_path / "deployment.json"
    manifest.write_text(
        json.dumps({"schema_version": 2, "activation_state": "staged"}),
        encoding="utf-8",
    )

    loaded = deployment_module.load_workspace_chat_rag_v2_deployment(
        env={deployment_module.DEPLOYMENT_MANIFEST_ENV: str(manifest)},
        require_activated=True,
    )

    assert loaded is None


def test_activated_manifest_seals_evidence_and_benchmark_files(tmp_path: Path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"test model placeholder")
    runtime = (tmp_path / "production-runtime").resolve()
    runtime.mkdir()
    evidence_report = tmp_path / "selected_profile_report.json"
    evidence_report.write_text(
        json.dumps(
            {
                "status": "PASS",
                "qualification_passed": True,
                "qualification_id": deployment_module.EXPECTED_EVIDENCE_RUN_ID,
                "selected_profile": deployment_module.EXPECTED_PROFILE,
                "decision": "ADVANCE_TO_CANARY",
                "canary_allowed": True,
            }
        ),
        encoding="utf-8",
    )
    benchmark_report = tmp_path / "benchmark_report.json"
    benchmark_fields = {
        "status": "PASS",
        "runtime_root": str(runtime),
        "effective_profile": deployment_module.EXPECTED_PROFILE,
        "fallback_applied": False,
        "warm_p95_ms": 2100.0,
        "runtime_init_count": 1,
        "memory_safe": True,
    }
    benchmark_report.write_text(json.dumps(benchmark_fields), encoding="utf-8")
    manifest = tmp_path / "deployment.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "activation_state": "activated",
                "requested_profile": deployment_module.EXPECTED_PROFILE,
                "runtime": {"root": str(runtime)},
                "model": {
                    "path": str(model.resolve()),
                    "revision": deployment_module.EXPECTED_MODEL_REVISION,
                    "checksum": deployment_module.EXPECTED_MODEL_CHECKSUM,
                    "device": "cpu",
                },
                "policy": {
                    "lexical_fallback_enabled": False,
                    "semantic_progressive": False,
                    "fail_closed": True,
                },
                "evidence": {
                    "run_id": deployment_module.EXPECTED_EVIDENCE_RUN_ID,
                    "report_path": str(evidence_report),
                    "report_sha256": deployment_module.sha256_file(evidence_report),
                },
                "benchmark": {
                    **benchmark_fields,
                    "report_path": str(benchmark_report),
                    "report_sha256": deployment_module.sha256_file(benchmark_report),
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = deployment_module.load_workspace_chat_rag_v2_deployment(
        manifest,
        require_activated=True,
    )
    assert loaded is not None
    assert loaded.activated is True
    assert loaded.requested_profile == deployment_module.EXPECTED_PROFILE
    identity = deployment_module.production_candidate_identity(loaded)
    assert identity["requested_profile"] == deployment_module.EXPECTED_PROFILE
    assert identity["model_revision"] == deployment_module.EXPECTED_MODEL_REVISION
    assert identity["model_checksum"] == deployment_module.EXPECTED_MODEL_CHECKSUM
    assert identity["benchmark_status"] == "PASS"
    assert identity["identity_sha256"].startswith("sha256:")
    assert "model_path" not in identity
    assert "runtime_root" not in identity

    benchmark_report.write_text(
        json.dumps({**benchmark_fields, "warm_p95_ms": 2999.0}),
        encoding="utf-8",
    )
    with pytest.raises(
        deployment_module.DeploymentManifestError,
        match="deployment_benchmark_report_changed",
    ):
        deployment_module.load_workspace_chat_rag_v2_deployment(
            manifest,
            require_activated=True,
        )


def test_production_identity_rejects_inactive_deployment(tmp_path: Path):
    deployment = deployment_module.WorkspaceChatRagV2Deployment(
        manifest_path=tmp_path / "deployment.json",
        activation_state=deployment_module.STAGED_STATE,
        requested_profile=deployment_module.EXPECTED_PROFILE,
        runtime_root=tmp_path / "runtime",
        model_path=tmp_path / "model",
        model_revision=deployment_module.EXPECTED_MODEL_REVISION,
        model_checksum=deployment_module.EXPECTED_MODEL_CHECKSUM,
        retrieval_device="cpu",
        fail_closed=True,
        evidence_run_id=deployment_module.EXPECTED_EVIDENCE_RUN_ID,
        benchmark_status="PASS",
    )

    with pytest.raises(
        deployment_module.DeploymentManifestError,
        match="deployment_identity_requires_activated_manifest",
    ):
        deployment_module.production_candidate_identity(deployment)


def _enabled_config(tmp_path: Path, **overrides) -> adapter.WorkspaceChatRagV2CanaryConfig:
    values = {
        "enabled": True,
        "requested_profile": "bge_m3_hybrid",
        "runtime_root": tmp_path,
        "bge_m3_model_path": tmp_path / "pinned-bge-m3",
        "bge_m3_model_revision": "test-revision",
        "bge_m3_model_checksum": "sha256:" + "a" * 64,
        "fail_closed_on_error": True,
    }
    values.update(overrides)
    return adapter.WorkspaceChatRagV2CanaryConfig(**values)


class _ImmediateExecutor:
    def __init__(self):
        self.submissions = []

    def submit(self, fn, **kwargs):
        self.submissions.append((fn, kwargs))
        return SimpleNamespace()


def test_preparation_schedule_deduplicates_and_retry_is_explicit(monkeypatch, tmp_path):
    config = _enabled_config(tmp_path)
    source = _source("PREP-101 must be indexed once.")
    executor = _ImmediateExecutor()
    monkeypatch.setattr(adapter, "_get_executor", lambda: executor)

    with ThreadPoolExecutor(max_workers=8) as callers:
        futures = [
            callers.submit(
                adapter.schedule_workspace_chat_source_preparation,
                (source,),
                config=config,
            )
            for _ in range(24)
        ]
        for future in futures:
            future.result()

    assert len(executor.submissions) == 1
    assert adapter.get_workspace_chat_source_preparation_status(
        (source,), config=config
    ) == {"temporary:source-1": "pending"}

    key = adapter._preparation_key(config, source)
    adapter._PREPARATION_REGISTRY[key]["status"] = "failed"
    adapter.schedule_workspace_chat_source_preparation((source,), config=config)
    assert len(executor.submissions) == 1

    adapter.retry_workspace_chat_source_preparation((source,), config=config)
    assert len(executor.submissions) == 2
    assert adapter._PREPARATION_REGISTRY[key]["status"] == "pending"


def test_preparation_fingerprint_changes_for_content_privacy_and_config(tmp_path):
    source = _source("fingerprint content", privacy_label="local_only")
    changed_content = _source("fingerprint content changed", privacy_label="local_only")
    changed_privacy = _source("fingerprint content", privacy_label="cloud_safe")
    first_config = _enabled_config(tmp_path / "runtime-a")
    changed_config = _enabled_config(tmp_path / "runtime-b")

    keys = {
        adapter._preparation_key(first_config, source),
        adapter._preparation_key(first_config, changed_content),
        adapter._preparation_key(first_config, changed_privacy),
        adapter._preparation_key(changed_config, source),
    }

    assert len(keys) == 4


def test_preparation_status_identity_includes_scope(tmp_path):
    config = _enabled_config(tmp_path)
    temporary = _source("temporary text")
    notebook = WorkspaceAIContextSource(
        source_id=temporary.source_id,
        source_scope="notebook",
        source_type=temporary.source_type,
        title="notebook copy",
        privacy_label=temporary.privacy_label,
        text="notebook text",
        included_chars=len("notebook text"),
        truncated=False,
    )

    statuses = adapter.get_workspace_chat_source_preparation_status(
        (temporary, notebook), config=config
    )

    assert statuses == {
        "temporary:source-1": "not_prepared",
        "notebook:source-1": "not_prepared",
    }


def test_query_returns_no_evidence_while_semantic_is_queued(monkeypatch, tmp_path):
    config = _semantic_config(tmp_path)
    source = _source("READY-GATE-77 awaits semantic preparation.")
    executor = _ImmediateExecutor()
    monkeypatch.setattr(adapter, "_get_executor", lambda: executor)

    result = adapter.retrieve_workspace_chat_evidence(
        "What is READY-GATE-77?",
        (source,),
        config=config,
    )

    assert len(executor.submissions) == 1
    assert result["retrieval_available"] is False
    assert result["summary_count"] == 0
    assert result["rag_v2_canary"]["effective_profile"] == "unavailable"


def test_prepare_then_query_uses_prepared_registry(monkeypatch, tmp_path):
    config = _enabled_config(tmp_path)
    source = _source("PREPARED-808 is available after preparation.")

    class FakeReport:
        failed_count = 0
        unsupported_count = 0
        empty_count = 0
        converted_count = 1
        skipped_count = 0
        indexed_chunk_count = 1

    class FakePipeline:
        def ingest(self, _specs):
            return FakeReport()

        def close(self):
            pass

    result = adapter.prepare_workspace_chat_sources(
        (source,), config=config, pipeline_factory=lambda _config: FakePipeline()
    )

    assert result["status"] == "ok"
    assert adapter.get_workspace_chat_source_preparation_status(
        (source,), config=config
    ) == {"temporary:source-1": "ready"}


def _semantic_config(tmp_path: Path) -> adapter.WorkspaceChatRagV2CanaryConfig:
    return adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        requested_profile="bge_m3_hybrid",
        runtime_root=tmp_path,
        bge_m3_model_path=tmp_path / "pinned-bge-m3",
        bge_m3_model_revision="test-revision",
        bge_m3_model_checksum="sha256:" + "a" * 64,
        fail_closed_on_error=True,
    )


def _sources(count: int) -> tuple[WorkspaceAIContextSource, ...]:
    return tuple(
        WorkspaceAIContextSource(
            source_id=f"source-{index}", source_scope="temporary",
            source_type="pasted_text", title=f"source-{index}.txt",
            privacy_label="local_only", text=f"evidence {index}",
            included_chars=len(f"evidence {index}"), truncated=False,
        )
        for index in range(count)
    )


def test_semantic_preparation_uses_bounded_incremental_batches(monkeypatch, tmp_path):
    config = _semantic_config(tmp_path)
    sources = _sources(5)
    staged_documents: list[str] = []
    initialized: list[object] = []

    def initialize_worker(_config):
        initialized.append(_config)
        return {
            "status": "ok", "reused": False, "init_latency_ms": 12.5,
            "readiness": {
                "protocol_version": "1", "retrieval_profile": "bge_m3_hybrid",
                "model": {"model_id": "BAAI/bge-m3", "fingerprint": "model-fingerprint"},
            },
        }

    def prepare_staged_source(spec, _config, *, group_size):
        staged_documents.append(spec.document_id)
        assert group_size == 4
        return {
            "converted_count": 1, "skipped_count": 0,
            "failed_count": 0, "indexed_chunk_count": len(staged_documents) * 10,
        }

    monkeypatch.setattr(
        adapter._SUBPROCESS_CLIENT, "initialize_worker", initialize_worker
    )
    monkeypatch.setattr(
        adapter._SUBPROCESS_CLIENT, "prepare_staged_source", prepare_staged_source
    )

    result = adapter.prepare_workspace_chat_sources(sources, config=config)

    assert len(initialized) == 1
    assert len(staged_documents) == 5
    assert len(set(staged_documents)) == 5
    assert all(document_id.startswith("wsc-") for document_id in staged_documents)
    assert result["status"] == "ok"
    assert result["report"]["initialization"] == {
        "status": "ok", "reused": False, "init_latency_ms": 12.5,
        "readiness": {
            "protocol_version": "1", "retrieval_profile": "bge_m3_hybrid",
            "model": {"model_id": "BAAI/bge-m3", "fingerprint": "model-fingerprint"},
        },
    }
    assert result["prepared_count"] == 5
    assert {key: value for key, value in result["report"].items() if key != "initialization"} == {
        "converted_count": 5,
        "skipped_count": 0,
        "failed_count": 0,
        "indexed_chunk_count": 50,
        "batch_count": 5,
        "batch_size": 1,
    }
    assert set(adapter.get_workspace_chat_source_preparation_status(sources, config=config).values()) == {"ready"}


def test_semantic_preparation_batch_failure_leaves_all_sources_not_ready(monkeypatch, tmp_path):
    config = _semantic_config(tmp_path)
    sources = _sources(5)
    calls = 0

    def prepare_staged_source(_spec, _config, *, group_size):
        nonlocal calls
        assert group_size == 4
        calls += 1
        if calls == 2:
            raise RuntimeError("sensitive source details must stay private")
        return {
            "converted_count": 1, "skipped_count": 0,
            "failed_count": 0, "indexed_chunk_count": 10,
        }

    def initialize_worker(_config):
        return {"status": "ok", "reused": True, "init_latency_ms": 0.0}

    monkeypatch.setattr(
        adapter._SUBPROCESS_CLIENT, "initialize_worker", initialize_worker
    )
    monkeypatch.setattr(
        adapter._SUBPROCESS_CLIENT, "prepare_staged_source", prepare_staged_source
    )

    with pytest.raises(
        RuntimeError,
        match=r"^preparation_batch_002_document_[0-9a-f]{12}_runtimeerror$",
    ):
        adapter.prepare_workspace_chat_sources(sources, config=config)

    assert calls == 2
    assert set(adapter.get_workspace_chat_source_preparation_status(sources, config=config).values()) == {"failed"}
    for source in sources:
        entry = adapter._PREPARATION_REGISTRY[adapter._preparation_key(config, source)]
        assert entry["reason"] == "runtimeerror"
        assert "sensitive" not in str(entry)


def test_semantic_preparation_initialization_failure_is_phase_safe(monkeypatch, tmp_path):
    config = _semantic_config(tmp_path)
    sources = _sources(2)

    def initialize_worker(_config):
        raise adapter.SemanticBackendError("bge_worker_init_timeout")

    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "initialize_worker", initialize_worker)

    with pytest.raises(RuntimeError, match=r"^preparation_init_bge_worker_init_timeout$"):
        adapter.prepare_workspace_chat_sources(sources, config=config)

    assert set(adapter.get_workspace_chat_source_preparation_status(sources, config=config).values()) == {"failed"}
    for source in sources:
        entry = adapter._PREPARATION_REGISTRY[adapter._preparation_key(config, source)]
        assert entry["reason"] == "runtimeerror"


def test_batch_failure_reason_is_opaque_and_deterministic(tmp_path):
    config = _semantic_config(tmp_path)
    source = _sources(1)[0]
    spec = adapter._materialize_sources((source,), config.runtime_root)[0][0]

    reason = adapter._batch_failure_reason(7, (spec,), RuntimeError("private details"))

    assert reason.startswith("preparation_batch_007_document_")
    assert reason.endswith("_runtimeerror")
    assert source.source_id not in reason
    assert source.title not in reason
    assert source.text not in reason
    assert str(spec.path) not in reason


def test_query_config_is_read_only_and_uses_production_index(tmp_path):
    config = _semantic_config(tmp_path)

    preparation = adapter._pipeline_config(config, "bge_m3_hybrid")
    query = adapter._pipeline_config(
        config, "bge_m3_hybrid", read_only=True
    )

    assert preparation.index_read_only is False
    assert preparation.ensure_embeddings_on_open is True
    assert query.index_read_only is True
    assert query.ensure_embeddings_on_open is False
    assert query.index_path == preparation.index_path


def test_seeded_preparation_enables_read_only_query_without_preparing(tmp_path):
    config = _semantic_config(tmp_path)
    sources = _sources(2)
    fingerprints = [adapter._source_fingerprint(source) for source in sources]

    adapter.seed_workspace_chat_source_preparation(
        sources,
        config=config,
        expected_source_fingerprints=fingerprints,
    )

    assert set(
        adapter.get_workspace_chat_source_preparation_status(sources, config=config).values()
    ) == {"ready"}


def test_worker_initialization_accepts_staging_specific_timeout(tmp_path, monkeypatch):
    config = _semantic_config(tmp_path)
    observed = {}

    def initialize_worker(_config, *, timeout_s=300.0):
        observed["timeout_s"] = timeout_s
        return {"status": "ok", "reused": False, "init_latency_ms": 1.0, "readiness": {}}

    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "initialize_worker", initialize_worker)

    result = adapter.initialize_workspace_chat_rag_v2_worker(config, timeout_s=601.0)

    assert result["status"] == "ok"
    assert observed["timeout_s"] == 601.0


def test_structured_excel_query_routes_before_semantic_preparation(tmp_path, monkeypatch):
    from openpyxl import Workbook
    import aios_habit.workspace_chat_source_ingest as ingest

    managed_root = tmp_path / "managed_workbooks"
    managed_root.mkdir()
    workbook_path = managed_root / "sales.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sales"
    sheet.append(["Region", "Revenue"])
    sheet.append(["North", 10])
    sheet.append(["North", 20])
    sheet.append(["South", 5])
    workbook.save(workbook_path)
    monkeypatch.setattr(ingest, "MANAGED_WORKBOOK_ROOT", managed_root)
    monkeypatch.setattr(
        adapter,
        "schedule_workspace_chat_source_preparation",
        lambda *_args, **_kwargs: pytest.fail("semantic preparation should not run"),
    )
    source = WorkspaceAIContextSource(
        source_id="excel-source",
        source_scope="temporary",
        source_type="xlsx",
        title="sales.xlsx",
        privacy_label="machine_only",
        text="Region | Revenue",
        included_chars=16,
        truncated=False,
        managed_path=str(workbook_path.resolve()),
    )
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, runtime_root=tmp_path / "rag")

    result = adapter.retrieve_workspace_chat_evidence(
        "Tính tổng Revenue theo Region",
        (source,),
        config=config,
    )

    assert result["status"] == "structured_excel_query"
    assert result["rag_v2_canary"]["backend"] == "structured_excel_sqlite"
    assert result["summary_count"] == 1
    assert "North | 30" in result["evidence_items"][0]["text"]
    retrieved = result["retrieved_context_sources"][0]
    assert (retrieved.source_id, retrieved.source_scope) == ("excel-source", "temporary")
    assert retrieved.privacy_label == "machine_only"
def test_structured_excel_query_cites_all_contributing_sheets(tmp_path, monkeypatch):
    from openpyxl import Workbook
    import aios_habit.workspace_chat_source_ingest as ingest

    managed_root = tmp_path / "managed_workbooks"
    managed_root.mkdir()
    workbook_path = managed_root / "regional-sales.xlsx"
    workbook = Workbook()
    east = workbook.active
    east.title = "East"
    east.append(["Region", "Revenue"])
    east.append(["North", 10])
    west = workbook.create_sheet(title="West")
    west.append(["Region", "Revenue"])
    west.append(["South", 20])
    workbook.save(workbook_path)
    workbook.close()

    monkeypatch.setattr(ingest, "MANAGED_WORKBOOK_ROOT", managed_root)
    source = WorkspaceAIContextSource(
        source_id="regional-excel-source",
        source_scope="temporary",
        source_type="xlsx",
        title="regional-sales.xlsx",
        privacy_label="machine_only",
        text="Region | Revenue",
        included_chars=16,
        truncated=False,
        managed_path=str(workbook_path.resolve()),
    )
    config = adapter.WorkspaceChatRagV2CanaryConfig(enabled=True, runtime_root=tmp_path / "rag")

    result = adapter.retrieve_workspace_chat_evidence(
        "Tính tổng Revenue trên tất cả các sheet",
        (source,),
        config=config,
    )

    evidence = result["evidence_items"][0]
    assert result["status"] == "structured_excel_query"
    assert evidence["location_info"] == "Sheets: East, West"
    assert "Structured Excel result — multi-region (East, West)" in evidence["text"]
    assert result["citations"][0]["location"] == "Sheets: East, West"
