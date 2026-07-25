from pathlib import Path
import importlib.util


def load_checker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_docs.py"
    spec = importlib.util.spec_from_file_location("check_docs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_doc(path: Path, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Sample\n\nStatus: `ACTIVE`\nOwner role: Test\n"
        "Last reviewed: 2026-07-25\nReview cadence: Test\n" + body,
        encoding="utf-8",
    )


def test_check_root_reports_missing_required_documents(tmp_path):
    checker = load_checker()
    errors = checker.check_root(tmp_path, required_paths=("docs/required.md",))
    assert errors == ["missing required document: docs/required.md"]


def test_check_document_accepts_metadata_and_valid_relative_link(tmp_path):
    checker = load_checker()
    document = tmp_path / "docs" / "security" / "sample.md"
    target = tmp_path / "docs" / "security" / "target.md"
    write_doc(target)
    write_doc(document, "\n[Target](target.md)\n[External](https://example.invalid)\n")
    assert checker.check_document(document, tmp_path) == []


def test_check_document_reports_broken_relative_link(tmp_path):
    checker = load_checker()
    document = tmp_path / "docs" / "security" / "sample.md"
    write_doc(document, "\n[Missing](missing.md)\n")
    assert "broken local link missing.md" in checker.check_document(document, tmp_path)[0]
