# Developer Runbook

## Setup

```powershell
py -3 -m pip install -e .
```

## Required validation

```powershell
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
git status --short --ignored
```

Do not stage private/runtime data. Do not claim a gate is `DONE` without its
current command evidence. Read `ROADMAP.md` and the relevant Gate Card before
implementation.
