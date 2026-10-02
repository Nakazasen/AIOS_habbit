"""Scorer + top-K selector for golden questions.

Score formula (design doc section 3.2, step 2):
    diem(q) = 100 * (0.30*D + 0.20*G + 0.20*E + 0.15*W + 0.10*N + 0.05*F)

- D: hypothesis discrimination (pairs discriminated / total pairs).
- G: important-gap fill (gap priority weight x newly covered aspects).
- E: measurable evidence demanded (1.0 measurable / 0.5 descriptive / 0 none).
- W: Why-Why/4M depth (new branch or deeper Why level).
- N: novelty (1 - max Jaccard vs selected + history; dup >= 0.85 excluded).
- F: batch-answer feasibility (penalized for destructive-test keywords).

Reuses existing guardrails from adaptive_interview_engine:
detect_leading_question (reject), detect_semantic_duplicate (reject),
validate_candidate_question (final budget check).

Greedy top-K selection per phenomenon with hard constraints:
>= 1 discriminator (D > 0), >= 1 measurable-evidence question (E == 1.0),
coverage of >= 3 of the 4M branches.

Python 3.11 compatible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple

from aios_habit.adaptive_interview_engine import (
    detect_leading_question,
    detect_semantic_duplicate,
    validate_candidate_question,
)
from aios_habit.knowledge_coverage import KnowledgeGapCandidate

from aios_habit.golden_question_generator import (
    ASPECT_OF_LOAI,
    Hypothesis,
    PhenomenonContext,
    _MEASURABLE_EVIDENCE,
)
from aios_habit.golden_question_schema import (
    LOAI_CAUSAL_MECHANISM,
    LOAI_DISCRIMINATOR,
    GoldenQuestion,
    SCORE_COMPONENTS,
)

# Criterion weights (must sum to 1.0).
WEIGHTS: Dict[str, float] = {
    "D": 0.30,
    "G": 0.20,
    "E": 0.20,
    "W": 0.15,
    "N": 0.10,
    "F": 0.05,
}

# Gap priority weights for criterion G.
PRIORITY_WEIGHT: Dict[str, float] = {"high": 1.0, "medium": 0.6, "low": 0.3}

# Keywords that make a batch question infeasible without stopping the line.
INFEASIBLE_KEYWORDS: Tuple[str, ...] = (
    "phá hủy",
    "tháo máy chạy thử",
    "dừng line",
)

# Text markers that indicate the question demands a concrete value.
CONCRETE_VALUE_MARKERS: Tuple[str, ...] = (
    "bao nhiêu",
    "giá trị cụ thể",
    "giá trị số",
    "đo được",
    "kèm đơn vị",
)


class GoldenScorerError(ValueError):
    """Raised when scoring/selection cannot proceed."""


@dataclass(frozen=True)
class SelectionState:
    """Tracks what the already-selected questions cover (for G/W/N)."""

    aspects: Tuple[str, ...] = ()
    m4_branches: Tuple[str, ...] = ()
    loai_set: Tuple[str, ...] = ()
    why_levels: Tuple[int, ...] = ()
    texts: Tuple[str, ...] = ()

    def with_question(self, q: GoldenQuestion) -> "SelectionState":
        aspects = tuple(self.aspects) + tuple(a for a in ASPECT_OF_LOAI.get(q.loai_cau_hoi, ()) if a not in self.aspects)
        m4_branches = tuple(self.m4_branches)
        if q.m4_branch and q.m4_branch not in m4_branches:
            m4_branches = m4_branches + (q.m4_branch,)
        loai_set = tuple(self.loai_set) if q.loai_cau_hoi in self.loai_set else tuple(self.loai_set) + (q.loai_cau_hoi,)
        why_levels = tuple(self.why_levels)
        if q.loai_cau_hoi == LOAI_CAUSAL_MECHANISM and q.why_level not in why_levels:
            why_levels = why_levels + (q.why_level,)
        return SelectionState(
            aspects=aspects,
            m4_branches=m4_branches,
            loai_set=loai_set,
            why_levels=why_levels,
            texts=tuple(self.texts) + (q.text,),
        )


def _total_hypothesis_pairs(hypotheses: Sequence[Hypothesis]) -> int:
    n = len(hypotheses)
    return n * (n - 1) // 2 if n >= 2 else 0


def _score_d(q: GoldenQuestion, total_pairs: int) -> float:
    """Hypothesis discrimination."""
    if q.loai_cau_hoi == LOAI_DISCRIMINATOR:
        if total_pairs <= 0:
            return 0.0
        return min(1.0, len(q.discriminant_pairs) / total_pairs)
    if len(q.gia_thuyet_lien_quan) >= 2:
        return 0.3
    return 0.0


def _score_g(
    q: GoldenQuestion,
    gap: KnowledgeGapCandidate,
    state: SelectionState,
    total_aspects: int,
) -> float:
    """Important-gap fill: priority weight x newly covered aspects."""
    if total_aspects <= 0:
        return 0.0
    aspects = ASPECT_OF_LOAI.get(q.loai_cau_hoi, ())
    new_aspects = [a for a in aspects if a not in state.aspects]
    weight = PRIORITY_WEIGHT.get(gap.priority, 0.3)
    return weight * (len(new_aspects) / total_aspects)


def _score_e(q: GoldenQuestion) -> float:
    """Measurable evidence demanded."""
    evidence = set(q.expected_evidence)
    if not evidence:
        return 0.0
    if evidence & set(_MEASURABLE_EVIDENCE):
        lowered = q.text.lower()
        if any(marker in lowered for marker in CONCRETE_VALUE_MARKERS):
            return 1.0
        return 0.5
    return 0.5 if "description" in evidence or "document" in evidence else 0.0


def _score_w(q: GoldenQuestion, state: SelectionState) -> float:
    """Why-Why / 4M depth."""
    if q.m4_branch:
        if q.m4_branch not in state.m4_branches:
            return 1.0
        return 0.5
    if q.loai_cau_hoi == LOAI_CAUSAL_MECHANISM:
        max_level = max(state.why_levels) if state.why_levels else 0
        if q.why_level > max_level:
            return 1.0
        return 0.5
    if q.loai_cau_hoi in state.loai_set:
        return 0.0
    return 0.5


def _jaccard(a: str, b: str) -> float:
    ta = set(re.findall(r"\w+", a.lower()))
    tb = set(re.findall(r"\w+", b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _score_n(
    q: GoldenQuestion,
    state: SelectionState,
    history_questions: Sequence[str],
) -> float:
    """Novelty: 1 - max Jaccard against selected + history."""
    others = list(state.texts) + list(history_questions)
    if not others:
        return 1.0
    best = max(_jaccard(q.text, other) for other in others)
    return max(0.0, 1.0 - best)


def _score_f(q: GoldenQuestion) -> float:
    """Batch-answer feasibility."""
    lowered = q.text.lower()
    if any(keyword in lowered for keyword in INFEASIBLE_KEYWORDS):
        return 0.5
    return 1.0


def score_components(
    q: GoldenQuestion,
    ctx: PhenomenonContext,
    gap_by_id: Dict[str, KnowledgeGapCandidate],
    state: SelectionState,
    total_aspects: int,
    history_questions: Sequence[str],
) -> Dict[str, float]:
    """Compute the six score components of one question (all in [0, 1])."""
    total_pairs = _total_hypothesis_pairs(ctx.hypotheses)
    gap = gap_by_id.get(q.target_gap_id)
    if gap is None:
        raise GoldenScorerError("Câu hỏi %s nối tới gap_id lạ: %s." % (q.question_id, q.target_gap_id))
    return {
        "D": _score_d(q, total_pairs),
        "G": _score_g(q, gap, state, total_aspects),
        "E": _score_e(q),
        "W": _score_w(q, state),
        "N": _score_n(q, state, history_questions),
        "F": _score_f(q),
    }


def total_score(components: Dict[str, float]) -> float:
    """Weighted total in [0, 100]."""
    return round(100.0 * sum(WEIGHTS[k] * components[k] for k in SCORE_COMPONENTS), 1)


def _passes_hard_guardrails(
    q: GoldenQuestion,
    state: SelectionState,
    history_questions: Sequence[str],
) -> bool:
    """Leading questions and semantic duplicates are rejected outright."""
    if not q.text or not q.text.strip():
        return False
    if detect_leading_question(q.text):
        return False
    if detect_semantic_duplicate(q.text, list(state.texts) + list(history_questions)):
        return False
    return True


def _adds_coverage(q: GoldenQuestion, state: SelectionState) -> bool:
    """True if q covers a new aspect, 4M branch, question kind, or Why level."""
    aspects = ASPECT_OF_LOAI.get(q.loai_cau_hoi, ())
    if any(a not in state.aspects for a in aspects):
        return True
    if q.m4_branch and q.m4_branch not in state.m4_branches:
        return True
    if q.loai_cau_hoi not in state.loai_set:
        return True
    if q.loai_cau_hoi == LOAI_CAUSAL_MECHANISM:
        max_level = max(state.why_levels) if state.why_levels else 0
        if q.why_level > max_level:
            return True
    return False


@dataclass(frozen=True)
class SelectionResult:
    """Outcome of top-K selection for one phenomenon."""

    phenomenon: str
    selected: Tuple[GoldenQuestion, ...]
    rejected_count: int
    constraints_met: Dict[str, bool]
    min_score: float
    # Ids added by hard-constraint enforcement (may sit below min_score).
    forced_question_ids: Tuple[str, ...] = ()


def select_top_k(
    ctx: PhenomenonContext,
    candidates: Sequence[GoldenQuestion],
    k: int = 3,
    min_score: float = 55.0,
    history_questions: Sequence[str] = (),
) -> SelectionResult:
    """Greedy top-K selection with hard per-phenomenon constraints.

    Constraints: >= 1 discriminator (D > 0), >= 1 measurable-evidence
    question (E == 1.0), coverage of >= 3 of the 4M branches.
    """
    if k <= 0:
        raise GoldenScorerError("k phải lớn hơn 0.")
    gaps = list(ctx.gaps)
    if not gaps:
        raise GoldenScorerError("Cần ít nhất 1 gap để chấm điểm.")
    gap_by_id = {g.gap_id: g for g in gaps}

    all_aspects: Set[str] = set()
    for q in candidates:
        all_aspects.update(ASPECT_OF_LOAI.get(q.loai_cau_hoi, ()))
    total_aspects = len(all_aspects)

    # Filter hard guardrails first.
    pool: List[GoldenQuestion] = []
    rejected = 0
    for q in candidates:
        if _passes_hard_guardrails(q, SelectionState(), history_questions):
            pool.append(q)
        else:
            rejected += 1

    selected: List[GoldenQuestion] = []
    selected_ids: Set[str] = set()
    state = SelectionState()

    def _score_pool() -> List[Tuple[float, Dict[str, float], GoldenQuestion]]:
        scored = []
        for q in pool:
            if q.question_id in selected_ids:
                continue
            components = score_components(q, ctx, gap_by_id, state, total_aspects, history_questions)
            scored.append((total_score(components), components, q))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored

    def _take(score: float, components: Dict[str, float], q: GoldenQuestion) -> None:
        selected.append(q.with_score(score, components))
        selected_ids.add(q.question_id)

    # Greedy pass: pick the best question that adds new coverage.
    while len(selected) < k:
        progressed = False
        for score, components, q in _score_pool():
            if score < min_score:
                break
            if not _adds_coverage(q, state):
                continue
            _take(score, components, q)
            state = state.with_question(q)
            progressed = True
            break
        if not progressed:
            break

    # Hard-constraint enforcement: add the best unselected question that
    # satisfies each missing constraint (even without new coverage).
    def _constraints() -> Dict[str, bool]:
        has_discriminator = any(
            score_components(q, ctx, gap_by_id, SelectionState(), total_aspects, history_questions)["D"] > 0
            for q in selected
        )
        has_measurable = any(
            score_components(q, ctx, gap_by_id, SelectionState(), total_aspects, history_questions)["E"] >= 1.0
            for q in selected
        )
        branches = {q.m4_branch for q in selected if q.m4_branch}
        return {
            "discriminator": has_discriminator,
            "measurable_evidence": has_measurable,
            "m4_branches_ge_3": len(branches) >= 3,
        }

    def _add_best(predicate) -> bool:
        for score, components, q in _score_pool():
            if predicate(q, components):
                _take(score, components, q)
                forced_ids.append(q.question_id)
                return True
        return False

    forced_ids: List[str] = []
    constraints = _constraints()
    if not constraints["discriminator"]:
        _add_best(lambda q, c: c["D"] > 0)
    if not constraints["measurable_evidence"]:
        _add_best(lambda q, c: c["E"] >= 1.0)
    if not constraints["m4_branches_ge_3"]:
        # Add best 4M questions until 3 branches are covered (or pool exhausted).
        while True:
            branches = {q.m4_branch for q in selected if q.m4_branch}
            if len(branches) >= 3:
                break
            added = _add_best(
                lambda q, c: bool(q.m4_branch) and q.m4_branch not in {s.m4_branch for s in selected if s.m4_branch}
            )
            if not added:
                break
    constraints = _constraints()

    # Update state to reflect the final selection (for the budget check).
    for q in selected:
        state = state.with_question(q)

    # Final budget guardrail from the existing engine.
    for index, q in enumerate(selected):
        validate_candidate_question(q.text, [s.text for s in selected[:index]], index, max(k, len(selected)))

    return SelectionResult(
        phenomenon=ctx.phenomenon,
        selected=tuple(selected),
        rejected_count=rejected,
        constraints_met=constraints,
        min_score=min_score,
        forced_question_ids=tuple(forced_ids),
    )
