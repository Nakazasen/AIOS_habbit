# Implementation Plan: Antigravity Truthful Bridge & Repository Governance

**Branch**: `specs/antigravity-truthful-bridge` | **Date**: 2026-08-22 | **Specification**: [spec.md](spec.md) | **Milestone**: M4

**Input**: Feature specification from `specs/antigravity-truthful-bridge/spec.md` and requirements from `ORIGINAL_REQUEST.md` (R1-R5).

---

## 1. Summary & Objectives

The Antigravity Truthful Bridge eliminates simulation facades, mock adapters, and deceptive health statuses in the AIOS Habit Workspace Chat integration with Antigravity IDE. It introduces:
1. An honest **6-State Finite State Machine (FSM)** exposing verified statuses via `/health`.
2. A cryptographic, bundle-verified **Asynchronous Outbox/Inbox Handoff Engine** (`local_runs/ide_handoff/`).
3. Strict schema validation (`ide_handoff_response_v1`), zero-fabrication citation matching, and automated timeout expiration.
4. UI integration with honest attribution ("Nguồn AI: Antigravity IDE"), distinct RAG vs AI provider status separation, and a **Strict Fail-Closed Policy** that completely prohibits fallback to Smart Router upon bridge failure.
5. Strict AST enforcement prohibiting `RealWorkspaceAIProviderClient` within the sidecar daemon.
6. Full Spec Kit governance (`spec.md`, `plan.md`, `tasks.md`) and `.antigravityrules` compliance.

---

## 2. Technical Context & Environment

- **Language / Runtime**: Python 3.11+
- **Core Dependencies**: `streamlit`, standard library (`urllib`, `json`, `hashlib`, `uuid`, `dataclasses`, `logging`, `pathlib`, `ast`, `re`, `ipaddress`).
- **Storage & State**: File-based Outbox/Inbox directories under `local_runs/ide_handoff/` (strictly `.gitignore` excluded); SQLite message/evidence store in `src/aios_habit/workspace_chat_store.py`.
- **Testing Framework**: `pytest` (unit, integration, AST static analysis, mock HTTP server).
- **Target Platform**: Local Windows / macOS / Linux developer workstation.
- **Port & Protocol**: Local loopback `http://127.0.0.1:8585` (GET `/health`, POST `/v1/chat/completions`).

---

## 3. Constitution & Governance Check (.antigravityrules)

| Principle | Enforcement & Evidence | Gate Status |
|---|---|---|
| **Truthfulness (Điều 1)** | Direct mode reports `unavailable` if unverified; zero fake capabilities (`reasoning`, `large_context`, `excel_sql`) advertised; zero fake citation generation. | **PASS** |
| **Anti-Laziness (Điều 2)** | Full implementation across all modules with 100% test coverage; no placeholders, no skipped edge cases. | **PASS** |
| **Evidence-Based (Điều 3)** | Bundle uses SHA-256 digest of evidence lines; citations validated with word boundaries (`\bEVD-X\b`). | **PASS** |
| **Fail-Closed (Điều 4)** | Bridge errors return explicit failure to user; 0 calls to Smart Router or fallback provider. `local_only` data blocked from non-local networks. | **PASS** |
| **Graphify (Điều 5)** | Graph query performed prior to edits; graph update (`graphify update .`) executed on source modifications. | **PASS** |
| **Spec Kit (Điều 6)** | Complete artifacts (`spec.md`, `plan.md`, `tasks.md`) co-located in `specs/antigravity-truthful-bridge/`. | **PASS** |
| **AgentMemory (Điều 7)** | Checkpoints saved at milestones; session integrity preserved. | **PASS** |
| **Excalidraw (Điều 8)** | Visual diagrams maintained where required. | **PASS** |
| **Housekeeping (Điều 9)** | No temporary clutter, clean git status, zero `local_runs/` files tracked. | **PASS** |

---

## 4. Technical Architecture & Component Interaction

