# Project: Vietnamese Localization of Understand Knowledge Graph (`knowledge-graph.json`)

## Architecture & System Overview
The target artifact is `.understand-anything/knowledge-graph.json` in the `AIOS_habbit` repository.
This file is ingested by:
- The Understand Vite dev server (`packages/dashboard/vite.config.ts`)
- React frontend components (`App.tsx`, `store.ts`, `GraphView.tsx`, `NodeInfo.tsx`, `LayerLegend.tsx`, `LearnPanel.tsx`)
- Assistant skills (`/understand-chat`, `/understand-explain`, `/understand-onboard`)

### Structural Analysis
- **Root Keys**: `"version"`, `"project"`, `"nodes"`, `"edges"`, `"layers"`, `"tour"`
- **Nodes**: Exactly 142 file nodes. All `summary` fields localized into Vietnamese with preserved IT terms.
- **Edges**: 58 edges. Canonical edge types aligned with `@understand-anything/core/schema.ts` and explicit `weight: 0.5`.
- **Layers**: 8 layer objects. Names and descriptions localized into Vietnamese.
- **Tour**: 9 tour step objects. Titles and descriptions localized into Vietnamese.
- **Project Metadata**: `project.description` localized into Vietnamese.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| F1 | Layers & Tour Translation | Translate 8 layers (`name`, `description`) and 9 tour steps (`title`, `description`) + `project.description` into natural Vietnamese while preserving core IT terms. | M1 | Survey (Explorer 1) | DONE |
| F2 | Node Summaries Chunk 1 | Translate summaries of nodes 1–35 (`.agents/`, `.github/`, `.specify/feature.json`) into Vietnamese. | M2.1 | Survey (Explorer 2) | DONE |
| F3 | Node Summaries Chunk 2 | Translate summaries of nodes 36–71 (`.specify/`, `00_governance/`, `01_design/`, `02_sources/`, `03_evidence_registry/`, `09_handover/`, `10_schemas/`). | M2.2 | Survey (Explorer 2) | DONE |
| F4 | Node Summaries Chunk 3 | Translate summaries of nodes 72–106 (`11_templates/`, root docs/scripts, `config/`, `docs/rag_v2/`, `docs/reports/`, `docs/requirements/`). | M2.3 | Survey (Explorer 2) | DONE |
| F5 | Node Summaries Chunk 4 | Translate summaries of nodes 107–142 (`docs/security/`, `specs/`, `tests/fixtures/`, `scripts/`, `src/aios_habit/` Python modules). | M2.4 | Survey (Explorer 2) | DONE |
| F6 | Master Assembly & Verification | Merge all translated chunks, overwrite `.understand-anything/knowledge-graph.json`, run automated verification harness (`verify_knowledge_graph.py` & `.mjs`), check JSON syntax, encoding, schema, and referential integrity. | M3 | Survey (Explorer 3) | DONE |
| F7 | Multi-Reviewer, Adversarial & Forensic Audit Gate | Independent linguistic review, IT terminology compliance review, adversarial challenger check, and forensic audit verification. | M4 | Project Quality Standard | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Layers & Tour Localization | Translate 8 layers and 9 tour steps + project description | None | DONE |
| M2.1 | Nodes Chunk 1 (1–35) | Translate summaries for nodes 1–35 | None | DONE |
| M2.2 | Nodes Chunk 2 (36–71) | Translate summaries for nodes 36–71 | None | DONE |
| M2.3 | Nodes Chunk 3 (72–106) | Translate summaries for nodes 72–106 | None | DONE |
| M2.4 | Nodes Chunk 4 (107–142) | Translate summaries for nodes 107–142 | None | DONE |
| M3 | Assembly & Harness Execution | Merge translated chunks into `.understand-anything/knowledge-graph.json` and run verification scripts | M1, M2.1, M2.2, M2.3, M2.4 | DONE |
| M4 | Comprehensive Verification Gate | Reviewer 1 (Language), Reviewer 2 (IT Terms), Challenger 1 (Parity), Challenger 2 (Dashboard), Auditor (Integrity) | M3 | DONE |

## Automated Verification Results
- `verify_knowledge_graph.py`: 100% PASS (0 syntax errors, 0 orphaned references, UTF-8 clean).
- `verify_knowledge_graph.mjs`: 100% PASS (Node.js JSON.parse valid, schema matched).
- Forensic Audit Verdict: CLEAN (Zero integrity violations, zero mock/dummy strings).
- Reviewer Verdicts: 100% APPROVE.
