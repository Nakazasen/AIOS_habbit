import pytest
from aios_habit.knowledge_map_html import graph_to_html_map

sample_graph = {
    "nodes": [
        {"id": "node-1", "label": "LSU Component", "type": "system", "description": "Laser Scanner Unit", "source_ref": "Doc 1", "confidence": "high"},
        {"id": "node-2", "label": "Drum unit", "type": "component", "description": "Photoconductor Drum", "source_ref": "Doc 2", "confidence": "medium"},
        {"id": "node-3", "label": "Mirror", "type": "component", "description": "Polygon mirror", "source_ref": "Doc 3", "confidence": "low"}
    ],
    "edges": [
        {"from": "node-1", "to": "node-2", "relation": "exposes", "description": "exposes connection", "source_ref": "Doc 1", "confidence": "high"},
        {"from": "node-1", "to": "node-99", "relation": "connects", "description": "invalid", "source_ref": "Doc 99", "confidence": "low"}
    ]
}

# 1. test_html_map_contains_node_labels
def test_html_map_contains_node_labels():
    html_str = graph_to_html_map(sample_graph)
    assert "LSU Component" in html_str
    assert "Drum unit" in html_str
    assert "Mirror" in html_str

# 2. test_html_map_contains_relation_chips
def test_html_map_contains_relation_chips():
    html_str = graph_to_html_map(sample_graph)
    assert "exposes" in html_str
    assert "exposes connection" in html_str

# 3. test_html_map_escapes_html
def test_html_map_escapes_html():
    evil_graph = {
        "nodes": [
            {"id": "node-1", "label": "LSU <script>alert(1)</script>", "type": "system", "description": "<evil>", "source_ref": "<source>"}
        ],
        "edges": [
            {"from": "node-1", "to": "node-1", "relation": "<rel>", "description": "<desc>"}
        ]
    }
    html_str = graph_to_html_map(evil_graph)
    assert "<script" not in html_str
    assert "LSU &lt;script&gt;alert(1)&lt;/script&gt;" in html_str
    assert "&lt;evil&gt;" in html_str
    assert "&lt;source&gt;" in html_str
    assert "&lt;rel&gt;" in html_str
    assert "&lt;desc&gt;" in html_str

# 4. test_html_map_limits_nodes
def test_html_map_limits_nodes():
    html_str = graph_to_html_map(sample_graph, max_nodes=2)
    assert "LSU Component" in html_str
    assert "Drum unit" in html_str
    assert "Mirror" not in html_str
    assert "Cảnh báo:" in html_str

# 5. test_html_map_handles_empty_graph
def test_html_map_handles_empty_graph():
    html_str = graph_to_html_map({})
    assert "Đồ thị trống" in html_str

# 6. test_html_map_no_external_scripts
def test_html_map_no_external_scripts():
    html_str = graph_to_html_map(sample_graph)
    html_lower = html_str.lower()
    assert "<script" not in html_lower
    assert "http://" not in html_lower
    assert "https://" not in html_lower

# 7. test_html_map_max_edges_truncation
def test_html_map_max_edges_truncation():
    graph = {
        "nodes": [
            {"id": "node-1", "label": "Node 1", "type": "system"},
            {"id": "node-2", "label": "Node 2", "type": "system"},
            {"id": "node-3", "label": "Node 3", "type": "system"}
        ],
        "edges": [
            {"from": "node-1", "to": "node-2", "relation": "rel1"},
            {"from": "node-2", "to": "node-3", "relation": "rel2"}
        ]
    }
    # Limit max_edges to 1
    html_str = graph_to_html_map(graph, max_edges=1)
    assert "Cảnh báo:" in html_str
    assert "liên kết vượt quá" in html_str
    # Check that only 1 relation is rendered (or rel2 is NOT in the html)
    # The warning should indicate the truncation.
    assert "rel1" in html_str or "rel2" in html_str

# 8. test_html_map_unknown_node_type_fallback
def test_html_map_unknown_node_type_fallback():
    graph = {
        "nodes": [
            {"id": "node-unknown", "label": "Unknown Item", "type": "super_weird_type"}
        ],
        "edges": []
    }
    html_str = graph_to_html_map(graph)
    # Should fall back to 'other' column/lane
    # Under lanes, it groups by type which falls back to 'other'.
    assert "OTHER (1)" in html_str
    assert "Unknown Item" in html_str

# 9. test_html_map_explicit_source_ref_render
def test_html_map_explicit_source_ref_render():
    graph = {
        "nodes": [
            {"id": "node-1", "label": "Node 1", "type": "system", "source_ref": "Document XYZ Section 3.4"}
        ],
        "edges": []
    }
    html_str = graph_to_html_map(graph)
    assert "Document XYZ Section 3.4" in html_str

# 10. test_html_map_explicit_confidence_render
def test_html_map_explicit_confidence_render():
    graph = {
        "nodes": [
            {"id": "node-1", "label": "Node 1", "type": "system", "confidence": "high"},
            {"id": "node-2", "label": "Node 2", "type": "system", "confidence": "medium"},
            {"id": "node-3", "label": "Node 3", "type": "system", "confidence": "low"}
        ],
        "edges": []
    }
    html_str = graph_to_html_map(graph)
    assert "CONF: HIGH" in html_str
    assert "CONF: MEDIUM" in html_str
    assert "CONF: LOW" in html_str