```text
+----------------------------------------------------------------------------------------------------+
|                                    AIOS Habit Workspace Chat UI                                    |
|  - Header: render_bridge_header_status() [Status Badge: direct | handoff | pending | failed]       |
|  - Chat: route_workspace_chat_submission()                                                         |
|  - Handoff Banner: render_handoff_pending_banner()                                                 |
|  - Attribution: render_ai_answer_header() ("Nguồn AI: Antigravity IDE")                            |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                         +------------------------+------------------------+
                         |                                                 |
                         v (Direct Mode if direct_ready)                   v (Handoff Mode if handoff_ready)
+--------------------------------------------------+  +----------------------------------------------+
|       Direct Adapter Client                      |  |     IDE Handoff Engine                       |
|  - call_antigravity_bridge()                     |  |  - write_ide_handoff_bundle()                |
|  - is_local_endpoint()                           |  |  - verify_bundle_integrity() (SHA-256)       |
|  - sanitize_reason()                             |  |  - check_handoff_request_timeouts()          |
+------------------------+-------------------------+  |  - import_ide_response()                     |
                         |                            |  - save_imported_ide_answer()                |
                         v (HTTP POST :8585)          +----------------------+-----------------------+
+--------------------------------------------------+                         |
|   Antigravity Sidecar Daemon (:8585)             |                         v (File I/O)
|  - GET /health -> evaluate_sidecar_health()      |  +----------------------------------------------+
|  - POST /v1/chat/completions -> HTTP 503         |  | local_runs/ide_handoff/                      |
|  - Background Watcher: process_pending_ide_...() |  |  ├── outbox/<req_id>/ (11 bundle files)      |
|  - AST Guard: ZERO RealWorkspaceAIProviderClient |  |  ├── inbox/<req_id>/ (response.json)         |
+--------------------------------------------------+  |  └── processed/<req_id>/ (archived result)   |
                                                      +----------------------------------------------+
```

---

## 5. 6-State FSM State Transition Matrix

The Antigravity Bridge health FSM operates across 6 well-defined states with strict entry, exit, and transition guards:

| Current State | Event / Trigger | Guard / Condition | Target State | Side Effects / Output |
|---|---|---|---|---|
| `unavailable` | Sidecar startup & health probe | Daemon offline / connection refused | `unavailable` | Mode: `none`, capabilities: `[]`, sanitized connection error reason |
| `unavailable` | Sidecar daemon responds HTTP 200 | Outbox empty, no direct adapter | `handoff_ready` | Mode: `handoff`, capabilities: `["local_handoff"]` |
| `unavailable` | Sidecar daemon responds HTTP 200 | Verified local IDE protocol detected | `direct_ready` | Mode: `direct`, capabilities: `["direct_chat", "local_handoff"]` |
| `handoff_ready` | User submits question | Direct unavailable, handoff active | `handoff_pending` | Outbox bundle created; UI displays "Đang chờ Antigravity IDE xử lý" |
| `handoff_ready` | Verified direct adapter detected | Runtime protocol check succeeds | `direct_ready` | Mode: `direct`, capabilities updated |
| `handoff_pending` | Background watcher / IDE writes response | `response.json` valid schema & citations | `completed` | Status updated; response imported into chat; UI displays answer |
| `handoff_pending` | Expiration timer exceeded | `now > expires_at` (timeout reached) | `failed` | `request_status.json` state=`failed`, reason=`timeout`; UI shows error |
| `handoff_pending` | Response validation fails | Corrupt JSON, invalid schema, bad citations | `failed` | `request_status.json` state=`failed`, reason=`validation_failed` |
| `completed` | New question submitted | Outbox empty of pending requests | `handoff_ready` | System ready for next request |
| `failed` | User clicks Refresh / retry | Stale requests handled / daemon healthy | `handoff_ready` | Reason cleared; UI returns to ready badge |
| `ANY` | Daemon internal exception / HTTP 500 | Unhandled daemon error | `failed` | Mode: `none`, capabilities: `[]`, sanitized exception reason |

### Request Lifecycle FSM (Within Bundle)
1. `handoff_pending`: Initial state written to `request_status.json` upon bundle creation.
2. `completed`: Transitioned atomically by `save_imported_ide_answer` upon valid schema import.
3. `failed`: Transitioned by `check_handoff_request_timeouts` (timeout) or `import_ide_response` (validation error).

---

## 6. Asynchronous Outbox/Inbox Data Flow & Protocol

### 6.1 Directory Structure (`local_runs/ide_handoff/`)
```text
local_runs/ide_handoff/
├── outbox/
│   └── <request_id>/
│       ├── manifest.json                  # Full metadata, schema version, allowed IDs, SHA-256
│       ├── evidence_bundle.json           # Compact metadata for IDE agents
│       ├── question.md                    # Raw user question in Markdown
│       ├── prompt.md                      # Prompt with embedded response schema
│       ├── prompt_for_antigravity.md      # Exact instructions for Antigravity IDE
│       ├── evidence_full.jsonl            # Canonical JSONL evidence records (hashed for SHA-256)
│       ├── evidence_full.md               # Human-readable formatted evidence
│       ├── source_manifest.json           # List of source files and IDs
│       ├── completeness.json              # Completeness verification and SHA-256 checksum
│       ├── README_FOR_IDE.md              # Operator and agent guidance
│       └── request_status.json            # Atomic FSM status tracking
├── inbox/
│   └── <request_id>/
│       └── response.json                  # Antigravity IDE response payload
└── processed/
    └── <request_id>/
        ├── response.json                  # Archived copy of response
        └── import_result.json             # Verification results and saved draft ID
```

