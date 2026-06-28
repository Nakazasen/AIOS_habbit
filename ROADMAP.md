# AIOS WorkLens High-Level Roadmap Index

This document serves as the high-level index for the development phases, product loop, and doctrine of AIOS WorkLens.

## Core Reference Documents
- **Product North Star & Doctrine:** [PRODUCT_NORTH_STAR.md](file:///D:/Sandbox/AIOS_habbit/PRODUCT_NORTH_STAR.md) - Contains what AIOS WorkLens is, what it is NOT, the 7 product layers, and the core product loops.
- **Master Roadmap & Governance:** [WORKLENS_MASTER_ROADMAP.md](file:///D:/Sandbox/AIOS_habbit/WORKLENS_MASTER_ROADMAP.md) - Details the 8 roadmap development phases, model role rules, legacy repository usage policies, and active gate status.

---

## Active Gate & Phase Status

- **Current stable GitHub HEAD:** `214c44f` (`Clarify provider fallback reason in daily flow`).
- **Provider/router foundation:** ✅ Usable daily-pilot foundation for normal documents, not production-grade P1.0.
  - Local-first MOM/company safety remains the default protected path.
  - One-screen **Làm việc hằng ngày** flow is stable enough for guided daily pilot use.
  - Normal-document provider routing is wired through the router and browser/UI pilot.
  - DeepSeek has been verified with synthetic public normal-document smoke tests and UI pilot.
  - Q&A-to-Case preserves answer, source refs, safety, and route summary in the generated case draft.
  - Route log / route summary visibly reports provider, fallback state, and external-send status.
  - Provider health, key masking, cooldown, and key-rotation foundation are present.
  - `API Key.txt`, `API*.txt`, `.env`, and provider config files are ignored and not tracked.
  - MOM/company cloud block is protected by tests and direct negative audits.
- **Current warnings:**
  - This is **not P1.0 production-ready**; it is ready for owner roadmap decision.
  - Browser automation could not type Vietnamese accents reliably during the last pilot.
  - Notebook name entry can append to the default value instead of replacing it.
  - Answer, route, and provider metadata are visible but require scrolling in the UI.
  - Q2/Q3 browser automation sometimes needed repeated focus/submit attempts.
  - Selecting a newly created case from a long dropdown can require scrolling.
  - MOM UI safety was not rerun in the last browser pilot, although direct/policy tests pass.
  - Provider key-rotation foundation exists, but real multi-key rotation is not fully field-tested.
- **Next recommended gates:**
  1. **AIOS-P1-READINESS-DECISION-1** — owner decides whether to open P1.0 readiness checklist, run a short daily pilot, or harden UX first.
  2. **AIOS-UX-DAILY-HARDENING-1** — reduce the top daily-flow frictions if owner chooses UX hardening.
  3. Optional later: configure another provider key.
  4. Optional later: Router-6 advanced provider pool, only after real daily use proves the need.

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
