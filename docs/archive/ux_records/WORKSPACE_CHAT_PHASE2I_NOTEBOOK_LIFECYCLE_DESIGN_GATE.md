# WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_DESIGN_GATE

## 1. Kết luận

Design date: `2026-07-04` (`Asia/Bangkok`).

Final status: `PASS_READY_FOR_GEMINI_PHASE2I_NOTEBOOK_LIFECYCLE_IMPLEMENTATION`.

Khuyến nghị **Option A — Archive/hide/restore notebook MVP**:

- owner có thể `Lưu trữ sổ`;
- sổ đã lưu trữ biến mất khỏi danh sách chính;
- sổ vẫn xuất hiện trong khu vực thu gọn `Sổ đã lưu trữ`;
- owner có thể `Khôi phục sổ`;
- không xóa notebook hoặc bất kỳ dữ liệu phụ thuộc nào;
- chưa thêm đổi tên và tuyệt đối chưa thêm hard delete.

Đây là giải pháp nhỏ nhất giải quyết danh sách nhiễu nhưng vẫn có đường phục hồi rõ ràng. Hard delete bị từ chối trong Phase 2I vì data graph bao gồm conversations, messages, notebook sources, temporary sources và source selections; hiện chưa có transaction, trash hoặc recovery mechanism.

## 2. Baseline

| Check | Evidence |
|---|---|
| Repo | `D:\Sandbox\AIOS_habbit` |
| Branch | `main` |
| HEAD | `2ba4b4242e893c2d883aff665c49819ecb68b6eb` |
| `origin/main` | `2ba4b4242e893c2d883aff665c49819ecb68b6eb` |
| Latest commit | `2ba4b42 Implement Workspace Chat Phase 2I privacy source control` |
| Tracking state | `## main...origin/main` |
| Worktree before design | clean |
| Runtime paths before design | clean |

## 3. Owner problem

Owner có thể tạo nhiều sổ nhưng không thể dọn các sổ test hoặc sổ không còn dùng. Danh sách chính sẽ ngày càng dài và khó tìm.

Một nút xóa đơn giản không an toàn: notebook là root của nhiều dữ liệu làm việc. Xóa nhầm có thể làm mất cuộc trò chuyện, tin nhắn, nguồn và selection state mà owner không nhìn thấy hết ở màn hình danh sách.

MVP cần:

- làm gọn danh sách;
- không mất dữ liệu;
- có thể đảo ngược;
- không buộc owner hiểu quan hệ dữ liệu kỹ thuật;
- không ảnh hưởng privacy, AI answer hoặc provider behavior.

## 4. Current notebook data model evidence

### Existing entities and ownership

| Entity | Direct owner/reference | Storage |
|---|---|---|
| `DocumentNotebook` | root; `id` | `notebooks.jsonl` |
| `WorkspaceConversation` | `notebook_id` | `conversations.jsonl` |
| `NotebookSource` | `notebook_id` | `notebook_sources.jsonl` |
| `ChatMessage` | `conversation_id` | `messages.jsonl` |
| `TemporaryConversationSource` | `conversation_id` | `temporary_sources.jsonl` |
| `ConversationSourceSelection` | `conversation_id`, then source scope/id | `conversation_source_selections.jsonl` |

Relationship:

```text
DocumentNotebook
├── WorkspaceConversation
│   ├── ChatMessage
│   ├── TemporaryConversationSource
│   └── ConversationSourceSelection
└── NotebookSource
```

Selection records can reference notebook sources or temporary sources, but are owned operationally by a conversation.

### Existing model/store capability

`DocumentNotebook` currently has:

- `id`;
- `title`;
- `description`;
- `created_at`;
- `updated_at`.

Store supports:

- `load_notebooks()`;
- `load_notebook(id)`;
- `save_notebook(notebook)`.

Store does **not** support:

- archive state;
- archived/active filtering;
- archive/restore helpers;
- notebook delete;
- cascade delete;
- trash/recovery.

There is `delete_notebook_source()`, but that deletes a source, not a notebook, and is not evidence that notebook deletion is safe.

### Active UI state

Streamlit session state holds:

- `wsc_active_notebook_id`;
- `wsc_active_conversation_id`;
- related presentation/action state.

The notebook list is rendered only when `wsc_active_notebook_id is None`. Opening a notebook sets the active ID; returning to the list clears notebook and conversation IDs.

