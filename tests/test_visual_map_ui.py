from typing import Any
import pytest
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.visual_map_models import VisualMapNode, VisualMapEdge
from aios_habit.visual_map_builder import build_active_case_visual_graph
from aios_habit.visual_map_export import VisualMapExportMode
from aios_habit.visual_map_ui import (
    build_visual_map_ui_state,
    summarize_visual_map_for_owner,
    filter_visual_map_nodes,
    filter_visual_map_edges,
    get_node_detail_payload,
    get_edge_detail_payload,
    list_missing_evidence_nodes,
    list_risk_claim_nodes,
    list_next_action_nodes,
    list_learning_nodes,
    build_visual_map_export_payload
)

@pytest.fixture
def sample_graph():
    case = Case(case_id="CASE-001", title="Test Case")
    ev1 = EvidenceItem(evidence_id="EV-1", case_id="CASE-001", title="Ev 1", confidence="high", privacy_level="local_only", source_type="note", source_path="local.txt")
    graph = build_active_case_visual_graph(case, [ev1])
    def create_dummy_node(node_id, node_type, title):
        return VisualMapNode(
            node_id=node_id, node_type=node_type, title=title, source_case_id="CASE-001", display_title=title,
            short_label="short", description="desc", evidence_ids=[], privacy_level="safe", confidence="medium",
            created_at="2023-01-01T00:00:00", updated_at="2023-01-01T00:00:00", domain="general", tags=[], status="open", local_only=False
        )
    graph.nodes.append(create_dummy_node("n1", "missing_evidence", "Missing DB Log"))
    graph.nodes.append(create_dummy_node("n2", "risk", "Data Loss Risk"))
    graph.nodes.append(create_dummy_node("n3", "action", "Restart Server"))
    graph.nodes.append(create_dummy_node("n4", "learning_card", "Check logs first"))
    
    graph.edges.append(VisualMapEdge(
        edge_id="e1", from_node_id="node_case_CASE-001", to_node_id="n3", edge_type="has_limitation", reason="Need restart", 
        confidence="medium", privacy_level="safe", evidence_ids=[], direction="directed", created_at="2023-01-01T00:00:00", local_only=False
    ))
    return graph

def test_ui_state_counts(sample_graph):
    state = build_visual_map_ui_state(sample_graph)
    assert state["node_count"] == len(sample_graph.nodes)
    assert state["edge_count"] == len(sample_graph.edges)
    assert state["missing_evidence_count"] == 1
    assert state["risk_claim_count"] == 1

def test_node_filter_by_type(sample_graph):
    filtered = filter_visual_map_nodes(sample_graph, node_type="action")
    assert len(filtered) == 1
    assert filtered[0].node_id == "n3"

def test_node_filter_by_privacy_level(sample_graph):
    filtered = filter_visual_map_nodes(sample_graph, privacy_level="local_only")
    assert any(n.node_id == "node_evidence_EV-1" for n in filtered)

def test_node_filter_by_confidence(sample_graph):
    filtered = filter_visual_map_nodes(sample_graph, min_confidence="high")
    assert any(n.node_id == "node_evidence_EV-1" for n in filtered)

def test_node_search(sample_graph):
    filtered = filter_visual_map_nodes(sample_graph, search_text="Data Loss")
    assert len(filtered) == 1
    assert filtered[0].node_id == "n2"

def test_edge_filter_by_type(sample_graph):
    filtered = filter_visual_map_edges(sample_graph, edge_type="has_limitation")
    assert len(filtered) == 1
    assert filtered[0].edge_id == "e1"

def test_edge_filter_by_privacy_level(sample_graph):
    filtered = filter_visual_map_edges(sample_graph, privacy_level="safe")
    assert len(filtered) == 1
    assert filtered[0].edge_id == "e1"

def test_edge_search(sample_graph):
    filtered = filter_visual_map_edges(sample_graph, search_text="restart")
    assert len(filtered) == 1
    assert filtered[0].edge_id == "e1"

def test_node_detail_payload(sample_graph):
    payload = get_node_detail_payload(sample_graph, "node_evidence_EV-1")
    assert payload["node_id"] == "node_evidence_EV-1"
    assert payload["node_type"] == "evidence"
    assert "Ev 1" in payload["title"]
    assert payload["privacy_level"] == "local_only"

def test_edge_detail_payload(sample_graph):
    payload = get_edge_detail_payload(sample_graph, "e1")
    assert payload["edge_id"] == "e1"
    assert payload["edge_type"] == "has_limitation"
    assert payload["reason"] == "Need restart"
    assert payload["privacy_level"] == "safe"

def test_panels_list_nodes(sample_graph):
    missing = list_missing_evidence_nodes(sample_graph)
    assert len(missing) == 1
    assert missing[0].node_id == "n1"
    
    risks = list_risk_claim_nodes(sample_graph)
    assert len(risks) == 1
    assert risks[0].node_id == "n2"
    
    actions = list_next_action_nodes(sample_graph)
    assert len(actions) == 1
    assert actions[0].node_id == "n3"
    
    learning = list_learning_nodes(sample_graph)
    assert len(learning) == 1
    assert learning[0].node_id == "n4"

def test_owner_summary(sample_graph):
    summary = summarize_visual_map_for_owner(sample_graph)
    assert "Missing DB Log" in summary["Còn thiếu gì trước khi kết luận?"]
    assert "Restart Server" in summary["Việc tiếp theo nên làm là gì?"]
    assert "Check logs first" in summary["Bài học nào có thể dùng lại?"]
    assert "Data Loss Risk" in summary["Rủi ro nếu kết luận vội là gì?"]

def test_export_payloads(sample_graph):
    payload_local = build_visual_map_export_payload(sample_graph, VisualMapExportMode.LOCAL_FULL)
    assert "json" in payload_local
    assert "mermaid" in payload_local
    assert "node_evidence_EV-1" in payload_local["json"]
    
    payload_safe = build_visual_map_export_payload(sample_graph, VisualMapExportMode.CLOUD_SAFE_SUMMARY)
    assert "node_evidence_EV-1" not in payload_safe["json"] # Because EV-1 is local_only
