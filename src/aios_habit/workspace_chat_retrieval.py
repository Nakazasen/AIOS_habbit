from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import (
    create_rag_search_schema,
    index_rag_chunks,
    search_rag_chunks,
)

# Constants for guards
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_OVERLAP = 120
MAX_SOURCES = 20
MAX_TOTAL_INDEXED_CHARS = 600 * 1024  # 600 KB
MAX_CHUNKS = 500
DEFAULT_MAX_EVIDENCE_SNIPPETS = 5
MAX_SNIPPETS_PER_SOURCE = 2
RANKING_STRATEGY = "workspace_lexical_diversity_v2"

# Language-agnostic ranking still benefits from ignoring a small set of common
# function words. These are generic stop words, not corpus-specific vocabulary.
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with",
    "có", "của", "đã", "đang", "được", "gì", "khi", "là", "nào", "như",
    "ở", "thế", "theo", "trong", "từ", "và", "với",
}


def sanitize_citation_title(title: str) -> str:
    """Ensure the title does not expose absolute filesystem paths."""
    if not title:
        return "unnamed-source"
    title_str = str(title)
    if "\\" in title_str or "/" in title_str:
        return Path(title_str).name
    return title_str


def map_workspace_privacy(label: Optional[str]) -> str:
    """Map Workspace Chat privacy labels to the RAG core privacy mode."""
    if not label:
        return "local_only"
    cleaned = label.strip().lower()
    if cleaned in {"machine_only", "cloud_allowed", "cloud_safe", "public", "normal"}:
        return "cloud_safe"
    return "local_only"


def chunk_source_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[str]:
    """Split text into deterministic chunks with overlap."""
    chunks: List[str] = []
    text_str = (text or "").strip()
    if not text_str:
        return chunks

    start = 0
    text_len = len(text_str)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text_str[start:end])
        if end >= text_len:
            break
        start += chunk_size - overlap
    return chunks


def _tokens(value: str) -> Tuple[str, ...]:
    return tuple(
        token
        for token in re.findall(r"[\w]+", (value or "").casefold())
        if len(token) >= 2 and token not in _STOP_WORDS
    )


def _source_key(source: WorkspaceAIContextSource) -> str:
    return f"{source.source_scope or ''}:{source.source_id or ''}"


def _select_sources(
    question: str,
    sources: List[WorkspaceAIContextSource],
) -> List[WorkspaceAIContextSource]:
    """Select sources with generic lexical evidence rather than input order."""
    query_text = question.casefold()
    query_tokens = tuple(dict.fromkeys(_tokens(question)))
    source_documents = {
        _source_key(source): (
            sanitize_citation_title(source.title).casefold(),
            (source.text or "").casefold(),
        )
        for source in sources
    }
    document_frequency = Counter()
    for title, text in source_documents.values():
        for token in query_tokens:
            if token in title or token in text:
                document_frequency[token] += 1

    source_count = max(1, len(sources))
    weights = {
        token: 1.0 + math.log((source_count + 1) / (document_frequency[token] + 1))
        for token in query_tokens
    }
    total_weight = sum(weights.values()) or 1.0
    ranked = []
    for source in sources:
        title, text = source_documents[_source_key(source)]
        title_weight = sum(weight for token, weight in weights.items() if token in title)
        text_weight = sum(weight for token, weight in weights.items() if token in text)
        score = 0.0
        if query_text and query_text in title:
            score += 40.0
        if query_text and query_text in text:
            score += 24.0
        score += 20.0 * title_weight / total_weight
        score += 12.0 * text_weight / total_weight
        ranked.append((score, _source_key(source), source))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [source for _, _, source in ranked[:MAX_SOURCES]]


def _result_relevance(result: Any, question: str, document_count: int) -> float:
    query_text = question.casefold()
    query_tokens = tuple(dict.fromkeys(_tokens(question)))
    title = (result.source_title or "").casefold()
    text = (result.text or "").casefold()
    title_tokens = set(_tokens(title))
    text_tokens = set(_tokens(text))
    matched_title = sum(token in title_tokens for token in query_tokens)
    matched_text = sum(token in text_tokens for token in query_tokens)
    denominator = max(1, len(query_tokens))
    score = float(result.score)
    if query_text and query_text in title:
        score += 18.0
    if query_text and query_text in text:
        score += 12.0
    score += 10.0 * matched_title / denominator
    score += 8.0 * matched_text / denominator
    # A tiny bounded bonus makes broad matches comparable without overwhelming BM25.
    score += min(1.0, math.log1p(max(1, document_count)) / 10.0)
    return score


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _select_diverse_results(
    search_results: List[Any],
    question: str,
    limit: int,
) -> List[Tuple[Any, float]]:
    candidates = [
        {
            "result": result,
            "relevance": _result_relevance(result, question, len(search_results)),
            "tokens": set(_tokens(result.text)),
        }
        for result in search_results
    ]
    selected: List[dict] = []
    source_counts: Counter[str] = Counter()
    while candidates and len(selected) < limit:
        under_cap = [
            candidate
            for candidate in candidates
            if source_counts[candidate["result"].document_id] < MAX_SNIPPETS_PER_SOURCE
        ]
        eligible = under_cap or candidates
        scored = []
        for candidate in eligible:
            duplicate_similarity = max(
                (_jaccard(candidate["tokens"], chosen["tokens"]) for chosen in selected),
                default=0.0,
            )
            source_penalty = 2.5 * source_counts[candidate["result"].document_id]
            diversity_score = candidate["relevance"] - 5.0 * duplicate_similarity - source_penalty
            scored.append((diversity_score, candidate))
        scored.sort(
            key=lambda row: (
                -row[0],
                -row[1]["relevance"],
                row[1]["result"].chunk_id,
            )
        )
        chosen = scored[0][1]
        selected.append(chosen)
        source_counts[chosen["result"].document_id] += 1
        candidates.remove(chosen)
    return [(candidate["result"], candidate["relevance"]) for candidate in selected]


