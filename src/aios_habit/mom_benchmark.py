from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aios_habit.real_doc_inventory import MOM_RUNTIME_DIR, ensure_mom_runtime_dir

BENCHMARK_RECORDS_FILE = MOM_RUNTIME_DIR / "benchmark_records.jsonl"
NOTEBOOK_TITLE = "Production History Registration System and Process Specification Interface"
NOTEBOOK_URL = "https://notebooklm.google.com/notebook/b4a708d1-c613-436d-ac55-2923c1e43b46"


@dataclass
class BenchmarkScores:
    source_traceability: int = 0
    answer_completeness: int = 0
    hallucination_risk: int = 0
    actionability: int = 0
    vietnamese_clarity: int = 0
    evidence_alignment: int = 0


@dataclass
class MomBenchmarkRecord:
    question_id: str
    question: str
    aios_answer_summary: str
    aios_source_refs: list[dict[str, Any]]
    notebooklm_answer_summary: str = ""
    notebooklm_query_status: str = "manual_required"  # success, failed, manual_required
    comparison_scores: dict[str, int] = field(default_factory=dict)
    winner: str = "Inconclusive"  # AIOS, NotebookLM, Tie, Inconclusive
    notes: str = ""
    privacy_level: str = "local_only"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    record_id: str = field(default_factory=lambda: f"MOM-BENCH-{uuid.uuid4().hex[:8].upper()}")


def _clamp_score(value: int) -> int:
    return max(0, min(5, int(value)))


def compare_aios_notebooklm(
    question: str,
    aios_source_refs: list[dict[str, Any]],
    aios_answer_summary: str = "",
    notebooklm_answer_summary: str = "",
    notebooklm_query_status: str = "manual_required",
) -> tuple[dict[str, int], str, str]:
    source_count = len(aios_source_refs)
    has_notebook_answer = bool(notebooklm_answer_summary.strip()) and notebooklm_query_status == "success"

    scores = {
        "source_traceability": _clamp_score(5 if source_count >= 2 else 3 if source_count == 1 else 0),
        "answer_completeness": _clamp_score(3 if aios_answer_summary.strip() else 1 if source_count else 0),
        "hallucination_risk": _clamp_score(5 if source_count and "chưa đủ" in aios_answer_summary.lower() else 4 if source_count else 2),
        "actionability": _clamp_score(4 if "next" in aios_answer_summary.lower() or "kiểm" in aios_answer_summary.lower() else 2 if source_count else 0),
        "vietnamese_clarity": _clamp_score(4 if aios_answer_summary.strip() else 0),
        "evidence_alignment": _clamp_score(5 if source_count else 0),
    }

    if not has_notebook_answer:
        return scores, "Inconclusive", "NotebookLM query chưa thành công; chỉ đánh giá được phía AIOS."

    aios_total = sum(scores.values())
    notebook_bonus = 0
    if any(token in notebooklm_answer_summary.lower() for token in ("nguồn", "source", "trích", "citation")):
        notebook_bonus += 3
    if any(token in notebooklm_answer_summary.lower() for token in ("không đủ", "chưa đủ", "not enough")):
        notebook_bonus += 2
    notebook_total = 15 + notebook_bonus

    if abs(aios_total - notebook_total) <= 2:
        winner = "Tie"
    elif aios_total > notebook_total:
        winner = "AIOS"
    else:
        winner = "NotebookLM"
    return scores, winner, "NotebookLM là comparator, không phải ground truth; ground truth vẫn là MOM source refs."


def build_benchmark_record(
    question_id: str,
    question: str,
    aios_source_refs: list[dict[str, Any]],
    aios_answer_summary: str = "",
    notebooklm_answer_summary: str = "",
    notebooklm_query_status: str = "manual_required",
    notes: str = "",
) -> MomBenchmarkRecord:
    scores, winner, auto_notes = compare_aios_notebooklm(
        question=question,
        aios_source_refs=aios_source_refs,
        aios_answer_summary=aios_answer_summary,
        notebooklm_answer_summary=notebooklm_answer_summary,
        notebooklm_query_status=notebooklm_query_status,
    )
    merged_notes = notes.strip() or auto_notes
    if notes.strip() and auto_notes:
        merged_notes = f"{notes.strip()} | {auto_notes}"
    return MomBenchmarkRecord(
        question_id=question_id,
        question=question,
        aios_answer_summary=aios_answer_summary,
        aios_source_refs=aios_source_refs,
        notebooklm_answer_summary=notebooklm_answer_summary,
        notebooklm_query_status=notebooklm_query_status,
        comparison_scores=scores,
        winner=winner,
        notes=merged_notes,
    )


def save_benchmark_record(record: MomBenchmarkRecord) -> Path:
    ensure_mom_runtime_dir()
    with BENCHMARK_RECORDS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return BENCHMARK_RECORDS_FILE


def load_benchmark_records(path: str | Path = BENCHMARK_RECORDS_FILE, limit: Optional[int] = None) -> list[MomBenchmarkRecord]:
    p = Path(path)
    if not p.exists():
        return []
    records: list[MomBenchmarkRecord] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(MomBenchmarkRecord(**json.loads(line)))
                except Exception:
                    continue
    records.reverse()
    return records[:limit] if limit else records


def notebooklm_manual_required_record(question_id: str, question: str, aios_source_refs: list[dict[str, Any]], aios_answer_summary: str) -> MomBenchmarkRecord:
    return build_benchmark_record(
        question_id=question_id,
        question=question,
        aios_source_refs=aios_source_refs,
        aios_answer_summary=aios_answer_summary,
        notebooklm_query_status="manual_required",
        notes="Streamlit app không gọi trực tiếp NotebookLM MCP; Antigravity agent/browser cần query notebook hiện có.",
    )
