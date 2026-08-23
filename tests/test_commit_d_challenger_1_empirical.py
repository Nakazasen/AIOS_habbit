# -*- coding: utf-8 -*-
"""Empirical Challenger 1 Test Suite for Commit D.

Validates:
1. AST static analysis: Inspect AST of all `src/aios_habit/*.py` and verify ZERO `subprocess` or `shutil.which` calls for graphify/excaliflow.
2. Capability degradation: Simulate missing graphic libraries / unavailable states; verify `ExcaliFlowAdapter` returns `CapabilityStatus.UNAVAILABLE` and emits localized `evidence_graph_render_error` without crashing.
3. Concurrency & Thread-safety: Test concurrent capability checks and scene exports across threads.
4. Clean environment smoke test: Load synthetic `rag-trace/v1` trace, verify topology mapping, deterministic content hashing, and HTML/SVG rendering.
"""
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Set
from unittest.mock import patch
import pytest

from aios_habit.evidence_graph_viewer import (
    EvidenceGraphViewerCache,
    EvidenceGraphViewModel,
    build_evidence_graph_view_model,
    compute_trace_content_hash,
    render_evidence_graph_html,
)
from aios_habit.evidence_trace import create_evidence_trace
from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
)
from aios_habit.excaliflow_adapter import (
    CJK_MULTI_LOCALE_FONT_STACK,
    CapabilityStatus,
    ExcaliFlowAdapter,
    ExcaliFlowCapabilities,
)
from aios_habit.graphify_adapter import (
    GraphifyAdapter,
    GraphifyCapabilities,
)
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    normalize_locale,
    t,
)
import uuid

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def _make_sample_trace(
    query: str = "Query",
    answer_text: str = "Answer",
    citations: Optional[List[Dict[str, Any]]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    ui_locale: str = DEFAULT_LOCALE,
    answer_language: str = DEFAULT_LOCALE,
    trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EvidenceTrace:
    t_id = trace_id or f"trc_sample_{uuid.uuid4().hex[:8]}"
    nodes: List[EvidenceNode] = [
        EvidenceNode(id=f"q_{t_id}", node_type="question", title=query, snippet=query),
        EvidenceNode(id=f"a_{t_id}", node_type="answer", title=answer_text, snippet=answer_text),
    ]
    edges: List[EvidenceEdge] = [
        EvidenceEdge(source_id=f"a_{t_id}", target_id=f"q_{t_id}", relation_type="derives_from"),
    ]

    src_map: Dict[str, str] = {}
    if sources:
        for s in sources:
            s_id = str(s.get("source_id", "s1"))
            s_title = str(s.get("title", s_id))
            nodes.append(EvidenceNode(
                id=s_id,
                node_type="source",
                title=s_title,
                snippet=s.get("snippet", ""),
                source_id=s.get("source_path", s_id),
            ))
            src_map[s_id] = s_id

    if citations:
        for idx, c in enumerate(citations):
            c_id = str(c.get("citation_id", f"[{idx+1}]"))
            c_node_id = f"cit_{t_id}_{idx}"
            s_id = str(c.get("source_id", "s1"))
            nodes.append(EvidenceNode(
                id=c_node_id,
                node_type="citation",
                title=c_id,
                snippet=c.get("snippet", ""),
                citation_id=c_id,
                source_id=s_id,
            ))
            edges.append(EvidenceEdge(source_id=f"a_{t_id}", target_id=c_node_id, relation_type="cites"))
            if s_id in src_map:
                edges.append(EvidenceEdge(source_id=c_node_id, target_id=s_id, relation_type="extracted_from"))

    return EvidenceTrace(
        trace_id=t_id,
        query=query,
        answer_text=answer_text,
        ui_locale=ui_locale,
        answer_language=answer_language,
        nodes=nodes,
        edges=edges,
        metadata=metadata or {"status": "valid", "insufficient_evidence": False},
    )


# ==============================================================================
# 1. AST Static Analysis: Inspect all `src/aios_habit/*.py`
# ==============================================================================

class TestChallenger1ASTStaticAnalysis:
    """Empirical verification that Graphify and ExcaliFlow adapters use ZERO subprocess or shutil.which calls."""

    ADAPTER_FILES = [
        "src/aios_habit/graphify_adapter.py",
        "src/aios_habit/excaliflow_adapter.py",
        "src/aios_habit/evidence_graph_viewer.py",
        "src/aios_habit/evidence_trace.py",
        "src/aios_habit/evidence_trace_schema.py",
    ]

    def test_all_aios_habit_files_ast_parseable(self) -> None:
        """Verify all python files in src/aios_habit/ are syntactically valid and parseable into AST."""
        src_dir = REPO_ROOT / "src" / "aios_habit"
        py_files = list(src_dir.glob("*.py"))
        assert len(py_files) >= 40, f"Expected >=40 python files in src/aios_habit, found {len(py_files)}"

        for py_file in py_files:
            content = py_file.read_text(encoding="utf-8-sig")
            tree = ast.parse(content, filename=str(py_file))
            assert isinstance(tree, ast.Module), f"Failed to parse AST for {py_file.name}"

    def test_zero_subprocess_in_graphify_and_excaliflow_adapters(self) -> None:
        """Inspect AST of graphify and excaliflow modules to prove ZERO subprocess imports or invocations."""
        prohibited_call_names = {"run", "popen", "call", "check_output", "check_call", "system", "spawn"}

        for rel_path in self.ADAPTER_FILES:
            target = REPO_ROOT / rel_path
            assert target.exists(), f"Target file missing: {rel_path}"
            tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))

            for node in ast.walk(tree):
                # Check for import subprocess
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name != "subprocess", (
                            f"Violation: 'import subprocess' found in {rel_path}:{node.lineno}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert node.module != "subprocess", (
                            f"Violation: 'from subprocess import ...' found in {rel_path}:{node.lineno}"
                        )

                # Check for direct calls like os.system or subprocess.run
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        attr_name = node.func.attr.lower()
                        if isinstance(node.func.value, ast.Name):
                            val_id = node.func.value.id.lower()
                            if val_id in ("subprocess", "os") and attr_name in prohibited_call_names:
                                assert False, (
                                    f"Violation: call '{val_id}.{attr_name}' found in {rel_path}:{node.lineno}"
                                )

    def test_zero_shutil_which_in_graphify_and_excaliflow_adapters(self) -> None:
        """Inspect AST of adapters to guarantee ZERO shutil.which calls (strictly no PATH probing)."""
        for rel_path in self.ADAPTER_FILES:
            target = REPO_ROOT / rel_path
            tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    assert node.func.attr != "which", (
                        f"Violation: 'which()' PATH lookup call found in {rel_path}:{node.lineno}"
                    )

    def test_all_src_files_graphify_excaliflow_references_never_invoke_cli(self) -> None:
        """Verify across entire src/aios_habit/*.py that graphify/excaliflow are never invoked via CLI string commands."""
        src_dir = REPO_ROOT / "src" / "aios_habit"
        cli_command_patterns = [
            re.compile(r'["\']graphify\s+(extract|cluster|export|view|update)', re.IGNORECASE),
            re.compile(r'["\']excaliflow\s+', re.IGNORECASE),
            re.compile(r'subprocess\..*graphify', re.IGNORECASE),
            re.compile(r'subprocess\..*excaliflow', re.IGNORECASE),
        ]

        for py_file in src_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in cli_command_patterns:
                match = pattern.search(content)
                assert match is None, (
                    f"Violation: Prohibited external CLI command pattern '{pattern.pattern}' found in {py_file.name}: {match.group(0)}"
                )


