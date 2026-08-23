# Implementation Plan: Conversation Management UX

**Branch**: `004-conversation-management-ux` | **Date**: 2026-08-22 | **Spec**: [spec.md](spec.md)

## Summary

Make conversation management unambiguous in Workspace Chat and make deletion recover immediately to a valid conversation or an actionable empty state. Preserve permanent storage semantics, use an explicit deletion target independent of incidental selection, and recover session and URL navigation as one state.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Streamlit and project-local Workspace Chat modules

**Storage**: Local JSONL conversation, message, temporary-source, and selection records

**Testing**: pytest

**Target Platform**: Local Windows browser session

**Project Type**: Local-first Streamlit application

**Performance Goals**: Navigation and post-delete recovery complete in the same rerun without a network call

**Constraints**: Preserve unrelated conversation and notebook data; Vietnamese-first copy; do not restore legacy UI routes

**Scale/Scope**: Workspace Chat conversation list, rename/delete controls, state/URL recovery, and regression tests

## Constitution Check

*Pass before and after design.*

- Evidence before assertion: pass; all state transitions receive automated tests.
- Local-first privacy: pass; no provider, network, or source-content path is used.
- User-centered Workspace Chat: pass; Vietnamese-first, supported UI only.
- Change discipline: pass; feature has specification, design, tasks, Graphify evidence, and required validation.
- Architecture/roadmap impact: none; this is a bounded correction to the supported Workspace Chat interaction.

## Project Structure

### Documentation

```text
specs/004-conversation-management-ux/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/conversation-management-ui.md
└── tasks.md
```

### Source

```text
src/aios_habit/
├── workspace_chat_app.py
├── workspace_chat_store.py
└── workspace_chat_models.py

tests/
├── test_workspace_chat_store.py
└── test_workspace_chat_owner_flow.py
```

**Structure Decision**: Keep the existing single-project layout. Persistence helpers remain in the Workspace Chat store; UI navigation and action rendering remain in the Workspace Chat app.

## Complexity Tracking

No constitution violation or additional project structure is required.
