# AIOS WorkLens High-Level Roadmap Index

This document serves as the high-level index for the development phases, product loop, and doctrine of AIOS WorkLens.

## Core Reference Documents
- **Product North Star & Doctrine:** [PRODUCT_NORTH_STAR.md](file:///D:/Sandbox/AIOS_habbit/PRODUCT_NORTH_STAR.md) - Contains what AIOS WorkLens is, what it is NOT, the 7 product layers, and the core product loops.
- **Master Roadmap & Governance:** [WORKLENS_MASTER_ROADMAP.md](file:///D:/Sandbox/AIOS_habbit/WORKLENS_MASTER_ROADMAP.md) - Details the 8 roadmap development phases, model role rules, legacy repository usage policies, and active gate status.

---

## Active Gate & Phase Status

- **Current stable GitHub HEAD:** `3f2629e` (`Fix real normal document provider UI route`).
- **Provider/router foundation:** ✅ Usable foundation for normal documents, not production-grade P1.0.
  - Local-first MOM/company safety remains the default protected path.
  - Normal-document provider routing is wired through the router for custom notebooks.
  - DeepSeek has been verified with synthetic public normal-document pilots.
  - Provider health, key masking, cooldown, and key-rotation foundation are present.
  - Vietnamese route-log UI is available for user-readable routing decisions.
  - `API Key.txt`, `API*.txt`, `.env`, and provider config files are ignored and not tracked.
  - MOM/company cloud block is protected by tests and direct audits.
- **Current warnings:**
  - DOM/browser evidence is still partial in some browser-agent runs because automation was unstable.
  - The real daily pilot passed by direct path after the UI browser task failed internally.
  - Q&A-to-Case preserves answer, source refs, and safety, but does not persist route summary as a dedicated case field yet.
  - Provider key-rotation foundation exists, but real multi-key rotation is not fully field-tested.
  - This is **not P1.0 production-ready**.
- **Next recommended gates:**
  1. **AIOS-REAL-USER-PILOT-1** — actual non-confidential document.
  2. **AIOS-QA-CASE-ROUTE-SUMMARY-1** — preserve route summary in case draft.
  3. **AIOS-UX-DAILY-HARDENING-1** — reduce friction in daily workflow.
  4. Optional later: configure another provider key.
  5. Optional later: Router-6 advanced provider pool, only after real user pilot.

---

## Historical Gate & Phase Status

- **M1 to M1.3 (Intake Stabilization):** Completed.
- **M1.4 (Senior Learning Memory MVP):** Completed (Conditional PASS).
- **M1.5 (Pilot UX & Export Safety Hardening):** Completed.
- **M1.6 (Roadmap Governance Lock):** ✅ Completed (Doctrine and roles locked in docs).
- **M1.6B (Governance Cleanup):** ✅ Completed (Changelog/status cleanup and role-first agent rules).
- **M1.7 (Workspace + Knowledge Notebook + Simplified Navigation):** ✅ Passed after M1.7B hotfix (Workspace isolation, Knowledge Notebook upload, simplified central sidebar navigation, case linking; no RAG/OCR/vector DB).
- **M1.7B (Notebook Source Path Containment Hotfix):** ✅ Passed (`PASS_M1_7B_BLOCKER_FIXED`; `notebook_id` traversal blocked with allowlist + `resolve()`/`is_relative_to()`).
- **M1.8A (Practical Notebook Intelligence Fast Lane):** ✅ Passed (Local chunking ~1200 char, keyword/phrase search, Q&A/Study Pack prompt builders, structural Mermaid graph).
- **M1.8B (In-App Notebook Q&A):** ✅ Passed (In-app answer button, lightweight OpenAI-compatible LLM adapter (urllib), provider config, local/cloud privacy behavior).
- **M1.8C (Q&A Truth Modes + NotebookLM Bridge MVP):** ✅ Passed (Truth modes, hard block cloud/local_only unsafe flow, NotebookLM Bridge prompt schemas, JSON/Mermaid paste and preview).
- **M1.8D (Persist NotebookLM Bridge Imports):** ✅ Passed (Persistent import store, save/view/delete imports, graph/study/case investigation import preview, graph tab integration).
- **M1.8D-R (Roadmap Sync):** ✅ Passed (Roadmap & governance document synchronization, no drift guardrails).
- **M1.8E (Daily Work Pain Polish):** **Next immediate gate** (Focusing on daily-use polish, making saved imports easier to reuse, context sufficiency checking, reducing copy-paste friction, no heavy RAG/traceability code).
- **Phase 2A (Fake-data Pilot):** Gated (End-to-end validation with synthetic data only).
- **Phase 2 (Real-data Pilot):** Not started / gated (Do not use real data until Phase 2A passes).

---

## Historical Phase Results (Collaborative MVP Hardening)
- **Phase A (Initial Audit):** PASS.
- **Phase B (Public Safety Gate):** PASS (Git-ignore rules and scans verified).
- **Phase C (Public Branch):** PASS.
- **Phase D (MVP Hardening):** PASS.
- **Phase E (Real Phase Gate):** PASS.
- **Phase F (Tests):** PASS.
- **Phase G (GitHub Actions):** PASS.
- **Phase H (Docs Update):** PASS.
- **Phase I (Final Local Validation):** PASS.
- **Phase J (Commit and Push):** PASS.
