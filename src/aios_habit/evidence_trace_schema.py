# -*- coding: utf-8 -*-
"""Evidence Trace Contract & Dataclass Schema for AIOS WorkLens.

Defines the standardized schema for capturing structured evidence traces,
claim-evidence relationships, citation anchors, and multilingual metadata.
Guarantees strict UTF-8 serialization and anti-mojibake representation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from aios_habit.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, normalize_locale

SCHEMA_VERSION_1_0_0 = "1.0.0"
SCHEMA_VERSION_V1 = "evidence_trace_v1"
SCHEMA_VERSION_RAG_TRACE_V1 = "rag-trace/v1"
SUPPORTED_SCHEMA_VERSIONS = frozenset({
    SCHEMA_VERSION_1_0_0,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_RAG_TRACE_V1,
})

ALLOWED_NODE_TYPES = frozenset({
    "source",
    "chunk",
    "evidence",
    "claim",
    "citation",
    "answer",
    "question",
    "inference",
    "limitation",
    "action",
    "verification",
    "summary",
})

ALLOWED_EDGE_TYPES = frozenset({
    "cites",
    "supports",
    "contradicts",
    "refutes",
    "derived_from",
    "derives_from",
    "depends_on",
    "verifies",
    "limits",
    "recommends",
    "references",
    "extracted_from",
})


@dataclass
class EvidenceNode:
    """Individual node in the evidence trace graph representing an entity, fact, or claim."""
    id: str
    node_type: str
    title: str = ""
    snippet: str = ""
    source_id: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Convenience aliases and optional properties
    citation_id: Optional[str] = None
    verification_status: Optional[str] = None
    privacy_label: str = "local_only"
    language: Optional[str] = None

    @property
    def node_id(self) -> str:
        """Alias for id."""
        return self.id

    @property
    def label(self) -> str:
        """Alias for title."""
        return self.title

    @property
    def content(self) -> str:
        """Alias for snippet."""
        return self.snippet

    @property
    def source_path(self) -> str:
        """Alias for source_id."""
        return self.source_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to a JSON-serializable dictionary."""
        d: Dict[str, Any] = {
            "id": self.id,
            "node_id": self.id,
            "node_type": self.node_type,
            "title": self.title,
            "label": self.title,
            "snippet": self.snippet,
            "content": self.snippet,
            "source_id": self.source_id,
            "source_path": self.source_id,
            "confidence": float(self.confidence),
            "metadata": dict(self.metadata),
        }
        if self.citation_id is not None:
            d["citation_id"] = self.citation_id
        if self.verification_status is not None:
            d["verification_status"] = self.verification_status
        if self.privacy_label:
            d["privacy_label"] = self.privacy_label
        if self.language is not None:
            d["language"] = self.language
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceNode:
        """Construct EvidenceNode from dictionary, supporting field aliases."""
        node_id = str(data.get("id") or data.get("node_id") or "")
        node_type = str(data.get("node_type", "evidence"))
        title = str(data.get("title") or data.get("label") or "")
        snippet = str(data.get("snippet") or data.get("content") or "")
        source_id = str(data.get("source_id") or data.get("source_path") or "")

        confidence_val = data.get("confidence", 1.0)
        try:
            confidence = float(confidence_val)
        except (ValueError, TypeError):
            confidence = 1.0

        metadata = dict(data.get("metadata") or data.get("properties") or {})
        citation_id = data.get("citation_id")
        verification_status = data.get("verification_status")
        privacy_label = str(data.get("privacy_label", "local_only"))
        language = data.get("language") or data.get("locale")

        return cls(
            id=node_id,
            node_type=node_type,
            title=title,
            snippet=snippet,
            source_id=source_id,
            confidence=confidence,
            metadata=metadata,
            citation_id=citation_id,
            verification_status=verification_status,
            privacy_label=privacy_label,
            language=language,
        )


