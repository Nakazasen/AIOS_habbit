# -*- coding: utf-8 -*-
"""On-Demand Multilingual Evidence Graph Viewer Engine for AIOS WorkLens.

Milestone: Commit C
Key Guarantees:
1. Exact 1-1 Topology: Only nodes and edges present in `rag-trace/v1` trace are rendered.
   Zero hallucinated, synthetic, or fake nodes/edges.
2. Insufficient Evidence Guard: Traces flagged with `insufficient_evidence` display a localized
   warning notice and refuse to draw fake or deceptive graphs.
3. Deterministic SHA-256 Caching: Cached by `(trace_id, content_hash)` over canonical JSON.
4. UTF-8 & Verbatim Preservation: 100% fidelity for source paths, snippets, citation IDs (`[1]`, `[E1]`),
   error codes, and CJK / Vietnamese characters without mojibake or `\\uXXXX` escapes.
5. Pure Local Offline Rendering & Fail-Safe: Zero cloud egress, no external CDNs/fonts,
   catches any rendering exception and displays a friendly localized notice without crashing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import html
import json
import logging
import threading
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from aios_habit.evidence_trace_schema import (
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
)
from aios_habit.evidence_trace import is_insufficient_evidence
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    normalize_locale,
    t,
)

LOGGER = logging.getLogger(__name__)

# Multilingual font stacks ensuring crisp typography across Windows, macOS, Linux, Android
CJK_MULTI_LOCALE_FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, '
    '"Noto Sans", "Noto Sans CJK SC", "Noto Sans CJK JP", "Microsoft YaHei", "Yu Gothic", '
    '"Meiryo", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", sans-serif'
)

CJK_MONOSPACE_FONT_STACK = (
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", '
    '"Noto Sans Mono CJK SC", "Noto Sans Mono CJK JP", monospace'
)


def compute_trace_content_hash(trace_or_dict: Union[EvidenceTrace, Dict[str, Any]]) -> str:
    """Compute deterministic SHA-256 content hash of trace nodes, edges, and metadata.

    Ensures order-independent canonical representation with ensure_ascii=False.
    """
    def _to_node_dict(n: Any) -> Dict[str, Any]:
        if isinstance(n, dict):
            return dict(n)
        if hasattr(n, "to_dict"):
            try:
                res = n.to_dict()
                if isinstance(res, dict):
                    return res
            except Exception:
                pass
        return {"id": str(getattr(n, "id", n)), "title": str(getattr(n, "title", n))}

    def _to_edge_dict(e: Any) -> Dict[str, Any]:
        if isinstance(e, dict):
            return dict(e)
        if hasattr(e, "to_dict"):
            try:
                res = e.to_dict()
                if isinstance(res, dict):
                    return res
            except Exception:
                pass
        return {"source_id": str(getattr(e, "source_id", "")), "target_id": str(getattr(e, "target_id", ""))}

    if isinstance(trace_or_dict, EvidenceTrace):
        nodes_raw = [_to_node_dict(n) for n in (trace_or_dict.nodes or []) if n is not None]
        edges_raw = [_to_edge_dict(e) for e in (trace_or_dict.edges or []) if e is not None]
        metadata_raw = trace_or_dict.metadata or {}
        query_val = trace_or_dict.query or ""
        answer_val = trace_or_dict.answer_text or ""
        schema_ver = trace_or_dict.schema_version or "rag-trace/v1"
        trace_id_val = trace_or_dict.trace_id or ""
    elif isinstance(trace_or_dict, dict):
        nodes_input = trace_or_dict.get("nodes") or []
        edges_input = trace_or_dict.get("edges") or []
        nodes_raw = [_to_node_dict(n) for n in nodes_input if n is not None] if isinstance(nodes_input, list) else []
        edges_raw = [_to_edge_dict(e) for e in edges_input if e is not None] if isinstance(edges_input, list) else []
        metadata_raw = trace_or_dict.get("metadata") or {}
        query_val = trace_or_dict.get("query", "") or trace_or_dict.get("question", "") or ""
        answer_val = trace_or_dict.get("answer_text", "") or trace_or_dict.get("answer", "") or ""
        schema_ver = trace_or_dict.get("schema_version", "rag-trace/v1")
        trace_id_val = trace_or_dict.get("trace_id", "")
    else:
        nodes_raw = []
        edges_raw = []
        metadata_raw = {}
        query_val = ""
        answer_val = ""
        schema_ver = "rag-trace/v1"
        trace_id_val = ""

    # Canonicalize nodes by sorting on 'id'
    canonical_nodes = sorted(
        nodes_raw,
        key=lambda x: str(x.get("id") or x.get("node_id") or ""),
    )

    # Canonicalize edges by sorting on source_id, target_id, relation_type
    canonical_edges = sorted(
        edges_raw,
        key=lambda x: (
            str(x.get("source_id") or x.get("source_node_id") or ""),
            str(x.get("target_id") or x.get("target_node_id") or ""),
            str(x.get("relation_type") or ""),
            str(x.get("edge_id") or ""),
        ),
    )

    # Canonicalize metadata
    canonical_metadata = {
        str(k): v for k, v in sorted(metadata_raw.items(), key=lambda item: str(item[0]))
        if k not in ("cached_at", "render_time")
    }

    canonical_payload: Dict[str, Any] = {
        "trace_id": str(trace_id_val),
        "schema_version": str(schema_ver),
        "query": str(query_val),
        "answer_text": str(answer_val),
        "nodes": canonical_nodes,
        "edges": canonical_edges,
        "metadata": canonical_metadata,
    }

    serialized_bytes = json.dumps(
        canonical_payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(serialized_bytes).hexdigest()


class EvidenceGraphViewerCache:
    """Thread-safe in-memory cache for rendered Evidence Graph view models and HTML artifacts."""

    def __init__(self, max_entries: int = 500) -> None:
        self._lock = threading.Lock()
        self._cache: Dict[Tuple[str, str, str], Any] = {}
        self._max_entries = max_entries

    def _make_key(self, trace_id: str, content_hash: str, locale: str) -> Tuple[str, str, str]:
        return (str(trace_id).strip(), str(content_hash).strip(), normalize_locale(locale))

    def get(self, trace_id: str, content_hash: str, locale: str = DEFAULT_LOCALE) -> Optional[Any]:
        key = self._make_key(trace_id, content_hash, locale)
        with self._lock:
            return self._cache.get(key)

    def set(self, trace_id: str, content_hash: str, value: Any, locale: str = DEFAULT_LOCALE) -> None:
        key = self._make_key(trace_id, content_hash, locale)
        with self._lock:
            if len(self._cache) >= self._max_entries:
                # Evict oldest entry
                oldest_key = next(iter(self._cache))
                self._cache.pop(oldest_key, None)
            self._cache[key] = value

    def has(self, trace_id: str, content_hash: str, locale: str = DEFAULT_LOCALE) -> bool:
        key = self._make_key(trace_id, content_hash, locale)
        with self._lock:
            return key in self._cache

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# Global Viewer Cache Singleton
VIEWER_CACHE = EvidenceGraphViewerCache()


@dataclass
class EvidenceGraphViewModel:
    """Data transfer object containing processed graph elements ready for UI rendering."""
    trace_id: str
    content_hash: str
    locale: str
    is_insufficient: bool
    notice: Optional[str] = None
    notice_desc: Optional[str] = None
    stats: Dict[str, int] = field(default_factory=dict)
    stats_label: str = ""
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "content_hash": self.content_hash,
            "locale": self.locale,
            "is_insufficient": self.is_insufficient,
            "notice": self.notice,
            "notice_desc": self.notice_desc,
            "stats": self.stats,
            "stats_label": self.stats_label,
            "nodes": self.nodes,
            "edges": self.edges,
            "metadata": self.metadata,
            "is_cached": self.is_cached,
        }


def _coerce_to_trace(trace_or_dict: Union[EvidenceTrace, Dict[str, Any]]) -> EvidenceTrace:
    """Coerce input into an EvidenceTrace instance safely."""
    if trace_or_dict is None:
        raise TypeError("Expected EvidenceTrace or dict, got NoneType")
    if isinstance(trace_or_dict, EvidenceTrace):
        if not isinstance(trace_or_dict.nodes, list) or not isinstance(trace_or_dict.edges, list):
            raise TypeError("Trace nodes and edges must be lists")
        return trace_or_dict
    if isinstance(trace_or_dict, dict):
        nodes = trace_or_dict.get("nodes")
        if nodes is not None and not isinstance(nodes, list):
            raise TypeError("nodes must be a list")
        edges = trace_or_dict.get("edges")
        if edges is not None and not isinstance(edges, list):
            raise TypeError("edges must be a list")
        if isinstance(nodes, list):
            for n in nodes:
                if not isinstance(n, (dict, EvidenceNode)):
                    raise TypeError(f"Invalid node type: {type(n)}")
                if isinstance(n, dict):
                    nt = n.get("node_type")
                    if nt is not None and not isinstance(nt, (str, int, float)):
                        raise TypeError(f"node_type must be a string or primitive, got {type(nt)}")
                    nid = n.get("id")
                    if "id" in n and nid is None and not n.get("title"):
                        raise TypeError("Node id cannot be None without title")
        return EvidenceTrace.from_dict(trace_or_dict)
    raise TypeError(f"Expected EvidenceTrace or dict, got {type(trace_or_dict).__name__}")


# Commit C Allowed Node Types: Strictly limited to question, answer, source, citation.
# Non-allowed types (chunk, evidence, claim, inference, limitation, action, verification, summary, custom)
# are filtered out to prevent unwarranted reasoning/extrapolation.
COMMIT_C_ALLOWED_NODE_TYPES = {"question", "answer", "source", "citation"}


def build_evidence_graph_view_model(
    trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
    locale: str = DEFAULT_LOCALE,
) -> EvidenceGraphViewModel:
    """Construct an exact 1-to-1 evidence graph view model.

    Enforces:
    - Insufficient evidence guard: Returns refused graph structure when insufficient.
    - Exact 1-to-1 topology: Only permitted Commit C nodes (question, answer, source, citation) are included.
    - Strict edge filtering: Only edges connecting two valid permitted nodes are kept.
    - Verbatim preservation of snippets, source paths, and citation identifiers.
    """
    loc = normalize_locale(locale)
    trace = _coerce_to_trace(trace_or_dict)
    content_hash = compute_trace_content_hash(trace)

    # Base insufficient evidence check
    if is_insufficient_evidence(trace):
        notice_text = t("evidence_graph_insufficient", locale=loc)
        notice_desc = t("evidence_graph_insufficient_desc", locale=loc)
        return EvidenceGraphViewModel(
            trace_id=trace.trace_id,
            content_hash=content_hash,
            locale=loc,
            is_insufficient=True,
            notice=notice_text,
            notice_desc=notice_desc,
            stats={"nodes": 0, "edges": 0, "sources": 0, "citations": 0},
            stats_label=t("evidence_graph_stats_label", locale=loc, nodes=0, edges=0),
            nodes=[],
            edges=[],
            metadata=dict(trace.metadata or {}),
            is_cached=False,
        )

    # Node styling mappings for permitted Commit C node types
    NODE_TYPE_STYLES: Dict[str, Dict[str, str]] = {
        "question": {
            "icon": "❓",
            "bg": "#0c4a6e",
            "border": "#0284c7",
            "color": "#38bdf8",
            "badge_bg": "rgba(2, 132, 199, 0.2)",
        },
        "answer": {
            "icon": "💡",
            "bg": "#064e3b",
            "border": "#059669",
            "color": "#34d399",
            "badge_bg": "rgba(5, 150, 105, 0.2)",
        },
        "citation": {
            "icon": "🏷️",
            "bg": "#78350f",
            "border": "#d97706",
            "color": "#fbbf24",
            "badge_bg": "rgba(217, 119, 6, 0.2)",
        },
        "source": {
            "icon": "📄",
            "bg": "#4c1d95",
            "border": "#7c3aed",
            "color": "#a78bfa",
            "badge_bg": "rgba(124, 58, 237, 0.2)",
        },
    }
    DEFAULT_STYLE: Dict[str, str] = {
        "icon": "🔹",
        "bg": "#1e293b",
        "border": "#64748b",
        "color": "#cbd5e1",
        "badge_bg": "rgba(100, 116, 139, 0.2)",
    }

    # Filter nodes strictly to COMMIT_C_ALLOWED_NODE_TYPES
    raw_nodes = trace.nodes or []
    filtered_nodes = [
        node for node in raw_nodes
        if str(getattr(node, "node_type", "") or "").lower() in COMMIT_C_ALLOWED_NODE_TYPES
    ]

    source_count = sum(1 for n in filtered_nodes if str(getattr(n, "node_type", "")).lower() == "source")
    citation_count = sum(1 for n in filtered_nodes if str(getattr(n, "node_type", "")).lower() == "citation")

    # If after filtering, either valid source or citation nodes are missing -> insufficient evidence
    if source_count == 0 or citation_count == 0:
        notice_text = t("evidence_graph_insufficient", locale=loc)
        notice_desc = t("evidence_graph_insufficient_desc", locale=loc)
        return EvidenceGraphViewModel(
            trace_id=trace.trace_id,
            content_hash=content_hash,
            locale=loc,
            is_insufficient=True,
            notice=notice_text,
            notice_desc=notice_desc,
            stats={"nodes": 0, "edges": 0, "sources": 0, "citations": 0},
            stats_label=t("evidence_graph_stats_label", locale=loc, nodes=0, edges=0),
            nodes=[],
            edges=[],
            metadata=dict(trace.metadata or {}),
            is_cached=False,
        )

    valid_node_ids = {str(n.id) for n in filtered_nodes}
    view_nodes: List[Dict[str, Any]] = []

    for node in filtered_nodes:
        ntype = str(node.node_type or "other").lower()
        style = NODE_TYPE_STYLES.get(ntype, DEFAULT_STYLE)
        type_trans_key = f"node_type_{ntype}"
        type_display = t(type_trans_key, locale=loc)
        if type_display == type_trans_key:
            type_display = ntype.capitalize()

        # Verbatim field preservation
        node_dict: Dict[str, Any] = {
            "id": node.id,
            "node_type": ntype,
            "type_label": type_display,
            "title": node.title or node.id,
            "snippet": node.snippet or "",
            "source_id": node.source_id or "",
            "citation_id": node.citation_id or "",
            "confidence": float(node.confidence) if node.confidence is not None else None,
            "verification_status": node.verification_status or "verified",
            "privacy_label": node.privacy_label or "local_only",
            "language": node.language or loc,
            "metadata": dict(node.metadata or {}),
            "style": style,
        }
        view_nodes.append(node_dict)

    # Filter edges: only include edges where BOTH source_id and target_id are in valid_node_ids
    view_edges: List[Dict[str, Any]] = []
    for edge in (trace.edges or []):
        src_id_str = str(edge.source_id)
        tgt_id_str = str(edge.target_id)
        if src_id_str not in valid_node_ids or tgt_id_str not in valid_node_ids:
            continue

        rtype = str(edge.relation_type or "references").lower()
        edge_trans_key = f"edge_{rtype}"
        edge_display = t(edge_trans_key, locale=loc)
        if edge_display == edge_trans_key:
            rel_trans_key = f"rel_{rtype}"
            edge_display = t(rel_trans_key, locale=loc)
            if edge_display == rel_trans_key:
                edge_display = edge.label or rtype.replace("_", " ")

        edge_dict: Dict[str, Any] = {
            "edge_id": edge.edge_id or f"e_{src_id_str}_{tgt_id_str}",
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relation_type": rtype,
            "relation": rtype,
            "label": edge.label or edge_display,
            "display_label": edge_display,
            "weight": float(edge.weight) if edge.weight is not None else 1.0,
            "metadata": dict(edge.metadata or {}),
        }
        view_edges.append(edge_dict)

    stats = {
        "nodes": len(view_nodes),
        "edges": len(view_edges),
        "sources": source_count,
        "citations": citation_count,
    }

    stats_label = t(
        "evidence_graph_stats_label",
        locale=loc,
        nodes=len(view_nodes),
        edges=len(view_edges),
    )

    return EvidenceGraphViewModel(
        trace_id=trace.trace_id,
        content_hash=content_hash,
        locale=loc,
        is_insufficient=False,
        notice=None,
        notice_desc=None,
        stats=stats,
        stats_label=stats_label,
        nodes=view_nodes,
        edges=view_edges,
        metadata=dict(trace.metadata or {}),
        is_cached=False,
    )


def _esc(val: Any) -> str:
    """Escape text safely for HTML insertion without double escaping."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)


