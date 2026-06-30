from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


GENERAL_PLAYBOOK = "general"
MANUFACTURING_PLAYBOOK = "manufacturing_mom_wms"

MANUFACTURING_TERMS = {
    "manufacturing",
    "factory",
    "mom",
    "wms",
    "ams",
    "agv",
    "opcenter",
    "interstock",
    "matecon",
    "oricon",
    "supply line",
    "production line",
}


@dataclass(frozen=True)
class DomainPlaybook:
    playbook_id: str
    vocabulary: List[str] = field(default_factory=list)
    action_reminders: List[str] = field(default_factory=list)
    common_evidence_types: List[str] = field(default_factory=list)
    risk_reminders: List[str] = field(default_factory=list)


PLAYBOOKS: Dict[str, DomainPlaybook] = {
    GENERAL_PLAYBOOK: DomainPlaybook(
        playbook_id=GENERAL_PLAYBOOK,
        vocabulary=[],
        action_reminders=[
            "Verify the answer against cited evidence before taking action.",
            "List missing source types or documents instead of guessing.",
        ],
        common_evidence_types=["documents", "tables", "images", "logs", "notes"],
        risk_reminders=["Do not infer facts that are not supported by evidence."],
    ),
    MANUFACTURING_PLAYBOOK: DomainPlaybook(
        playbook_id=MANUFACTURING_PLAYBOOK,
        vocabulary=sorted(MANUFACTURING_TERMS),
        action_reminders=[
            "Check relevant system logs and interface records named by the evidence.",
            "Compare the current mapping/configuration with the cited table or document.",
            "Collect the relevant error image and responsible-person confirmation when the evidence calls for it.",
        ],
        common_evidence_types=["workflow documents", "interface tables", "logs", "screenshots", "master-data exports"],
        risk_reminders=[
            "Do not assume manufacturing flow behavior unless MOM/WMS/AGV evidence is present.",
            "Do not turn generic office questions into manufacturing workflow tasks.",
        ],
    ),
    "accounting": DomainPlaybook(playbook_id="accounting", common_evidence_types=["invoices", "ledgers", "contracts"]),
    "hr_policy": DomainPlaybook(playbook_id="hr_policy", common_evidence_types=["policy documents", "forms", "handbooks"]),
    "japanese_learning": DomainPlaybook(playbook_id="japanese_learning", common_evidence_types=["lesson notes", "vocabulary tables"]),
    "it_ops": DomainPlaybook(playbook_id="it_ops", common_evidence_types=["logs", "runbooks", "tickets"]),
    "legal_contract": DomainPlaybook(playbook_id="legal_contract", common_evidence_types=["contracts", "amendments", "email records"]),
    "general_office": DomainPlaybook(playbook_id="general_office", common_evidence_types=["PDFs", "slides", "spreadsheets", "notes"]),
}


def get_domain_playbook(playbook_id: str = GENERAL_PLAYBOOK) -> DomainPlaybook:
    return PLAYBOOKS.get(playbook_id or GENERAL_PLAYBOOK, PLAYBOOKS[GENERAL_PLAYBOOK])


def text_has_manufacturing_terms(text: str) -> bool:
    lowered = (text or "").lower()
    return any(term in lowered for term in MANUFACTURING_TERMS)


def select_domain_playbook(
    question: str = "",
    corpus_texts: Iterable[str] | None = None,
    requested_playbook: str = GENERAL_PLAYBOOK,
    allow_domain_assist: bool = False,
) -> str:
    requested = requested_playbook or GENERAL_PLAYBOOK
    if requested != GENERAL_PLAYBOOK:
        if requested == MANUFACTURING_PLAYBOOK and allow_domain_assist:
            return MANUFACTURING_PLAYBOOK
        return requested if requested in PLAYBOOKS and allow_domain_assist else GENERAL_PLAYBOOK

    if not allow_domain_assist:
        return GENERAL_PLAYBOOK

    if text_has_manufacturing_terms(question):
        return MANUFACTURING_PLAYBOOK

    for text in corpus_texts or []:
        if text_has_manufacturing_terms(text):
            return MANUFACTURING_PLAYBOOK

    return GENERAL_PLAYBOOK


def manufacturing_text_allowed(playbook_id: str) -> bool:
    return playbook_id == MANUFACTURING_PLAYBOOK
