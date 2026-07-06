import pytest
import os
import glob

FORBIDDEN_TERMS = [
    "MES",
    "MOM",
    "ManualShipping",
    "生産履歴",
    "C31",
    "C32",
    "kdcRenameShipChangeQty"
]

def test_rag_v2_core_has_no_hardcoded_business_logic():
    """
    Ensure no business domain hard-code in new RAG v2 core modules.
    Tests/Docs/Legacy code are ignored here.
    """
    import aios_habit
    base_dir = os.path.dirname(aios_habit.__file__)
    rag_v2_dir = os.path.join(base_dir, "rag_v2")

    assert os.path.isdir(rag_v2_dir), "rag_v2 package must exist"

    python_files = glob.glob(os.path.join(rag_v2_dir, "**", "*.py"), recursive=True)
    assert len(python_files) > 0, "Expected Python files in rag_v2 package"

    violations = []

    for filepath in python_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            for term in FORBIDDEN_TERMS:
                # We do a naive check. If the term appears anywhere in the file (even comments), we flag it.
                if term in content:
                    violations.append(f"File {filepath} contains forbidden term: {term}")

    assert len(violations) == 0, "\n".join(violations)
