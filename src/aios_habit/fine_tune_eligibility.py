"""Deterministic eligibility assessment for fine-tuning expert knowledge models.

Implements T070 of Goal 010-expert-knowledge-acquisition.
Fail-closed invariants:
1. Absolute pure function: No side effects, no background training jobs, no external network calls.
2. Privacy guard: Raw audio, raw transcripts, and local_only assets strictly disqualify fine-tuning.
3. Data volume guard: Datasets below 500 verified, cleaned pairs return NOT_APPLICABLE.
4. RAG baseline priority: If BGE-M3 + In-Context retrieval achieves >= 80% accuracy, fine-tune is NOT_APPLICABLE.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Verdict Constants
VERDICT_NOT_APPLICABLE = "NOT_APPLICABLE"
VERDICT_ELIGIBLE = "ELIGIBLE"
VERDICT_BLOCKED_PRIVACY = "BLOCKED_PRIVACY"

MIN_REQUIRED_SAMPLES = 500
RAG_SATISFACTION_THRESHOLD = 0.80


@dataclass(frozen=True)
class FineTuneDatasetMetadata:
    """Metadata describing candidate dataset considered for fine-tuning."""

    total_samples: int
    has_raw_audio: bool
    has_raw_transcripts: bool
    has_local_only_data: bool
    has_pii_or_secrets: bool
    baseline_rag_accuracy: float
    dataset_digest: str = ""
    domain_scope: str = "general"


@dataclass(frozen=True)
class FineTuneRubricItem:
    """Individual rule evaluated in the fine-tune eligibility rubric."""

    rule_name: str
    passed: bool
    description: str
    evidence: str


@dataclass(frozen=True)
class FineTuneAssessmentReport:
    """Comprehensive evaluation report for model fine-tuning eligibility."""

    report_id: str
    verdict: str
    is_eligible: bool
    primary_reason: str
    rubric_results: Tuple[FineTuneRubricItem, ...]
    baseline_rag_accuracy: float
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def digest(self) -> str:
        payload = f"{self.report_id}:{self.verdict}:{self.is_eligible}:{self.primary_reason}:{self.baseline_rag_accuracy}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluate_fine_tune_eligibility(
    dataset_meta: FineTuneDatasetMetadata,
    report_id: Optional[str] = None,
) -> FineTuneAssessmentReport:
    """Evaluate whether fine-tuning is applicable or justified based on strict fail-closed rubric.

    Implements T070.
    Invariants: Pure deterministic evaluation. Zero side effects.
    """
    rubric_items: List[FineTuneRubricItem] = []
    rid = report_id or f"FTR-{int(datetime.now(timezone.utc).timestamp())}"

    # Rule 1: Privacy and Data Containment
    privacy_passed = not (
        dataset_meta.has_raw_audio
        or dataset_meta.has_raw_transcripts
        or dataset_meta.has_local_only_data
        or dataset_meta.has_pii_or_secrets
    )
    privacy_evidence = (
        "Dữ liệu sạch, không chứa audio thô, transcript chưa lọc hoặc dữ liệu local_only."
        if privacy_passed
        else "Phát hiện vi phạm dữ liệu nhạy cảm: chứa audio thô, transcript thô hoặc dữ liệu local_only."
    )
    rubric_items.append(
        FineTuneRubricItem(
            rule_name="Bảo vệ Dữ liệu Riêng tư & Cục bộ",
            passed=privacy_passed,
            description="Tuyệt đối không sử dụng audio gốc, transcript chưa kiểm duyệt hoặc dữ liệu local_only.",
            evidence=privacy_evidence,
        )
    )

    if not privacy_passed:
        return FineTuneAssessmentReport(
            report_id=rid,
            verdict=VERDICT_BLOCKED_PRIVACY,
            is_eligible=False,
            primary_reason="Bị chặn do vi phạm an toàn dữ liệu: Chứa dữ liệu âm thanh thô, bản chép lời hoặc nhãn local_only.",
            rubric_results=tuple(rubric_items),
            baseline_rag_accuracy=dataset_meta.baseline_rag_accuracy,
        )

    # Rule 2: Minimum Dataset Volume
    volume_passed = dataset_meta.total_samples >= MIN_REQUIRED_SAMPLES
    volume_evidence = (
        f"Số lượng mẫu {dataset_meta.total_samples} >= {MIN_REQUIRED_SAMPLES}."
        if volume_passed
        else f"Số lượng mẫu hiện tại ({dataset_meta.total_samples}) quá nhỏ so với ngưỡng tối thiểu ({MIN_REQUIRED_SAMPLES})."
    )
    rubric_items.append(
        FineTuneRubricItem(
            rule_name="Quy mô Tập dữ liệu Tối thiểu",
            passed=volume_passed,
            description=f"Yêu cầu tối thiểu {MIN_REQUIRED_SAMPLES} cặp câu hỏi - phản hồi đã làm sạch.",
            evidence=volume_evidence,
        )
    )

    # Rule 3: RAG Baseline Satisfaction
    rag_adequate = dataset_meta.baseline_rag_accuracy >= RAG_SATISFACTION_THRESHOLD
    rag_evidence = (
        f"Độ chính xác RAG baseline đạt {int(dataset_meta.baseline_rag_accuracy * 100)}% (>= {int(RAG_SATISFACTION_THRESHOLD * 100)}%), chiến lược RAG + Prompt là tối ưu."
        if rag_adequate
        else f"Độ chính xác RAG baseline chỉ đạt {int(dataset_meta.baseline_rag_accuracy * 100)}%."
    )
    rubric_items.append(
        FineTuneRubricItem(
            rule_name="Hiệu năng Kiến trúc Truy xuất RAG Baseline",
            passed=not rag_adequate,  # Pass if RAG is inadequate (which would justify fine-tune)
            description=f"Nếu RAG baseline >= {int(RAG_SATISFACTION_THRESHOLD * 100)}%, fine-tuning là không cần thiết và lãng phí tài nguyên.",
            evidence=rag_evidence,
        )
    )

    # Final Decision Synthesis
    if not volume_passed:
        return FineTuneAssessmentReport(
            report_id=rid,
            verdict=VERDICT_NOT_APPLICABLE,
            is_eligible=False,
            primary_reason=f"Số lượng mẫu tri thức ({dataset_meta.total_samples}) chưa đủ ngưỡng tối thiểu ({MIN_REQUIRED_SAMPLES}). Fine-tuning không khả thi.",
            rubric_results=tuple(rubric_items),
            baseline_rag_accuracy=dataset_meta.baseline_rag_accuracy,
        )

    if rag_adequate:
        return FineTuneAssessmentReport(
            report_id=rid,
            verdict=VERDICT_NOT_APPLICABLE,
            is_eligible=False,
            primary_reason=f"Kiến trúc RAG BGE-M3 đạt độ chính xác {int(dataset_meta.baseline_rag_accuracy * 100)}% (đạt ngưỡng thỏa mãn). Không có cơ sở kỹ thuật để fine-tune mô hình.",
            rubric_results=tuple(rubric_items),
            baseline_rag_accuracy=dataset_meta.baseline_rag_accuracy,
        )

    return FineTuneAssessmentReport(
        report_id=rid,
        verdict=VERDICT_ELIGIBLE,
        is_eligible=True,
        primary_reason="Đạt tất cả tiêu chí đánh giá kỹ thuật để đề xuất phương án fine-tuning.",
        rubric_results=tuple(rubric_items),
        baseline_rag_accuracy=dataset_meta.baseline_rag_accuracy,
    )
