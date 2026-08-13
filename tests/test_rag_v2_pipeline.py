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
    DeterministicRerankerBackend,
    SemanticBackendError,
    SemanticBackendUnavailable,
    SemanticModelDescriptor,
    UnavailableRerankerBackend,
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
    assert result.synthesis_result.abstention_reasons == ()
    assert result.synthesis_result.provider_used is False
    assert state["mode"] == "local_only"
    assert state["provider_used"] is False
    assert state["index_path"] == "rag_v2_dev.sqlite"
    assert str(source_path) not in str(state)


def test_pipeline_routes_cloud_safe_query_through_injected_validated_provider(tmp_path):
    source_path = tmp_path / "release.txt"
    source_path.write_text(
        "The current release marker identifies the approved second version.",
        encoding="utf-8",
    )
    source = SourceSpec(source_path, privacy_labels=("cloud_safe",))
    requests = []

    def provider(request):
        requests.append(request)
        return "- The current release marker identifies the approved second version [1]"

    with RagV2DevPipeline(
        _config(tmp_path),
        synthesis_provider=provider,
    ) as pipeline:
        pipeline.ingest([source])
        state = pipeline.inspect([source])
        result = pipeline.query("current release marker", [source])

    assert state["mode"] == "provider_capable"
    assert state["provider_configured"] is True
    assert state["provider_used"] is False
    assert len(requests) == 1
    assert requests[0].evidence_pack is result.evidence_pack
    assert result.provider_used is True
    assert result.route == "provider_validated"
    assert result.synthesis_result.provider_used is True
    assert result.synthesis_result.citation_ids == ("[1]",)


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
    assert report.failed_count == 1
    assert report.unsupported_count == 1
    assert report.empty_count == 0
    assert report.indexed_chunk_count == 0
    assert [item.status for item in report.items] == ["disabled", "failed", "unsupported"]
    assert report.items[-1].warning_codes == ("unsupported_file_type",)
    assert blocked.evidence_pack.item_count == 0


def test_pipeline_classifies_empty_extraction_without_counting_it_usable(tmp_path):
    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("", encoding="utf-8")

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        report = pipeline.ingest([SourceSpec(empty_path)])

    assert report.converted_count == 0
    assert report.empty_count == 1
    assert report.failed_count == 0
    assert report.unsupported_count == 0
    assert report.indexed_chunk_count == 0
    assert report.items[0].status == "empty"
    assert report.items[0].warning_codes == ("empty_extracted_content",)


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


def test_pipeline_activates_hybrid_fusion_and_reports_ranking_profile(tmp_path):
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
        source = SourceSpec(source_path)
        pipeline.ingest([source])
        result = pipeline.query("semantic local evidence", [source])
        state = pipeline.inspect()

    retrieval = state["retrieval"]
    assert retrieval["requested_profile"] == "hybrid"
    assert retrieval["effective_profile"] == "hybrid"
    assert retrieval["degraded"] is False
    assert retrieval["degraded_reason"] == ""
    assert retrieval["semantic"]["available"] is True
    assert retrieval["semantic"]["embedded_chunk_count"] == 1
    assert retrieval["ranking"]["rrf_k"] == config.rrf_k
    assert result.search_response.summary.candidate_backend == "hybrid_rrf"
    assert result.search_response.results[0].ranking_signals["final_rank"] == 1.0


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


