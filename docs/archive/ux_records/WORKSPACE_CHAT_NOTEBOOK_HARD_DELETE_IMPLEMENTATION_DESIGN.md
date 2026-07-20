# Workspace Chat Notebook Hard Delete Implementation Design

## 1. Baseline

- HEAD: `831e98d4373886d7b6c9711f3050b70a076d3553`
- `origin/main`: `831e98d4373886d7b6c9711f3050b70a076d3553`

## 2. Owner decision

Owner selected hard delete.

Reason:

- hard delete is needed to free disk/local data;
- old notebooks cannot be kept forever;
- archive/hide/restore is not sufficient for this storage cleanup need;
- trash/soft delete is not the selected MVP.

## 3. Current state

Current Workspace Chat has:

- archive/hide/restore via `archived_at`, `archive_notebook()`, and `restore_notebook()`;
- active and archived notebook list UI;
- no notebook hard delete store path;
- no owner-facing notebook delete UI;
- `delete_notebook_source()`, which deletes one notebook source only and is not notebook deletion.

## 4. Selected design

Implement hard delete notebook with cascade.

- No trash layer in this MVP.
- Archive remains available as reversible cleanup.
- Hard delete is destructive cleanup for owner-confirmed old notebooks.
- Delete is local-only and must not call provider/cloud.

## 5. Data cascade contract

Hard delete notebook permanently removes:

- the `DocumentNotebook` record;
- all `WorkspaceConversation` records whose `notebook_id` matches the notebook;
- all `ChatMessage` records whose `conversation_id` belongs to those conversations;
- all `NotebookSource` records whose `notebook_id` matches the notebook;
- all `TemporaryConversationSource` records whose `conversation_id` belongs to those conversations;
- all `ConversationSourceSelection` records whose `conversation_id` belongs to those conversations;
- notebook lifecycle metadata such as `archived_at`, by deleting the notebook record itself.

Hard delete must not remove:

- other notebooks;
- conversations from other notebooks;
- messages from other notebooks;
- notebook sources from other notebooks;
- temporary sources from other notebooks' conversations;
- source selections from other notebooks' conversations;
- provider/config data;
- Case Cockpit data;
- `.ai`;
- `local_cases` as a directory;
- unrelated runtime files.

## 6. Store design

Recommended helper:

```python
def delete_notebook_permanently(notebook_id: str) -> bool:
    ...
```

A richer result object is optional only if implementation needs owner-facing counts or error categories. Avoid changing `workspace_chat_models.py` unless a result type is truly necessary.

Store algorithm:

1. Load the target notebook with `load_notebook(notebook_id)`.
2. If missing, return `False` without touching any file.
3. Collect child conversation IDs using `load_conversations(notebook_id)`.
4. Rewrite affected JSONL stores by filtering:
   - `notebooks.jsonl`: remove the notebook ID;
   - `conversations.jsonl`: remove conversations with that notebook ID;
   - `messages.jsonl`: remove messages whose `conversation_id` is in collected IDs;
   - `notebook_sources.jsonl`: remove sources with that notebook ID;
   - `temporary_sources.jsonl`: remove temporary sources whose `conversation_id` is in collected IDs;
   - `conversation_source_selections.jsonl`: remove selections whose `conversation_id` is in collected IDs.
5. Preserve all unrelated records byte-for-byte as much as current JSONL helpers allow.
6. Return `True` only after all rewrites succeed.

Partial failure strategy:

- Determine all IDs to delete before writing.
- Prefer writing through helper functions that use temporary file replacement for each affected file.
- If delete fails before any write, data remains unchanged.
- If delete fails during write, surface safe failure and never show fake success.
- Tests must cover missing notebook and unrelated data preservation.

Implementation must not manually edit runtime JSON outside store helpers.

## 7. UI design

Placement:

- Put `Xóa vĩnh viễn sổ` in a visually separated danger zone on each notebook card.
- Keep it separate from `Lưu trữ sổ`.
- Do not place it in the main owner happy path.
- Archived notebook cards may also expose delete, but only with the same confirmation flow.

Confirmation flow:

1. Owner clicks `Xóa vĩnh viễn sổ`.
2. UI displays destructive warning.
3. Owner must type the exact notebook title.
4. Owner must check acknowledgement if implemented.
5. Final delete action remains disabled or blocked until exact title matches.

