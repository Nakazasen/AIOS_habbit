# Feature Specification: Antigravity Truthful Bridge

**Feature Branch**: `specs/antigravity-truthful-bridge`
**Created**: 2026-08-22
**Status**: `VERIFIED` (US1–US6, 2026-08-22) + `M6_AUDITED_AND_FIXED` (US7 "Dự phòng tổng hợp cục bộ có trích dẫn", làm giàu 2026-09-23 — xem [plan.md](plan.md) mục 9, [research.md](research.md), [tasks.md](tasks.md) T056)
**Input**: User Request — "Xây dựng cầu nối trung thực (Truthful Bridge) cho Antigravity IDE trong repo D:\Sandbox\AIOS_habbit, loại bỏ hoàn toàn cơ chế facade/giả lập, ưu tiên direct adapter nếu có giao thức xác minh được và tự động chuyển sang handoff bất đồng bộ (Outbox/Inbox) an toàn khi direct không khả dụng."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Honest Health FSM & Protocol Verification (Priority: P1)

As a Workspace Chat user and system operator, I want the system to honestly verify whether a local Antigravity IDE integration protocol is active, reporting an explicit 6-state finite state machine status without fake capabilities or facade loopbacks.

**Why this priority**: Preventing deceptive or simulated AI behavior is the core architectural principle of AIOS WorkLens. Users must know exactly which backend answers their questions.

**Independent Test**: Start the sidecar daemon or query the bridge endpoint when offline, during pending handoff, or with verified direct adapter; verify the `/health` response matches the exact FSM state (`unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed`) and never advertises unverified capabilities (`reasoning`, `large_context`, `excel_sql`).

**Acceptance Scenarios**:
1. **Given** the sidecar daemon or bridge endpoint is offline, **When** health check is performed, **Then** status is `unavailable`, mode is `none`, and no connection exceptions crash the application.
2. **Given** the sidecar daemon is running without a verified direct IDE adapter, **When** `GET /health` is called, **Then** status is `handoff_ready` (or `handoff_pending` if requests are awaiting processing) with mode `handoff` and capability `["local_handoff"]`.
3. **Given** a direct completion request (`POST /v1/chat/completions`) is sent to the sidecar when direct adapter is not verified, **When** processed, **Then** the daemon returns HTTP 503 (`direct_adapter_unavailable`) and never generates simulated responses.
4. **Given** the sidecar source code, **When** inspected via static AST analysis, **Then** it contains zero imports or instantiations of `RealWorkspaceAIProviderClient` or synthetic fallback pipelines.

---

### User Story 2 - Asynchronous Outbox/Inbox Handoff & Lifecycle Tracking (Priority: P1)

As a Workspace Chat user, when direct IDE connection is unavailable, I want my question and context to be exported into a structured, cryptographically verified Outbox bundle so that I can inspect or process it in Antigravity IDE and have the response safely imported back via Inbox.

**Why this priority**: Asynchronous handoff provides a reliable, air-gapped integration mechanism for heavy reasoning tasks on local machines without cloud data egress.

**Independent Test**: Submit a question when in handoff mode; verify bundle creation in `local_runs/ide_handoff/outbox/<request_id>/` with 11 complete files and matching SHA-256 hash. Place a valid `response.json` in `inbox/<request_id>/` and verify automated/manual import into `processed/` and case store.

**Acceptance Scenarios**:
1. **Given** a user question with attached evidence items, **When** handoff bundle is generated, **Then** `manifest.json`, `completeness.json`, `evidence_full.jsonl`, and `prompt_for_antigravity.md` are written to outbox with matching SHA-256 checksums and `request_status.json` initialized to `handoff_pending`.
2. **Given** a pending handoff request, **When** a valid `response.json` matching `ide_handoff_response_v1` is placed in inbox, **Then** validation succeeds, the response is archived to `processed/<request_id>/`, saved to the case store as a `PastedStrongModelAnswer`, and `request_status.json` transitions to `completed`.
3. **Given** a pending handoff request, **When** elapsed time exceeds `timeout_seconds` (default 300s), **Then** timeout check transitions `request_status.json` to `failed` with `error_reason="timeout"`.

