"""Question-only multilingual search expansion. Never sends document text."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Optional, Sequence

from aios_habit.rag_v2.script_family import script_family

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_ANCHOR_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_\-]{1,}\b")
_ANCHOR_STOP = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "how", "in", "into", "is", "it", "of", "on", "or", "should", "than",
    "that", "the", "them", "then", "this", "to", "what", "when", "where", "which",
    "who", "why", "with", "using", "must", "also", "just", "only", "other",
})
_TITLE_SKIP = frozenset({
    "summarize", "create", "compare", "identify", "describe", "explain", "list",
    "provide", "available", "documented", "highlight", "including", "connected",
    "overall", "actionable",
})


def _keep_latin_anchor(token: str) -> bool:
    key = token.casefold()
    if key in _ANCHOR_STOP or key in _TITLE_SKIP or len(token) < 2:
        return False
    if any(character.isdigit() for character in token):
        return True
    if token.isupper():
        return True
    if sum(1 for character in token if character.isupper()) >= 2:
        return True
    return token[0].isupper() and len(token) >= 4
_MAX_VARIANTS = 3
_MAX_VARIANT_CHARS = 180

EXPAND_SYSTEM_PROMPT = (
    "You write short search queries for a local factory document index.\n"
    "The user question may be in a different script than the documents.\n"
    "Return JSON only, no markdown: "
    '{"variants":[{"text":"...","language_hint":"ja"}]}\n'
    "Rules:\n"
    "- 2 or 3 short queries a technician would type in the document script.\n"
    "- Keep Latin acronyms and CamelCase tokens from the question unchanged.\n"
    "- Do not invent product names, file names, or table names.\n"
    "- Do not repeat the original question unchanged.\n"
    "- Do not include document contents; you only rewrite the question."
)


def latin_query_anchors(original_query: str) -> tuple[str, ...]:
    """Keep user-typed Latin codes; skip closed-class English words."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _ANCHOR_RE.finditer(original_query or ""):
        token = match.group(0)
        key = token.casefold()
        if not _keep_latin_anchor(token) or key in seen:
            continue
        seen.add(key)
        found.append(token)
    return tuple(found)


def mix_original_anchors(original_query: str, variant_text: str) -> str:
    mixed = variant_text
    for token in latin_query_anchors(original_query):
        if token.casefold() in mixed.casefold():
            continue
        candidate = f"{mixed} {token}".strip()
        if len(candidate) <= _MAX_VARIANT_CHARS:
            mixed = candidate
    return mixed


def parse_expansion_payload(
    raw: str,
    *,
    original_query: str,
    require_script: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Parse model JSON into the build_query_plan expansion mapping."""
    text = str(raw or "").strip()
    if not text:
        return None
    match = _JSON_OBJECT_RE.search(text)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    raw_variants = payload.get("variants") if isinstance(payload, Mapping) else None
    if not isinstance(raw_variants, Sequence) or isinstance(raw_variants, (str, bytes)):
        return None
    original_key = original_query.casefold().strip()
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_variants:
        if not isinstance(item, Mapping):
            continue
        variant_text = " ".join(str(item.get("text") or "").split())
        if (
            not variant_text
            or len(variant_text) > _MAX_VARIANT_CHARS
            or variant_text.casefold() == original_key
            or variant_text.casefold() in seen
        ):
            continue
        if require_script and script_family(variant_text) != require_script:
            continue
        variant_text = mix_original_anchors(original_query, variant_text)
        if variant_text.casefold() in seen:
            continue
        seen.add(variant_text.casefold())
        hint = str(item.get("language_hint") or require_script or "unknown")[:24]
        cleaned.append(
            {
                "text": variant_text,
                "language_hint": hint,
                "origin": "expansion",
            }
        )
        if len(cleaned) >= _MAX_VARIANTS:
            break
    if not cleaned:
        return None
    return {"variants": cleaned}


def expand_question_for_corpus_script(
    question: str,
    *,
    corpus_script: str,
    gemini_ready: bool,
) -> Optional[dict[str, Any]]:
    """Expand using Gemini Web. Sends the question only — no source text."""
    if not gemini_ready or corpus_script not in {"cjk"}:
        return None
    from aios_habit.antigravity_bridge import call_antigravity_bridge

    response = call_antigravity_bridge(
        question=(
            f"Document script family: {corpus_script}\n"
            f"User question: {question}"
        ),
        system_prompt=EXPAND_SYSTEM_PROMPT,
        context_text="",
        privacy_mode="cloud_allowed",
        answer_language="ja",
        timeout_seconds=60,
    )
    if not response.ok:
        return None
    return parse_expansion_payload(
        response.answer_text,
        original_query=question,
        require_script="cjk",
    )
