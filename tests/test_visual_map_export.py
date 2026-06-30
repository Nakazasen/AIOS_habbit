import pytest
import json
from aios_habit.visual_map_models import (
    VisualMapNode, VisualMapEdge, VisualKnowledgeGraph, VisualMapExportMode, validate_visual_graph
)
from aios_habit.visual_map_export import (
    redact_visual_graph, export_visual_graph_json, export_visual_graph_mermaid
)

def build_test_graph():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("n1", "case", "Bui " + "Duc " + "Vinh case", "c", "NotebookLM " + "replacement", "c", [], "local_only", "high", "t", "t", "d", [], "open", True, "Bui " + "Duc " + "Vinh case"))
    g.nodes.append(VisualMapNode("n2", "source", "C:\\" + "Users\\file.txt", "s", "VN" + "1234", "c", [], "local_only", "high", "t", "t", "d", [], "open", True, "C:\\" + "Users\\file.txt"))
    g.nodes.append(VisualMapNode("n3", "action", "Action", "a", "P1.0 " + "is open", "c", [], "safe", "high", "t", "t", "d", [], "open", False, "Action"))
    g.edges.append(VisualMapEdge("e1", "n1", "n2", "cites", "reason", [], "high", "dir", "t", "local_only", True))
    g.edges.append(VisualMapEdge("e2", "n3", "n1", "follows_up", "Bui " + "Duc " + "Vinh", [], "high", "dir", "t", "local_only", True))
    return g

def test_local_only_evidence_is_blocked_from_cloud_safe_summary():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.CLOUD_SAFE_SUMMARY)
    assert len(safe_g.nodes) == 1
    assert safe_g.nodes[0].node_id == "n3"
    assert len(safe_g.edges) == 0

def test_local_only_evidence_is_blocked_from_notebooklm_safe():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.NOTEBOOKLM_SAFE)
    assert len(safe_g.nodes) == 1
    assert safe_g.nodes[0].node_id == "n3"

def test_personal_names_are_redacted_in_safe_export():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.LOCAL_REDACTED)
    assert "Bui " + "Duc " + "Vinh" not in safe_g.nodes[0].title
    assert "[PERSON_REDACTED]" in safe_g.nodes[0].title

def test_employee_ids_are_redacted_in_safe_export():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.LOCAL_REDACTED)
    assert "[EMPLOYEE_ID_REDACTED]" in safe_g.nodes[1].description

def test_absolute_local_paths_are_redacted_in_safe_export():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.LOCAL_REDACTED)
    assert "[LOCAL_SOURCE]" in safe_g.nodes[1].title
    assert "C:\\" + "Users" not in safe_g.nodes[1].title

def test_source_basename_is_safe_in_local_redacted():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.LOCAL_REDACTED)
    assert safe_g.nodes[1].display_title == "[LOCAL_SOURCE]"

def test_no_notebooklm_replacement_claim_appears():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.NOTEBOOKLM_SAFE)
    assert "NotebookLM parity claimed: NO" in safe_g.warnings[0]
    for n in safe_g.nodes:
        assert "replacement" not in n.description.lower() or "[REDACTED]" in n.description

def test_no_p1_0_claim_appears():
    g = build_test_graph()
    safe_g = redact_visual_graph(g, VisualMapExportMode.NOTEBOOKLM_SAFE)
    assert "P1.0 " + "is open" not in safe_g.nodes[0].description
    assert "[REDACTED]" in safe_g.nodes[0].description

def test_safe_mermaid_export_contains_no_unsafe_path_personal_data():
    g = build_test_graph()
    m = export_visual_graph_mermaid(g, VisualMapExportMode.LOCAL_REDACTED)
    assert "Bui " + "Duc " + "Vinh" not in m
    assert "C:\\" + "Users" not in m
    assert "[LOCAL_SOURCE]" in m

def test_safe_export_redacts_unsafe_node_ids_and_hostnames():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("node_C:\\" + "Users\\Admin\\secret.txt", "source", "kmcn" + ".local", "s", "host kdtvn" + ".local", "c", [], "local_only", "high", "t", "t", "d", [], "open", True, "C:\\" + "Users\\Admin\\secret.txt"))
    safe_g = redact_visual_graph(g, VisualMapExportMode.LOCAL_REDACTED)
    assert "C:\\" + "Users" not in safe_g.nodes[0].node_id
    assert "kmcn" + ".local" not in safe_g.nodes[0].title
    assert "kdtvn" + ".local" not in safe_g.nodes[0].description
    assert "[HOSTNAME_REDACTED]" in safe_g.nodes[0].description

def test_safe_mermaid_export_does_not_leak_unsafe_node_ids():
    g = VisualKnowledgeGraph()
    g.nodes.append(VisualMapNode("node_C:\\" + "Users\\Admin\\secret.txt", "source", "C:\\" + "Users\\Admin\\secret.txt", "s", "source", "c", [], "local_only", "high", "t", "t", "d", [], "open", True, "C:\\" + "Users\\Admin\\secret.txt"))
    m = export_visual_graph_mermaid(g, VisualMapExportMode.LOCAL_REDACTED)
    assert "C:\\" + "Users" not in m
    assert "[LOCAL_SOURCE]" in m

def test_local_json_export_validates_against_schema():
    g = build_test_graph()
    j = export_visual_graph_json(g, VisualMapExportMode.LOCAL_FULL)
    d = json.loads(j)
    assert len(d["nodes"]) == 3