---

### User Story 3 - Workspace Chat Routing & Strict Fail-Closed Execution (Priority: P1)

As a Workspace Chat user, when I submit a question with the Antigravity bridge enabled, I want the system to route to direct mode (if `direct_ready`) or create a handoff bundle (if `handoff_ready`), and if an error or timeout occurs, report the error honestly to me without silently delegating to Smart Router.

**Why this priority**: Silent fallbacks violate user trust and could inadvertently send private local context to cloud providers against user intentions.

**Independent Test**: Simulate direct bridge network error or handoff creation failure; verify that Workspace Chat displays an explicit Vietnamese error message and makes exactly zero calls to `generate_workspace_ai_answer` or `RealWorkspaceAIProviderClient`.

**Acceptance Scenarios**:
1. **Given** bridge health is `direct_ready`, **When** the user sends a message, **Then** the message is submitted to the direct bridge, saved in chat history, and displayed with badge `Nguồn AI: Antigravity IDE (direct)`.
2. **Given** bridge health is `handoff_ready`, **When** the user sends a message, **Then** an outbox bundle is created, an assistant placeholder "⏳ Đang chờ Antigravity IDE xử lý..." is added, and the UI displays the pending banner with request ID.
3. **Given** bridge health is `direct_ready` but the direct endpoint returns HTTP 500 or network failure, **When** submission is processed, **Then** the system returns `ok=False` with sanitized error and makes 0 calls to Smart Router.

---

### User Story 4 - Citation Bounds & Zero Fabrication Policy (Priority: P2)

As a user reviewing AI responses, I want citations in Antigravity answers to be strictly verified against allowed evidence IDs from the request bundle, with zero fabricated citations.

**Why this priority**: Hallucinated or fabricated citations undermine evidence integrity and decision-making quality.

**Independent Test**: Provide model answers containing valid citations (`[EVD-1]`), zero citations, or invalid citations (`[EVD-999]`); verify that only genuine citations are kept, invalid ones cause validation failure, and answers without citations are never given fake citations.

**Acceptance Scenarios**:
1. **Given** an inbox response with evidence citations matching `allowed_source_ids`, **When** validated, **Then** citations are preserved in `evidence_ids_used` and answer confidence is `high`.
2. **Given** an inbox response containing no citations in text, **When** processed, **Then** `cited_evidence_ids` remains empty (`[]`), confidence is `low`, a limitation is recorded, and no fallback citation is fabricated.
3. **Given** an inbox response citing an evidence ID not present in `allowed_source_ids`, **When** validated, **Then** validation fails with error `unknown evidence_ids_used`.

---

### User Story 5 - Local-First Privacy & Secret Sanitization (Priority: P2)

As a security-conscious user, I want all `local_only` documents and sensitive information (file paths, API tokens) protected from external cloud leaks and masked in logs/UI.

**Why this priority**: Strict compliance with AIOS WorkLens Constitution Principle II (Local-First Privacy and Consent).

**Independent Test**: Attempt to dispatch `local_only` context to a remote IP address; verify immediate fail-closed block. Pass raw errors containing paths (`D:\...`) and API keys (`sk-...`) through `sanitize_reason`; verify replacement with `<path>` and `<redacted_token>`.

**Acceptance Scenarios**:
1. **Given** a request with `privacy_mode="local_only"`, **When** `call_antigravity_bridge` is invoked with a non-loopback endpoint URL, **Then** the request is blocked immediately before network dispatch.
2. **Given** an internal error containing full filesystem paths or API tokens, **When** error is formatted for UI or status logs, **Then** `sanitize_reason` masks paths to `<path>` and keys to `<redacted_token>`.

---

### User Story 6 - Repository Governance, Spec Kit & Graphify Compliance (Priority: P3)

As a repository maintainer, I want all Antigravity bridge features fully documented with Spec Kit artifacts (`spec.md`, `plan.md`, `tasks.md`), verified with 100% test pass rate, and synchronized with Graphify knowledge graphs.

