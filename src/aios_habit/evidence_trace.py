# -*- coding: utf-8 -*-
"""Evidence Trace Module.

Re-exports core classes, dataclasses, and contracts from evidence_trace_schema
and provides high-level builders and citation verification helpers for AIOS WorkLens.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import uuid

from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_1_0_0,
    SCHEMA_VERSION_RAG_TRACE_V1,
    SCHEMA_VERSION_V1,
    SUPPORTED_SCHEMA_VERSIONS,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)
from aios_habit.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, normalize_locale


def extract_cited_evidence_ids(answer_text: str, candidate_ids: Sequence[str]) -> List[str]:
    """Extract citation IDs strictly cited in answer_text matching word boundaries.

    Prevents false positive prefix matches and never fabricates citations.
    """
    if not answer_text or not candidate_ids:
        return []
    cited: List[str] = []
    for cand in candidate_ids:
        cand_str = str(cand).strip()
        if not cand_str:
            continue
        pattern = re.compile(r'(?<![A-Za-z0-9_-])' + re.escape(cand_str) + r'(?![A-Za-z0-9_-])')
        if pattern.search(answer_text):
            if cand_str not in cited:
                cited.append(cand_str)
    return cited


def create_evidence_trace(
    trace_id: Optional[str] = None,
    schema_version: str = SCHEMA_VERSION_RAG_TRACE_V1,
    notebook_id: str = "",
    conversation_id: str = "",
    user_message_id: str = "",
    assistant_message_id: str = "",
    query: str = "",
    answer_text: str = "",
    ui_locale: str = DEFAULT_LOCALE,
    answer_language: str = DEFAULT_LOCALE,
    source_language: str = "auto",
    created_at: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
    nodes: Optional[List[EvidenceNode]] = None,
    edges: Optional[List[EvidenceEdge]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
) -> EvidenceTrace:
    """Factory helper to create a validated EvidenceTrace with consistent defaults."""
    if not trace_id or not trace_id.strip():
        trace_id = f"trc_{uuid.uuid4().hex[:12]}"

    meta = dict(metadata or {})
    if status is not None:
        meta["status"] = status
        if status == "insufficient_evidence":
            meta["insufficient_evidence"] = True

    return EvidenceTrace(
        trace_id=trace_id,
        schema_version=schema_version,
        notebook_id=notebook_id,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        query=query,
        answer_text=answer_text,
        ui_locale=ui_locale,
        answer_language=answer_language,
        source_language=source_language,
        created_at=created_at or datetime.now(timezone.utc).isoformat(),
        provenance=dict(provenance or {}),
        nodes=list(nodes or []),
        edges=list(edges or []),
        metadata=meta,
    )


def build_evidence_trace_from_citations(
    query: str,
    answer_text: str,
    evidence_items: Sequence[Any],
    allowed_source_ids: Optional[Sequence[str]] = None,
    notebook_id: str = "",
    conversation_id: str = "",
    user_message_id: str = "",
    assistant_message_id: str = "",
    ui_locale: str = DEFAULT_LOCALE,
    answer_language: str = DEFAULT_LOCALE,
    source_language: str = "auto",
    provenance: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EvidenceTrace:
    """Build an EvidenceTrace connecting question, answer, and verified evidence nodes.

    Strictly verifies citations:
    - Only sources enabled in allowed_source_ids (if specified) are allowed.
    - Only evidence cited in answer_text is included in the graph.
    - If no valid citations from enabled sources are present, sets status to 'insufficient_evidence'.
    """
    if not trace_id or not trace_id.strip():
        trace_id = f"trc_{uuid.uuid4().hex[:12]}"
    short_id = trace_id.replace("trc_", "")[:8]

    q_node_id = f"q_{short_id}"
    ans_node_id = f"ans_{short_id}"

    q_node = EvidenceNode(
        id=q_node_id,
        node_type="question",
        title=query[:120] if query else "Câu hỏi",
        snippet=query,
        confidence=1.0,
        privacy_label="local_only",
    )
    ans_node = EvidenceNode(
        id=ans_node_id,
        node_type="answer",
        title=f"Câu trả lời ({answer_language})",
        snippet=answer_text[:300] if answer_text else "",
        confidence=1.0,
        privacy_label="local_only",
    )

    nodes: List[EvidenceNode] = [q_node, ans_node]
    edges: List[EvidenceEdge] = [
        EvidenceEdge(
            source_id=ans_node_id,
            target_id=q_node_id,
            relation_type="derives_from",
            label="Trả lời cho câu hỏi",
            weight=1.0,
            edge_id=f"e_{short_id}_ans_q",
        )
    ]

    allowed_set: Optional[Set[str]] = (
        {str(s).strip() for s in allowed_source_ids if str(s).strip()}
        if allowed_source_ids is not None
        else None
    )

    valid_cited_count = 0
    candidate_id_to_item: Dict[str, Tuple[int, Dict[str, Any]]] = {}

    for idx, item in enumerate(evidence_items, start=1):
        if isinstance(item, dict):
            item_id = str(item.get("id") or item.get("source_id") or item.get("evidence_id") or f"src_{idx}")
            title = str(item.get("title") or item.get("source_title") or f"Nguồn {idx}")
            snippet = str(item.get("text") or item.get("snippet") or item.get("content") or item.get("extracted_text") or "")
            source_path = str(item.get("source_path") or item.get("filename") or item.get("source_id") or "")
            citation_label = str(item.get("citation_id") or item.get("citation_label") or item.get("evidence_id") or f"[{idx}]")
            source_id = str(item.get("source_id") or item.get("id") or item.get("evidence_id") or source_path or item_id)
        else:
            item_id = str(getattr(item, "id", None) or getattr(item, "source_id", None) or getattr(item, "evidence_id", None) or f"src_{idx}")
            title = str(getattr(item, "source_title", None) or getattr(item, "title", None) or f"Nguồn {idx}")
            snippet = str(getattr(item, "snippet", None) or getattr(item, "text", None) or getattr(item, "extracted_text", None) or "")
            source_path = str(getattr(item, "source_path", None) or getattr(item, "filename", None) or getattr(item, "relative_path", None) or "")
            citation_label = str(getattr(item, "citation_id", None) or getattr(item, "citation_label", None) or getattr(item, "evidence_id", None) or f"[{idx}]")
            source_id = str(getattr(item, "source_id", None) or getattr(item, "id", None) or getattr(item, "evidence_id", None) or source_path or item_id)

        is_allowed = True
        if allowed_set is not None:
            is_allowed = bool(
                item_id in allowed_set
                or source_id in allowed_set
                or source_path in allowed_set
                or citation_label in allowed_set
                or citation_label.strip("[]") in allowed_set
                or str(idx) in allowed_set
            )

        if not is_allowed:
            continue

        keys_to_match = [
            citation_label,
            f"[{idx}]",
            f"[E{idx}]",
            f"[{citation_label.strip('[]')}]",
            item_id,
            source_id,
        ]
        if citation_label.startswith("[") and citation_label.endswith("]"):
            keys_to_match.append(citation_label.strip("[]"))

        item_dict = {
            "item_id": item_id,
            "source_id": source_id,
            "title": title,
            "snippet": snippet,
            "source_path": source_path,
            "citation_label": citation_label,
            "idx": idx,
        }

        for k in keys_to_match:
            candidate_id_to_item[k] = (idx, item_dict)

    cited_keys = extract_cited_evidence_ids(answer_text, list(candidate_id_to_item.keys()))
    seen_item_indices: Set[int] = set()

    for ck in cited_keys:
        item_idx, item_info = candidate_id_to_item[ck]
        if item_idx in seen_item_indices:
            continue
        seen_item_indices.add(item_idx)

        valid_cited_count += 1
        src_node_id = f"src_{short_id}_{item_idx}"
        cit_node_id = f"cit_{short_id}_{item_idx}"

        src_node = EvidenceNode(
            id=src_node_id,
            node_type="source",
            title=item_info["title"],
            snippet=item_info["snippet"],
            source_id=item_info["source_path"] or item_info["source_id"],
            confidence=0.95,
            citation_id=item_info["citation_label"],
            verification_status="verified",
            privacy_label="local_only",
        )
        cit_node = EvidenceNode(
            id=cit_node_id,
            node_type="citation",
            title=item_info["citation_label"],
            snippet=item_info["snippet"][:200] if item_info["snippet"] else "",
            source_id=src_node_id,
            confidence=1.0,
            citation_id=item_info["citation_label"],
            verification_status="verified",
            privacy_label="local_only",
        )

        nodes.extend([src_node, cit_node])

        edges.append(
            EvidenceEdge(
                source_id=ans_node_id,
                target_id=cit_node_id,
                relation_type="cites",
                label="Dẫn nguồn trích dẫn",
                weight=1.0,
                edge_id=f"e_{short_id}_ans_cit_{item_idx}",
            )
        )
        edges.append(
            EvidenceEdge(
                source_id=cit_node_id,
                target_id=src_node_id,
                relation_type="extracted_from",
                label="Trích từ nguồn tài liệu",
                weight=1.0,
                edge_id=f"e_{short_id}_cit_src_{item_idx}",
            )
        )

    meta = dict(metadata or {})
    if valid_cited_count == 0:
        meta["status"] = "insufficient_evidence"
        meta["insufficient_evidence"] = True
        meta["reason"] = (
            "No valid citations found in answer text from enabled sources"
            if evidence_items
            else "No evidence items provided"
        )
    else:
        meta["status"] = "valid"
        meta["insufficient_evidence"] = False
        meta["cited_count"] = valid_cited_count

    return EvidenceTrace(
        trace_id=trace_id,
        schema_version=SCHEMA_VERSION_RAG_TRACE_V1,
        notebook_id=notebook_id,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        query=query,
        answer_text=answer_text,
        ui_locale=ui_locale,
        answer_language=answer_language,
        source_language=source_language,
        created_at=datetime.now(timezone.utc).isoformat(),
        provenance=dict(provenance or {}),
        nodes=nodes,
        edges=edges,
        metadata=meta,
    )


def is_insufficient_evidence(trace: Optional[EvidenceTrace]) -> bool:
    """Check if an EvidenceTrace represents an insufficient evidence state."""
    if not trace:
        return True
    if trace.metadata.get("status") == "insufficient_evidence":
        return True
    if trace.metadata.get("insufficient_evidence") is True:
        return True
    evidence_nodes = [
        n for n in trace.nodes
        if n.node_type in ("source", "chunk", "evidence", "citation")
    ]
    return len(evidence_nodes) == 0


__all__ = [
    "EvidenceNode",
    "EvidenceEdge",
    "EvidenceTrace",
    "EvidenceTraceContract",
    "SCHEMA_VERSION_1_0_0",
    "SCHEMA_VERSION_V1",
    "SCHEMA_VERSION_RAG_TRACE_V1",
    "SUPPORTED_SCHEMA_VERSIONS",
    "ALLOWED_NODE_TYPES",
    "ALLOWED_EDGE_TYPES",
    "DEFAULT_LOCALE",
    "SUPPORTED_LOCALES",
    "extract_cited_evidence_ids",
    "create_evidence_trace",
    "build_evidence_trace_from_citations",
    "is_insufficient_evidence",
]
