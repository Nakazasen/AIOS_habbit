from pathlib import Path

import pytest

from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus
from aios_habit.rag_v2.chunk_revisions import ChunkRevisionStore
from aios_habit.rag_v2.chunk_upload_config import UploadChunkConfig, validate_upload_config
from aios_habit.rag_v2.chunking import (
    LitePilotConfig,
    StructureAwareChunker,
    apply_lite_pilot_filter,
    choose_chunk_style,
    lite_strategy_id,
    profile_elements,
)


def make_element(**overrides):
    data = {
        "element_id": "e1",
        "document_id": "doc1",
        "source_path": "/tmp/source.txt",
        "source_name": "source.txt",
        "file_type": "txt",
        "extractor": "unit",
        "extraction_status": ExtractionStatus.SUCCESS,
        "element_type": ElementType.TEXT,
        "text": "alpha beta gamma",
        "privacy_labels": ("private",),
        "source_fingerprint": "fp1",
        "section_path": ("Intro",),
    }
    data.update(overrides)
    return DocumentElement(**data)


def test_profiler_prefers_heading_then_falls_back_on_validator():
    elements = [make_element(section_path=("A", "B"), text="# Title\nbody")]
    profile = profile_elements(elements * 3)
    picked = choose_chunk_style(profile)
    assert picked["style"] == "heading"
    fallback = choose_chunk_style(profile, single_line_chunks=250)
    assert fallback["style"] == "recursive"


def test_lite_filter_keeps_baseline_when_disabled():
    chunker = StructureAwareChunker(max_chars=100)
    text = " ".join(f"word{i}" for i in range(80))
    chunks = chunker.chunk_elements([make_element(text=text)])
    assert any(not chunk.retrievable for chunk in chunks)
    kept = apply_lite_pilot_filter(chunks, LitePilotConfig(enabled=False), page_count=2)
    assert kept == chunks


def test_lite_filter_drops_parents_for_short_docs_only():
    chunker = StructureAwareChunker(max_chars=100)
    text = " ".join(f"word{i}" for i in range(80))
    chunks = chunker.chunk_elements([make_element(text=text)])
    short_kept = apply_lite_pilot_filter(
        chunks, LitePilotConfig(enabled=True), page_count=2
    )
    assert short_kept and all(chunk.retrievable for chunk in short_kept)
    long_kept = apply_lite_pilot_filter(
        chunks, LitePilotConfig(enabled=True), page_count=12
    )
    assert long_kept == chunks


def test_upload_config_validation_cpu_guards():
    ok = validate_upload_config(UploadChunkConfig(parser="office", max_chars=900))
    assert ok["graph_workers"] == 1
    with pytest.raises(ValueError):
        validate_upload_config(UploadChunkConfig(max_chars=5000))
    with pytest.raises(ValueError):
        validate_upload_config(UploadChunkConfig(graph_workers=8))


def test_revision_edit_history_and_rollback(tmp_path: Path):
    store = ChunkRevisionStore.load(tmp_path / "revisions.jsonl")
    first = store.edit("c1", "dong mot", note="sua loi")
    second = store.edit("c1", "dong mot sua", note="bo sung")
    assert (first.version, second.version) == (1, 2)
    assert "dong mot" in store.diff("c1", 1, 2)
    rolled = store.rollback("c1", 1)
    assert rolled.version == 3
    assert rolled.text == "dong mot"
    assert len(store.history("c1")) == 3


def test_strategy_id_stable_and_versioned():
    config = LitePilotConfig(enabled=True)
    assert lite_strategy_id(config, "heading") == lite_strategy_id(config, "heading")
    assert lite_strategy_id(config, "heading").startswith("lite-e5-v1:heading:")


def test_pipeline_pilot_tags_strategy_and_limits_parents(tmp_path: Path):
    from aios_habit.rag_v2.pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec

    source_path = tmp_path / "long.txt"
    source_path.write_text(" ".join(f"word{i} doan van dai" for i in range(400)), encoding="utf-8")
    base = RagV2DevConfig(runtime_root=tmp_path / "base", max_chunk_chars=120)
    pilot = RagV2DevConfig(
        runtime_root=tmp_path / "pilot",
        max_chunk_chars=120,
        lite_pilot_enabled=True,
        lite_long_doc_pages=10,
    )
    assert base.index_build_compatibility()["compatibility_hash"] != pilot.index_build_compatibility()["compatibility_hash"]
    with RagV2DevPipeline(base) as pipe_base:
        pipe_base.ingest([SourceSpec(source_path)])
        base_count = pipe_base.index.count()
    with RagV2DevPipeline(pilot) as pipe_pilot:
        report = pipe_pilot.ingest([SourceSpec(source_path)])
        assert report.converted_count == 1
        assert pipe_pilot.index.count() <= base_count


def test_evidence_dedup_and_detailed_guard():
    from aios_habit.rag_v2.evidence import build_evidence_pack, dedup_diverse_results
    from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
    from aios_habit.rag_v2.query_planning import coerce_query_plan

    def make_result(chunk_id, text, role):
        return SearchResult(
            chunk_id=chunk_id,
            score=1.0,
            text=text,
            document_id="doc1",
            source_path="/tmp/a.txt",
            source_name="a.txt",
            file_type="txt",
            metadata={"representation_role": role},
            privacy_labels=("local_only",),
        )

    dupes = (
        make_result("c1", "gia tri ap suat 5 bar bang dieu khien", "child"),
        make_result("c2", "gia tri ap suat 5 bar bang dieu khien", "child"),
    )
    assert [item.chunk_id for item in dedup_diverse_results(dupes)] == ["c1"]
    plan = coerce_query_plan("gia tri ap suat la bao nhieu")
    summary = SearchSummary(
        query="q",
        indexed_chunk_count=2,
        eligible_chunk_count=2,
        candidate_count=2,
        returned_count=2,
    )
    response = SearchResponse(
        results=(
            make_result("s1", "tom tat tai lieu van hanh", "summary"),
            make_result("d1", "ap suat muc tieu 5 bar tai tram 2", "child"),
        ),
        summary=summary,
    )
    pack = build_evidence_pack(plan, response)
    assert any(item.chunk_id == "d1" for item in pack.items)