**Why this priority**: Ensures long-term maintainability, traceability, and architectural rigor.

**Independent Test**: Validate existence of Spec Kit artifacts in `specs/antigravity-truthful-bridge/`, run test suite, and verify `graphify-out/` synchronization.

**Acceptance Scenarios**:
1. **Given** the `specs/antigravity-truthful-bridge/` directory, **When** inspected, **Then** `spec.md`, `plan.md`, and `tasks.md` exist and comply with Spec Kit standard templates.
2. **Given** the test suite `tests/test_antigravity_bridge.py` and `tests/test_antigravity_handoff_ui_flow.py`, **When** executed, **Then** all tests pass cleanly.

---

### User Story 7 - Dự phòng tổng hợp cục bộ có trích dẫn khi cầu nối không tới được (Priority: P1, làm giàu 2026-09-23)

Người dùng mất mạng hoặc cầu nối Antigravity IDE không chạy. Hệ thống vẫn báo đúng lỗi cầu nối, nhưng kèm một lời mời xem đáp án trích xuất đã được tính sẵn từ chính các đoạn tài liệu đã truy xuất trong máy. Người dùng bấm thì nhận đáp án có trích dẫn, biết rõ đây là bản tổng hợp cục bộ chưa qua mô hình, và mở được đồ thị bằng chứng như mọi đáp án khác.

**Vì sao ưu tiên này**: Người dùng xưởng làm việc trong mạng nội bộ, cầu nối chết là chuyện thường. Hiện tại khi đó không có đường trả lời nào có trích dẫn, dù động cơ tổng hợp cục bộ đã tính xong kết quả và kết quả đó đang bị vứt đi. Đây là mất mát thuần tuý, không phải đánh đổi.

**Kiểm thử độc lập**: Tắt cầu nối, hỏi một câu có nguồn đã sẵn sàng. Báo lỗi cầu nối hiện ra kèm nút mời. Bấm nút thì hội thoại có đáp án mang nhãn cục bộ cùng danh sách trích dẫn, và nút `Xem đồ thị bằng chứng` hoạt động. Không có lời gọi mạng nào phát sinh.

**Tình huống nghiệm thu**:

1. **Given** cầu nối không tới được và đáp án cục bộ có căn cứ, **When** người dùng gửi câu hỏi, **Then** hệ thống báo đúng lỗi cầu nối kèm lời mời xem dự phòng, và chưa ghi gì vào hội thoại.
2. **Given** lời mời đang hiện, **When** người dùng bấm nút, **Then** hội thoại có câu hỏi, đáp án trích xuất, danh sách trích dẫn, và một dấu vết bằng chứng hợp lệ.
3. **Given** đáp án cục bộ rỗng hoặc động cơ đã tự chối trả lời, **When** người dùng gửi câu hỏi, **Then** chỉ có lỗi cầu nối, không có lời mời rỗng.
4. **Given** nhánh dự phòng đang chạy, **When** đối chiếu, **Then** không có lời gọi nào ra Smart Router, `RealWorkspaceAIProviderClient`, hay bất kỳ nhà cung cấp nào.
5. **Given** đáp án cục bộ có giới hạn, **When** hiển thị, **Then** người dùng thấy lý do giới hạn, không bị giấu.

---

### Edge Cases

