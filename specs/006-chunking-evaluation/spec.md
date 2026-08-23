# Feature Specification: Evidence-Based Chunking Evaluation

**Feature Branch**: `006-chunking-evaluation`  
**Created**: 2026-08-24  
**Status**: Draft  
**Input**: User description: "Evaluate and improve RAG chunking only when measured evidence proves a gain; cover Vietnamese, Japanese, and Chinese documents without assuming overlap is automatically better."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify whether a chunking change is worthwhile (Priority: P1)

As a Workspace Chat owner, I can compare the current chunking against defined candidate strategies using the same representative documents and questions, so I can approve only a change that improves finding the right evidence without making normal use unacceptably slow.

**Why this priority**: Adding overlap or changing boundaries without measurement can increase duplicate vectors, CPU time, and poor citations while appearing more sophisticated.

**Independent Test**: Run the evaluation with the unchanged current strategy and at least one candidate; inspect a local report containing retrieval accuracy, citation support, latency, index size, chunk distribution, and failures by language.

**Acceptance Scenarios**:

1. **Given** a frozen evaluation corpus and question set, **When** the owner runs a baseline evaluation, **Then** the system records enough detail to reproduce the baseline without changing the existing runtime index.
2. **Given** a candidate strategy, **When** it is evaluated against the same inputs, **Then** the report compares it directly with the baseline and labels it `improved`, `neutral`, or `rejected` rather than assuming it is better.

---

### User Story 2 - Preserve sentence meaning in Vietnamese, Japanese, and Chinese (Priority: P1)

As a user who searches multilingual factory documentation, I receive evidence that does not split a sentence in the middle merely because the language uses `。`, `！`, or `？` instead of English punctuation.

**Why this priority**: Japanese and Chinese documents are already present in the indexed snapshot; a boundary rule designed only for spaces can cut their meaning at an arbitrary character position.

**Independent Test**: Run a multilingual boundary fixture suite containing long Vietnamese, Japanese, and Chinese passages and questions whose answer crosses a former chunk boundary.

**Acceptance Scenarios**:

1. **Given** a long Japanese or Chinese sentence ending in recognised sentence punctuation before the size limit, **When** it is divided, **Then** the boundary occurs at that punctuation rather than in the middle of the sentence.
2. **Given** a passage with no safe boundary before the limit, **When** it is divided, **Then** the report records this fallback and the resulting chunks stay within the configured safety limit.

---

### User Story 3 - Prevent navigation summaries from becoming false evidence (Priority: P2)

As a reviewer, I can tell whether a document summary helped locate a document without allowing it to displace the detailed source passage needed to support an answer.

**Why this priority**: A summary is useful for navigation but is not equivalent to the original procedure, table row, or engineering parameter.

**Independent Test**: Evaluate general and cross-source questions where both a summary and a detailed evidence chunk are available, then inspect which items reach the final evidence pack.

**Acceptance Scenarios**:

1. **Given** a question requiring a precise value or procedure, **When** a document summary and a detailed chunk are both relevant, **Then** the detailed chunk remains available as the answer's supporting evidence.
2. **Given** a summary cannot be supported by an eligible detailed source, **When** the system prepares an answer, **Then** it does not present the summary as a sufficient factual citation.

---

### User Story 4 - Avoid spending effort on inactive legacy paths (Priority: P3)

As the product owner, I can see whether the fixed-width/truncating legacy chunkers are invoked by the Workspace Chat RAG path before approving any work on them.

**Why this priority**: Correcting unused code does not improve the user-facing retrieval path and adds regression risk.

**Independent Test**: Produce a trace or call inventory for an actual Workspace Chat ingestion and query run, distinguishing RAG v2 from comparison or legacy flows.

**Acceptance Scenarios**:

1. **Given** the supported Workspace Chat BGE path, **When** a document is prepared and queried, **Then** the report identifies the responsible chunking path.
2. **Given** a legacy chunker is not on that path, **When** evaluation completes, **Then** it is explicitly out of scope for this feature.

