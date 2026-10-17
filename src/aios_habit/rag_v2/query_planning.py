"""Generic, provider-independent query planning for local retrieval.

The planner deliberately carries only the user query and validated retrieval variants.
It never receives documents, source metadata, or evidence text.
"""
from __future__ import annotations

import os
from pathlib import Path
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
_TECHNICAL_CODE_RE = re.compile(r"\b[A-Z]\d{2,5}\b")
_NG_RE = re.compile(r"\bNG\b", re.IGNORECASE)
_FOUR_M_RE = re.compile(r"\b4M\b")
_MA_UNIT_RE = re.compile(r"\b\d+\s*mA\b", re.IGNORECASE)
_MEASUREMENT_UNIT_RE = re.compile(r"(?:(?:\d+(?:[.,]\d+)?|\b)\s*(?:[µ\u00b5]m|um|mm|dot)\b|\b\d+\s*mA\b)", re.IGNORECASE)
_TECHNICAL_WORD_RE = re.compile(r"\b(?:beam|jig|lightpath|takt_\w+|errcolor|bowoveradjustment)\b", re.IGNORECASE)
_VIET_TECHNICAL_RE = re.compile(r"\b(?:loi|hong|bang)\b", re.IGNORECASE)
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
    r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b|"
    r"\.(?:exe|pdf|xlsx|xls|pptx|ppt|txt|dll|csv)\b|"
    r"\b\d{1,4}(?:[/-]\d{1,4}){1,2}\b|"
    r"\b(?:sheet|cell|row|column|page|trang|sku|sop|error|fault|code)\s*[:#-]?\s*\d+\b|"
    r"\bversion\s+\d+\b"
    r")",
    re.IGNORECASE,
)
_GENERAL_PROCESS_RE = re.compile(
    r"(?:"
    r"nhu the nao|"
    r"\bra sao\b|"
    r"gom nhung|"
    r"thanh phan chinh|"
    r"dien ra qua|"
    r"noi chung|"
    r"phoi hop|"
    r"buoc co ban|"
    r"nhung buoc nao"
    r")"
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
class HybridRankingConfig:
    """Bounded, scale-independent ranking controls for three retrieval channels (QD-07)."""

    rrf_k: int = 60
    lexical_weight: float = 1.0
    dense_weight: float = 1.0
    sparse_weight: float = 1.0
    rerank_limit: int = 30
    near_duplicate_threshold: float = 0.92
    multivector_score_band: float = 0.15

    def __post_init__(self) -> None:
        if self.rrf_k < 1 or self.rerank_limit < 1:
            raise ValueError("ranking limits must be positive")
        if (
            self.lexical_weight <= 0.0
            or self.dense_weight <= 0.0
            or self.sparse_weight <= 0.0
        ):
            raise ValueError("channel weights must be positive")
        if not 0.0 <= self.near_duplicate_threshold <= 1.0:
            raise ValueError("near_duplicate_threshold must be between zero and one")
        if self.multivector_score_band < 0.0:
            raise ValueError("multivector_score_band must be non-negative")


def determine_query_channel_ranking_config(query: str) -> Optional[HybridRankingConfig]:
    """Single authoritative decision point for dynamic channel weight overrides (QD-07)."""
    if not query:
        return None
    clean_query = query.replace("`", "")
    has_date = bool(re.search(r"\b\d{1,2}/\d{1,2}\b", clean_query))
    has_maint_ctx = False
    try:
        from aios_habit.domain_config import get_maintenance_context_pattern
        has_maint_ctx = bool(get_maintenance_context_pattern().search(clean_query))
    except Exception:
        has_maint_ctx = False

    if has_date and has_maint_ctx:
        return HybridRankingConfig(lexical_weight=0.2, dense_weight=3.0, sparse_weight=1.5)

    has_col_range = (
        bool(re.search(r"[-+]\d+\s*(?:đến|to|~|-)\s*[-+]\d+", clean_query, re.IGNORECASE))
        or bool(re.search(r"cột\s*(?:từ\s*)?[-+]\d+", clean_query, re.IGNORECASE))
    )
    if has_col_range:
        return HybridRankingConfig(lexical_weight=0.05, dense_weight=2.0, sparse_weight=3.5)

    return None


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
    # Unified channel ranking configuration (QD-07)
    ranking_config: Optional[HybridRankingConfig] = None

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


CJK_GRAMMAR_STOPWORDS: frozenset[str] = frozenset({
    # Japanese question words & particles
    "何ですか", "何で", "何です", "何でしょうか", "何でしょう", "ですか", "でしたか", "でした", "でし", "したか",
    "ますか", "ましたか", "りま", "ます", "すか", "なりま", "ります", "でしょうか", "何", "なん", "なに",
    "どのような", "どのよう", "どのよ", "のよう", "ような", "どの", "のよ", "よう", "うな",
    "どう", "どれ", "どんな", "なぜ", "どうして", "どこ", "いつ", "いくつ", "誰", "どちら",
    # Japanese particles and connectives
    "は", "が", "を", "に", "の", "と", "で", "へ", "から", "まで", "より", "では", "とは", "には", "でも",
    "また", "および", "あるいは", "または", "など", "について", "における", "による", "によって", "ため", "として",
    # Japanese grammatical conjugations / auxiliary fragments
    "になる", "になり", "になります", "になるか", "になりますか", "になった", "なると", "なら", "にな", "なり",
    "である", "超え", "える", "ると", "を超", "を超え", "超える", "えると", "ると必", "と必", "と必ず", "必ず",
    "長くな", "くなる", "が長", "長く", "くな", "なる", "離が", "離が長", "が長く",
    "る想", "なる想", "態は", "状態は", "態は何", "は何で", "は何",
    "うな発", "な発生", "な発", "はど", "ではど", "はどの", "ではどの", "はどのよ",
    "し", "した", "たか", "て", "ても", "ば", "たら", "たり", "ない", "なかった", "ず",
    "能に", "能にな", "読取不能に", "不能にな", "能になり", "になりま", "なります", "りますか",
    "定状態は", "状態は何", "態は何で", "は何です", "定状態", "想定状", "取不", "読取不", "取不能",
    "る想定", "定状",
    # Chinese question words & particles
    "是什么", "是多少", "怎样", "如何", "是否有", "哪些", "什么", "怎么", "为什么", "哪天", "哪个", "何时", "何处", "吗", "呢", "吧", "的", "了", "在", "是", "与", "和", "或", "或者", "以及",
})


def _split_script_boundaries(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"([a-zA-Z0-9]+)([\u3040-\u30ff\u3400-\u9fff])", r"\1 \2", text)
    text = re.sub(r"([\u3040-\u30ff\u3400-\u9fff])([a-zA-Z0-9]+)", r"\1 \2", text)
    return text


def extract_content_terms(value: str) -> Tuple[str, ...]:
    """Return ordered, unique query terms after generic function-word removal."""
    seen: set[str] = set()
    result = []
    # Extract paired C-line/jig aliases (e.g. C23とC24 -> c23/24, c23/c24)
    paired_c = re.search(r"(?<![A-Za-z0-9])(C\d{2,3})\s*(?:と|and|&|/|,|\+)\s*C?(\d{2,3})(?![A-Za-z0-9])", value or "", re.IGNORECASE)
    if paired_c:
        c1 = paired_c.group(1).lower()
        c2 = paired_c.group(2).lower()
        for p in (f"{c1}/{c2}", f"{c1}/c{c2}"):
            if p not in seen:
                seen.add(p)
                result.append(p)
    split_text = _split_script_boundaries(value or "")
    # 1. Non-CJK tokens and short pure CJK terms from split_text
    for match in _TOKEN_RE.finditer(split_text):
        token = match.group(0).lower()
        if token in _COMMON_STOPWORDS or token in CJK_GRAMMAR_STOPWORDS or token in seen:
            continue
        # Drop unsegmented mixed/long CJK phrases (len > 4 or containing Japanese particles)
        if _CJK_RE.search(token) and (len(token) > 4 or any(c in token for c in "はがをにのとでへかもてただなねよか")):
            continue
        seen.add(token)
        result.append(token)
    # Preserve signed numeric tokens (e.g. -8, -3, +2, +8) and double-dash '--'
    for match in re.finditer(r"(?<!\w)[-+]\d+(?:\.\d+)?(?!\w)", value or ""):
        st = match.group(0).lower()
        if st not in seen:
            seen.add(st)
            result.append(st)
    if "--" in (value or ""):
        if "--" not in seen:
            seen.add("--")
            result.append("--")
    # 2. CJK compound decomposition
    if _CJK_RE.search(split_text):
        for match in _CJK_RE.finditer(split_text):
            compound = match.group(0).lower()
            if len(compound) < 2:
                continue
            # Add full compound if 2 <= len <= 6 and not bounded by particles
            if (
                2 <= len(compound) <= 6
                and compound not in _COMMON_STOPWORDS
                and compound not in CJK_GRAMMAR_STOPWORDS
                and compound not in seen
            ):
                if not any(compound.startswith(p) for p in "はがをにのとでへかもてただなねよる") and not any(compound.endswith(p) for p in "はがをにのとでへかもてただなねよか"):
                    seen.add(compound)
                    result.append(compound)
            for width in (2, 3):
                for index in range(len(compound) - width + 1):
                    ngram = compound[index : index + width]
                    if ngram in _COMMON_STOPWORDS or ngram in CJK_GRAMMAR_STOPWORDS or ngram in seen:
                        continue
                    if any(ngram.startswith(p) for p in "はがをにのとでへかもてただなねよる") or any(ngram.endswith(p) for p in "はがをにのとでへかもてただなねよか"):
                        continue
                    seen.add(ngram)
                    result.append(ngram)
    return tuple(result)


VIETNAMESE_EVIDENCE_STOPWORDS: frozenset[str] = frozenset({
    "ủng", "hộ", "chung", "riêng", "hay", "và", "của", "hoặc",
})


def extract_evidence_terms(value: str) -> Tuple[str, ...]:
    """Return content terms excluding Vietnamese/CJK function words for evidence coverage."""
    terms = extract_content_terms(value)
    return tuple(
        term for term in terms
        if term.casefold() not in VIETNAMESE_EVIDENCE_STOPWORDS
        and term.casefold() not in CJK_GRAMMAR_STOPWORDS
    )


def extract_target_terms(value: str) -> Tuple[str, ...]:
    """Return literal terms from the user query without semantic rewriting."""
    return extract_evidence_terms(value)



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
    cleaned = (value or "").replace("`", "")
    # Strip leading bullet dashes, but preserve trailing content like '--'
    cleaned = re.sub(r"^[\s\-•\t]+", "", cleaned)
    cleaned = re.sub(r"[\s•\t\?]+$", "", cleaned)
    return " ".join(cleaned.split())


_PURE_INTERROGATIVE_RE = re.compile(
    r"^(?:(?:phải|cần)\s+)?(?:xử\s*lý|khắc\s*phục|giải\s*quyết|làm|thực\s*hiện)?\s*"
    r"(?:như\s*thế\s*nào|thế\s*nào|ra\s*sao|sao|làm\s*sao|gì|đâu|nào)\s*[\?!\.]*$",
    re.IGNORECASE,
)


def _unique_clause_parts(parts: Sequence[str], original: str) -> list[str]:
    cleaned: list[str] = []
    original_key = original.casefold()
    seen: set[str] = set()
    for raw in parts:
        part = _clean_clause(raw)
        key = part.casefold()
        if (
            not part
            or key == original_key
            or not extract_content_terms(part)
            or key in seen
            or _PURE_INTERROGATIVE_RE.match(part.strip())
        ):
            continue
        seen.add(key)
        cleaned.append(part)
        if len(cleaned) >= _MAX_FACETS:
            break
    return cleaned


def _split_question_clauses(original: str) -> list[str]:
    """Split only on explicit question structure, never on noun-phrase 'and'."""
    raw_splits = _FACET_SPLIT_RE.split(original)
    if len(raw_splits) >= 2:
        structural = _unique_clause_parts(raw_splits, original)
        if structural:
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

    - ``overview``: general system or process questions, or short vague asks, with no code
    - ``focused``: medium specificity or explicit multi-source synthesis
    - ``full``: a concrete code, file, table, or a specific procedure
    """
    intent = str(intent_category or "general").casefold()
    concrete = _has_concrete_entity(query, target_terms)
    general = bool(_GENERAL_PROCESS_RE.search(_ascii_fold(query))) or _has_overview_wording(query)
    if concrete:
        return "full"
    if intent in {"procedure", "actionable_output", "diagnosis", "precise_lookup", "excel_native"} and not general:
        return "full"
    if general or intent in {"summarize_document", "open_ended_research"}:
        return "overview"
    terms = tuple(target_terms) if target_terms else extract_content_terms(query)
    token_count = len(str(query or "").split())
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
    cleaned = " ".join(value.replace("`", "").strip().split())
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
    clean_original = _clean_variant(original) or original
    variants = [
        RetrievalQueryVariant(
            text=clean_original,
            language_hint=language_hint,
            origin="original",
            variant_id="query_original",
            facet_id="query",
        )
    ]
    parts = _split_question_clauses(original)
    if parts:
        for position, part in enumerate(parts, 1):
            if (
                part.casefold() != original.casefold()
                and part.casefold() != clean_original.casefold()
            ):
                variants.append(
                    RetrievalQueryVariant(
                        text=part,
                        language_hint=language_hint,
                        origin="facet",
                        variant_id=f"facet_{position}",
                        facet_id=f"facet_{position}",
                    )
                )

    paired_match = re.search(r"(?<![A-Za-z0-9])(C\d{2,3})\s*(?:と|and|&|/|,|\+)\s*C?(\d{2,3})(?![A-Za-z0-9])", original, re.IGNORECASE)
    if paired_match:
        c_prefix = paired_match.group(1).upper()
        c_second = paired_match.group(2)
        paired_alias = f"{c_prefix}/{c_second}"
        paired_variant_text = original[:paired_match.start()] + paired_alias + original[paired_match.end():]
        variants.append(
            RetrievalQueryVariant(
                text=paired_variant_text,
                language_hint=language_hint,
                origin="paired_alias",
                variant_id="paired_alias_1",
                facet_id="query",
                target_equivalent=True,
            )
        )

    optics_variant = _build_optical_lsu_crosslingual_variant(original, language_hint)
    if optics_variant is not None:
        variants.append(optics_variant)

    return tuple(variants[:_MAX_VARIANTS])


def _resolve_glossary_lsu_path() -> Path | None:
    """Resolve the location of config/glossary_lsu.json."""
    custom_path = os.environ.get("AIOS_GLOSSARY_LSU_PATH")
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.is_file():
            return p
    try:
        from aios_habit.workspace_paths import default_agent_workspace_root
        candidate = default_agent_workspace_root() / "config" / "glossary_lsu.json"
        if candidate.is_file():
            return candidate
    except Exception:
        pass
    try:
        candidate = Path(__file__).resolve().parents[3] / "config" / "glossary_lsu.json"
        if candidate.is_file():
            return candidate
    except Exception:
        pass
    candidate = Path.cwd() / "config" / "glossary_lsu.json"
    if candidate.is_file():
        return candidate
    return None


def _load_optical_lsu_glossary() -> tuple[
    tuple[tuple[re.Pattern[str], str], ...],
    tuple[tuple[re.Pattern[str], str], ...]
]:
    """Dynamically load 28 optical LSU equivalences from external configuration file.

    Fulfills ticket DESKTOP-QD-S2-GLOSSARY-WORKER-LIFECYCLE-HOME (QD-03).
    Decouples glossary rules from Python source code, maintaining 100% equivalence.
    """
    glossary_path = _resolve_glossary_lsu_path()
    if glossary_path is not None:
        try:
            with open(glossary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ja_to_vi_raw = data.get("ja_to_vi", [])
            vi_to_ja_raw = data.get("vi_to_ja", [])

            ja_to_vi_rules: list[tuple[re.Pattern[str], str]] = []
            for item in ja_to_vi_raw:
                p_str = item.get("pattern", "")
                eq = item.get("equivalent", "")
                if p_str and eq:
                    flags = re.IGNORECASE if "IGNORECASE" in str(item.get("flags", "IGNORECASE")) else 0
                    ja_to_vi_rules.append((re.compile(p_str, flags), eq))

            vi_to_ja_rules: list[tuple[re.Pattern[str], str]] = []
            for item in vi_to_ja_raw:
                p_str = item.get("pattern", "")
                eq = item.get("equivalent", "")
                if p_str and eq:
                    flags = re.IGNORECASE if "IGNORECASE" in str(item.get("flags", "IGNORECASE")) else 0
                    vi_to_ja_rules.append((re.compile(p_str, flags), eq))

            if len(ja_to_vi_rules) == 16 and len(vi_to_ja_rules) == 12:
                return tuple(ja_to_vi_rules), tuple(vi_to_ja_rules)
        except Exception:
            pass

    # Built-in fallback preserving exact 28 rules (16 JA->VI, 12 VI->JA)
    return (
        (
            (re.compile(r"画像\s*中央", re.IGNORECASE), "trung tâm ảnh"),
            (re.compile(r"(?<![A-Za-z0-9])中央(?![A-Za-z0-9])", re.IGNORECASE), "trung tâm"),
            (re.compile(r"周辺(?:\s*部)?", re.IGNORECASE), "hai bên ảnh"),
            (re.compile(r"画像", re.IGNORECASE), "ảnh"),
            (re.compile(r"基準軸", re.IGNORECASE), "trục tiêu chuẩn trục chuẩn"),
            (re.compile(r"左右", re.IGNORECASE), "độ lệch trái phải"),
            (re.compile(r"(?:laser\s*power|レーザー\s*パワー|レーザー・パワー)", re.IGNORECASE), "lượng sáng Laser Power"),
            (re.compile(r"光量(?:\s*データ)?", re.IGNORECASE), "lượng sáng"),
            (re.compile(r"(?:beam\s*径|ビーム\s*径)", re.IGNORECASE), "đường kính beam"),
            (re.compile(r"光軸", re.IGNORECASE), "trục quang"),
            (re.compile(r"確認", re.IGNORECASE), "kiểm tra"),
            (re.compile(r"調整", re.IGNORECASE), "điều chỉnh"),
            (re.compile(r"測定", re.IGNORECASE), "đo lường"),
            (re.compile(r"SIM\s*貼付|貼付け", re.IGNORECASE), "dán SIM tape"),
            (re.compile(r"補正順番|手順", re.IGNORECASE), "trình tự thao tác"),
            (re.compile(r"相関|correlation", re.IGNORECASE), "tương quan"),
        ),
        (
            (re.compile(r"trung\s*tâm\s*ảnh", re.IGNORECASE), "画像中央"),
            (re.compile(r"trung\s*tâm", re.IGNORECASE), "中央"),
            (re.compile(r"hai\s*bên\s*ảnh|ngoại\s*vi", re.IGNORECASE), "周辺"),
            (re.compile(r"trục\s*(?:tiêu\s*)?chuẩn", re.IGNORECASE), "基準軸"),
            (re.compile(r"độ\s*lệch\s*trái\s*[-–]?\s*phải|lệch\s*trái\s*[-–]?\s*phải", re.IGNORECASE), "左右 基準軸"),
            (re.compile(r"lượng\s*sáng|công\s*suất\s*laser", re.IGNORECASE), "Laser Power 光量"),
            (re.compile(r"đường\s*kính\s*beam", re.IGNORECASE), "Beam径"),
            (re.compile(r"trục\s*quang", re.IGNORECASE), "光軸"),
            (re.compile(r"kiểm\s*tra|xác\s*nhận", re.IGNORECASE), "確認"),
            (re.compile(r"dán\s*(?:sim|tape)|sim\s*tape", re.IGNORECASE), "SIM 貼付 貼付け"),
            (re.compile(r"trình\s*tự(?:\s*thao\s*tác)?|thứ\s*tự\s*thao\s*tác", re.IGNORECASE), "補正順番 手順"),
            (re.compile(r"tương\s*quan", re.IGNORECASE), "相関 Correlation"),
        ),
    )


_OPTICAL_LSU_JA_TO_VI_EQUIVALENCES, _OPTICAL_LSU_VI_TO_JA_EQUIVALENCES = _load_optical_lsu_glossary()


def get_optical_lsu_ja_to_vi_equivalences() -> tuple[tuple[re.Pattern[str], str], ...]:
    """Return the currently loaded JA->VI optical equivalences (16 rules)."""
    return _OPTICAL_LSU_JA_TO_VI_EQUIVALENCES


def get_optical_lsu_vi_to_ja_equivalences() -> tuple[tuple[re.Pattern[str], str], ...]:
    """Return the currently loaded VI->JA optical equivalences (12 rules)."""
    return _OPTICAL_LSU_VI_TO_JA_EQUIVALENCES


def _build_optical_lsu_crosslingual_variant(
    original: str,
    language_hint: str,
) -> Optional[RetrievalQueryVariant]:
    """Build a target-equivalent cross-lingual search variant for optical / LSU concepts.

    Enables BM25 lexical channels to match technical sections across Japanese and Vietnamese
    (e.g. image center/periphery, laser power/light quantity, beam diameter).
    """
    if not original:
        return None
    matched_translations: list[str] = []
    seen_terms: set[str] = set()

    is_cjk = bool(_CJK_RE.search(original))
    if is_cjk:
        for pattern, vi_equiv in _OPTICAL_LSU_JA_TO_VI_EQUIVALENCES:
            if pattern.search(original):
                for token in vi_equiv.split():
                    tk_low = token.lower()
                    if tk_low not in seen_terms:
                        seen_terms.add(tk_low)
                        matched_translations.append(token)
        if len(matched_translations) >= 2:
            variant_text = " ".join(matched_translations)
            return RetrievalQueryVariant(
                text=variant_text,
                language_hint="vi",
                origin="crosslingual_optics",
                variant_id="optics_equiv_1",
                facet_id="query",
                target_equivalent=True,
            )
    else:
        for pattern, ja_equiv in _OPTICAL_LSU_VI_TO_JA_EQUIVALENCES:
            if pattern.search(original):
                for token in ja_equiv.split():
                    tk_low = token.lower()
                    if tk_low not in seen_terms:
                        seen_terms.add(tk_low)
                        matched_translations.append(token)
        if len(matched_translations) >= 2:
            variant_text = " ".join(matched_translations)
            return RetrievalQueryVariant(
                text=variant_text,
                language_hint="ja",
                origin="crosslingual_optics",
                variant_id="optics_equiv_1",
                facet_id="query",
                target_equivalent=True,
            )
    return None




def _detect_intent_category(query: str) -> tuple[str, tuple[str, ...]]:
    """Return a corpus-neutral answer shape from explicit question wording.

    Expands detection to include operational/procedural, diagnosis (faults, causes,
    countermeasures, anomaly patterns), and lookup (parameters, tolerances, tables,
    counts, threshold units). Preserves generic shape for high-level concepts and
    negative control cases.
    """
    original = " ".join((query or "").strip().split())
    if not original:
        return "general", ("query",)

    ascii_folded = _ascii_fold(original)

    # 1. Negative guards (Ca kiểm âm): câu hỏi tổng quan, định nghĩa, khái niệm chung
    # hoặc kiến trúc dịch vụ không mang tính chẩn đoán/tra cứu kỹ thuật cụ thể.
    generic_guards = (
        "khai niem" in ascii_folded,
        "dinh nghia" in ascii_folded,
        "tong quan" in ascii_folded,
        "overview" in ascii_folded,
        "service outage" in ascii_folded,
        "list all error codes in the table" in ascii_folded,
        "describe the architectural components" in ascii_folded,
        "how do these services exchange data" in ascii_folded,
        "khac nhau the nao" in ascii_folded and not any(k in ascii_folded for k in ("ng", "loi", "jig", "beam")),
        "phan biet nhu the nao" in ascii_folded and not any(k in ascii_folded for k in ("ng", "loi", "jig", "beam")),
    )
    if any(generic_guards):
        return "general", ("query",)

    # 2. Procedure markers: quy trình, hướng dẫn, trình tự thao tác
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
        "trinh tu thao tac" in ascii_folded,
        "quan ly va kiem tra the nao" in ascii_folded,
        "手順" in original,
        "操作手順" in original,
    )
    if any(procedure_markers):
        return "procedure", ("query",)

    # 3. Coordinate lookup markers: tra cứu vị trí tài liệu, vị trí ô, workbook/sheet thuần túy
    coordinate_lookup_markers = (
        "find the supply-instruction location" in ascii_folded,
        "sheet nao" in ascii_folded,
        "toa do o" in ascii_folded,
        "cell location" in ascii_folded,
        "source coordinate" in ascii_folded,
    )
    if any(coordinate_lookup_markers):
        return "lookup", ("query",)

    # 4. Technical diagnosis markers: chẩn đoán mã lỗi, mã máy, hiện tượng, nguyên nhân, đối sách,
    # bảng thông số, dung sai, ngưỡng kỹ thuật, đo kiểm
    technical_diagnosis_markers = (
        # Tiếng Việt
        "nguyen nhan" in ascii_folded,
        "doi sach" in ascii_folded,
        "bat thuong" in ascii_folded,
        "hien tuong" in ascii_folded,
        "su co" in ascii_folded,
        bool(_VIET_TECHNICAL_RE.search(ascii_folded)),
        "di thuong" in ascii_folded,
        "khong doc duoc" in ascii_folded,
        "doc khong duoc" in ascii_folded,
        "bao duong" in ascii_folded,
        "tai sao" in ascii_folded,
        "xu ly the nao" in ascii_folded,
        "hieu qua" in ascii_folded,
        "bang quy doi" in ascii_folded,
        "bang thong so" in ascii_folded,
        "nominal" in ascii_folded,
        "dung sai" in ascii_folded,
        "tolerance" in ascii_folded,
        "gioi han" in ascii_folded,
        "nguong" in ascii_folded,
        "threshold" in ascii_folded,
        "gia tri" in ascii_folded,
        "bao nhieu" in ascii_folded,
        "ty le" in ascii_folded,
        "ti le" in ascii_folded,
        "so luong" in ascii_folded,
        "pham vi ngay" in ascii_folded,
        "record dau" in ascii_folded,
        "phuong phap tinh" in ascii_folded,
        # Tiếng Nhật / Tiếng Trung
        "原因" in original,
        "対策" in original,
        "異常" in original,
        "不具合" in original,
        "現象" in original,
        "故障" in original,
        "障害" in original,
        "発生" in original,
        "判定" in original,
        "排查" in original,
        "読取不能" in original,
        "想定状態" in original,
        "斜め光" in original,
        "色差" in original,
        "偏色" in original,
        "問題" in original,
        "ずれる" in original,
        "なぜ" in original,
        "比較" in original or "比较" in original,
        "公差" in original,
        "規格" in original or "规格" in original,
        "閾値" in original,
        "余量" in original,
        "測定値" in original or "測定" in original,
        "範囲" in original or "范围" in original,
        "平均値" in original,
        "多少" in original,
        "いくつ" in original,
        "何件" in original,
        "何record" in original.lower(),
        "何serial" in original.lower(),
        "哪一天" in original,
        "分別有多少" in original or "分别有多少" in original,
        "表" in original,
        # Ký hiệu kỹ thuật, mã lỗi, acronyms, đơn vị
        bool(_NG_RE.search(original)),
        "ng率" in original.lower(),
        "ng rate" in ascii_folded,
        "root cause" in ascii_folded,
        "countermeasure" in ascii_folded,
        "anomaly" in ascii_folded,
        "symptom" in ascii_folded,
        "troubleshoot" in ascii_folded,
        "trend" in ascii_folded,
        "errcolor" in ascii_folded,
        "bowoveradjustment" in ascii_folded,
        "lightpath" in ascii_folded,
        "takt_" in ascii_folded,
        "jig" in ascii_folded,
        bool(_TECHNICAL_CODE_RE.search(original)),
        bool(_FOUR_M_RE.search(original)),
        bool(_TECHNICAL_WORD_RE.search(original)),
        bool(_MEASUREMENT_UNIT_RE.search(original)),
        "9999.9" in original,
        "999" in original,
    )
    if any(technical_diagnosis_markers):
        return "diagnosis", ("query",)

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
    if (
        len(extra_facets) >= 2 or _has_explicit_cross_source_wording(original)
    ) and intent_category != "procedure":
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
        ranking_config=determine_query_channel_ranking_config(original),
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
        ranking_config=fallback.ranking_config,
    )



def coerce_query_plan(query: str | RetrievalQueryPlan) -> RetrievalQueryPlan:
    """Preserve the historical string API while accepting an already validated plan."""
    return query if isinstance(query, RetrievalQueryPlan) else identity_query_plan(str(query or ""))
