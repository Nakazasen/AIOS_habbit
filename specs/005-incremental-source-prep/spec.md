# Feature Specification: Incremental Source Preparation

**Feature Branch**: `005-incremental-source-prep`

**Created**: 2026-08-22

**Trạng thái**: `IMPLEMENTED_PENDING_BROWSER_SMOKE` — code/test đã có; còn cần smoke trình duyệt với nguồn thật

> Checklist cũ trong `tasks.md` của đặc tả này là dấu vết lập kế hoạch, không phải 35 việc cần viết lại. Trạng thái thực thi hiện tại được theo dõi trong `ROADMAP.md` và Đợt 0 của đặc tả 008.

**Input**: Make Workspace Chat prepare every new or changed searchable document in the background, keep previously ready documents searchable, show trustworthy progress, and avoid requiring the user to ask the same question again.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask from a newly added document (Priority: P1)

An operator adds a document and asks a question using it. The operator sees that only that document is being prepared, and the original question completes automatically when preparation succeeds.

**Why this priority**: It removes the current dead-end where the operator must wait and manually submit the same question again.

**Independent Test**: Add one unprepared document, submit a question scoped to it, then complete preparation and verify exactly one answer is produced without a second submit.

**Acceptance Scenarios**:

1. **Given** a newly added enabled document, **When** the operator submits a question that selects it, **Then** the chat shows preparation status for that document and retains the question as pending.
2. **Given** preparation succeeds, **When** the page refreshes or polls again, **Then** the retained question is answered once without further operator input.
3. **Given** preparation fails, **When** the operator views the status, **Then** the failure identifies the affected document and offers a retry without affecting ready documents.

---

### User Story 2 - Continue using ready documents (Priority: P1)

An operator can continue asking questions from already ready documents while other documents are being prepared.

**Why this priority**: Adding a file must not take the existing knowledge base offline.

**Independent Test**: With one ready and one preparing document, submit a question that clearly selects the ready document and verify it proceeds without waiting for the new one.

**Acceptance Scenarios**:

1. **Given** a ready document and an unrelated preparing document, **When** the operator asks a specific question about the ready document, **Then** the answer path does not wait for the unrelated document.
2. **Given** a vague question for which a safe narrow scope cannot be identified, **When** some enabled documents are still preparing, **Then** the chat asks the operator to narrow the question or choose sources instead of starting a whole-library preparation job.

---

### User Story 3 - Understand document readiness (Priority: P2)

An operator can see which documents are ready, preparing, failed, or not yet prepared, and can retry only failed documents.

**Why this priority**: Readiness must be visible and actionable instead of appearing as a generic search error.

**Independent Test**: Render each readiness state and verify the displayed scope, message, and retry action are correct.

**Acceptance Scenarios**:

1. **Given** a document has completed preparation, **When** its source row is rendered, **Then** it is shown as ready for search.
2. **Given** a document is preparing or fails, **When** its source row is rendered, **Then** the status and the available recovery action are shown in Vietnamese.

### User Story 4 - Let background preparation finish the library (Priority: P1)

After a successful upload, the operator can return to work while AIOS gradually prepares every new or changed enabled source. The operator sees compact overall progress and the source currently being read.

**Acceptance Scenarios**:

1. **Given** new or changed sources after an upload, **When** the upload has completed, **Then** AIOS queues all searchable sources in the background and returns control immediately.
2. **Given** the application remains open, **When** preparation completes one source, **Then** it automatically proceeds to the next pending source until none remain.
3. **Given** the application restarts mid-queue, **When** the notebook is opened again, **Then** unfinished sources are rediscovered from durable state and preparation resumes without re-reading unchanged ready sources.
4. **Given** a question needs an unready source, **When** it is submitted, **Then** that source is raised ahead of ordinary background work and the question is answered once it is ready.

### Edge Cases

