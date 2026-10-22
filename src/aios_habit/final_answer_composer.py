from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from aios_habit.domain_playbooks import GENERAL_PLAYBOOK, get_domain_playbook, select_domain_playbook
from aios_habit.question_intent_classifier import (
    INTENT_MO_HO,
    INTENT_TONG_HOP,
    INTENT_TONG_QUAN,
    INTENT_TRA_CUU,
    classify_question_intent,
    suggest_rephrasings,
)
from aios_habit.rag_core_profiles import normalize_profile_id
from aios_habit.rag_evidence import RAGEvidenceItem, RAGEvidencePack
from aios_habit.source_router import classify_query_profile, route_evidence_by_profile

# 5-Tier Answer Ladder Constants (DESKTOP-SELF-LEARN-5TIER-ANSWER-LADDER)
TIER_1_DIRECT = 1
TIER_2_SYNTHESIS = 2
TIER_3_AMBIGUOUS = 3
TIER_4_INFERRED = 4
TIER_5_ACTIONS = 5

TIER_NAMES = {
    TIER_1_DIRECT: "Bậc 1: Trả lời trực tiếp có bằng chứng trích dẫn",
    TIER_2_SYNTHESIS: "Bậc 2: Tổng hợp đa nguồn có bằng chứng",
    TIER_3_AMBIGUOUS: "Bậc 3: Gợi ý diễn đạt lại & trả lời giả định",
    TIER_4_INFERRED: "Bậc 4: Trả lời bằng suy luận AI có nhãn cảnh báo",
    TIER_5_ACTIONS: "Bậc 5: Đính kèm nút hành động tiếp nối",
}

# Mandatory fixed warning label for Tier 4 (non-negotiable per ticket requirement)
TIER_4_WARNING_BANNER = (
    "> ⚠️ **LƯU Ý: CÂU TRẢ LỜI ĐƯỢC SUY LUẬN TỰ ĐỘNG BỞI AI**  \n"
    "> *Nội dung này hiện CHƯA CÓ trong kho tri thức nội bộ của công ty. "
    "Đây chỉ là nhận định kỹ thuật chung mang tính tham khảo. "
    "Bạn nên kiểm chứng lại với tài liệu thiết kế gốc hoặc chuyên gia phụ trách.*"
)

ACTION_TEACH_AIOS = "teach_aios"
ACTION_ASK_EXPERT = "ask_expert"
ACTION_ASK_EXTERNAL_AI = "ask_external_ai"

TIER_5_DEFAULT_ACTIONS: List[Dict[str, str]] = [
    {
        "id": ACTION_TEACH_AIOS,
        "label": "🎓 Dạy AIOS điều này",
        "description": "Bổ sung thông tin chuẩn xác vào kho tri thức cá nhân hoặc công ty",
    },
    {
        "id": ACTION_ASK_EXPERT,
        "label": "👨‍💼 Hỏi chuyên gia miền",
        "description": "Chuyển thắc mắc vào hàng đợi của kỹ sư/chuyên gia phụ trách",
    },
    {
        "id": ACTION_ASK_EXTERNAL_AI,
        "label": "🌐 Hỏi AI ngoài",
        "description": "Chuyển ngữ cảnh sang mô hình ngoại vi (Gemini/ChatGPT) để tham khảo",
    },
]

COLD_REFUSAL_PATTERNS = (
    "tôi không tìm thấy trong tài liệu có nội dung trả lời câu hỏi này",
    "toi khong tim thay trong tai lieu co noi dung tra loi cau hoi nay",
    "không tìm thấy dữ liệu trích xuất phù hợp trong kho tài liệu để trả lời câu hỏi này",
    "khong tim thay du lieu trich xuat phu hop trong kho tai lieu de tra loi cau hoi nay",
    "chưa tìm thấy đoạn phù hợp trong nguồn đang bật",
    "chua tim thay doan phu hop trong nguon dang bat",
)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize(
        "NFKD", (value or "").casefold().replace("đ", "d")
    )
    folded = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    return " ".join(folded.split())


def is_cold_refusal(text: str) -> bool:
    """Check if an answer text represents a cold bare refusal without 5-tier recovery."""
    folded = _fold(text)
    if not folded:
        return True
    # If the answer contains Tier 4 warning banner, Tier 3 clarification, or Tier 5 actions,
    # it is an attempted recovery and NOT a cold refusal.
    if "luu y: cau tra loi duoc suy luan tu dong boi ai" in folded:
        return False
    if "lam ro y dinh cau hoi" in folded or "neu y ban la" in folded:
        return False
    if "hanh dong tiep noi" in folded or "day aios" in folded:
        return False

    for pat in COLD_REFUSAL_PATTERNS:
        if pat in folded:
            return True
    return False


@dataclass(frozen=True)
class AnswerLadderMetrics:
    """Metrics tracking 5-tier answer ladder performance and cold refusal elimination."""

    total_queries: int = 0
    tier_1_count: int = 0
    tier_2_count: int = 0
    tier_3_count: int = 0
    tier_4_count: int = 0
    tier_5_action_count: int = 0
    cold_refusal_count: int = 0
    cold_refusal_rate: float = 0.0  # Range 0.0 - 100.0%
    rephrase_offered_count: int = 0
    rephrase_accepted_count: int = 0
    rephrase_acceptance_rate: float = 0.0  # Range 0.0 - 100.0%

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "tier_1_count": self.tier_1_count,
            "tier_2_count": self.tier_2_count,
            "tier_3_count": self.tier_3_count,
            "tier_4_count": self.tier_4_count,
            "tier_5_action_count": self.tier_5_action_count,
            "cold_refusal_count": self.cold_refusal_count,
            "cold_refusal_rate_pct": round(self.cold_refusal_rate, 2),
            "rephrase_offered_count": self.rephrase_offered_count,
            "rephrase_accepted_count": self.rephrase_accepted_count,
            "rephrase_acceptance_rate_pct": round(self.rephrase_acceptance_rate, 2),
        }


