from __future__ import annotations

import sqlite3
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import (
    create_rag_search_schema,
    index_rag_chunks,
    search_rag_chunks,
    RAGSearchFilter,
)

# Constants for guards
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_OVERLAP = 120
MAX_SOURCES = 20
MAX_TOTAL_INDEXED_CHARS = 600 * 1024  # 600 KB
MAX_CHUNKS = 500
DEFAULT_MAX_EVIDENCE_SNIPPETS = 5

def sanitize_citation_title(title: str) -> str:
    """Ensure the title does not expose absolute filesystem paths."""
    if not title:
        return "unnamed-source"
    # If it looks like a Windows or Unix path, get the filename
    title_str = str(title)
    if "\\" in title_str or "/" in title_str:
        return Path(title_str).name
    return title_str

def map_workspace_privacy(label: Optional[str]) -> str:
    """
    Map Workspace Chat privacy label to RAG core privacy mode:
    - machine_only, cloud_allowed, cloud_safe, public, normal -> cloud_safe
    - local_only, blank, None, unknown -> local_only
    """
    if not label:
        return "local_only"
    cleaned = label.strip().lower()
    if cleaned in {"machine_only", "cloud_allowed", "cloud_safe", "public", "normal"}:
        return "cloud_safe"
    return "local_only"

def chunk_source_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> List[str]:
    """Split text into deterministic chunks with overlap."""
    chunks = []
    text_str = (text or "").strip()
    if not text_str:
        return chunks

    start = 0
    text_len = len(text_str)
    while start < text_len:
        end = start + chunk_size
        chunk = text_str[start:end]
        chunks.append(chunk)
        if end >= text_len:
            break
        start += chunk_size - overlap
    return chunks