- A source is deleted, disabled, or changed while its preparation or a pending question is waiting.
- The BGE deployment is unavailable: no background job must be falsely reported as active.
- A pending question becomes stale after five minutes or after its source selection changes.
- A question is too broad to safely select a small source set; it must not start a second whole-library job, but an existing upload queue continues.
- The process closes while a source is preparing; it must not remain falsely marked as preparing after restart.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST queue every new or changed searchable document in the background after a successful upload or restore when local BGE retrieval is available.
- **FR-001a**: The queue MUST use one CPU preparation worker at a time, continue until no eligible pending source remains, and not block the upload or normal Streamlit interaction.
- **FR-001b**: A question-selected source MAY be promoted ahead of normal background work; an already-ready source question MUST not wait for unrelated work.
- **FR-002**: The system MUST reuse a ready document's existing search preparation across application restarts when its content and configured model identity still match.
- **FR-003**: The system MUST retain a question blocked only by source preparation and automatically continue it once all selected sources are ready.
- **FR-004**: The system MUST never submit the same retained question more than once.
- **FR-005**: The system MUST allow questions scoped to ready documents to proceed while unrelated documents prepare.
- **FR-006**: When a safe narrow scope cannot be inferred and any required source is unready, the system MUST request a narrower question or source selection instead of starting a second query-triggered whole-library job.
- **FR-007**: The system MUST display Vietnamese readiness, failure, and retry information for each source.
- **FR-008**: The system MUST discard a pending question if it becomes stale, its selected sources change, or those sources are deleted or disabled.
- **FR-009**: The system MUST preserve the existing fail-closed behavior when the BGE deployment is unavailable.
- **FR-010**: The retrieval request MUST use the exact bounded source scope whose readiness was checked; it MUST NOT re-expand to every enabled source after a pending question is released.
- **FR-011**: An interactive question may prepare at most one previously unprepared source automatically. The waiting UI MUST state the number of sources involved and allow the operator to cancel the pending question without cancelling safe background indexing.
- **FR-012**: The system MUST persist readiness, failure reason, model identity, source fingerprint, and queue priority durably so it can recover after a Streamlit rerun or process restart.
- **FR-013**: The screen MUST show compact overall progress (`ready / total`, current source, pending, failed) and each source row MUST show its individual readiness state and retry action.
- **FR-014**: AI provenance MUST distinguish bridge, generation provider, and verified model identity. A local alias or requested model name MUST NOT be displayed as a verified upstream model.
- **FR-015**: Evidence display MUST group multiple retrieved chunks from the same document and show their chunk count and available location, rather than repeating the same filename as separate documents.

### Key Entities

- **Source readiness**: The searchable state of one document for one model and content version.
- **Pending question**: A user-submitted question held only while its selected sources are prepared.
- **Source selection snapshot**: The exact set of enabled documents that a pending question may use.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test with one new relevant document, the user submits a question once and receives at most one answer after preparation completes.
- **SC-002**: In a test with at least one ready and one unrelated preparing document, a specific question about the ready document proceeds without waiting for the unrelated document.
- **SC-003**: A broad question with unready sources never starts preparation for every enabled document automatically.
- **SC-004**: Every source readiness state is visible in Vietnamese and failed sources can be retried individually.
- **SC-005**: A released pending question cannot fail solely because retrieval re-selected an unprepared source outside its previously checked scope.
- **SC-006**: With 75 queued sources, the UI returns immediately after upload and visibly progresses until each source is ready or failed; it does not require a follow-up question to continue.
- **SC-007**: A model alias such as `antigravity-brain-pro` is never presented as a verified Gemini model name.

## Assumptions

- BGE-M3 may be unavailable; this feature must not bypass its deployment validation.
- Existing document storage and source selection scopes remain unchanged.
- Automatic continuation is limited to the current conversation and expires after five minutes.
- The existing local source fingerprint is the authority for identifying changed content.
- Interactive preparation favours a single best matching source; broader document coverage remains an explicit, user-controlled action.
