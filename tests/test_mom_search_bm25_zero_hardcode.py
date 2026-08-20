from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# AST Helper Utilities
# ---------------------------------------------------------------------------

def _load_ast(rel_path: str) -> ast.AST:
    file_path = PROJECT_ROOT / rel_path
    assert file_path.exists(), f"Target file not found: {file_path}"
    source = file_path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(file_path))


def _find_all_names_and_strings(tree: ast.AST) -> tuple[set[str], set[str], list[float]]:
    names: set[str] = set()
    strings: set[str] = set()
    numbers: list[float] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                strings.add(node.value)
            elif isinstance(node.value, (int, float)):
                numbers.append(float(node.value))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
                numbers.append(-float(node.operand.value))

    return names, strings, numbers


# ---------------------------------------------------------------------------
# R1: Zero Hardcode & Pure BM25 in mom_local_index.py
# ---------------------------------------------------------------------------

def test_ast_mom_local_index_zero_hardcoded_terms():
    """Verify mom_local_index.py contains 0 occurrences of q1_terms, q2_terms, q3_terms."""
    tree = _load_ast("src/aios_habit/mom_local_index.py")
    names, strings, _ = _find_all_names_and_strings(tree)

    forbidden_identifiers = {"q1_terms", "q2_terms", "q3_terms", "q1", "q2", "q3"}
    matched_names = names.intersection(forbidden_identifiers)
    assert not matched_names, f"Forbidden hardcoded term identifiers found in AST names: {matched_names}"

    for s in strings:
        s_lower = s.lower()
        assert "q1_terms" not in s_lower, f"Forbidden substring 'q1_terms' in string constant: {s}"
        assert "q2_terms" not in s_lower, f"Forbidden substring 'q2_terms' in string constant: {s}"
        assert "q3_terms" not in s_lower, f"Forbidden substring 'q3_terms' in string constant: {s}"


def test_ast_mom_local_index_zero_file_penalties():
    """Verify mom_local_index.py contains 0 file penalties (-50.0) or target doc penalties."""
    tree = _load_ast("src/aios_habit/mom_local_index.py")
    _, strings, numbers = _find_all_names_and_strings(tree)

    assert -50.0 not in numbers, "Forbidden penalty value -50.0 found in numeric constants of mom_local_index.py"
    assert -50 not in numbers, "Forbidden penalty value -50 found in numeric constants of mom_local_index.py"

    for s in strings:
        assert "erd_kho_van_new.html" not in s, f"Targeted file hardcoding 'erd_kho_van_new.html' found in strings: {s}"


def test_mom_local_index_search_bm25_functional(tmp_path, monkeypatch):
    """Functional verification of objective BM25 search ranking without heuristics."""
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_local_index import (
        MomChunk,
        MomSearchHit,
        build_mom_local_index,
        search_mom_index,
    )

    doc_dir = tmp_path / "mom_docs"
    doc_dir.mkdir()

    (doc_dir / "assembly_guide.md").write_text(
        "Standard operating procedure for production assembly lines. "
        "Steps for checking components and mounting parts on conveyors.",
        encoding="utf-8",
    )
    (doc_dir / "inventory_policy.md").write_text(
        "Warehouse inventory policy. Material safety stock and buffer limits for raw goods.",
        encoding="utf-8",
    )
    (doc_dir / "qa_checklist.md").write_text(
        "Quality assurance checklist for final inspection before shipping.",
        encoding="utf-8",
    )

    build_res = build_mom_local_index(doc_dir)
    assert build_res.root_exists is True
    assert build_res.chunks_generated >= 3

    hits = search_mom_index("assembly line procedure", limit=3)
    assert len(hits) >= 1
    assert "assembly_guide.md" in hits[0].chunk.relative_path
    assert hits[0].score > 0.0
    assert all(h.score >= 0.0 for h in hits)

    # Search for Chinese / Japanese / Korean terms
    (doc_dir / "cjk_spec.md").write_text(
        "自動化工程 仕様書 製造履歴 登録手順",
        encoding="utf-8",
    )
    build_mom_local_index(doc_dir)

    cjk_hits = search_mom_index("製造履歴", limit=3)
    assert len(cjk_hits) >= 1
    assert "cjk_spec.md" in cjk_hits[0].chunk.relative_path


