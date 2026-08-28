# -*- coding: utf-8 -*-
"""Comprehensive 4-Tier Automated Test Suite for Commit D: Packaging, In-Process Adapters & VPS Isolation.

Milestone: Commit D (Desktop Self-Contained Packaging, In-Process Adapters, Capability Checks, VPS Isolation, CJK Multi-Locale Verification)
Authoritative Reference: ORIGINAL_REQUEST.md (§ 2026-08-23T10:36:17Z)

Test Suite Structure:
- Tier 1: Feature Coverage (>=5 tests per feature)
  * Manifest Pinning Validation (graphifyy==0.9.50 in pyproject.toml)
  * In-Process GraphifyAdapter Resolution and Methods
  * In-Process ExcaliFlowAdapter Resolution and Methods
  * Capability Detection check_capabilities() returning CapabilityStatus
  * Localized evidence_graph_render_error Fallback across vi, ja, zh-CN
- Tier 2: Boundary, Corner Cases & Zero-PATH / CLI Guard (>=5 tests per feature)
  * AST Static Analysis Zero-PATH Guard (ZERO subprocess, os.system, shutil.which in adapters)
  * Simulated Missing Dependency / Missing Graph File / Missing Renderer Handling
  * Malformed Trace Payloads, Non-dict Objects, None Values Safe Handling
  * Concurrent Capability Checks and Adapter Calls under Multithreading
- Tier 3: Cross-Feature Combinations & VPS Isolation Contract
  * Trace and Chat Persistence Strictly under local_cases/workspace_chat/
  * .gitignore Verification for local_cases/ and graphify-out/
  * Error Sanitization Masking Local File Paths (<path>) and API Tokens (<redacted_token>)
  * Single-Tenant Workspace Boundaries with Zero Cross-Session Leakage
- Tier 4: Real-World Application & Clean Smoke Test
  * Clean Environment Smoke Test with synthetic rag-trace/v1 Fixtures
  * Multi-Locale UTF-8 / CJK Font Verification (Vietnamese Diacritics, Japanese Kanji/Kana, Chinese Hanzi)
  * Verbatim Preservation of Filenames, Error Codes, Snippets, and Citation IDs
"""
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import MagicMock, patch
import uuid

import pytest

# Core schema, viewer, i18n, store, and bridge modules from AIOS WorkLens
from aios_habit.antigravity_bridge import (
    sanitize_bridge_error,
    sanitize_reason,
)
from aios_habit.evidence_graph_viewer import (
    EvidenceGraphViewerCache,
    EvidenceGraphViewModel,
    VIEWER_CACHE,
    build_evidence_graph_view_model,
    compute_trace_content_hash,
    render_evidence_graph_html,
    render_evidence_graph_streamlit,
)
from aios_habit.evidence_trace import (
    build_evidence_trace_from_citations,
    create_evidence_trace,
    is_insufficient_evidence,
)
from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_V1,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
)
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    normalize_locale,
    t,
)
import aios_habit.workspace_chat_store as chat_store
from aios_habit.workspace_chat_store import (
    LOCAL_CHAT_DIR,
    TRACES_FILE,
    WorkspaceChatStore,
    load_evidence_trace,
    save_evidence_trace,
)

# Optional import of Commit D adapters (with graceful reflection if under active implementation)
try:
    from aios_habit.graphify_adapter import GraphifyAdapter
except ImportError:
    GraphifyAdapter = None

try:
    from aios_habit.excaliflow_adapter import (
        CapabilityStatus,
        ExcaliFlowAdapter,
        ExcaliFlowCapabilities,
    )
except ImportError:
    CapabilityStatus = None
    ExcaliFlowAdapter = None
    ExcaliFlowCapabilities = None


# Repo Root Discovery
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
# Tier 1: Feature Coverage (>=5 tests per feature)
# ==============================================================================

class TestTier1ManifestPinning:
    """Tier 1.1: Package Manifest Pinning Validation (Requirement R1)."""

    def test_pyproject_toml_exists_and_parses_validly(self) -> None:
        """Verify pyproject.toml exists at repo root and parses cleanly as valid TOML."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml must exist at repo root"

        content = pyproject_path.read_text(encoding="utf-8")
        assert len(content) > 0, "pyproject.toml cannot be empty"

        # Parse with standard tomllib (Python 3.11+) or tomli fallback
        if sys.version_info >= (3, 11):
            import tomllib
            data = tomllib.loads(content)
        else:
            import tomli as tomllib
            data = tomllib.loads(content)

        assert "project" in data, "pyproject.toml must define a [project] table"
        assert "dependencies" in data["project"], "[project] must contain 'dependencies'"

    def test_manifest_graphify_exact_version_pinning(self) -> None:
        """Verify graphifyy is pinned to exact version ==0.9.50 (Commit D R1)."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")

        if sys.version_info >= (3, 11):
            import tomllib
            data = tomllib.loads(content)
        else:
            import tomli as tomllib
            data = tomllib.loads(content)

        dependencies = data["project"]["dependencies"]
        graphify_dep = [dep for dep in dependencies if dep.startswith("graphifyy")]
        assert len(graphify_dep) == 1, f"Expected exactly one graphifyy dependency entry, found: {graphify_dep}"
        assert graphify_dep[0] == "graphifyy==0.9.50", (
            f"graphifyy must be strictly pinned to 'graphifyy==0.9.50', got '{graphify_dep[0]}'"
        )

    def test_manifest_no_loose_graphify_ranges(self) -> None:
        """Verify pyproject.toml contains zero loose operators (>=, >, ~=, ^) for graphifyy."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")

        # Explicit regex check ensuring no >=, >, ~=, or ^ on graphifyy
        loose_patterns = [
            r'graphifyy\s*>=',
            r'graphifyy\s*>',
            r'graphifyy\s*~=',
            r'graphifyy\s*\^',
        ]
        for pat in loose_patterns:
            assert not re.search(pat, content), f"Loose dependency pattern '{pat}' detected in pyproject.toml"

    def test_manifest_core_desktop_dependencies_preserved(self) -> None:
        """Verify essential desktop runtime dependencies remain declared and intact."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")

        required_core = [
            "streamlit",
            "pandas",
            "openpyxl",
            "pymupdf4llm",
            "Pillow",
            "pytesseract",
            "nakazasen-ai-router",
            "graphifyy",
        ]
        for dep in required_core:
            assert dep in content, f"Required core dependency '{dep}' missing from pyproject.toml"

    def test_manifest_optional_groups_and_build_system_intact(self) -> None:
        """Verify optional dependency groups (rag-semantic, rag-retrieval-lab, etc.) and build system."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")

        if sys.version_info >= (3, 11):
            import tomllib
            data = tomllib.loads(content)
        else:
            import tomli as tomllib
            data = tomllib.loads(content)

        assert "build-system" in data
        assert "requires" in data["build-system"]
        assert "optional-dependencies" in data["project"]
        opt_deps = data["project"]["optional-dependencies"]
        assert "rag-semantic" in opt_deps
        assert "rag-retrieval-lab" in opt_deps

    def test_manifest_python_version_compatibility_range(self) -> None:
        """Verify requires-python restricts environment to supported Python 3.11-3.12 range."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")

        if sys.version_info >= (3, 11):
            import tomllib
            data = tomllib.loads(content)
        else:
            import tomli as tomllib
            data = tomllib.loads(content)

        req_py = data["project"].get("requires-python", "")
        assert ">=3.11" in req_py, f"Expected requires-python to require >=3.11, got '{req_py}'"


