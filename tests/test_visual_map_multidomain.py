import pytest
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.visual_map_builder import build_active_case_visual_graph

def test_graph_works_for_hr_sample_case():
    case = Case("HR-1", "HR case")
    ev = EvidenceItem("E-1", "HR-1", "note", "policy.pdf", "Title", "Text")
    g = build_active_case_visual_graph(case, [ev], domain_playbook="hr")
    assert any(n.node_type == "domain_playbook" and n.domain == "hr" for n in g.nodes)

def test_graph_works_for_accounting_sample_case():
    case = Case("ACC-1", "Accounting case")
    ev = EvidenceItem("E-1", "ACC-1", "note", "invoice.pdf", "Title", "Text")
    g = build_active_case_visual_graph(case, [ev], domain_playbook="accounting")
    assert any(n.node_type == "domain_playbook" and n.domain == "accounting" for n in g.nodes)

def test_graph_works_for_japanese_learning_sample_case():
    case = Case("JP-1", "JP case")
    ev = EvidenceItem("E-1", "JP-1", "note", "grammar.md", "Title", "Text")
    g = build_active_case_visual_graph(case, [ev], domain_playbook="japanese_learning")
    assert any(n.node_type == "domain_playbook" and n.domain == "japanese_learning" for n in g.nodes)

def test_graph_works_for_it_manual_sample_case():
    case = Case("IT-1", "IT case")
    ev = EvidenceItem("E-1", "IT-1", "note", "manual.md", "Title", "Text")
    g = build_active_case_visual_graph(case, [ev], domain_playbook="it_manual")
    assert any(n.node_type == "domain_playbook" and n.domain == "it_manual" for n in g.nodes)

def test_graph_works_for_manufacturing_sample_without_hardcoded_mom_logic():
    case = Case("MFG-1", "Manufacturing case")
    ev = EvidenceItem("E-1", "MFG-1", "note", "SOP.pdf", "Title", "Text")
    g = build_active_case_visual_graph(case, [ev], domain_playbook="manufacturing")
    assert any(n.node_type == "domain_playbook" and n.domain == "manufacturing" for n in g.nodes)
    
def test_node_click_payload_includes_source_evidence_reference():
    case = Case("C1", "C")
    ev = EvidenceItem("E-1", "C1", "note", "path", "Title", "Text")
    g = build_active_case_visual_graph(case, [ev])
    ev_node = next(n for n in g.nodes if n.node_type == "evidence")
    # In JSON export, the node contains evidence_ids and metadata
    assert "E-1" in ev_node.evidence_ids

def test_edge_click_payload_includes_reason():
    case = Case("C1", "C")
    ev = EvidenceItem("E-1", "C1", "note", "path", "Title", "Text")
    g = build_active_case_visual_graph(case, [ev])
    e = g.edges[0]
    assert e.reason != ""

def test_confidence_and_limitations_are_visible():
    case = Case("C1", "C")
    ans = {"confidence": "medium", "warnings": ["w"]}
    g = build_active_case_visual_graph(case, [], final_answer=ans)
    ans_node = next(n for n in g.nodes if n.node_type == "answer")
    assert ans_node.confidence == "medium"
    risk_node = next(n for n in g.nodes if n.node_type == "risk")
    assert risk_node.title == "w"