# ==============================================================================
# 2. Capability Degradation & Error Handling
# ==============================================================================

class TestChallenger1CapabilityDegradation:
    """Empirical verification that ExcaliFlowAdapter returns UNAVAILABLE and localized error banners without crashing."""

    def test_unavailable_status_via_override_status(self) -> None:
        """Verify ExcaliFlowAdapter initialized with override_status=CapabilityStatus.UNAVAILABLE."""
        adapter = ExcaliFlowAdapter(override_status=CapabilityStatus.UNAVAILABLE)
        caps = adapter.check_capabilities()

        assert caps.status == CapabilityStatus.UNAVAILABLE
        assert caps.is_available is False
        assert caps.has_html_renderer is False
        assert caps.has_svg_renderer is False
        assert caps.has_excalidraw_export is False
        assert len(caps.supported_formats) == 0
        assert "simulated_override" in caps.missing_dependencies

    def test_unavailable_status_via_override_available_false(self) -> None:
        """Verify ExcaliFlowAdapter initialized with override_available=False."""
        adapter = ExcaliFlowAdapter(override_available=False)
        assert adapter.is_available() is False

        caps = adapter.check_capabilities()
        assert caps.status == CapabilityStatus.UNAVAILABLE
        assert caps.is_available is False

    @pytest.mark.parametrize("locale,expected_error_text", [
        ("vi", "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra."),
        ("ja", "根拠グラフを表示できません。エラーが発生しました。"),
        ("zh-CN", "无法显示证据图谱。发生错误。"),
        ("fr-FR", "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra."),  # Fallback to vi
        ("", "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra."),       # Fallback to vi
    ])
    def test_render_trace_html_unavailable_emits_localized_error_banner(
        self, locale: str, expected_error_text: str
    ) -> None:
        """Verify render_trace_html under UNAVAILABLE state returns localized error card without crashing."""
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = _make_sample_trace(
            query="Test query",
            answer_text="Test answer [1]",
            citations=[{"citation_id": "[1]", "snippet": "Test snippet", "source_path": "doc.txt", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "doc.txt", "source_path": "doc.txt"}],
        )

        html_out = adapter.render_trace_html(trace, locale=locale)
        assert isinstance(html_out, str)
        assert '<div class="egv-container egv-error"' in html_out
        assert expected_error_text in html_out
        assert "❌" in html_out

    def test_render_trace_svg_unavailable_emits_localized_error_svg(self) -> None:
        """Verify render_trace_svg under UNAVAILABLE state returns valid SVG error card."""
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = _make_sample_trace(query="Test", answer_text="Answer")

        svg_out = adapter.render_trace_svg(trace, locale="ja")
        assert isinstance(svg_out, str)
        assert "<svg" in svg_out
        assert "</svg>" in svg_out
        assert "根拠グラフを表示できません。エラーが発生しました。" in svg_out

    def test_export_excalidraw_scene_unavailable_raises_clean_runtime_error(self) -> None:
        """Verify export_excalidraw_scene under UNAVAILABLE state fails closed with informative RuntimeError."""
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = _make_sample_trace(query="Test", answer_text="Answer")

        with pytest.raises(RuntimeError) as excinfo:
            adapter.export_excalidraw_scene(trace, locale="vi")
        assert "unavailable" in str(excinfo.value).lower()

    def test_renderer_internal_exception_resilience(self) -> None:
        """Verify unexpected runtime exceptions inside render_trace_html produce clean localized error container."""
        adapter = ExcaliFlowAdapter()

        with patch("aios_habit.excaliflow_adapter.render_evidence_graph_html", side_effect=Exception("GPU driver crash")):
            html_out = adapter.render_trace_html({}, locale="zh-CN")
            assert '<div class="egv-container egv-error"' in html_out
            assert "无法显示证据图谱。发生错误。" in html_out