def _render_node_card(n: Dict[str, Any]) -> str:
    style = n["style"]
    cid_badge = ""
    if n.get("citation_id"):
        cid_badge = f'<span style="background:{style["badge_bg"]}; color:{style["color"]}; border:1px solid {style["border"]}; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700; margin-left:6px;">{_esc(n["citation_id"])}</span>'

    conf_badge = ""
    if n.get("confidence") is not None:
        conf_val = int(round(float(n["confidence"]) * 100))
        conf_badge = f'<span style="color:#94a3b8; font-size:11px; margin-left:auto;">{conf_val}%</span>'

    snippet_html = ""
    if n.get("snippet"):
        snippet_html = f'<div style="margin-top:8px; font-size:12px; color:#cbd5e1; line-height:1.5; max-height:120px; overflow-y:auto; word-break:break-word; background:rgba(0,0,0,0.25); padding:6px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.06); font-family:inherit;">{_esc(n["snippet"])}</div>'

    source_id_html = ""
    if n.get("source_id"):
        source_id_html = f'<div style="margin-top:6px; font-size:11px; color:#a78bfa; word-break:break-all;">📁 {_esc(n["source_id"])}</div>'

    return f"""
<div class="egv-node-card" style="background:{style["bg"]}; border:1px solid {style["border"]}; border-radius:8px; padding:12px 14px; margin-bottom:12px; box-shadow:0 4px 12px rgba(0,0,0,0.3); transition:transform 0.15s ease;">
    <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:16px;">{style["icon"]}</span>
        <span style="font-size:13px; font-weight:700; color:{style["color"]};">{_esc(n["type_label"])}</span>
        {cid_badge}
        {conf_badge}
    </div>
    <div style="margin-top:6px; font-size:13px; font-weight:600; color:#f8fafc; word-break:break-word; line-height:1.4;">
        {_esc(n["title"])}
    </div>
    {source_id_html}
    {snippet_html}
</div>
"""


