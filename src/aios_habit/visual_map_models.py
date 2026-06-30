from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class VisualMapExportMode(str, Enum):
    LOCAL_FULL = "local_full"
    LOCAL_REDACTED = "local_redacted"
    CLOUD_SAFE_SUMMARY = "cloud_safe_summary"
    NOTEBOOKLM_SAFE = "notebooklm_safe"

@dataclass
class VisualMapNode:
    node_id: str
    node_type: str
    title: str
    short_label: str
    description: str
    source_case_id: str
    evidence_ids: List[str]
    privacy_level: str
    confidence: str
    created_at: str
    updated_at: str
    domain: str
    tags: List[str]
    status: str
    local_only: bool
    display_title: str
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VisualMapEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    reason: str
    evidence_ids: List[str]
    confidence: str
    direction: str
    created_at: str
    privacy_level: str
    local_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VisualKnowledgeGraph:
    nodes: List[VisualMapNode] = field(default_factory=list)
    edges: List[VisualMapEdge] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    export_mode: Optional[str] = None
    privacy_summary: Optional[str] = None
    redaction_summary: Optional[str] = None

@dataclass
class VisualMapValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)

ALLOWED_NODE_TYPES = {
    "case", "source", "evidence", "extracted_fact", "claim", "answer", 
    "decision", "action", "risk", "missing_evidence", "learning_card", 
    "checklist_item", "person_or_role", "system_or_tool", "tag_topic", 
    "domain_playbook"
}

ALLOWED_EDGE_TYPES = {
    "cites", "supports", "contradicts", "derived_from", "requires", 
    "blocks", "follows_up", "similar_to", "caused_by", "mitigates", 
    "assigned_to", "belongs_to", "extracted_from", "answered_by", 
    "has_limitation", "has_missing_evidence", "updates_learning", 
    "uses_domain_playbook"
}

def validate_visual_graph(graph: VisualKnowledgeGraph) -> VisualMapValidationResult:
    errors = []
    node_ids = {n.node_id for n in graph.nodes}
    
    for n in graph.nodes:
        if n.node_type not in ALLOWED_NODE_TYPES:
            errors.append(f"Unknown node type: {n.node_type}")
            
    for e in graph.edges:
        if e.edge_type not in ALLOWED_EDGE_TYPES:
            errors.append(f"Unknown edge type: {e.edge_type}")
        if not e.edge_type:
            errors.append("Untyped edge")
        if not e.reason:
            errors.append(f"Edge {e.edge_id} missing reason")
        if e.from_node_id not in node_ids:
            errors.append(f"Edge from unknown node: {e.from_node_id}")
        if e.to_node_id not in node_ids:
            errors.append(f"Edge to unknown node: {e.to_node_id}")
            
    node_by_id = {n.node_id: n for n in graph.nodes}
    claim_nodes = {n.node_id for n in graph.nodes if n.node_type == "claim"}
    claims_with_edges = set()
    for e in graph.edges:
        if e.edge_type == "supports":
            if e.from_node_id in claim_nodes:
                claims_with_edges.add(e.from_node_id)
            if e.to_node_id in claim_nodes:
                claims_with_edges.add(e.to_node_id)
        elif e.edge_type == "has_missing_evidence" and e.from_node_id in claim_nodes:
            target = node_by_id.get(e.to_node_id)
            if target and target.node_type == "missing_evidence":
                claims_with_edges.add(e.from_node_id)
    for c in claim_nodes:
        if c not in claims_with_edges:
            errors.append(f"Claim node {c} missing supports or has_missing_evidence edge")
            
    evidence_nodes_refs = set()
    for n in graph.nodes:
        if n.node_type == "evidence":
            for ref in n.evidence_ids:
                evidence_nodes_refs.add(ref)

    for n in graph.nodes:
        if n.node_type != "evidence":
            for ref in n.evidence_ids:
                if ref not in evidence_nodes_refs:
                    errors.append(f"Cited evidence ID {ref} not in graph evidence nodes")
                    
    for e in graph.edges:
        for ref in e.evidence_ids:
            if ref not in evidence_nodes_refs:
                errors.append(f"Cited evidence ID {ref} in edge not in graph evidence nodes")

    return VisualMapValidationResult(ok=len(errors) == 0, errors=errors)