# ==============================================================================
# 3. Concurrency & Thread-Safety Stress Testing
# ==============================================================================

class TestChallenger1ConcurrencyAndThreadSafety:
    """Empirical verification of thread-safety under concurrent capability checks, scene exports, and renders."""

    def test_concurrent_capability_checks_and_scene_exports(self) -> None:
        """Test concurrent capability checks and export_excalidraw_scene across 30 threads."""
        adapter = ExcaliFlowAdapter()
        trace = _make_sample_trace(
            query="Kiểm thử tải đồng thời",
            answer_text="Hệ thống vận hành ổn định [1].",
            citations=[{"citation_id": "[1]", "snippet": "Tải cao", "source_path": "load.txt", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "load.txt", "source_path": "load.txt"}],
        )

        caps_results: List[Any] = []
        scene_results: List[Dict[str, Any]] = []
        errors: List[Exception] = []

        def worker_caps() -> Any:
            return adapter.check_capabilities()

        def worker_export() -> Dict[str, Any]:
            return adapter.export_excalidraw_scene(trace, locale="vi")

        with ThreadPoolExecutor(max_workers=30) as executor:
            fut_caps = [executor.submit(worker_caps) for _ in range(50)]
            fut_scenes = [executor.submit(worker_export) for _ in range(50)]

            for fut in as_completed(fut_caps):
                try:
                    caps_results.append(fut.result())
                except Exception as exc:
                    errors.append(exc)

            for fut in as_completed(fut_scenes):
                try:
                    scene_results.append(fut.result())
                except Exception as exc:
                    errors.append(exc)

        assert len(errors) == 0, f"Concurrency errors occurred: {errors}"
        assert len(caps_results) == 50
        assert len(scene_results) == 50

        # Verify all exported scenes are structurally intact
        for scene in scene_results:
            assert scene["type"] == "excalidraw"
            assert scene["version"] == 2
            assert len(scene["elements"]) > 0

    def test_concurrent_multilingual_html_and_svg_rendering(self) -> None:
        """Test concurrent rendering across vi, ja, zh-CN locales with 30 threads."""
        adapter = ExcaliFlowAdapter()
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

        locales = ["vi", "ja", "zh-CN"]
        render_results: List[str] = []
        svg_results: List[str] = []
        errors: List[Exception] = []

        def render_html_task(idx: int) -> str:
            loc = locales[idx % len(locales)]
            return adapter.render_trace_html(raw_data, locale=loc, use_cache=True)

        def render_svg_task(idx: int) -> str:
            loc = locales[idx % len(locales)]
            return adapter.render_trace_svg(raw_data, locale=loc)

        with ThreadPoolExecutor(max_workers=30) as executor:
            fut_html = [executor.submit(render_html_task, i) for i in range(60)]
            fut_svg = [executor.submit(render_svg_task, i) for i in range(60)]

            for fut in as_completed(fut_html):
                try:
                    render_results.append(fut.result())
                except Exception as exc:
                    errors.append(exc)

            for fut in as_completed(fut_svg):
                try:
                    svg_results.append(fut.result())
                except Exception as exc:
                    errors.append(exc)

        assert len(errors) == 0
        assert len(render_results) == 60
        assert len(svg_results) == 60

        for r in render_results:
            assert '<div class="egv-container egv-full"' in r
        for s in svg_results:
            assert "<svg" in s and "</svg>" in s


