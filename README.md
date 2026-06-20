# AIOS Habit

Public-safe MVP for a local-first, evidence-based, AI-independent personal memory platform.

## Public Repository Safety

This public repository contains code, docs, schemas, templates, and synthetic examples only. It must not contain private runtime data, real evidence JSONL, real memory vault JSONL, raw transcripts, secrets, credentials, or personal export packs.

Private runtime data remains local and is blocked by `.gitignore`.

## What AIOS Habit Does

- Discovers project folders using metadata-only signals.
- Stores evidence pointers and hashes instead of raw content.
- Stores memory units with strict evidence/status validation.
- Extracts candidates for review, not verified truth.
- Builds profiles from verified/export-allowed memory only.
- Exports AI packs only after redaction/audit checks.

## Install

```powershell
py -3 -m pip install -e .
```

## AIOS Habit Studio (Web UI)

The recommended way for normal users to interact with AIOS Habit is the Studio UI.
Double-click `RUN_AIOS_HABIT_STUDIO.bat` or run:
```powershell
.\scripts\run_studio.ps1
```
See [STUDIO_UI.md](docs/STUDIO_UI.md) for more details.

## CLI Usage (For AI Executors/Developers)

```powershell
aios-habit --help
```

Without install:

```powershell
$env:PYTHONPATH="src"
py -3 -m aios_habit.cli status
```

## Validate

```powershell
py -3 -m pytest
$env:PYTHONPATH="src"
py -3 -m aios_habit.cli audit
py -3 -m aios_habit.cli phase validate --phase 0
```
