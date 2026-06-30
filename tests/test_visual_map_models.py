import pytest
from aios_habit.visual_map_models import (
    VisualMapNode, VisualMapEdge, VisualKnowledgeGraph, validate_visual_graph
)

def test_creates_case_evidence_action_learning_graph_nodes():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("n1", "case", "c", "c", "c", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "c"))
    g.nodes.append(VisualMapNode("n2", "evidence", "e", "e", "e", "c", ["E-1"], "safe", "high", "t", "t", "d", [], "open", False, "e"))
    g.nodes.append(VisualMapNode("n3", "action", "a", "a", "a", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "a"))
    g.nodes.append(VisualMapNode("n4", "learning_card", "l", "l", "l", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "l"))
    
    g.edges.append(VisualMapEdge("e1", "n1", "n2", "cites", "reason", ["E-1"], "high", "dir", "t", "safe", False))
    
    res = validate_visual_graph(g)
    assert res.ok, res.errors

def test_rejects_unknown_node_type():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("n1", "unknown_type", "t", "t", "t", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "t"))
    res = validate_visual_graph(g)
    assert not res.ok
    assert any("Unknown node type" in e for e in res.errors)

def test_creates_typed_edges_only():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("n1", "case", "c", "c", "c", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "c"))
    g.edges.append(VisualMapEdge("e1", "n1", "n1", "cites", "reason", [], "high", "dir", "t", "safe", False))
    res = validate_visual_graph(g)
    assert res.ok

def test_rejects_unknown_edge_type():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("n1", "case", "c", "c", "c", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "c"))
    g.edges.append(VisualMapEdge("e1", "n1", "n1", "related", "reason", [], "high", "dir", "t", "safe", False))
    res = validate_visual_graph(g)
    assert not res.ok
    assert any("Unknown edge type" in e for e in res.errors)

def test_rejects_edge_without_reason():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("n1", "case", "c", "c", "c", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "c"))
    g.edges.append(VisualMapEdge("e1", "n1", "n1", "cites", "", [], "high", "dir", "t", "safe", False))
    res = validate_visual_graph(g)
    assert not res.ok
    assert any("missing reason" in e for e in res.errors)

def test_every_claim_node_has_evidence_or_missing_evidence_edge():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("n1", "claim", "c", "c", "c", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "c"))
    # Claim without supporting edge
    res = validate_visual_graph(g)
    assert not res.ok
    assert any("missing supports or has_missing_evidence edge" in e for e in res.errors)
    
    g.nodes.append(VisualMapNode("n2", "evidence", "e", "e", "e", "c", ["E-1"], "safe", "high", "t", "t", "d", [], "open", False, "e"))
    g.edges.append(VisualMapEdge("e1", "n1", "n2", "supports", "reason", ["E-1"], "high", "dir", "t", "safe", False))
    res = validate_visual_graph(g)
    assert res.ok
