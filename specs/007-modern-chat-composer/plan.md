# Implementation Plan: Modern Chat Composer

**Branch**: `007-modern-chat-composer` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Replace the tall question form with a compact, rounded Workspace Chat composer inspired by current AI browser and IDE inputs. Add thumbnail-backed image attachment, browser-confirmed clipboard image paste, and an inline Mô hình AI picker that maps to the existing Gemini Web, C-AGENT and Router backends. Retain question processing, image ingestion, search preference, and pending-source safeguards.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Streamlit 1.60.0 and a small local image clipboard component

**Storage**: Existing local Workspace Chat store; no schema change

**Testing**: pytest, source-level UI contracts, existing Workspace Chat flow tests

**Target Platform**: Local-first browser UI on Windows; responsive from 360 px viewport width

**Project Type**: Local web application

**Performance Goals**: Composer remains immediately interactive; no additional network request or client-side dependency

**Constraints**: Vietnamese-first; preserve local-first privacy behavior; require a user gesture before clipboard read; do not alter the established image allowlist or pending-source lifecycle

**Scale/Scope**: One Workspace Chat composer in `workspace_chat_app.py`, focused tests, and a pinned clipboard component; excludes sidebars, source-library design, provider routing, and data models

## Constitution Check

| Gate | Status | Evidence |
|---|---|---|
| Evidence before assertion | Pass | Acceptance scenarios and source-level regression tests cover the form contract. |
| Local-first privacy and consent | Pass | Reuses current question and image submission path; no new data egress. |
| User-centered Workspace Chat | Pass | Vietnamese-first labels and native accessible controls are retained. |
| Change discipline and verifiable quality | Pass | Spec, plan, tasks, targeted tests, import and audit validation are required. |
| Graph-aware investigation | Pass | Graphify was queried for `workspace_chat_app.py` and its Workspace Chat tests. |

## Project Structure

```text
specs/007-modern-chat-composer/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── composer-ui-contract.md
└── tasks.md

src/aios_habit/
└── workspace_chat_app.py       # composer layout, state and scoped styling

tests/
├── test_workspace_chat_source_selection_owner_flow.py
├── test_workspace_chat_multi_file_uploader.py
├── test_workspace_chat_ui_i18n.py
└── test_workspace_chat_composer_ui.py
```

**Structure Decision**: Modify the existing single Streamlit application module and retain its established submission path. Add a small dedicated UI-contract test module instead of a frontend framework.

## Complexity Tracking

No constitution violations or additional complexity are required.
