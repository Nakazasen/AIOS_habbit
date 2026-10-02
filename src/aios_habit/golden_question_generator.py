"""Deterministic golden-question candidate generator.

Builds candidate questions from (per design doc section 3.2, step 1):
1. Existing seeds: generate_seed_questions(gap) from adaptive_interview_engine.
2. 4M templates (TEMPLATES_4M) bound to the concrete phenomenon.
3. Why-Why skeleton (build_why_chain) with a demand for measurable evidence.
4. New causal templates (~10 kinds) bound to phenomenon + hypothesis sets.

No LLM is used here; everything is deterministic so the batch is reproducible.
Scoring/selection lives in golden_question_scorer.py.

Python 3.11 compatible.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Sequence, Tuple

from aios_habit.adaptive_interview_engine import generate_seed_questions
from aios_habit.error_cases.investigation_tree import (
    BRANCHES,
    TEMPLATES_4M,
    build_why_chain,
)
from aios_habit.expert_interview_models import SeedQuestion
from aios_habit.knowledge_coverage import (
    GAP_TYPE_CONFLICT,
    GAP_TYPE_MISSING_CONDITION,
    GAP_TYPE_MISSING_EXAMPLE,
    GAP_TYPE_MISSING_EXCEPTION,
    GAP_TYPE_MISSING_THRESHOLD,
    GAP_TYPE_STALE_KNOWLEDGE,
    KnowledgeGapCandidate,
)

from aios_habit.golden_question_schema import (
    LOAI_BEFORE_AFTER,
    LOAI_CAUSAL_MECHANISM,
    LOAI_DISCRIMINATOR,
    LOAI_EVIDENCE_CONFIRM,
    LOAI_EVIDENCE_REFUTE,
    LOAI_EXCEPTION,
    LOAI_M4_MACHINE,
    LOAI_M4_MAN,
    LOAI_M4_MATERIAL,
    LOAI_M4_METHOD,
    LOAI_PERM_COUNTERMEASURE,
    LOAI_PHENOMENON,
    LOAI_RECURRENCE,
    LOAI_RELATED_CASE,
    LOAI_TEMP_COUNTERMEASURE,
    LOAI_TIMELINE,
    GoldenQuestion,
)


class GoldenGenerationError(ValueError):
    """Raised when candidate generation cannot proceed on the given input."""


@dataclass(frozen=True)
class Hypothesis:
    """One cause hypothesis extracted from real error cases."""

    hypothesis_id: str
    text: str

    def __post_init__(self) -> None:
        if not self.hypothesis_id.strip() or not self.text.strip():
            raise GoldenGenerationError("Giả thuyết phải có mã và nội dung.")


@dataclass(frozen=True)
class PhenomenonContext:
    """Everything the generator needs for one real error phenomenon."""

    batch_id: str
    error_code: str
    phenomenon: str
    case_ids: Tuple[str, ...]
    error_group: str = "F CALL"
    model_line_station: str = ""
    gaps: Tuple[KnowledgeGapCandidate, ...] = ()
    hypotheses: Tuple[Hypothesis, ...] = ()
    hypothesis_source_note: str = ""

    def __post_init__(self) -> None:
        if not self.batch_id.strip():
            raise GoldenGenerationError("batch_id không được để trống.")
        if not self.phenomenon.strip():
            raise GoldenGenerationError("phenomenon không được để trống.")
        if not self.case_ids:
            raise GoldenGenerationError(
                "Pilot bắt buộc dùng hiện tượng F CALL thật: case_ids không được rỗng."
            )


# Map (gap_type, seed suggested_order) -> loai_cau_hoi for reused seeds.
_SEED_LOAI_MAP: Dict[Tuple[str, int], str] = {
    (GAP_TYPE_MISSING_THRESHOLD, 1): LOAI_EVIDENCE_CONFIRM,
    (GAP_TYPE_MISSING_THRESHOLD, 2): LOAI_EVIDENCE_CONFIRM,
    (GAP_TYPE_MISSING_THRESHOLD, 3): LOAI_EXCEPTION,
    (GAP_TYPE_CONFLICT, 1): LOAI_PHENOMENON,
    (GAP_TYPE_CONFLICT, 2): LOAI_EVIDENCE_CONFIRM,
    (GAP_TYPE_MISSING_CONDITION, 1): LOAI_TIMELINE,
    (GAP_TYPE_MISSING_CONDITION, 2): LOAI_EVIDENCE_CONFIRM,
}

_SEED_EVIDENCE_MAP: Dict[Tuple[str, int], Tuple[str, ...]] = {
    (GAP_TYPE_MISSING_THRESHOLD, 1): ("numerical_threshold",),
    (GAP_TYPE_MISSING_THRESHOLD, 2): ("unit",),
    (GAP_TYPE_MISSING_THRESHOLD, 3): ("description",),
    (GAP_TYPE_CONFLICT, 1): ("description",),
    (GAP_TYPE_CONFLICT, 2): ("document",),
    (GAP_TYPE_MISSING_CONDITION, 1): ("description",),
    (GAP_TYPE_MISSING_CONDITION, 2): ("measurement",),
}

_M4_LOAI: Dict[str, str] = {
    "Man": LOAI_M4_MAN,
    "Machine": LOAI_M4_MACHINE,
    "Material": LOAI_M4_MATERIAL,
    "Method": LOAI_M4_METHOD,
}

# Preferred gap types per question kind (for target_gap_id binding).
_LOAI_GAP_PREFERENCE: Dict[str, Tuple[str, ...]] = {
    LOAI_DISCRIMINATOR: (GAP_TYPE_CONFLICT, GAP_TYPE_MISSING_CONDITION, GAP_TYPE_MISSING_THRESHOLD),
    LOAI_EVIDENCE_CONFIRM: (GAP_TYPE_MISSING_THRESHOLD, GAP_TYPE_MISSING_CONDITION, GAP_TYPE_CONFLICT),
    LOAI_EVIDENCE_REFUTE: (GAP_TYPE_MISSING_THRESHOLD, GAP_TYPE_MISSING_CONDITION, GAP_TYPE_CONFLICT),
    LOAI_EXCEPTION: (GAP_TYPE_MISSING_EXCEPTION, GAP_TYPE_MISSING_CONDITION),
    LOAI_TIMELINE: (GAP_TYPE_MISSING_CONDITION,),
    LOAI_BEFORE_AFTER: (GAP_TYPE_MISSING_CONDITION, GAP_TYPE_STALE_KNOWLEDGE),
    LOAI_TEMP_COUNTERMEASURE: (GAP_TYPE_MISSING_CONDITION, GAP_TYPE_MISSING_EXAMPLE),
    LOAI_PERM_COUNTERMEASURE: (GAP_TYPE_MISSING_CONDITION, GAP_TYPE_MISSING_EXAMPLE),
    LOAI_RECURRENCE: (GAP_TYPE_MISSING_CONDITION,),
    LOAI_RELATED_CASE: (GAP_TYPE_MISSING_EXAMPLE, GAP_TYPE_MISSING_CONDITION),
    LOAI_PHENOMENON: (GAP_TYPE_MISSING_CONDITION, GAP_TYPE_MISSING_EXAMPLE),
    LOAI_CAUSAL_MECHANISM: (GAP_TYPE_MISSING_CONDITION, GAP_TYPE_CONFLICT),
}

_MEASURABLE_EVIDENCE = ("numerical_threshold", "unit", "log", "photo", "trend", "measurement")


def default_gap_for_phenomenon(ctx: PhenomenonContext) -> KnowledgeGapCandidate:
    """Build a fallback gap when a phenomenon has no detected gaps yet.

    Grounded in the real case ids (evidence_refs), never invented.
    """
    code = ctx.error_code.strip() or "UNKNOWN"
    return KnowledgeGapCandidate(
        gap_id="GAP-%s-%s" % (ctx.batch_id, code),
        collection_id="error_cases",
        scope=ctx.error_group,
        title="Thiếu tri thức điều tra cho hiện tượng: %s" % ctx.phenomenon,
        description=(
            "Hiện tượng '%s' (mã %s) chưa có tri thức điều tra đầy đủ "
            "(điều kiện, ngưỡng, ngoại lệ)." % (ctx.phenomenon, code)
        ),
        gap_type=GAP_TYPE_MISSING_CONDITION,
        evidence_refs=tuple(ctx.case_ids),
        priority="high",
    )


def _pick_gap_id(loai: str, gaps: Sequence[KnowledgeGapCandidate]) -> str:
    preferred = _LOAI_GAP_PREFERENCE.get(loai, ())
    for gap_type in preferred:
        for gap in gaps:
            if gap.gap_type == gap_type:
                return gap.gap_id
    return gaps[0].gap_id


def _evidence_from_collect_text(collect_text: str) -> Tuple[str, ...]:
    """Map the 4M 'data to collect' hint to evidence vocabulary."""
    lowered = collect_text.lower()
    found = []
    if any(k in lowered for k in ("log", "biểu đồ", "trend", "ghi nhận")):
        found.append("log")
    if any(k in lowered for k in ("ảnh", "chụp")):
        found.append("photo")
    if any(k in lowered for k in ("số", "đo", "thông số", "giờ")):
        found.append("measurement")
    if any(k in lowered for k in ("sop", "tài liệu", "phiếu", "biên bản", "hồ sơ", "bản ghi")):
        found.append("document")
    if not found:
        found.append("description")
    return tuple(found)


def _seed_to_golden(
    seed: SeedQuestion,
    ctx: PhenomenonContext,
    question_id: str,
    gap: KnowledgeGapCandidate,
) -> GoldenQuestion:
    key = (gap.gap_type, seed.suggested_order)
    loai = _SEED_LOAI_MAP.get(key, LOAI_PHENOMENON)
    evidence = _SEED_EVIDENCE_MAP.get(key, ("description",))
    aspects = ", ".join(seed.expected_aspects) if seed.expected_aspects else loai
    return GoldenQuestion(
        question_id=question_id,
        text=seed.text,
        target_gap_id=gap.gap_id,
        target_case_ids=ctx.case_ids,
        loai_cau_hoi=loai,
        muc_tieu="Lấp khoảng trống '%s' ở khía cạnh: %s." % (gap.title, aspects),
        gia_thuyet_lien_quan=(),
        expected_evidence=evidence,
        batch_id=ctx.batch_id,
    )


def _m4_to_golden(
    branch: str,
    template_question: str,
    collect_text: str,
    ctx: PhenomenonContext,
    question_id: str,
    gaps: Sequence[KnowledgeGapCandidate],
) -> GoldenQuestion:
    loai = _M4_LOAI[branch]
    evidence = _evidence_from_collect_text(collect_text)
    text = "%s (xét trên hiện tượng: '%s')" % (template_question, ctx.phenomenon)
    if set(evidence) & set(_MEASURABLE_EVIDENCE):
        # A measurable 4M question must demand a concrete value (design 3.2:
        # E = 1.0 only when the question asks for a specific value).
        text += " Nêu giá trị cụ thể kèm đơn vị đo."
    return GoldenQuestion(
        question_id=question_id,
        text=text,
        target_gap_id=_pick_gap_id(loai, gaps),
        target_case_ids=ctx.case_ids,
        loai_cau_hoi=loai,
        muc_tieu="Xác minh nhánh 4M %s cho hiện tượng '%s'." % (branch, ctx.phenomenon),
        gia_thuyet_lien_quan=(),
        expected_evidence=_evidence_from_collect_text(collect_text),
        m4_branch=branch,
        batch_id=ctx.batch_id,
    )


def _why_to_golden(
    level: int,
    why_question: str,
    ctx: PhenomenonContext,
    question_id: str,
    gaps: Sequence[KnowledgeGapCandidate],
) -> GoldenQuestion:
    text = "%s Trả lời kèm bằng chứng đo được cụ thể (số đo/log/ảnh), không trả lời chung chung." % why_question
    return GoldenQuestion(
        question_id=question_id,
        text=text,
        target_gap_id=_pick_gap_id(LOAI_CAUSAL_MECHANISM, gaps),
        target_case_ids=ctx.case_ids,
        loai_cau_hoi=LOAI_CAUSAL_MECHANISM,
        muc_tieu="Đào sâu chuỗi Why-Why tới tầng %d cho hiện tượng '%s'." % (level, ctx.phenomenon),
        gia_thuyet_lien_quan=tuple(h.hypothesis_id for h in ctx.hypotheses),
        expected_evidence=("measurement", "description"),
        why_level=level,
        batch_id=ctx.batch_id,
    )


# Causal templates: (loai_cau_hoi, text_template, muc_tieu_template, evidence).
# {phenomenon}, {H}, {H1}, {H2}, {param} are bound at generation time.
_CAUSAL_TEMPLATES: Tuple[Tuple[str, str, str, Tuple[str, ...]], ...] = (
    (
        LOAI_DISCRIMINATOR,
        "Giữa hai giả thuyết '{H1}' và '{H2}', dấu hiệu đo được nào phân biệt được hai khả năng này?",
        "Buộc người trả lời đưa ra phép thử phân biệt thay vì trả lời chung chung 'kiểm tra cả hai'.",
        ("measurement", "log"),
    ),
    (
        LOAI_EVIDENCE_CONFIRM,
        "Bằng chứng đo được nào (số đo/log/ảnh) sẽ XÁC NHẬN giả thuyết '{H}' cho hiện tượng '{phenomenon}'?",
        "Thu thập tiêu chí xác nhận cụ thể cho từng giả thuyết.",
        ("measurement", "log", "photo"),
    ),
    (
        LOAI_EVIDENCE_REFUTE,
        "Kết quả đo nào sẽ BÁC BỎ giả thuyết '{H}' cho hiện tượng '{phenomenon}'?",
        "Thu thập tiêu chí bác bỏ để loại giả thuyết sai sớm.",
        ("measurement", "log"),
    ),
    (
        LOAI_BEFORE_AFTER,
        "Trước khi xuất hiện '{phenomenon}', máy/công đoạn có thay đổi gì (thay linh kiện, đổi lot, chỉnh thông số, mất điện)? Giá trị trước–sau cụ thể?",
        "Bắt timeline thay đổi — manh mối nhân quả hay bị bỏ sót nhất.",
        ("description", "log"),
    ),
    (
        LOAI_TIMELINE,
        "'{phenomenon}' xuất hiện ở thời điểm/điều kiện nào: khởi động, đang chạy, đổi lot, đổi ca?",
        "Xác định điều kiện xuất hiện của hiện tượng.",
        ("description",),
    ),
    (
        LOAI_RECURRENCE,
        "Điều kiện nào thì '{phenomenon}' tái phát 100%? Điều kiện nào thì không tái phát?",
        "Xác định điều kiện tái phát để kiểm chứng nhân quả.",
        ("description", "log"),
    ),
    (
        LOAI_EXCEPTION,
        "Trường hợp nào '{phenomenon}' KHÔNG xảy ra dù điều kiện tương tự?",
        "Tìm ngoại lệ để thu hẹp phạm vi nguyên nhân.",
        ("description",),
    ),
    (
        LOAI_TEMP_COUNTERMEASURE,
        "Đối sách tạm thời cho '{phenomenon}' là gì? Ai làm, khi nào xong?",
        "Thu thập đối sách tạm thời khả thi ngay.",
        ("description",),
    ),
    (
        LOAI_PERM_COUNTERMEASURE,
        "Đối sách lâu dài để '{phenomenon}' không tái phát là gì? Ai làm, khi nào xong?",
        "Thu thập đối sách lâu dài.",
        ("description",),
    ),
    (
        LOAI_RELATED_CASE,
        "Ca lỗi nào trước đây giống '{phenomenon}' nhất? Kết luận điều tra khi đó là gì?",
        "Tận dụng kinh nghiệm các ca tương tự.",
        ("document", "description"),
    ),
    (
        LOAI_PHENOMENON,
        "Mô tả chính xác '{phenomenon}': mã hiển thị, tiếng kêu, mùi, vị trí, tần suất?",
        "Chuẩn hóa mô tả hiện tượng trước khi điều tra.",
        ("photo", "description"),
    ),
)


def _render_causal_templates(ctx: PhenomenonContext) -> List[GoldenQuestion]:
    """Render causal templates bound to phenomenon + hypotheses (no ids yet)."""
    out: List[GoldenQuestion] = []
    hyps = list(ctx.hypotheses)
    for loai, text_tpl, muc_tieu_tpl, evidence in _CAUSAL_TEMPLATES:
        if loai == LOAI_DISCRIMINATOR:
            if len(hyps) < 2:
                continue
            for h1, h2 in combinations(hyps, 2):
                text = text_tpl.format(H1=h1.text, H2=h2.text)
                out.append(
                    GoldenQuestion(
                        question_id="PENDING",
                        text=text,
                        target_gap_id="PENDING",
                        target_case_ids=ctx.case_ids,
                        loai_cau_hoi=loai,
                        muc_tieu=muc_tieu_tpl,
                        gia_thuyet_lien_quan=(h1.hypothesis_id, h2.hypothesis_id),
                        expected_evidence=evidence,
                        discriminant_pairs=((h1.hypothesis_id, h2.hypothesis_id),),
                        batch_id=ctx.batch_id,
                    )
                )
        elif loai in (LOAI_EVIDENCE_CONFIRM, LOAI_EVIDENCE_REFUTE):
            if not hyps:
                continue
            for h in hyps:
                text = text_tpl.format(H=h.text, phenomenon=ctx.phenomenon)
                out.append(
                    GoldenQuestion(
                        question_id="PENDING",
                        text=text,
                        target_gap_id="PENDING",
                        target_case_ids=ctx.case_ids,
                        loai_cau_hoi=loai,
                        muc_tieu=muc_tieu_tpl,
                        gia_thuyet_lien_quan=(h.hypothesis_id,),
                        expected_evidence=evidence,
                        batch_id=ctx.batch_id,
                    )
                )
        else:
            text = text_tpl.format(phenomenon=ctx.phenomenon)
            out.append(
                GoldenQuestion(
                    question_id="PENDING",
                    text=text,
                    target_gap_id="PENDING",
                    target_case_ids=ctx.case_ids,
                    loai_cau_hoi=loai,
                    muc_tieu=muc_tieu_tpl,
                    gia_thuyet_lien_quan=tuple(h.hypothesis_id for h in hyps),
                    expected_evidence=evidence,
                    batch_id=ctx.batch_id,
                )
            )
    return out


def generate_candidates(
    ctx: PhenomenonContext,
    start_index: int = 1,
) -> List[GoldenQuestion]:
    """Generate all candidate golden questions for one phenomenon (deterministic).

    Order: reused seeds -> 4M-bound -> Why chain -> causal templates.
    Question ids are assigned sequentially: GQ-<batch_id>-<n>.
    """
    gaps = list(ctx.gaps) or [default_gap_for_phenomenon(ctx)]
    gap_by_id = {g.gap_id: g for g in gaps}

    pending: List[GoldenQuestion] = []

    # 1. Reused seeds from the existing interview engine.
    for gap in gaps:
        for seed in generate_seed_questions(gap):
            pending.append((_seed_to_golden(seed, ctx, "PENDING", gap), gap.gap_id))

    # 2. 4M templates bound to the phenomenon.
    for branch in BRANCHES:
        for template_question, collect_text in TEMPLATES_4M[branch]:
            q = _m4_to_golden(branch, template_question, collect_text, ctx, "PENDING", gaps)
            pending.append((q, q.target_gap_id))

    # 3. Why-Why chain with measurable-evidence demand.
    for node in build_why_chain(ctx.phenomenon):
        q = _why_to_golden(node.level, node.question, ctx, "PENDING", gaps)
        pending.append((q, q.target_gap_id))

    # 4. Causal templates.
    for q in _render_causal_templates(ctx):
        gap_id = _pick_gap_id(q.loai_cau_hoi, gaps)
        pending.append((q, gap_id))

    # Assign sequential ids and final gap binding.
    result: List[GoldenQuestion] = []
    index = start_index
    for q, gap_id in pending:
        question_id = "GQ-%s-%02d" % (ctx.batch_id, index)
        index += 1
        result.append(
            GoldenQuestion(
                question_id=question_id,
                text=q.text,
                target_gap_id=gap_id,
                target_case_ids=q.target_case_ids,
                loai_cau_hoi=q.loai_cau_hoi,
                muc_tieu=q.muc_tieu,
                gia_thuyet_lien_quan=q.gia_thuyet_lien_quan,
                expected_evidence=q.expected_evidence,
                discriminant_pairs=q.discriminant_pairs,
                m4_branch=q.m4_branch,
                why_level=q.why_level,
                batch_id=q.batch_id,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Wire-in: golden questions as seed questions for the adaptive interview engine
# ---------------------------------------------------------------------------

# Aspect tags per loai_cau_hoi, used as SeedQuestion.expected_aspects.
ASPECT_OF_LOAI: Dict[str, Tuple[str, ...]] = {
    LOAI_PHENOMENON: ("mo_ta_hien_tuong",),
    LOAI_TIMELINE: ("thoi_diem_dieu_kien",),
    LOAI_BEFORE_AFTER: ("thay_doi_truoc_sau",),
    LOAI_M4_MAN: ("nhan_su_4m",),
    LOAI_M4_MACHINE: ("may_moc_4m",),
    LOAI_M4_MATERIAL: ("vat_lieu_4m",),
    LOAI_M4_METHOD: ("phuong_phap_4m",),
    LOAI_CAUSAL_MECHANISM: ("co_che_why",),
    LOAI_EVIDENCE_CONFIRM: ("bang_chung_xac_nhan",),
    LOAI_EVIDENCE_REFUTE: ("bang_chung_bac_bo",),
    LOAI_DISCRIMINATOR: ("phan_biet_gia_thuyet",),
    LOAI_EXCEPTION: ("ngoai_le",),
    LOAI_TEMP_COUNTERMEASURE: ("doi_sach_tam_thoi",),
    LOAI_PERM_COUNTERMEASURE: ("doi_sach_lau_dai",),
    LOAI_RECURRENCE: ("dieu_kien_tai_phat",),
    LOAI_RELATED_CASE: ("ca_lien_quan",),
}


def golden_to_seed_questions(
    questions: Sequence[GoldenQuestion],
) -> Tuple[SeedQuestion, ...]:
    """Convert golden questions to SeedQuestion, keyed by the existing gap system.

    target_gap_id links back to KnowledgeGapCandidate.gap_id, so the adaptive
    interview engine can consume golden questions through its normal seed flow.
    """
    seeds: List[SeedQuestion] = []
    for order, q in enumerate(questions, 1):
        aspects = ASPECT_OF_LOAI.get(q.loai_cau_hoi, (q.loai_cau_hoi,))
        seeds.append(
            SeedQuestion(
                question_id=q.question_id,
                text=q.text,
                target_gap_id=q.target_gap_id,
                expected_aspects=aspects,
                suggested_order=order,
            )
        )
    return tuple(seeds)
