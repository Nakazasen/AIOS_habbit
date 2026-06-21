import pytest
from aios_habit.knowledge_map_view import (
    build_saved_graph_view,
    graph_to_node_table,
    graph_to_edge_table,
    graph_to_pretty_mermaid
)

sample_graph = {
    "nodes": [
        {"id": "node-1", "label": "LSU Component", "type": "system", "description": "Laser Scanner Unit", "source_ref": "Doc 1", "confidence": "high"},
        {"id": "node-2", "label": "Drum unit", "type": "component", "description": "Photoconductor Drum", "source_ref": "Doc 2", "confidence": "medium"},
        {"id": "node-3", "label": "Mirror", "type": "component", "description": "Polygon mirror", "source_ref": "Doc 3", "confidence": "low"}
    ],
    "edges": [
        {"from": "node-1", "to": "node-2", "relation": "exposes", "description": "exposes connection", "source_ref": "Doc 1", "confidence": "high"},
        {"from": "node-1", "to": "node-99", "relation": "connects", "description": "invalid edge", "source_ref": "Doc 99", "confidence": "low"}
    ]
}

# 1. test_graph_to_node_table
def test_graph_to_node_table():
    table = graph_to_node_table(sample_graph)
    assert len(table) == 3
    assert table[0]["label"] == "LSU Component"
    assert table[0]["type"] == "system"
    assert table[0]["confidence"] == "high"
    assert table[0]["id"] == "node-1"

# 2. test_graph_to_edge_table
def test_graph_to_edge_table():
    table = graph_to_edge_table(sample_graph)
    assert len(table) == 2
    assert table[0]["from_label"] == "LSU Component"
    assert table[0]["to_label"] == "Drum unit"
    assert table[0]["relation"] == "exposes"
    assert table[1]["from_label"] == "LSU Component"
    assert table[1]["to_label"] == "node-99"

# 3. test_pretty_mermaid_contains_relation_labels
def test_pretty_mermaid_contains_relation_labels():
    mermaid = graph_to_pretty_mermaid(sample_graph)
    assert "node_1 -->|exposes| node_2" in mermaid

# 4. test_pretty_mermaid_escapes_labels
def test_pretty_mermaid_escapes_labels():
    graph_with_quotes = {
        "nodes": [
            {"id": "node-1", "label": 'LSU "Component" (Mirror)', "type": "system"}
        ],
        "edges": []
    }
    mermaid = graph_to_pretty_mermaid(graph_with_quotes)
    assert 'node_1["LSU \'Component\' (Mirror)"]' in mermaid

# 5. test_pretty_mermaid_limits_nodes
def test_pretty_mermaid_limits_nodes():
    mermaid = graph_to_pretty_mermaid(sample_graph, max_nodes=2)
    assert "node_1" in mermaid
    assert "node_2" in mermaid
    assert "node_3" not in mermaid

# 6. test_invalid_edges_are_skipped
def test_invalid_edges_are_skipped():
    mermaid = graph_to_pretty_mermaid(sample_graph)
    assert "node_99" not in mermaid
    assert "connects" not in mermaid
