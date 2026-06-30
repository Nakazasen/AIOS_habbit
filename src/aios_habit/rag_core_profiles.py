from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class GenericQueryProfile(str, Enum):
    FACTUAL_LOOKUP = "factual_lookup"
    COMPARE_CONTRAST = "compare_contrast"
    SUMMARIZE_DOCUMENT = "summarize_document"
    EXTRACT_FIELDS = "extract_fields"
    TABLE_QUESTION = "table_question"
    IMAGE_VISIBLE_FACTS = "image_visible_facts"
    IMAGE_LIMITATIONS = "image_limitations"
    SCHEMA_QUESTION = "schema_question"
    PROCEDURE_STEPS = "procedure_steps"
    TROUBLESHOOTING_GENERAL = "troubleshooting_general"
    MISSING_EVIDENCE_GENERAL = "missing_evidence_general"
    HANDOVER_GENERAL = "handover_general"
    TRANSLATION_OR_REWRITE = "translation_or_rewrite"
    DECISION_SUPPORT = "decision_support"
    OPEN_ENDED_RESEARCH = "open_ended_research"


@dataclass(frozen=True)
class GenericProfileSpec:
    profile_id: str
    expected_source_types: List[str]


PROFILE_SPECS: Dict[str, GenericProfileSpec] = {
    GenericQueryProfile.FACTUAL_LOOKUP.value: GenericProfileSpec("factual_lookup", ["pdf", "pptx", "doc", "docx", "html", "txt", "xlsx", "csv"]),
    GenericQueryProfile.COMPARE_CONTRAST.value: GenericProfileSpec("compare_contrast", ["pdf", "pptx", "doc", "docx", "xlsx", "csv", "html"]),
    GenericQueryProfile.SUMMARIZE_DOCUMENT.value: GenericProfileSpec("summarize_document", ["pdf", "pptx", "doc", "docx", "html", "txt"]),
    GenericQueryProfile.EXTRACT_FIELDS.value: GenericProfileSpec("extract_fields", ["xlsx", "xls", "csv", "html", "sql", "pdf"]),
    GenericQueryProfile.TABLE_QUESTION.value: GenericProfileSpec("table_question", ["xlsx", "xls", "csv", "html", "sql"]),
    GenericQueryProfile.IMAGE_VISIBLE_FACTS.value: GenericProfileSpec("image_visible_facts", ["screenshot", "image", "png", "jpg"]),
    GenericQueryProfile.IMAGE_LIMITATIONS.value: GenericProfileSpec("image_limitations", ["screenshot", "image", "png", "jpg"]),
    GenericQueryProfile.SCHEMA_QUESTION.value: GenericProfileSpec("schema_question", ["html", "sql", "csv", "xlsx"]),
    GenericQueryProfile.PROCEDURE_STEPS.value: GenericProfileSpec("procedure_steps", ["pdf", "pptx", "doc", "docx", "html", "txt"]),
    GenericQueryProfile.TROUBLESHOOTING_GENERAL.value: GenericProfileSpec("troubleshooting_general", ["log", "txt", "csv", "xlsx", "pdf", "html"]),
    GenericQueryProfile.MISSING_EVIDENCE_GENERAL.value: GenericProfileSpec("missing_evidence_general", ["log", "txt", "pdf", "xlsx", "csv", "html"]),
    GenericQueryProfile.HANDOVER_GENERAL.value: GenericProfileSpec("handover_general", ["txt", "md", "log", "pdf", "xlsx", "screenshot"]),
    GenericQueryProfile.TRANSLATION_OR_REWRITE.value: GenericProfileSpec("translation_or_rewrite", ["pdf", "doc", "docx", "txt", "md", "html"]),
    GenericQueryProfile.DECISION_SUPPORT.value: GenericProfileSpec("decision_support", ["pdf", "pptx", "doc", "docx", "xlsx", "csv", "html"]),
    GenericQueryProfile.OPEN_ENDED_RESEARCH.value: GenericProfileSpec("open_ended_research", ["pdf", "pptx", "doc", "docx", "html", "txt", "xlsx", "csv", "screenshot"]),
}