def _render_graph_container(
    trace: EvidenceTrace,
    content_hash: str,
    view_model: EvidenceGraphViewModel,
    loc: str,
    is_cached: bool = False,
) -> str:
    question_nodes = [n for n in view_model.nodes if n["node_type"] == "question"]
    answer_nodes = [n for n in view_model.nodes if n["node_type"] == "answer"]
    citation_nodes = [n for n in view_model.nodes if n["node_type"] == "citation"]
    source_nodes = [n for n in view_model.nodes if n["node_type"] == "source"]

    edge_items_html = []
    for e in view_model.edges:
        edge_items_html.append(f"""
<div style="display:inline-flex; align-items:center; gap:6px; background:rgba(30,41,59,0.8); border:1px solid #475569; border-radius:9999px; padding:4px 12px; margin:4px 6px; font-size:11px; color:#cbd5e1;">
    <span style="color:#94a3b8; font-family:monospace;">{_esc(e["source_id"])}</span>
    <span style="color:#38bdf8; font-weight:600;">──({_esc(e["label"])})─▶</span>
    <span style="color:#94a3b8; font-family:monospace;">{_esc(e["target_id"])}</span>
</div>
""")
    edges_summary_html = "".join(edge_items_html) if edge_items_html else '<span style="color:#64748b; font-size:12px;">(0 edges)</span>'

    q_cards = "".join(_render_node_card(n) for n in question_nodes) or '<div style="color:#64748b; font-size:12px;">--</div>'
    a_cards = "".join(_render_node_card(n) for n in answer_nodes) or '<div style="color:#64748b; font-size:12px;">--</div>'
    c_cards = "".join(_render_node_card(n) for n in citation_nodes) or '<div style="color:#64748b; font-size:12px;">(0 citations)</div>'
    s_cards = "".join(_render_node_card(n) for n in source_nodes) or '<div style="color:#64748b; font-size:12px;">(0 sources)</div>'

    cached_badge_html = ""
    if is_cached:
        cached_badge_html = f'<span class="egv-cached-badge" style="color:#10b981; font-size:11px; font-weight:600; background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:9999px;">{_esc(t("evidence_graph_cached_badge", locale=loc))}</span>'

    return f"""
<div class="egv-container egv-full" data-trace-id="{_esc(trace.trace_id)}" style="background:#0f172a; border:1px solid #334155; border-radius:12px; padding:16px 20px; color:#f8fafc; font-family:{CJK_MULTI_LOCALE_FONT_STACK}; margin:10px 0; box-shadow:0 8px 24px rgba(0,0,0,0.4);">
    <!-- Header -->
    <div style="display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #334155; padding-bottom:12px; margin-bottom:16px; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; align-items:center; gap:10px;">
            <span style="font-size:20px;">🕸️</span>
            <div>
                <div style="font-size:15px; font-weight:700; color:#f8fafc;">{_esc(t("evidence_graph_title", locale=loc))}</div>
                <div style="font-size:11px; color:#94a3b8; font-family:monospace;">ID: {_esc(trace.trace_id)} · SHA-256: {_esc(content_hash[:12])}...</div>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.3); padding:2px 10px; border-radius:9999px; font-size:12px; font-weight:600;">
                {_esc(view_model.stats_label)}
            </span>
            {cached_badge_html}
        </div>
    </div>

    <!-- Multi-Column Board Flow -->
    <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:16px;">
        <!-- Column 1: Question & Answer -->
        <div style="flex:1.2; min-width:280px;">
            <div style="font-size:12px; font-weight:700; color:#38bdf8; text-transform:uppercase; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                <span>💬</span>
                <span>{_esc(t("node_type_question", locale=loc))} & {_esc(t("node_type_answer", locale=loc))}</span>
            </div>
            {q_cards}
            {a_cards}
        </div>

        <!-- Column 2: Citations -->
        <div style="flex:1; min-width:260px;">
            <div style="font-size:12px; font-weight:700; color:#fbbf24; text-transform:uppercase; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                <span>🏷️</span>
                <span>{_esc(t("citations", locale=loc))} ({len(citation_nodes)})</span>
            </div>
            {c_cards}
        </div>

        <!-- Column 3: Source Documents -->
        <div style="flex:1.2; min-width:280px;">
            <div style="font-size:12px; font-weight:700; color:#a78bfa; text-transform:uppercase; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                <span>📁</span>
                <span>{_esc(t("evidence_graph_source_nodes", locale=loc))} ({len(source_nodes)})</span>
            </div>
            {s_cards}
        </div>
    </div>

    <!-- Edges & Relations Footer -->
    <div style="background:#1e293b; border-radius:8px; padding:10px 14px; border:1px solid #334155;">
        <div style="font-size:11px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
            <span>🔗</span>
            <span>{_esc(t("edges", locale=loc))} ({len(view_model.edges)})</span>
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:4px;">
            {edges_summary_html}
        </div>
    </div>
</div>
"""


