from pathlib import Path
import json
import tempfile

from .audit import audit_repo
from .models import DecisionPattern, EvidenceRecord, MemoryUnit, RAW_PATTERNS, WorkflowCard, scan_text_for_patterns

REQUIRED_ROOT_FILES = [
    "CONSTITUTION.md",
    "ROADMAP.md",
    "ARCHITECTURE.md",
    "PROJECT_HANDOVER.md",
    "CHANGELOG.md",
    "README.md",
    "pyproject.toml",
]

REQUIRED_GOVERNANCE_FILES = [
    "00_governance/PHASE_0_EXIT_CHECKLIST.md",
    "00_governance/DATA_POLICY.md",
    "00_governance/SOURCE_POLICY.md",
    "00_governance/VALIDATION_RULES.md",
]


def schemas_parse(repo: Path) -> list[str]:
    errors: list[str] = []
    for folder_name in ["10_schemas", "schemas"]:
        folder = repo / folder_name
        if not folder.exists():
            continue
        for schema_path in folder.glob("*.json"):
            try:
                json.loads(schema_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"schema parse fail {schema_path}: {exc}")
    return errors


def phase_validate(repo: Path, phase: str) -> list[str]:
    validators = {
        "0": _phase_0,
        "1": _phase_1,
        "2": _phase_2,
        "3": _phase_3,
        "4": _phase_4,
        "5": _phase_5,
        "6": _phase_6,
        "7": _phase_7,
        "8": _phase_8,
        "9": _phase_9,
    }
    validator = validators.get(phase)
    if validator is None:
        return ["unknown phase"]
    return validator(repo)


def _phase_0(repo: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_ROOT_FILES + REQUIRED_GOVERNANCE_FILES:
        if not (repo / relative_path).exists():
            errors.append(f"missing {relative_path}")
    errors.extend(schemas_parse(repo))
    return errors


def _phase_1(repo: Path) -> list[str]:
    errors: list[str] = []
    if not (repo / "src/aios_habit/discovery.py").exists():
        errors.append("missing discovery module")
    if "discover" not in (repo / "src/aios_habit/cli.py").read_text(encoding="utf-8"):
        errors.append("missing discover command")
    if not (repo / "02_sources").exists():
        errors.append("missing inventory output dir")
    return errors


def _phase_2(repo: Path) -> list[str]:
    errors: list[str] = []
    if not (repo / "src/aios_habit/evidence.py").exists():
        errors.append("missing evidence module")
    if not EvidenceRecord("", "", "", "").validate():
        errors.append("evidence validation does not fail missing fields")
    return errors


def _phase_3(repo: Path) -> list[str]:
    errors: list[str] = []
    if not (repo / "src/aios_habit/memory.py").exists():
        errors.append("missing memory module")
    if "verified memory requires evidence" not in MemoryUnit("M", "identity", "t", "s", [], status="verified").validate():
        errors.append("verified memory without evidence should fail")
    draft = MemoryUnit("M", "identity", "t", "s", [], status="draft", export_allowed=True)
    if "only verified memory can be export_allowed" not in draft.validate():
        errors.append("export_allowed draft should fail")
    return errors


def _phase_4(repo: Path) -> list[str]:
    module = repo / "src/aios_habit/extraction.py"
    if not module.exists():
        return ["missing extraction module"]
    if "needs_evidence" not in module.read_text(encoding="utf-8"):
        return ["extract does not create needs_evidence candidates"]
    return []


def _phase_5(repo: Path) -> list[str]:
    errors: list[str] = []
    if not (repo / "src/aios_habit/workflow.py").exists():
        errors.append("missing workflow module")
    if not WorkflowCard("W", "t", "", steps=[], output="", evidence_ids=[]).validate():
        errors.append("workflow validation does not fail missing fields")
    if not DecisionPattern("D", "t", "", criteria=[], tradeoffs=[], evidence_ids=[]).validate():
        errors.append("decision validation does not fail missing fields")
    return errors


def _phase_6(repo: Path) -> list[str]:
    module = repo / "src/aios_habit/profiles.py"
    if not module.exists():
        return ["missing profiles module"]
    if "UNKNOWN" not in module.read_text(encoding="utf-8"):
        return ["profiles do not mark unsupported claims UNKNOWN"]
    return []


def _phase_7(repo: Path) -> list[str]:
    if not (repo / "src/aios_habit/export_pack.py").exists():
        return ["missing export module"]
    if not scan_text_for_patterns("raw transcript", RAW_PATTERNS):
        return ["raw transcript marker not detected"]
    return []


def _phase_8(repo: Path) -> list[str]:
    errors: list[str] = []
    if not (repo / "src/aios_habit/audit.py").exists():
        errors.append("missing audit module")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "x.md").write_text("api_key` = abcdefghijk", encoding="utf-8")
        audit_errors, _warnings = audit_repo(temp_path)
        if not audit_errors:
            errors.append("audit should fail on secret fixture")
    return errors


def _phase_9(repo: Path) -> list[str]:
    module = repo / "src/aios_habit/handover.py"
    if not module.exists():
        return ["missing handover module"]
    if "Recovery" not in module.read_text(encoding="utf-8"):
        return ["handover lacks recovery"]
    return []
