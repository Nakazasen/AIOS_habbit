# Conversation Management UI Contract

## Conversation list

- Each conversation entry provides a visible selected state when it is active.
- Each entry exposes management for that exact conversation; management labels and confirmations include its current title.

## Delete confirmation

- Shows the title of the pending deletion target.
- Provides `Cancel` and `Delete` actions.
- `Cancel` makes no persistent change.
- `Delete` removes the target only after confirmation.

## Post-delete navigation

- When a remaining conversation exists, it is rendered immediately and becomes the active URL target.
- When none exists, the content pane presents a Vietnamese empty state and a create-conversation action.
- A stale URL never leaves a blank content pane.

## Error behavior

- Missing target or persistence failure leaves unaffected data intact and renders a Vietnamese error message.
- No provider, retrieval, or source ingestion action is triggered by conversation management.
