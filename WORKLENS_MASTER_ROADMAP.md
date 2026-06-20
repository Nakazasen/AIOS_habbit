# WorkLens Master Roadmap & Governance

Every phase of the AIOS WorkLens lifecycle must use strict PASS/FAIL gates. A phase or gate is not considered complete until deliverables, validation evidence, handover, and rollback options are clearly documented.

---

## 1. Current Gate Status

The project has advanced through the following local-first stabilization gates:

- **M1: Merge PR #1** — Completed (Squash merged).
- **M1.1: Streamlit Launch Hotfix** — Completed (ImportError resolved by correcting direct streamlit run paths).
- **M1.2: Vietnamese UI Policy & Localization** — Completed (100% UI localization in Vietnamese).
- **M1.3: Quick Intake Flow** — Completed (Single-screen intake creating case + initial evidence).
- **M1.4: Senior Learning Memory MVP** — Completed (Conditional PASS; model, storage, and UI form completed).
- **M1.5: Pilot UX / Export Safety Hardening** — Completed (Implemented and validated; compact UI mode, extracted pure handover helper, audit warnings, and export mode options).
- **M1.6: Roadmap Governance Lock** — ✅ Completed (Locking product doctrine, loop, layers, model roles, and phase definitions).
- **M1.6B: Governance Cleanup** — Completed (Changelog/status cleanup and role-first agent rules).
- **M1.7: Workspace + Knowledge Notebook + Simplified Navigation** — Implemented / Pending Audit (Workspace isolation, Knowledge Notebook upload, simplified central sidebar navigation, case linking, no full RAG yet).
- **Phase 2 Real Work Pilot** — **Upcoming** (Will begin once M1.7 and governance shells are stable).

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

### Phase 1.5 — Product Shell / Navigation / Knowledge Notebook Foundation (Active Target)
- **Objective:** Establish workspace/notebook concepts and clean navigation.
- **Scope:**
  - Simplify navigation (reduce sidebar radio button clutter).
  - Introduce workspaces (industry/domain context isolation).
  - Introduce knowledge notebooks (ingest background documentation separate from case evidence).
  - Allow uploading source documents to notebooks, ensuring they do not pollute case evidence.
  - Allow cases to link to a notebook.
  - Source metadata/preview only; no full RAG implementation yet.
- **Validation:** Isolated file storage structure and clean tabbed navigation.
- **Exit Criteria:** PASS if workspaces and notebook document lists work without mixing with evidence.

### Phase 2 — Real Work Pilot (Pending M1.7 Stability)
- **Objective:** Run Case Cockpit on real incidents in local environments.
- **Scope:** Daily use in a single workspace and one knowledge notebook. Create cases, add evidence, generate actions/handovers, and write learning cards.
- **Deliverables:** Pilot feedback, local-only notes. No real private data committed to Git.
- **Validation:** Checklist compliance (`MONDAY_PILOT_CHECKLIST.md`).
- **Exit Criteria:** PASS if the user successfully completes at least one full incident loop.

### Phase 3 — Learning Memory Hardening
- **Objective:** Enable query and lookup of experience cards.
- **Scope:** Search learning cards, case similarity indexing, pattern memory, communication memory, and review/confirmation governance.
- **Validation:** Similarity tests and confirmed/unconfirmed card safety checks.

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
