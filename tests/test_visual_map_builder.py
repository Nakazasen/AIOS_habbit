import pytest
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.learning_models import SeniorLearningCard
from aios_habit.visual_map_builder import build_active_case_visual_graph
from aios_habit.visual_map_models import validate_visual_graph

def test_builder_creates_expected_nodes_and_edges():
    case = Case(case_id="CASE-1", title="Sample", privacy_level="safe")
    ev = EvidenceItem("EVD-1", "CASE-1", "note", "path/to.md", "Title", "Text", privacy_level="safe")
    ans = {"evidence_ids_used": ["EVD-1"], "confidence": "high", "warnings": ["Missing context"], "next_actions": ["Review"]}
    lc = SeniorLearningCard("CASE-1", ["Action"], "Lesson learned", "Check this", [], "high")
    cg = {"ok": False, "reasons": ["Unsafe claim"]}
    
    g = build_active_case_visual_graph(case, [ev], final_answer=ans, learning_cards=[lc], claim_guard_result=cg, domain_playbook="hr")
    
    node_types = {n.node_type for n in g.nodes}
    assert "case" in node_types
    assert "evidence" in node_types
    assert "source" in node_types
    assert "answer" in node_types
    assert "missing_evidence" in node_types
    assert "action" in node_types
    assert "learning_card" in node_types
    assert "domain_playbook" in node_types
    assert "risk" in node_types
    assert "claim" in node_types # claim guard block creates a blocked claim
    
    edge_types = {e.edge_type for e in g.edges}
    assert "extracted_from" in edge_types
    assert "cites" in edge_types
    assert "has_limitation" in edge_types
    assert "follows_up" in edge_types
    assert "updates_learning" in edge_types
    assert "uses_domain_playbook" in edge_types
    assert "blocks" in edge_types

def test_imported_antigravity_strong_answer_creates_answer_cites_edges():
    case = Case(case_id="CASE-1", title="Sample", privacy_level="safe")
    ev = EvidenceItem("EVD-1", "CASE-1", "note", "path.md", "Title", "Text", privacy_level="safe")
    ans = {"cited_evidence_ids": ["EVD-1"], "confidence": "high"}
    
    g = build_active_case_visual_graph(case, [ev], strong_answer=ans)
    
    ans_nodes = [n for n in g.nodes if n.node_type == "answer"]
    assert len(ans_nodes) == 1
    assert ans_nodes[0].metadata.get("source") == "ide_handoff_strong_answer"
    
    cites_edges = [e for e in g.edges if e.edge_type == "cites" and e.from_node_id == ans_nodes[0].node_id]
    assert len(cites_edges) == 1
    assert cites_edges[0].evidence_ids == ["EVD-1"]

def test_missing_evidence_warning_creates_missing_evidence_node():
    case = Case(case_id="CASE-1", title="Sample", privacy_level="safe")
    ans = {"insufficient_evidence": True, "warnings": []}
    g = build_active_case_visual_graph(case, [], final_answer=ans)
    me_nodes = [n for n in g.nodes if n.node_type == "missing_evidence"]
    assert len(me_nodes) == 1
    assert me_nodes[0].title == "Insufficient evidence"

def test_final_owner_answer_warning_creates_has_limitation_edge():
    case = Case(case_id="CASE-1", title="Sample", privacy_level="safe")
    ans = {"warnings": ["Generic warning"]}
    g = build_active_case_visual_graph(case, [], final_answer=ans)
    risk_nodes = [n for n in g.nodes if n.node_type == "risk"]
    assert len(risk_nodes) == 1
    assert risk_nodes[0].title == "Generic warning"
    
    lim_edges = [e for e in g.edges if e.edge_type == "has_limitation"]
    assert len(lim_edges) == 1
    
def test_claim_guard_blocked_claim_becomes_risk_claim_node():
    case = Case(case_id="CASE-1", title="Sample", privacy_level="safe")
    cg = {"ok": False, "reasons": ["Bad claim"]}
    g = build_active_case_visual_graph(case, [], claim_guard_result=cg)
    risk_nodes = [n for n in g.nodes if n.node_type == "risk"]
    claim_nodes = [n for n in g.nodes if n.node_type == "claim"]
    assert len(risk_nodes) == 1
    assert len(claim_nodes) == 1
    blocks_edges = [e for e in g.edges if e.edge_type == "blocks"]
    assert len(blocks_edges) == 1
    missing_edges = [e for e in g.edges if e.edge_type == "has_missing_evidence"]
    assert len(missing_edges) == 1
    res = validate_visual_graph(g)
    assert res.ok, res.errors

def test_duplicate_evidence_nodes_are_collapsed():
    case = Case(case_id="CASE-1", title="Sample", privacy_level="safe")
    ev1 = EvidenceItem("EVD-1", "CASE-1", "note", "path.md", "Title", "Text", privacy_level="safe")
    ev2 = EvidenceItem("EVD-1", "CASE-1", "note", "path.md", "Title", "Text", privacy_level="safe")
    
    g = build_active_case_visual_graph(case, [ev1, ev2])
    ev_nodes = [n for n in g.nodes if n.node_type == "evidence"]
    assert len(ev_nodes) == 1
