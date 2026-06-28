# P1 Owner Acceptance Runbook

This runbook is for the owner. It cannot be completed by an agent alone.

## Goal

Verify that AIOS WorkLens can support a daily owner workflow without the owner needing to understand tests or internal implementation details.

## Safe data modes

### Fake-data mode

Use fake cases, fake file names, and fake operational details. This is the safest mode for screenshots or sharing results.

### Real-data local-only mode

If you use company or sensitive material, keep it local-only. Do not paste it into NotebookLM, cloud chat, external IDEs, or public screenshots.

## Acceptance steps

1. Open the repository locally.
2. Run the owner workflow guide:

   ```powershell
   $env:PYTHONPATH='src'; py -3 -m aios_habit.cli owner-workflow --fake-data
   ```

3. Read the printed steps from top to bottom.
4. For fake data, perform the described RAG search, evidence review, prompt export decision, and paste-back decision using only fake content.
5. For real data, stop before any external export unless the evidence is clearly cloud_safe.
6. Record whether each step was understandable without reading test files or asking an agent.
7. Report the result back to ChatGPT using the template below.

## PASS criteria

- You can identify the next action from the guide.
- You understand when local_only blocks external export.
- You can tell what evidence/citations support an answer.
- You know what to do when evidence is insufficient.
- You can record whether the workflow is acceptable for daily use.

## FAIL criteria

- You need an agent to explain what to run next.
- You cannot tell whether data may leave the machine.
- Evidence/citations are unclear.
- Prompt export/paste-back is confusing.
- The flow feels too manual for daily use.

## What counts as too manual

- More than one unclear command before seeing useful guidance.
- Needing to inspect Python tests to understand the workflow.
- Copy/paste steps that do not clearly explain privacy and evidence risks.
- No clear answer for insufficient evidence.

## Safe and unsafe evidence to share

Safe to share:

- Fake-data screenshots.
- PASS/FAIL notes with no company names or raw content.
- Redacted error messages.

Unsafe to share:

- API keys.
- `.env` files.
- Company/MOM/source documents.
- local_cases content.
- Generated prompt packs containing sensitive text.
- Paste-back answers containing company data.

## Owner report template

```text
AIOS Owner Acceptance Run
Mode: fake-data / real-data-local-only
Date:
Result: PASS / FAIL
Too manual: YES / NO
Most confusing step:
Privacy confidence: HIGH / MEDIUM / LOW
Evidence/citation confidence: HIGH / MEDIUM / LOW
Notes:
```

## Current status

Real owner acceptance is `BLOCKED_NEEDS_OWNER_ACCEPTANCE` until the human owner completes this run and reports the result.
