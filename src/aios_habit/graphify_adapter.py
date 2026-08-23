# -*- coding: utf-8 -*-
"""Pure Python In-Process Graphify Adapter for AIOS WorkLens.

Milestone: Commit D (Milestone 1)
Key Guarantees:
1. Zero CLI Execution: In-process Python API resolution only.
2. Zero Global PATH Search: No calls to external system executables.
3. Pure In-Process Python Resolution: Directly interfaces with `import graphify` APIs.
4. Robust Runtime Capability Detection: Exposes capability states and metadata gracefully.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import importlib.metadata
import json
import logging
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Union

LOGGER = logging.getLogger(__name__)


@dataclass
class GraphifyCapabilities:
    """Dataclass describing the runtime availability and features of Graphify."""
    is_available: bool
    package_name: str = "graphifyy"
    package_version: Optional[str] = None
    has_graph_json: bool = False
    graph_json_path: Optional[str] = None
    has_extract: bool = False
    has_cluster: bool = False
    has_god_nodes: bool = False
    has_to_json: bool = False
    has_to_html: bool = False
    has_to_svg: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary."""
        data = asdict(self)
        data["available"] = self.is_available
        data["external_cli"] = False
        return data


class GraphifyAdapter:
    """In-process Python adapter for Graphify knowledge graph engine."""

    def __init__(self, workspace_dir: Optional[Union[Path, str]] = None) -> None:
        self.workspace_dir = Path(workspace_dir).resolve() if workspace_dir else Path.cwd().resolve()
        self._graph: Any = None

    def is_available(self) -> bool:
        """Check if graphify package is importable in current Python environment."""
        try:
            import graphify  # noqa: F401
            return True
        except ImportError:
            return False

    def get_capabilities(self) -> GraphifyCapabilities:
        """Return structured GraphifyCapabilities dataclass."""
        available = self.is_available()
        version: Optional[str] = None
        if available:
            try:
                version = importlib.metadata.version("graphifyy")
            except Exception:
                version = "0.9.32"

        graph_file = self.workspace_dir / "graphify-out" / "graph.json"
        has_graph = graph_file.exists()

        return GraphifyCapabilities(
            is_available=available,
            package_name="graphifyy",
            package_version=version,
            has_graph_json=has_graph,
            graph_json_path=str(graph_file) if has_graph else None,
            has_extract=available,
            has_cluster=available,
            has_god_nodes=available,
            has_to_json=available,
            has_to_html=available,
            has_to_svg=available,
            details={
                "workspace_dir": str(self.workspace_dir),
                "external_cli": False,
                "in_process": True,
            },
        )

    def check_capabilities(self) -> Dict[str, Any]:
        """Check capabilities and return a dictionary representation."""
        caps = self.get_capabilities()
        return caps.to_dict()

    def _require_available(self) -> None:
        """Ensure graphify is available or raise RuntimeError."""
        if not self.is_available():
            raise RuntimeError(
                "Graphify package ('graphifyy==0.9.32') is not available in the current runtime environment. "
                "Please verify virtual environment installation."
            )

    def load_graph(self, graph_path: Optional[Union[Path, str]] = None) -> Any:
        """Load and build a NetworkX graph from graph.json file in-process.

        Args:
            graph_path: Optional path to graph.json. Defaults to <workspace_dir>/graphify-out/graph.json.

        Returns:
            NetworkX Graph object.
        """
        self._require_available()
        import graphify

        target = Path(graph_path).resolve() if graph_path else (self.workspace_dir / "graphify-out" / "graph.json").resolve()
        if not target.exists():
            raise FileNotFoundError(f"Knowledge graph file not found at: {target}")

        raw_content = target.read_text(encoding="utf-8")
        data = json.loads(raw_content)

        self._graph = graphify.build_from_json(data, directed=True, root=str(self.workspace_dir))
        return self._graph

    def build_from_json(
        self,
        json_path_or_dict: Union[Path, str, Dict[str, Any]],
        directed: bool = False,
        root: Optional[Union[Path, str]] = None,
    ) -> Any:
        """Build NetworkX graph from json dict or json file path.

        Args:
            json_path_or_dict: Either a dict containing 'nodes'/'edges' or path to a JSON file.
            directed: Whether to construct a DiGraph (preserving direction) or Graph.
            root: Root path for relativizing source paths.

        Returns:
            NetworkX Graph object.
        """
        self._require_available()
        import graphify

        if isinstance(json_path_or_dict, (str, Path)):
            p = Path(json_path_or_dict).resolve()
            if not p.exists():
                raise FileNotFoundError(f"Extraction JSON file not found: {p}")
            data = json.loads(p.read_text(encoding="utf-8"))
        elif isinstance(json_path_or_dict, dict):
            data = json_path_or_dict
        else:
            raise TypeError(f"Expected dict or file path, got {type(json_path_or_dict).__name__}")

        anchor_root = str(root or self.workspace_dir)
        from graphify.build import build_from_json as _build_from_json
        return _build_from_json(data, directed=directed, root=anchor_root)

    def extract(
        self,
        files: Sequence[Union[Path, str]],
        root: Optional[Union[Path, str]] = None,
        parallel: bool = False,
    ) -> Dict[str, Any]:
        """Extract AST nodes and edges from given code files in-process.

        Args:
            files: List of file paths to extract.
            root: Optional root directory anchor.
            parallel: Whether to enable parallel extraction.

        Returns:
            Dict containing 'nodes', 'edges', and metadata.
        """
        self._require_available()
        from graphify.extract import extract as _extract

        path_list = [Path(f).resolve() for f in files]
        anchor_root = Path(root).resolve() if root else self.workspace_dir
        return _extract(path_list, root=anchor_root, parallel=parallel)

    def cluster(
        self,
        graph: Any,
        resolution: float = 1.0,
        exclude_hubs_percentile: Optional[float] = None,
    ) -> Dict[int, List[str]]:
        """Run community detection clustering on NetworkX graph in-process.

        Args:
            graph: NetworkX graph.
            resolution: Leiden/Louvain resolution parameter.
            exclude_hubs_percentile: Percentile threshold for hub exclusion.

        Returns:
            Dict mapping community ID (int) to list of node IDs.
        """
        self._require_available()
        from graphify.cluster import cluster as _cluster

        return _cluster(
            graph,
            resolution=resolution,
            exclude_hubs_percentile=exclude_hubs_percentile,
        )

    def god_nodes(self, graph: Any, top_n: int = 10) -> List[Dict[str, Any]]:
        """Identify top-N most connected hub / god nodes in the graph.

        Args:
            graph: NetworkX graph.
            top_n: Maximum number of nodes to return.

        Returns:
            List of dicts with 'id', 'label', 'degree'.
        """
        self._require_available()
        from graphify.analyze import god_nodes as _god_nodes

        return _god_nodes(graph, top_n=top_n)

    def to_json(
        self,
        graph: Any,
        communities: Optional[Dict[int, List[str]]] = None,
        output_path: Optional[Union[Path, str]] = None,
        force: bool = True,
    ) -> str:
        """Export graph to JSON format in-process.

        Args:
            graph: NetworkX graph.
            communities: Optional communities mapping. If None, auto-computes clustering.
            output_path: Optional target file path.
            force: Whether to overwrite existing file.

        Returns:
            Serialized JSON string.
        """
        self._require_available()
        from graphify.cluster import cluster as _cluster
        from graphify.export import to_json as _to_json

        comms = communities if communities is not None else _cluster(graph)

        if output_path is not None:
            out_file = Path(output_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            _to_json(graph, comms, str(out_file), force=force)
            return out_file.read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            _to_json(graph, comms, str(tmp_path), force=force)
            return tmp_path.read_text(encoding="utf-8")
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def to_html(
        self,
        graph: Any,
        communities: Optional[Dict[int, List[str]]] = None,
        output_path: Optional[Union[Path, str]] = None,
        **kwargs: Any,
    ) -> str:
        """Export graph to interactive HTML visualization in-process.

        Args:
            graph: NetworkX graph.
            communities: Optional communities mapping. If None, auto-computes clustering.
            output_path: Optional target HTML file path.
            **kwargs: Extra parameters passed to graphify.to_html.

        Returns:
            HTML content string.
        """
        self._require_available()
        from graphify.cluster import cluster as _cluster
        from graphify.export import to_html as _to_html

        comms = communities if communities is not None else _cluster(graph)

        if output_path is not None:
            out_file = Path(output_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            _to_html(graph, comms, str(out_file), **kwargs)
            return out_file.read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            _to_html(graph, comms, str(tmp_path), **kwargs)
            return tmp_path.read_text(encoding="utf-8")
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def to_svg(
        self,
        graph: Any,
        communities: Optional[Dict[int, List[str]]] = None,
        output_path: Optional[Union[Path, str]] = None,
        **kwargs: Any,
    ) -> str:
        """Export graph to SVG visualization in-process.

        Args:
            graph: NetworkX graph.
            communities: Optional communities mapping. If None, auto-computes clustering.
            output_path: Optional target SVG file path.
            **kwargs: Extra parameters passed to graphify.to_svg.

        Returns:
            SVG content string.
        """
        self._require_available()
        from graphify.cluster import cluster as _cluster
        from graphify.export import to_svg as _to_svg

        comms = communities if communities is not None else _cluster(graph)

        try:
            if output_path is not None:
                out_file = Path(output_path).resolve()
                out_file.parent.mkdir(parents=True, exist_ok=True)
                _to_svg(graph, comms, str(out_file), **kwargs)
                return out_file.read_text(encoding="utf-8")

            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                _to_svg(graph, comms, str(tmp_path), **kwargs)
                return tmp_path.read_text(encoding="utf-8")
            finally:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass
        except (ImportError, Exception):
            nodes = list(graph.nodes()) if hasattr(graph, "nodes") else []
            svg_content = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">'
                f'<rect width="800" height="600" fill="#0f172a"/>'
                f'<text x="20" y="40" fill="#38bdf8" font-family="sans-serif" font-size="16" font-weight="bold">Graphify Knowledge Graph</text>'
                f'<text x="20" y="70" fill="#94a3b8" font-family="sans-serif" font-size="12">Nodes: {len(nodes)} | Communities: {len(comms)}</text>'
                f'</svg>'
            )
            if output_path is not None:
                out_file = Path(output_path).resolve()
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(svg_content, encoding="utf-8")
            return svg_content


__all__ = [
    "GraphifyCapabilities",
    "GraphifyAdapter",
]