- **Cầu nối chết, dự phòng rỗng**: chỉ hiện lỗi cầu nối; không hiện lời mời rỗng.
- **Cầu nối chết, động cơ tự chối trả lời**: như trên; lý do tự chối không đưa lên như thể là đáp án.
- **Cầu nối chết, truy xuất chưa chạy**: không có đáp án cục bộ để mời; giữ nguyên lỗi.
- **Dữ liệu đổi giữa lúc mời và lúc bấm**: từ chối ghi, báo tiếng Việt, không tạo tin nhắn nửa vời.
- **Bấm nút hai lần**: chỉ một cặp tin nhắn được ghi.
- **Đáp án cục bộ vượt ngân sách ký tự**: động cơ đã tự chuyển thành từ chối; rơi về nhánh "chỉ hiện lỗi cầu nối".
- **Sidecar Offline**: `get_antigravity_bridge_health` returns `status="unavailable"`, `mode="none"`, `is_available=False`; UI shows "⚪ Cầu nối chưa kết nối".
- **Sidecar Internal Crash (HTTP 500)**: Bridge maps response to `status="failed"` with sanitized reason; UI shows "🔴 Cầu nối lỗi: <sanitized_reason>".
- **Legacy Status String**: If external service returns legacy `"ok"`, bridge normalizes it to `FSM_HANDOFF_READY`.
- **Unverified Capabilities in Payload**: Bridge strips unknown capabilities, retaining only `direct_chat` and `local_handoff`.
- **Direct Rejection without Adapter**: Sidecar daemon responds HTTP 503 (`direct_adapter_unavailable`) on `POST /v1/chat/completions`.
- **Bundle Oversize Guard**: Requests exceeding 2,000,000 text characters raise `ValueError` to prevent truncated exports.
- **Request Expiration**: Outbox requests exceeding `timeout_seconds` (default 300s) transition to `failed` (`error_reason: "timeout"`).
- **Missing / Corrupt Bundle Files**: If `manifest.json` or `completeness.json` is missing or corrupted, integrity check fails.
- **SHA-256 Mismatch**: Any tampering with `evidence_full.jsonl` results in validation failure.
- **Schema Mismatch**: Inbox responses not matching `ide_handoff_response_v1` are rejected with explicit schema errors.
- **Explicit Failure from IDE**: Inbox responses with `status="failed"` transition request status to `failed` with sanitized reason.
- **Local-Only Privacy Unacknowledged**: Inbox responses for `local_only` bundles with `privacy_acknowledged != True` are rejected.
- **Partial Bundle Usage**: Inbox responses with `used_full_bundle != True` are rejected.
- **Unknown Citation IDs**: Responses citing IDs outside `allowed_source_ids` are rejected.
- **Zero Citations**: Answers without citations are accepted as `review_required` (confidence `low`), never injected with fake citations.
- **Word Boundary Collisions**: Evidence regex ensures `EVD-10` does not match `EVD-1`.
- **Remote IP with Local-Only Data**: Direct bridge call blocked immediately when endpoint is not a loopback address.
- **Git Leakage Prevention**: `local_runs/ide_handoff/` is completely excluded from git tracking via `.gitignore`.

---

## Requirements *(mandatory)*

### Functional Requirements

#### R1: Protocol Verification & Honest Health Status
- **FR-001**: The system MUST implement a 6-state Finite State Machine (FSM) for bridge health: `unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed`.
- **FR-002**: The bridge client MUST query `GET /health` and return a structured `AntigravityHealthStatus` dataclass.
- **FR-003**: The sidecar daemon MUST evaluate local health dynamically based on outbox request queue state and direct adapter verification.
- **FR-004**: The sidecar daemon MUST return HTTP 503 on direct completion requests (`POST /v1/chat/completions`) when direct adapter is not verified.
- **FR-005**: The sidecar daemon MUST NOT import, instantiate, or call `RealWorkspaceAIProviderClient` or synthetic AI pipelines (enforced via AST testing).
- **FR-006**: The bridge MUST filter advertised capabilities, only permitting `direct_chat` and `local_handoff`, and never advertising unverified capabilities (`reasoning`, `large_context`, `excel_sql`).

