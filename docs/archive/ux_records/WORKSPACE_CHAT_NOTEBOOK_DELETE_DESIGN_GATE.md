# Workspace Chat Notebook Delete Design Gate

## 1. Baseline

- HEAD: `831e98d4373886d7b6c9711f3050b70a076d3553`
- `origin/main`: `831e98d4373886d7b6c9711f3050b70a076d3553`

## 2. Owner final decision

Owner selected Option C: hard delete notebook.

Reason:

- “Xóa sổ” means permanently deleting all data inside the notebook;
- the goal is to free local machine/storage footprint;
- old notebooks may become unnecessary;
- keeping old notebook data forever is not acceptable.

Archive/hide/restore is not enough for this need.
Soft delete/trash is not selected for this MVP because owner explicitly chose permanent deletion for storage cleanup.

## 3. Problem statement

Current Phase 2I implemented archive/hide/restore only.
Archive is not delete.
There is no owner-facing notebook hard delete UI.
Notebook hard delete must be designed before implementation because it is destructive and cascades across Workspace Chat local data.

## 4. Current implementation evidence

Current repository evidence shows:

- `DocumentNotebook` has optional `archived_at` lifecycle metadata;
- `archive_notebook()` sets archive metadata;
- `restore_notebook()` clears archive metadata;
- the app renders active and archived notebook lists;
- archived notebooks can be restored;
- no hard delete notebook path was found;
- `delete_notebook_source()` deletes a notebook source only, not a notebook;
- Phase 2I intentionally excluded hard delete, cascade delete, and trash purge.

## 5. Definitions

- Archive: hide from main list, data preserved, restore possible.
- Soft delete / trash: hide from normal list, visible in trash, restore possible, optional purge later.
- Hard delete: destructive deletion of notebook and all child data.
- Cascade delete: deletion of conversations, messages, notebook sources, temporary sources, source selections, and metadata.

## 6. Options and final decision

### Option A — Keep archive/hide/restore only

Rejected for the current owner need.
It remains useful for reversible list cleanup, but it does not free old notebook data permanently.

### Option B — Add soft delete / trash layer

Rejected for this MVP.
It is safer than hard delete, but it duplicates archive unless owner needs a distinct recoverable trash concept.
It also does not immediately satisfy the selected “xóa vĩnh viễn” meaning.

### Option C — Add hard delete notebook

Selected.

- Highest risk, but matches owner intent.
- Requires exact confirmation.
- Requires child-data cascade design.
- Requires partial failure/recovery strategy.
- Requires tests for conversations, messages, notebook sources, temporary sources, selections, privacy labels, and active sessions.
- Must not call provider or weaken privacy behavior.

## 7. Risk matrix

| Option | Data-loss risk | Implementation risk | Owner value | Testability | MVP suitability |
| --- | --- | --- | --- | --- | --- |
| A. Archive/hide/restore only | Low | Low | Low for disk cleanup | High | Not enough |
| B. Soft delete / trash | Medium | Medium | Medium | Medium | Deferred |
| C. Hard delete notebook | High | High | High | Medium | Selected with safeguards |

## 8. Selected gate status

`PASS_READY_FOR_HARD_DELETE_IMPLEMENTATION_PROMPT`

Hard delete is now the target, but implementation must not start until the implementation prompt uses the cascade contract, confirmation UX, tests, and safeguards in `WORKSPACE_CHAT_NOTEBOOK_HARD_DELETE_IMPLEMENTATION_DESIGN.md`.
