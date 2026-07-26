from pathlib import Path

import pytest

from aios_habit.rag_v2 import (
    EvidenceConfidence,
    RagV2DevConfig,
    RagV2DevPipeline,
    SourceSpec,
)
from aios_habit.rag_v2.semantic import (
    DeterministicEmbeddingBackend,
    SemanticBackendUnavailable,
    unavailable_embedding_backend,
)


def _config(tmp_path, **overrides):
    values = {"runtime_root": tmp_path / "runtime", "max_chunk_chars": 120}
    values.update(overrides)
    return RagV2DevConfig(**values)


def test_pipeline_ingests_queries_and_skips_unchanged_source(tmp_path):
    source_path = tmp_path / "guide.txt"
    source_path.write_text("Local evidence describes a bounded release checklist.", encoding="utf-8")
    source = SourceSpec(source_path)

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        first = pipeline.ingest([source])
        second = pipeline.ingest([source])
        result = pipeline.query("bounded release checklist", [source])
        state = pipeline.inspect([source])

    assert first.converted_count == 1
    assert first.failed_count == 0
    assert first.indexed_chunk_count == 1
    assert second.skipped_count == 1
    assert result.provider_used is False
    assert result.route == "local_retrieval_evidence"
    assert result.evidence_pack.items[0].source_name == "guide.txt"
    assert result.evidence_pack.confidence != EvidenceConfidence.INSUFFICIENT
    assert result.synthesis_result.grounded is True
    assert result.synthesis_result.abstained is False
    assert result.synthesis_result.citation_ids == ("[1]",)
    assert result.synthesis_result.provider_used is False
    assert state["mode"] == "local_only"
    assert state["provider_used"] is False
    assert state["index_path"] == "rag_v2_dev.sqlite"
    assert str(source_path) not in str(state)


def test_pipeline_reindex_atomically_removes_old_chunks(tmp_path):
    source_path = tmp_path / "notes.txt"
    source_path.write_text("obsolete marker from the first version", encoding="utf-8")
    source = SourceSpec(source_path, document_id="stable-document")

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        first = pipeline.ingest([source])
        assert pipeline.query("obsolete marker", [source]).evidence_pack.item_count == 1

        source_path.write_text("current marker from the second version", encoding="utf-8")
        stale = pipeline.query("obsolete marker", [source])
        second = pipeline.ingest([source])
        old = pipeline.query("obsolete", [source])
        current = pipeline.query("current marker", [source])

    assert first.indexed_chunk_count == 1
    assert stale.evidence_pack.item_count == 0
    assert stale.synthesis_result.abstained is True
    assert stale.synthesis_result.grounded is False
    assert "stale_fingerprint_excluded_all_chunks" in stale.evidence_pack.insufficiency_reasons
    assert second.converted_count == 1
    assert second.indexed_chunk_count == 1
    assert old.evidence_pack.item_count == 0
    assert old.synthesis_result.abstained is True
    assert current.evidence_pack.item_count == 1
    assert current.synthesis_result.grounded is True


def test_pipeline_reports_disabled_missing_and_unsupported_sources_fail_soft(tmp_path):
    disabled_path = tmp_path / "disabled.txt"
    disabled_path.write_text("must not be indexed", encoding="utf-8")
    unsupported_path = tmp_path / "binary.unknown"
    unsupported_path.write_bytes(b"opaque")
    sources = [
        SourceSpec(disabled_path, enabled=False),
        SourceSpec(tmp_path / "missing.txt"),
        SourceSpec(unsupported_path),
    ]

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        report = pipeline.ingest(sources)
        blocked = pipeline.query("must not be indexed", sources)

    assert report.disabled_count == 1
    assert report.failed_count == 2
    assert report.indexed_chunk_count == 0
    assert [item.status for item in report.items] == ["disabled", "failed", "failed"]
    assert blocked.evidence_pack.item_count == 0


