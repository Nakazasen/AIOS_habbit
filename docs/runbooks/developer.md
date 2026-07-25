# Developer Runbook

Status: `ACTIVE`
Owner role: Maintainer / release reviewer
Last reviewed: 2026-07-25
Review cadence: Every Gate Card closure and release candidate

## Setup

```powershell
py -3 -m pip install -e .
```

## Required validation

```powershell
py -3 scripts/check_docs.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
git status --short --ignored
```

## Workflow

1. Read `ROADMAP.md`, the active Gate Card and relevant ADR/requirements/contracts
   before implementation.
2. Keep code/docs changes within the Gate allowlist; do not open planned RAG/A18/
   P1.0 work by implication.
3. Use synthetic fixtures only. Do not stage private/runtime data, keys, raw
   documents, screenshots, provider headers or `local_cases/`/`local_runs/`.
4. Add focused regression tests, then run all required validation.
5. Record current evidence in canonical roadmap/handover/changelog only after it
   passes. A Gate is not `DONE` without rollback and review evidence.

## Release and maintenance

Use [quality gates](../quality/QUALITY_GATES.md),
[release checklist](../release/RELEASE_CHECKLIST.md),
[dependency policy](../security/DEPENDENCY_POLICY.md) and
[contributing guide](../../CONTRIBUTING.md). For a privacy/provider route change,
read the threat/privacy records and the P0 policy-consolidation Gate Card first.
