"""Deterministic, citation-validated local synthesis for RAG v2 evidence packs."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Tuple

from .evidence import EvidenceAnswerMode, EvidencePack


@dataclass(frozen=True)
class GroundedClaim:
    """One extractive claim that is traceable to validated evidence citations."""

    text: str
    citation_ids: Tuple[str, ...]
    evidence_ids: Tuple[str, ...]
    obligation_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalSynthesisResult:
    """Fail-closed local answer contract; no provider or network is involved."""

    answer: str
    claims: Tuple[GroundedClaim, ...]
    citation_ids: Tuple[str, ...]
    grounded: bool
    abstained: bool
    abstention_reasons: Tuple[str, ...]
    provider_used: bool = False
    answer_mode: str = EvidenceAnswerMode.ANSWER.value
    limitation_reasons: Tuple[str, ...] = ()
    mode: str = "local_extractive"


@dataclass(frozen=True)
class SynthesisPlan:
    """Privacy-safe obligations for bounded grounded answer generation."""

    answer_shape: str
    max_claims: int
    allowed_citation_ids: Tuple[str, ...]
    required_facet_ids: Tuple[str, ...]
    missing_facet_ids: Tuple[str, ...]
    required_obligation_ids: Tuple[str, ...]
    missing_obligation_ids: Tuple[str, ...]
    limitation_reasons: Tuple[str, ...]


@dataclass(frozen=True)
class ProviderSynthesisValidation:
    """Deterministic validation outcome for a provider-generated answer."""

    valid: bool
    citation_ids: Tuple[str, ...]
    material_claim_count: int
    covered_facet_ids: Tuple[str, ...]
    errors: Tuple[str, ...]


def validate_grounded_claims(
    pack: EvidencePack,
    claims: Iterable[GroundedClaim],
) -> Tuple[str, ...]:
    """Return stable validation errors for claims that cannot be cited to the pack."""
    available = {item.citation_id: item.evidence_id for item in pack.items}
    errors = []
    for index, claim in enumerate(claims, 1):
        if not claim.text.strip():
            errors.append(f"claim_{index}_empty")
        if not claim.citation_ids:
            errors.append(f"claim_{index}_missing_citation")
            continue
        unknown = [citation for citation in claim.citation_ids if citation not in available]
        if unknown:
            errors.append(f"claim_{index}_unknown_citation")
        expected_ids = tuple(
            available[citation]
            for citation in claim.citation_ids
            if citation in available
        )
        if tuple(claim.evidence_ids) != expected_ids:
            errors.append(f"claim_{index}_evidence_mismatch")
    return tuple(dict.fromkeys(errors))


_CITATION_RE = re.compile(r"\[(\d+)\]")
_HEADING_RE = re.compile(r"^#{1,6}\s|^[^.!?]{1,80}:$")
_CRITICAL_LITERAL_RE = re.compile(
    r"(?<![\w])(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d+(?:[.,]\d+)%|\d+[.,]\d+|\d{2,}|[A-Z]{2,}[A-Z0-9_-]*\d[A-Z0-9_-]*)(?![\w])"
)
_ANSWER_SHAPE_MARKERS = {
    "procedure": ("PRECHECKS:", "STEPS:", "POSTCHECKS:"),
    "actionable_output": ("PRECHECKS:", "STEPS:", "POSTCHECKS:"),
    "compare_change": ("SIDE_A:", "SIDE_B:", "DIFFERENCES:"),
    "diagnosis": ("SYMPTOMS:", "CHECKS:", "ACTIONS:"),
}


def _critical_literals(text: str) -> Tuple[str, ...]:
    without_citations = _CITATION_RE.sub("", text)
    return tuple(dict.fromkeys(match.group(0).casefold() for match in _CRITICAL_LITERAL_RE.finditer(without_citations)))


def _required_shape_markers(answer_shape: str) -> Tuple[str, ...]:
    return _ANSWER_SHAPE_MARKERS.get(answer_shape, ())


def build_synthesis_plan(
    pack: EvidencePack,
    *,
    answer_shape: str = "grounded_summary",
    max_claims: int = 8,
) -> SynthesisPlan:
    """Build bounded citation and facet obligations without copying source text."""
    if max_claims < 1:
        raise ValueError("max_claims must be at least 1")
    normalized_shape = answer_shape.strip().lower() or "grounded_summary"
    structural = tuple(item for item in pack.coverage_map if item.facet_id != "query")
    required = tuple(item.facet_id for item in structural if item.status == "covered")
    missing = tuple(item.facet_id for item in structural if item.status != "covered")
    required_obligations = tuple(
        item.obligation_id
        for item in pack.obligation_coverage_map
        if item.status == "covered"
    )
    missing_obligations = tuple(
        item.obligation_id
        for item in pack.obligation_coverage_map
        if item.status != "covered"
    )
    limitation_reasons = tuple(dict.fromkeys(
        (*pack.soft_warning_reasons, *missing, *missing_obligations)
    ))
    return SynthesisPlan(
        answer_shape=normalized_shape,
        max_claims=max_claims,
        allowed_citation_ids=tuple(item.citation_id for item in pack.items),
        required_facet_ids=required,
        missing_facet_ids=missing,
        required_obligation_ids=required_obligations,
        missing_obligation_ids=missing_obligations,
        limitation_reasons=limitation_reasons,
    )


def format_provider_synthesis_contract(plan: SynthesisPlan) -> str:
    """Render privacy-safe provider instructions containing IDs and counts only."""
    allowed = ", ".join(plan.allowed_citation_ids) or "none"
    required = ", ".join(plan.required_facet_ids) or "none"
    missing = ", ".join(plan.missing_facet_ids) or "none"
    required_obligations = ", ".join(plan.required_obligation_ids) or "none"
    missing_obligations = ", ".join(plan.missing_obligation_ids) or "none"
    limitations = ", ".join(plan.limitation_reasons) or "none"
    limitation_rule = (
        f"End with exactly `LIMITATIONS: {limitations}`; this marker is not a factual claim."
        if plan.limitation_reasons
        else "Do not emit a LIMITATIONS marker."
    )
    shape_markers = _required_shape_markers(plan.answer_shape)
    shape_rule = (
        f"Use these exact section markers once each: {', '.join(shape_markers)}."
        if shape_markers
        else "No fixed section markers are required."
    )
    return (
        "RAG_V2_GROUNDED_ANSWER_CONTRACT\n"
        f"Answer shape: {plan.answer_shape}. Maximum material claims: {plan.max_claims}.\n"
        f"Allowed evidence labels: {allowed}.\n"
        f"Covered facets that require cited representation: {required}.\n"
        f"Missing facets that must be stated as limitations, not invented: {missing}.\n"
        f"Covered obligations that require cited representation: {required_obligations}.\n"
        f"Missing obligations that must be stated as limitations, not invented: {missing_obligations}.\n"
        "Treat each NGUỒN n block as the preassigned evidence label [n]; do not create labels. "
        "Every factual bullet or paragraph must end with one or more allowed evidence labels. "
        "Dates, percentages, quantities, and identifiers must appear in the evidence blocks cited "
        "by that same factual line. "
        f"Do not emit unknown labels. {shape_rule} {limitation_rule}"
    )


def validate_provider_synthesis_answer(
    pack: EvidencePack,
    answer: str,
    plan: SynthesisPlan,
) -> ProviderSynthesisValidation:
    """Validate bounded citation/facet obligations without semantic guesswork."""
    normalized = answer.strip()
    errors = []
    if not normalized:
        errors.append("provider_answer_empty")

    citation_ids = tuple(
        dict.fromkeys(f"[{value}]" for value in _CITATION_RE.findall(normalized))
    )
    allowed = set(plan.allowed_citation_ids)
    if normalized and not citation_ids:
        errors.append("provider_answer_missing_citations")
    if any(citation not in allowed for citation in citation_ids):
        errors.append("provider_answer_unknown_citation")

    stripped_lines = tuple(line.strip() for line in normalized.splitlines() if line.strip())
    limitation_lines = tuple(
        line for line in stripped_lines if line.startswith("LIMITATIONS:")
    )
    if plan.limitation_reasons:
        expected_marker = f"LIMITATIONS: {', '.join(plan.limitation_reasons)}"
        if limitation_lines != (expected_marker,):
            errors.append("provider_answer_missing_required_limitations")
    elif limitation_lines:
        errors.append("provider_answer_unexpected_limitations")

    material_lines = tuple(
        line
        for line in stripped_lines
        if not line.startswith("LIMITATIONS:") and not _HEADING_RE.match(line)
    )
    if len(material_lines) > plan.max_claims:
        errors.append("provider_answer_claim_budget_exceeded")
    if any(not _CITATION_RE.search(line) for line in material_lines):
        errors.append("provider_answer_uncited_material_claim")

    required_markers = _required_shape_markers(plan.answer_shape)
    if any(stripped_lines.count(marker) != 1 for marker in required_markers):
        errors.append("provider_answer_shape_contract_failed")

    evidence_by_citation = {
        item.citation_id: item.text.casefold()
        for item in pack.items
    }
    for line in material_lines:
        line_citations = tuple(
            dict.fromkeys(f"[{value}]" for value in _CITATION_RE.findall(line))
        )
        cited_text = "\n".join(
            evidence_by_citation[citation]
            for citation in line_citations
            if citation in evidence_by_citation
        )
        if any(literal not in cited_text for literal in _critical_literals(line)):
            errors.append("provider_answer_unsupported_critical_literal")
            break

    citations_by_facet = {
        item.facet_id: set(item.citation_ids)
        for item in pack.coverage_map
        if item.status == "covered"
    }
    used = set(citation_ids) & allowed
    covered_facets = tuple(
        facet_id
        for facet_id in plan.required_facet_ids
        if used & citations_by_facet.get(facet_id, set())
    )
    if len(covered_facets) != len(plan.required_facet_ids):
        errors.append("provider_answer_missing_required_facet_citation")

    citations_by_obligation = {
        item.obligation_id: set(item.citation_ids)
        for item in pack.obligation_coverage_map
        if item.status == "covered"
    }
    covered_obligations = tuple(
        obligation_id
        for obligation_id in plan.required_obligation_ids
        if used & citations_by_obligation.get(obligation_id, set())
    )
    if len(covered_obligations) != len(plan.required_obligation_ids):
        errors.append("provider_answer_missing_required_obligation_citation")

    return ProviderSynthesisValidation(
        valid=not errors,
        citation_ids=citation_ids,
        material_claim_count=len(material_lines),
        covered_facet_ids=covered_facets,
        errors=tuple(dict.fromkeys(errors)),
    )


def synthesize_evidence(
    pack: EvidencePack,
    *,
    answer_shape: str = "grounded_summary",
    max_claims: int = 5,
) -> LocalSynthesisResult:
    """Build a bounded extractive answer or explicitly abstain when evidence is weak."""
    if max_claims < 1:
        raise ValueError("max_claims must be at least 1")

    if pack.answer_mode == EvidenceAnswerMode.ABSTAIN:
        fatal_reasons = list(pack.hard_insufficiency_reasons)
        if not fatal_reasons:
            fatal_reasons.append("evidence_pack_insufficient")
        elif "evidence_pack_insufficient" not in fatal_reasons:
            fatal_reasons.insert(0, "evidence_pack_insufficient")
        if not pack.items:
            fatal_reasons.append("no_citable_evidence")
        return LocalSynthesisResult(
            answer="Không tìm thấy bằng chứng đủ liên quan trong corpus.",
            claims=(),
            citation_ids=(),
            grounded=False,
            abstained=True,
            abstention_reasons=tuple(dict.fromkeys(fatal_reasons)),
            answer_mode=EvidenceAnswerMode.ABSTAIN.value,
        )

    claims = tuple(
        GroundedClaim(
            text=item.snippet.strip(),
            citation_ids=(item.citation_id,),
            evidence_ids=(item.evidence_id,),
            obligation_ids=item.matched_obligations,
        )
        for item in pack.items[:max_claims]
        if item.snippet.strip()
    )
    validation_errors = validate_grounded_claims(pack, claims)
    if not claims or validation_errors:
        return _abstention(pack, (*pack.insufficiency_reasons, *validation_errors, "no_valid_grounded_claims"))

    normalized_shape = (answer_shape or "").strip().lower()
    sections = _sections_for_shape(normalized_shape)
    if sections and not any(
        obligation_id in claim.obligation_ids
        for obligation_id in sections.values()
        for claim in claims
    ):
        return _abstention(pack, (*pack.insufficiency_reasons, "no_supported_answer_section"))
    if normalized_shape == "diagnosis":
        answer = _format_structured_claims(claims, sections)
    elif normalized_shape in ("procedure", "actionable_output"):
        answer = _format_structured_claims(claims, sections)
    elif normalized_shape == "compare_change":
        answer = _format_structured_claims(claims, sections)
    else:
        answer = "\n".join(
            f"- {claim.text} {' '.join(claim.citation_ids)}"
            for claim in claims
        )
    citation_ids = tuple(
        dict.fromkeys(citation for claim in claims for citation in claim.citation_ids)
    )
    return LocalSynthesisResult(
        answer=answer,
        claims=claims,
        citation_ids=citation_ids,
        grounded=True,
        abstained=False,
        abstention_reasons=(),
        answer_mode=pack.answer_mode.value,
        limitation_reasons=tuple(dict.fromkeys(
            (*pack.soft_warning_reasons, *pack.retrieval_summary.missing_obligation_ids)
        )),
    )


def _sections_for_shape(answer_shape: str) -> dict[str, str]:
    """Return the fixed evidence obligations for a structured answer shape."""
    if answer_shape == "diagnosis":
        return {
            "SYMPTOMS:": "problem",
            "CHECKS:": "check",
            "ACTIONS:": "action",
        }
    if answer_shape in ("procedure", "actionable_output"):
        return {
            "PRECHECKS:": "precheck",
            "STEPS:": "step",
            "POSTCHECKS:": "postcheck",
        }
    if answer_shape == "compare_change":
        return {
            "SIDE_A:": "side_a",
            "SIDE_B:": "side_b",
            "DIFFERENCES:": "differences",
        }
    return {}


def _format_structured_claims(
    claims: Tuple[GroundedClaim, ...],
    sections: dict[str, str],
) -> str:
    """Render claims only in sections explicitly supported by their evidence."""
    rendered = []
    for marker, obligation_id in sections.items():
        supported = [
            claim for claim in claims if obligation_id in claim.obligation_ids
        ]
        rendered.append(marker)
        if supported:
            rendered.extend(
                f"- {claim.text} {' '.join(claim.citation_ids)}"
                for claim in supported
            )
        else:
            rendered.append("- No grounded evidence retrieved for this section.")
    return "\n".join(rendered)


def _abstention(pack: EvidencePack, reasons: Iterable[str]) -> LocalSynthesisResult:
    normalized = tuple(dict.fromkeys(reason for reason in reasons if reason))
    return LocalSynthesisResult(
        answer="Không tìm thấy bằng chứng đủ liên quan trong corpus.",
        claims=(),
        citation_ids=(),
        grounded=False,
        abstained=True,
        abstention_reasons=normalized or ("insufficient_evidence",),
        answer_mode=EvidenceAnswerMode.ABSTAIN.value,
        limitation_reasons=pack.soft_warning_reasons,
    )
