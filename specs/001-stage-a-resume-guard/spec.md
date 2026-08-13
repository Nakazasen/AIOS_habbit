# Feature Specification: Resumable Stage A Preparation

**Feature Branch**: `001-stage-a-resume-guard`

**Created**: 2026-08-14

**Status**: Ready for planning

**Input**: User description: "Recover the sealed benchmark artifacts where an original copy exists, then make the provider-free Workspace Chat Stage A preparation diagnosable, resumable and fail-closed before rerunning BQ01/BQ02."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resume an interrupted local preparation (Priority: P1)

An evaluation operator can resume a Stage A preparation that stopped part way through a local-only corpus without rebuilding sources that were already committed.

**Why this priority**: The current diagnostic cannot be safely repeated while a single slow source forces an opaque full restart.

**Independent Test**: Simulate a failure after one source is committed, rerun with the same frozen source identity, and verify the completed source is not sent for preparation again.

**Acceptance Scenarios**:

1. **Given** a matching incomplete checkpoint with one committed source, **When** the operator reruns Stage A, **Then** preparation resumes at the next source and retains the prior committed source.
2. **Given** a checkpoint whose candidate or corpus identity differs, **When** the operator reruns Stage A, **Then** it stops without reusing that checkpoint.

---

### User Story 2 - Identify and bound a stalled source (Priority: P2)

An evaluation operator can see safe per-source progress and receives a deterministic failure when one local preparation operation exceeds its declared deadline.

**Why this priority**: The previous run stopped at 917 chunks / 757 embeddings with no durable indication of the responsible source or a safe restart point.

**Independent Test**: Force one source preparation call to exceed its deadline and verify the checkpoint retains completed progress, records a safe opaque source identifier, and leaves the stage not ready.

**Acceptance Scenarios**:

1. **Given** a source exceeds the configured local preparation deadline, **When** Stage A processes it, **Then** it closes the worker path and reports a fail-closed timeout without marking the stage ready.
2. **Given** a source completes, **When** its commit succeeds, **Then** its progress is durably recorded before the next source begins.

---

### User Story 3 - Preserve diagnostic gate boundaries (Priority: P3)

An evaluation operator can distinguish a recoverable runtime failure from a gate-valid BQ01/BQ02 diagnostic and cannot use Stage A to initialize a live provider route.

**Why this priority**: Resumability must not weaken the frozen identity, local-only policy, or the Stage B authorization boundary.

**Independent Test**: Run the preparation path with local-only inputs and verify it exposes no provider initialization, rejects missing or mismatched identity, and produces no ready stage after a timeout.

**Acceptance Scenarios**:

1. **Given** missing sealed production evidence or an immutable NotebookLM reference, **When** the diagnostic gate is evaluated, **Then** it remains invalid rather than fabricating or substituting an artifact.
2. **Given** local-only sources, **When** Stage A is resumed, **Then** it remains provider-free and Stage B is not invoked.

### Edge Cases

- A stale checkpoint must never be reused when its frozen candidate, corpus, or source manifest identity changes.
- A failed source must not be reported as ready merely because prior sources completed.
- Empty or non-text sources must not create misleading completion records.
- Interrupted writes must leave either the prior valid checkpoint or a complete replacement, never a partial record.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Stage A MUST persist safe, per-source completion progress after each successful local commit.
- **FR-002**: Stage A MUST resume only from a checkpoint that exactly matches the frozen candidate and source/corpus identity.
- **FR-003**: Stage A MUST skip preparation work already recorded as committed by a matching checkpoint.
- **FR-004**: Stage A MUST enforce a declared per-source preparation deadline and fail closed on expiry.
- **FR-005**: A failed or timed-out source MUST leave the stage unready and preserve the restart point for completed sources.
- **FR-006**: Progress and failure evidence MUST use opaque source identities and MUST NOT persist source text, file names, credentials, or provider responses.
- **FR-007**: Stage A MUST remain provider-free for local-only sources and MUST NOT initiate Stage B synthesis.
- **FR-008**: Missing production evidence or immutable NotebookLM reference artifacts MUST remain a gate blocker; no generated replacement may be treated as sealed evidence.

### Key Entities

- **Preparation checkpoint**: Durable, identity-bound record of a Stage A run, its safe progress and terminal state.
- **Source progress entry**: Opaque source identity, completion position, and completion time for a successfully committed source.
- **Preparation deadline**: Operator-declared maximum duration for processing one source before a fail-closed result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A simulated interruption after one of three sources resumes with zero repeat preparation calls for the completed source.
- **SC-002**: A simulated timeout produces an unready stage and a checkpoint containing the last completed source within one execution attempt.
- **SC-003**: All focused adapter and staging tests pass while proving no provider call is required for Stage A.
- **SC-004**: A missing sealed artifact is reported as blocked and is never replaced by newly generated local data.

## Assumptions

- The worker's per-source commit is idempotent for an unchanged source identity.
- A bounded operator-configured per-source deadline is safer than allowing an unbounded local worker operation.
- The original sealed artifacts may only be restored from an existing original copy supplied or located by the operator; regeneration is out of scope.
- Stage B remains explicitly out of scope and locked.