### 6.2 Schema Contract: `RESPONSE_SCHEMA_VERSION = "ide_handoff_response_v1"`
```json
{
  "schema_version": "ide_handoff_response_v1",
  "request_id": "REQ-20260822-120000-A1B2C3D4",
  "status": "completed",
  "answer_markdown": "Phân tích chi tiết dựa trên tài liệu [EVD-1]...",
  "answer_text": "Phân tích chi tiết dựa trên tài liệu [EVD-1]...",
  "cited_evidence_ids": ["EVD-1"],
  "evidence_ids_used": ["EVD-1"],
  "limitations": [],
  "confidence": "high",
  "confidence_label": "high",
  "privacy_acknowledged": true,
  "used_full_bundle": true,
  "unsupported_claims": [],
  "recommended_next_actions": ["Kiểm tra lại bằng chứng và lưu Case nếu cần."],
  "model_tool_name": "Antigravity IDE AI"
}
```

### 6.3 Verification & Validation Rules
1. **Schema Check**: `schema_version == "ide_handoff_response_v1"`.
2. **Explicit Failure Check**: If `status == "failed"`, import fails with sanitized reason.
3. **Content Requirement**: `answer_markdown` or `answer_text` must be non-empty.
4. **Attribution Requirement**: `model_tool_name` must be present.
5. **Privacy Gate**: If `manifest.privacy_mode == "local_only"`, `privacy_acknowledged` MUST be `true`.
6. **Full Bundle Confirmation**: `used_full_bundle` MUST be `true`.
7. **Zero-Fabrication Citation Matching**:
   - `cited_evidence_ids` / `evidence_ids_used` must only contain IDs present in `manifest.allowed_source_ids`.
   - Unknown citations cause hard rejection.
   - Regex word-boundary matching (`\bEVD-1\b` vs `\bEVD-10\b`) prevents substring false positives.
   - Zero citations result in empty list (low confidence), NEVER fabricating `allowed_source_ids[0]`.

---

## 7. Fail-Closed & Privacy Architecture

### 7.1 Strict Fail-Closed Policy
- **Direct Mode**: When `call_antigravity_bridge` fails (HTTP 500, connection refused, offline), it returns `(False, "", None, error_message)`. The UI reports the exact error. **Zero calls are made to `RealWorkspaceAIProviderClient` or Smart Router.**
- **Handoff Mode**: When bundle writing fails or timeout expires, the request is marked `failed`. No fallback route is invoked.
- **Sidecar Daemon Isolation**: AST static analysis (`TestSidecarDaemonASTSecurity`) verifies that `scripts/antigravity_sidecar_daemon.py` contains zero imports or instantiations of `RealWorkspaceAIProviderClient` or `generate_workspace_ai_answer`.

### 7.2 Data Privacy & Sanitization Engine
- **Endpoint Locality Guard**: `is_local_endpoint(url)` validates that URLs resolve to loopback (`127.0.0.1`, `localhost`) or RFC 1918 private subnets. Non-local endpoints are blocked immediately when `privacy_mode == "local_only"`.
- **Reason Sanitizer**: `sanitize_reason()` scrubs:
  - Absolute system paths: `([A-Za-z]:)?/[a-zA-Z0-9_\-\./]+` -> `<path>`
  - API tokens and bearer credentials: `(sk-[a-zA-Z0-9_\-]+|Bearer\s+[a-zA-Z0-9_\-]+)` -> `<redacted_token>`
  - Maximum output length bounded to 200 characters.
- **Log Leakage Prevention**: Prompts, evidence text, and raw document contents are never written to logger or health responses.

---

## 8. Test Mapping & Verification Traceability