def test_pipeline_reranker_capability_degrades_or_fails_strict_preflight(tmp_path):
    embedding = DeterministicEmbeddingBackend(dimension=8)
    unavailable = UnavailableRerankerBackend(
        "reranker model is not cached locally",
        SemanticModelDescriptor(
            model_id="missing/reranker",
            revision="v1",
            runtime="deterministic-test",
            dimension=1,
            normalized=False,
        ),
    )
    degraded_config = _config(
        tmp_path,
        retrieval_profile="hybrid_rerank",
        embedding_model_id=embedding.descriptor.model_id,
        embedding_dimension=embedding.descriptor.dimension,
        reranker_model_id="missing/reranker",
    )
    with RagV2DevPipeline(
        degraded_config,
        embedding_backend=embedding,
        reranker_backend=unavailable,
    ) as pipeline:
        state = pipeline.inspect()

    assert state["retrieval"]["effective_profile"] == "hybrid"
    assert state["retrieval"]["degraded"] is True
    assert state["retrieval"]["degraded_reason"] == "reranker model is not cached locally"
    assert state["retrieval"]["reranker"]["available"] is False

    strict_config = _config(
        tmp_path,
        retrieval_profile="hybrid_rerank",
        embedding_model_id=embedding.descriptor.model_id,
        embedding_dimension=embedding.descriptor.dimension,
        reranker_model_id="missing/reranker",
        strict_semantic=True,
    )
    with pytest.raises(SemanticBackendUnavailable, match="reranker model"):
        RagV2DevPipeline(
            strict_config,
            embedding_backend=embedding,
            reranker_backend=unavailable,
        )


def test_pipeline_hybrid_rerank_uses_injected_local_cross_encoder(tmp_path):
    source_path = tmp_path / "guide.txt"
    source_path.write_text("alpha beta complete local evidence", encoding="utf-8")
    embedding = DeterministicEmbeddingBackend(dimension=8)
    reranker = DeterministicRerankerBackend()
    config = _config(
        tmp_path,
        retrieval_profile="hybrid_rerank",
        embedding_model_id=embedding.descriptor.model_id,
        embedding_dimension=embedding.descriptor.dimension,
        reranker_model_id=reranker.descriptor.model_id,
    )

    with RagV2DevPipeline(
        config,
        embedding_backend=embedding,
        reranker_backend=reranker,
    ) as pipeline:
        source = SourceSpec(source_path)
        pipeline.ingest([source])
        result = pipeline.query("alpha beta", [source])
        state = pipeline.inspect()

    assert state["retrieval"]["effective_profile"] == "hybrid_rerank"
    assert state["retrieval"]["degraded"] is False
    assert state["retrieval"]["reranker"]["available"] is True
    assert result.search_response.summary.candidate_backend == "hybrid_rrf_rerank"
    assert "reranker_score" in result.search_response.results[0].ranking_signals


def test_pipeline_runtime_reranker_failure_retries_hybrid_and_reports_degradation(tmp_path):
    class FailingReranker(DeterministicRerankerBackend):
        def score_pairs(self, pairs):
            del pairs
            raise SemanticBackendError("synthetic reranker inference failure")

    source_path = tmp_path / "guide.txt"
    source_path.write_text("alpha beta local evidence", encoding="utf-8")
    embedding = DeterministicEmbeddingBackend(dimension=8)
    reranker = FailingReranker()
    config = _config(
        tmp_path,
        retrieval_profile="hybrid_rerank",
        embedding_model_id=embedding.descriptor.model_id,
        embedding_dimension=embedding.descriptor.dimension,
        reranker_model_id=reranker.descriptor.model_id,
    )

    with RagV2DevPipeline(
        config,
        embedding_backend=embedding,
        reranker_backend=reranker,
    ) as pipeline:
        source = SourceSpec(source_path)
        pipeline.ingest([source])
        result = pipeline.query("alpha beta", [source])
        state = pipeline.inspect()

    assert result.search_response.summary.candidate_backend == "hybrid_rrf"
    assert state["retrieval"]["effective_profile"] == "hybrid"
    assert state["retrieval"]["degraded"] is True
    assert state["retrieval"]["degraded_reason"] == "synthetic reranker inference failure"