def retrieve_local_evidence(
    question: str,
    context_sources: Tuple[WorkspaceAIContextSource, ...],
    max_evidence_snippets: int = DEFAULT_MAX_EVIDENCE_SNIPPETS
) -> Dict[str, Any]:
    """
    Perform local FTS retrieval using an in-memory SQLite database.
    Does not call external provider embeddings or services.

    Returns a dictionary of:
    - retrieval_applied (bool)
    - evidence_items (list of dict)
    - retrieved_context_sources (tuple of WorkspaceAIContextSource)
    - summary_count (int)
    - citations (list of dict)
    - safe_owner_message (str)
    - indexed_source_count (int)
    - indexed_chunk_count (int)
    - indexed_char_count (int)
    - truncated_by_guard (bool)
    """
    clean_q = (question or "").strip()

    # Python statistics for testing and verification
    stats = {
        "indexed_source_count": 0,
        "indexed_chunk_count": 0,
        "indexed_char_count": 0,
        "truncated_by_guard": False,
    }

    if not clean_q:
        return {
            "retrieval_applied": False,
            "evidence_items": [],
            "retrieved_context_sources": (),
            "summary_count": 0,
            "citations": [],
            "safe_owner_message": "Câu hỏi không được rỗng.",
            **stats
        }

    # Filter out empty text sources and limit sources
    valid_sources = [s for s in context_sources if (s.text or "").strip()]
    if len(valid_sources) > MAX_SOURCES:
        valid_sources = valid_sources[:MAX_SOURCES]
        stats["truncated_by_guard"] = True

    if not valid_sources:
        return {
            "retrieval_applied": True,
            "evidence_items": [],
            "retrieved_context_sources": (),
            "summary_count": 0,
            "citations": [],
            "safe_owner_message": "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật.",
            **stats
        }

    # Build RAGChunks with character & chunk count guards
    rag_chunks: List[RAGChunk] = []
    total_chars_indexed = 0
    chunk_index = 0
    indexed_sources = set()

    for src in valid_sources:
        if len(rag_chunks) >= MAX_CHUNKS or total_chars_indexed >= MAX_TOTAL_INDEXED_CHARS:
            stats["truncated_by_guard"] = True
            break

        src_text = src.text
        text_chunks = chunk_source_text(src_text)
        safe_title = sanitize_citation_title(src.title)

        source_has_indexed_chunks = False
        for text_chunk in text_chunks:
            if len(rag_chunks) >= MAX_CHUNKS:
                stats["truncated_by_guard"] = True
                break
            chunk_len = len(text_chunk)
            if total_chars_indexed + chunk_len > MAX_TOTAL_INDEXED_CHARS:
                stats["truncated_by_guard"] = True
                # Truncate chunk to fit budget
                remaining = MAX_TOTAL_INDEXED_CHARS - total_chars_indexed
                if remaining <= 0:
                    break
                text_chunk = text_chunk[:remaining]
                chunk_len = len(text_chunk)

            total_chars_indexed += chunk_len
            source_has_indexed_chunks = True

            # Formulate stable deterministic chunk ID
            raw_id_seed = f"{src.source_scope}:{src.source_id}:{chunk_index}:{text_chunk}".encode("utf-8")
            chunk_id = f"CH-{hashlib.md5(raw_id_seed).hexdigest()[:12].upper()}"

            # Map workspace privacy to RAG privacy mode
            rag_privacy = map_workspace_privacy(src.privacy_label)

            rag_chunk = RAGChunk(
                chunk_id=chunk_id,
                document_id=src.source_id,
                element_ids=[f"EL-{chunk_id}"],
                text=text_chunk,
                source_title=safe_title,
                source_path=src.source_id,
                relative_path=safe_title,
                citation_label=safe_title,
                file_type=src.source_type or "txt",
                element_types=["text"],
                page_numbers=[],
                sheet_names=[],
                slide_numbers=[],
                section_labels=[],
                row_ranges=[],
                cell_ranges=[],
                privacy_mode=rag_privacy,
                source_hash=hashlib.sha256(text_chunk.encode("utf-8")).hexdigest(),
                chunk_index=chunk_index,
            )
            rag_chunks.append(rag_chunk)
            chunk_index += 1

        if source_has_indexed_chunks:
            indexed_sources.add(src.source_id)

    stats["indexed_source_count"] = len(indexed_sources)
    stats["indexed_chunk_count"] = len(rag_chunks)
    stats["indexed_char_count"] = total_chars_indexed

    # Safe failure handling for SQLite/FTS database operations
    search_results = []
    try:
        conn = sqlite3.connect(":memory:")
        try:
            create_rag_search_schema(conn)
            index_rag_chunks(conn, rag_chunks)

            # Search chunks using standard project FTS/LIKE parser
            search_results = search_rag_chunks(conn, query=clean_q, limit=max_evidence_snippets)
        finally:
            conn.close()
    except Exception:
        # Fallback to empty results instead of crashing the app
        search_results = []

    # If no results found, return empty results with safe Vietnamese message
    if not search_results:
        return {
            "retrieval_applied": True,
            "evidence_items": [],
            "retrieved_context_sources": (),
            "summary_count": 0,
            "citations": [],
            "safe_owner_message": "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật.",
            **stats
        }

    # Deterministic ordering by score desc, then by chunk_id to ensure 100% stable sequence
    sorted_results = sorted(search_results, key=lambda x: (x.score, x.chunk_id), reverse=True)
    if len(sorted_results) > max_evidence_snippets:
        sorted_results = sorted_results[:max_evidence_snippets]

    # Map search results to evidence items and virtual retrieved_context_sources
    evidence_items = []
    retrieved_sources_list = []
    citations = []

    # Map original sources by ID to easily resolve scope/type/privacy
    original_by_id = {s.source_id: s for s in valid_sources}

    for idx, res in enumerate(sorted_results, 1):
        orig = original_by_id.get(res.document_id)
        if not orig:
            continue

        snippet_text = res.text.strip()
        safe_title = sanitize_citation_title(res.source_title)

        # Formulate citation label/location info safely without exposing paths
        location_info = ""
        if res.page_numbers:
            location_info = f"Trang {', '.join(map(str, res.page_numbers))}"
        elif res.sheet_names:
            location_info = f"Sheet: {', '.join(res.sheet_names)}"
        elif res.slide_numbers:
            location_info = f"Slide {', '.join(map(str, res.slide_numbers))}"

        evidence_item = {
            "snippet_index": idx,
            "source_id": orig.source_id,
            "source_scope": orig.source_scope,
            "source_type": orig.source_type,
            "title": safe_title,
            "text": snippet_text,
            "location_info": location_info,
            "score": res.score,
        }
        evidence_items.append(evidence_item)

        # Form a virtual context source for prompt
        # We append location info to the title to let the AI see context details
        virtual_title = f"{safe_title} ({location_info})" if location_info else safe_title
        retrieved_source = WorkspaceAIContextSource(
            source_id=f"{orig.source_id}_chunk_{idx}",
            source_scope=orig.source_scope,
            source_type=orig.source_type,
            title=virtual_title,
            privacy_label=orig.privacy_label,
            text=snippet_text,
            included_chars=len(snippet_text),
            truncated=False,
        )
        retrieved_sources_list.append(retrieved_source)

        citations.append({
            "title": safe_title,
            "snippet": snippet_text[:150] + "..." if len(snippet_text) > 150 else snippet_text,
            "location": location_info,
        })

    # Count distinct source documents
    distinct_sources = len(set(item["source_id"] for item in evidence_items))
    summary_count = len(evidence_items)

    return {
        "retrieval_applied": True,
        "evidence_items": evidence_items,
        "retrieved_context_sources": tuple(retrieved_sources_list),
        "summary_count": summary_count,
        "citations": citations,
        "safe_owner_message": f"Đã dùng {summary_count} đoạn liên quan từ {distinct_sources} nguồn.",
        **stats
    }