| Requirement | Feature Description | Primary Implementation | Verification Test Suite |
|---|---|---|---|
| **R1** | 6-State FSM Health & Sanitized Reasons | `src/aios_habit/antigravity_bridge.py`<br>`scripts/antigravity_sidecar_daemon.py` | `TestAntigravityHealthFSM::test_health_fsm_unavailable_when_server_offline`<br>`TestAntigravityHealthFSM::test_health_fsm_all_six_states`<br>`TestAntigravityHealthFSM::test_health_fsm_server_500_error`<br>`TestAntigravityHealthFSM::test_health_fsm_no_fake_capabilities_advertised` |
| **R1** | Sidecar Loopback Purge (AST Verification) | `scripts/antigravity_sidecar_daemon.py` | `TestSidecarDaemonASTSecurity::test_sidecar_daemon_no_forbidden_ai_imports`<br>`TestSidecarDaemonASTSecurity::test_sidecar_daemon_no_forbidden_instantiations` |
| **R1** | Direct Mode 503 Rejection & Health States | `scripts/antigravity_sidecar_daemon.py` | `TestSidecarDaemonDynamicHealth::test_evaluate_sidecar_health_empty_outbox`<br>`TestSidecarDaemonDynamicHealth::test_evaluate_sidecar_health_with_pending_requests`<br>`TestSidecarDaemonDynamicHealth::test_sidecar_rejects_direct_completion_http_503` |
| **R1, R2** | Zero-Fabrication Citation Matching | `src/aios_habit/antigravity_bridge.py`<br>`src/aios_habit/ide_handoff_bridge.py` | `TestAntigravityCitationIntegrity::test_process_handoff_with_genuine_citation`<br>`TestAntigravityCitationIntegrity::test_process_handoff_zero_citations_no_fabrication`<br>`TestAntigravityCitationIntegrity::test_process_handoff_unknown_citation_filtered`<br>`TestAntigravityCitationIntegrity::test_process_handoff_word_boundary_matching` |
| **R2** | Outbox Bundle & SHA-256 Integrity | `src/aios_habit/ide_handoff_bridge.py` | `test_ui_flow_creates_outbox_bundle_prompt_and_status`<br>`test_no_local_runs_tracked_by_git` |
| **R2** | Inbox Response Schema & Import Validation | `src/aios_habit/ide_handoff_bridge.py` | `test_inbox_response_imports_and_processed_result_written`<br>`test_wrong_request_unknown_id_missing_privacy_and_full_bundle_false_rejected` |
| **R2** | Handoff Timeout & Expiration Lifecycle | `src/aios_habit/ide_handoff_bridge.py` | `TestAntigravityCitationIntegrity::test_process_handoff_expires_stale_requests`<br>`test_ui_handoff_timeout_expiration_flow` |
| **R3** | Direct Mode Routing & Honest Attribution | `src/aios_habit/antigravity_bridge.py`<br>`src/aios_habit/workspace_chat_app.py` | `test_route_workspace_chat_direct_mode_success_and_attribution` |
| **R3** | Strict Fail-Closed Enforcement (0 Fallbacks) | `src/aios_habit/antigravity_bridge.py`<br>`src/aios_habit/ai_provider_bridge.py` | `TestAntigravityFailClosed::test_call_antigravity_bridge_offline_fails_closed`<br>`TestAntigravityFailClosed::test_call_antigravity_bridge_http_500`<br>`TestAntigravityFailClosed::test_ai_provider_bridge_offline_fail_closed`<br>`test_route_workspace_chat_direct_mode_fail_closed_never_fallbacks` |
| **R3** | UI Handoff Pending State & Header Badges | `src/aios_habit/workspace_chat_ui.py`<br>`src/aios_habit/workspace_chat_app.py` | `test_route_workspace_chat_handoff_mode_pending_state`<br>`test_render_bridge_header_status_truthfulness` |
| **R4** | Privacy Guard (`local_only`) & Log Sanitization | `src/aios_habit/antigravity_bridge.py`<br>`src/aios_habit/ide_handoff_bridge.py` | `TestAntigravityPrivacyAndSanitization::test_sanitize_bridge_error_masks_absolute_paths`<br>`TestAntigravityPrivacyAndSanitization::test_sanitize_bridge_error_masks_api_tokens`<br>`TestAntigravityPrivacyAndSanitization::test_bridge_error_does_not_leak_user_prompt`<br>`TestAntigravityPrivacyAndSanitization::test_local_only_cloud_fail_closed`<br>`test_local_only_cloud_provider_blocked_and_vi_instruction`<br>`test_bridge_manual_step_report_is_utf8_and_not_mojibake` |
| **R5** | Spec Kit Artifacts & Repository Governance | `specs/antigravity-truthful-bridge/` | Spec Kit validation & `graphify update .` |
