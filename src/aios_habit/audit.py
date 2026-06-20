from pathlib import Path

from .models import MemoryUnit, RAW_PATTERNS, SECRET_PATTERNS, scan_text_for_patterns
from .storage import read_jsonl

SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv"}
TEXT_EXTENSIONS = {".md", ".json", ".jsonl", ".py", ".toml", ".yml", ".yaml", ".gitignore"}


def audit_repo(repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    required_files = [
        "CONSTITUTION.md",
        "ROADMAP.md",
        "ARCHITECTURE.md",
        "PROJECT_HANDOVER.md",
        "CHANGELOG.md",
        "README.md",
        "pyproject.toml",
    ]
    for relative_path in required_files:
        if not (repo / relative_path).exists():
            errors.append(f"missing {relative_path}")

    for path in repo.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != ".gitignore":
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        if scan_text_for_patterns(text, SECRET_PATTERNS):
            errors.append(f"secret pattern: {path}")
        if _is_export_path(path) and scan_text_for_patterns(text, RAW_PATTERNS):
            errors.append(f"source conversation marker in export: {path}")

    evidence_ids = {record.get("evidence_id") for record in read_jsonl(repo / "03_evidence_registry/records/evidence.jsonl")}
    for record in read_jsonl(repo / "05_memory_vault/memory_units.jsonl"):
        memory = MemoryUnit(**record)
        errors.extend(f"{memory.memory_id}: {error}" for error in memory.validate())
        if memory.status == "verified" and any(evidence_id not in evidence_ids for evidence_id in memory.evidence_ids):
            errors.append(f"{memory.memory_id}: evidence missing")

    return errors, warnings


def _is_export_path(path: Path) -> bool:
    return "07_ai_export_packs" in path.parts or "06_ai_export_packs" in path.parts