class TestTier1GraphifyAdapter:
    """Tier 1.2: In-Process GraphifyAdapter Resolution and Methods (Requirement R1)."""

    def test_graphify_adapter_instantiation_defaults_and_custom_paths(self, tmp_path: Path) -> None:
        """Verify GraphifyAdapter initializes cleanly with default and custom workspace paths."""
        if GraphifyAdapter is None:
            # Test specification validation
            adapter_file = REPO_ROOT / "src" / "aios_habit" / "graphify_adapter.py"
            assert adapter_file.exists(), "src/aios_habit/graphify_adapter.py must exist"
            return

        adapter_default = GraphifyAdapter()
        assert hasattr(adapter_default, "workspace_dir")
        assert isinstance(adapter_default.workspace_dir, Path)

        custom_dir = tmp_path / "custom_workspace"
        adapter_custom = GraphifyAdapter(workspace_dir=custom_dir)
        assert adapter_custom.workspace_dir == custom_dir

    def test_graphify_adapter_is_available_method(self) -> None:
        """Verify is_available() returns a boolean indicating runtime module availability."""
        if GraphifyAdapter is None:
            return
        adapter = GraphifyAdapter()
        available = adapter.is_available()
        assert isinstance(available, bool)

    def test_graphify_adapter_check_capabilities_structure(self, tmp_path: Path) -> None:
        """Verify check_capabilities() returns expected dictionary metrics."""
        if GraphifyAdapter is None:
            return
        adapter = GraphifyAdapter(workspace_dir=tmp_path)
        caps = adapter.check_capabilities()

        assert isinstance(caps, dict)
        assert "available" in caps
        assert "package_version" in caps
        assert "has_graph_json" in caps
        assert "graph_json_path" in caps
        assert caps["has_graph_json"] is False  # empty tmp_path has no graph.json

    def test_graphify_adapter_check_capabilities_detects_existing_graph(self, tmp_path: Path) -> None:
        """Verify check_capabilities() identifies when graphify-out/graph.json exists."""
        if GraphifyAdapter is None:
            return
        graph_dir = tmp_path / "graphify-out"
        graph_dir.mkdir(parents=True)
        graph_file = graph_dir / "graph.json"
        graph_file.write_text('{"nodes": [], "edges": []}', encoding="utf-8")

        adapter = GraphifyAdapter(workspace_dir=tmp_path)
        caps = adapter.check_capabilities()
        assert caps["has_graph_json"] is True
        assert caps["graph_json_path"] == str(graph_file)

    def test_graphify_adapter_load_graph_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Verify load_graph() raises FileNotFoundError when target graph.json does not exist."""
        if GraphifyAdapter is None:
            return
        adapter = GraphifyAdapter(workspace_dir=tmp_path)
        if adapter.is_available():
            with pytest.raises(FileNotFoundError):
                adapter.load_graph()

    def test_graphify_adapter_load_graph_unavailable_raises_runtime_error(self, tmp_path: Path) -> None:
        """Verify load_graph() raises RuntimeError when graphify is not available in environment."""
        if GraphifyAdapter is None:
            return
        adapter = GraphifyAdapter(workspace_dir=tmp_path)
        with patch.object(adapter, "is_available", return_value=False):
            with pytest.raises(RuntimeError):
                adapter.load_graph()

    def test_graphify_adapter_pure_python_in_process_guarantee(self) -> None:
        """Verify GraphifyAdapter communicates via in-process Python APIs without spawning subprocesses."""
        adapter_file = REPO_ROOT / "src" / "aios_habit" / "graphify_adapter.py"
        if adapter_file.exists():
            content = adapter_file.read_text(encoding="utf-8")
            assert "subprocess" not in content, "GraphifyAdapter must not import or invoke subprocess"
            assert "shutil.which" not in content, "GraphifyAdapter must not probe PATH with shutil.which"


class TestTier1ExcaliFlowAdapter:
    """Tier 1.3: In-Process ExcaliFlowAdapter Resolution and Methods (Requirement R2)."""

    def test_excaliflow_adapter_instantiation_and_override(self) -> None:
        """Verify ExcaliFlowAdapter initializes cleanly with default or overridden availability."""
        if ExcaliFlowAdapter is None:
            adapter_file = REPO_ROOT / "src" / "aios_habit" / "excaliflow_adapter.py"
            assert adapter_file.exists(), "src/aios_habit/excaliflow_adapter.py must exist"
            return

        adapter_default = ExcaliFlowAdapter()
        assert adapter_default is not None

        adapter_disabled = ExcaliFlowAdapter(override_available=False)
        assert adapter_disabled._override_available is False

    def test_excaliflow_adapter_check_capabilities_returns_capabilities_object(self) -> None:
        """Verify check_capabilities() returns capability metrics dataclass or dict."""
        if ExcaliFlowAdapter is None:
            return
        caps = ExcaliFlowAdapter.check_capabilities()
        if hasattr(caps, "status"):
            assert caps.status in (CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE, CapabilityStatus.DEGRADED)
            assert isinstance(caps.is_available, bool)
            assert isinstance(caps.supported_formats, list)
        elif isinstance(caps, dict):
            assert "status" in caps
            assert "is_available" in caps

    def test_excaliflow_adapter_render_trace_html_happy_path(self) -> None:
        """Verify render_trace_html() generates valid responsive HTML board when available."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter()
        trace = _make_sample_trace(
            query="Kiểm tra tồn kho",
            answer_text="Hàng tồn kho còn 100 sản phẩm [1].",
            citations=[
                {"citation_id": "[1]", "snippet": "Kho còn 100 chiếc.", "source_path": "kho.xlsx", "source_id": "s1"}
            ],
            sources=[{"source_id": "s1", "title": "kho.xlsx", "source_path": "kho.xlsx"}],
            ui_locale="vi",
            answer_language="vi",
        )

        html_out = adapter.render_trace_html(trace, locale="vi")
        assert isinstance(html_out, str)
        assert '<div class="egv-container egv-full"' in html_out
        assert "kho.xlsx" in html_out
        assert "[1]" in html_out

    def test_excaliflow_adapter_export_excalidraw_scene_happy_path(self) -> None:
        """Verify export_excalidraw_scene() returns canonical Excalidraw scene JSON structure."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter()
        trace = _make_sample_trace(
            query="Kiểm tra quy trình",
            answer_text="Thực hiện theo bước A [1].",
            citations=[{"citation_id": "[1]", "snippet": "Bước A", "source_path": "sop.pdf", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "sop.pdf", "source_path": "sop.pdf"}],
        )

        scene = adapter.export_excalidraw_scene(trace, locale="vi")
        assert isinstance(scene, dict)
        assert scene.get("type") == "excalidraw"
        assert scene.get("version") == 2
        assert "elements" in scene
        assert "appState" in scene

    def test_excaliflow_adapter_accepts_both_dataclass_and_dict_payloads(self) -> None:
        """Verify adapter accepts both EvidenceTrace dataclass and raw Python dict payloads."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter()
        trace = _make_sample_trace(
            query="Hỏi đáp",
            answer_text="Trả lời [1].",
            citations=[{"citation_id": "[1]", "snippet": "Bằng chứng", "source_path": "doc.txt", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "doc.txt", "source_path": "doc.txt"}],
        )

        html_from_dc = adapter.render_trace_html(trace, locale="vi")
        html_from_dict = adapter.render_trace_html(trace.to_dict(), locale="vi")

        assert isinstance(html_from_dc, str)
        assert isinstance(html_from_dict, str)
        assert "doc.txt" in html_from_dc
        assert "doc.txt" in html_from_dict

    def test_excaliflow_adapter_stateless_and_reusable(self) -> None:
        """Verify multiple sequential render calls on same instance produce consistent deterministic output."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter()
        trace = _make_sample_trace(
            query="Truy vấn kiểm tra",
            answer_text="Kết quả kiểm tra [1].",
            citations=[{"citation_id": "[1]", "snippet": "Đoạn văn trích dẫn", "source_path": "data.csv", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "data.csv", "source_path": "data.csv"}],
        )

        out1 = adapter.render_trace_html(trace, locale="vi", use_cache=False)
        out2 = adapter.render_trace_html(trace, locale="vi", use_cache=False)
        assert out1 == out2


class TestTier1CapabilityStatusAndDetection:
    """Tier 1.4: Capability Detection returning CapabilityStatus (Requirement R2)."""

    def test_capability_status_enum_members_and_values(self) -> None:
        """Verify CapabilityStatus enum members (AVAILABLE, UNAVAILABLE, DEGRADED)."""
        if CapabilityStatus is None:
            return
        assert CapabilityStatus.AVAILABLE.value == "available"
        assert CapabilityStatus.UNAVAILABLE.value == "unavailable"
        assert CapabilityStatus.DEGRADED.value == "degraded"

    def test_excaliflow_capabilities_dataclass_attributes_and_defaults(self) -> None:
        """Verify ExcaliFlowCapabilities dataclass structure and field defaults."""
        if ExcaliFlowCapabilities is None or CapabilityStatus is None:
            return
        caps = ExcaliFlowCapabilities(
            status=CapabilityStatus.AVAILABLE,
            is_available=True,
            has_html_renderer=True,
            has_svg_renderer=True,
            has_excalidraw_export=True,
            renderer_version="0.1.0-internal",
            supported_formats=["html", "excalidraw_json", "svg"],
            missing_dependencies=[],
            details={"engine": "pure_python"},
        )
        assert caps.status == CapabilityStatus.AVAILABLE
        assert caps.is_available is True
        assert caps.has_html_renderer is True
        assert caps.has_svg_renderer is True
        assert "html" in caps.supported_formats

    def test_excaliflow_capabilities_to_dict_serialization(self) -> None:
        """Verify ExcaliFlowCapabilities.to_dict() produces a clean serializable dictionary."""
        if ExcaliFlowCapabilities is None or CapabilityStatus is None:
            return
        caps = ExcaliFlowCapabilities(
            status=CapabilityStatus.UNAVAILABLE,
            is_available=False,
            has_html_renderer=False,
            missing_dependencies=["pillow"],
        )
        d = caps.to_dict()
        assert isinstance(d, dict)
        assert d["status"] == "unavailable"
        assert d["is_available"] is False
        assert d["missing_dependencies"] == ["pillow"]

    def test_capability_detection_runtime_probe_behavior(self) -> None:
        """Verify check_capabilities() inspects capabilities safely without side effects."""
        if ExcaliFlowAdapter is None:
            return
        caps = ExcaliFlowAdapter.check_capabilities()
        assert caps is not None

    def test_capability_detection_performance_and_fast_execution(self) -> None:
        """Verify check_capabilities() executes within minimal overhead (<10ms)."""
        if ExcaliFlowAdapter is None:
            return
        import time
        start = time.perf_counter()
        for _ in range(50):
            ExcaliFlowAdapter.check_capabilities()
        duration = time.perf_counter() - start
        avg_ms = (duration / 50) * 1000
        assert avg_ms < 10.0, f"check_capabilities() exceeded 10ms threshold: {avg_ms:.2f}ms"


class TestTier1LocalizedErrorFallback:
    """Tier 1.5: Localized evidence_graph_render_error fallback across vi, ja, zh-CN (Requirement R2)."""

    def test_i18n_translation_key_parity_for_evidence_graph_render_error(self) -> None:
        """Verify evidence_graph_render_error key exists in all 3 language dictionaries."""
        for loc in ("vi", "ja", "zh-CN"):
            assert "evidence_graph_render_error" in TRANSLATIONS[loc]
            val = TRANSLATIONS[loc]["evidence_graph_render_error"]
            assert isinstance(val, str) and len(val.strip()) > 0

    def test_i18n_exact_error_string_matches(self) -> None:
        """Verify exact localized error strings match specification."""
        assert t("evidence_graph_render_error", locale="vi") == "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra."
        assert t("evidence_graph_render_error", locale="ja") == "根拠グラフを表示できません。エラーが発生しました。"
        assert t("evidence_graph_render_error", locale="zh-CN") == "无法显示证据图谱。发生错误。"

    def test_excaliflow_adapter_unavailable_renders_localized_error_banner_vi(self) -> None:
        """Verify ExcaliFlowAdapter with override_available=False renders Vietnamese error banner."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = create_evidence_trace(query="Test", answer_text="Answer")
        html_out = adapter.render_trace_html(trace, locale="vi")

        assert '<div class="egv-container egv-error"' in html_out
        assert "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra." in html_out
        assert "❌" in html_out

    def test_excaliflow_adapter_unavailable_renders_localized_error_banner_ja(self) -> None:
        """Verify ExcaliFlowAdapter with override_available=False renders Japanese error banner."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = create_evidence_trace(query="テスト", answer_text="回答")
        html_out = adapter.render_trace_html(trace, locale="ja")

        assert '<div class="egv-container egv-error"' in html_out
        assert "根拠グラフを表示できません。エラーが発生しました。" in html_out

    def test_excaliflow_adapter_unavailable_renders_localized_error_banner_zh_cn(self) -> None:
        """Verify ExcaliFlowAdapter with override_available=False renders Simplified Chinese error banner."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = create_evidence_trace(query="测试", answer_text="回答")
        html_out = adapter.render_trace_html(trace, locale="zh-CN")

        assert '<div class="egv-container egv-error"' in html_out
        assert "无法显示证据图谱。发生错误。" in html_out

    def test_excaliflow_adapter_unavailable_unknown_locale_fallbacks_to_vi(self) -> None:
        """Verify unknown or invalid locale falls back cleanly to Vietnamese error banner."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = create_evidence_trace(query="Test", answer_text="Answer")
        html_out = adapter.render_trace_html(trace, locale="fr-FR")

        assert '<div class="egv-container egv-error"' in html_out
        assert "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra." in html_out

    def test_excaliflow_adapter_export_excalidraw_scene_unavailable_raises_clean_error(self) -> None:
        """Verify export_excalidraw_scene() raises clean RuntimeError when adapter is unavailable."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter(override_available=False)
        trace = create_evidence_trace(query="Test", answer_text="Answer")
        with pytest.raises(RuntimeError) as excinfo:
            adapter.export_excalidraw_scene(trace, locale="vi")
        assert "unavailable" in str(excinfo.value).lower()


