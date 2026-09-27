"""Tests for the durable per-file ingest manifest (Vé 1: sổ file chống trùng).

Rule under test: a source file that has not changed since its last ingest must
be skipped from the door — no read, no convert, no chunk, no hash. Only when
mtime/size change may the pipeline read the file again (to re-hash); only when
the content hash changes may it convert and chunk again.
"""

import os
import time
from pathlib import Path
from unittest import mock

from aios_habit.rag_v2 import RagV2DevConfig, RagV2DevPipeline, SourceSpec
from aios_habit.rag_v2 import pipeline as pipeline_module


def _config(tmp_path, **overrides):
    values = {"runtime_root": tmp_path / "runtime", "max_chunk_chars": 120}
    values.update(overrides)
    return RagV2DevConfig(**values)


def _write_source(tmp_path: Path, text: str) -> Path:
    source_path = tmp_path / "guide.txt"
    source_path.write_text(text, encoding="utf-8")
    return source_path


class _CallCounter:
    """Wrap pipeline internals to prove what the second ingest did NOT do."""

    def __init__(self, pipeline: RagV2DevPipeline):
        self.reads: list[str] = []
        self.converts: list[tuple] = []
        self._pipeline = pipeline
        self._orig_fingerprint = pipeline_module._file_fingerprint
        self._orig_convert = pipeline.registry.convert_document

    def _counting_fingerprint(self, path):
        self.reads.append(str(path))
        return self._orig_fingerprint(path)

    def _counting_convert(self, *args, **kwargs):
        self.converts.append(args)
        return self._orig_convert(*args, **kwargs)

    def __enter__(self):
        self._fp_patch = mock.patch.object(
            pipeline_module, "_file_fingerprint", self._counting_fingerprint
        )
        self._convert_patch = mock.patch.object(
            self._pipeline.registry, "convert_document", self._counting_convert
        )
        self._fp_patch.start()
        self._convert_patch.start()
        return self

    def __exit__(self, *exc):
        self._convert_patch.stop()
        self._fp_patch.stop()
        return False


def test_reingest_same_file_skips_without_reading(tmp_path):
    """Vé 1 acceptance: vất lại file cũ thì bỏ qua từ cửa."""
    source_path = _write_source(
        tmp_path, "Local evidence describes a bounded release checklist."
    )
    source = SourceSpec(source_path)

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        first = pipeline.ingest([source])
        assert first.converted_count == 1

        with _CallCounter(pipeline) as counter:
            second = pipeline.ingest([source])

        assert second.skipped_count == 1
        assert second.items[0].status == "unchanged"
        assert counter.reads == [], "unchanged file must not be read/hashed"
        assert counter.converts == [], "unchanged file must not be converted/chunked"


def test_touch_only_mtime_still_skips_convert(tmp_path):
    """mtime đổi nhưng nội dung y nguyên: được đọc để băm lại, nhưng không convert."""
    source_path = _write_source(
        tmp_path, "Local evidence describes a bounded release checklist."
    )
    source = SourceSpec(source_path)

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        assert pipeline.ingest([source]).converted_count == 1

        stamp_ns = time.time_ns() + 5_000_000_000
        os.utime(source_path, ns=(stamp_ns, stamp_ns))

        with _CallCounter(pipeline) as counter:
            second = pipeline.ingest([source])

        assert second.skipped_count == 1
        assert second.items[0].status == "unchanged"
        assert len(counter.reads) == 1, "changed mtime requires one re-hash"
        assert counter.converts == [], "same content must not be converted again"


def test_modified_file_is_reingested(tmp_path):
    source_path = _write_source(
        tmp_path, "Local evidence describes a bounded release checklist."
    )
    source = SourceSpec(source_path)

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        assert pipeline.ingest([source]).converted_count == 1
        source_path.write_text(
            "Local evidence describes a bounded release checklist. Second version.",
            encoding="utf-8",
        )

        with _CallCounter(pipeline) as counter:
            second = pipeline.ingest([source])

        assert second.converted_count == 1
        assert second.items[0].status == "converted"
        assert len(counter.reads) == 1
        assert len(counter.converts) == 1


def test_manifest_survives_new_pipeline_instance(tmp_path):
    """Manifest bền: pipeline mới mở lại vẫn bỏ qua file cũ mà không đọc."""
    source_path = _write_source(
        tmp_path, "Local evidence describes a bounded release checklist."
    )
    source = SourceSpec(source_path)
    manifest_path = (
        tmp_path / "runtime" / "rag_v2_dev.sqlite.ingest_manifest.json"
    )

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        assert pipeline.ingest([source]).converted_count == 1
    assert manifest_path.is_file(), "manifest must be persisted beside the index"

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        with _CallCounter(pipeline) as counter:
            second = pipeline.ingest([source])

        assert second.skipped_count == 1
        assert counter.reads == [], "manifest hit must skip without reading"
        assert counter.converts == []


def test_wiped_index_forces_reingest_despite_manifest(tmp_path):
    """Index bị xóa thì manifest không được cho skip mù: phải ingest lại."""
    source_path = _write_source(
        tmp_path, "Local evidence describes a bounded release checklist."
    )
    source = SourceSpec(source_path)

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        assert pipeline.ingest([source]).converted_count == 1

    for leftover in (tmp_path / "runtime").glob("rag_v2_dev.sqlite*"):
        if not leftover.name.endswith(".ingest_manifest.json"):
            leftover.unlink()

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        second = pipeline.ingest([source])

        assert second.converted_count == 1, "wiped index must trigger re-ingest"
        assert second.skipped_count == 0


def test_corrupt_manifest_falls_back_to_reingest(tmp_path):
    """Manifest hỏng: không crash, ingest lại bình thường."""
    source_path = _write_source(
        tmp_path, "Local evidence describes a bounded release checklist."
    )
    source = SourceSpec(source_path)

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        assert pipeline.ingest([source]).converted_count == 1
        manifest_path = pipeline._ingest_manifest.path
        manifest_path.write_text("{not valid json", encoding="utf-8")

    with RagV2DevPipeline(_config(tmp_path)) as pipeline:
        second = pipeline.ingest([source])
        assert second.skipped_count == 1, "index gate still skips unchanged content"
