# AIOS WorkLens

[Tiếng Việt](README_VI.md)

AIOS WorkLens is a local-first Workspace Chat for querying working documents with
retrievable evidence. It is designed to keep document preparation, search, chat
state, and evidence records under the operator's control.

## Current capabilities

- Workspace Chat with notebook and conversation-scoped sources.
- Local BGE-M3 hybrid retrieval when a verified local model pack is available.
- Vietnamese, Japanese, and Simplified Chinese UI/answer language support.
- `rag-trace/v1` evidence records linked to chat messages.
- An on-demand Evidence Graph for answers that contain valid evidence citations.
- Desktop and VPS packaging sources, including pinned Graphify and ExcaliFlow
  dependencies.

The Evidence Graph is an aid to inspect an answer's cited evidence. It does not
turn an answer without valid citations into verified knowledge.

## Status and boundaries

- `Workspace Chat` is the supported user-facing interface. The retired Case
  Cockpit and Habit Studio are not part of the normal workflow.
- The offline Windows/Linux wheelhouses are stored through Git LFS. They must
  be pulled before an offline build or installation.
- The BGE-M3 model pack is deliberately not stored in this Git repository. A
  desktop build checks its revision and checksum and stops if the verified model
  artifact is missing or corrupted.
- Desktop/VPS packaging is source and test verified in this repository. Validate
  the final package on the target machine before treating it as a production
  deployment.

## Quick start on Windows

Requirements: Git, Git LFS, Python **3.11**, and `uv`.

```powershell
git clone https://github.com/Nakazasen/AIOS_habbit.git
cd AIOS_habbit
git lfs install
git lfs pull
uv sync --group dev
```

Start Workspace Chat:

```powershell
.\RUN_AIOS_WORKSPACE_CHAT.bat
```

Or:

```powershell
.\scripts\run_workspace_chat.ps1
```

If BGE-M3 is unavailable, follow the model-pack and retrieval runbooks before
expecting document retrieval to work. The application reports that condition
instead of silently pretending search is available.

## Development checks

```powershell
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
git diff --check
git status --short
```

## Documentation

- [Vietnamese README](README_VI.md)
- [Roadmap and canonical delivery state](ROADMAP.md)
- [Project handover](PROJECT_HANDOVER.md)
- [Workspace architecture](WORKLENS_ARCHITECTURE.md)
- [Desktop packaging guide](packaging/desktop/README.md)
- [VPS deployment guide](packaging/vps/README.md)
- [Operator runbook](docs/runbooks/operator.md)
- [Developer runbook](docs/runbooks/developer.md)

## Local-data safety

Do not commit runtime data or private sources: `local_cases/`, `local_runs/`,
JSONL evidence and memory, uploaded documents, screenshots, `.env` files,
credentials, tokens, or caches. The provider and bridge configuration must be
reviewed before any organisation-specific or confidential source is sent beyond
the local machine.
