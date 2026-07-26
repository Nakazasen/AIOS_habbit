from pathlib import Path

import pytest

from aios_habit.rag_v2 import (
    EvidenceConfidence,
    RagV2DevConfig,
    RagV2DevPipeline,
    SourceSpec,
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
