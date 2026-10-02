"""Tests for golden_question_scorer: weights, components, guardrails, constraints."""
from __future__ import annotations

import pytest

from aios_habit.adaptive_interview_engine import generate_seed_questions_with_golden
from aios_habit.golden_question_generator import (
    Hypothesis,
    PhenomenonContext,
    default_gap_for_phenomenon,
    generate_candidates,
)
from aios_habit.golden_question_schema import (
    LOAI_DISCRIMINATOR,
    GoldenQuestion,
)
from aios_habit.golden_question_scorer import (
    WEIGHTS,
    SelectionState,
    score_components,
    select_top_k,
    total_score,
)
from aios_habit.knowledge_coverage import KnowledgeGapCandidate


def _ctx(**overrides):
    data = {
        "batch_id": "KB-SCORER",
        "error_code": "F000",
        "phenomenon": "Khi khởi động, màn hình LCD hiển thị F000",
        "case_ids": ("2023/183",),
        "hypotheses": (
            Hypothesis("H1", "lỗi bo mạch điều khiển"),
            Hypothesis("H2", "sụt áp nguồn cấp lúc khởi động"),
        ),
    }
    data.update(overrides)
    ctx = PhenomenonContext(**data)
    gaps = list(ctx.gaps) or [default_gap_for_phenomenon(ctx)]
    return PhenomenonContext(
        batch_id=ctx.batch_id,
        error_code=ctx.error_code,
        phenomenon=ctx.phenomenon,
        case_ids=ctx.case_ids,
        error_group=ctx.error_group,
        model_line_station=ctx.model_line_station,
        gaps=tuple(gaps),
        hypotheses=ctx.hypotheses,
        hypothesis_source_note=ctx.hypothesis_source_note,
    )


def _gap_map(ctx):
    return {g.gap_id: g for g in ctx.gaps}


def _total_aspects(candidates):
    from aios_habit.golden_question_generator import ASPECT_OF_LOAI

    aspects = set()
    for q in candidates:
        aspects.update(ASPECT_OF_LOAI.get(q.loai_cau_hoi, ()))
    return len(aspects)


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    assert WEIGHTS["D"] == 0.30
    assert WEIGHTS["G"] == 0.20
    assert WEIGHTS["E"] == 0.20
    assert WEIGHTS["W"] == 0.15
    assert WEIGHTS["N"] == 0.10
    assert WEIGHTS["F"] == 0.05


def test_discriminator_scores_full_d():
    ctx = _ctx()
    candidates = generate_candidates(ctx)
    disc = next(q for q in candidates if q.loai_cau_hoi == LOAI_DISCRIMINATOR)
    components = score_components(
        disc, ctx, _gap_map(ctx), SelectionState(), _total_aspects(candidates), ()
    )
    # One hypothesis pair, one discriminant pair -> D == 1.0.
    assert components["D"] == 1.0
    assert total_score(components) >= 30.0  # D alone contributes 30 points


def test_measurable_evidence_scores_e_full():
    ctx = _ctx()
    candidates = generate_candidates(ctx)
    gap_map = _gap_map(ctx)
    total_aspects = _total_aspects(candidates)
    best_e = max(
        score_components(q, ctx, gap_map, SelectionState(), total_aspects, ())["E"]
        for q in candidates
    )
    assert best_e == 1.0, "generator must produce at least one measurable question"


def test_infeasible_keyword_penalizes_f():
    ctx = _ctx()
    gap_id = ctx.gaps[0].gap_id
    q = GoldenQuestion(
        question_id="GQ-X-01",
        text="Có cần tháo máy chạy thử để kiểm tra hiện tượng này không, giá trị đo là bao nhiêu?",
        target_gap_id=gap_id,
        target_case_ids=("2023/183",),
        loai_cau_hoi="phenomenon",
        muc_tieu="Kiểm tra F.",
        expected_evidence=("measurement",),
    )
    components = score_components(q, ctx, _gap_map(ctx), SelectionState(), 16, ())
    assert components["F"] == 0.5


def test_leading_question_rejected_from_selection():
    ctx = _ctx()
    gap_id = ctx.gaps[0].gap_id
    leading = GoldenQuestion(
        question_id="GQ-X-LEAD",
        text="Chắc chắn là do bo mạch hỏng phải không, hãy xác nhận giúp?",
        target_gap_id=gap_id,
        target_case_ids=("2023/183",),
        loai_cau_hoi="phenomenon",
        muc_tieu="Dẫn dắt.",
    )
    result = select_top_k(ctx, [leading], k=1, min_score=0.0)
    assert result.selected == ()
    assert result.rejected_count == 1


def test_semantic_duplicate_rejected():
    ctx = _ctx()
    candidates = generate_candidates(ctx)[:5]
    history = [candidates[0].text]
    result = select_top_k(ctx, candidates, k=3, min_score=0.0, history_questions=history)
    selected_texts = [q.text for q in result.selected]
    assert candidates[0].text not in selected_texts


def test_selection_meets_hard_constraints():
    ctx = _ctx()
    candidates = generate_candidates(ctx)
    result = select_top_k(ctx, candidates, k=3, min_score=55.0)
    assert result.constraints_met["discriminator"]
    assert result.constraints_met["measurable_evidence"]
    assert result.constraints_met["m4_branches_ge_3"]
    assert len(result.selected) >= 3
    # Greedy picks respect the floor; hard-constraint force-adds (design 3.2)
    # may go below it to satisfy the hard coverage requirements.
    for q in result.selected:
        if q.question_id not in result.forced_question_ids:
            assert q.diem >= 55.0
    for q in result.selected:
        assert set(q.diem_thanh_phan.keys()) == {"D", "G", "E", "W", "N", "F"}


def test_selection_scores_descend_greedily():
    ctx = _ctx()
    candidates = generate_candidates(ctx)
    result = select_top_k(ctx, candidates, k=3, min_score=55.0)
    scores = [q.diem for q in result.selected[:3]]
    assert scores == sorted(scores, reverse=True)


def test_min_score_blocks_greedy_but_not_hard_constraints():
    # With an unreachable floor the greedy pass picks nothing, but the hard
    # per-phenomenon constraints (design 3.2: "ràng buộc cứng") still
    # force-add the best discriminator / measurable / 4M questions.
    ctx = _ctx()
    candidates = generate_candidates(ctx)
    result = select_top_k(ctx, candidates, k=3, min_score=100.0)
    assert result.selected, "hard constraints must still be satisfied"
    assert all(q.diem < 100.0 for q in result.selected)
    assert result.constraints_met["discriminator"]


def test_wire_in_golden_questions_become_seeds_keyed_by_gap():
    ctx = _ctx()
    candidates = generate_candidates(ctx)
    result = select_top_k(ctx, candidates, k=3, min_score=55.0)
    gap = ctx.gaps[0]
    seeds = generate_seed_questions_with_golden(gap, result.selected)
    golden_ids = {q.question_id for q in result.selected if q.target_gap_id == gap.gap_id}
    seed_ids = [s.question_id for s in seeds]
    for gid in golden_ids:
        assert gid in seed_ids
    # Golden seeds come first, legacy seeds fill the rest.
    assert seed_ids[0] in golden_ids
    # No duplicate question texts.
    assert len({s.text for s in seeds}) == len(seeds)
