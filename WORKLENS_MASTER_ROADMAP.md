# WorkLens Master Roadmap & Governance

Every phase of the AIOS WorkLens lifecycle must use strict PASS/FAIL gates. A phase or gate is not considered complete until deliverables, validation evidence, handover, and rollback options are clearly documented.

---

## 1. Current Gate Status

The project has advanced through the following local-first stabilization gates:

- **M1: Merge PR #1** — Completed (Squash merged).
- **M1.1: Streamlit Launch Hotfix** — Completed (ImportError resolved).
- **M1.2: Vietnamese UI Policy & Localization** — Completed (100% UI localization in Vietnamese).
- **M1.3: Quick Intake Flow** — Completed (Single-screen intake creating case + initial evidence).
- **M1.4: Senior Learning Memory MVP** — Completed (Conditional PASS; model, storage, and UI form completed).
- **M1.5: Pilot UX / Export Safety Hardening** — Completed (Implemented and validated; compact UI mode, pure handover, export options).
- **M1.6: Roadmap Governance Lock** — ✅ Completed (Doctrine and roles locked in docs).
- **M1.6B: Governance Cleanup** — Completed (Changelog/status cleanup and role-first agent rules).
- **M1.7: Workspace + Knowledge Notebook + Simplified Navigation** — ✅ Passed after M1.7B hotfix (Workspace isolation, Knowledge Notebook upload, simplified central sidebar navigation, case linking; no RAG/OCR/vector DB).
- **M1.7B: Notebook Source Path Containment Hotfix** — ✅ Passed (`PASS_M1_7B_BLOCKER_FIXED`; `notebook_id` traversal blocked with allowlist + `resolve()`/`is_relative_to()`).
- **M1.8A: Practical Notebook Intelligence Fast Lane** — ✅ Passed (Local chunking, keyword/phrase search, prompt builders, structural Mermaid graph; commit: `dc94b7d`).
- **M1.8B: In-App Notebook Q&A** — ✅ Passed (urllib OpenAI adapter, in-app answer button, local/cloud privacy logic; commit: `013f0c8`).
- **M1.8C: Q&A Truth Modes + NotebookLM Bridge MVP** — ✅ Passed (Truth modes, hard block cloud/local_only unsafe flow, JSON/Mermaid paste preview; commit: `8b289fe`).
- **M1.8D: Persist NotebookLM Bridge Imports** — ✅ Passed (Persistent import store, save/view/delete UI, graph tab integration; commit: `97e0243`).
- **M1.8D-R: Roadmap Sync** — ✅ Passed (Roadmap & governance document synchronization, no drift guardrails).
- **M1.8E: Daily Work Pain Polish** — **Next immediate gate** (Focusing on practical daily-use polish, making saved imports easier to reuse, context sufficiency checking, reducing copy-paste friction, no heavy RAG/traceability code).
- **Phase 2A: Fake-data Pilot** — **Gated** (End-to-end validation with synthetic/fake data only).
- **Phase 2: Real-data Pilot** — **Not started / gated** (Do not open real data until Phase 2A passes).

---

## 2. Roadmap Phases

### Phase 0 — Product Governance (Locked)
- **Objective:** Establish core product loops, roadmap, privacy limits, and model roles.
- **Scope:** Define North Star, migration policy, inheritance mapping, and agent constraints.
- **Deliverables:** `PRODUCT_NORTH_STAR.md`, `WORKLENS_MASTER_ROADMAP.md`, and Root policy docs.
- **Validation:** All governance files exist, align with daily loops, and are locked.
- **Exit Criteria:** PASS if governance is locked and no model bypasses it.

### Phase 1 — Local-first Case Cockpit Foundation (Locked)
- **Objective:** Create the initial incident case capture and learning card shell.
- **Scope:** App launcher, quick intake, evidence ingestion, map visualization, prompt packaging, secure handovers, audit check, Vietnamese UI, and local/export safety.
- **Deliverables:** Streamlit cockpit app, local JSONL storage for cases/evidence/learning cards, and test suite.
- **Validation:** 100% compile check, green test suite (`pytest`), and manual execution.
- **Exit Criteria:** PASS if UI opens, core loop works, and learning memory is preserved locally.

### Phase 1.5 — Product Shell / Navigation / Knowledge Notebook Foundation (Completed)
- **Objective:** Establish workspace/notebook concepts and clean navigation.
- **Scope:** Workspace selector, knowledge notebooks upload, local preview, and simplified sidebar navigation.
- **Exit Criteria:** PASS if workspaces and notebook document lists work without mixing with evidence.

### Phase 1.8 — Notebook Intelligence & Bridge Persistence (Completed)
- **Objective:** Integrate local Q&A engine and import/persist rich structures from NotebookLM.
- **Scope:** Local chunk indexing, keyword searching, Q&A/Study Pack prompt builders, urllib LLM client, truth modes, cloud safety hard gating, JSON/Mermaid parsing, and JSONL persistence.
- **Exit Criteria:** PASS if NotebookLM JSON/Mermaid results are persistent, queryable, and rendering correctly in UI.