def compute_answer_ladder_metrics(records: Sequence[Dict[str, Any]]) -> AnswerLadderMetrics:
    """Compute cold refusal rate and rephrase acceptance rate across turn records."""
    total = len(records)
    if not total:
        return AnswerLadderMetrics()

    t1 = 0
    t2 = 0
    t3 = 0
    t4 = 0
    t5_actions = 0
    cold_refusals = 0
    rephrase_offered = 0
    rephrase_accepted = 0

    for rec in records:
        tier_val = rec.get("tier")
        ans_text = str(rec.get("answer_text") or rec.get("answer") or "")

        if is_cold_refusal(ans_text):
            cold_refusals += 1

        if tier_val == TIER_1_DIRECT or rec.get("tier_1"):
            t1 += 1
        elif tier_val == TIER_2_SYNTHESIS or rec.get("tier_2"):
            t2 += 1
        elif tier_val == TIER_3_AMBIGUOUS or rec.get("tier_3"):
            t3 += 1
        elif tier_val == TIER_4_INFERRED or rec.get("tier_4"):
            t4 += 1

        if rec.get("has_tier_5_actions") or "Hành động tiếp nối" in ans_text or rec.get("action_items"):
            t5_actions += 1

        if rec.get("suggested_rephrasings") or "Làm rõ ý định câu hỏi" in ans_text:
            rephrase_offered += 1
            if rec.get("rephrase_accepted") or rec.get("chosen_rephrase"):
                rephrase_accepted += 1

    cold_rate = (cold_refusals / total) * 100.0
    acc_rate = (rephrase_accepted / rephrase_offered * 100.0) if rephrase_offered > 0 else 0.0

    return AnswerLadderMetrics(
        total_queries=total,
        tier_1_count=t1,
        tier_2_count=t2,
        tier_3_count=t3,
        tier_4_count=t4,
        tier_5_action_count=t5_actions,
        cold_refusal_count=cold_refusals,
        cold_refusal_rate=cold_rate,
        rephrase_offered_count=rephrase_offered,
        rephrase_accepted_count=rephrase_accepted,
        rephrase_acceptance_rate=acc_rate,
    )


def format_tier_5_actions_markdown(actions: Sequence[Dict[str, str]] | None = None) -> str:
    """Format Tier 5 actionable follow-up buttons inside the markdown body."""
    items = actions if actions is not None else TIER_5_DEFAULT_ACTIONS
    lines = [
        "---",
        "### ⚡ Hành động tiếp nối:",
    ]
    for act in items:
        lines.append(f"- **[{act['label']}]**: {act.get('description', '')}")
    return "\n".join(lines)


def format_tier_3_ambiguous_answer(
    question: str,
    suggested_rephrasings: Sequence[str],
    provisional_answer: str = "",
    actions: Sequence[Dict[str, str]] | None = None,
) -> str:
    """Format a Tier 3 answer for ambiguous questions."""
    lines = [
        "### ❓ Làm rõ ý định câu hỏi",
        f"Câu hỏi *\"{question}\"* có phạm vi rộng hoặc chưa rõ ngữ cảnh cụ thể.",
        "",
    ]
    if provisional_answer.strip():
        best_dir = suggested_rephrasings[0] if suggested_rephrasings else "hướng suy đoán khả dĩ nhất"
        lines.extend([
            f"**Nếu ý bạn là hướng *\"{best_dir}\"*, câu trả lời tạm thời là:**",
            "",
            provisional_answer.strip(),
            "",
        ])
    if suggested_rephrasings:
        lines.extend([
            "**Nếu bạn muốn tìm hiểu theo hướng cụ thể hơn, hãy chọn một trong các gợi ý bên dưới:**",
            "",
        ])
        for idx, rephrase in enumerate(suggested_rephrasings, 1):
            lines.append(f"{idx}. 👉 **{rephrase}**")
        lines.append("")

    lines.append(format_tier_5_actions_markdown(actions))
    return "\n".join(lines)


def format_tier_4_inferred_answer(
    question: str,
    inferred_content: str,
    reasoning_steps: Sequence[str] | None = None,
    actions: Sequence[Dict[str, str]] | None = None,
) -> str:
    """Format a Tier 4 answer using AI inferred reasoning with the mandatory fixed warning banner."""
    lines = [
        TIER_4_WARNING_BANNER,
        "",
        "### 💡 Nhận định & Suy luận Kỹ thuật (Tham khảo):",
        "",
        inferred_content.strip(),
        "",
    ]
    if reasoning_steps:
        lines.extend([
            "### 🔍 Các bước khuyến nghị kiểm tra / xác thực:",
            "",
        ])
        for idx, step in enumerate(reasoning_steps, 1):
            lines.append(f"{idx}. {step}")
        lines.append("")

    lines.append(format_tier_5_actions_markdown(actions))
    return "\n".join(lines)


