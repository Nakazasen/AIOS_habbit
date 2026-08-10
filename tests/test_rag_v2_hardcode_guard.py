"""Regression guard against corpus-specific logic in the active RAG v2 core."""
from __future__ import annotations

import ast
from pathlib import Path

import aios_habit


FORBIDDEN_LITERALS = (
    "manualshipping",
    "kdcrenameshipchangeqty",
    "named_procedure",
    "named_query_equivalent",
    "opcenter",
    "cnmom",
    "t_parts",
    "revup",
    "生産履歴",
    "供給指示",
    "払出先情報",
    "棚番情報",
    "出庫処理",
)
SEMANTIC_NAME_PARTS = ("cue", "keyword", "equivalent", "synonym", "intent", "obligation")
ALLOWED_MODULE_COLLECTIONS = {
    "_answer_shape_markers",
    "_canonical_privacy_labels",
    "_common_stopwords",
    "_repairable_provider_validation_errors",
    "_soft_warning_reason_codes",
    "job_statuses",
    "active_statuses",
    "terminal_statuses",
}
QUARANTINED_IMPORT_PREFIXES = (
    "aios_habit.query_intent",
    "aios_habit.domain_playbooks",
    "aios_habit.rag_search",
    "aios_habit.mom_local_index",
    "aios_habit.workspace_chat",
)


def _module_collection_size(node: ast.AST) -> int | None:
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        return len(node.elts)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in {"set", "frozenset", "tuple", "list"} and node.args:
            return _module_collection_size(node.args[0])
    if isinstance(node, ast.Dict):
        return len(node.keys)
    return None


def test_rag_v2_core_has_no_hardcoded_business_logic():
    rag_v2_dir = Path(aios_habit.__file__).resolve().parent / "rag_v2"
    python_files = sorted(rag_v2_dir.rglob("*.py"))
    assert python_files, "Expected Python files in rag_v2 package"

    violations: list[str] = []
    for filepath in python_files:
        source = filepath.read_text(encoding="utf-8-sig")
        lowered = source.casefold()
        for literal in FORBIDDEN_LITERALS:
            if literal.casefold() in lowered:
                violations.append(f"{filepath}: forbidden benchmark literal {literal!r}")

        tree = ast.parse(source, filename=str(filepath))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""]
            else:
                continue
            for module_name in imported:
                if module_name.startswith(QUARANTINED_IMPORT_PREFIXES):
                    violations.append(
                        f"{filepath}:{node.lineno}: quarantined legacy import {module_name!r}"
                    )

        for statement in tree.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            value = statement.value
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            names = [target.id.casefold() for target in targets if isinstance(target, ast.Name)]
            size = _module_collection_size(value)
            for name in names:
                if name in ALLOWED_MODULE_COLLECTIONS or size is None or size < 3:
                    continue
                if any(part in name for part in SEMANTIC_NAME_PARTS):
                    violations.append(
                        f"{filepath}:{statement.lineno}: suspicious semantic vocabulary {name!r}"
                    )

    assert not violations, "\n".join(violations)
