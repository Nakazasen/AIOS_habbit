# Workspace Chat Notebook Delete Design Gate

## 1. Baseline

- HEAD: `08a1b3b27b86746dcfb01fc2eda9af8aaa567806`
- `origin/main`: `08a1b3b27b86746dcfb01fc2eda9af8aaa567806`

## 2. Problem statement

Owner asked why the UI has no notebook delete.
Current Phase 2I implemented archive/hide/restore only.
Archive is not delete.
There is no notebook hard delete UI.

## 3. Current implementation evidence

Current repository evidence shows:

- `DocumentNotebook` has optional `archived_at` lifecycle metadata;
- `archive_notebook()` sets archive metadata;
- `restore_notebook()` clears archive metadata;
- the app renders active and archived notebook lists;
- archived notebooks can be restored;
- no hard delete notebook path was found;
- `delete_notebook_source()` deletes a notebook source only, not a notebook.

## 4. Definitions

- Archive: hide from main list, data preserved, restore possible.
- Soft delete / trash: hide from normal list, visible in trash, restore possible, optional purge later.
- Hard delete: destructive deletion of notebook and all child data.
- Cascade delete: deletion of conversations, messages, notebook sources, temporary sources, source selections, and metadata.

## 5. Options

### Option A — Keep archive/hide/restore only

- Best if owner only needs list cleanup.
- No destructive data loss.
- Already implemented.
- Could improve copy so owner understands archive means cleanup.

### Option B — Add soft delete / trash layer

- Safer than hard delete.
- More complex than archive.
- Needs trash UI, restore, retention policy, and no accidental provider/privacy changes.
- Might duplicate archive unless use case is clearly different.

### Option C — Add hard delete notebook

- Highest risk.
- Requires explicit confirm.
- Requires child-data cascade design.
- Requires partial failure/recovery strategy.
- Requires tests for conversations, messages, notebook sources, temporary sources, selections, privacy labels, active sessions.
- Should not be implemented without owner approval.

## 6. Risk matrix

| Option | Data-loss risk | Implementation risk | Owner value | Testability | MVP suitability |
| --- | --- | --- | --- | --- | --- |
| A. Archive/hide/restore only | Low | Low | Medium if cleanup is enough | High | High |
| B. Soft delete / trash | Medium | Medium | Medium to high if owner needs delete semantics | Medium | Medium |
| C. Hard delete notebook | High | High | High only if permanent deletion is required | Medium to low | Low without explicit approval |

## 7. Recommended decision

Do not implement delete immediately.
Ask owner to choose:

- A: archive is enough;
- B: soft delete/trash needed;
- C: hard delete needed with full safeguards.

Recommended status: `PASS_READY_FOR_OWNER_DELETE_DECISION`

## 8. Required owner decision

Ask exactly:

“Bạn muốn ‘xóa sổ’ nghĩa là ẩn khỏi danh sách chính, đưa vào thùng rác có thể khôi phục, hay xóa vĩnh viễn toàn bộ dữ liệu bên trong?”

## 9. If owner chooses hard delete later

Future requirements:

- allowed files to be decided later;
- no provider changes;
- no privacy weakening;
- no runtime JSON manual edits;
- tests for cascade safety;
- owner smoke for delete confirmation and restore/impossibility depending option.

## 10. Final status

`PASS_READY_FOR_OWNER_DELETE_DECISION`
