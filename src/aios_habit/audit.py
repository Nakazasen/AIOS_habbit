import os
from pathlib import Path
import subprocess
from typing import Iterator

from .models import MemoryUnit, RAW_PATTERNS, SECRET_PATTERNS, scan_text_for_patterns
from .storage import read_jsonl

SKIP_DIRS = {
    ".ai",
    ".git",
    ".codex",
    ".excaliflow",
    ".nvidia-agent",
    ".pytest_cache",
    ".tmp",
    ".tmp_smoke",
    ".tmp_verify_venv",
    ".understand-anything",
    "__pycache__",
    ".venv",
    ".venv-rag",
    ".venv-rag-compat",
    "venv",
    ".agents",
    ".local",
    "build",
    "cache",
    "dist",
    "graphify-out",
    "inbox_local_only",
    "local_cases",
    "local_runs",
    "private",
    "pytest_goal_032",
    "pytest_goal_033",
    "raw",
    "scratch",
    "secrets",
    "tailieugoc",
    "Tài liệu của tất cả dòng máy",
}
TEXT_EXTENSIONS = {".md", ".json", ".jsonl", ".py", ".toml", ".yml", ".yaml", ".gitignore"}


class AuditFileEnumerationError(RuntimeError):
    pass


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

    try:
        audit_files = list(_iter_audit_files(repo))
    except AuditFileEnumerationError:
        errors.append("không thể liệt kê đầy đủ tệp thuộc phạm vi kiểm toán")
        audit_files = []

    for path in audit_files:
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


def _iter_audit_files(repo: Path) -> Iterator[Path]:
    """Yield tracked and visible untracked files without entering ignored local data."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as error:
        if (repo / ".git").exists():
            raise AuditFileEnumerationError from error
        yield from _walk_visible_text_files(repo)
        return

    for raw_relative_path in result.stdout.split(b"\0"):
        if not raw_relative_path:
            continue
        relative_path = raw_relative_path.decode("utf-8", errors="surrogateescape")
        path = repo / relative_path
        if path.is_file() and (path.suffix.lower() in TEXT_EXTENSIONS or path.name == ".gitignore"):
            yield path


def _walk_visible_text_files(repo: Path) -> Iterator[Path]:
    for root, directory_names, file_names in os.walk(repo):
        directory_names[:] = [name for name in directory_names if name not in SKIP_DIRS]
        root_path = Path(root)
        for file_name in file_names:
            path = root_path / file_name
            if path.suffix.lower() in TEXT_EXTENSIONS or path.name == ".gitignore":
                yield path


def _is_export_path(path: Path) -> bool:
    return "07_ai_export_packs" in path.parts or "06_ai_export_packs" in path.parts
