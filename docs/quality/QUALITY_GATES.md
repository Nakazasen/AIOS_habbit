# Quality Gates

Status: `ACTIVE`
Owner role: Maintainer / release reviewer
Last reviewed: 2026-07-25
Review cadence: Every Gate Card closure and release candidate

## Required local gates

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

## Gate interpretation

| Gate | Evidence | Failure action |
|---|---|---|
| Documentation contract | Required docs, metadata and local links | Correct docs/links; do not bypass check |
| Compile | Python source/test compile | Read exact traceback; fix root cause |
| Tests | Unit/integration regression behavior | Add/repair contract test; do not delete assertion |
| CLI audit | Repository safety and evidence integrity | Investigate source/fixture rather than suppress scan |
| Workspace Chat import | Supported UI bootstrap compatibility | Read import failure; preserve Vietnamese-safe UX |
| Git diff checks | Whitespace/patch safety | Correct diff before review |
| Git status | Private runtime/credential safety | Remove from index; do not delete owner data without consent |

## CI parity

Core CI must run the documentation check, compile, pytest, CLI audit and
Workspace Chat import without provider credentials. CI may not perform live AI
calls or upload private runtime data. Dependency advisory scans remain advisory
until the owner approves their enforcement policy.

## Completion rule

A Gate Card is `DONE` only after current command evidence passes and its scope,
rollback and canonical roadmap/handover/changelog state are updated.
