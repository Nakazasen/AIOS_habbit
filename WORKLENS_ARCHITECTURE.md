# WorkLens Architecture

## Current State
AIOS Case Cockpit v0.1 is a Streamlit monolith in `src/aios_habit/case_cockpit.py` with supporting modules for models, store, ingest, graph, and actions.

## Target Module Boundaries
- `apps/case_cockpit` or current `src/aios_habit/case_cockpit.py`: UI shell.
- `case_core`: case model, lifecycle, validation.
- `ingest`: Excel/CSV/image/chat/log/document ingestion.
- `visual_graph`: CaseGraph and timeline rendering.
- `memory`: verified learning extraction and reuse.
- `agent_bridge`: prompt packs first, external bridges later.
- `governance`: audit, privacy, migration rules.
- `export`: safe handover and model-specific packages.

## Refactor Rule
Do not perform a large refactor until v0.1 proves the daily loop. Keep the monolith if it is the fastest path to Monday utility.
