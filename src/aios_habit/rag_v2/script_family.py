"""Script-family helpers for retrieval. No domain vocabulary."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Optional, Sequence

_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af]")
_LATIN_RE = re.compile(r"[A-Za-zÀ-ỹ]")

# lexical, dense, sparse — all strictly positive for HybridRankingConfig
MISMATCH_CHANNEL_WEIGHTS = (0.25, 1.5, 1.25)


def script_family(text: str) -> str:
    sample = str(text or "")
    cjk = len(_CJK_RE.findall(sample))
    latin = len(_LATIN_RE.findall(sample))
    if cjk > latin:
        return "cjk"
    if latin > cjk:
        return "latin"
    return "mixed"


def majority_script(texts: Sequence[str]) -> Optional[str]:
    families = [script_family(item) for item in texts if str(item or "").strip()]
    if not families:
        return None
    family, count = Counter(families).most_common(1)[0]
    if family == "mixed" or count * 2 <= len(families):
        return None
    return family


def plan_has_cjk_variants(plan: object) -> bool:
    variants = getattr(plan, "variants", ()) or ()
    return any(script_family(getattr(item, "text", "")) == "cjk" for item in variants)


def corpus_needs_cjk_query_expansion(query: str, corpus_texts: Iterable[str]) -> bool:
    """Latin questions against a CJK-bearing corpus need extra search strings."""
    if script_family(query) != "latin":
        return False
    hits = sum(1 for item in corpus_texts if _CJK_RE.search(str(item or "")))
    return hits >= 8


def query_corpus_script_mismatch(query: str, corpus_texts: Iterable[str]) -> bool:
    query_family = script_family(query)
    majority = majority_script(tuple(corpus_texts))
    if not majority or query_family in {"mixed"}:
        return False
    return query_family != majority


def uses_script_mismatch_ranking(query: str, corpus_texts: Sequence[str]) -> bool:
    return query_corpus_script_mismatch(query, corpus_texts)


def should_retry_thin_results(
    *,
    unique_document_count: int,
    indexed_document_count: int,
    already_retried: bool,
) -> bool:
    return (
        not already_retried
        and unique_document_count <= 1
        and indexed_document_count >= 5
    )
