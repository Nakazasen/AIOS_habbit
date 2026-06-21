from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from aios_habit.document_extractors import USABLE_STATUSES, local_capabilities
from aios_habit.mom_local_index import MomChunk, build_mom_local_index, load_mom_chunks

STATUS_BUCKETS = (
    "extracted_success",
    "extracted_partial",
    "ocr_success",
    "ocr_partial",
    "unsupported_no_local_tool",
    "failed_with_reason",
)


@dataclass
class MomCoverageSummary:
    total_files: int
    usable_files: int
    usable_coverage_percent: float
    chunks_generated: int
    status_counts: dict[str, int]
    extension_counts: dict[str, int]
    chunk_count_by_extension: dict[str, int]
    unsupported_by_reason: dict[str, int]
    ocr_chunks_count: int
    docx_chunks_count: int
    png_ocr_chunks_count: int
    pdf_ocr_chunks_count: int
    unknown_unsupported: int
    capabilities: dict[str, Any] = field(default_factory=dict)
    privacy_level: str = "local_only"


def _file_statuses(chunks: list[MomChunk], unsupported: list[dict[str, Any]]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for chunk in chunks:
        status = chunk.extraction_status or "extracted_success"
        if status in USABLE_STATUSES:
            statuses[chunk.relative_path] = status
    for item in unsupported:
        rel = str(item.get("relative_path") or "")
        status = str(item.get("extraction_status") or "unsupported_no_local_tool")
        if status not in STATUS_BUCKETS:
            status = "failed_with_reason" if status.startswith("failed") else "unsupported_no_local_tool"
        statuses.setdefault(rel, status)
    return statuses


def summarize_mom_coverage(root_path: str | Path, *, rebuild: bool = True) -> MomCoverageSummary:
    result = build_mom_local_index(root_path, write_runtime=True) if rebuild else None
    chunks = load_mom_chunks()
    unsupported = result.unsupported_files if result else []
    file_status = _file_statuses(chunks, unsupported)
    status_counts = Counter(file_status.values())
    for bucket in STATUS_BUCKETS:
        status_counts.setdefault(bucket, 0)
    extension_counts = Counter(Path(rel).suffix.lower() or "[no_ext]" for rel in file_status)
    chunk_count_by_extension = Counter(chunk.file_type for chunk in chunks)
    unsupported_by_reason = Counter(str(item.get("reason") or "unknown") for item in unsupported)
    unknown_unsupported = sum(1 for item in unsupported if not item.get("extraction_status") and not item.get("reason"))
    total_files = len(file_status)
    usable_files = sum(1 for status in file_status.values() if status in USABLE_STATUSES)
    return MomCoverageSummary(
        total_files=total_files,
        usable_files=usable_files,
        usable_coverage_percent=round((usable_files / total_files * 100.0) if total_files else 0.0, 2),
        chunks_generated=len(chunks),
        status_counts=dict(sorted(status_counts.items())),
        extension_counts=dict(sorted(extension_counts.items())),
        chunk_count_by_extension=dict(sorted(chunk_count_by_extension.items())),
        unsupported_by_reason=dict(sorted(unsupported_by_reason.items())),
        ocr_chunks_count=sum(1 for chunk in chunks if chunk.extraction_status in {"ocr_success", "ocr_partial"}),
        docx_chunks_count=sum(1 for chunk in chunks if chunk.file_type == ".docx"),
        png_ocr_chunks_count=sum(1 for chunk in chunks if chunk.file_type == ".png" and chunk.extraction_status in {"ocr_success", "ocr_partial"}),
        pdf_ocr_chunks_count=sum(1 for chunk in chunks if chunk.file_type == ".pdf" and chunk.extractor_name == "pdf_image_ocr"),
        unknown_unsupported=unknown_unsupported,
        capabilities=local_capabilities(),
    )


def coverage_summary_to_dict(summary: MomCoverageSummary) -> dict[str, Any]:
    return asdict(summary)
