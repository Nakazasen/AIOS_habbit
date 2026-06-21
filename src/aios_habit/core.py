from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import uuid

ROOT = Path(__file__).resolve().parents[2]

SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----",
    r"(?i)(api[_-]?key|token|password|secret|credentials)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]",
]

RAW_PATTERNS = [
    r"(?i)raw transcript",
    r"(?i)chat transcript",
    r"(?i)conversation transcript",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def nid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class EvidenceRecord:
    evidence_id: str
    title: str
    source_type: str
    source_path: str
    source_pointer: str = ""
    captured_at: str = field(default_factory=now)
    classification: str = "metadata_only"
    summary: str = ""
    hash: str = ""
    risk_level: str = "low"
    allowed_for_export: bool = True
    notes: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        for field_name in ["evidence_id", "title", "source_type", "source_path", "captured_at", "classification"]:
            if not getattr(self, field_name):
                errors.append(f"missing {field_name}")
        if self.risk_level not in {"low", "medium", "high", "local_only"}:
            errors.append("invalid risk_level")
        return errors


@dataclass
class MemoryUnit:
    memory_id: str
    category: str
    title: str
    statement: str
    evidence_ids: list[str] = field(default_factory=list)
    confidence: str = "low"
    status: str = "draft"
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    tags: list[str] = field(default_factory=list)
    export_allowed: bool = False
    review_notes: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        categories = {
            "identity",
            "behavior",
            "language",
            "workflow",
            "project_knowledge",
            "lessons_learned",
            "decision_patterns",
        }
        statuses = {"draft", "needs_evidence", "verified", "deprecated", "rejected"}
        if self.category not in categories:
            errors.append("invalid category")
        if self.status not in statuses:
            errors.append("invalid status")
        if self.status == "verified" and not self.evidence_ids:
            errors.append("verified memory requires evidence")
        if self.export_allowed and self.status != "verified":
            errors.append("only verified memory can be export_allowed")
        return errors


@dataclass
class ProjectCard:
    project_id: str
    name: str
    path: str
    status: str = "candidate"
    description: str = ""
    detected_signals: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    last_seen_at: str = field(default_factory=now)
    tags: list[str] = field(default_factory=list)


@dataclass
class WorkflowCard:
    workflow_id: str
    title: str
    trigger: str
    context: str = ""
    steps: list[str] = field(default_factory=list)
    output: str = ""
    failure_modes: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "draft"
    tags: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        required = {
            "trigger": self.trigger,
            "steps": self.steps,
            "output": self.output,
            "evidence": self.evidence_ids,
        }
        return [name for name, value in required.items() if not value]


@dataclass
class DecisionPattern:
    decision_id: str
    title: str
    context: str
    criteria: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    preferred_action: str = ""
    anti_patterns: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "draft"
    tags: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        required = {
            "context": self.context,
            "criteria": self.criteria,
            "tradeoffs": self.tradeoffs,
            "evidence": self.evidence_ids,
        }
        return [name for name, value in required.items() if not value]


def as_dict(obj) -> dict:
    return asdict(obj)


def scan_text_for_patterns(text: str, patterns: list[str]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text)]