# ==============================================================================
# 4. Clean Environment Smoke Test & Synthetic rag-trace/v1 Verification
# ==============================================================================

class TestChallenger1CleanEnvironmentSmokeTest:
    """Empirical verification using synthetic rag-trace/v1 trace fixture."""

    def test_synthetic_rag_trace_topology_mapping(self) -> None:
        """Verify exact 1-to-1 topology mapping (nodes, edges, node types, relations) from synthetic fixture."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        assert fixture_path.exists()

        trace_dict = json.loads(fixture_path.read_text(encoding="utf-8"))
        view_model: EvidenceGraphViewModel = build_evidence_graph_view_model(trace_dict, locale="vi")

        assert view_model.is_insufficient is False
        assert len(view_model.nodes) == 6
        assert len(view_model.edges) == 5

        # Check nodes
        node_id_map = {n["id"]: n for n in view_model.nodes}
        assert "n_q" in node_id_map and node_id_map["n_q"]["node_type"] == "question"
        assert "n_a" in node_id_map and node_id_map["n_a"]["node_type"] == "answer"
        assert "n_c1" in node_id_map and node_id_map["n_c1"]["node_type"] == "citation"
        assert "n_c2" in node_id_map and node_id_map["n_c2"]["node_type"] == "citation"
        assert "src_doc_1" in node_id_map and node_id_map["src_doc_1"]["node_type"] == "source"
        assert "src_doc_2" in node_id_map and node_id_map["src_doc_2"]["node_type"] == "source"

        # Check edges
        edge_tuples = [(e["source_id"], e["target_id"], e["relation"]) for e in view_model.edges]
        assert ("n_q", "n_a", "derives_from") in edge_tuples
        assert ("n_c1", "n_a", "supports") in edge_tuples
        assert ("n_c2", "n_a", "supports") in edge_tuples
        assert ("src_doc_1", "n_c1", "extracted_from") in edge_tuples
        assert ("src_doc_2", "n_c2", "extracted_from") in edge_tuples

    def test_deterministic_content_hashing_consistency(self) -> None:
        """Verify SHA-256 content hashing is 100% deterministic across 100 iterations."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        trace_dict = json.loads(fixture_path.read_text(encoding="utf-8"))

        initial_hash = compute_trace_content_hash(trace_dict)
        assert len(initial_hash) == 64
        assert re.match(r"^[0-9a-f]{64}$", initial_hash)

        for _ in range(100):
            h = compute_trace_content_hash(trace_dict)
            assert h == initial_hash

    def test_html_and_svg_rendering_from_synthetic_trace(self) -> None:
        """Verify rendering HTML and SVG from synthetic trace fixture produces self-contained artifacts."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        trace_dict = json.loads(fixture_path.read_text(encoding="utf-8"))

        adapter = ExcaliFlowAdapter()

        # HTML Rendering
        html_board = adapter.render_trace_html(trace_dict, locale="vi", use_cache=False)
        assert '<div class="egv-container egv-full"' in html_board
        assert "ERR_KHO_SYNC_0x80040111" in html_board
        assert "Báo_cáo_tài_chính_và_kho_vận_Q3_2026.xlsx" in html_board
        assert "Quy_trình_kiểm_kê_kho_hàng_v3.docx" in html_board
        assert "[1]" in html_board
        assert "[2]" in html_board

        # SVG Rendering
        svg_board = adapter.render_trace_svg(trace_dict, locale="vi")
        assert svg_board.startswith("<svg")
        assert svg_board.endswith("</svg>")
        assert "ERR_KHO_SYNC_0x80040111" in svg_board
        assert "Báo_cáo_tài_chính_và_kho_vận_Q3_2026.xlsx" in svg_board

    def test_excalidraw_scene_export_from_synthetic_trace(self) -> None:
        """Verify Excalidraw scene JSON export from synthetic trace fixture."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        trace_dict = json.loads(fixture_path.read_text(encoding="utf-8"))

        adapter = ExcaliFlowAdapter()
        scene = adapter.export_excalidraw_scene(trace_dict, locale="vi")

        assert scene["type"] == "excalidraw"
        assert scene["version"] == 2
        assert "elements" in scene
        assert len(scene["elements"]) >= 11  # 6 node rects + text + 5 edge arrows
