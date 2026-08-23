# Feature Specification: Conversation Management UX

**Feature Branch**: `004-conversation-management-ux`

**Created**: 2026-08-22

**Status**: Draft

**Input**: User description: "Deleting a conversation is difficult to use, does not clearly identify the target conversation, and leaves a blank screen until another conversation is selected."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete the intended conversation safely (Priority: P1)

As a Workspace Chat user, I can start deletion from a clearly identified conversation and confirm exactly which conversation will be removed.

**Why this priority**: A mistaken or ambiguous deletion risks losing user work and is the immediate usability failure reported.

**Independent Test**: Create several conversations, choose delete for one named conversation, confirm, and verify only that conversation and its conversation-only data are removed.

**Acceptance Scenarios**:

1. **Given** several conversations in a notebook, **When** I choose the delete action for one conversation, **Then** the confirmation identifies that conversation by title before I can complete deletion.
2. **Given** a deletion confirmation, **When** I cancel, **Then** no conversation or related data changes.
3. **Given** a deletion confirmation, **When** I confirm, **Then** only the named conversation and its conversation-scoped data are removed.

---

### User Story 2 - Continue without a blank screen after deletion (Priority: P1)

As a Workspace Chat user, after deleting the conversation I am viewing, I immediately land in a usable next state instead of an empty black content area.

**Why this priority**: The current failure makes a normal destructive action appear to break the application.

**Independent Test**: Delete the active conversation while other conversations exist, then repeat when it is the last conversation; verify the page always presents a usable destination.

**Acceptance Scenarios**:

1. **Given** the active conversation is deleted and another conversation remains, **When** deletion completes, **Then** the application opens an available remaining conversation and its URL/state match it.
2. **Given** the active conversation is the last one, **When** deletion completes, **Then** the application presents a clear empty state with an immediate action to create a new conversation.
3. **Given** the conversation displayed in the URL no longer exists, **When** the page is refreshed, **Then** the application recovers to a valid conversation or the clear empty state.

---

### User Story 3 - Manage the selected conversation with confidence (Priority: P2)

As a Workspace Chat user, I can see which conversation is selected and manage that exact conversation without relying on ambiguous sidebar state.

**Why this priority**: Rename and deletion controls are currently separated from the conversation list and make it easy to lose track of their target.

**Independent Test**: Switch among similarly named conversations, open management controls, rename one, and confirm the changed title and selection remain unambiguous.

**Acceptance Scenarios**:

1. **Given** several conversations, **When** I select one, **Then** its selected state is visually distinct and the management area names that conversation.
2. **Given** the management area is open, **When** I rename the selected conversation, **Then** its list entry and management heading update together.
3. **Given** conversations have similar titles, **When** I open a destructive action, **Then** the confirmation still makes the target distinguishable.

### Edge Cases

- The selected conversation has already been deleted in another tab or external cleanup before the page reruns.
- Deletion persistence fails; the existing conversation remains selected and a clear error is shown.
- A stale URL references a conversation from another notebook or a conversation that no longer exists.
- The notebook has no conversations before first use or after deleting its final conversation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The conversation list MUST provide a clear selected state and a management entry point associated with a specific conversation.
- **FR-002**: Rename and delete controls MUST visibly name the conversation they affect.
- **FR-003**: Deletion confirmation MUST require an explicit confirm action and MUST offer a cancel action that preserves all data.
- **FR-004**: On successful deletion, the system MUST remove only the selected conversation and its conversation-scoped messages, temporary sources, and source selections.
- **FR-005**: After successful deletion of the active conversation, the system MUST select a remaining conversation when one exists; otherwise it MUST show a usable no-conversation state with a create action.
- **FR-006**: The application MUST clear or replace an invalid conversation reference in both in-memory navigation state and the browser URL.
- **FR-007**: If deletion fails or the selected conversation cannot be found, the system MUST preserve valid existing state and show a clear Vietnamese error message.
- **FR-008**: Existing notebook-level sources and data belonging to other conversations MUST remain unchanged by conversation management actions.

### Key Entities

- **Workspace conversation**: A titled discussion belonging to one notebook, with conversation-scoped messages, temporary sources, and source selections.
- **Active conversation reference**: The currently displayed conversation as represented by application navigation state and shareable page location.
- **Deletion target**: The explicitly identified conversation pending confirmation; it must not drift when the selected conversation changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In all tested deletion cases, users reach a usable conversation or no-conversation state immediately after one confirmation action, with no blank content screen.
- **SC-002**: In all tested rename and deletion cases involving multiple similarly named conversations, the UI identifies the target before the change is committed.
- **SC-003**: In automated deletion tests, no messages, temporary sources, selections, or notebook-level sources belonging to other conversations are changed.
- **SC-004**: A stale or deleted conversation link recovers to a usable state on the first page refresh.

## Assumptions

- Conversation deletion remains permanent, but requires a lightweight in-context confirmation rather than a typed title challenge.
- When deleting the active conversation, the application chooses the first remaining conversation in the existing list order; it does not create a replacement automatically.
- Conversation management remains within the Workspace Chat sidebar and does not change notebook archival or deletion behavior.