@dataclass
class EvidenceEdge:
    """Directed edge representing a relationship between two evidence nodes."""
    source_id: str
    target_id: str
    relation_type: str
    label: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    edge_id: Optional[str] = None

    @property
    def relation(self) -> str:
        """Alias for relation_type."""
        return self.relation_type

    @property
    def source_node_id(self) -> str:
        """Alias for source_id."""
        return self.source_id

    @property
    def target_node_id(self) -> str:
        """Alias for target_id."""
        return self.target_id

    @property
    def confidence(self) -> float:
        """Alias for weight."""
        return self.weight

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to a JSON-serializable dictionary."""
        d: Dict[str, Any] = {
            "source_id": self.source_id,
            "source_node_id": self.source_id,
            "target_id": self.target_id,
            "target_node_id": self.target_id,
            "relation_type": self.relation_type,
            "relation": self.relation_type,
            "label": self.label,
            "weight": float(self.weight),
            "confidence": float(self.weight),
            "metadata": dict(self.metadata),
        }
        if self.edge_id:
            d["edge_id"] = self.edge_id
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceEdge:
        """Construct EvidenceEdge from dictionary, supporting field aliases."""
        source_id = str(data.get("source_id") or data.get("source_node_id") or "")
        target_id = str(data.get("target_id") or data.get("target_node_id") or "")
        relation_type = str(data.get("relation_type") or data.get("relation") or "supports")
        label = str(data.get("label", ""))

        weight_val = data.get("weight")
        if weight_val is None:
            weight_val = data.get("confidence", 1.0)
        try:
            weight = float(weight_val)
        except (ValueError, TypeError):
            weight = 1.0

        metadata = dict(data.get("metadata", {}))
        edge_id = data.get("edge_id")

        return cls(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            label=label,
            weight=weight,
            metadata=metadata,
            edge_id=edge_id,
        )


@dataclass
class EvidenceTrace:
    """Complete Evidence Trace structure capturing question, answer, and evidence graph."""
    trace_id: str = ""
    schema_version: str = SCHEMA_VERSION_RAG_TRACE_V1
    notebook_id: str = ""
    conversation_id: str = ""
    user_message_id: str = ""
    assistant_message_id: str = ""
    query: str = ""
    answer_text: str = ""
    ui_locale: str = DEFAULT_LOCALE
    answer_language: str = DEFAULT_LOCALE
    source_language: str = "auto"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: Dict[str, Any] = field(default_factory=dict)
    nodes: List[EvidenceNode] = field(default_factory=list)
    edges: List[EvidenceEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.nodes is None:
            self.nodes = []
        if self.edges is None:
            self.edges = []
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.schema_version:
            self.schema_version = SCHEMA_VERSION_RAG_TRACE_V1
        self.ui_locale = normalize_locale(self.ui_locale or "vi")
        self.answer_language = normalize_locale(self.answer_language or "vi")
        if self.source_language and self.source_language != "auto" and self.source_language not in SUPPORTED_LOCALES:
            self.source_language = normalize_locale(self.source_language)
        if self.provenance and "provenance" not in self.metadata:
            self.metadata["provenance"] = dict(self.provenance)
        elif self.metadata and "provenance" in self.metadata and not self.provenance:
            self.provenance = dict(self.metadata["provenance"]) if isinstance(self.metadata.get("provenance"), dict) else {}

    @property
    def answer(self) -> str:
        """Alias for answer_text."""
        return self.answer_text

    @property
    def question(self) -> str:
        """Alias for query."""
        return self.query

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to a JSON-serializable dictionary."""
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "notebook_id": self.notebook_id,
            "conversation_id": self.conversation_id,
            "user_message_id": self.user_message_id,
            "assistant_message_id": self.assistant_message_id,
            "query": self.query,
            "question": self.query,
            "answer_text": self.answer_text,
            "answer": self.answer_text,
            "ui_locale": self.ui_locale,
            "answer_language": self.answer_language,
            "source_language": self.source_language,
            "created_at": self.created_at,
            "provenance": dict(self.provenance),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": dict(self.metadata),
        }

    def to_json(self, indent: Optional[int] = 2, ensure_ascii: bool = False) -> str:
        """Serialize trace to JSON string with strict UTF-8 preservation."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=ensure_ascii)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceTrace:
        """Construct EvidenceTrace from dictionary."""
        raw_nodes = data.get("nodes") or []
        raw_edges = data.get("edges") or []
        nodes = [EvidenceNode.from_dict(n) if isinstance(n, dict) else n for n in raw_nodes]
        edges = [EvidenceEdge.from_dict(e) if isinstance(e, dict) else e for e in raw_edges]
        return cls(
            trace_id=str(data.get("trace_id") or ""),
            schema_version=str(data.get("schema_version") or SCHEMA_VERSION_RAG_TRACE_V1),
            notebook_id=str(data.get("notebook_id") or ""),
            conversation_id=str(data.get("conversation_id") or ""),
            user_message_id=str(data.get("user_message_id") or ""),
            assistant_message_id=str(data.get("assistant_message_id") or ""),
            query=str(data.get("query") or data.get("question") or ""),
            answer_text=str(data.get("answer_text") or data.get("answer") or ""),
            ui_locale=str(data.get("ui_locale") or DEFAULT_LOCALE),
            answer_language=str(data.get("answer_language") or DEFAULT_LOCALE),
            source_language=str(data.get("source_language") or "auto"),
            created_at=str(data.get("created_at") or ""),
            provenance=dict(data.get("provenance") or {}),
            nodes=nodes,
            edges=edges,
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> EvidenceTrace:
        """Deserialize EvidenceTrace from JSON string."""
        return cls.from_dict(json.loads(json_str))


class EvidenceTraceContract:
    """Contract validator for EvidenceTrace instances."""
    SCHEMA_VERSIONS = SUPPORTED_SCHEMA_VERSIONS
    SUPPORTED_LOCALES = frozenset(SUPPORTED_LOCALES)
    ALLOWED_NODE_TYPES = ALLOWED_NODE_TYPES
    ALLOWED_EDGE_TYPES = ALLOWED_EDGE_TYPES

    @classmethod
    def validate_trace(cls, trace: EvidenceTrace) -> Tuple[bool, List[str]]:
        """Validate trace conformity with the Evidence Trace Contract."""
        errors: List[str] = []

        # Validate schema version
        if not trace.schema_version or not trace.schema_version.strip():
            errors.append("Missing required field: schema_version")
        elif (
            trace.schema_version not in cls.SCHEMA_VERSIONS
            and not (trace.schema_version.startswith("1.") and len(trace.schema_version.split(".")) == 3)
        ):
            errors.append(f"Invalid schema_version: '{trace.schema_version}', supported: {sorted(cls.SCHEMA_VERSIONS)}")

        # Validate locales
        if trace.ui_locale not in cls.SUPPORTED_LOCALES:
            errors.append(f"Invalid ui_locale: '{trace.ui_locale}', supported: {sorted(cls.SUPPORTED_LOCALES)}")

        if trace.answer_language not in cls.SUPPORTED_LOCALES:
            errors.append(f"Invalid answer_language: '{trace.answer_language}', supported: {sorted(cls.SUPPORTED_LOCALES)}")

        # Validate source_language if specified
        if trace.source_language and trace.source_language != "auto" and trace.source_language not in cls.SUPPORTED_LOCALES:
            errors.append(f"Invalid source_language: '{trace.source_language}', supported: {sorted(cls.SUPPORTED_LOCALES)} or 'auto'")

        # Validate created_at timestamp
        if trace.created_at:
            try:
                datetime.fromisoformat(trace.created_at.replace("Z", "+00:00"))
            except Exception:
                errors.append(f"Invalid ISO 8601 created_at format: '{trace.created_at}'")

        # Validate nodes
        node_ids: Set[str] = set()
        for idx, node in enumerate(trace.nodes):
            if not node.id or not str(node.id).strip():
                errors.append(f"Node at index {idx} missing id")
            elif node.id in node_ids:
                errors.append(f"Duplicate node id: '{node.id}'")
            else:
                node_ids.add(node.id)

            if not (0.0 <= node.confidence <= 1.0):
                errors.append(f"Node '{node.id}' confidence {node.confidence} out of range [0.0, 1.0]")

            if not node.node_type or not str(node.node_type).strip():
                errors.append(f"Node '{node.id}' missing node_type")
            elif node.node_type not in cls.ALLOWED_NODE_TYPES:
                errors.append(
                    f"Node '{node.id}' invalid node_type: '{node.node_type}', allowed: {sorted(cls.ALLOWED_NODE_TYPES)}"
                )

        # Validate edges
        edge_ids: Set[str] = set()
        for idx, edge in enumerate(trace.edges):
            if edge.edge_id:
                if edge.edge_id in edge_ids:
                    errors.append(f"Duplicate edge_id: '{edge.edge_id}'")
                else:
                    edge_ids.add(edge.edge_id)

            if not edge.source_id or not str(edge.source_id).strip():
                errors.append(f"Edge at index {idx} missing source_id")
            elif edge.source_id not in node_ids:
                errors.append(f"Edge '{edge.edge_id or idx}' source_id '{edge.source_id}' not found in nodes")

            if not edge.target_id or not str(edge.target_id).strip():
                errors.append(f"Edge at index {idx} missing target_id")
            elif edge.target_id not in node_ids:
                errors.append(f"Edge '{edge.edge_id or idx}' target_id '{edge.target_id}' not found in nodes")

            if not edge.relation_type or not str(edge.relation_type).strip():
                errors.append(f"Edge '{edge.edge_id or idx}' missing relation_type")
            elif edge.relation_type not in cls.ALLOWED_EDGE_TYPES:
                errors.append(
                    f"Edge '{edge.edge_id or idx}' invalid relation_type: '{edge.relation_type}', allowed: {sorted(cls.ALLOWED_EDGE_TYPES)}"
                )

            if not (0.0 <= edge.weight <= 1.0):
                errors.append(f"Edge '{edge.edge_id or idx}' weight {edge.weight} out of range [0.0, 1.0]")

        return len(errors) == 0, errors

    @classmethod
    def validate(cls, trace: EvidenceTrace) -> Tuple[bool, List[str]]:
        """Alias for validate_trace."""
        return cls.validate_trace(trace)
