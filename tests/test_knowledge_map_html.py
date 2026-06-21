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