LEGACY_PROFILE_MAP = {
    "excel_mapping": GenericQueryProfile.EXTRACT_FIELDS.value,
    "process_boundary": GenericQueryProfile.PROCEDURE_STEPS.value,
    "design_change": GenericQueryProfile.DECISION_SUPPORT.value,
    "screenshot_visible_facts": GenericQueryProfile.IMAGE_VISIBLE_FACTS.value,
    "screenshot_unsupported_inference": GenericQueryProfile.IMAGE_LIMITATIONS.value,
    "schema_tables_fields": GenericQueryProfile.SCHEMA_QUESTION.value,
    "schema_unsupported_conclusions": GenericQueryProfile.MISSING_EVIDENCE_GENERAL.value,
    "mixed_troubleshooting": GenericQueryProfile.TROUBLESHOOTING_GENERAL.value,
    "owner_handover": GenericQueryProfile.HANDOVER_GENERAL.value,
    "missing_evidence": GenericQueryProfile.MISSING_EVIDENCE_GENERAL.value,
    "general": GenericQueryProfile.FACTUAL_LOOKUP.value,
}


def normalize_profile_id(profile_id: str) -> str:
    return LEGACY_PROFILE_MAP.get(profile_id, profile_id)


def expected_source_types_for(profile_id: str) -> List[str]:
    normalized = normalize_profile_id(profile_id)
    spec = PROFILE_SPECS.get(normalized, PROFILE_SPECS[GenericQueryProfile.FACTUAL_LOOKUP.value])
    return list(spec.expected_source_types)


def classify_generic_query_profile(question: str, target_source_type: str = "") -> str:
    q = (question or "").lower()
    target = (target_source_type or "").lower()

    if target in {"png", "jpg", "jpeg", "screenshot", "image"}:
        if any(term in q for term in ["show", "visible", "what does", "nhin thay", "nhìn thấy"]):
            return GenericQueryProfile.IMAGE_VISIBLE_FACTS.value
        return GenericQueryProfile.IMAGE_LIMITATIONS.value

    if any(term in q for term in ["screenshot", "image", "visible", "anh chup", "ảnh"]):
        if any(term in q for term in ["show", "visible", "what does", "nhin thay", "nhìn thấy"]):
            return GenericQueryProfile.IMAGE_VISIBLE_FACTS.value
        return GenericQueryProfile.IMAGE_LIMITATIONS.value

    if "missing evidence" in q or "insufficient evidence" in q or "thiếu bằng chứng" in q:
        return GenericQueryProfile.MISSING_EVIDENCE_GENERAL.value

    if any(term in q for term in ["handover", "next action", "next step", "owner action", "bàn giao"]):
        return GenericQueryProfile.HANDOVER_GENERAL.value

    if any(term in q for term in ["troubleshooting", "debug", "investigate", "root cause", "kiểm tra gì", "điều tra"]):
        return GenericQueryProfile.TROUBLESHOOTING_GENERAL.value

    if any(term in q for term in ["translate", "rewrite", "dịch", "viết lại", "summarize in"]):
        return GenericQueryProfile.TRANSLATION_OR_REWRITE.value

    if any(term in q for term in ["compare", "contrast", "difference", "khác nhau", "so sánh"]):
        return GenericQueryProfile.COMPARE_CONTRAST.value

    if any(term in q for term in ["summarize", "summary", "tóm tắt", "overview"]):
        return GenericQueryProfile.SUMMARIZE_DOCUMENT.value

    if any(term in q for term in ["schema", "database", "sql", "erd"]):
        return GenericQueryProfile.SCHEMA_QUESTION.value

    if any(term in q for term in ["table", "spreadsheet", "excel", "csv", "field", "column", "row", "key", "mapping", "invoice"]):
        if any(term in q for term in ["field", "column", "key", "extract", "invoice", "mapping"]):
            return GenericQueryProfile.EXTRACT_FIELDS.value
        return GenericQueryProfile.TABLE_QUESTION.value

    if any(term in q for term in ["procedure", "process", "step", "manual", "how to", "quy trình"]):
        return GenericQueryProfile.PROCEDURE_STEPS.value

    if any(term in q for term in ["decide", "decision", "should we", "risk", "recommend"]):
        return GenericQueryProfile.DECISION_SUPPORT.value

    if any(term in q for term in ["research", "explore", "find sources"]):
        return GenericQueryProfile.OPEN_ENDED_RESEARCH.value

    return GenericQueryProfile.FACTUAL_LOOKUP.value
