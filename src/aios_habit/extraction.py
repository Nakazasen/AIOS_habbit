from pathlib import Path

from .models import EvidenceRecord, MemoryUnit, nid, sha_text


def extract_candidate(source: Path) -> tuple[EvidenceRecord, MemoryUnit]:
    text = source.read_text(encoding="utf-8", errors="ignore")
    evidence = EvidenceRecord(
        evidence_id=nid("EVD"),
        title="Markdown extraction source",
        source_type="markdown",
        source_path=str(source),
        summary=f"Metadata pointer for {source.name}",
        hash=sha_text(text),
        risk_level="low",
    )
    candidate = MemoryUnit(
        memory_id=nid("MEM"),
        category="project_knowledge",
        title=f"Candidate from {source.name}",
        statement=f"NEEDS_REVIEW: structured knowledge candidate from {source.name}",
        evidence_ids=[evidence.evidence_id],
        confidence="low",
        status="needs_evidence",
    )
    return evidence, candidate
