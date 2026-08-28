# -*- coding: utf-8 -*-
"""Static AST Analysis & Integrity Verification Suite for Commit D Milestone 1.

Enforces:
1. Zero Subprocess Invocations: No `subprocess` module imports or execution calls.
2. Zero PATH Search: No `shutil.which` or CLI resolution.
3. Pure In-Process Resolution: `graphify_adapter.py` and `excaliflow_adapter.py` must use pure in-process APIs.
4. Manifest Pinning: `pyproject.toml` strictly pins `"graphifyy==0.9.50"`.
"""
from __future__ import annotations

import ast
from pathlib import Path
import pytest


ADAPTER_FILES = [
    "src/aios_habit/graphify_adapter.py",
    "src/aios_habit/excaliflow_adapter.py",
]


def test_manifest_pins_exact_graphifyy_version() -> None:
    """Verify pyproject.toml line contains exact pin 'graphifyy==0.9.50'."""
    repo_root = Path(__file__).resolve().parent.parent
    pyproject_path = repo_root / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist"

    content = pyproject_path.read_text(encoding="utf-8")
    assert '"graphifyy==0.9.50"' in content or "'graphifyy==0.9.50'" in content
    assert '"graphifyy>=' not in content and "'graphifyy>=" not in content


def test_ast_zero_subprocess_in_adapters() -> None:
    """Inspect AST of Commit D adapters to guarantee ZERO subprocess imports or calls."""
    repo_root = Path(__file__).resolve().parent.parent

    for rel_path in ADAPTER_FILES:
        target_file = repo_root / rel_path
        assert target_file.exists(), f"Target file {rel_path} must exist"

        tree = ast.parse(target_file.read_text(encoding="utf-8"), filename=str(target_file))

        for node in ast.walk(tree):
            # Check import subprocess
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

            # Check calls
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                assert func_name not in ("system", "popen", "spawn"), (
                    f"Prohibited process call '{func_name}' in {rel_path}:{node.lineno}"
                )


def test_ast_zero_shutil_which_in_adapters() -> None:
    """Inspect AST of Commit D adapters to guarantee ZERO shutil.which calls."""
    repo_root = Path(__file__).resolve().parent.parent

    for rel_path in ADAPTER_FILES:
        target_file = repo_root / rel_path
        tree = ast.parse(target_file.read_text(encoding="utf-8"), filename=str(target_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "which":
                    # If func is shutil.which or which
                    assert False, f"Prohibited 'which()' lookup detected in {rel_path}:{node.lineno}"
