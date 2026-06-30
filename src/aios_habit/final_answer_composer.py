from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from aios_habit.domain_playbooks import GENERAL_PLAYBOOK, get_domain_playbook, select_domain_playbook
from aios_habit.rag_core_profiles import normalize_profile_id
from aios_habit.rag_evidence import RAGEvidenceItem, RAGEvidencePack
from aios_habit.source_router import classify_query_profile, route_evidence_by_profile


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


def compose_final_owner_answer(
    pack: RAGEvidencePack,
    target_source_type: str = "",
    case_context: str = "",
    max_items: int = 6,
    domain_playbook: str = GENERAL_PLAYBOOK,
    allow_domain_assist: bool = False,
) -> FinalOwnerAnswer:
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

    warnings: List[str] = routed.route_warnings.copy()
    if pack.privacy_mode == "local_only":
        warnings.append("Privacy: local_only evidence stays local; no cloud/provider call was made.")
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

    sections = [
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
    ]

    return FinalOwnerAnswer(
        draft_id=_stable_final_id(pack),
        pack_id=pack.pack_id,
        query=pack.query,
        answer_text="\n".join(sections),
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
        },
    )


def final_owner_answer_to_dict(answer: FinalOwnerAnswer) -> Dict[str, Any]:
    return asdict(answer)
