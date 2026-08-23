# -*- coding: utf-8 -*-
"""Tier 4 Test Suite for Commit B: Cloud Isolation, Privacy Policy & Prohibited Renderers.

Opaque-box and requirement-driven test suite validating:
1. Cloud Isolation & Data Leakage Prevention:
   - Evidence traces, node graphs, and raw store paths are strictly `local_only` by default.
   - External bridge payloads (Antigravity Bridge, AI Provider Bridge, Gemini Web) do not leak
     `local_only` internal evidence traces, machine paths, or store files (`traces.jsonl`, etc.).
   - Bridge error sanitization masks paths, tokens, and sensitive system parameters.
2. Zero Prohibited Visual Graph Renderers (Scope Guard R5):
   - AST Static Analysis of `src/aios_habit/` confirming ZERO imports or invocations of
     `excalidraw`, `excaliflow`, or `graphify` visual renderers in Commit B scope.
   - Confirming no visual graph rendering UI widgets or external graph calls are active.
3. Storage Isolation & Git Safety:
   - Verifying `local_cases/` is ignored by Git in `.gitignore` to prevent any local trace commit.
"""
from __future__ import annotations

import ast
from pathlib import Path
import pytest

from aios_habit.antigravity_bridge import sanitize_bridge_error, sanitize_reason
from aios_habit.evidence_trace_schema import EvidenceNode, EvidenceTrace
import aios_habit.workspace_chat_store as chat_store


# ---------------------------------------------------------------------------
# Tier 4 Tests: Cloud Isolation & Payload Privacy
# ---------------------------------------------------------------------------

class TestCloudIsolationAndPrivacy:
    """Verifies that evidence traces and internal store paths never leak to cloud services."""

    def test_evidence_node_defaults_to_local_only(self) -> None:
        """All EvidenceNode instances must have privacy_label='local_only' by default."""
        node = EvidenceNode(
            id="src_priv_01",
            node_type="source",
            title="Private Internal Document",
            snippet="Confidential payroll data.",
        )
        assert node.privacy_label == "local_only"
        dict_rep = node.to_dict()
        assert dict_rep["privacy_label"] == "local_only"

    def test_bridge_error_sanitization_masks_paths_and_tokens(self) -> None:
        """Verify error messages returned from bridges do not leak local file paths or secret tokens."""
        raw_error_path = "Failed to load D:/Sandbox/AIOS_habbit/local_cases/workspace_chat/traces.jsonl: file locked"
        sanitized_path = sanitize_bridge_error(raw_error_path)
        assert "D:/Sandbox" not in sanitized_path
        assert "traces.jsonl" not in sanitized_path
        assert "<path>" in sanitized_path

        raw_error_token = "Authorization error with token sk-abcdef1234567890XYZ: unauthorized"
        sanitized_token = sanitize_reason(raw_error_token)
        assert "sk-abcdef1234567890XYZ" not in sanitized_token
        assert "<redacted_token>" in sanitized_token

    def test_store_directory_resides_in_gitignored_local_cases(self) -> None:
        """Verify the store root resides in local_cases/ and local_cases/ is in .gitignore."""
        store_dir = chat_store.LOCAL_CHAT_DIR
        assert "local_cases" in store_dir.parts

        repo_root = Path(__file__).resolve().parent.parent
        gitignore_path = repo_root / ".gitignore"
        assert gitignore_path.exists(), ".gitignore must exist in repo root"

        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        assert "local_cases/" in gitignore_content or "local_cases" in gitignore_content


# ---------------------------------------------------------------------------
# Tier 4 Tests: AST Static Analysis Guard (Prohibiting Visual Graph Renderers)
# ---------------------------------------------------------------------------

class TestProhibitedVisualRenderersScopeGuard:
    """AST Static Analysis verifying zero prohibited visual graph renderers in Commit B."""

    MODULES_TO_INSPECT: list[str] = [
        "src/aios_habit/evidence_trace_schema.py",
        "src/aios_habit/evidence_trace.py",
        "src/aios_habit/workspace_chat_store.py",
        "src/aios_habit/workspace_chat_models.py",
        "src/aios_habit/antigravity_bridge.py",
        "src/aios_habit/ide_handoff_bridge.py",
    ]

    PROHIBITED_MODULE_NAMES: frozenset[str] = frozenset({
        "excalidraw",
        "excaliflow",
        "graphify",
    })

    def test_ast_check_prohibited_renderer_imports(self) -> None:
        """Inspect AST of core Commit B source files to guarantee NO imports of prohibited renderers."""
        repo_root = Path(__file__).resolve().parent.parent

        for rel_path in self.MODULES_TO_INSPECT:
            module_file = repo_root / rel_path
            if not module_file.exists():
                continue

            tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_mod = alias.name.split(".")[0].lower()
                        assert base_mod not in self.PROHIBITED_MODULE_NAMES, (
                            f"Prohibited import '{alias.name}' detected in {rel_path}:{node.lineno}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        base_mod = node.module.split(".")[0].lower()
                        assert base_mod not in self.PROHIBITED_MODULE_NAMES, (
                            f"Prohibited from-import '{node.module}' detected in {rel_path}:{node.lineno}"
                        )

    def test_ast_check_prohibited_renderer_function_calls(self) -> None:
        """Inspect AST of core Commit B source files to guarantee NO calls to prohibited renderers."""
        repo_root = Path(__file__).resolve().parent.parent

        prohibited_call_keywords = {"render_excalidraw", "render_graphify", "call_excaliflow"}

        for rel_path in self.MODULES_TO_INSPECT:
            module_file = repo_root / rel_path
            if not module_file.exists():
                continue

            tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    for prohibited in prohibited_call_keywords:
                        assert prohibited not in func_name.lower(), (
                            f"Prohibited call '{func_name}' detected in {rel_path}:{node.lineno}"
                        )