def render_evidence_graph_html(
    trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
    locale: str = DEFAULT_LOCALE,
    use_cache: bool = True,
) -> str:
    """Render a pure local, offline-safe, responsive HTML visualization board of the evidence graph.

    Fail-Safe: Catches any rendering exception and returns a localized friendly error banner.
    Zero Cloud Egress: All styles and layouts are embedded inline. No external CDNs or network calls.
    Cache Honesty: Only displays the cached badge when retrieved from VIEWER_CACHE on a cache hit.
    """
    loc = normalize_locale(locale)

    try:
        trace = _coerce_to_trace(trace_or_dict)
        content_hash = compute_trace_content_hash(trace)

        if use_cache:
            cached_html = VIEWER_CACHE.get(trace.trace_id, content_hash, locale=loc)
            if cached_html is not None:
                return cached_html

        view_model = build_evidence_graph_view_model(trace, locale=loc)

        if view_model.is_insufficient:
            insufficient_html_fresh = f"""
<div class="egv-container egv-insufficient" data-trace-id="{_esc(trace.trace_id)}" style="background:#1e1b18; border:1px solid #78350f; border-radius:10px; padding:18px 22px; color:#fde68a; font-family:{CJK_MULTI_LOCALE_FONT_STACK}; margin:10px 0;">
    <!-- trace_id: {_esc(trace.trace_id)} -->
    <div style="display:flex; align-items:center; gap:10px; font-size:15px; font-weight:600; color:#fbbf24;">
        <span>⚠️</span>
        <span>{_esc(view_model.notice)}</span>
    </div>
    <div style="margin-top:8px; font-size:13px; color:#d4d4d8; line-height:1.5;">
        {_esc(view_model.notice_desc)}
    </div>
</div>
"""
            insufficient_html_cached = f"""
<div class="egv-container egv-insufficient" data-trace-id="{_esc(trace.trace_id)}" style="background:#1e1b18; border:1px solid #78350f; border-radius:10px; padding:18px 22px; color:#fde68a; font-family:{CJK_MULTI_LOCALE_FONT_STACK}; margin:10px 0;">
    <!-- trace_id: {_esc(trace.trace_id)} -->
    <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; align-items:center; gap:10px; font-size:15px; font-weight:600; color:#fbbf24;">
            <span>⚠️</span>
            <span>{_esc(view_model.notice)}</span>
        </div>
        <span class="egv-cached-badge" style="color:#10b981; font-size:11px; font-weight:600; background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:9999px;">{_esc(t("evidence_graph_cached_badge", locale=loc))}</span>
    </div>
    <div style="margin-top:8px; font-size:13px; color:#d4d4d8; line-height:1.5;">
        {_esc(view_model.notice_desc)}
    </div>
</div>
"""
            if use_cache:
                VIEWER_CACHE.set(trace.trace_id, content_hash, insufficient_html_cached, locale=loc)
            return insufficient_html_fresh

        full_html_fresh = _render_graph_container(trace, content_hash, view_model, loc, is_cached=False)
        full_html_cached = _render_graph_container(trace, content_hash, view_model, loc, is_cached=True)

        if use_cache:
            VIEWER_CACHE.set(trace.trace_id, content_hash, full_html_cached, locale=loc)

        return full_html_fresh

    except Exception as exc:
        LOGGER.exception("Failed to render evidence graph HTML for trace: %s", exc)
        error_msg = t("evidence_graph_render_error", locale=loc)
        return f"""
<div class="egv-container egv-error" style="background:#261313; border:1px solid #991b1b; border-radius:10px; padding:16px 20px; color:#fca5a5; font-family:{CJK_MULTI_LOCALE_FONT_STACK}; margin:10px 0;">
    <div style="display:flex; align-items:center; gap:8px; font-size:14px; font-weight:600; color:#ef4444;">
        <span>❌</span>
        <span>{_esc(error_msg)}</span>
    </div>
</div>
"""