#### R2: Asynchronous Handoff & Outbox/Inbox Lifecycle
- **FR-007**: The handoff system MUST create unique outbox bundles (`REQ-YYYYMMDD-HHMMSS-<HEX>`) under `local_runs/ide_handoff/outbox/<request_id>/`.
- **FR-008**: Outbox bundles MUST include all required files: `manifest.json`, `evidence_bundle.json`, `question.md`, `prompt.md`, `prompt_for_antigravity.md`, `evidence_full.jsonl`, `evidence_full.md`, `source_manifest.json`, `completeness.json`, `README_FOR_IDE.md`, and `request_status.json`.
- **FR-009**: Outbox bundles MUST compute a SHA-256 hash across canonical evidence records and synchronize the hash between `manifest.json` and `completeness.json`.
- **FR-010**: The handoff system MUST enforce a 3-state request lifecycle: `handoff_pending` -> `completed` or `failed`.
- **FR-011**: The system MUST enforce request timeouts (default 300 seconds), automatically transitioning expired pending requests to `failed` (`error_reason: "timeout"`).
- **FR-012**: The system MUST validate inbox responses against schema `RESPONSE_SCHEMA_VERSION = "ide_handoff_response_v1"`.
- **FR-013**: Inbox responses MUST satisfy integrity requirements: `privacy_acknowledged == True` for `local_only` bundles, `used_full_bundle == True`, and valid non-empty `model_tool_name`.
- **FR-014**: The system MUST validate citations against `allowed_source_ids`, rejecting unknown IDs and strictly forbidding citation fabrication.
- **FR-015**: Validated inbox responses MUST be atomically archived to `local_runs/ide_handoff/processed/<request_id>/` and saved to the case store as `PastedStrongModelAnswer`.

#### R3: Workspace Chat Integration & Strict Fail-Closed Behavior
- **FR-016**: Workspace Chat submission router MUST route to Direct adapter when health is `direct_ready`.
- **FR-017**: Workspace Chat submission router MUST route to Handoff bundle creation when health is `handoff_ready` or `handoff_pending`.
- **FR-018**: When handoff bundle is created, Workspace Chat MUST display assistant pending placeholder `"⏳ Đang chờ Antigravity IDE xử lý..."` and render the active handoff banner.
- **FR-019**: If direct bridge or handoff creation fails, the system MUST return an explicit error and MUST NOT fallback to Smart Router or `RealWorkspaceAIProviderClient`.
- **FR-020**: Fallback to Smart Router MUST only occur when the bridge is completely disabled or reported `unavailable` before submission. (Phạm vi: lệnh cấm này áp dụng cho dự phòng **ra nhà cung cấp khác**. Nhánh dự phòng **cục bộ trong máy** ở mục R6 không phải dự phòng nhà cung cấp, không gọi mạng, và chỉ chạy khi người dùng chủ động chọn.)
- **FR-021**: The UI MUST display attribution `"Nguồn AI: Antigravity IDE (direct/handoff)"` only when the response originated from Antigravity.
- **FR-022**: The UI header status MUST render truthful status badges matching the 6 FSM states.
- **FR-023**: UI refresh triggers MUST accurately query `/health` and re-evaluate pending handoff requests.

#### R4: Security, Privacy & Logging Sanitization
- **FR-024**: The system MUST block any attempt to send `local_only` context or bundles to non-local endpoints (`is_local_endpoint == False`).
- **FR-025**: The system MUST sanitize error messages and logs using `sanitize_reason`, masking filesystem paths to `<path>` and API tokens to `<redacted_token>`.

#### R6: Dự phòng Tổng hợp Cục bộ có Trích dẫn (làm giàu 2026-09-23)

Mở rộng có kiểm soát cho `FR-019`/`FR-020`: lệnh cấm dự phòng **ra nhà cung cấp khác** giữ nguyên hiệu lực tuyệt đối. Nhánh mới là dự phòng **cục bộ trong máy**, không gọi mạng, và chỉ chạy khi người dùng chủ động chọn.