def _base_stats(context_sources: Tuple[WorkspaceAIContextSource, ...]) -> Dict[str, Any]:
    extraction_truncated_count = sum(bool(source.truncated) for source in context_sources)
    return {
        "received_source_count": len(context_sources),
        "eligible_source_count": 0,
        "indexed_source_count": 0,
        "indexed_chunk_count": 0,
        "indexed_char_count": 0,
        "candidate_count": 0,
        "distinct_source_count": 0,
        "per_source_result_counts": {},
        "ranking_strategy": RANKING_STRATEGY,
        "source_extraction_truncated": extraction_truncated_count > 0,
        "source_extraction_truncated_count": extraction_truncated_count,
        "source_selection_truncated": False,
        "chunk_budget_truncated": False,
        "char_budget_truncated": False,
        "truncation_reasons": (["source_extraction_truncated"] if extraction_truncated_count else []),
        "truncated_by_guard": extraction_truncated_count > 0,
        "retrieval_error": "",
    }


def _empty_result(stats: Dict[str, Any], message: str, *, applied: bool = True) -> Dict[str, Any]:
    return {
        "retrieval_applied": applied,
        "evidence_items": [],
        "retrieved_context_sources": (),
        "summary_count": 0,
        "citations": [],
        "safe_owner_message": message,
        **stats,
    }


