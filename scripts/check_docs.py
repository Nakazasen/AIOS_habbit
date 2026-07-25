#!/usr/bin/env python3
"""Validate the professionalization documentation contract without dependencies."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, Sequence

METADATA_FIELDS = ("Status:", "Owner role:", "Last reviewed:", "Review cadence:")
PROFESSIONAL_DIRECTORIES = (
    "docs/adr",
    "docs/architecture",
    "docs/contracts",
    "docs/governance",
    "docs/onboarding",
    "docs/operations",
    "docs/quality",
    "docs/release",
    "docs/requirements",
    "docs/security",
    "docs/user",
)
REQUIRED_PATHS = (
    "SECURITY.md",
    "CONTRIBUTING.md",
    "docs/DOCUMENTATION_GOVERNANCE.md",
    "docs/PROFESSIONALIZATION_INDEX.md",
    "docs/roadmap/completed/PROFESSIONALIZATION-BASELINE.md",
    "docs/security/THREAT_MODEL.md",
    "docs/security/PRIVACY_IMPACT_ASSESSMENT.md",
    "docs/security/DEPENDENCY_POLICY.md",
    "docs/quality/TEST_STRATEGY.md",
    "docs/quality/QUALITY_GATES.md",
    "docs/operations/BACKUP_RESTORE.md",
    "docs/operations/INCIDENT_RESPONSE.md",
    "docs/operations/TROUBLESHOOTING.md",
    "docs/operations/OBSERVABILITY.md",
    "docs/release/RELEASE_POLICY.md",
    "docs/release/RELEASE_CHECKLIST.md",
    "docs/release/SUPPORTED_VERSIONS.md",
    "docs/release/SBOM_POLICY.md",
    "docs/governance/RISK_REGISTER.md",
    "docs/governance/OWNERSHIP_AND_REVIEW.md",
    "docs/governance/DEFINITION_OF_READY_DONE.md",
    "docs/requirements/PRODUCT_REQUIREMENTS.md",
    "docs/requirements/NON_FUNCTIONAL_REQUIREMENTS.md",
    "docs/requirements/TRACEABILITY_MATRIX.md",
    "docs/contracts/RUNTIME_INTERFACES.md",
    "docs/contracts/PERSISTED_DATA_COMPATIBILITY.md",
    "docs/quality/UX_ACCESSIBILITY_ACCEPTANCE.md",
    "docs/operations/DATA_MIGRATION_COMPATIBILITY.md",
    "docs/operations/PERFORMANCE_CAPACITY_BASELINE.md",
    "docs/governance/MAINTENANCE_DEPRECATION_POLICY.md",
    "docs/governance/LOCALIZATION_GLOSSARY.md",
    "docs/onboarding/MAINTAINER_ONBOARDING.md",
    "docs/user/WORKSPACE_CHAT_USER_GUIDE.md",
    "docs/adr/README.md",
)
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def professional_markdown_paths(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for relative in PROFESSIONAL_DIRECTORIES:
        directory = root / relative
        if directory.exists():
            paths.update(path for path in directory.rglob("*.md") if path.is_file())
    for relative in ("SECURITY.md", "CONTRIBUTING.md", "docs/DOCUMENTATION_GOVERNANCE.md", "docs/PROFESSIONALIZATION_INDEX.md"):
        path = root / relative
        if path.exists():
            paths.add(path)
    return sorted(paths)


def is_external_target(target: str) -> bool:
    lowered = target.lower()
    return (
        not target
        or target.startswith("#")
        or lowered.startswith(("http://", "https://", "mailto:", "tel:", "file:"))
    )


def check_document(path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# "):
        errors.append(f"{path.relative_to(root)}: missing H1 title")
    for field in METADATA_FIELDS:
        if field not in text:
            errors.append(f"{path.relative_to(root)}: missing metadata {field}")
    for match in _LINK_RE.finditer(text):
        raw_target = match.group(1).strip().split(maxsplit=1)[0].strip("<>")
        target = raw_target.split("#", 1)[0]
        if is_external_target(target):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(root)}: broken local link {raw_target}")
    return errors


def check_root(root: Path, required_paths: Sequence[str] = REQUIRED_PATHS) -> list[str]:
    errors: list[str] = []
    for relative in required_paths:
        if not (root / relative).is_file():
            errors.append(f"missing required document: {relative}")
    for path in professional_markdown_paths(root):
        errors.extend(check_document(path, root))
    return errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = args.root.resolve()
    errors = check_root(root)
    if errors:
        print("DOCUMENTATION_CONTRACT=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("DOCUMENTATION_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