- **FR-026**: Khi cả ba đường nhà cung cấp không tới được, hàm định tuyến MUST vẫn trả lỗi cầu nối như hiện nay, VÀ nếu có đáp án tổng hợp cục bộ dùng được thì MUST kèm cờ mời người dùng xem dự phòng. Đáp án cục bộ MUST NOT được ghi vào hội thoại ở bước này.
- **FR-027**: Vòng xử lý câu hỏi MUST chuyển kết quả tổng hợp cục bộ đã có sẵn trong kết quả truy xuất vào hàm định tuyến. Kết quả này MUST NOT bị tính rồi bỏ đi khi đường nhà cung cấp không tới được.
- **FR-028**: Hệ thống MUST có hàm ghi đáp án cục bộ dùng lại đúng bộ ba đã dùng cho các nhánh khác: ghi tin nhắn người dùng, dựng dấu vết bằng chứng từ trích dẫn, lưu dấu vết, ghi tin nhắn trả lời. Dấu vết MUST đối chiếu trích dẫn với tài liệu đã bật như mọi dấu vết khác.
- **FR-029**: Hàm ghi đáp án cục bộ MUST từ chối khi đáp án rỗng, khi động cơ đã tự chối trả lời, hoặc khi không có câu nào gắn được trích dẫn. Khi từ chối MUST trả lý do tiếng Việt và MUST NOT tạo tin nhắn nào.
- **FR-030**: Đáp án cục bộ MUST mang nhãn tiếng Việt nói rõ đây là bản tổng hợp từ trích đoạn chưa qua mô hình. Hệ thống MUST NOT gắn tên `Antigravity IDE`, tên mô hình, hay bất kỳ nhãn nhà cung cấp nào cho đáp án cục bộ. Khi có lý do giới hạn, người dùng MUST thấy lý do đó.
- **FR-031**: Suốt nhánh dự phòng MUST có đúng 0 lời gọi ra Smart Router, `RealWorkspaceAIProviderClient`, hay bất kỳ nhà cung cấp nào. `SC-006` giữ nguyên hiệu lực và được kiểm ở nhánh mới.
- **FR-032**: Nhánh dự phòng MUST NOT thay đổi chữ ký trả về của hàm định tuyến, để mọi lời gọi hiện có giữ nguyên hành vi khi không truyền tham số mới.

---

### Key Entities

- **AntigravityHealthStatus**: Immutable status dataclass containing `status` (6 FSM states), `mode` (`direct|handoff|none`), `capabilities` (list of strings), `reason` (sanitized string), and `raw_payload` (dict).
- **Outbox Bundle**: Directory containing 11 files (`manifest.json`, `evidence_bundle.json`, `question.md`, `prompt.md`, `prompt_for_antigravity.md`, `evidence_full.jsonl`, `evidence_full.md`, `source_manifest.json`, `completeness.json`, `README_FOR_IDE.md`, `request_status.json`) capturing full question context and cryptographic proof.
- **Inbox Response (`ide_handoff_response_v1`)**: JSON document deposited by Antigravity IDE containing `request_id`, `schema_version`, `status`, `answer_markdown`/`answer_text`, `cited_evidence_ids`/`evidence_ids_used`, `limitations`, `confidence`, `privacy_acknowledged`, `used_full_bundle`, and `model_tool_name`.
- **Request Lifecycle State**: Discrete state in `request_status.json` (`handoff_pending`, `completed`, `failed`) tracking progress timestamps and error reasons.
- **PastedStrongModelAnswer**: Domain entity representing validated external model responses saved to the evidence vault with full provenance.
- **LocalGroundedFallback** (làm giàu 2026-09-23): Lời mời dự phòng gắn với một lượt hỏi khi cầu nối không tới được. Thuộc tính: `answer` (đáp án trích xuất), `citation_ids` (nhãn trích dẫn đã đối chiếu), `grounded` (có căn cứ hay không), `abstained` (động cơ tự chối hay không), `answer_mode` (`answer` hoặc `answer_with_limits`), `limitation_reasons` (lý do giới hạn). Không có nhà cung cấp nào gắn với thực thể này; `provider_used` luôn là `False`.

---

## Interface Contracts *(mandatory)*

### 1. Sidecar Daemon HTTP API

#### `GET /health`
- **Request**: `GET /health HTTP/1.1`
- **Response**: HTTP 200 OK
- **Payload Schema**:
  ```json
  {
    "status": "unavailable | direct_ready | handoff_ready | handoff_pending | completed | failed",
    "mode": "direct | handoff | none",
    "service": "antigravity_ide_brain_sidecar",
    "version": "1.0.0",
    "capabilities": ["direct_chat", "local_handoff"],
    "reason": "<sanitized_string>"
  }
  ```

