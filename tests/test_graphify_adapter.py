# -*- coding: utf-8 -*-
"""Comprehensive Automated Unit & Integration Test Suite for GraphifyAdapter.

Validates:
1. In-process Python API availability & capabilities.
2. Building and loading graphs from JSON dicts and files.
3. In-process AST extraction, clustering, god nodes analysis.
4. In-process JSON, HTML, SVG export.
5. Error handling when files are missing or graphify is unavailable.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import pytest

from aios_habit.graphify_adapter import (
    GraphifyAdapter,
    GraphifyCapabilities,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Fixture creating a temporary workspace structure."""
    ws = tmp_path / "test_ws"
    ws.mkdir(parents=True, exist_ok=True)
    out_dir = ws / "graphify-out"
    out_dir.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def sample_graph_json(temp_workspace: Path) -> Path:
    """Fixture creating a minimal valid graph.json file."""
    graph_path = temp_workspace / "graphify-out" / "graph.json"
    data = {
        "nodes": [
            {"id": "mod_a", "label": "module_a", "source_file": "module_a.py"},
            {"id": "mod_b", "label": "module_b", "source_file": "module_b.py"},
            {"id": "func_calc", "label": "calculate()", "source_file": "module_a.py"},
        ],
        "edges": [
            {"source": "mod_a", "target": "mod_b", "relation": "imports", "confidence": "EXTRACTED"},
            {"source": "mod_a", "target": "func_calc", "relation": "contains", "confidence": "EXTRACTED"},
        ],
    }
    graph_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return graph_path


def test_graphify_adapter_is_available() -> None:
    """Verify is_available returns True in environment with graphify installed."""
    adapter = GraphifyAdapter()
    assert adapter.is_available() is True


def test_graphify_adapter_capabilities(temp_workspace: Path, sample_graph_json: Path) -> None:
    """Verify get_capabilities and check_capabilities return expected dictionary and dataclass."""
    adapter = GraphifyAdapter(workspace_dir=temp_workspace)

    caps = adapter.get_capabilities()
    assert isinstance(caps, GraphifyCapabilities)
    assert caps.is_available is True
    assert caps.package_name == "graphifyy"
    assert caps.has_graph_json is True
    assert caps.graph_json_path == str(sample_graph_json)
    assert caps.has_extract is True
    assert caps.has_cluster is True
    assert caps.has_god_nodes is True

    caps_dict = adapter.check_capabilities()
    assert isinstance(caps_dict, dict)
    assert caps_dict["available"] is True
    assert caps_dict["is_available"] is True
    assert caps_dict["external_cli"] is False
    assert caps_dict["has_graph_json"] is True


def test_load_graph_success(temp_workspace: Path, sample_graph_json: Path) -> None:
    """Verify loading graph directly from default workspace path."""
    adapter = GraphifyAdapter(workspace_dir=temp_workspace)
    G = adapter.load_graph()

    assert G is not None
    assert G.number_of_nodes() >= 3
    assert G.number_of_edges() >= 2


def test_load_graph_custom_path(sample_graph_json: Path) -> None:
    """Verify loading graph from an explicitly specified path."""
    adapter = GraphifyAdapter()
    G = adapter.load_graph(graph_path=sample_graph_json)

    assert G is not None
    assert "mod_a" in G.nodes
    assert "mod_b" in G.nodes


def test_load_graph_file_not_found(temp_workspace: Path) -> None:
    """Verify FileNotFoundError when graph.json does not exist."""
    non_existent = temp_workspace / "no_such_file.json"
    adapter = GraphifyAdapter(workspace_dir=temp_workspace)

    with pytest.raises(FileNotFoundError):
        adapter.load_graph(graph_path=non_existent)


def test_build_from_json_dict_and_path(temp_workspace: Path, sample_graph_json: Path) -> None:
    """Verify build_from_json works for both in-memory dict and file path."""
    adapter = GraphifyAdapter(workspace_dir=temp_workspace)

    # 1. From Path
    G1 = adapter.build_from_json(sample_graph_json, directed=True)
    assert G1.number_of_nodes() >= 3

    # 2. From Dict
    data = json.loads(sample_graph_json.read_text(encoding="utf-8"))
    G2 = adapter.build_from_json(data, directed=False)
    assert G2.number_of_nodes() >= 3

    # 3. Invalid type raises TypeError
    with pytest.raises(TypeError):
        adapter.build_from_json(12345)  # type: ignore


def test_extract_and_build(temp_workspace: Path) -> None:
    """Verify in-process AST extraction on a Python source file."""
    src_file = temp_workspace / "sample_service.py"
    src_file.write_text(
        "import os\n\nclass DataManager:\n    def fetch(self):\n        return 42\n",
        encoding="utf-8",
    )

    adapter = GraphifyAdapter(workspace_dir=temp_workspace)
    extraction = adapter.extract([src_file])

    assert isinstance(extraction, dict)
    assert "nodes" in extraction
    assert "edges" in extraction
    assert len(extraction["nodes"]) > 0

    # Build graph from extracted AST
    G = adapter.build_from_json(extraction, directed=True)
    assert G.number_of_nodes() > 0


def test_cluster_and_god_nodes(temp_workspace: Path, sample_graph_json: Path) -> None:
    """Verify in-process community detection and god nodes ranking."""
    adapter = GraphifyAdapter(workspace_dir=temp_workspace)
    G = adapter.load_graph(sample_graph_json)

    # Clustering
    communities = adapter.cluster(G, resolution=1.0)
    assert isinstance(communities, dict)
    assert len(communities) > 0

    # God nodes
    gods = adapter.god_nodes(G, top_n=5)
    assert isinstance(gods, list)
    for node_info in gods:
        assert "id" in node_info
        assert "degree" in node_info


def test_exports_json_html_svg(temp_workspace: Path, sample_graph_json: Path) -> None:
    """Verify in-process export functions to JSON, HTML, and SVG formats."""
    adapter = GraphifyAdapter(workspace_dir=temp_workspace)
    G = adapter.load_graph(sample_graph_json)
    communities = adapter.cluster(G)

    # 1. to_json (in-memory & file)
    json_str = adapter.to_json(G, communities=communities)
    assert isinstance(json_str, str)
    assert "nodes" in json_str

    out_json = temp_workspace / "export.json"
    adapter.to_json(G, communities=communities, output_path=out_json)
    assert out_json.exists()
    assert len(out_json.read_text(encoding="utf-8")) > 0

    # 2. to_html (in-memory & file)
    html_str = adapter.to_html(G, communities=communities)
    assert isinstance(html_str, str)
    assert "<html" in html_str.lower() or "<div" in html_str.lower() or "<svg" in html_str.lower()

    out_html = temp_workspace / "export.html"
    adapter.to_html(G, communities=communities, output_path=out_html)
    assert out_html.exists()

    # 3. to_svg (in-memory & file)
    svg_str = adapter.to_svg(G, communities=communities)
    assert isinstance(svg_str, str)
    assert "<svg" in svg_str.lower()

    out_svg = temp_workspace / "export.svg"
    adapter.to_svg(G, communities=communities, output_path=out_svg)
    assert out_svg.exists()


def test_adapter_when_package_unavailable() -> None:
    """Verify graceful error throwing when graphify is not installed."""
    adapter = GraphifyAdapter()
    with patch.object(adapter, "is_available", return_value=False):
        caps = adapter.get_capabilities()
        assert caps.is_available is False
        assert caps.has_extract is False

        with pytest.raises(RuntimeError) as exc_info:
            adapter.load_graph()
        assert "graphify package" in str(exc_info.value).lower()
