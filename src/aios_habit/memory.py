from pathlib import Path

from .models import MemoryUnit
from .storage import read_jsonl


def validate_memory(path: Path, evidence_path: Path) -> list[str]:
    errors: list[str] = []
    evidence_ids = {record.get("evidence_id") for record in read_jsonl(evidence_path)}

    for record in read_jsonl(path):
        memory = MemoryUnit(**record)
        errors.extend(f"{memory.memory_id}: {error}" for error in memory.validate())
        if memory.status == "verified" and any(evidence_id not in evidence_ids for evidence_id in memory.evidence_ids):
            errors.append(f"{memory.memory_id}: missing evidence record")

    return errors