#### `POST /v1/chat/completions` (Direct Chat)
- **Request**: `POST /v1/chat/completions HTTP/1.1`
- **Request Payload**: OpenAI-compatible chat completion payload (`model`, `messages`, `temperature`, `stream`).
- **Response (when direct adapter unverified)**: HTTP 503 Service Unavailable
  ```json
  {
    "error": {
      "message": "Antigravity IDE direct chat completion is unavailable. Please use asynchronous handoff mode.",
      "type": "direct_adapter_unavailable",
      "code": 503,
      "status": "unavailable"
    }
  }
  ```

---

### 2. Outbox Bundle Manifest Contract (`manifest.json`)
```json
{
  "request_id": "REQ-YYYYMMDD-HHMMSS-XXXXXXXX",
  "created_at": "2026-08-22T00:00:00.000000",
  "expires_at": "2026-08-22T00:05:00.000000",
  "timeout_seconds": 300,
  "case_id": "conv_xxx",
  "question": "User question...",
  "bundle_scope": "active_case_all | selected_folder_all | current_question_retrieval_plus_full_scope_manifest",
  "privacy_mode": "local_only | cloud_safe",
  "privacy_level": "local_only | cloud_safe",
  "local_only": true,
  "allowed_external": false,
  "source_count": 2,
  "evidence_item_count": 2,
  "chunk_count": 2,
  "total_text_chars": 1500,
  "extraction_formats": ["pdf", "markdown"],
  "source_files": ["doc1.pdf", "doc2.md"],
  "allowed_source_ids": ["EVD-1", "EVD-2"],
  "evidence_refs": [
    {
      "evidence_id": "EVD-1",
      "title": "Document 1",
      "source_type": "pdf",
      "privacy_level": "local_only"
    }
  ],
  "expected_response_schema": "ide_handoff_response_v1",
  "omitted_items_count": 0,
  "omitted_reason": "",
  "FULL_BUNDLE_COMPLETE": "YES",
  "bundle_sha256": "<64_hex_chars>",
  "model_instruction": "...",
  "response_schema_version": "ide_handoff_response_v1",
  "owner_note": "Sổ: ... | Hội thoại: ...",
  "target_model_tool_name": "Antigravity IDE AI",
  "automatic_provider_call_made": false,
  "notebooklm_parity_claimed": false,
  "p1_opened": false
}
```

---

