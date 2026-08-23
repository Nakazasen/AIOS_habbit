# Research: Conversation Management UX

## Decision: Make the destructive target explicit

**Decision**: Keep a distinct pending deletion target keyed by conversation ID, and render the target title in the confirmation.

**Rationale**: Current controls implicitly act on the active conversation inside a detached expander. Users cannot reliably verify the intended target, particularly when titles are similar.

**Alternatives considered**: Immediate deletion was rejected because deletion is permanent. A generic confirmation was rejected because selection can change during reruns and drift from the intended target.

## Decision: Recover active state and URL together after deletion

**Decision**: After deleting an active conversation, clear the deleted ID from the URL and state, then select the first remaining conversation in existing list order; if none remains, render an explicit empty state with a create action.

**Rationale**: The current flow clears only session state, leaving the deleted `conv` parameter. Initialization restores that invalid ID on the next rerun, producing the observed empty content pane.

## Decision: Treat stale navigation as recoverable input

**Decision**: Validate that the requested conversation exists and belongs to the active notebook before rendering its content. Replace invalid state with a valid fallback or no-conversation state.

**Rationale**: A stale tab, refresh, or external cleanup can leave invalid navigation even without the delete button.

## Decision: Preserve store semantics

**Decision**: Keep permanent deletion and the existing cascade to messages, temporary sources, and source selections; do not change notebook source ownership or deletion behavior.

**Rationale**: The defect is targeting and navigation recovery, not storage retention policy.
