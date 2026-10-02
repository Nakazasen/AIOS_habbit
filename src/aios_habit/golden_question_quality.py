"""Before/after quality measurement for the golden-question pilot.

Metrics (design doc section 3.5), measured on the SAME question set over the
pilot phenomena, with an index snapshot taken before measuring:

- M1 knowledge coverage: remaining gaps via evaluate_coverage (reused);
  target: high-priority gaps down >= 60%.
- M2 retrieval: new staging chunks in top-5; target: hit >= 4/5 phenomena.
- M3 form completeness: required fields filled, measurable evidence,
  causal mechanism + 4M present; target >= 80%.
- M4 hypothesis discrimination: % of hypothesis pairs the answers
  discriminate; target >= 70%.
- M5 expert deviation: % content changed after real-expert review;
  target < 30% (otherwise recalibrate the scorer weights).

The "before" and "after" retrieval adapters are injected, so tests use
FakeKnowledgeRetrievalAdapter while production uses the real RAG adapter.
Nothing here writes to the production index.

Python 3.11 compatible.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Dict, List, Optional, Sequence, Tuple

from aios_habit.golden_question_generator import PhenomenonContext
from aios_habit.golden_question_schema import (
    ANSWER_STATE_ANSWERED,
    LOAI_DISCRIMINATOR,
    GoldenAnswer,
    GoldenQuestion,
)
from aios_habit.knowledge_coverage import (
    CollectionInventory,
    CoverageMetric,
    CoverageQuestion,
    KnowledgeGapCandidate,
    KnowledgeRetrievalAdapter,
    evaluate_coverage,
)

# Pilot pass thresholds.
M1_HIGH_GAP_REDUCTION_TARGET = 0.60
M2_HIT_TARGET = 4
M3_COMPLETENESS_TARGET = 0.80
M4_DISCRIMINATION_TARGET = 0.70
M5_DEVIATION_LIMIT = 0.30

# Marker used to recognize newly-enriched chunks in retrieval receipts.
GOLDEN_NEW_MARKERS = ("STAGING-GQ", "GQ-NEW-")


@dataclass(frozen=True)
class QualityReport:
    """Before/after measurement outcome for one batch."""

    batch_id: str
    m1_high_gaps_before: int
    m1_high_gaps_after: int
    m1_high_gap_reduction: float
    m1_coverage_before: float
    m1_coverage_after: float
    m2_hits: int
    m2_total: int
    m2_details: Tuple[Dict[str, Any], ...]
    m3_form_completeness: float
    m3_measurable_evidence_rate: float
    m3_causal_complete_rate: float
    m3_total_answers: int
    m4_discriminated_pairs: int
    m4_total_pairs: int
    m4_rate: float
    answer_time: Dict[str, Any] = field(default_factory=dict)
    verdicts: Dict[str, bool] = field(default_factory=dict)

    def overall_pass(self) -> bool:
        return all(self.verdicts.values())


def build_standard_questions(
    phenomena: Sequence[PhenomenonContext],
) -> List[CoverageQuestion]:
    """The fixed standard question set, identical before and after."""
    questions: List[CoverageQuestion] = []
    for index, ctx in enumerate(phenomena, 1):
        questions.append(
            CoverageQuestion(
                question_id="STD-%s-%02d" % (ctx.batch_id, index),
                scope=ctx.error_group or "F CALL",
                question_text=(
                    "Hiện tượng '%s': nguyên nhân, cơ chế gây lỗi và đối sách là gì?"
                    % ctx.phenomenon
                ),
                expected_evidence=("causal_mechanism", "countermeasure", "evidence"),
            )
        )
    return questions


def measure_m1(
    adapter: KnowledgeRetrievalAdapter,
    inventory: CollectionInventory,
    questions: Sequence[CoverageQuestion],
    known_gaps: Optional[Sequence[KnowledgeGapCandidate]] = None,
) -> Tuple[CoverageMetric, List[KnowledgeGapCandidate]]:
    """Knowledge-gap coverage via the existing evaluate_coverage."""
    return evaluate_coverage(inventory, questions, known_gaps=known_gaps, adapter=adapter)


def high_gap_count(gaps: Sequence[KnowledgeGapCandidate]) -> int:
    return sum(1 for g in gaps if g.priority == "high")


def measure_m2(
    adapter: KnowledgeRetrievalAdapter,
    questions: Sequence[CoverageQuestion],
    top_k: int = 5,
) -> Dict[str, Any]:
    """Retrieval: do new staging chunks reach top-k for each phenomenon?"""
    details: List[Dict[str, Any]] = []
    hits = 0
    for q in questions:
        receipt = adapter.retrieve(q, top_k=top_k)
        snippets = list(receipt.retrieved_snippets)[:top_k]
        new_chunks = [
            s.snippet_id
            for s in snippets
            if s.snippet_id.startswith(GOLDEN_NEW_MARKERS)
            or bool(s.metadata.get("golden_new"))
        ]
        hit = bool(new_chunks)
        hits += 1 if hit else 0
        details.append(
            {
                "question_id": q.question_id,
                "hit": hit,
                "new_chunks_in_top": new_chunks,
                "top_snippet_ids": [s.snippet_id for s in snippets],
            }
        )
    return {"hits": hits, "total": len(questions), "details": details}


_MEASURABLE_HINTS = re.compile(r"\d|v\b|a\b|°c|mm|bar|log|ảnh|do")


def _has_measurable_evidence(answer: GoldenAnswer) -> bool:
    if answer.thresholds:
        return True
    for item in answer.evidence_to_collect:
        if _MEASURABLE_HINTS.search(item.lower()):
            return True
    return False


def measure_m3(answers: Sequence[GoldenAnswer]) -> Dict[str, Any]:
    """Form completeness across the imported answers."""
    total = len(answers)
    if total == 0:
        return {
            "form_completeness": 0.0,
            "measurable_evidence_rate": 0.0,
            "causal_complete_rate": 0.0,
            "total_answers": 0,
        }
    required_filled = 0
    measurable = 0
    causal_complete = 0
    for a in answers:
        # GoldenAnswer.__post_init__ already guarantees structural validity;
        # here we measure richness beyond the minimum.
        filled = all(
            [
                len(a.answer_text.strip()) >= 20,
                bool(a.hypotheses) or a.answer_state != ANSWER_STATE_ANSWERED,
                bool(a.confirm_criteria.strip()) or a.answer_state != ANSWER_STATE_ANSWERED,
            ]
        )
        if filled:
            required_filled += 1
        if _has_measurable_evidence(a):
            measurable += 1
        if a.answer_state == ANSWER_STATE_ANSWERED and a.causal_mechanism.strip() and a.m4_branches:
            causal_complete += 1
    answered = [a for a in answers if a.answer_state == ANSWER_STATE_ANSWERED]
    return {
        "form_completeness": round(required_filled / total, 3),
        "measurable_evidence_rate": round(measurable / total, 3),
        "causal_complete_rate": round(causal_complete / len(answered), 3) if answered else 0.0,
        "total_answers": total,
    }


def measure_m4(
    phenomena: Sequence[PhenomenonContext],
    questions_by_id: Dict[str, GoldenQuestion],
    answers: Sequence[GoldenAnswer],
) -> Dict[str, Any]:
    """Hypothesis discrimination: % of hypothesis pairs an answer discriminates.

    Pairs are counted per phenomenon (from its hypothesis set). A pair counts
    as discriminated when a discriminator-kind answer for that phenomenon names
    both hypotheses and carries non-empty discriminate_notes.
    """
    discriminated = 0
    total = 0
    pairs_hit: List[str] = []
    for ctx in phenomena:
        ids = sorted(h.hypothesis_id for h in ctx.hypotheses)
        ctx_cases = set(ctx.case_ids)
        for h1, h2 in combinations(ids, 2):
            total += 1
            hit = False
            for a in answers:
                q = questions_by_id.get(a.question_id)
                if q is None or q.loai_cau_hoi != LOAI_DISCRIMINATOR:
                    continue
                if not a.discriminate_notes.strip():
                    continue
                if not (set(q.target_case_ids) & ctx_cases):
                    continue
                named = set(a.hypotheses) | set(q.gia_thuyet_lien_quan)
                if h1 in named and h2 in named:
                    hit = True
                    break
            if hit:
                discriminated += 1
                pairs_hit.append("%s|%s" % (h1, h2))
    rate = round(discriminated / total, 3) if total else 0.0
    return {
        "discriminated_pairs": discriminated,
        "total_pairs": total,
        "rate": rate,
        "pairs": sorted(pairs_hit),
    }


def measure_m5(draft_text: str, reviewed_text: str) -> float:
    """Expert deviation: fraction of content changed after expert review.

    0.0 = untouched, 1.0 = fully rewritten.
    """
    if not draft_text and not reviewed_text:
        return 0.0
    ratio = difflib.SequenceMatcher(None, draft_text, reviewed_text).ratio()
    return round(1.0 - ratio, 3)


def measure_answer_time(answers: Sequence[GoldenAnswer]) -> Dict[str, Any]:
    """Answer time: span from the first to the last answered_at timestamp.

    Informational only (the design sets no pass/fail threshold for it):
    measures how long batch answering took once respondents started.
    Returns {} when fewer than two answers carry a parseable timestamp.
    """
    from datetime import datetime

    stamps: List[datetime] = []
    for a in answers:
        raw = (a.answered_at or "").strip()
        if not raw:
            continue
        try:
            stamps.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
        except ValueError:
            continue
    if len(stamps) < 2:
        return {}
    span_s = (max(stamps) - min(stamps)).total_seconds()
    return {
        "answers_with_timestamp": len(stamps),
        "batch_span_seconds": round(span_s, 1),
        "batch_span_minutes": round(span_s / 60.0, 1),
    }


def run_before_after(
    batch_id: str,
    phenomena: Sequence[PhenomenonContext],
    before_adapter: KnowledgeRetrievalAdapter,
    after_adapter: KnowledgeRetrievalAdapter,
    inventory: CollectionInventory,
    questions_by_id: Dict[str, GoldenQuestion],
    answers: Sequence[GoldenAnswer],
) -> QualityReport:
    """Run M1–M4 before/after on the same standard question set."""
    standard_questions = build_standard_questions(phenomena)

    metric_before, gaps_before = measure_m1(before_adapter, inventory, standard_questions)
    metric_after, gaps_after = measure_m1(after_adapter, inventory, standard_questions)
    high_before = high_gap_count(gaps_before)
    high_after = high_gap_count(gaps_after)
    reduction = (
        round((high_before - high_after) / high_before, 3) if high_before > 0 else 0.0
    )

    m2 = measure_m2(after_adapter, standard_questions)
    m3 = measure_m3(answers)
    m4 = measure_m4(phenomena, questions_by_id, answers)

    verdicts = {
        "M1_high_gap_reduction_ge_60pct": reduction >= M1_HIGH_GAP_REDUCTION_TARGET,
        "M2_new_chunk_hits_ge_4_of_5": m2["hits"] >= M2_HIT_TARGET,
        "M3_form_completeness_ge_80pct": m3["form_completeness"] >= M3_COMPLETENESS_TARGET,
        "M4_hypothesis_discrimination_ge_70pct": m4["rate"] >= M4_DISCRIMINATION_TARGET,
    }
    details = tuple(
        dict(item, question_text=q.question_text)
        for item, q in zip(m2["details"], standard_questions)
    )
    return QualityReport(
        batch_id=batch_id,
        m1_high_gaps_before=high_before,
        m1_high_gaps_after=high_after,
        m1_high_gap_reduction=reduction,
        m1_coverage_before=round(metric_before.coverage_ratio, 3),
        m1_coverage_after=round(metric_after.coverage_ratio, 3),
        m2_hits=m2["hits"],
        m2_total=m2["total"],
        m2_details=details,
        m3_form_completeness=m3["form_completeness"],
        m3_measurable_evidence_rate=m3["measurable_evidence_rate"],
        m3_causal_complete_rate=m3["causal_complete_rate"],
        m3_total_answers=m3["total_answers"],
        m4_discriminated_pairs=m4["discriminated_pairs"],
        m4_total_pairs=m4["total_pairs"],
        m4_rate=m4["rate"],
        answer_time=measure_answer_time(answers),
        verdicts=verdicts,
    )


def render_quality_report(report: QualityReport) -> str:
    """Render the before/after report as Markdown (Vietnamese)."""
    lines: List[str] = []
    lines.append("# Báo cáo chất lượng làm giàu tri thức — batch %s" % report.batch_id)
    lines.append("")
    verdict = "ĐẠT" if report.overall_pass() else "CHƯA ĐẠT"
    lines.append("Kết luận chung: **%s**" % verdict)
    lines.append("")
    lines.append("| Metric | Trước | Sau | Ngưỡng | Kết quả |")
    lines.append("| --- | --- | --- | --- | --- |")
    m1_ok = "ĐẠT" if report.verdicts.get("M1_high_gap_reduction_ge_60pct") else "CHƯA ĐẠT"
    lines.append(
        "| M1 phủ tri thức (gap high) | %d gap | %d gap | giảm ≥ 60%% | %s (giảm %.1f%%) |"
        % (
            report.m1_high_gaps_before,
            report.m1_high_gaps_after,
            m1_ok,
            report.m1_high_gap_reduction * 100,
        )
    )
    lines.append(
        "| M1 coverage_ratio | %.3f | %.3f | — | — |"
        % (report.m1_coverage_before, report.m1_coverage_after)
    )
    m2_ok = "ĐẠT" if report.verdicts.get("M2_new_chunk_hits_ge_4_of_5") else "CHƯA ĐẠT"
    lines.append(
        "| M2 truy hồi (chunk mới vào top-5) | — | %d/%d hiện tượng | ≥ 4/5 | %s |"
        % (report.m2_hits, report.m2_total, m2_ok)
    )
    m3_ok = "ĐẠT" if report.verdicts.get("M3_form_completeness_ge_80pct") else "CHƯA ĐẠT"
    lines.append(
        "| M3 đầy form | — | %.1f%% (%d đáp án) | ≥ 80%% | %s |"
        % (report.m3_form_completeness * 100, report.m3_total_answers, m3_ok)
    )
    lines.append(
        "| M3 bằng chứng đo được | — | %.1f%% | — | — |" % (report.m3_measurable_evidence_rate * 100)
    )
    lines.append(
        "| M3 đủ cơ chế + 4M | — | %.1f%% | — | — |" % (report.m3_causal_complete_rate * 100)
    )
    m4_ok = "ĐẠT" if report.verdicts.get("M4_hypothesis_discrimination_ge_70pct") else "CHƯA ĐẠT"
    lines.append(
        "| M4 phân biệt giả thuyết | — | %d/%d cặp (%.1f%%) | ≥ 70%% | %s |"
        % (
            report.m4_discriminated_pairs,
            report.m4_total_pairs,
            report.m4_rate * 100,
            m4_ok,
        )
    )
    lines.append("")
    lines.append("## Chi tiết M2 theo hiện tượng")
    lines.append("")
    for item in report.m2_details:
        mark = "✓" if item["hit"] else "✗"
        lines.append(
            "- %s %s — chunk mới trong top-5: %s"
            % (mark, item["question_id"], ", ".join(item["new_chunks_in_top"]) or "không có")
        )
    lines.append("")
    lines.append("## Thời gian trả lời (tham khảo)")
    lines.append("")
    if report.answer_time:
        lines.append(
            "- Khoảng thời gian từ đáp án đầu tới đáp án cuối: %.1f phút (%d đáp án có mốc thời gian)."
            % (report.answer_time["batch_span_minutes"], report.answer_time["answers_with_timestamp"])
        )
    else:
        lines.append("- Chưa có đủ mốc thời gian answered_at để đo.")
    lines.append("")
    lines.append("## Đề xuất hiệu chỉnh")
    lines.append("")
    if report.verdicts.get("M1_high_gap_reduction_ge_60pct") and report.overall_pass():
        lines.append("- Các ngưỡng pilot đều đạt; giữ nguyên trọng số scorer cho vòng tiếp theo.")
    else:
        lines.append("- Metric chưa đạt cần xem lại câu hỏi của hiện tượng tương ứng trước khi mở rộng batch.")
        lines.append("- Nếu M5 (độ lệch chuyên gia) ≥ 30%, hiệu chỉnh trọng số scorer cho vòng 2.")
    lines.append("")
    return "\n".join(lines)


def write_quality_report(report: QualityReport, out_dir: str) -> str:
    """Write bao_cao_chat_luong_<batch_id>.md; returns the file path."""
    from pathlib import Path

    path = Path(out_dir) / ("bao_cao_chat_luong_%s.md" % report.batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_quality_report(report), encoding="utf-8")
    return str(path)
