"""AIOS Habit Memory - Integrated with Hermes Agent MemoryStore.

Ported directly from Hermes Agent (v0.21.6+724).
Provides:
- ENTRY_DELIMITER ("\\n§\\n")
- MemoryStore with bounded character budgets (MEMORY.md: 2200, USER.md: 1375)
- memory_tool (add, replace, remove, batch)
- validate_memory (legacy AIOS compatibility)
"""

from __future__ import annotations

from pathlib import Path

from .hermes_memory import (
    DEFAULT_MEMORY_CHAR_LIMIT,
    DEFAULT_USER_CHAR_LIMIT,
    ENTRY_DELIMITER,
    MEMORY_BLOCK_HEADERS,
    MemoryStore,
    get_memory_dir,
    load_on_disk_store,
    memory_tool,
)
from .models import MemoryUnit
from .storage import read_jsonl


def validate_memory(path: Path, evidence_path: Path) -> list[str]:
    """Validate legacy memory units against evidence records."""
    errors: list[str] = []
    if not path.exists():
        return errors
    evidence_ids = {record.get("evidence_id") for record in read_jsonl(evidence_path)} if evidence_path.exists() else set()

    for record in read_jsonl(path):
        memory = MemoryUnit(**record)
        errors.extend(f"{memory.memory_id}: {error}" for error in memory.validate())
        if memory.status == "verified" and any(evidence_id not in evidence_ids for evidence_id in memory.evidence_ids):
            errors.append(f"{memory.memory_id}: missing evidence record")

    return errors


__all__ = [
    "ENTRY_DELIMITER",
    "MEMORY_BLOCK_HEADERS",
    "DEFAULT_MEMORY_CHAR_LIMIT",
    "DEFAULT_USER_CHAR_LIMIT",
    "MemoryStore",
    "get_memory_dir",
    "load_on_disk_store",
    "memory_tool",
    "validate_memory",
]
