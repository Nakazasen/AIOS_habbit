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
_DANGEROUS_QUERY_RE = re.compile(r"[\x00-\x1f]|[\"'`;]|--|/\*|\*/")
_COMMON_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "what", "when", "where", "which", "who", "with",
})
_FACET_SPLIT_RE = re.compile(r"(?:[\r\n;]+|(?<=[.!?])\s+)")
_MAX_FACETS = 4
_MAX_VARIANTS = 6
_MAX_VARIANT_CHARS = 240
_MAX_TOTAL_VARIANT_CHARS = 900


@dataclass(frozen=True)
class RetrievalQueryVariant:
    """One bounded retrieval formulation with no source-derived content."""

    text: str
    language_hint: str = "unknown"
    origin: str = "original"
    variant_id: str = "query_original"
    facet_id: str = "query"


@dataclass(frozen=True)
class RetrievalQueryPlan:
    """Validated original query plus deterministic, inspectable retrieval variants."""

    original_query: str
    variants: Tuple[RetrievalQueryVariant, ...]
    content_terms: Tuple[str, ...]
    expansion_status: str = "identity"
    intent_category: str = "general"
    required_obligations: Tuple[str, ...] = ("query",)

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
                }
                for item in self.variants
            ],
            "content_terms": self.content_terms,
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
    """Return ordered, unique query terms after removing common function words."""
    seen: set[str] = set()
    result = []
    for match in _TOKEN_RE.finditer(value or ""):
        token = match.group(0).lower()
        if token in _COMMON_STOPWORDS or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return tuple(result)