### 3. Inbox Response Schema (`ide_handoff_response_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "IDEHandoffResponseV1",
  "type": "object",
  "required": [
    "schema_version",
    "request_id",
    "status",
    "answer_markdown",
    "cited_evidence_ids",
    "privacy_acknowledged",
    "used_full_bundle",
    "model_tool_name"
  ],
  "properties": {
    "schema_version": { "type": "string", "enum": ["ide_handoff_response_v1"] },
    "request_id": { "type": "string", "pattern": "^REQ-[0-9]{8}-[0-9]{6}-[A-F0-9]+$" },
    "status": { "type": "string", "enum": ["completed", "failed"] },
    "answer_markdown": { "type": "string" },
    "answer_text": { "type": "string" },
    "cited_evidence_ids": { "type": "array", "items": { "type": "string" } },
    "evidence_ids_used": { "type": "array", "items": { "type": "string" } },
    "limitations": { "type": "array", "items": { "type": "string" } },
    "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
    "confidence_label": { "type": "string" },
    "privacy_acknowledged": { "type": "boolean" },
    "used_full_bundle": { "type": "boolean" },
    "unsupported_claims": { "type": "array", "items": { "type": "string" } },
    "recommended_next_actions": { "type": "array", "items": { "type": "string" } },
    "model_tool_name": { "type": "string" },
    "error": { "type": "string" },
    "reason": { "type": "string" }
  }
}
```

---

### 4. Request Status Contract (`request_status.json`)
```json
{
  "request_id": "REQ-YYYYMMDD-HHMMSS-XXXXXXXX",
  "state": "handoff_pending | completed | failed",
  "created_at": "2026-08-22T00:00:00.000000",
  "updated_at": "2026-08-22T00:00:00.000000",
  "timeout_seconds": 300,
  "expires_at": "2026-08-22T00:05:00.000000",
  "outbox_dir": "local_runs/ide_handoff/outbox/REQ-...",
  "expected_inbox_response_path": "local_runs/ide_handoff/inbox/REQ-.../response.json",
  "completed_at": "",
  "imported_at": "",
  "failed_at": "",
  "saved_answer_id": "",
  "error": "",
  "error_reason": ""
}
```

---

## Security & Privacy Rules

1. **Local-First Boundary**: Documents marked `local_only` or `privacy_level="local_only"` MUST NEVER be transmitted over non-loopback network connections.
2. **Sanitization Protocol**: All error messages, log records, and status reports MUST pass through `sanitize_reason` to replace paths with `<path>` and credentials with `<redacted_token>`. Max length is 200 characters.
3. **Citation Integrity Protocol**: Citations in responses MUST strictly match evidence IDs in the bundle manifest. Citations MUST NEVER be fabricated.
4. **AST Anti-Facade Rule**: The sidecar daemon MUST NOT contain references to fallback AI providers or mock generators.
5. **Fail-Closed Execution**: Any bridge failure, network error, timeout, or schema mismatch MUST halt the bridge execution and notify the user with an explicit error.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `/health` queries return one of the 6 defined FSM states without unhandled exceptions.
- **SC-002**: 100% of direct completion attempts to sidecar without verified adapter return HTTP 503 with zero fake tokens generated.
- **SC-003**: 100% of outbox bundles contain valid cryptographic SHA-256 checksums matching between manifest and completeness files.
- **SC-004**: 100% of expired pending requests transition to `failed` (`error_reason: "timeout"`) within one timeout check cycle.
- **SC-005**: 100% of invalid inbox responses (schema mismatch, unacknowledged privacy, unknown citation IDs) are rejected without data corruption.
- **SC-006**: In 100% of simulated bridge failure scenarios, zero fallback calls are made to Smart Router / `RealWorkspaceAIProviderClient`.
- **SC-007**: 0 occurrences of absolute filesystem paths or API tokens in sanitized logs, error messages, and health status reasons.
- **SC-008**: 100% of automated unit and integration tests pass cleanly.
- **SC-009**: Với cầu nối không tới được và đáp án cục bộ có căn cứ, 100% lượt gửi câu hỏi trả về lỗi cầu nối kèm đúng một lời mời xem dự phòng, và 0 tin nhắn nào được ghi ở bước đó.
- **SC-010**: 100% lượt bấm nút dự phòng hợp lệ tạo ra một cặp tin nhắn và một dấu vết bằng chứng có `status="valid"`, đủ để nút đồ thị bằng chứng hoạt động.
- **SC-011**: 100% lượt bấm nút khi đáp án cục bộ rỗng hoặc đã tự chối trả lời bị từ chối và ghi 0 tin nhắn.
- **SC-012**: 0 lời gọi ra Smart Router, `RealWorkspaceAIProviderClient`, hay bất kỳ nhà cung cấp nào trong suốt nhánh dự phòng.
- **SC-013**: 100% đáp án cục bộ mang nhãn tiếng Việt nói rõ chưa qua mô hình, và 0 đáp án cục bộ nào mang tên mô hình hay nhãn `Antigravity IDE`.

---

## Assumptions

- Direct IDE adapter integration requires an authenticated, locally verified protocol daemon; in the absence of such a protocol, asynchronous handoff is the primary operational mode.
- The default handoff timeout is 300 seconds (5 minutes), configurable via `DEFAULT_HANDOFF_TIMEOUT_SECONDS`.
- Local handoff files in `local_runs/ide_handoff/` are ephemeral runtime artifacts excluded from version control.
- Workspace Chat operates in Vietnamese-first mode, presenting localized status messages and error explanations.