def _wrap_evidence_graph_for_component(graph_html: str) -> str:
    """Put the graph fragment in an isolated, responsive HTML document.

    Streamlit's Markdown renderer is intentionally permissive but is not a
    reliable host for a complex, nested visualisation.  A component iframe
    keeps graph markup from leaking into the chat as literal ``<div>`` text
    and prevents graph CSS from changing the surrounding conversation.
    """
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html, body {{ margin:0; padding:0; width:100%; background:#0b1220; overflow-x:hidden; }}
body {{ font-family:{CJK_MULTI_LOCALE_FONT_STACK}; }}
.egv-container {{ box-sizing:border-box; min-width:0 !important; margin:0 !important; border-radius:0 !important; }}
.egv-node-card {{ min-width:0; }}
@media (max-width: 720px) {{
  .egv-container {{ padding:14px !important; }}
  .egv-full > div {{ min-width:0 !important; width:100%; }}
}}
</style>
</head>
<body>{graph_html}</body>
</html>"""


def _evidence_graph_component_height(view_model: EvidenceGraphViewModel) -> int:
    """Choose a usable iframe height without making ordinary chats enormous."""
    column_sizes = (
        sum(1 for node in view_model.nodes if node["node_type"] in {"question", "answer"}),
        sum(1 for node in view_model.nodes if node["node_type"] == "citation"),
        sum(1 for node in view_model.nodes if node["node_type"] == "source"),
    )
    tallest_column = max(column_sizes, default=1)
    return min(960, max(520, 260 + (tallest_column * 140)))


def render_evidence_graph_streamlit(
    trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
    locale: str = DEFAULT_LOCALE,
) -> None:
    """Render the Evidence Graph Viewer component in Streamlit.

    Renders one readable, responsive graph in an isolated component.

    The detailed ExcaliFlow Atlas is an explicit secondary action. It is not
    embedded by default because its fixed wide canvas makes the normal chat
    view hard to read and forces horizontal scrolling.
    """
    loc = normalize_locale(locale)

    try:
        import streamlit as st  # type: ignore
    except ImportError:
        LOGGER.warning("Streamlit not available in runtime environment")
        return

    try:
        trace = _coerce_to_trace(trace_or_dict)
        content_hash = compute_trace_content_hash(trace)

        view_model = build_evidence_graph_view_model(trace, locale=loc)
        if view_model.is_insufficient:
            st.warning(f"⚠️ {t('evidence_graph_insufficient', locale=loc)}")
            st.caption(t("evidence_graph_insufficient_desc", locale=loc))
            return

        graph_html = render_evidence_graph_html(trace, locale=loc, use_cache=True)
        component_html = _wrap_evidence_graph_for_component(graph_html)
        import streamlit.components.v1 as components  # type: ignore
        components.html(
            component_html,
            height=_evidence_graph_component_height(view_model),
            scrolling=True,
        )

        atlas_state_key = f"wsc_show_evidence_atlas_{trace.trace_id}_{content_hash[:12]}"
        atlas_open = bool(st.session_state.get(atlas_state_key, False))
        if not atlas_open:
            if st.button(
                t("btn_open_evidence_atlas", locale=loc),
                key=f"btn_open_evidence_atlas_{trace.trace_id}",
            ):
                st.session_state[atlas_state_key] = True
                atlas_open = True

        if atlas_open:
            st.caption(t("evidence_atlas_details_hint", locale=loc))
            try:
                from aios_habit.excaliflow_adapter import ExcaliFlowAdapter

                adapter = ExcaliFlowAdapter()
                if not adapter.is_available():
                    raise RuntimeError("evidence_atlas_unavailable")
                atlas_html = adapter.render_evidence_atlas_html(trace, locale=loc)
                components.html(atlas_html, height=820, scrolling=True)
            except Exception as exc:
                LOGGER.exception("Atlas renderer error: %s", exc)
                st.error(f"❌ {t('evidence_graph_render_error', locale=loc)}")

    except Exception as exc:
        LOGGER.exception("Failed in render_evidence_graph_streamlit: %s", exc)
        try:
            import streamlit as st  # type: ignore
            st.error(f"❌ {t('evidence_graph_render_error', locale=loc)}")
        except Exception:
            pass


__all__ = [
    "CJK_MULTI_LOCALE_FONT_STACK",
    "CJK_MONOSPACE_FONT_STACK",
    "compute_trace_content_hash",
    "EvidenceGraphViewerCache",
    "VIEWER_CACHE",
    "EvidenceGraphViewModel",
    "build_evidence_graph_view_model",
    "render_evidence_graph_html",
    "render_evidence_graph_streamlit",
]