## 5. Options evaluated

| Option | Owner value | Data risk | Scope | Decision |
|---|---|---:|---:|---|
| A — Archive/hide/restore | Solves list cleanup and test-notebook noise | Low; reversible | Small | **Choose** |
| B — Rename + archive | Also improves organization | Low | Larger UI/test surface | Defer rename |
| C — Hard delete | Permanently removes data | High | Large; needs cascade/recovery policy | Reject for MVP |
| D — Hide test notebooks only | Narrow cleanup | Low | Special-case behavior | Reject |
| Rename only | Improves labels but not list length | Low | Small | Does not solve gap |
| No action | No implementation risk | None | None | Owner gap remains |

## 6. Proposed owner-facing UX

### Main notebook list

Each active notebook card keeps its existing open action and adds a secondary action:

`Lưu trữ sổ`

Clicking it does not archive immediately. The card shows an inline confirmation:

`Sổ này sẽ được ẩn khỏi danh sách chính. Dữ liệu bên trong không bị xóa.`

Actions:

- `Xác nhận lưu trữ`
- `Hủy`

No title typing is required because this action is reversible and does not delete data.

### Archived section

Below the active list:

`Sổ đã lưu trữ`

Render as collapsed by default. If empty:

`Chưa có sổ đã lưu trữ.`

Each archived card shows title, description, conversation count, archived status, and:

`Khôi phục sổ`

Archived cards do not show `Mở sổ`. Owner restores first, then opens from the main list. This avoids editing or creating new child data inside a hidden notebook and keeps archived meaning simple.

### Feedback

- archive success: `Đã lưu trữ sổ.`
- restore success: `Đã khôi phục sổ.`
- archive failure: `Không thể lưu trữ sổ. Vui lòng thử lại.`
- restore failure: `Không thể khôi phục sổ. Vui lòng thử lại.`
- stale/missing notebook: `Không tìm thấy sổ này. Danh sách đã được cập nhật.`

## 7. Exact Vietnamese copy

| Purpose | Exact copy |
|---|---|
| Archive action | `Lưu trữ sổ` |
| Confirmation | `Sổ này sẽ được ẩn khỏi danh sách chính. Dữ liệu bên trong không bị xóa.` |
| Confirm action | `Xác nhận lưu trữ` |
| Cancel action | `Hủy` |
| Archived section | `Sổ đã lưu trữ` |
| Empty archived section | `Chưa có sổ đã lưu trữ.` |
| Restore action | `Khôi phục sổ` |
| Archive success | `Đã lưu trữ sổ.` |
| Restore success | `Đã khôi phục sổ.` |
| Archive failure | `Không thể lưu trữ sổ. Vui lòng thử lại.` |
| Restore failure | `Không thể khôi phục sổ. Vui lòng thử lại.` |
| Missing notebook | `Không tìm thấy sổ này. Danh sách đã được cập nhật.` |
| Phase boundary | `Không xóa dữ liệu trong Phase 2I.` |

Owner UI không dùng `hard delete`, `soft delete`, `cascade`, `schema`, `JSONL`, `record`, `foreign key` hoặc enum nội bộ.

## 8. Data behavior

Archiving changes only notebook lifecycle metadata:

- notebook remains persisted with the same ID/title/description/timestamps;
- conversations remain unchanged;
- notebook sources remain unchanged;
- messages remain unchanged;
- temporary sources remain unchanged;
- source selections remain unchanged;
- privacy labels remain unchanged;
- enabled states remain unchanged;
- saved case references remain unchanged;
- no provider or extractor is called.

Restore clears archive metadata and returns the notebook to the active list with all child data intact.

No lifecycle action writes child data files.

## 9. Active notebook/session policy

Recommendation: archive is available only on the notebook list, where `wsc_active_notebook_id` is already `None`.

Consequences:

- owner cannot archive the notebook currently open;
- owner must use `Quay lại danh sách sổ` first;
- no forced navigation while editing/chatting;
- no risk that the current page references a newly hidden notebook.

Defense in depth:

- archive callback must clear `wsc_active_notebook_id` and `wsc_active_conversation_id` if a stale event/session somehow targets the active notebook;
- archive/restore must rerun and clear pending confirmation state;
- if an archived notebook ID is injected into active session state, app must clear active notebook/conversation and return to the list rather than open it.