def test_index_build_compatibility_excludes_query_time_and_reranker_tuning(tmp_path):
    base = _config(
        tmp_path,
        retrieval_profile="bge_m3_hybrid_rerank",
        bge_m3_model_path=tmp_path / "bge-m3",
        bge_m3_model_revision="model-revision",
        bge_m3_model_checksum="sha256:model",
        retrieval_limit=10,
        candidate_limit=100,
        dense_candidate_limit=100,
        rerank_limit=30,
        reranker_model_id="reranker/a",
        rrf_k=60,
        context_neighbor_window=1,
    )
    tuned = _config(
        tmp_path,
        retrieval_profile="bge_m3_hybrid_rerank_expand",
        bge_m3_model_path=tmp_path / "bge-m3",
        bge_m3_model_revision="model-revision",
        bge_m3_model_checksum="sha256:model",
        retrieval_limit=25,
        candidate_limit=250,
        dense_candidate_limit=200,
        rerank_limit=80,
        reranker_model_id="reranker/b",
        rrf_k=90,
        lexical_channel_weight=2.0,
        dense_channel_weight=1.5,
        sparse_channel_weight=0.5,
        context_neighbor_window=3,
        context_parent_limit=4,
    )

    assert tuned.index_build_compatibility() == base.index_build_compatibility()


def test_index_build_compatibility_invalidates_index_producing_changes(tmp_path):
    common = {
        "retrieval_profile": "bge_m3_hybrid",
        "bge_m3_model_path": tmp_path / "bge-m3",
        "bge_m3_model_revision": "model-revision",
        "bge_m3_model_checksum": "sha256:model",
    }
    base = _config(tmp_path, **common).index_build_compatibility()
    changed_chunking = _config(
        tmp_path,
        **{**common, "max_chunk_chars": 121},
    ).index_build_compatibility()
    changed_model = _config(
        tmp_path,
        **{**common, "bge_m3_model_revision": "other-revision"},
    ).index_build_compatibility()
    changed_privacy = _config(
        tmp_path,
        **{**common, "allowed_privacy_labels": ("public",)},
    ).index_build_compatibility()
    changed_sparse_requirement = _config(
        tmp_path,
        **{**common, "retrieval_profile": "bge_m3_dense"},
    ).index_build_compatibility()

    assert base["compatibility_hash"] == _config(
        tmp_path,
        **common,
    ).index_build_compatibility()["compatibility_hash"]
    assert changed_chunking["compatibility_hash"] != base["compatibility_hash"]
    assert changed_model["compatibility_hash"] != base["compatibility_hash"]
    assert changed_privacy["compatibility_hash"] != base["compatibility_hash"]
    assert changed_sparse_requirement["compatibility_hash"] != base["compatibility_hash"]


def test_pipeline_resumes_partial_semantic_index_without_reembedding_completed_source(tmp_path):
    first_path = tmp_path / "first.txt"
    second_path = tmp_path / "second.txt"
    first_path.write_text("first semantic source", encoding="utf-8")
    second_path.write_text("second semantic source", encoding="utf-8")
    first_source = SourceSpec(first_path, document_id="doc-first")
    second_source = SourceSpec(second_path, document_id="doc-second")
    first_backend = DeterministicEmbeddingBackend(dimension=8)
    config = _config(
        tmp_path,
        retrieval_profile="hybrid",
        embedding_model_id=first_backend.descriptor.model_id,
        embedding_dimension=first_backend.descriptor.dimension,
        ensure_embeddings_on_open=False,
    )

    with RagV2DevPipeline(config, embedding_backend=first_backend) as pipeline:
        interrupted = pipeline.ingest([first_source])

    resumed_backend = DeterministicEmbeddingBackend(dimension=8)
    with RagV2DevPipeline(config, embedding_backend=resumed_backend) as pipeline:
        resumed = pipeline.ingest([first_source, second_source])
        expected = {
            item.document_id: item.source_fingerprint
            for item in resumed.items
            if item.chunk_count > 0
        }
        verification = pipeline.index.verify_index_coverage(
            sparse_required=True,
            expected_document_fingerprints=expected,
        )

    assert interrupted.converted_count == 1
    assert first_backend.embedded_document_count == 1
    assert resumed.skipped_count == 1
    assert resumed.converted_count == 1
    assert resumed.indexed_chunk_count == 2
    assert resumed_backend.embedded_document_count == 1
    assert verification["valid"] is True
    assert verification["document_count"] == 2
    assert verification["dense_embedding_count"] == 2
    assert verification["sparse_embedding_count"] == 2