### Edge Cases

- A source can contain tables, spreadsheets, OCR text, headings, blank spacer rows, and more than one language.
- A candidate can increase recall while producing too many duplicated chunks or exceeding CPU/latency limits.
- A malformed or empty source must not be counted as a retrieval success.
- Evaluation artifacts must not expose `local_only` document text outside the local workspace.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST establish a reproducible baseline for the current Workspace Chat RAG v2 chunking behavior before changing it.
- **FR-002**: The evaluation MUST use the same frozen corpus and question set for every compared strategy and retain local provenance for each expected evidence source.
- **FR-003**: The evaluation MUST include multilingual boundary cases for Vietnamese, Japanese, and Simplified Chinese, including questions that need text on both sides of a former boundary.
- **FR-004**: The evaluation MUST report retrieval quality, support for final citations, warm-query latency, preparation time, index size, total chunk count, and chunk-length distribution for every strategy.
- **FR-005**: The evaluation MUST compare the current no-overlap strategy with one or more bounded, sentence-aware candidate strategies; a candidate MUST be rejected if it does not meet the stated quality and resource gates.
- **FR-006**: The system MUST distinguish document-navigation summaries from detailed answer evidence and test whether summaries crowd the final evidence pack.
- **FR-007**: The system MUST record whether each evaluated query used the supported RAG v2 chunking path, and MUST NOT change legacy chunkers unless runtime evidence places them on the supported Workspace Chat path.
- **FR-008**: The system MUST preserve table, page, sheet, row, section, and privacy provenance through every candidate strategy.
- **FR-009**: All evaluation reports, fixtures, and logs MUST remain local; raw `local_only` source content MUST not be copied into cloud prompts, commits, or public reports.
- **FR-010**: No candidate chunking strategy may replace the current production/default behavior until it has a recorded acceptance decision and a rollback path.

### Key Entities

- **Evaluation corpus**: A frozen local set of representative documents and source identities used across all comparisons.
- **Question-evidence case**: A question with expected supporting source passages, language, query category, and boundary challenge label.
- **Chunking strategy**: A named, versioned set of boundary and context rules evaluated against the baseline.
- **Evaluation run**: A reproducible comparison record with corpus identity, strategy identity, measured outcomes, and a pass/reject decision.
- **Summary evidence outcome**: The relation between a navigation summary, detailed source chunks, and the evidence finally offered to an answer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every evaluated strategy has a reproducible local report covering 100% of the frozen question-evidence cases and identifies the supporting source selected for each case.
- **SC-002**: The multilingual fixture suite has no sentence-midpoint split when recognised Vietnamese, Japanese, or Chinese sentence punctuation is available within the permitted boundary window.
- **SC-003**: A candidate is eligible for adoption only if it improves expected-evidence retrieval by at least 5 percentage points or fixes a confirmed multilingual boundary failure, while warm-query latency increases by no more than 25% and index size by no more than 25% versus baseline.
- **SC-004**: For every precise-value or procedure case with detailed evidence available, the final evidence pack includes at least one detailed chunk rather than relying only on a document summary.
- **SC-005**: The final recommendation explicitly identifies the active user-facing chunking path and labels legacy-path work as included or excluded with evidence.

## Assumptions

- This feature is evaluation-first: it does not change default chunking, BGE-M3 configuration, retrieval provider routing, or document deletion behavior until evidence selects a candidate.
- Existing local Workspace Chat documents and the validated question corpus can be used only through local paths and anonymized identifiers in reports.
- The 5-point quality, 25% latency, and 25% index-size gates are initial owner-facing defaults; a later approved plan may tighten them for the actual hardware and corpus.
- Table-aware chunking, parent context, and Excel compaction remain protected baseline behavior unless a measured regression demonstrates a defect.
- RAG v1 code is not in scope unless an actual Workspace Chat trace proves it is used for the supported BGE path.