No owner-facing “active notebook” error copy is needed in normal flow because the action is not rendered while a notebook is open.

## 10. Default/protected notebook policy

Recommendation:

- no notebook ID is permanently protected;
- default seeded notebooks may be archived and restored like owner-created notebooks;
- notebooks with conversations or sources may be archived because no child data is deleted;
- empty and non-empty notebooks use the same behavior;
- the last active notebook may be archived.

If all notebooks are archived, the main list shows the existing create form plus the collapsed archived section. Owner can create a notebook or restore one. This is clearer than a hidden “cannot archive last notebook” rule.

Archive is not delete, so special protection based on content count is unnecessary.

## 11. Store/model impact

### Minimal model change

Add to `DocumentNotebook`:

```python
archived_at: Optional[str] = None
```

Why `archived_at` instead of a separate boolean:

- `None` means active;
- a timestamp means archived;
- one field avoids contradictory `is_archived=False` plus non-empty timestamp;
- supports stable archived ordering and future audit copy without new migration.

This is a local persistence shape extension, not a destructive migration.

### Minimal store helpers

Add:

- `load_active_notebooks()`;
- `load_archived_notebooks()`;
- `archive_notebook(notebook_id) -> bool`;
- `restore_notebook(notebook_id) -> bool`.

Both mutation helpers:

1. resolve notebook from `load_notebooks()`;
2. return false if missing;
3. set/clear `archived_at`;
4. update `updated_at`;
5. persist through existing `save_notebook()`;
6. do not read/write child stores.

Idempotency:

- archiving an already archived notebook returns true without changing `archived_at`;
- restoring an active notebook returns true without changing other fields.

### Why model/store edits are necessary

Archive must survive reruns and application restarts. Session state alone would only hide a notebook temporarily. A persisted lifecycle flag is therefore necessary.

No new file, database, dependency or schema version system is needed.

## 12. Migration and backward compatibility

- Existing notebook JSON lacks `archived_at`; dataclass default makes it active.
- Newly saved notebooks include `archived_at: null` or a timestamp.
- Missing `archived_at` always means active.
- `null`, empty string and whitespace are treated as active.
- A valid non-empty string means archived.
- Unexpected non-string metadata must fail safe as archived in list filtering, so malformed lifecycle state does not silently expose a notebook as active.
- Loading one malformed notebook must not delete or rewrite it automatically.
- No bulk rewrite/migration on startup.
- No runtime JSON edits in implementation or tests.

Tests must isolate store paths through existing fixtures.

## 13. Tests to add/update

### Model/store tests

- old notebook payload without `archived_at` loads active;
- new notebook defaults active;
- archive persists a timestamp;
- archive is idempotent;
- restore clears metadata;
- restore is idempotent;
- missing notebook returns false and creates nothing;
- active/archived filtering is correct;
- malformed lifecycle metadata fails safe without rewrite;
- archive/restore do not alter title, description, created timestamp or ID.

### Ownership/data-safety tests

Create a notebook with:

- conversation;
- messages;
- notebook source;
- temporary source;
- enabled notebook and temporary selections.

Snapshot every child collection, archive, restore, and assert every child object is byte/value-equivalent. Confirm privacy labels and enabled states are unchanged.

### UI/owner-flow tests

- active list excludes archived notebooks;
- archived expander is collapsed;
- archived cards cannot open;
- confirmation is required before archive;
- cancel changes nothing;
- exact Vietnamese copy;
- archive success/failure feedback;
- restore returns notebook to main list;
- no action rendered inside active notebook view;
- stale archived active ID returns safely to list;
- lifecycle actions do not call provider, AI answer, extractor, or save child records;
- all-archived empty-main state still exposes create and restore paths;
- internal technical terms do not appear in owner copy.

### Regression

- Phase 2I privacy mapping/edit/block tests unchanged;
- source selection and answer preview tests;
- `tests/test_workspace_chat_ai_answer.py`;
- full suite;
- CLI audit;
- runtime dirt check.

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Accidental data loss | Archive only; no child deletion |
| Orphaned conversations | Notebook remains; references unchanged |
| Active session mismatch | Action list-only; stale archived IDs fail back to list |
| Owner cannot find hidden notebook | Persistent collapsed `Sổ đã lưu trữ` section |
| Accidental archive click | Explicit inline confirmation |
| Restore changes child state | Store helper mutates notebook metadata only |
| Default notebook disappears | Reversible; archived section always available |
| Malformed metadata exposes hidden data | Unknown non-string state fails safe as archived |
| Scope grows into deletion | Hard delete explicitly forbidden |