# ---------------------------------------------------------------------------
# R2: Excel Streaming Chunking Defaults in excel_extractors.py
# ---------------------------------------------------------------------------

def test_ast_excel_extractors_default_limits_none():
    """Verify AST defaults in ExcelExtractionConfig have max_rows_per_sheet and max_non_empty_cells set to None."""
    tree = _load_ast("src/aios_habit/excel_extractors.py")

    config_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ExcelExtractionConfig":
            config_class = node
            break

    assert config_class is not None, "ExcelExtractionConfig class definition not found in AST"

    field_defaults: dict[str, Any] = {}
    for item in config_class.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            val = None
            if item.value is not None:
                if isinstance(item.value, ast.Constant):
                    val = item.value.value
            field_defaults[item.target.id] = val

    assert "max_rows_per_sheet" in field_defaults, "max_rows_per_sheet field missing from ExcelExtractionConfig"
    assert field_defaults["max_rows_per_sheet"] is None, (
        f"max_rows_per_sheet default must be None, got: {field_defaults['max_rows_per_sheet']}"
    )

    assert "max_non_empty_cells" in field_defaults, "max_non_empty_cells field missing from ExcelExtractionConfig"
    assert field_defaults["max_non_empty_cells"] is None, (
        f"max_non_empty_cells default must be None, got: {field_defaults['max_non_empty_cells']}"
    )

    assert field_defaults.get("enable_row_chunking") is True, "enable_row_chunking must default to True"
    assert field_defaults.get("repeat_headers_in_chunks") is True, "repeat_headers_in_chunks must default to True"
    assert field_defaults.get("chunk_row_size") == 500, "chunk_row_size must default to 500"


def test_runtime_excel_extraction_config_defaults():
    """Verify runtime instantiation of ExcelExtractionConfig has None limits and streaming enabled."""
    from aios_habit.excel_extractors import ExcelExtractionConfig

    cfg = ExcelExtractionConfig()
    assert cfg.max_rows_per_sheet is None
    assert cfg.max_non_empty_cells is None
    assert cfg.enable_row_chunking is True
    assert cfg.repeat_headers_in_chunks is True
    assert cfg.chunk_row_size == 500


# ---------------------------------------------------------------------------
# R3: Zero POLISHED_ANSWERS & Canned Dictionaries in scripts/
# ---------------------------------------------------------------------------

def test_ast_scripts_zero_polished_answers():
    """Verify scripts/generate_ai_grounded_report.py and run_workspace_chat_12_questions.py have 0 POLISHED_ANSWERS."""
    target_scripts = [
        "scripts/generate_ai_grounded_report.py",
        "scripts/run_workspace_chat_12_questions.py",
    ]

    for script_rel in target_scripts:
        tree = _load_ast(script_rel)
        names, strings, _ = _find_all_names_and_strings(tree)

        assert "POLISHED_ANSWERS" not in names, (
            f"Forbidden identifier POLISHED_ANSWERS found in AST names of {script_rel}"
        )
        assert not any("POLISHED_ANSWERS" in s for s in strings), (
            f"Forbidden string literal POLISHED_ANSWERS found in {script_rel}"
        )


def test_claim_guard_and_dynamic_abstention():
    """Verify dynamic abstention governance via ClaimGuard."""
    from aios_habit.claim_guard import evaluate_claim_readiness

    readiness = evaluate_claim_readiness(
        test_scope="narrow MOM test",
        corpus_domains=["mom"],
        answer_quality="fail",
        model_used="deterministic",
        human_review_status="pending",
        claim_type="general_notebooklm_replacement",
    )
    assert readiness.allowed is False
    assert len(readiness.reasons) >= 1