def test_pipeline_privacy_filter_is_applied_before_evidence(tmp_path):
    source_path = tmp_path / "private.txt"
    source_path.write_text("restricted local evidence", encoding="utf-8")
    source = SourceSpec(source_path, privacy_labels=("local_only",))
    config = _config(tmp_path, allowed_privacy_labels=("cloud_safe",))

    with RagV2DevPipeline(config) as pipeline:
        pipeline.ingest([source])
        result = pipeline.query("restricted evidence", [source])

    assert result.evidence_pack.item_count == 0
    assert "privacy_filter_excluded_all_chunks" in result.evidence_pack.insufficiency_reasons


def test_pipeline_defaults_local_and_rejects_network_or_unknown_labels(tmp_path):
    source = SourceSpec(tmp_path / "anything.txt")
    assert source.privacy_labels == ("local_only",)
    assert RagV2DevConfig(runtime_root=tmp_path / "runtime").enable_network is False

    with pytest.raises(ValueError, match="local-only"):
        RagV2DevConfig(runtime_root=tmp_path / "runtime", enable_network=True)
    with pytest.raises(ValueError, match="canonical"):
        SourceSpec(tmp_path / "anything.txt", privacy_labels=("unclassified",))


def test_pipeline_default_lexical_profile_never_constructs_fastembed(tmp_path, monkeypatch):
    import aios_habit.rag_v2.pipeline as pipeline_module

    def fail_if_constructed(*args, **kwargs):
        del args, kwargs
        raise AssertionError("FastEmbed must not initialize for lexical profile")

    monkeypatch.setattr(pipeline_module, "FastEmbedEmbeddingBackend", fail_if_constructed)
    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        state = pipeline.inspect()

    assert state["retrieval"]["requested_profile"] == "lexical"
    assert state["retrieval"]["effective_profile"] == "lexical"
    assert state["retrieval"]["degraded"] is False
    assert state["retrieval"]["semantic"]["configured"] is False


def test_pipeline_prepares_dense_backend_without_claiming_gate_d_fusion(tmp_path):
    source_path = tmp_path / "guide.txt"
    source_path.write_text("semantic local evidence", encoding="utf-8")
    backend = DeterministicEmbeddingBackend(dimension=8)
    config = _config(
        tmp_path,
        retrieval_profile="hybrid",
        embedding_model_id=backend.descriptor.model_id,
        embedding_dimension=backend.descriptor.dimension,
    )

    with RagV2DevPipeline(config, embedding_backend=backend) as pipeline:
        pipeline.ingest([SourceSpec(source_path)])
        state = pipeline.inspect()

    retrieval = state["retrieval"]
    assert retrieval["requested_profile"] == "hybrid"
    assert retrieval["effective_profile"] == "lexical"
    assert retrieval["degraded"] is True
    assert retrieval["degraded_reason"] == "cross_channel_fusion_pending_gate_d"
    assert retrieval["semantic"]["available"] is True
    assert retrieval["semantic"]["embedded_chunk_count"] == 1


def test_pipeline_reports_unavailable_semantic_backend_or_fails_strict_preflight(tmp_path):
    backend = unavailable_embedding_backend(
        "missing/model",
        dimension=8,
        reason="model is not cached locally",
    )
    degraded_config = _config(
        tmp_path,
        retrieval_profile="hybrid",
        embedding_model_id="missing/model",
        embedding_dimension=8,
    )
    with RagV2DevPipeline(degraded_config, embedding_backend=backend) as pipeline:
        state = pipeline.inspect()

    assert state["retrieval"]["effective_profile"] == "lexical"
    assert state["retrieval"]["degraded"] is True
    assert state["retrieval"]["degraded_reason"] == "model is not cached locally"

    strict_config = _config(
        tmp_path,
        retrieval_profile="hybrid",
        embedding_model_id="missing/model",
        embedding_dimension=8,
        strict_semantic=True,
    )
    with pytest.raises(SemanticBackendUnavailable, match="not cached"):
        RagV2DevPipeline(strict_config, embedding_backend=backend)
