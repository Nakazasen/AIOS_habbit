"""Generic, provider-independent query planning for local retrieval.

The planner deliberately carries only the user query and validated retrieval variants.
It never receives documents, source metadata, or evidence text.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping, Protocol, Sequence, Tuple

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]+")
_JAPANESE_RE = re.compile(r"[\u3040-\u30ff]")
_VIETNAMESE_DIACRITIC_RE = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.IGNORECASE)
_DANGEROUS_QUERY_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_UNSAFE_EXPANSION_RE = re.compile(
    r"(?:^|[;\s])(?:select|insert|update|delete|drop|alter|create|pragma|attach|detach)\b",
    re.IGNORECASE,
)
_FACET_SPLIT_RE = re.compile(r"(?:\r?\n|[;；]|\s+[•·]\s+)")
_COMMA_CLAUSE_SPLIT_RE = re.compile(r"\s*,\s*(?:and|và|đồng thời)\s+", re.IGNORECASE)
_BARE_CLAUSE_SPLIT_RE = re.compile(r"\s+(?:and|và|đồng thời)\s+", re.IGNORECASE)
_QUESTION_CUE_RE = re.compile(
    r"\b(?:how|what|where|when|why|which|who|verify|check|"
    r"dau|cho nao|lam sao|nhu the nao|lam the nao|kiem|xac minh)\b"
)
_RIGHT_QUESTION_START_RE = re.compile(
    r"^(?:where|how|what|when|why|which|who|verify|check|"
    r"cho nao|o dau|dau\b|lam sao|nhu the nao|lam the nao|kiem tra|kiem\b|xac minh)\b"
)
_CROSS_SOURCE_WORDING_RE = re.compile(
    r"\b(?:tong hop|nhieu nguon|tat ca cac tai lieu|toan bo tai lieu|"
    r"xuyen suot|synthesize|synthesis|cross-source|cross source|"
    r"all sources|all documents|comprehensive|architecture|"
    r"kien truc|cau truc tong)\b"
)
_OVERVIEW_WORDING_RE = re.compile(
    r"\b(?:tom tat|tong quan|gioi thieu|overview|summar(?:y|ize)|"
    r"what is this|about this (?:corpus|document|collection|set)|"
    r"cac tai lieu|toan bo (?:tai lieu|van ban)|introduce|"
    r"open[- ]ended|general (?:overview|summary)|khao sat chung|"
    r"nhin chung|noi dung chinh|main (?:topics|themes)|"
    r"corpus about|documents (?:about|cover)|tai lieu nay)\b"
)
_CONCRETE_ENTITY_RE = re.compile(
    r"(?:"
    r"\b[A-Za-z]{1,8}[-_][A-Za-z0-9]{2,}\b|"
    r"\b[A-Za-z]*\d{2,}[A-Za-z0-9]*\b|"
    r"\b(?:sheet|cell|row|column|page|trang|sku|sop|error|fault|code)\s*[:#-]?\s*\d+\b|"
    r"\bversion\s+\d+\b"
    r")",
    re.IGNORECASE,
)
_SUMMARY_FIRST_TRUE = frozenset({"1", "true", "yes", "on"})
_SUMMARY_FIRST_FALSE = frozenset({"0", "false", "no", "off"})
_DEFAULT_OVERVIEW_MAX_VARIANTS = 3
_DEFAULT_FOCUSED_MAX_VARIANTS = 3
_DEFAULT_FULL_MAX_VARIANTS = 8
_COMMON_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "what", "when", "where", "which", "who", "with",
})
_MAX_FACETS = 4
_MAX_VARIANTS = 8
_MAX_VARIANT_CHARS = 240
_MAX_TOTAL_VARIANT_CHARS = 900

@dataclass(frozen=True)
class RetrievalQueryVariant:
    """One bounded retrieval formulation with no source-derived content.

    ``target_equivalent`` is only set for a validated, query-only expansion that
    explicitly represents the subject of the original question.  Structural
    aliases remain recall-only and can never prove target relevance.
    """

    text: str
    language_hint: str = "unknown"
    origin: str = "original"
    variant_id: str = "query_original"
    facet_id: str = "query"
    target_equivalent: bool = False


@dataclass(frozen=True)
class RetrievalQueryPlan:
    """Validated original query plus deterministic, inspectable retrieval variants."""

    original_query: str
    variants: Tuple[RetrievalQueryVariant, ...]
    content_terms: Tuple[str, ...]
    expansion_status: str = "identity"
    intent_category: str = "general"
    required_obligations: Tuple[str, ...] = ("query",)
    target_terms: Tuple[str, ...] = ()
    query_language: str = "unknown"
    # Runtime routing hint. Omitted from fingerprint so enabling summary-first
    # does not rewrite stored plan identity for the default full path.
    retrieval_mode: str = "full"

    @property
    def facet_ids(self) -> Tuple[str, ...]:
        """Return stable conceptual facets without exposing query text."""
        return tuple(dict.fromkeys(item.facet_id for item in self.variants if item.facet_id))

    @property
    def target_retrieval_limit(self) -> int:
        """Return dynamic retrieval limit based on intent category."""
        return 25 if self.intent_category == "cross_source_synthesis" else 15

    @property
    def target_per_document_limit(self) -> int:
        """Return dynamic per-document limit based on intent category."""
        return 5

    @property
    def fingerprint(self) -> str:
        payload = {
            "original_query": self.original_query,
            "variants": [
                {
                    "text": item.text,
                    "language_hint": item.language_hint,
                    "origin": item.origin,
                    "variant_id": item.variant_id,
                    "facet_id": item.facet_id,
                    "target_equivalent": item.target_equivalent,
                }
                for item in self.variants
            ],
            "content_terms": self.content_terms,
            "target_terms": self.target_terms,
            "query_language": self.query_language,
            "expansion_status": self.expansion_status,
            "intent_category": self.intent_category,
            "required_obligations": list(self.required_obligations),
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()






class QueryExpander(Protocol):
    """Optional query-only expander; implementations must not receive source content."""

    def expand(self, question: str) -> Mapping[str, Any]:
        ...


def extract_content_terms(value: str) -> Tuple[str, ...]:
    """Return ordered, unique query terms after generic function-word removal."""
    seen: set[str] = set()
    result = []
    for match in _TOKEN_RE.finditer(value or ""):
        token = match.group(0).lower()
        if token in _COMMON_STOPWORDS or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return tuple(result)


def extract_target_terms(value: str) -> Tuple[str, ...]:
    """Return literal terms from the user query without semantic rewriting."""
    return extract_content_terms(value)


def _ascii_fold(value: str) -> str:
    folded = unicodedata.normalize("NFD", str(value or "")).casefold()
    return "".join(
        character for character in folded
        if not unicodedata.combining(character)
    ).replace("đ", "d")


def _has_question_cue(value: str) -> bool:
    return bool(_QUESTION_CUE_RE.search(_ascii_fold(value)))


def _right_starts_with_question_cue(value: str) -> bool:
    return bool(_RIGHT_QUESTION_START_RE.match(_ascii_fold(value).strip()))


def _clean_clause(value: str) -> str:
    return " ".join(value.strip(" -•\t?").split())


def _unique_clause_parts(parts: Sequence[str], original: str) -> list[str]:
    cleaned: list[str] = []
    original_key = original.casefold()
    seen: set[str] = set()
    for raw in parts:
        part = _clean_clause(raw)
        key = part.casefold()
        if not part or key == original_key or not extract_content_terms(part) or key in seen:
            continue
        seen.add(key)
        cleaned.append(part)
        if len(cleaned) >= _MAX_FACETS:
            break
    return cleaned


def _split_question_clauses(original: str) -> list[str]:
    """Split only on explicit question structure, never on noun-phrase 'and'."""
    structural = _unique_clause_parts(_FACET_SPLIT_RE.split(original), original)
    if len(structural) >= 2:
        return structural

    question_parts = _unique_clause_parts(re.split(r"\?\s+", original), original)
    if len(question_parts) >= 2 and all(_has_question_cue(part) for part in question_parts):
        return question_parts

    comma_parts = _unique_clause_parts(_COMMA_CLAUSE_SPLIT_RE.split(original), original)
    if (
        len(comma_parts) >= 2
        and all(_has_question_cue(part) for part in comma_parts)
        and _right_starts_with_question_cue(comma_parts[1])
    ):
        return comma_parts

    bare_parts = _unique_clause_parts(_BARE_CLAUSE_SPLIT_RE.split(original), original)
    if (
        len(bare_parts) >= 2
        and all(_has_question_cue(part) for part in bare_parts)
        and _right_starts_with_question_cue(bare_parts[1])
    ):
        return bare_parts
    return []


def _has_explicit_cross_source_wording(query: str) -> bool:
    return bool(_CROSS_SOURCE_WORDING_RE.search(_ascii_fold(query)))

def resolve_summary_first_routing(default: bool = False) -> bool:
    """Return whether summary-first routing is enabled.

    ``AIOS_RAG_V2_SUMMARY_FIRST`` wins when set. Unset keeps ``default`` so the
    old full-corpus multi-variant path stays active until the operator opts in.
    """
    raw = str(os.environ.get("AIOS_RAG_V2_SUMMARY_FIRST", "") or "").strip().casefold()
    if raw in _SUMMARY_FIRST_TRUE:
        return True
    if raw in _SUMMARY_FIRST_FALSE:
        return False
    return bool(default)


def _has_overview_wording(query: str) -> bool:
    return bool(_OVERVIEW_WORDING_RE.search(_ascii_fold(query)))


def _has_concrete_entity(query: str, target_terms: Sequence[str] = ()) -> bool:
    text = str(query or "")
    if _CONCRETE_ENTITY_RE.search(text):
        return True
    for term in target_terms:
        token = str(term or "")
        if any(character.isdigit() for character in token) and len(token) >= 2:
            return True
    return False


def detect_retrieval_mode(
    query: str,
    intent_category: str = "general",
    target_terms: Sequence[str] = (),
) -> str:
    """Classify query specificity for optional summary-first routing.

    - ``overview``: summarize / open-ended / short vague asks without entities
    - ``focused``: medium specificity or explicit multi-source synthesis
    - ``full``: procedures and concrete entity/document lookups
    """
    intent = str(intent_category or "general").casefold()
    if intent in {"procedure", "actionable_output", "diagnosis", "precise_lookup", "excel_native"}:
        return "full"
    if _has_concrete_entity(query, target_terms):
        return "full"
    if _has_overview_wording(query):
        return "overview"
    terms = tuple(target_terms) if target_terms else extract_content_terms(query)
    token_count = len(str(query or "").split())
    if intent in {"summarize_document", "open_ended_research"}:
        return "overview"
    if token_count <= 8 and len(terms) <= 4 and intent in {"general", "cross_source_synthesis"}:
        return "overview"
    if intent == "cross_source_synthesis" or len(terms) >= 4:
        return "focused"
    return "full"


def max_variants_for_mode(
    retrieval_mode: str,
    *,
    overview_max: int = _DEFAULT_OVERVIEW_MAX_VARIANTS,
    focused_max: int = _DEFAULT_FOCUSED_MAX_VARIANTS,
    full_max: int = _DEFAULT_FULL_MAX_VARIANTS,
) -> int:
    mode = str(retrieval_mode or "full").casefold()
    if mode == "overview":
        return max(1, int(overview_max))
    if mode == "focused":
        return max(1, int(focused_max))
    return max(1, int(full_max))


def apply_summary_first_to_plan(
    plan: RetrievalQueryPlan,
    *,
    overview_max: int = _DEFAULT_OVERVIEW_MAX_VARIANTS,
    focused_max: int = _DEFAULT_FOCUSED_MAX_VARIANTS,
    full_max: int = _DEFAULT_FULL_MAX_VARIANTS,
) -> RetrievalQueryPlan:
    """Attach retrieval_mode and cap variants. Call only when summary-first is on."""
    mode = detect_retrieval_mode(
        plan.original_query,
        plan.intent_category,
        plan.target_terms,
    )
    cap = max_variants_for_mode(
        mode,
        overview_max=overview_max,
        focused_max=focused_max,
        full_max=full_max,
    )
    variants = tuple(plan.variants[:cap]) or plan.variants
    return replace(plan, retrieval_mode=mode, variants=variants)


def query_needs_broad_ready_retrieval(plan: RetrievalQueryPlan) -> bool:
    """Ready-source retrieval may inspect the full ready set for multi-aspect questions."""
    extra_facets = tuple(facet_id for facet_id in plan.facet_ids if facet_id != "query")
    return plan.intent_category == "cross_source_synthesis" or len(extra_facets) >= 2


def detect_query_language(query: str) -> str:
    """Classify a query for routing telemetry without using source content.

    A material combination of Japanese/Vietnamese script cues with English prose
    is labelled ``mixed``. Pure Japanese technical questions can include product
    identifiers, so they remain ``ja``. Unknown text makes no language claim.
    """
    text = str(query or "").strip()
    if not text:
        return "unknown"
    japanese = bool(_JAPANESE_RE.search(text) or _CJK_RE.search(text))
    vietnamese = bool(_VIETNAMESE_DIACRITIC_RE.search(text))
    latin_words = len(re.findall(r"\b[A-Za-z]{3,}\b", text))
    if japanese and vietnamese:
        return "mixed"
    if japanese:
        return "mixed" if latin_words >= 5 else "ja"
    if vietnamese:
        return "mixed" if latin_words >= 5 else "vi"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def _clean_variant(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = " ".join(value.strip().split())
    if (
        not cleaned
        or len(cleaned) > _MAX_VARIANT_CHARS
        or _DANGEROUS_QUERY_RE.search(cleaned)
        or _UNSAFE_EXPANSION_RE.search(cleaned)
    ):
        return ""
    return cleaned


def _identity_variants(
    original: str,
    intent_category: str = "general",
) -> Tuple[RetrievalQueryVariant, ...]:
    if not original:
        return ()
    language_hint = detect_query_language(original)
    variants = [
        RetrievalQueryVariant(
            text=original,
            language_hint=language_hint,
            origin="original",
            variant_id="query_original",
            facet_id="query",
        )
    ]
    parts = _split_question_clauses(original)
    if len(parts) >= 2:
        for position, part in enumerate(parts, 1):
            variants.append(
                RetrievalQueryVariant(
                    text=part,
                    language_hint=language_hint,
                    origin="facet",
                    variant_id=f"facet_{position}",
                    facet_id=f"facet_{position}",
                )
            )

    return tuple(variants[:_MAX_VARIANTS])


def _detect_intent_category(query: str) -> tuple[str, tuple[str, ...]]:
    """Return a corpus-neutral answer shape from explicit question wording.

    This deliberately does not infer a subject, add aliases, or inspect source
    text.  It only recognizes an operational/procedural request stated by the
    user (for example, "how does ... work?" or Vietnamese "hoạt động như thế
    nào?").  That shape needs a larger same-document evidence window than a
    fact lookup; treating it as generic silently cuts out later manual steps.
    """
    ascii_folded = _ascii_fold(query)
    procedure_markers = (
        "how does" in ascii_folded and "work" in ascii_folded,
        "how does" in ascii_folded and "operate" in ascii_folded,
        "how to " in ascii_folded,
        "what are the steps" in ascii_folded,
        "hoat dong nhu the nao" in ascii_folded,
        "lam the nao" in ascii_folded,
        "cach thuc hien" in ascii_folded,
        "quy trinh" in ascii_folded,
        "cac buoc" in ascii_folded,
        "huong dan" in ascii_folded,
    )
    if any(procedure_markers):
        return "procedure", ("query",)
    return "general", ("query",)


def match_text_obligations(
    intent_category: str,
    value: str | Iterable[str],
    *,
    required_obligations: Sequence[str] = (),
) -> Tuple[str, ...]:
    """Do not manufacture semantic obligation labels from source vocabulary."""
    return ()


def identity_query_plan(query: str, *, status: str = "identity") -> RetrievalQueryPlan:
    """Return the guaranteed offline plan with bounded structural facets."""
    original = " ".join((query or "").strip().split())
    intent_category, required_obligations = _detect_intent_category(original)
    variants = _identity_variants(original, intent_category)
    extra_facets = tuple(item.facet_id for item in variants if item.origin == "facet")
    if intent_category == "general" and (
        len(extra_facets) >= 2 or _has_explicit_cross_source_wording(original)
    ):
        intent_category = "cross_source_synthesis"
    effective_status = "faceted" if status == "identity" and len(variants) > 1 else status
    all_plan_text = " ".join([original, *(v.text for v in variants)])
    return RetrievalQueryPlan(
        original_query=original,
        variants=variants,
        content_terms=extract_content_terms(all_plan_text),
        target_terms=extract_target_terms(original),
        expansion_status=effective_status,
        intent_category=intent_category,
        required_obligations=required_obligations,
        query_language=detect_query_language(original),
    )


def build_query_plan(query: str, expansion: Mapping[str, Any] | None = None) -> RetrievalQueryPlan:
    """Validate untrusted expansion output and fail safely to an identity plan.

    External/cloud expansions may enrich query variants for candidate recall,
    but cannot act as a routing authority or override deterministic intent/obligations.
    """
    fallback = identity_query_plan(query)
    if not fallback.original_query or not isinstance(expansion, Mapping):
        return fallback

    raw_variants = expansion.get("variants")
    if not isinstance(raw_variants, Sequence) or isinstance(raw_variants, (str, bytes)):
        return identity_query_plan(query, status="expansion_unavailable")

    intent_category = str(expansion.get("intent_category") or fallback.intent_category)
    required_obligations = tuple(
        str(ob) for ob in expansion.get("required_obligations", fallback.required_obligations)
    )


    variants = list(fallback.variants)
    seen = {item.text.casefold() for item in variants}
    total_chars = sum(len(item.text) for item in variants)
    expansion_position = 0
    for raw in raw_variants:
        if len(variants) >= _MAX_VARIANTS:
            break
        if not isinstance(raw, Mapping):
            continue
        text = _clean_variant(raw.get("text"))
        if not text or text.casefold() in seen or total_chars + len(text) > _MAX_TOTAL_VARIANT_CHARS:
            continue
        language_hint = _clean_variant(raw.get("language_hint"))[:24] or "unknown"
        origin = _clean_variant(raw.get("origin"))[:32] or "expansion"
        target_equivalent = bool(raw.get("target_equivalent") is True)
        if origin in {"structural_intent", "facet", "original"}:
            target_equivalent = False
        expansion_position += 1
        variants.append(
            RetrievalQueryVariant(
                text=text,
                language_hint=language_hint,
                origin=origin,
                variant_id=f"expansion_{expansion_position}",
                facet_id="query",
                target_equivalent=target_equivalent,
            )
        )
        seen.add(text.casefold())
        total_chars += len(text)

    if len(variants) == len(fallback.variants):
        return identity_query_plan(query, status="expansion_rejected")
    all_plan_text = " ".join([fallback.original_query, *(v.text for v in variants)])
    return RetrievalQueryPlan(
        original_query=fallback.original_query,
        variants=tuple(variants),
        content_terms=extract_content_terms(all_plan_text),
        target_terms=extract_target_terms(fallback.original_query),
        expansion_status="expanded",
        intent_category=intent_category,
        required_obligations=required_obligations,
        query_language=fallback.query_language,
    )



def coerce_query_plan(query: str | RetrievalQueryPlan) -> RetrievalQueryPlan:
    """Preserve the historical string API while accepting an already validated plan."""
    return query if isinstance(query, RetrievalQueryPlan) else identity_query_plan(str(query or ""))