@dataclass
class FinalOwnerAnswer:
    draft_id: str
    pack_id: str
    query: str
    answer_text: str
    citation_ids: List[str]
    evidence_ids: List[str]
    privacy_mode: str
    allowed_external: bool
    insufficient_evidence: bool
    confidence_label: str
    warnings: List[str] = field(default_factory=list)
    composer_name: str = "deterministic_generic_rag_composer_v1"
    provider_call: bool = False
    notebooklm_call: bool = False
    answer_kind: str = "final_owner_answer"
    final_answer: bool = True
    requires_strong_model_or_human_review: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)
    # 5-Tier Response Ladder enhancements
    tier: int = TIER_1_DIRECT
    intent: str = INTENT_TRA_CUU
    suggested_rephrasings: List[str] = field(default_factory=list)
    action_items: List[Dict[str, str]] = field(default_factory=list)
    has_warning_banner: bool = False


def _stable_final_id(pack: RAGEvidencePack) -> str:
    raw = f"final:{pack.pack_id}:{pack.query}:" + "|".join(i.evidence_id for i in pack.items)
    return "FANS-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def _valid_items(pack: RAGEvidencePack, max_items: int) -> List[RAGEvidenceItem]:
    return [i for i in pack.items if i.metadata.get("_is_metadata_only") != "True"][:max_items]


def _ref_id(index: int) -> str:
    return f"[E{index}]"


