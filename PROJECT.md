# Project: Antigravity Truthful Bridge

> Không phải luật sản phẩm. Đặc tả cầu nối Antigravity. Lối vào: `AGENTS.md`. Spec: `specs/antigravity-truthful-bridge/`.

## Architecture
The Antigravity Truthful Bridge provides an honest, non-facade integration between AIOS Habit Workspace Chat and the Antigravity IDE environment on the local machine. It implements a dual-mode strategy:
1. **Direct Adapter Mode**: Active only when a genuine, locally verified Antigravity IDE protocol endpoint is confirmed (`direct_ready`). If no verified protocol exists, it reports `unavailable` (never simulated).
2. **Asynchronous Handoff Mode**: Outbox/Inbox file-based bundle protocol (`handoff_ready`, `handoff_pending`, `completed`, `failed`) using `local_runs/ide_handoff/` with strict schema validation (`ide_handoff_response_v1`), SHA-256 bundle verification, and citation bounds checking.
3. **Finite State Machine (FSM)**: 6 distinct states (`unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed`).
4. **Strict Fail-Closed Policy**: If Antigravity is chosen and fails or times out, the system reports the error directly to the user. It NEVER silently delegates to `RealWorkspaceAIProviderClient` or Smart Router.
5. **Privacy & Security**: Zero transmission of `local_only` context to cloud endpoints; zero leakage of prompts, documents, tokens, or private paths into log streams.

## Code Layout
- `scripts/antigravity_sidecar_daemon.py`: Sidecar daemon providing local `/health` and truthful endpoint handling without fake loopbacks.
- `src/aios_habit/antigravity_bridge.py`: Bridge client, FSM health parsing, status polling, and truthful citation management.
- `src/aios_habit/ide_handoff_bridge.py`: Outbox/Inbox bundle generation, SHA-256 hashing, schema validation, and lifecycle transition tracking.
- `src/aios_habit/ai_provider_bridge.py`: AI provider routing ensuring strict fail-closed behavior for Antigravity provider.
- `src/aios_habit/workspace_chat_app.py` & `src/aios_habit/workspace_chat_ui.py`: UI status display, honest attribution ("Nguồn AI: Antigravity IDE"), handoff pending state display ("Đang chờ Antigravity IDE xử lý"), and refresh handling.
- `tests/test_antigravity_bridge.py`: Unit and integration tests for bridge health, FSM, direct mode, Tier 5 hardening, and fail-closed logic.
- `tests/test_antigravity_handoff_ui_flow.py`: Tests for handoff lifecycle, UI state transitions, outbox/inbox flow, and Tier 5 adversarial stress tests.
- `specs/antigravity-truthful-bridge/`: Spec Kit artifacts (`spec.md`, `plan.md`, `tasks.md`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Honest Health & FSM | 6-state FSM (`unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed`), sanitized failure reasons, no fake capabilities | M1 | R1 |
| 2 | Sidecar Loopback Purge | Eliminate `RealWorkspaceAIProviderClient` and fake mock responses from sidecar daemon | M1 | R1 |
| 3 | Citation Integrity | Remove automatic citation fabrication (`allowed_source_ids[0]`), enforce genuine evidence citations | M1, M2 | R1, R2 |
| 4 | Outbox/Inbox Lifecycle | File-based bundle creation with unique ID, SHA-256 hash, timeout tracking, state transitions | M2 | R2 |
| 5 | Schema Validation | Strict validation of `RESPONSE_SCHEMA_VERSION = "ide_handoff_response_v1"`, privacy flag, and citation scope | M2 | R2 |
| 6 | Workspace Chat Submission Flow | Route chat query to direct adapter (if `direct_ready`) or create handoff bundle (`handoff_pending`), displaying "Đang chờ Antigravity IDE xử lý" | M3 | R3 |
| 7 | Strict Fail-Closed Enforcement | On bridge error or timeout, return explicit error to user; 0 calls to Smart Router / `RealWorkspaceAIProviderClient` | M3 | R3 |
| 8 | Honest UI Attribution & Refresh | Display "Nguồn AI: Antigravity IDE" only on genuine Antigravity responses; global status "Cầu nối sẵn sàng" with mode; accurate UI refresh | M3 | R3 |
| 9 | RAG vs Bridge Separation | Clear boundary between notebook document selection warnings vs AI provider bridge status | M3 | R3 |
| 10 | Security, Privacy & Sanitization | Block `local_only` cloud dispatch; sanitize logs (no prompt/doc/token/private path leakage) | M1, M2, M3 | R4 |
| 11 | Spec Kit & Governance | Spec Kit artifacts (`spec.md`, `plan.md`, `tasks.md`), `.antigravityrules` compliance, graphify update | M4 | R5 |
| 12 | Comprehensive Test Suite & Hardening | Pass 100% pytest suite, adversarial coverage audit, forensic integrity verification | M5 | Verification |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Protocol Verification, Health FSM & Sidecar Cleanup | Clean sidecar daemon, FSM `/health`, eliminate fake capabilities & loopbacks, privacy sanitization | none | **DONE** |
| M2 | Asynchronous Handoff Lifecycle & Schema Validation | Outbox/Inbox bundle generation, lifecycle transitions, timeout handling, schema & citation validation | M1 | **DONE** |
| M3 | Workspace Chat Integration & Strict Fail-Closed Policy | UI submission wiring, pending status, fail-closed enforcement, honest attribution, RAG separation | M1, M2 | **DONE** |
| M4 | Spec Kit Artifacts & Repository Governance | Create `specs/antigravity-truthful-bridge/` (`spec.md`, `plan.md`, `tasks.md`), run graphify updates | M1, M2, M3 | **DONE** |
| M5 | Final Milestone: E2E Verification & Hardening | 100% pytest pass rate, adversarial challenger hardening (Tier 5), forensic integrity audit | M1, M2, M3, M4 | **DONE** |

## Interface Contracts
### Sidecar ↔ Bridge Client
- Endpoint `/health`:
  - Request: `GET /health`
  - Response JSON: `{"status": "<fsm_status>", "mode": "<direct|handoff|none>", "capabilities": [...], "reason": "<sanitized_reason_or_empty>"}`
  - Allowed status values: `unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed`.

### Handoff Bundle Contract
- Request Bundle (`local_runs/ide_handoff/outbox/<request_id>/`):
  - `manifest.json`, `question.md`, `prompt.md`, `prompt_for_antigravity.md`, `evidence_full.jsonl`, `evidence_full.md`, `source_manifest.json`, `completeness.json`, `request_status.json`.
- Response File (`local_runs/ide_handoff/inbox/<request_id>/response.json`):
  - Schema version: `ide_handoff_response_v1`
  - Fields: `request_id`, `schema_version`, `status` ("completed"|"failed"), `answer_markdown`, `answer_text`, `model_tool_name`, `privacy_acknowledged`, `evidence_ids_used`, `used_full_bundle`.