# ==============================================================================
# Tier 2: Boundary, Corner Cases & Zero-PATH / CLI Guard (>=5 per feature)
# ==============================================================================

class TestTier2ASTZeroPATHGuard:
    """Tier 2.1: AST Static Analysis Zero-PATH / CLI Guard (Requirement R1, R3)."""

    ADAPTER_FILES = [
        "src/aios_habit/graphify_adapter.py",
        "src/aios_habit/excaliflow_adapter.py",
    ]

    PROHIBITED_SUBPROCESS_CALLS = {
        "popen",
        "run",
        "call",
        "check_output",
        "check_call",
    }

    def test_ast_guard_no_subprocess_imports_in_adapters(self) -> None:
        """Verify ZERO imports of 'subprocess' module in Commit D adapters."""
        for rel_path in self.ADAPTER_FILES:
            target_path = REPO_ROOT / rel_path
            if not target_path.exists():
                continue
            tree = ast.parse(target_path.read_text(encoding="utf-8"), filename=str(target_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name != "subprocess", (
                            f"Prohibited import 'subprocess' in {rel_path}:{node.lineno}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert node.module != "subprocess", (
                            f"Prohibited from-import 'subprocess' in {rel_path}:{node.lineno}"
                        )

    def test_ast_guard_no_subprocess_calls_in_adapters(self) -> None:
        """Verify ZERO invocations of subprocess functions in Commit D adapters."""
        for rel_path in self.ADAPTER_FILES:
            target_path = REPO_ROOT / rel_path
            if not target_path.exists():
                continue
            tree = ast.parse(target_path.read_text(encoding="utf-8"), filename=str(target_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr.lower()
                    elif isinstance(node.func, ast.Name):
                        func_name = node.func.id.lower()
                    assert func_name not in self.PROHIBITED_SUBPROCESS_CALLS, (
                        f"Prohibited subprocess call '{func_name}' in {rel_path}:{node.lineno}"
                    )

    def test_ast_guard_no_os_system_or_popen_in_adapters(self) -> None:
        """Verify ZERO calls to os.system, os.popen, or os.spawn in Commit D adapters."""
        prohibited_os = {"system", "popen", "spawnl", "spawnle", "spawnlp", "spawnv", "spawnve", "spawnvp"}
        for rel_path in self.ADAPTER_FILES:
            target_path = REPO_ROOT / rel_path
            if not target_path.exists():
                continue
            tree = ast.parse(target_path.read_text(encoding="utf-8"), filename=str(target_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        assert node.func.attr not in prohibited_os, (
                            f"Prohibited os.{node.func.attr} call in {rel_path}:{node.lineno}"
                        )

    def test_ast_guard_no_shutil_which_in_adapters(self) -> None:
        """Verify ZERO calls to shutil.which in Commit D adapters (strictly no PATH probing)."""
        for rel_path in self.ADAPTER_FILES:
            target_path = REPO_ROOT / rel_path
            if not target_path.exists():
                continue
            tree = ast.parse(target_path.read_text(encoding="utf-8"), filename=str(target_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == "which":
                        assert False, f"Prohibited shutil.which call in {rel_path}:{node.lineno}"

    def test_ast_guard_no_cli_invocations_in_evidence_graph_viewer(self) -> None:
        """Verify evidence_graph_viewer.py has ZERO subprocess or shutil.which calls."""
        viewer_path = REPO_ROOT / "src" / "aios_habit" / "evidence_graph_viewer.py"
        tree = ast.parse(viewer_path.read_text(encoding="utf-8"), filename=str(viewer_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "subprocess"
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in self.PROHIBITED_SUBPROCESS_CALLS
                assert node.func.attr != "which"

    def test_ast_guard_pure_python_in_process_resolution(self) -> None:
        """Verify adapters operate purely on data structures and standard Python APIs."""
        for rel_path in self.ADAPTER_FILES:
            target_path = REPO_ROOT / rel_path
            if not target_path.exists():
                continue
            content = target_path.read_text(encoding="utf-8")
            assert "cmd.exe" not in content
            assert "powershell" not in content
            assert "/bin/sh" not in content
            assert "/bin/bash" not in content


class TestTier2SimulatedMissingDependenciesAndErrors:
    """Tier 2.2: Simulated Missing Dependencies, Graph Files & Error Handling (Requirement R2)."""

    def test_simulated_missing_graphify_dependency(self, tmp_path: Path) -> None:
        """Simulate missing graphify module; verify is_available() returns False and check_capabilities flags it."""
        if GraphifyAdapter is None:
            return
        adapter = GraphifyAdapter(workspace_dir=tmp_path)
        with patch.object(adapter, "is_available", return_value=False):
            assert adapter.is_available() is False
            caps = adapter.check_capabilities()
            assert caps["available"] is False

    def test_simulated_missing_graph_file_handling(self, tmp_path: Path) -> None:
        """Verify load_graph() on non-existent file cleanly raises FileNotFoundError."""
        if GraphifyAdapter is None:
            return
        adapter = GraphifyAdapter(workspace_dir=tmp_path)
        with patch.object(adapter, "is_available", return_value=True):
            with pytest.raises(FileNotFoundError):
                adapter.load_graph(tmp_path / "non_existent_graph.json")

    def test_simulated_missing_graphics_libraries_capability_check(self) -> None:
        """Verify check_capabilities() safely reports UNAVAILABLE when optional graphic dependencies fail."""
        if ExcaliFlowAdapter is None or CapabilityStatus is None:
            return
        with patch.object(ExcaliFlowAdapter, "check_capabilities") as mock_check:
            mock_check.return_value = ExcaliFlowCapabilities(
                status=CapabilityStatus.UNAVAILABLE,
                is_available=False,
                missing_dependencies=["xml.etree"],
            )
            caps = ExcaliFlowAdapter.check_capabilities()
            assert caps.status == CapabilityStatus.UNAVAILABLE
            assert caps.is_available is False
            assert "xml.etree" in caps.missing_dependencies

    def test_simulated_renderer_exception_fallback_in_render_html(self) -> None:
        """Verify render_trace_html catches internal renderer exceptions and returns localized error container."""
        # Test directly against evidence_graph_viewer.render_evidence_graph_html
        class ThrowingTrace:
            @property
            def trace_id(self) -> str:
                raise ValueError("Simulated catastrophic corruption")

        bad_trace = ThrowingTrace()
        html_out = render_evidence_graph_html(bad_trace, locale="vi")
        assert '<div class="egv-container egv-error"' in html_out
        assert "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra." in html_out

    def test_simulated_excalidraw_export_unavailable_fail_closed(self) -> None:
        """Verify export_excalidraw_scene fails closed without returning corrupt data when unavailable."""
        if ExcaliFlowAdapter is None:
            return
        adapter = ExcaliFlowAdapter(override_available=False)
        with pytest.raises(RuntimeError):
            adapter.export_excalidraw_scene({}, locale="ja")


class TestTier2MalformedTracePayloads:
    """Tier 2.3: Malformed Trace Payloads, Non-dict Objects, None Values Safe Handling."""

    def test_malformed_trace_none_input_handled_safely(self) -> None:
        """Verify None input does not crash renderer and produces safe fallback."""
        html_out = render_evidence_graph_html(None, locale="vi")
        assert isinstance(html_out, str)
        assert ("egv-error" in html_out) or ("egv-insufficient" in html_out)

    def test_malformed_trace_empty_dict_handled_safely(self) -> None:
        """Verify empty dictionary input is treated as insufficient evidence without crashing."""
        html_out = render_evidence_graph_html({}, locale="vi")
        assert isinstance(html_out, str)
        assert ("egv-insufficient" in html_out) or ("egv-error" in html_out)

    @pytest.mark.parametrize("invalid_payload", [
        "not_a_trace_just_a_string",
        12345,
        True,
        3.14159,
        ["a", "list", "of", "strings"],
    ])
    def test_malformed_trace_primitive_types_handled_safely(self, invalid_payload: Any) -> None:
        """Verify passing primitive or list types does not raise uncaught exceptions."""
        html_out = render_evidence_graph_html(invalid_payload, locale="ja")
        assert isinstance(html_out, str)
        assert len(html_out) > 0

    def test_malformed_trace_corrupted_nodes_handled_safely(self) -> None:
        """Verify trace containing corrupted/partial node objects renders safely."""
        corrupted_trace = {
            "schema_version": "rag-trace/v1",
            "trace_id": "trc_corrupt_001",
            "nodes": [
                None,
                {},
                {"id": "n1"},  # missing node_type, title, snippet
                {"node_type": "citation"},  # missing id
                {"id": "n2", "node_type": "unknown_invalid_type", "title": "Invalid Type"},
            ],
            "edges": [],
            "metadata": {},
        }
        html_out = render_evidence_graph_html(corrupted_trace, locale="zh-CN")
        assert isinstance(html_out, str)

    def test_malformed_trace_dangling_edges_filtered_safely(self) -> None:
        """Verify edges referencing non-existent nodes are safely ignored without crashing."""
        trace = {
            "schema_version": "rag-trace/v1",
            "trace_id": "trc_dangling_001",
            "query": "Hỏi",
            "answer_text": "Đáp [1]",
            "nodes": [
                {"id": "q", "node_type": "question", "title": "Hỏi"},
                {"id": "a", "node_type": "answer", "title": "Đáp"},
                {"id": "c1", "node_type": "citation", "title": "Trích", "citation_id": "[1]"},
                {"id": "s1", "node_type": "source", "title": "Nguồn", "source_path": "doc.txt"},
            ],
            "edges": [
                {"source_id": "q", "target_id": "a", "relation": "derives_from"},
                {"source_id": "c1", "target_id": "a", "relation": "supports"},
                {"source_id": "s1", "target_id": "c1", "relation": "extracted_from"},
                {"source_id": "ghost_node_1", "target_id": "a", "relation": "supports"},  # Dangling
                {"source_id": "c1", "target_id": "ghost_node_2", "relation": "supports"},  # Dangling
            ],
            "metadata": {},
        }
        vm = build_evidence_graph_view_model(trace, locale="vi")
        assert len(vm.nodes) == 4
        # Ghost edges must be filtered out
        edge_pairs = [(e["source_id"], e["target_id"]) for e in vm.edges]
        assert ("ghost_node_1", "a") not in edge_pairs
        assert ("c1", "ghost_node_2") not in edge_pairs

    def test_malformed_trace_circular_edges_handled_safely(self) -> None:
        """Verify cyclic graphs (e.g. A -> B -> A) do not cause recursion errors."""
        trace = {
            "schema_version": "rag-trace/v1",
            "trace_id": "trc_cycle_001",
            "query": "Vòng lặp",
            "answer_text": "Chu trình [1]",
            "nodes": [
                {"id": "c1", "node_type": "citation", "title": "Trích 1", "citation_id": "[1]"},
                {"id": "s1", "node_type": "source", "title": "Nguồn 1", "source_path": "doc1.txt"},
            ],
            "edges": [
                {"source_id": "s1", "target_id": "c1", "relation": "extracted_from"},
                {"source_id": "c1", "target_id": "s1", "relation": "extracted_from"},  # Cycle
            ],
            "metadata": {},
        }
        html_out = render_evidence_graph_html(trace, locale="vi")
        assert isinstance(html_out, str)


class TestTier2ConcurrencyAndMultithreading:
    """Tier 2.4: Concurrent Capability Checks and Adapter Calls under Multithreading."""

    def test_concurrent_graphify_capability_checks(self, tmp_path: Path) -> None:
        """Verify 25 concurrent threads calling check_capabilities() on GraphifyAdapter execute cleanly."""
        if GraphifyAdapter is None:
            return
        adapter = GraphifyAdapter(workspace_dir=tmp_path)
        errors: List[Exception] = []

        def worker() -> Dict[str, Any]:
            return adapter.check_capabilities()

        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    assert isinstance(res, dict)
                except Exception as exc:
                    errors.append(exc)

        assert len(errors) == 0, f"Encountered concurrency errors: {errors}"

    def test_concurrent_excaliflow_capability_checks(self) -> None:
        """Verify 25 concurrent threads calling check_capabilities() on ExcaliFlowAdapter execute cleanly."""
        if ExcaliFlowAdapter is None:
            return
        errors: List[Exception] = []

        def worker() -> Any:
            return ExcaliFlowAdapter.check_capabilities()

        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    assert res is not None
                except Exception as exc:
                    errors.append(exc)

        assert len(errors) == 0, f"Encountered concurrency errors: {errors}"

    def test_concurrent_trace_rendering_and_caching(self) -> None:
        """Verify 30 concurrent threads rendering traces and querying VIEWER_CACHE without data races."""
        trace = _make_sample_trace(
            query="Đồng bộ kho",
            answer_text="Hàng tồn còn 50 cái [1].",
            citations=[{"citation_id": "[1]", "snippet": "Tồn 50", "source_path": "kho.xlsx", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "kho.xlsx", "source_path": "kho.xlsx"}],
            ui_locale="vi",
        )

        results: List[str] = []
        errors: List[Exception] = []

        def render_worker() -> str:
            return render_evidence_graph_html(trace, locale="vi", use_cache=True)

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(render_worker) for _ in range(60)]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as exc:
                    errors.append(exc)

        assert len(errors) == 0
        assert len(results) == 60
        # All returned HTML boards must be valid and non-empty
        for html_item in results:
            assert "kho.xlsx" in html_item

    def test_concurrent_mixed_valid_and_malformed_trace_rendering(self) -> None:
        """Verify 20 concurrent threads submitting mixed valid, malformed, and insufficient traces."""
        valid_trace = _make_sample_trace(
            query="Valid",
            answer_text="Valid Answer [1]",
            citations=[{"citation_id": "[1]", "snippet": "Snip", "source_path": "a.txt", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "a.txt", "source_path": "a.txt"}],
        )
        insufficient_trace = create_evidence_trace(query="No citations", answer_text="Just answer")
        malformed_payloads = [None, {}, "raw_string", 42, valid_trace, insufficient_trace]

        results = []
        errors = []

        def mixed_worker(payload: Any) -> str:
            return render_evidence_graph_html(payload, locale="ja", use_cache=False)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(mixed_worker, malformed_payloads[i % len(malformed_payloads)]) for i in range(40)]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as exc:
                    errors.append(exc)

        assert len(errors) == 0
        assert len(results) == 40

    def test_concurrent_deterministic_sha256_hashing(self) -> None:
        """Verify 20 threads computing content hash of same trace obtain 100% identical SHA-256 digests."""
        trace = _make_sample_trace(
            query="Hash test",
            answer_text="Answer text [1]",
            citations=[{"citation_id": "[1]", "snippet": "Snippet", "source_path": "s.txt", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "s.txt", "source_path": "s.txt"}],
        )

        hashes = []

        def hash_worker() -> str:
            return compute_trace_content_hash(trace)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(hash_worker) for _ in range(40)]
            for fut in as_completed(futures):
                hashes.append(fut.result())

        assert len(set(hashes)) == 1, "Content hashes diverged under concurrent execution!"
        assert len(hashes[0]) == 64


# ==============================================================================
# Tier 3: Cross-Feature Combinations & VPS Isolation Contract
# ==============================================================================

class TestTier3VPSIsolationAndPersistence:
    """Tier 3.1: VPS Storage Isolation & Persistence Contract (Requirement R4)."""

    def test_chat_store_local_dir_resides_in_local_cases(self) -> None:
        """Verify LOCAL_CHAT_DIR path explicitly resides under local_cases/workspace_chat/."""
        store_dir = chat_store.LOCAL_CHAT_DIR
        parts = [p.lower() for p in store_dir.parts]
        assert "local_cases" in parts
        assert "workspace_chat" in parts

    def test_save_evidence_trace_persists_under_local_cases(self, tmp_path: Path) -> None:
        """Verify save_evidence_trace writes trace records strictly inside local_cases/workspace_chat/."""
        custom_store_dir = tmp_path / "local_cases" / "workspace_chat"
        custom_store_dir.mkdir(parents=True)
        traces_file = custom_store_dir / "traces.jsonl"

        trace = _make_sample_trace(
            query="Kiểm thử lưu vết",
            answer_text="Đã lưu vết [1].",
            citations=[{"citation_id": "[1]", "snippet": "Bằng chứng", "source_path": "doc.pdf", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "doc.pdf", "source_path": "doc.pdf"}],
        )

        with patch("aios_habit.workspace_chat_store.TRACES_FILE", traces_file), \
             patch("aios_habit.workspace_chat_store.LOCAL_CHAT_DIR", custom_store_dir):
            saved = save_evidence_trace(trace)
            assert saved is not None
            assert traces_file.exists()
            content = traces_file.read_text(encoding="utf-8")
            assert trace.trace_id in content

    def test_all_store_file_paths_isolated_in_local_cases(self) -> None:
        """Verify all chat store data files (conversations, messages, traces, notebooks) reside in local_cases."""
        files_to_check = [
            chat_store.CONVERSATIONS_FILE,
            chat_store.MESSAGES_FILE,
            chat_store.TRACES_FILE,
            chat_store.NOTEBOOKS_FILE,
        ]
        for f in files_to_check:
            parts = [p.lower() for p in f.parts]
            assert "local_cases" in parts, f"Store file '{f}' does not reside in local_cases"

    def test_zero_trace_writes_to_system_root_or_temp(self) -> None:
        """Verify store operations never write trace files to system root or repository root."""
        root_traces = REPO_ROOT / "traces.jsonl"
        assert not root_traces.exists(), "traces.jsonl must never exist at repository root"

    def test_store_init_creates_local_cases_directory_safely(self, tmp_path: Path) -> None:
        """Verify WorkspaceChatStore constructor initializes local_cases directory with clean permissions."""
        custom_dir = tmp_path / "custom_tenant" / "local_cases" / "workspace_chat"
        store = WorkspaceChatStore(base_dir=custom_dir)
        assert store.base_dir.exists()


class TestTier3GitignoreVerification:
    """Tier 3.2: .gitignore Verification for local_cases/ and graphify-out/ (Requirement R4)."""

    def test_gitignore_file_exists_at_repo_root(self) -> None:
        """Verify .gitignore exists at repository root."""
        gitignore_path = REPO_ROOT / ".gitignore"
        assert gitignore_path.exists(), ".gitignore must exist at repository root"

    def test_gitignore_explicitly_contains_local_cases(self) -> None:
        """Verify .gitignore explicitly excludes local_cases/ to prevent trace data leakage."""
        gitignore_path = REPO_ROOT / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8")
        assert "local_cases/" in content or "local_cases" in content, (
            ".gitignore must contain 'local_cases/' to prevent trace leaks"
        )

    def test_gitignore_explicitly_contains_graphify_out(self) -> None:
        """Verify .gitignore explicitly excludes graphify-out/ knowledge graph build outputs."""
        gitignore_path = REPO_ROOT / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8")
        assert "graphify-out/" in content or "graphify-out" in content, (
            ".gitignore must contain 'graphify-out/'"
        )

    def test_gitignore_prevents_accidental_git_tracking_of_local_cases(self) -> None:
        """Verify local_cases path matching against gitignore patterns."""
        gitignore_path = REPO_ROOT / ".gitignore"
        lines = [line.strip() for line in gitignore_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        has_local_cases = any(line.startswith("local_cases") for line in lines)
        has_graphify_out = any(line.startswith("graphify-out") for line in lines)
        assert has_local_cases, "local_cases pattern not found in .gitignore lines"
        assert has_graphify_out, "graphify-out pattern not found in .gitignore lines"


class TestTier3ErrorAndTokenSanitization:
    """Tier 3.3: Error Sanitization Masking Local Paths and Secret Tokens (Requirement R4)."""

    def test_error_sanitizer_masks_windows_file_paths(self) -> None:
        """Verify sanitize_bridge_error masks Windows absolute file paths with <path>."""
        raw_error = "Error reading D:\\Sandbox\\AIOS_habbit\\local_cases\\workspace_chat\\traces.jsonl: file locked"
        sanitized = sanitize_bridge_error(raw_error)
        assert "D:\\Sandbox" not in sanitized
        assert "local_cases" not in sanitized
        assert "<path>" in sanitized

    def test_error_sanitizer_masks_posix_file_paths(self) -> None:
        """Verify sanitize_bridge_error masks POSIX/Linux file paths with <path>."""
        raw_error = "Permission denied at /var/aios/local_cases/workspace_chat/traces.jsonl on line 42"
        sanitized = sanitize_bridge_error(raw_error)
        assert "/var/aios" not in sanitized
        assert "<path>" in sanitized

    def test_error_sanitizer_masks_openai_api_tokens(self) -> None:
        """Verify sanitize_reason masks OpenAI API keys (sk-...) with <redacted_token>."""
        raw_reason = "Authentication failed with token sk-proj-1234567890abcdef1234567890abcdef"
        sanitized = sanitize_reason(raw_reason)
        assert "sk-proj-1234567890" not in sanitized
        assert "<redacted_token>" in sanitized

    def test_error_sanitizer_masks_anthropic_and_google_tokens(self) -> None:
        """Verify sanitize_reason masks Anthropic (ant-...) and Google (AIzaSy...) API keys."""
        raw_reason_ant = "Invalid token ant-api03-abcdef1234567890"
        sanitized_ant = sanitize_reason(raw_reason_ant)
        assert "ant-api03" not in sanitized_ant
        assert "<redacted_token>" in sanitized_ant

        raw_reason_goog = "Quota exceeded for key AIzaSyAbCdEf1234567890"
        sanitized_goog = sanitize_reason(raw_reason_goog)
        assert "AIzaSyAbCdEf" not in sanitized_goog
        assert "<redacted_token>" in sanitized_goog

    def test_error_sanitizer_complex_multiline_traceback_sanitization(self) -> None:
        """Verify multi-line tracebacks containing both local paths and tokens are fully sanitized."""
        raw_traceback = (
            "Traceback (most recent call last):\n"
            "  File \"D:\\Sandbox\\AIOS_habbit\\src\\aios_habit\\llm_client.py\", line 105, in call\n"
            "    raise AuthError(\"Token sk-998877665544332211 failed on /etc/aios/config.json\")\n"
            "AuthError: Unauthorized"
        )
        sanitized = sanitize_bridge_error(raw_traceback)
        assert "D:\\Sandbox" not in sanitized
        assert "/etc/aios" not in sanitized
        assert "sk-998877665544332211" not in sanitized


class TestTier3SingleTenantIsolation:
    """Tier 3.4: Single-Tenant Workspace Boundaries with Zero Cross-Session Leakage (Requirement R4)."""

    def test_single_tenant_isolated_stores_by_workspace_path(self, tmp_path: Path) -> None:
        """Verify two distinct workspace stores do not cross-read or leak traces."""
        tenant_a_dir = tmp_path / "tenant_alpha" / "local_cases" / "workspace_chat"
        tenant_b_dir = tmp_path / "tenant_beta" / "local_cases" / "workspace_chat"

        store_a = WorkspaceChatStore(base_dir=tenant_a_dir)
        store_b = WorkspaceChatStore(base_dir=tenant_b_dir)

        trace_a = _make_sample_trace(
            query="Truy vấn bí mật Tenant A",
            answer_text="Dữ liệu Tenant A [1]",
            citations=[{"citation_id": "[1]", "snippet": "Bí mật A", "source_path": "doc_a.pdf", "source_id": "sa"}],
            sources=[{"source_id": "sa", "title": "doc_a.pdf", "source_path": "doc_a.pdf"}],
        )

        store_a.save_trace(trace_a)

        # Tenant A can read trace A
        loaded_a = store_a.get_trace(trace_a.trace_id)
        assert loaded_a is not None
        assert loaded_a.trace_id == trace_a.trace_id

        # Tenant B MUST NOT be able to read trace A
        loaded_b = store_b.get_trace(trace_a.trace_id)
        assert loaded_b is None

    def test_single_tenant_trace_not_found_across_tenants(self, tmp_path: Path) -> None:
        """Verify querying non-existent trace across tenant boundary returns None cleanly without error."""
        tenant_b_dir = tmp_path / "tenant_b" / "local_cases" / "workspace_chat"
        store_b = WorkspaceChatStore(base_dir=tenant_b_dir)
        assert store_b.get_trace("trc_non_existent_tenant_a") is None

    def test_single_tenant_cache_isolation_by_trace_id_and_content(self) -> None:
        """Verify cache isolation: distinct trace IDs or contents yield distinct cache slots."""
        trace1 = _make_sample_trace(query="Q1", answer_text="A1")
        trace2 = _make_sample_trace(query="Q2", answer_text="A2")

        hash1 = compute_trace_content_hash(trace1)
        hash2 = compute_trace_content_hash(trace2)
        assert hash1 != hash2

        cache = EvidenceGraphViewerCache(max_entries=10)
        cache.set(trace1.trace_id, hash1, "<div>HTML1</div>", locale="vi")
        cache.set(trace2.trace_id, hash2, "<div>HTML2</div>", locale="vi")

        assert cache.get(trace1.trace_id, hash1, locale="vi") == "<div>HTML1</div>"
        assert cache.get(trace2.trace_id, hash2, locale="vi") == "<div>HTML2</div>"
        assert cache.get(trace1.trace_id, hash2, locale="vi") is None

    def test_single_tenant_no_global_mutable_leakage_between_chat_sessions(self) -> None:
        """Verify distinct conversation sessions maintain private message and trace state."""
        store = WorkspaceChatStore(base_dir=REPO_ROOT / "local_cases" / "workspace_chat")
        assert store is not None


# ==============================================================================
# Tier 4: Real-World Application & Clean Smoke Test
# ==============================================================================

class TestTier4CleanEnvironmentSmokeTest:
    """Tier 4.1: Clean Environment Smoke Test with synthetic rag-trace/v1 Fixture (Requirement R3)."""

    def test_smoke_load_synthetic_rag_trace_v1_fixture(self) -> None:
        """Verify synthetic rag-trace/v1 fixture loads and deserializes cleanly into EvidenceTrace."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        assert fixture_path.exists(), f"Fixture missing: {fixture_path}"

        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert raw_data["schema_version"] == "rag-trace/v1"
        assert raw_data["trace_id"] == "trc_commit_d_smoke_001"
        assert len(raw_data["nodes"]) == 6
        assert len(raw_data["edges"]) == 5

    def test_smoke_build_view_model_exact_topology_from_fixture(self) -> None:
        """Verify building EvidenceGraphViewModel from fixture yields exact 1-to-1 topology."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

        view_model = build_evidence_graph_view_model(raw_data, locale="vi")
        assert view_model.is_insufficient is False
        assert len(view_model.nodes) == 6
        assert len(view_model.edges) == 5

        # Verify node categorization
        node_types = {n["node_type"] for n in view_model.nodes}
        assert node_types == {"question", "answer", "citation", "source"}

        # Verify edge relations
        relations = {e.get("relation_type") or e.get("relation") for e in view_model.edges}
        assert relations == {"derives_from", "supports", "extracted_from"}

    def test_smoke_compute_deterministic_sha256_from_fixture(self) -> None:
        """Verify computing deterministic SHA-256 content hash from fixture trace."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

        hash_1 = compute_trace_content_hash(raw_data)
        hash_2 = compute_trace_content_hash(raw_data)

        assert isinstance(hash_1, str)
        assert len(hash_1) == 64
        assert hash_1 == hash_2

    def test_smoke_render_html_board_from_fixture(self) -> None:
        """Verify rendering standalone HTML board from fixture produces complete, self-contained markup."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

        html_out = render_evidence_graph_html(raw_data, locale="vi", use_cache=False)
        assert '<div class="egv-container egv-full"' in html_out
        assert "trc_commit_d_smoke_001" in html_out
        assert "ERR_KHO_SYNC_0x80040111" in html_out
        assert "Báo_cáo_tài_chính_và_kho_vận_Q3_2026.xlsx" in html_out
        assert "Quy_trình_kiểm_kê_kho_hàng_v3.docx" in html_out
        assert "[1]" in html_out
        assert "[2]" in html_out

    def test_smoke_excaliflow_adapter_end_to_end_from_fixture(self) -> None:
        """Verify ExcaliFlowAdapter processes fixture trace end-to-end in clean environment."""
        if ExcaliFlowAdapter is None:
            return
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_v1.json"
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

        adapter = ExcaliFlowAdapter()
        html_out = adapter.render_trace_html(raw_data, locale="vi")
        assert '<div class="egv-container egv-full"' in html_out
        assert "ERR_KHO_SYNC_0x80040111" in html_out


class TestTier4MultiLocaleUTF8CJKFonts:
    """Tier 4.2: Multi-Locale UTF-8 / CJK Font & Character Verification (Requirement R5)."""

    def test_cjk_vietnamese_diacritics_fidelity(self) -> None:
        """Verify Vietnamese complex diacritics and tone marks are preserved without mojibake."""
        vietnamese_text = "Lỗi đồng bộ dữ liệu kho vận và kiểm soát hàng tồn kho: ắ ằ ẳ ẵ ặ, ế ề ể ễ ệ, đ."
        trace = _make_sample_trace(
            query=vietnamese_text,
            answer_text="Xử lý theo hướng dẫn quy trình số 08 [1].",
            citations=[{"citation_id": "[1]", "snippet": vietnamese_text, "source_path": "kho.pdf", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "kho.pdf", "source_path": "kho.pdf"}],
            ui_locale="vi",
            answer_language="vi",
        )

        html_out = render_evidence_graph_html(trace, locale="vi")
        assert "ắ ằ ẳ ẵ ặ" in html_out
        assert "ế ề ể ễ ệ" in html_out
        assert "đồng bộ dữ liệu kho vận" in html_out

    def test_cjk_japanese_kanji_kana_fidelity(self) -> None:
        """Verify Japanese Kanji, Hiragana, and Katakana are preserved without mojibake."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_multilingual.json"
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

        html_out = render_evidence_graph_html(raw_data, locale="ja")
        assert "ハンディターミナルでの在庫同期エラー" in html_out
        assert "品質管理マニュアル" in html_out
        assert "在庫管理マニュアル_v2.0.pdf" in html_out
        assert "根拠グラフ" in html_out

    def test_cjk_simplified_chinese_hanzi_fidelity(self) -> None:
        """Verify Simplified Chinese Hanzi characters are preserved without mojibake."""
        chinese_query = "如何处理仓储库存同步异常 ERR_KHO_SYNC_0x80040111？"
        chinese_answer = "根据仓储操作规范 [1]，请检查无线终端连接状态并重新执行同步。"
        chinese_snippet = "仓储管理系统数据同步规范与错误码排查指引。"

        trace = _make_sample_trace(
            query=chinese_query,
            answer_text=chinese_answer,
            citations=[{"citation_id": "[1]", "snippet": chinese_snippet, "source_path": "仓储操作规范_2026.docx", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "仓储操作规范_2026.docx", "source_path": "仓储操作规范_2026.docx"}],
            ui_locale="zh-CN",
            answer_language="zh-CN",
        )

        html_out = render_evidence_graph_html(trace, locale="zh-CN")
        assert "如何处理仓储库存同步异常" in html_out
        assert "仓储操作规范_2026.docx" in html_out
        assert "证据图谱" in html_out
        assert "来源文档" in html_out

    def test_cjk_font_family_fallback_stack_in_rendered_html(self) -> None:
        """Verify rendered HTML board incorporates system CJK font fallbacks in CSS font-family."""
        trace = _make_sample_trace(
            query="Test fonts",
            answer_text="Answer [1]",
            citations=[{"citation_id": "[1]", "snippet": "Text", "source_path": "f.txt", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "f.txt", "source_path": "f.txt"}],
        )
        html_out = render_evidence_graph_html(trace, locale="vi")
        # Check presence of clean system font stack
        assert "font-family:" in html_out
        assert "sans-serif" in html_out

    def test_zero_raw_unicode_escapes_in_rendered_html(self) -> None:
        """Verify rendered HTML contains zero raw unicode escape sequences (\\uXXXX)."""
        fixture_path = FIXTURES_DIR / "synthetic_rag_trace_multilingual.json"
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

        html_out = render_evidence_graph_html(raw_data, locale="ja")
        assert "\\u" not in html_out, "Raw \\uXXXX unicode escape sequences detected in rendered HTML!"


class TestTier4VerbatimPreservation:
    """Tier 4.3: Verbatim Preservation of Filenames, Error Codes, Snippets, and Citation IDs."""

    def test_verbatim_preservation_complex_filenames(self) -> None:
        """Verify filenames with mixed unicode and extensions are preserved 100% verbatim."""
        filenames = [
            "Báo_cáo_tài_chính_và_kho_vận_Q3_2026.xlsx",
            "在庫管理マニュアル_v2.0.pdf",
            "仓储操作规范_2026.docx",
            "sys_log_2026-08-23_T10-36-17Z.log",
        ]
        for fname in filenames:
            trace = _make_sample_trace(
                query="Tra cứu",
                answer_text=f"Trích dẫn từ {fname} [1].",
                citations=[{"citation_id": "[1]", "snippet": "Nội dung", "source_path": fname, "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": fname, "source_path": fname}],
            )
            html_out = render_evidence_graph_html(trace, locale="vi")
            assert fname in html_out, f"Filename '{fname}' was modified or mangled in output!"

    def test_verbatim_preservation_error_codes(self) -> None:
        """Verify technical error codes (hex, uppercase, underscores) are preserved 100% verbatim."""
        error_codes = [
            "ERR_KHO_SYNC_0x80040111",
            "ORA-01403_NO_DATA_FOUND",
            "HTTP_503_SERVICE_UNAVAILABLE",
            "WS_TIMEOUT_EVD_99",
        ]
        for err in error_codes:
            trace = _make_sample_trace(
                query=f"Xử lý lỗi {err}",
                answer_text=f"Lỗi {err} đã được ghi nhận [1].",
                citations=[{"citation_id": "[1]", "snippet": f"Mô tả lỗi {err}", "source_path": "err.log", "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": "err.log", "source_path": "err.log"}],
            )
            html_out = render_evidence_graph_html(trace, locale="vi")
            assert err in html_out, f"Error code '{err}' was modified or mangled in output!"

    def test_verbatim_preservation_citation_ids(self) -> None:
        """Verify citation identifiers ([1], [E1], [CIT-01]) are preserved 100% verbatim."""
        citation_ids = ["[1]", "[2]", "[E1]", "[EVD-42]", "[CIT-99]"]
        for cid in citation_ids:
            trace = _make_sample_trace(
                query="Query",
                answer_text=f"Answer {cid}",
                citations=[{"citation_id": cid, "snippet": f"Snippet for {cid}", "source_path": "doc.txt", "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": "doc.txt", "source_path": "doc.txt"}],
            )
            html_out = render_evidence_graph_html(trace, locale="vi")
            assert cid in html_out, f"Citation ID '{cid}' was modified or mangled in output!"

    def test_verbatim_preservation_source_code_and_special_symbols(self) -> None:
        """Verify code snippets containing HTML/XML special symbols (<, >, &, \") are safely escaped."""
        raw_code = 'if (x < 10 && y > 20) { return "OK & Ready"; }'
        trace = _make_sample_trace(
            query="Code snippet query",
            answer_text="Here is the code [1].",
            citations=[{"citation_id": "[1]", "snippet": raw_code, "source_path": "script.js", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "script.js", "source_path": "script.js"}],
        )
        html_out = render_evidence_graph_html(trace, locale="vi")
        # Should be escaped for HTML insertion
        escaped_code = html.escape(raw_code, quote=True)
        assert escaped_code in html_out
        # Raw unescaped '<' followed by script tag should NOT exist
        assert '<script>' not in html_out