## 15. Anti-overengineering guardrails

- archive first; delete later only under a separate owner-approved design;
- no cascade delete;
- no trash retention scheduler;
- no bulk archive;
- no multi-select;
- no archive reason, tags, folders or global workspace manager;
- no rename in this MVP;
- no provider, AI answer, privacy or source-selection policy changes;
- no Case Cockpit changes;
- no new dependency or storage engine;
- no migration command;
- no background jobs.

## 16. Exact implementation allowlist for Gemini

Production:

- `src/aios_habit/workspace_chat_models.py`
- `src/aios_habit/workspace_chat_store.py`
- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`

Tests:

- `tests/test_workspace_chat_store.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py`

Docs:

- `docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_DESIGN_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_IMPLEMENTATION_AUDIT.md`

No other file is allowed without stopping and requesting owner approval.

## 17. Forbidden files and capabilities

- `.ai`;
- `local_cases`;
- `task.md`;
- `walkthrough.md`;
- `implementation_plan.md`;
- `src/aios_habit/workspace_chat_ai_answer.py`;
- `src/aios_habit/workspace_chat_answer_preview.py`;
- `tests/test_workspace_chat_ai_answer.py` modifications;
- provider/router/network modules;
- Excel extractor files;
- Case Cockpit files/tests;
- `requirements.txt`;
- `pyproject.toml`;
- runtime JSON edits;
- hard delete/cascade delete;
- notebook trash purge;
- provider setup;
- privacy-label or exact-source behavior changes;
- RAG/vector/embedding/retrieval/citation;
- OCR/new formats;
- stage, commit or push.

## 18. Gemini implementation prompt

```text
TASK: IMPLEMENT_WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE

Implement only the approved archive/hide/restore MVP in:
docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_DESIGN_GATE.md

Do not implement until the owner has approved this design gate.

Baseline gate:
- branch main;
- HEAD == origin/main at the approved design commit;
- worktree and runtime paths clean except the explicit allowlist;
- stop on unexpected dirty files; do not reset, clean or stash.

Implement:
- persisted DocumentNotebook.archived_at with backward-compatible active default;
- active/archived notebook load filters;
- idempotent archive/restore helpers that mutate notebook metadata only;
- main list shows active notebooks only;
- each active notebook card has Lưu trữ sổ with explicit inline confirmation;
- collapsed Sổ đã lưu trữ section with Khôi phục sổ;
- archived notebooks cannot open until restored;
- archive action is list-only;
- stale archived active session safely returns to list;
- exact Vietnamese copy from the design gate;
- no child data mutation.

Safety:
- no hard delete or cascade;
- no rename in this MVP;
- no runtime JSON edits;
- do not change privacy, AI answer, provider/router/network, extractor,
  dependencies or Case Cockpit;
- do not call provider/extractor from lifecycle actions.

Allowed files only:
- src/aios_habit/workspace_chat_models.py
- src/aios_habit/workspace_chat_store.py
- src/aios_habit/workspace_chat_app.py
- src/aios_habit/workspace_chat_ui.py
- tests/test_workspace_chat_store.py
- tests/test_workspace_chat_source_selection_owner_flow.py
- tests/test_workspace_chat_ui_copy.py
- tests/test_workspace_chat_source_selection_ui_copy.py
- docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_DESIGN_GATE.md
- docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_IMPLEMENTATION_AUDIT.md

Test:
- backward compatibility and malformed metadata fail-safe;
- archive/restore persistence and idempotency;
- full child-data preservation;
- active/archived list behavior, confirmation, cancel and restore;
- stale active-session handling;
- no provider/extractor/child-store calls;
- all Phase 2I privacy regressions;
- full suite and CLI audit.

Run:
py -3 -m pytest tests/test_workspace_chat_store.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_answer_preview.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md

Create:
docs/ux/WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE_IMPLEMENTATION_AUDIT.md

Do not stage.
Do not commit.
Do not push.
```