Exact Vietnamese copy:

- `Xóa vĩnh viễn sổ`
- `Hành động này sẽ xóa vĩnh viễn sổ và toàn bộ dữ liệu bên trong. Không thể khôi phục.`
- `Nhập chính xác tên sổ để xác nhận xóa`
- `Tôi hiểu dữ liệu sẽ bị xóa vĩnh viễn`
- `Xác nhận xóa vĩnh viễn`
- `Đã xóa vĩnh viễn sổ.`
- `Không thể xóa sổ vì tên xác nhận chưa đúng.`
- `Không thể xóa sổ. Vui lòng thử lại.`

Active session clearing:

- If the deleted notebook is active, clear `wsc_active_notebook_id`.
- Clear `wsc_active_conversation_id`.
- Clear pending archive/delete confirmation state.
- Return to notebook list.
- Do not show stale deleted notebook.
- Do not leave selected sources pointing to deleted records.

## 8. Test plan

Model/store tests:

- deleting existing notebook removes notebook, child conversations, messages, notebook sources, temporary sources, and source selections;
- deleting one notebook preserves unrelated notebooks and all unrelated children;
- missing notebook returns `False` and preserves all files;
- archived notebook can be hard-deleted with the same cascade;
- privacy labels and enabled/disabled states in other notebooks remain unchanged.

UI copy tests:

- hard delete warning copy exists;
- exact-title confirmation copy exists;
- success/failure copy exists;
- archive copy still exists and remains distinct;
- owner-facing copy does not use internal terms like JSONL, cascade, schema, or source scopes.

Owner-flow tests:

- wrong title blocks delete;
- exact title enables or executes delete;
- delete success clears active notebook/conversation state;
- deleted notebook no longer appears in active or archived lists;
- archived notebook delete uses same confirmation;
- no provider call path is introduced.

Privacy regression tests:

- local-only source still blocks AI in an unrelated notebook;
- delete does not call provider;
- delete does not create an AI answer;
- delete does not alter privacy mapping for remaining records.

Required validation:

- focused lifecycle/source/owner tests;
- AI answer tests;
- full suite.

## 9. Allowed implementation files

Suggested production allowlist:

- `src/aios_habit/workspace_chat_store.py`
- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`

Only include `src/aios_habit/workspace_chat_models.py` if a new result model is proven necessary. Prefer no schema change.

Suggested tests:

- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py`
- `tests/test_workspace_chat_store.py`

`tests/test_workspace_chat_store.py` already uses isolated temp stores and is appropriate for store-level cascade tests. If implementation keeps all store lifecycle tests in the existing owner-flow test file, explain why in the implementation audit.

Allowed docs:

- `docs/ux/WORKSPACE_CHAT_NOTEBOOK_HARD_DELETE_IMPLEMENTATION_AUDIT.md`

## 10. Forbidden scope

- No provider setup.
- No AI answer backend changes.
- No privacy weakening.
- No Case Cockpit changes.
- No RAG/vector/OCR/new file formats.
- No dependency changes.
- No runtime JSON manual edits.
- No manual edits to `.ai`, `local_cases`, `task.md`, `walkthrough.md`, or `implementation_plan.md`.
- No force push.
- No trash/soft delete layer in this MVP.

## 11. Validation commands

```text
py -3 -m pytest tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_store.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md
```

## 12. Owner smoke plan

Use synthetic, non-secret local data only:

1. Create a safe notebook.
2. Add a conversation.
3. Add one sendable source.
4. Add one local-only source.
5. Run source check and confirm no provider call.
6. Archive and restore once as lifecycle sanity.
7. Open delete danger zone.
8. Try delete with wrong title and confirm it is blocked.
9. Type exact title and confirm hard delete.
10. Confirm notebook disappears from active and archived lists.
11. Confirm deleted notebook cannot be opened.
12. Confirm other notebooks remain unaffected.
13. Confirm local-only privacy behavior remains unaffected in another notebook.
14. Confirm no provider/cloud call occurred.
15. Confirm no fake success appears on failure paths.

## 13. Final status

`PASS_READY_FOR_HARD_DELETE_IMPLEMENTATION_PROMPT`