def _clean(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text[: limit - 1].rstrip() + "..." if len(text) > limit else text


def _source_location(item: RAGEvidenceItem) -> str:
    parts: List[str] = []
    if item.page_numbers:
        parts.append("pages " + ",".join(map(str, item.page_numbers)))
    if item.sheet_names:
        parts.append("sheets " + ",".join(item.sheet_names))
    if item.slide_numbers:
        parts.append("slides " + ",".join(map(str, item.slide_numbers)))
    return "; ".join(parts) or item.citation_label or item.relative_path or item.source_title


def _claim_lines(items: List[RAGEvidenceItem], kind: str) -> List[str]:
    if not items:
        return ["- No extracted content evidence is available for a direct answer."]

    top = [_clean(i.snippet, 160) for i in items[:3]]
    if kind in ("extract_fields", "table_question"):
        return [
            f"- The table-like evidence relevant to the question starts here: {top[0]} [E1].",
            "- Extract the concrete table, field/column, key, value, status, or row reference before concluding.",
            "- If a required field or row is missing, mark it as missing evidence instead of guessing.",
        ]
    if kind == "procedure_steps":
        return [
            f"- The cited procedure evidence describes a step or condition: {top[0]} [E1].",
            "- Separate documented steps from events that still need logs, records, or other confirmation.",
            "- Do not turn a procedure description into proof that the event actually happened.",
        ]
    if kind == "decision_support":
        return [
            f"- The strongest cited evidence for the decision is: {top[0]} [E1].",
            "- Keep recommendations bounded by cited facts and list unresolved risks separately.",
        ]
    if kind == "image_visible_facts":
        return [
            f"- The directly visible image/OCR fact is: {top[0]} [E1].",
            "- Only use text, IDs, numbers, statuses, or objects visible in the image as image evidence.",
            "- Causes behind the image require another source; do not infer them from the image alone.",
        ]
    if kind == "image_limitations":
        return [
            f"- The image/screen evidence is: {top[0]} [E1].",
            "- The image alone cannot prove hidden system state, database state, or background process flow.",
            "- List what cannot be concluded and what source would be needed next.",
        ]
    if kind == "schema_question":
        return [
            f"- The schema/HTML/SQL evidence defines this structure: {top[0]} [E1].",
            "- List only fields, tables, keys, and relationships visible in the source.",
            "- Runtime behavior still needs logs, execution records, or operating documents.",
        ]
    if kind == "troubleshooting_general":
        return [
            f"- Start the investigation from the most directly relevant cited evidence: {top[0]} [E1].",
            "- Provide concrete checks tied to available sources, not a generic check-list.",
            "- Identify missing logs, records, screenshots, configuration, or documents explicitly.",
        ]
    if kind == "missing_evidence_general":
        return [
            f"- Current evidence is limited to: {top[0]} [E1].",
            "- Name the missing artifact/source type and explain why it is required.",
            "- Prioritize missing evidence by how directly it would answer the question.",
        ]
    if kind == "handover_general":
        return [
            f"- The handover-relevant evidence is: {top[0]} [E1].",
            "- Separate next actions, existing evidence, missing evidence, and responsible party only when the source supports it.",
            "- Do not assign responsibility or deadlines if the evidence does not state them.",
        ]
    if kind == "compare_contrast":
        return [
            f"- The first comparison anchor is: {top[0]} [E1].",
            "- Present similarities, differences, and the citation supporting each point.",
        ]
    if kind == "summarize_document":
        return [
            f"- The document summary should be anchored in: {top[0]} [E1].",
            "- Keep the summary scoped to extracted content, not filename assumptions.",
        ]
    return [
        f"- The strongest cited evidence for the question is: {top[0]} [E1].",
        "- Conclusions must stay inside the extracted content and cited source boundaries.",
    ]


def _actions(kind: str, playbook_id: str = GENERAL_PLAYBOOK) -> List[str]:
    common = [
        "1. Restate the exact question and decision needed.",
        "2. Check every claim against cited evidence [E1], [E2] before acting.",
    ]
    if kind in ("extract_fields", "table_question"):
        actions = common + [
            "3. Make a field/value/source table for the extracted facts.",
            "4. Mark absent fields, keys, rows, or values as missing evidence.",
        ]
    elif kind in ("procedure_steps", "decision_support"):
        actions = common + [
            "3. Split documented steps from checks that still require records or logs.",
            "4. Give a recommendation only when the cited evidence supports it.",
        ]
    elif kind.startswith("image_"):
        actions = common + [
            "3. Record visible facts from the image separately from inferred causes.",
            "4. Ask for another source if the question needs hidden state or causality.",
        ]
    elif kind in ("troubleshooting_general", "missing_evidence_general", "handover_general"):
        actions = common + [
            "3. Build a short timeline from the evidence: time, symptom, source, and next check.",
            "4. Collect missing evidence such as logs, records, configuration, documents, or images.",
            "5. Handover with: hypothesis, supporting evidence, missing evidence, and responsible party only if cited.",
        ]
    else:
        actions = common + [
            "3. If evidence is not enough, request the specific missing source instead of guessing.",
        ]

    if playbook_id != GENERAL_PLAYBOOK:
        playbook = get_domain_playbook(playbook_id)
        actions.extend(f"{index}. {text}" for index, text in enumerate(playbook.action_reminders, start=len(actions) + 1))
    return actions


def _understanding(kind: str) -> str:
    if kind.startswith("image_"):
        return "Visible facts are separated from inference; hidden state or cause needs another source."
    if kind in ("procedure_steps", "decision_support"):
        return "Procedure and decision answers must separate documented steps, observed events, and missing checks."
    if kind in ("extract_fields", "table_question"):
        return "Table evidence must be handled as fields, rows, keys, values, and source locations."
    if kind == "schema_question":
        return "Schema evidence proves structure only; runtime behavior needs execution evidence."
    if kind in ("troubleshooting_general", "missing_evidence_general", "handover_general"):
        return "The answer should connect symptom, cited evidence, missing artifacts, and next checks without filling gaps."
    return "The answer is bounded by extracted content, citations, and explicit uncertainty."


def determine_answer_tier(
    question: str,
    items: Sequence[RAGEvidenceItem],
    intent: str,
    insufficient_evidence: bool = False,
) -> int:
    """Determine which tier of the 5-Tier Response Ladder applies."""
    valid_items = [i for i in items if i.metadata.get("_is_metadata_only") != "True"]

    # When NO content evidence exists at all in the knowledge store
    if not valid_items:
        if intent == INTENT_MO_HO:
            return TIER_3_AMBIGUOUS
        return TIER_4_INFERRED

    # If content evidence exists:
    distinct_docs = {getattr(i, "document_id", "") or getattr(i, "source_title", "") for i in valid_items}
    if intent in (INTENT_TONG_HOP, INTENT_TONG_QUAN) or len(distinct_docs) >= 2 or len(valid_items) >= 3:
        return TIER_2_SYNTHESIS

    # Default: direct evidence-backed answer -> Tier 1
    return TIER_1_DIRECT


def compose_final_owner_answer(
    pack: RAGEvidencePack,
    target_source_type: str = "",
    case_context: str = "",
    max_items: int = 6,
    domain_playbook: str = GENERAL_PLAYBOOK,
    allow_domain_assist: bool = False,
    inferred_reasoning: str = "",
) -> FinalOwnerAnswer:
    """Compose a 5-Tier owner answer adhering strictly to the response ladder."""
    items = _valid_items(pack, max_items)
    profile = classify_query_profile(pack.query, target_source_type)
    routed = route_evidence_by_profile(items, profile, target_source_type)
    selected_playbook = select_domain_playbook(
        question=pack.query,
        corpus_texts=[i.snippet for i in items],
        requested_playbook=domain_playbook,
        allow_domain_assist=allow_domain_assist,
    )

    ordered_items = routed.primary_items + routed.supporting_items
    if not ordered_items and items:
        ordered_items = items

    kind = normalize_profile_id(profile.profile_id)
    citation_ids = [_ref_id(i + 1) for i in range(len(ordered_items))]
    evidence_ids = [i.evidence_id for i in ordered_items]

    # Classify intent & determine ladder tier
    source_titles = [i.source_title for i in ordered_items if i.source_title]
    intent_res = classify_question_intent(pack.query, context_titles=source_titles)
    active_tier = determine_answer_tier(
        pack.query,
        ordered_items,
        intent_res.intent,
        insufficient_evidence=pack.insufficient_evidence,
    )

    warnings: List[str] = routed.route_warnings.copy()
    if pack.privacy_mode == "local_only":
        warnings.append("Privacy: local_only-classified evidence (owner allows provider use since 2026-09-29).")
    if pack.insufficient_evidence or not ordered_items:
        warnings.append("Evidence is insufficient; treat this as a bounded answer with explicit gaps.")
    if routed.missing_required_source_types:
        warnings.append(f"Missing target source types: {', '.join(routed.missing_required_source_types)}.")
    if selected_playbook != GENERAL_PLAYBOOK:
        warnings.append(f"Domain playbook active: {selected_playbook}.")

    evidence_lines = []
    for idx, item in enumerate(ordered_items, 1):
        role = "Primary" if item in routed.primary_items else "Supporting"
        evidence_lines.append(
            f"- [E{idx}] [{role}] {item.source_title or item.citation_label}: {_clean(item.snippet, 170)}. "
            f"Why it matters: this source anchors a claim to {getattr(item, 'file_type', 'source')} at {_source_location(item)}."
        )

    table_rows = ["| Ref | Role | Source | Type | Location | Limitation |", "|---|---|---|---|---|---|"]
    for idx, item in enumerate(ordered_items, 1):
        role = "Primary" if item in routed.primary_items else "Supporting"
        limitation = "extracted snippet; inspect original source before final action" if len(item.text) > len(item.snippet) else "narrow evidence scope"
        table_rows.append(f"| [E{idx}] | {role} | {item.source_title or item.citation_label} | {getattr(item, 'file_type', 'unknown')} | {_source_location(item)} | {limitation} |")
    if not ordered_items:
        table_rows.append("| n/a | n/a | no extracted content evidence | n/a | n/a | source content required |")

    unsupported = [
        "- Do not conclude root cause without same-period supporting evidence.",
        "- Do not assign personal responsibility without a cited source.",
        "- Do not claim AIOS replaces NotebookLM; this is a bounded deterministic answer.",
    ]
    if not ordered_items:
        unsupported.insert(0, "- Do not conclude document content because no extracted content evidence is available.")
    if routed.missing_required_source_types:
        unsupported.insert(0, f"- REQUIRED MISSING EVIDENCE: cannot conclude fully because primary source type is missing: {', '.join(routed.missing_required_source_types)}.")

    confidence = "medium" if ordered_items and not pack.insufficient_evidence else "low"
    if len(ordered_items) >= 4 and not pack.insufficient_evidence and routed.source_type_pass == "PASS":
        confidence = "high"
    if routed.source_type_pass != "PASS":
        confidence = "low"

    tier_actions = list(TIER_5_DEFAULT_ACTIONS)
    rephrasings = intent_res.suggested_rephrasings or suggest_rephrasings(pack.query, source_titles)

    # Base sections preserving the established deterministic contract
    sections: List[str] = []
    has_banner = False

    if not ordered_items and active_tier == TIER_4_INFERRED:
        has_banner = True
        sections.append(TIER_4_WARNING_BANNER)
        sections.append("")

    if not ordered_items and active_tier == TIER_3_AMBIGUOUS:
        sections.append("### ❓ Làm rõ ý định câu hỏi")
        sections.append(f"Câu hỏi *\"{pack.query}\"* có phạm vi rộng hoặc chưa rõ ngữ cảnh cụ thể.")
        if rephrasings:
            sections.append("")
            sections.append("**Gợi ý diễn đạt lại cụ thể hơn:**")
            for idx, r in enumerate(rephrasings, 1):
                sections.append(f"{idx}. 👉 **{r}**")
        sections.append("")

    sections.extend([
        "## Ket luan ngan",
        *_claim_lines(ordered_items, kind)[:6],
        "",
        "## Cach hieu tu bang chung",
        _understanding(kind) + (f" Case context: {case_context}" if case_context else ""),
        "",
        "## Bang chung chinh",
        *(evidence_lines or ["- No [E1] content evidence is available."]),
        "",
        "## Huong xu ly / kiem tra",
        *_actions(kind, selected_playbook),
        "",
        "## Khong duoc ket luan neu chua co them bang chung",
        *unsupported,
        "",
        "## Bang nguon",
        *table_rows,
        "",
        "## Muc tin cay",
        f"{confidence}: based on {len(ordered_items)} content sources; source_type_pass={routed.source_type_pass}; privacy={pack.privacy_mode}; insufficient_evidence={pack.insufficient_evidence}; domain_playbook={selected_playbook}.",
        "",
        format_tier_5_actions_markdown(tier_actions),
    ])

    from aios_habit.answer_language_policy import purify_markdown_text
    answer_text = purify_markdown_text(
        "\n".join(sections),
        question=pack.query,
        route="final_owner_composer",
    )

    return FinalOwnerAnswer(
        draft_id=_stable_final_id(pack),
        pack_id=pack.pack_id,
        query=pack.query,
        answer_text=answer_text,
        citation_ids=citation_ids,
        evidence_ids=evidence_ids,
        privacy_mode=pack.privacy_mode,
        allowed_external=pack.allowed_external,
        insufficient_evidence=pack.insufficient_evidence or not bool(ordered_items),
        confidence_label=confidence,
        warnings=warnings,
        metadata={
            "target_source_type": target_source_type,
            "answer_profile": kind,
            "generic_profile": kind,
            "domain_playbook": selected_playbook,
            "source_type_pass": routed.source_type_pass,
            "answer_mode": "deterministic",
            "tier": str(active_tier),
            "tier_name": TIER_NAMES.get(active_tier, ""),
            "intent": intent_res.intent,
            "has_warning_banner": str(has_banner),
        },
        tier=active_tier,
        intent=intent_res.intent,
        suggested_rephrasings=rephrasings if active_tier == TIER_3_AMBIGUOUS else [],
        action_items=tier_actions,
        has_warning_banner=has_banner,
    )


def final_owner_answer_to_dict(answer: FinalOwnerAnswer) -> Dict[str, Any]:
    return asdict(answer)


import json
from pathlib import Path
import uuid


def log_ladder_turn(
    conversation_id: str,
    message_id: str,
    question: str,
    tier: int,
    intent: str,
    has_warning_banner: bool = False,
    rephrase_offered: bool = False,
    cold_refusal_avoided: bool = True,
    base_cases_dir: str | Path | None = None,
) -> Dict[str, Any]:
    """Log an answer ladder turn record to local_cases for metric tracking."""
    target_dir = Path(base_cases_dir) if base_cases_dir else Path("local_cases/answer_ladder")
    target_dir.mkdir(parents=True, exist_ok=True)
    turn_file = target_dir / "ladder_turns.jsonl"
    record = {
        "turn_id": f"TRN-{uuid.uuid4().hex[:8].upper()}",
        "conversation_id": conversation_id,
        "message_id": message_id,
        "question": question,
        "tier": tier,
        "intent": intent,
        "has_warning_banner": has_warning_banner,
        "rephrase_offered": rephrase_offered,
        "cold_refusal_avoided": cold_refusal_avoided,
        "created_at": datetime.now().isoformat(),
    }
    try:
        with turn_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return record


def record_ladder_rephrase_acceptance(
    conversation_id: str,
    message_id: str,
    chosen_rephrase: str,
    base_cases_dir: str | Path | None = None,
) -> Dict[str, Any]:
    """Record that the user accepted a suggested rephrasing from Tier 3."""
    user_id = "local_user"
    try:
        from aios_habit.answer_feedback import get_windows_identity
        user_id = get_windows_identity()
    except Exception:
        pass
    target_dir = Path(base_cases_dir) if base_cases_dir else Path("local_cases/answer_ladder")
    target_dir.mkdir(parents=True, exist_ok=True)
    event_file = target_dir / "rephrase_events.jsonl"
    record = {
        "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
        "conversation_id": conversation_id,
        "message_id": message_id,
        "user_id": user_id,
        "chosen_rephrase": chosen_rephrase,
        "created_at": datetime.now().isoformat(),
    }
    try:
        with event_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return record


def route_question_to_expert_queue(
    conversation_id: str,
    message_id: str,
    question: str,
    domain: str = "",
    base_cases_dir: str | Path | None = None,
) -> Dict[str, Any]:
    """Route a question to the domain expert queue (Tier 5 follow-up action)."""
    user_id = "local_user"
    try:
        from aios_habit.answer_feedback import get_windows_identity
        user_id = get_windows_identity()
    except Exception:
        pass
    target_dir = Path(base_cases_dir) if base_cases_dir else Path("local_cases/expert_inquiries")
    target_dir.mkdir(parents=True, exist_ok=True)
    inquiry_file = target_dir / "expert_queue.jsonl"
    record = {
        "inquiry_id": f"INQ-{uuid.uuid4().hex[:8].upper()}",
        "conversation_id": conversation_id,
        "message_id": message_id,
        "user_id": user_id,
        "question": question,
        "domain": domain or "general",
        "status": "pending_expert_review",
        "created_at": datetime.now().isoformat(),
    }
    try:
        with inquiry_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
    try:
        from aios_habit.expert_review_queue import get_expert_queue_repo, SOURCE_TIER5_INQUIRY
        get_expert_queue_repo().submit_to_queue(
            SOURCE_TIER5_INQUIRY,
            question=question,
            conversation_id=conversation_id,
            message_id=message_id,
            domain_id=domain,
            force_pass_throttle=True,
        )
    except Exception:
        pass
    return record


def deliver_5tier_ladder_answer(
    question: str,
    *,
    conversation_id: str,
    notebook_id: str = "",
    user_raw_input: str = "",
    user_message_id: str = "",
    current_ui_locale: str = "vi",
    answer_language: str = "vi",
    on_chunk: Any = None,
    inferred_reasoning: str = "",
    evidence_items: Sequence[Any] = (),
    base_cases_dir: str | Path | None = None,
) -> tuple[bool, str, dict[str, Any] | None, str | None]:
    """Deliver a 5-Tier Ladder answer (Tier 3 Ambiguous or Tier 4 Inferred) when internal evidence is absent.

    Saves user and assistant messages, persists evidence trace, streams chunks, and records ladder metrics.
    Ensures cold refusal rate stays at 0.0%.
    """
    intent_res = classify_question_intent(question)
    tier = TIER_3_AMBIGUOUS if intent_res.intent == INTENT_MO_HO else TIER_4_INFERRED
    draft_used_title = ""
    draft_body_found = ""
    from_error_cases_db = False

    # Pre-check DB error_cases for Sổ Điều tra lỗi (NB-LAZY-DTL) before Tier 3 ambiguous branch
    if not inferred_reasoning and notebook_id in ("NB-LAZY-DTL", "dieu_tra_loi"):
        try:
            from aios_habit.chat_action_error_lookup import (
                extract_codes,
                extract_filter_entities,
                is_natural_question,
                log_filter_event,
                lookup_glossary,
                resolve_db_path,
                search_similar,
                _OFFTOPIC_HINTS,
                _open_ro,
                _render_cards,
                _render_synthesized_answer,
            )
            from aios_habit.chat_action import ChatActionRequest, normalize_text

            norm = normalize_text(question)
            if not any(h in norm for h in _OFFTOPIC_HINTS):
                req_dummy = ChatActionRequest(question=question, notebook_id=notebook_id)
                db_p = resolve_db_path(req_dummy)
                if db_p:
                    conn_ec = _open_ro(db_p)
                    try:
                        codes = extract_codes(question)
                        filter_ents = extract_filter_entities(conn_ec, question)
                        has_filters = bool(
                            filter_ents.get("machine")
                            or filter_ents.get("serial")
                            or filter_ents.get("date_range")
                        )
                        if codes or has_filters:
                            gloss = lookup_glossary(conn_ec, codes) if codes else {}
                            extra = []
                            for code in codes:
                                ent = gloss.get(code, {})
                                extra.extend(
                                    str(ent.get(k) or "")
                                    for k in ("name_vi", "name_ja", "name_en", "cause", "remedy")
                                )
                            ec_cases, ec_codes, ec_total = search_similar(
                                conn_ec,
                                question,
                                extra_keywords=extra,
                                filter_entities=filter_ents,
                            )
                            if ec_cases or gloss or has_filters:
                                tier = TIER_4_INFERRED
                                from_error_cases_db = True
                                if has_filters:
                                    log_filter_event(
                                        question=question,
                                        entities={
                                            "machine": filter_ents.get("machine", {}).get("name")
                                            if filter_ents.get("machine")
                                            else None,
                                            "serial": filter_ents.get("serial"),
                                            "date_range": filter_ents.get("date_range", {}).get("label")
                                            if filter_ents.get("date_range")
                                            else None,
                                            "codes": ec_codes,
                                        },
                                        matched_count=ec_total,
                                        top_cases=ec_cases,
                                        conversation_id=conversation_id,
                                    )
                                if ec_codes and is_natural_question(question):
                                    inferred_reasoning = _render_synthesized_answer(
                                        ec_cases,
                                        ec_codes,
                                        gloss,
                                        ec_total,
                                        question,
                                        filter_entities=filter_ents,
                                    )
                                else:
                                    inferred_reasoning = _render_cards(
                                        ec_cases,
                                        ec_codes,
                                        gloss,
                                        ec_total,
                                        filter_entities=filter_ents,
                                    )
                                draft_used_title = (
                                    ec_cases[0]["bao_cao_goc"]
                                    if ec_cases and ec_cases[0].get("bao_cao_goc")
                                    else "error_cases_reconciled.db"
                                )
                    finally:
                        conn_ec.close()
        except Exception:
            pass

    if tier == TIER_3_AMBIGUOUS:
        rephrasings = intent_res.suggested_rephrasings or suggest_rephrasings(question)
        prov = inferred_reasoning or (
            f"Vấn đề bạn quan tâm liên quan đến '{question.strip()}'. "
            "Thông thường các sự cố này cần kiểm tra kết nối nguồn, tín hiệu cảm biến hoặc nhật ký lỗi gần nhất."
        )
        answer_text = format_tier_3_ambiguous_answer(
            question=question,
            suggested_rephrasings=rephrasings,
            provisional_answer=prov,
            actions=TIER_5_DEFAULT_ACTIONS,
        )
        has_banner = False
    else:
        if not inferred_reasoning:
            try:
                from aios_habit.draft_source_layer import (
                    get_draft_search_index,
                    format_draft_answer_body,
                    record_draft_invocation,
                    resolve_notebook_draft_domain,
                )
                target_domain = resolve_notebook_draft_domain(notebook_id)
                if target_domain:
                    idx = get_draft_search_index()
                    draft_hits, _ = idx.search(question, top_k=1, domain_filter=target_domain)
                    if draft_hits:
                        best_draft = draft_hits[0]
                        draft_used_title = best_draft.item.source_file
                        draft_body_found = format_draft_answer_body(best_draft.item.answer, source_name=best_draft.item.source_file)
                        record_draft_invocation(
                            best_draft.item.item_id,
                            question=question,
                            source_file=best_draft.item.source_file,
                            domain=target_domain,
                            base_cases_dir=base_cases_dir,
                        )
            except Exception:
                pass

        if not inferred_reasoning and not draft_body_found:
            try:
                from aios_habit.chat_action_error_lookup import extract_codes
                err_codes = extract_codes(question)
                if err_codes and notebook_id in ("mom_opcenter", "mom"):
                    codes_str = ", ".join(err_codes)
                    draft_body_found = (
                        f"Kho tài liệu MOM (Biên bản cuộc họp OpCenter - 44 tài liệu) hiện chưa có dữ liệu kỹ thuật về mã lỗi **{codes_str}**.\n\n"
                        f"💡 **Gợi ý**: Toàn bộ cơ sở dữ liệu điều tra lỗi sản xuất (30.075 ca KDTPS) thuộc phạm vi độc lập của **Sổ Điều tra lỗi** (`NB-LAZY-DTL`). "
                        f"Vui lòng chuyển sang **Sổ Điều tra lỗi** để tra cứu chi tiết lịch sử, hồ sơ và biện pháp xử lý cho mã lỗi {codes_str}."
                    )
            except Exception:
                pass

        inferred_body = inferred_reasoning or draft_body_found or (
            f"Về câu hỏi *'{question.strip()}'*, hệ thống chưa tìm thấy dữ liệu đối chiếu trực tiếp trong các tài liệu nội bộ đã bật. "
            "Theo nguyên lý kỹ thuật chung: Hãy xác định rõ mã thiết bị/model, kiểm tra trạng thái hoạt động trên màn hình điều khiển, "
            "đối chiếu bảng mã lỗi chuẩn và thu thập nhật ký vận hành tại thời điểm xảy ra sự cố."
        )
        steps = [
            "Kiểm tra lại tên chính xác của thiết bị hoặc tài liệu nghiệp vụ tương ứng.",
            "Đối chiếu các tham số và mã cảnh báo hiển thị trên giao diện điều khiển thực tế.",
            "Trao đổi trực tiếp với kỹ sư phụ trách miền để được cung cấp tài liệu SOP hoặc bản vẽ kỹ thuật.",
        ]
        if from_error_cases_db or (inferred_reasoning and "30.075" in inferred_reasoning):
            answer_text = inferred_reasoning
            has_banner = False
        else:
            answer_text = format_tier_4_inferred_answer(
                question=question,
                inferred_content=inferred_body,
                reasoning_steps=steps,
                actions=TIER_5_DEFAULT_ACTIONS,
            )
            has_banner = True

    from aios_habit.answer_language_policy import purify_markdown_text
    answer_text = purify_markdown_text(
        answer_text,
        question=question,
        route="5tier_ladder",
        conversation_id=conversation_id,
        base_cases_dir=base_cases_dir,
    )

    if on_chunk and answer_text:
        try:
            on_chunk(answer_text)
        except Exception:
            pass

    assistant_msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
    trace_id = f"TRC-{uuid.uuid4().hex[:8].upper()}"

    metadata = {
        "tier": tier,
        "tier_name": TIER_NAMES.get(tier, ""),
        "intent": intent_res.intent,
        "suggested_rephrasings": intent_res.suggested_rephrasings if tier == TIER_3_AMBIGUOUS else [],
        "action_items": TIER_5_DEFAULT_ACTIONS,
        "has_warning_banner": has_banner,
        "answer_mode": "5tier_ladder",
        "ladder_active": True,
        "cold_refusal_avoided": True,
        "draft_source": draft_used_title,
        "has_draft_label": bool(draft_used_title),
    }

    try:
        from aios_habit.workspace_chat_models import ChatMessage
        from aios_habit.workspace_chat_store import (
            load_messages,
            save_evidence_trace,
            save_message,
        )
        # Ensure user message exists
        existing_msgs = load_messages(conversation_id)
        has_user_msg = any(m.role == "user" and (m.content == question or m.content == user_raw_input) for m in existing_msgs)
        if not has_user_msg:
            user_msg = ChatMessage(
                id=user_message_id or f"MSG-{uuid.uuid4().hex[:8].upper()}",
                conversation_id=conversation_id,
                role="user",
                content=user_raw_input or question,
                created_at=datetime.now().isoformat(),
            )
            save_message(user_msg)

        asst_msg = ChatMessage(
            id=assistant_msg_id,
            conversation_id=conversation_id,
            role="assistant",
            content=answer_text,
            trace_id=trace_id,
            created_at=datetime.now().isoformat(),
            metadata=metadata,
        )
        save_message(asst_msg)

        from aios_habit.evidence_trace import EvidenceTrace
        trace = EvidenceTrace(
            trace_id=trace_id,
            conversation_id=conversation_id,
            notebook_id=notebook_id,
            user_message_id=user_msg.id if "user_msg" in locals() else (user_message_id or ""),
            assistant_message_id=assistant_msg_id,
            query=question,
            answer_text=answer_text,
            provenance={
                "operational_mode": "5tier_ladder",
                "tier": tier,
                "intent": intent_res.intent,
                "cold_refusal_avoided": True,
                "confidence_label": "inferred_reasoning" if tier == TIER_4_INFERRED else "ambiguity_clarification",
            },
        )
        traces_file = (Path(base_cases_dir) / "workspace_chat" / "traces.jsonl") if base_cases_dir else None
        save_evidence_trace(trace, traces_file=traces_file)
    except Exception as ex:
        import logging
        logging.getLogger(__name__).warning("Failed to persist ladder message/trace: %s", ex)

    log_ladder_turn(
        conversation_id=conversation_id,
        message_id=assistant_msg_id,
        question=question,
        tier=tier,
        intent=intent_res.intent,
        has_warning_banner=has_banner,
        rephrase_offered=(tier == TIER_3_AMBIGUOUS),
        cold_refusal_avoided=True,
        base_cases_dir=base_cases_dir,
    )

    badge = {
        "type": "ai_answered",
        "ai_source": "AIOS 5-Tier Ladder" if not draft_used_title else "AIOS 5-Tier Ladder (Draft Parallel)",
        "model_tool_name": f"Ladder Tier {tier}",
        "operational_mode": "5tier_ladder",
        "source_count": 1 if draft_used_title else 0,
        "source_titles": [draft_used_title] if draft_used_title else [],
        "retrieval_summary": (
            f"⚠️ [Bản thảo - chưa kiểm chứng qua chuyên gia] từ {draft_used_title}"
            if draft_used_title
            else (
                "💡 Câu trả lời suy luận kỹ thuật kèm nhãn cảnh báo (Tier 4)"
                if tier == TIER_4_INFERRED
                else "❓ Làm rõ câu hỏi mơ hồ & gợi ý diễn đạt lại (Tier 3)"
            )
        ),
        "tier": tier,
        "tier_name": TIER_NAMES.get(tier, ""),
        "intent": intent_res.intent,
        "suggested_rephrasings": intent_res.suggested_rephrasings if tier == TIER_3_AMBIGUOUS else [],
        "has_warning_banner": has_banner,
        "action_items": TIER_5_DEFAULT_ACTIONS,
        "cold_refusal_avoided": True,
        "draft_source": draft_used_title,
        "has_draft_label": bool(draft_used_title),
    }

    return (True, "Đã phản hồi theo Nấc thang 5 bậc.", badge, None)
