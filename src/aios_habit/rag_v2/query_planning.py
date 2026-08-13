"""Generic, provider-independent query planning for local retrieval.

The planner deliberately carries only the user query and validated retrieval variants.
It never receives documents, source metadata, or evidence text.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
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

    @property
    def facet_ids(self) -> Tuple[str, ...]:
        """Return stable conceptual facets without exposing query text."""
        return tuple(dict.fromkeys(item.facet_id for item in self.variants if item.facet_id))

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
    parts = []
    for raw_part in _FACET_SPLIT_RE.split(original):
        part = " ".join(raw_part.strip(" -•\t").split())
        if not part or part.casefold() == original.casefold() or not extract_content_terms(part):
            continue
        if part.casefold() not in {item.casefold() for item in parts}:
            parts.append(part)
        if len(parts) >= _MAX_FACETS:
            break
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
    """Return the corpus-neutral fallback shape.

    Semantic answer-shape classification belongs to a learned or caller-supplied
    component. The deterministic core must not infer it from embedded vocabularies.
    """
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

    Expected expansion schema:
    ``{"variants": [{"text": "...", "language_hint": "ja", "origin": "translation", "target_equivalent": true}]}``.
    ``target_equivalent`` is accepted only for bounded external expansions; it
    is never assigned to internally generated structural aliases.
    Invalid, excessive, duplicate, or unsafe variants are ignored rather than raised.
    """
    fallback = identity_query_plan(query)
    if not fallback.original_query or not isinstance(expansion, Mapping):
        return fallback

    raw_variants = expansion.get("variants")
    if not isinstance(raw_variants, Sequence) or isinstance(raw_variants, (str, bytes)):
        return identity_query_plan(query, status="expansion_unavailable")

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
        # The flag is meaningful only for external query reformulations.  A
        # caller cannot mark a structural/internal alias as target proof.
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
        intent_category=fallback.intent_category,
        required_obligations=fallback.required_obligations,
        query_language=fallback.query_language,
    )


def coerce_query_plan(query: str | RetrievalQueryPlan) -> RetrievalQueryPlan:
    """Preserve the historical string API while accepting an already validated plan."""
    return query if isinstance(query, RetrievalQueryPlan) else identity_query_plan(str(query or ""))
