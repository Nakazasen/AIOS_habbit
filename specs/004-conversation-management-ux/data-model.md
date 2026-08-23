# Data Model: Conversation Management UX

## Existing entities

### WorkspaceConversation

- Identified by `id` and scoped to one `notebook_id`.
- Owns conversation-scoped messages, temporary sources, and source selections.
- Existing persisted fields remain compatible; no migration is needed.

### Active conversation reference

- Has an in-session value and a URL value.
- Is valid only when the referenced conversation exists and belongs to the active notebook.
- On invalid input, transitions to a remaining conversation ID or `None` when the notebook is empty.

### Pending deletion target

- Ephemeral UI state containing one conversation ID.
- Is set only by an explicit delete action and cleared after confirm, cancel, target disappearance, or successful deletion.
- Is never persisted as part of a conversation.

## State transitions

| Event | Previous state | Result |
|---|---|---|
| Select conversation | Any valid notebook state | Active state and URL reference the selected conversation |
| Request deletion | Target exists | Pending target references that conversation |
| Cancel deletion | Pending target | Pending target cleared; data and active state unchanged |
| Delete inactive target | Target exists | Target data removed; active state remains valid |
| Delete active target with remaining conversations | Active target | First remaining conversation becomes active in state and URL |
| Delete final active target | Active target | Active state and URL are cleared; empty state is shown |
| Refresh stale URL | Missing/wrong-notebook target | State and URL resolve to a valid fallback or empty state |
