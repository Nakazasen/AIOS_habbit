# Troubleshooting Guide

Status: `ACTIVE`
Owner role: Operator / maintainer
Last reviewed: 2026-07-25
Review cadence: After recurring failure or release candidate

## Safe diagnostic rule

Collect status, command output and versions without copying source text, API keys,
Authorization headers, raw prompts, local paths or private runtime JSONL into a
shared channel.

## Common conditions

| Symptom | Safe checks | Next action |
|---|---|---|
| Launcher/dependency error | Confirm Python version; run editable install; capture sanitized traceback | Reinstall/repair environment, then run import gate |
| Workspace Chat has no expected notebook/source | Confirm local store exists and owner selected correct notebook/conversation | Stop before overwrite; check backup state |
| Source extraction failed | Confirm file type/size and owner-facing message | Keep local; do not send file to provider as fallback |
| AI provider unavailable | Confirm router config/network without printing key | Use local-only flow; follow provider incident path if needed |
| CLI audit fails | Read exact audit finding | Correct source/fixture/ignore rule; never broadly disable scan |
| Local index search is empty/wrong | Confirm selected index path, chunk count and query terms | Rebuild only if source/chunk input is available |
| Git shows private runtime file | Remove from index, preserve owner file, update ignore rules | Treat pushed exposure as security incident |

## Standard validation

```powershell
py -3 scripts/check_docs.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
```

If a command fails, preserve and read the full error before changing code or
configuration. See [quality gates](../quality/QUALITY_GATES.md).

## Escalation

Use [incident response](INCIDENT_RESPONSE.md) for suspected privacy/credential,
data-loss or public-exposure conditions. Use the risk register for recurring but
non-active operational gaps.