### Phase 1.8E — Daily Work Pain Polish (Active Target)
- **Objective:** Refine daily usability of NotebookLM imports and minimize operational friction.
- **Scope:**
  - Make saved NotebookLM imports easier to reuse.
  - Convert saved investigation imports into draft Cases or evidence checklists.
  - Improve "what should I do next?" guidance.
  - Show context sufficiency before asking AI.
  - Show recent imports / recent questions.
  - NO heavy RAG or traceability implementation.
- **Exit Criteria:** PASS if daily-use polish features work without regression.

### Phase 2A — Fake-data Pilot (Next)
- **Objective:** Validate the full WorkLens loop end-to-end using synthetic/fake data only.
- **Scope:** Run one or more simulated incidents in a single workspace and notebook. Create cases, add fake evidence/source docs, generate actions/handovers, and write learning cards.
- **Deliverables:** Pilot feedback, test notes, and cleanup items. No real private data.
- **Validation:** Checklist compliance and no local/private runtime data tracked in Git.
- **Exit Criteria:** PASS if the user successfully completes at least one full incident loop using fake data.

### Phase 2 — Real-data Pilot (Gated / Not Started)
- **Objective:** Run Case Cockpit on real incidents in local environments only after Phase 2A passes.
- **Scope:** Daily use in a single workspace and one knowledge notebook. Create cases, add evidence, generate actions/handovers, and write learning cards.
- **Deliverables:** Pilot feedback, local-only notes. No real private data committed to Git.
- **Validation:** Checklist compliance (`MONDAY_PILOT_CHECKLIST.md`) and explicit public-safety review.
- **Exit Criteria:** PASS if the user successfully completes at least one full real incident loop after fake-data validation.

### Phase 3 (Future) / P1.0 — Production Traceability Foundation
- **Objective:** Establish the foundation schema for tracking production units and checking risk clusters.
- **Scope:**
  - Define generic traceability concepts: `unit_type`, `unit_serial`, `component_type`, `component_lot`, `supplier_lot`, `mold_id`, `cav_id`, `process_step`, `jig_id`, `jig_result`, `inspection_result`, `defect_type`, `risk_cluster`.
  - Generic support for various units such as LSU, Drum, DLP, Fuser, Scanner, MainBody, and Other components (LSU is only the first sample scenario, not an LSU-only system).
  - Build a lightweight schema, parse fake CSV files, and generate a simple join/risk summary.
  - NO real-time prediction or ML models.
  - NO heavy graph DB or vector DB integrations.
  - NO production database connections (API/Direct).
- **No Drift Guardrail:**
  > [!IMPORTANT]
  > Production Traceability is a future branch, not the immediate main lane.
  > It must remain generic, not LSU-only. LSU is only the first sample scenario.
  > No prediction/ML/graph DB/vector DB in P1.0.
  > P1.0 must not delay daily WorkLens usability. Return to daily pain solving immediately after the foundation is laid.

### Phase 4 — Knowledge Notebook / Ingest Engine
- **Objective:** Upgrade source document ingestion.
- **Scope:** PDF/Excel/Markdown metadata extractors, source isolation, no OCR overbuild, check legacy ingest harvest.
- **Validation:** Synthetic document parsing tests.

### Phase 5 — Visual Knowledge Graph
- **Objective:** Build visual mapping of knowledge.
- **Scope:** Graph visualization of systems, databases, procedures, personnel, cases, and patterns.
- **Validation:** Interactive graph exploration views.

### Phase 6 — Senior Coach Layer
- **Objective:** Connect the work intelligence helper.
- **Scope:** Guided investigations, missing evidence prompts, check suggestion, user-styled drafts for chat/emails, and anti-fake-cause reasoning.
- **Validation:** Actionable help metrics.

### Phase 7 — Field Intelligence / Alert
- **Objective:** Telemetry anomaly indicators.
- **Scope:** Live log error hints, production context, no early predictions.
- **Validation:** Grounded alerting rules on real case telemetry.

---

## 3. Model Role Rules

To maintain high development quality and prevent "fake PASS" updates, future AI agents and models must strictly adhere to their designated roles:

- **Audit Specialist:**
  - Handles independent audits, code reviews, anti-fake PASS checks, and critical reasoning.
  - Verifies that evidence, tests, and security guidelines are fully satisfied before merging.
  - Current recommended model: Codex GPT-5.5 or equivalent.
- **Execution Specialist:**
  - Handles execution, coding, repository changes, and test creation.
  - Implements the feature changes detailed in approved plans.
  - Current recommended models: Gemini Flash 3.5 High / Gemini Pro 3.1 or equivalent.
- **Strict Constraint:** No feature merge is allowed without an audit review and validation confirmation.

---

## 4. Legacy Repository Policy

The repository `AIOS_habbit` is the **central repository** for the WorkLens product.
Other legacy repositories serve as **read-only reference sources** to harvest ideas/concepts after deep auditing, namely:
- `ABW_NVIDIA_FUSION_CONTROL`
- `skill-Anti-brain-wiki_note`
- `Nvidia`

### Key Constraints:
1. **No direct porting:** Do not copy code blocks directly without adapting them to the new clean modular structure.
2. **Audit first:** Do not harvest ingest, graph, or agent-bridge code until a pilot is executed and a thorough audit is completed.
