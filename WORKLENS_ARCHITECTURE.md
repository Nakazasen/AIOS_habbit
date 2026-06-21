# WorkLens Architecture & Modular Boundaries

This document defines the architectural target boundaries of AIOS WorkLens and aligns them with the product's locked layers.

---

## 1. Current Monolith vs Target Modules

AIOS Case Cockpit v0.1 is currently implemented as a Streamlit monolith in [case_cockpit.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/case_cockpit.py) with supporting modules for:
- [case_models.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/case_models.py) (Data Model)
- [case_store.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/case_store.py) (Local Storage)
- [case_prompt.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/case_prompt.py) (AI Prompts & Gating Policy)
- [case_audit.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/case_audit.py) (Safety Audits)
- [case_handover.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/case_handover.py) (Handover Formatting)
- [learning_models.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/learning_models.py) (Senior Learning Card Storage)
- [workspace_models.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_models.py) (Workspace & Knowledge Notebook storage/models)
- [source_ingest.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/source_ingest.py) (Source Document upload & preview parsing)
- [notebook_index.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/notebook_index.py) (Local source chunk indexing & search)
- [notebook_qa.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/notebook_qa.py) (Local context compiler & Q&A prompt generator)
- [llm_client.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/llm_client.py) (Lightweight HTTP-based LLM provider client)
- [notebook_bridge.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/notebook_bridge.py) (NotebookLM import schema parsing & Mermaid graph conversion)
- [notebook_import_store.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/notebook_import_store.py) (Persistent storage for NotebookLM imported results)

---

## 2. Seven Product Architecture Layers

Future development must organize boundaries along these locked layers:

### Layer 1: Workspace Boundary (`workspace/`)
- Manages configuration, user profiles, and active industry domain settings.
- Isolates distinct domains (e.g. MOM manufacturing vs IT support) in different local folders.

### Layer 2: Knowledge Notebook Boundary (`notebook/`)
- Ingests background knowledge resources (PDFs, Markdown manuals, procedures).
- Keeps notebooks completely isolated. Avoids mixing raw notebook sources with case evidence.
- Supports NotebookLM Bridge prompt compilation, structured results pasting, parsing, and persistent local storage (`notebook_import_store`).

### Layer 3: Case Cockpit Boundary (`cockpit/`)
- Handles active incident cases.
- Aggregates logs, screenshots, Excel sheets, and timeline events.
- Generates Case Map visualizations, next action recommendations, prompt packs, and handover markdown.

### Layer 4: Learning Memory Boundary (`memory/`)
- Saves experience memory as **Senior Learning Cards** (`SeniorLearningCard`).
- Coordinates state transitions (Draft, Reviewed, Confirmed).
- Gated by prompt privacy: draft cards are redacting placeholders; confirmed cards are included if the case is not `local_only`.

### Layer 5: Senior Coach / Work Intelligence Boundary (`coach/`)
- Guides the user's investigation flow, checks evidence gaps, and drafts styled communications (VI/JA).
- References historical cases and lessons learned without executing RAG overbuild.

### Layer 6: Visual Knowledge Graph (Advanced Boundary)
- Maps relationships between procedures, tables, components, past incidents, and verified causes.
- Renders structural workspace/notebook maps alongside importable/renderable graphs saved from external tools like NotebookLM.

### Layer 7: Field Intelligence / Alert (Advanced Boundary)
- Live log anomaly detection using historical case schemas.

---

## 3. Strict Refactor Rules
- **No Premature Abstraction:** Do not construct a modular refactor or distribute modules across separate services until Case Cockpit v0.1 has been validated through the Phase 2 Real Work Pilot.
- **Maintain Local-First Gating:** The `governance` and `export` boundaries must be strictly independent of UI scripts so they can be executed by automated test runners and command-line audit tools.
