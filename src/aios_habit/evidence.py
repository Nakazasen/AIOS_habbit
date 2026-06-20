from pathlib import Path

from .models import EvidenceRecord, nid, sha_text
from .storage import read_jsonl


def make_evidence(
    title: str,
    source_type: str,
    source_path: str,
    source_pointer: str = "",
    classification: str = "metadata_only",
    summary: str = "",
    risk_level: str = "low",
    local_only: bool = False,
    notes: str = "",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=nid("EVD"),
        title=title,
        source_type=source_type,
        source_path=source_path,
        source_pointer=source_pointer,
        classification=classification,
        summary=summary,
        hash=sha_text((source_path or "") + (summary or "")),
        risk_level=risk_level,
        allowed_for_export=not local_only,
        notes=notes,
    )


def validate_records(path: Path) -> list[str]:
    errors: list[str] = []
    for record in read_jsonl(path):
        evidence = EvidenceRecord(**record)
        errors.extend(f"{record.get('evidence_id')}: {error}" for error in evidence.validate())
    return errors