def retrieve_local_evidence(
    question: str,
    context_sources: Tuple[WorkspaceAIContextSource, ...],
    max_evidence_snippets: int = DEFAULT_MAX_EVIDENCE_SNIPPETS,
) -> Dict[str, Any]:
    """Retrieve local evidence with explicit guard accounting and diversity."""
    clean_q = (question or "").strip()
    stats = _base_stats(context_sources)
    if not clean_q:
        return _empty_result(stats, "Câu hỏi không được rỗng.", applied=False)

    valid_sources = [source for source in context_sources if (source.text or "").strip()]
    stats["eligible_source_count"] = len(valid_sources)
    selected_sources = _select_sources(clean_q, valid_sources)
    if len(valid_sources) > len(selected_sources):
        stats["source_selection_truncated"] = True
        stats["truncation_reasons"].append("source_selection_truncated")
    if not selected_sources:
        stats["truncated_by_guard"] = bool(stats["truncation_reasons"])
        return _empty_result(stats, "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật.")

    chunks_by_source = [
        (source, chunk_source_text(source.text))
        for source in selected_sources
    ]
    available_chunk_count = sum(len(chunks) for _, chunks in chunks_by_source)
    available_char_count = sum(len(chunk) for _, chunks in chunks_by_source for chunk in chunks)
    rag_chunks: List[RAGChunk] = []
    total_chars_indexed = 0
    indexed_sources = set()
    source_chunk_positions = [0] * len(chunks_by_source)

    while len(rag_chunks) < MAX_CHUNKS and total_chars_indexed < MAX_TOTAL_INDEXED_CHARS:
        made_progress = False
        for source_index, (source, text_chunks) in enumerate(chunks_by_source):
            local_chunk_index = source_chunk_positions[source_index]
            if local_chunk_index >= len(text_chunks):
                continue
            made_progress = True
            text_chunk = text_chunks[local_chunk_index]
            source_chunk_positions[source_index] += 1
            remaining = MAX_TOTAL_INDEXED_CHARS - total_chars_indexed
            if remaining <= 0:
                break
            if len(text_chunk) > remaining:
                text_chunk = text_chunk[:remaining]
            chunk_len = len(text_chunk)
            raw_id_seed = (
                f"{source.source_scope}:{source.source_id}:{local_chunk_index}:{text_chunk}"
            ).encode("utf-8")
            chunk_id = f"CH-{hashlib.md5(raw_id_seed).hexdigest()[:12].upper()}"
            safe_title = sanitize_citation_title(source.title)
            rag_chunks.append(RAGChunk(
                chunk_id=chunk_id,
                document_id=_source_key(source),
                element_ids=[f"EL-{chunk_id}"],
                text=text_chunk,
                source_title=safe_title,
                source_path=source.source_id,
                relative_path=safe_title,
                citation_label=safe_title,
                file_type=source.source_type or "txt",
                element_types=["text"],
                page_numbers=[],
                sheet_names=[],
                slide_numbers=[],
                section_labels=[],
                row_ranges=[],
                cell_ranges=[],
                privacy_mode=map_workspace_privacy(source.privacy_label),
                source_hash=hashlib.sha256(text_chunk.encode("utf-8")).hexdigest(),
                chunk_index=local_chunk_index,
            ))
            total_chars_indexed += chunk_len
            indexed_sources.add(_source_key(source))
            if len(rag_chunks) >= MAX_CHUNKS or total_chars_indexed >= MAX_TOTAL_INDEXED_CHARS:
                break
        if not made_progress:
            break

    if available_chunk_count > len(rag_chunks) and len(rag_chunks) >= MAX_CHUNKS:
        stats["chunk_budget_truncated"] = True
        stats["truncation_reasons"].append("chunk_budget_truncated")
    if available_char_count > total_chars_indexed and total_chars_indexed >= MAX_TOTAL_INDEXED_CHARS:
        stats["char_budget_truncated"] = True
        stats["truncation_reasons"].append("char_budget_truncated")
    stats.update({
        "indexed_source_count": len(indexed_sources),
        "indexed_chunk_count": len(rag_chunks),
        "indexed_char_count": total_chars_indexed,
        "truncated_by_guard": bool(stats["truncation_reasons"]),
    })

    search_results: List[Any] = []
    connection: Optional[sqlite3.Connection] = None
    try:
        connection = sqlite3.connect(":memory:")
        create_rag_search_schema(connection)
        index_rag_chunks(connection, rag_chunks)
        candidate_limit = min(MAX_CHUNKS, max(max_evidence_snippets * 8, 40))
        search_results = search_rag_chunks(connection, query=clean_q, limit=candidate_limit)
    except sqlite3.OperationalError:
        stats["retrieval_error"] = "sqlite_operational_error"
    except Exception:
        stats["retrieval_error"] = "retrieval_internal_error"
    finally:
        if connection is not None:
            connection.close()

    stats["candidate_count"] = len(search_results)
    if not search_results:
        return _empty_result(stats, "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật.")

    selected_results = _select_diverse_results(search_results, clean_q, max_evidence_snippets)
    original_by_key = {_source_key(source): source for source in selected_sources}
    evidence_items = []
    retrieved_sources_list = []
    citations = []
    per_source_counts: Counter[str] = Counter()

    for index, (result, rerank_score) in enumerate(selected_results, 1):
        original = original_by_key.get(result.document_id)
        if original is None:
            continue
        snippet_text = result.text.strip()
        safe_title = sanitize_citation_title(result.source_title)
        location_info = ""
        if result.page_numbers:
            location_info = f"Trang {', '.join(map(str, result.page_numbers))}"
        elif result.sheet_names:
            location_info = f"Sheet: {', '.join(result.sheet_names)}"
        elif result.slide_numbers:
            location_info = f"Slide {', '.join(map(str, result.slide_numbers))}"
        evidence_items.append({
            "snippet_index": index,
            "source_id": original.source_id,
            "source_scope": original.source_scope,
            "source_type": original.source_type,
            "title": safe_title,
            "text": snippet_text,
            "location_info": location_info,
            "score": rerank_score,
            "retrieval_score": result.score,
        })
        virtual_title = f"{safe_title} ({location_info})" if location_info else safe_title
        retrieved_sources_list.append(WorkspaceAIContextSource(
            source_id=original.source_id,
            source_scope=original.source_scope,
            source_type=original.source_type,
            title=virtual_title,
            privacy_label=original.privacy_label,
            text=snippet_text,
            included_chars=len(snippet_text),
            truncated=bool(original.truncated),
        ))
        citations.append({
            "title": safe_title,
            "snippet": snippet_text[:150] + "..." if len(snippet_text) > 150 else snippet_text,
            "location": location_info,
        })
        per_source_counts[original.source_id] += 1

    distinct_sources = len(per_source_counts)
    summary_count = len(evidence_items)
    stats["distinct_source_count"] = distinct_sources
    stats["per_source_result_counts"] = dict(sorted(per_source_counts.items()))
    return {
        "retrieval_applied": True,
        "evidence_items": evidence_items,
        "retrieved_context_sources": tuple(retrieved_sources_list),
        "summary_count": summary_count,
        "citations": citations,
        "safe_owner_message": f"Đã dùng {summary_count} đoạn liên quan từ {distinct_sources} nguồn.",
        **stats,
    }
