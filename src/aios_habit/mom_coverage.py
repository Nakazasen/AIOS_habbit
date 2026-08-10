from __future__ import annotations

import json
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
    "unsupported_no_local_ocr",
    "unsupported_no_local_tool",
    "failed_with_reason",
)
APPROVED_EXCLUSION = "approved_unrecoverable_exclusion"


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
    native_usable_files: int = 0
    ocr_usable_files: int = 0
    approved_exclusions: int = 0
    unresolved_files: int = 0
    disposition_coverage_percent: float = 0.0
    strict_passed: bool = False
    unresolved: list[dict[str, Any]] = field(default_factory=list)
    disposition_validation_errors: list[str] = field(default_factory=list)
    capabilities: dict[str, Any] = field(default_factory=dict)
    privacy_level: str = "local_only"


def _load_dispositions(path: str | Path | None, corpus_files: set[str]) -> tuple[set[str], list[str]]:
    if not path:
        return set(), []
    ledger_path = Path(path)
    if not ledger_path.exists():
        return set(), [f"disposition ledger not found: {ledger_path}"]
    try:
        payload = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return set(), [f"invalid disposition ledger: {exc}"]
    if payload.get("schema_version") != 1 or not isinstance(payload.get("dispositions"), list):
        return set(), ["disposition ledger must use schema_version 1 and a dispositions list"]
    approved: set[str] = set()
    errors: list[str] = []
    for index, item in enumerate(payload["dispositions"]):
        if not isinstance(item, dict):
            errors.append(f"disposition[{index}] must be an object")
            continue
        rel = str(item.get("relative_path") or "").replace("\\", "/").strip("/")
        required = ("reason", "approved_by", "approved_at")
        if not rel or item.get("disposition") != APPROVED_EXCLUSION or any(not str(item.get(key) or "").strip() for key in required):
            errors.append(f"invalid approved exclusion at disposition[{index}]")
            continue
        if rel not in corpus_files:
            errors.append(f"stale or out-of-corpus disposition: {rel}")
            continue
        if rel in approved:
            errors.append(f"duplicate disposition: {rel}")
            continue
        approved.add(rel)
    return approved, errors


def _best_file_status(chunks: list[MomChunk], unsupported: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    statuses: dict[str, str] = {}
    details: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        if chunk.text.strip() and chunk.extraction_status in USABLE_STATUSES:
            statuses[chunk.relative_path] = chunk.extraction_status
    for item in unsupported:
        rel = str(item.get("relative_path") or "").replace("\\", "/")
        status = str(item.get("extraction_status") or "unsupported_no_local_tool")
        if status not in STATUS_BUCKETS:
            status = "failed_with_reason" if status.startswith("failed") else "unsupported_no_local_tool"
        statuses.setdefault(rel, status)
        details.setdefault(rel, item)
    return statuses, details


def summarize_mom_coverage(
    root_path: str | Path,
    *,
    rebuild: bool = True,
    dispositions_path: str | Path | None = None,
) -> MomCoverageSummary:
    root = Path(root_path).resolve()
    result = build_mom_local_index(root, write_runtime=True) if rebuild else None
    chunks = load_mom_chunks()
    unsupported = result.unsupported_files if result else []
    errors = result.errors if result else []
    corpus_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if root.exists() and path.is_file()
    }
    file_status, unsupported_details = _best_file_status(chunks, unsupported)
    approved, disposition_errors = _load_dispositions(dispositions_path, corpus_files)
    status_counts = Counter(file_status.values())
    for bucket in STATUS_BUCKETS:
        status_counts.setdefault(bucket, 0)
    extension_counts = Counter(Path(rel).suffix.lower() or "[no_ext]" for rel in corpus_files)
    chunk_count_by_extension = Counter(chunk.file_type for chunk in chunks)
    unsupported_by_reason = Counter(str(item.get("reason") or "unknown") for item in unsupported)
    usable_paths = {rel for rel, status in file_status.items() if status in USABLE_STATUSES}
    approved -= usable_paths
    unresolved_paths = sorted(corpus_files - usable_paths - approved)
    error_by_path = {str(item.get("relative_path") or "").replace("\\", "/"): item for item in errors}
    unresolved = []
    for rel in unresolved_paths:
        detail = unsupported_details.get(rel) or error_by_path.get(rel) or {}
        unresolved.append({
            "relative_path": rel,
            "file_type": Path(rel).suffix.lower() or "[no_ext]",
            "extraction_status": file_status.get(rel, "unresolved"),
            "reason": detail.get("reason") or detail.get("error") or "source has no usable extraction result",
        })
    unknown_unsupported = sum(1 for item in unresolved if item["extraction_status"] == "unresolved")
    total_files = len(corpus_files)
    usable_files = len(usable_paths)
    ocr_paths = {
        chunk.relative_path for chunk in chunks
        if chunk.text.strip() and chunk.extraction_status in {"ocr_success", "ocr_partial"}
    }
    disposition_count = usable_files + len(approved)
    return MomCoverageSummary(
        total_files=total_files,
        usable_files=usable_files,
        usable_coverage_percent=round((usable_files / total_files * 100.0) if total_files else 100.0, 2),
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
        native_usable_files=len(usable_paths - ocr_paths),
        ocr_usable_files=len(usable_paths & ocr_paths),
        approved_exclusions=len(approved),
        unresolved_files=len(unresolved),
        disposition_coverage_percent=round((disposition_count / total_files * 100.0) if total_files else 100.0, 2),
        strict_passed=not unresolved and not disposition_errors and unknown_unsupported == 0,
        unresolved=unresolved,
        disposition_validation_errors=disposition_errors,
        capabilities=local_capabilities(),
    )


def coverage_summary_to_dict(summary: MomCoverageSummary) -> dict[str, Any]:
    return asdict(summary)