def _clean_variant(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = " ".join(value.strip().split())
    if not cleaned or len(cleaned) > _MAX_VARIANT_CHARS or _DANGEROUS_QUERY_RE.search(cleaned):
        return ""
    return cleaned


def _identity_variants(original: str) -> Tuple[RetrievalQueryVariant, ...]:
    if not original:
        return ()
    variants = [
        RetrievalQueryVariant(
            text=original,
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
    if len(parts) < 2:
        return tuple(variants)
    for position, part in enumerate(parts, 1):
        variants.append(
            RetrievalQueryVariant(
                text=part,
                origin="facet",
                variant_id=f"facet_{position}",
                facet_id=f"facet_{position}",
            )
        )
    return tuple(variants[:_MAX_VARIANTS])


_DIAGNOSIS_RE = re.compile(
    r"\b(?:error|errors|fault|faults|failure|failures|troubleshoot|troubleshooting|exception|symptom|handling|handled|bug|issue|issues|outage|unavailable|recover|recovery|root cause|lỗi|sự cố|báo lỗi|nguyên nhân|khắc phục|phục hồi|bất thường|xử lý|fehler|störung)\b",
    re.IGNORECASE | re.UNICODE,
)
_PROCEDURE_RE = re.compile(
    r"\b(?:steps|procedure|procedures|how to|how should|checklist|actionable checklist|guideline|instructions|quy trình|các bước|hướng dẫn|thực hiện|anleitung|schritte|process-plan)\b",
    re.IGNORECASE | re.UNICODE,
)
_COMPARISON_RE = re.compile(
    r"\b(?:compare|comparing|difference|differences|versus|vs|so sánh|khác biệt|vergleich|unterschied)\b",
    re.IGNORECASE | re.UNICODE,
)
_LOOKUP_TABLE_RE = re.compile(
    r"\b(?:list|show|find|lookup|spreadsheet|table|excel|sheet|row|cell|column|bảng|trạng thái|status|transition|valid status|track|tracked)\b",
    re.IGNORECASE | re.UNICODE,
)


def _detect_intent_category(query: str) -> tuple[str, tuple[str, ...]]:
    """Classify generic answer shape from query-only cues with stable precedence."""
    if not query:
        return "general", ("query",)

    has_lookup = bool(_LOOKUP_TABLE_RE.search(query))
    has_comparison = bool(_COMPARISON_RE.search(query))
    has_diagnosis = bool(_DIAGNOSIS_RE.search(query))
    has_procedure = bool(_PROCEDURE_RE.search(query))

    # A request to list or locate values is a lookup even when its target names an error.
    if has_lookup and not (has_comparison or has_procedure):
        return "lookup", ("lookup_target", "data_value")
    if has_comparison:
        return "compare_change", ("side_a", "side_b", "differences")
    if has_diagnosis:
        return "diagnosis", ("problem", "check", "action")
    if has_procedure:
        return "procedure", ("precheck", "step", "postcheck")
    if has_lookup:
        return "lookup", ("lookup_target", "data_value")
    return "general", ("query",)


_OBLIGATION_CUES = {
    "problem": frozenset({"error", "fault", "failure", "exception", "issue", "outage", "unavailable", "lỗi", "sự", "hỏng", "thất"}),
    "check": frozenset({"check", "verify", "inspect", "review", "test", "monitor", "log", "kiểm", "xác"}),
    "action": frozenset({"fix", "restart", "recover", "resolve", "handle", "execute", "step", "procedure", "khắc", "phục", "xử", "thực"}),
    "precheck": frozenset({"before", "precheck", "prerequisite", "prepare", "initial", "verify", "prior", "trước", "chuẩn", "kiểm"}),
    "step": frozenset({"step", "execute", "run", "perform", "procedure", "instructions", "bước", "thực", "chạy"}),
    "postcheck": frozenset({"after", "postcheck", "validate", "confirm", "monitor", "verify", "sau", "xác", "kiểm"}),
    "side_a": frozenset({"before", "current", "old", "existing", "former", "trước", "cũ", "hiện"}),
    "side_b": frozenset({"after", "new", "target", "proposed", "replacement", "sau", "mới", "đề"}),
    "differences": frozenset({"difference", "different", "versus", "compare", "change", "delta", "khác", "so", "thay"}),
}


def match_text_obligations(
    intent_category: str,
    value: str | Iterable[str],
    *,
    required_obligations: Sequence[str] = (),
) -> Tuple[str, ...]:
    """Return stable obligation IDs explicitly supported by local text/structure.

    This helper is deliberately lexical and source-local: it never adds an obligation
    merely because the query requests one. Callers must surface absent obligations as
    limitations instead of fabricating a supported answer section.
    """
    text = " ".join(value) if not isinstance(value, str) else value
    tokens = set(_TOKEN_RE.findall(text.casefold()))
    obligations = tuple(required_obligations)
    if not obligations:
        return ()
    return tuple(
        obligation
        for obligation in obligations
        if tokens & _OBLIGATION_CUES.get(obligation, frozenset())
    )


def identity_query_plan(query: str, *, status: str = "identity") -> RetrievalQueryPlan:
    """Return the guaranteed offline plan with bounded structural facets."""
    original = " ".join((query or "").strip().split())
    variants = _identity_variants(original)
    effective_status = "faceted" if status == "identity" and len(variants) > 1 else status
    intent_category, required_obligations = _detect_intent_category(original)
    return RetrievalQueryPlan(
        original_query=original,
        variants=variants,
        content_terms=extract_content_terms(original),
        expansion_status=effective_status,
        intent_category=intent_category,
        required_obligations=required_obligations,
    )


def build_query_plan(query: str, expansion: Mapping[str, Any] | None = None) -> RetrievalQueryPlan:
    """Validate untrusted expansion output and fail safely to an identity plan.

    Expected expansion schema:
    ``{"variants": [{"text": "...", "language_hint": "ja", "origin": "translation"}]}``.
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
        expansion_position += 1
        variants.append(
            RetrievalQueryVariant(
                text=text,
                language_hint=language_hint,
                origin=origin,
                variant_id=f"expansion_{expansion_position}",
                facet_id="query",
            )
        )
        seen.add(text.casefold())
        total_chars += len(text)

    if len(variants) == len(fallback.variants):
        return identity_query_plan(query, status="expansion_rejected")
    return RetrievalQueryPlan(
        original_query=fallback.original_query,
        variants=tuple(variants),
        content_terms=extract_content_terms(fallback.original_query),
        expansion_status="expanded",
        intent_category=fallback.intent_category,
        required_obligations=fallback.required_obligations,
    )


def coerce_query_plan(query: str | RetrievalQueryPlan) -> RetrievalQueryPlan:
    """Preserve the historical string API while accepting an already validated plan."""
    return query if isinstance(query, RetrievalQueryPlan) else identity_query_plan(str(query or ""))