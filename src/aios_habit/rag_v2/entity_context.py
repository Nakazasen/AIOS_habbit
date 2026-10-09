"""Conditional entity-based context expansion for synthesis (ticket SYNTH-CONTEXT-ENTITY-HOME).

Provides:
- Concrete entity extraction from technical queries (error codes, machine models, units, CJK markers).
- Item-level entity matching for candidate context chunks (ranks 9-12).
- Environment flag and configuration handling.
- Reusable selection helper for bridge and evidence pack builders.
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional, Sequence

DEFAULT_SYNTH_CONTEXT_TOPK = 8
DEFAULT_SYNTH_CONTEXT_EXPAND_MAX = 12
SYNTH_CONTEXT_TOPK_ENV = "AIOS_RAG_SYNTH_CONTEXT_TOPK"
SYNTH_CONTEXT_ENTITY_EXPAND_ENV = "AIOS_RAG_SYNTH_CONTEXT_ENTITY_EXPAND"


def is_synth_context_entity_expand_enabled() -> bool:
    """Return whether conditional entity-based context expansion is active."""
    raw = os.environ.get(SYNTH_CONTEXT_ENTITY_EXPAND_ENV, "1").strip().lower()
    return raw not in {"0", "false", "no", "off", "disable", "disabled"}


# Negative lookaround regexes to avoid boundary traps with CJK characters
_ENTITY_CODE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]+\d+[A-Za-z0-9_\-\.]*|\d+[A-Za-z]+[A-Za-z0-9_\-\.]*)(?![A-Za-z0-9])"
)
_ENTITY_ACRONYM_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{2,}(?:[-_][A-Z0-9]+)*(?![A-Za-z0-9])")
_ENTITY_TECH_NAME_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z][a-z0-9]{2,}(?:[A-Z][a-z0-9]+)*(?![A-Za-z0-9])")
_ENTITY_UNIT_NUM_RE = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[\.,]\d+)?\s*(?:dot|mm|µm|um|s|giây|độ|°C|c|n|%|vòng/phút|rpm|lot)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_ENTITY_DATE_RE = re.compile(
    r"(?:\b\d{1,2}[/月]\d{1,2}(?:日)?\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b)"
)
_ENTITY_RANGE_RE = re.compile(r"(?<![A-Za-z0-9])\d+[-–—~]\d+(?![A-Za-z0-9])")
_ENTITY_DECIMAL_NUM_RE = re.compile(r"(?<![A-Za-z0-9_\-\.])\d+\.\d+(?![A-Za-z0-9_\-\.])")
_ENTITY_STANDALONE_INT_RE = re.compile(r"(?<![A-Za-z0-9_\-\.])\d{3,}(?![A-Za-z0-9_\-\.])")
_ENTITY_DOC_EXT_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z0-9_\-]+\.(?:pptx|xlsx|csv|pdf|docx|txt)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_ENTITY_SPECIAL_CJK_MARKER_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z])(?=距離|色|軸|方向|相)")

_ENTITY_STOPWORDS = frozenset({
    "FILE", "LINE", "DATA", "WHAT", "WHEN", "WHERE", "HOW", "NOTE", "USER",
    "CUA", "TRONG", "THE", "AND", "FOR", "WITH", "THIS", "FROM", "UNIT",
    "SAU", "KHI", "HAY", "HAI", "BA", "CAC", "CO", "DUNG", "SAI", "THAM", "QUAN",
    "GHI", "TRA", "BAO", "VI", "DUY", "NHAU", "CHUNG", "QUAY",
    "NG", "OK",
})

_TECHNICAL_LOWERCASE_TERMS = frozenset({
    "beam", "skew", "diameter", "offset", "pitch", "jitter", "sensor", "lens",
    "shutter", "motor", "bracket", "housing", "polygon", "mirror", "tape",
    "calib", "calibration", "power", "current", "voltage",
})


def extract_concrete_query_entities(question: str) -> tuple[str, ...]:
    """Extract concrete technical entities, machine/error codes, and units from query.

    Returns tuple of distinct entity strings sorted by length descending.
    """
    if not question:
        return ()
    found: set[str] = set()
    text = str(question)

    for m in _ENTITY_CODE_RE.finditer(text):
        token = m.group(0).strip(".-_")
        if len(token) >= 2 and token.upper() not in _ENTITY_STOPWORDS:
            found.add(token)

    for m in _ENTITY_ACRONYM_RE.finditer(text):
        token = m.group(0).strip(".-_")
        if len(token) >= 2 and token.upper() not in _ENTITY_STOPWORDS:
            found.add(token)

    for m in _ENTITY_TECH_NAME_RE.finditer(text):
        token = m.group(0).strip(".-_")
        if len(token) >= 3 and token.upper() not in _ENTITY_STOPWORDS:
            found.add(token)

    for pat in (
        _ENTITY_UNIT_NUM_RE,
        _ENTITY_DATE_RE,
        _ENTITY_RANGE_RE,
        _ENTITY_DECIMAL_NUM_RE,
        _ENTITY_STANDALONE_INT_RE,
        _ENTITY_DOC_EXT_RE,
    ):
        for m in pat.finditer(text):
            token = m.group(0).strip()
            if token.upper() not in _ENTITY_STOPWORDS:
                found.add(token)

    for m in _ENTITY_SPECIAL_CJK_MARKER_RE.finditer(text):
        token = m.group(1).strip()
        if token:
            found.add(token)

    folded_lower = text.casefold()
    for term in _TECHNICAL_LOWERCASE_TERMS:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", folded_lower):
            found.add(term)

    return tuple(sorted(found, key=lambda s: (len(s), s), reverse=True))


def item_matches_any_entity(item: Any, entities: Sequence[str]) -> tuple[bool, str]:
    """Check if evidence item text or title contains any of the target entities."""
    if not entities:
        return False, ""
    if isinstance(item, dict):
        text = str(item.get("text") or item.get("snippet") or "")
        title = str(item.get("title") or "")
    else:
        text = str(
            getattr(item, "text", "")
            or getattr(item, "extracted_text", "")
            or getattr(item, "snippet", "")
            or ""
        )
        title = str(
            getattr(item, "title", "")
            or getattr(item, "source_title", "")
            or getattr(item, "source_name", "")
            or ""
        )
    haystack = f"{title} {text}"
    for ent in entities:
        pat = r"(?<![A-Za-z0-9])" + re.escape(ent) + r"(?![A-Za-z0-9])"
        if re.search(pat, haystack, re.IGNORECASE):
            return True, ent
    return False, ""


def select_entity_conditional_context(
    question: str,
    evidence_items: Sequence[Any],
    base_topk: int = DEFAULT_SYNTH_CONTEXT_TOPK,
    max_expand_topk: int = DEFAULT_SYNTH_CONTEXT_EXPAND_MAX,
    enabled: Optional[bool] = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Select context chunks with entity-conditional expansion for ranks 9-12 (ticket SYNTH-CONTEXT-ENTITY-HOME).

    Rules:
    - Base chunks (1..base_topk, default 8) are always included in their original order.
    - If enabled, candidate chunks from base_topk to max_expand_topk (default 9..12) are inspected.
    - A candidate chunk is included ONLY if it contains at least one concrete entity from the question.
    - General questions with no entities keep strictly the base chunks.
    - Preserves ordering and citation numbering of all chunks.
    - Returns selected chunks list + telemetry dict.
    """
    is_enabled = is_synth_context_entity_expand_enabled() if enabled is None else bool(enabled)
    items_list = list(evidence_items) if evidence_items else []
    base_count = min(len(items_list), max(1, base_topk))
    base_items = items_list[:base_count]

    telemetry: dict[str, Any] = {
        "expanded": False,
        "enabled": is_enabled,
        "base_count": len(base_items),
        "total_selected": len(base_items),
        "expanded_indices": [],
        "matched_entities": [],
        "entities_found": [],
    }

    if not is_enabled or len(items_list) <= base_count:
        return base_items, telemetry

    entities = extract_concrete_query_entities(question)
    telemetry["entities_found"] = list(entities)

    if not entities:
        return base_items, telemetry

    candidate_items = items_list[base_count:max_expand_topk]
    selected = list(base_items)

    for offset, cand in enumerate(candidate_items):
        idx = base_count + offset
        matched, matched_ent = item_matches_any_entity(cand, entities)
        if matched:
            selected.append(cand)
            telemetry["expanded_indices"].append(idx)
            telemetry["matched_entities"].append(matched_ent)

    telemetry["expanded"] = len(telemetry["expanded_indices"]) > 0
    telemetry["total_selected"] = len(selected)
    return selected, telemetry
