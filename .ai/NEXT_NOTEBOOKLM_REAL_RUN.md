# Next NotebookLM Real Run Packet

## Current state

- Current commit: `35dc85c`
- Source folder: `D:\Sandbox\MOM_WMS_QLLSSX\tailieugoc`
- Existing AIOS run path: `local_runs/notebooklm_compare/`
- Current status: AIOS answers exist; NotebookLM answers are missing.
- P1.0: NOT opened
- NotebookLM parity: NOT claimed

## Discovered `nlm` commands

```powershell
nlm create notebook <title>
nlm source add <notebook-id> --file <file> --wait
nlm query notebook <notebook-id> <question> --json
nlm notebook list --json
```

## Safe preparation notes

- Do not claim NotebookLM parity from this run.
- Do not commit `local_runs/` outputs.
- Do not commit NotebookLM answers if they contain real company text.
- Do not commit real MOM/WMS source docs.
- Do not print API keys or `.env`.
- Prefer a dedicated notebook title such as `AIOS MOM WMS Compare MVP 35dc85c`.

## Suggested next goal prompt

```text
/goal Run the real NotebookLM import/query/collect pass for AIOS_habbit comparison MVP.

Repo: D:\Sandbox\AIOS_habbit
Commit: 35dc85c
Source folder: D:\Sandbox\MOM_WMS_QLLSSX	ailieugoc
Runtime folder: local_runs/notebooklm_compare/

Use nlm commands only:
- nlm create notebook <title>
- nlm source add <notebook-id> --file <file> --wait
- nlm query notebook <notebook-id> <question> --json
- nlm notebook list --json

Import approved real MOM/WMS documents, ask the same questions from questions.jsonl, collect NotebookLM answers into local_runs/notebooklm_compare/notebooklm_answers.jsonl, run evaluator, and create a redacted aggregate summary only.

Do not commit local_runs, NotebookLM answers, raw company content, generated DB/index files, API keys, or .env.
Do not claim NotebookLM parity.
Do not open P1.0.
```
