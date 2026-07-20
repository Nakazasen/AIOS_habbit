# WORKSPACE_CHAT_PHASE2_RESEARCH_FIRST_DESIGN_AUDIT

## Final status

`PASS_WITH_WARNINGS_NEEDS_OWNER_REVIEW`

Phase 2 should be research-first and should start with a small, local-first source model for Workspace Chat. Do not start by wiring live AI, rewriting Case Cockpit, or adding a heavy document platform.

## Baseline

- Repo: `D:\Sandbox\AIOS_habbit`
- Branch expected: `main`
- Expected sync point: `HEAD == origin/main == 1166afc`
- Current Phase 1 files reviewed:
  - `src/aios_habit/workspace_chat_models.py`
  - `src/aios_habit/workspace_chat_store.py`
  - `src/aios_habit/workspace_chat_ui.py`
  - `src/aios_habit/workspace_chat_app.py`
  - `tests/test_workspace_chat_architecture_boundary.py`
  - `tests/test_workspace_chat_models.py`
  - `tests/test_workspace_chat_store.py`
  - `tests/test_workspace_chat_owner_flow.py`
  - `tests/test_workspace_chat_ui_copy.py`

Phase 1 already provides independent Workspace Chat app/store/models/UI helpers, isolated storage under `local_cases/workspace_chat/`, default notebooks, multiple conversations per notebook, and temporary conversation sources with full pasted text.

Important Phase 1 limitations for Phase 2:

- Notebook metadata exists, but there is no long-term notebook source model.
- `WorkspaceConversation.selected_source_ids` exists, but no source selection store/UI exists yet.
- Temporary sources cannot yet be promoted into notebook sources.
- The right panel displays source names only; there is no answer-source usage record.
- Excel is not ingested directly yet.

## External research summary

| Product/repo | Useful pattern | AIOS decision |
|---|---|---|
| NotebookLM | Notebook + source mental model; source selection; answer verification from source context. | Keep owner model as `Sổ tài liệu`; show selected/used sources clearly. |
| Open WebUI | Workspace knowledge can be selected for chat. | Use a simple owner-facing source chooser, not technical settings. |
| AnythingLLM | Clear split between workspace documents and thread-attached documents. | Best fit: `Nguồn trong sổ` vs `Nguồn tạm trong cuộc trò chuyện`. |
| Dify | Separates knowledge, app, and runtime source choice. | Keep source selection separate from conversation and answer rendering. |
| RAGFlow | Document parsing quality and answer traceability matter. | Track extraction status and source-use metadata; do not import a full platform. |
| Docling | Supports XLSX and structured document conversion. | Candidate for later; do not add heavy dependency in first MVP. |
| Unstructured | Can split Excel into table-like elements. | Candidate for messy spreadsheets later. |
| LlamaIndex/LangChain loaders | Excel loaders exist but often add framework concepts. | Avoid framework lock-in; use AIOS-owned adapter boundary. |
| openpyxl | Local `.xlsx` workbook/sheet/value reader. | Best first MVP for `.xlsx` extraction. |

Research conclusion: AIOS should copy the product pattern, not the implementation bulk. The safest Phase 2 architecture is a small source lifecycle and selection layer over the existing Workspace Chat shell.

## Recommended Phase 2 scope

### Phase 2A — Source models and store

Add:

- `NotebookSource`: long-term source owned by a notebook.
- `ConversationSourceSelection`: per-conversation enabled/disabled source selection.
- Optional later `AnswerSourceUse`: source usage record for assistant messages.

Store files should remain under Workspace Chat storage:

- `notebook_sources.jsonl`
- `conversation_source_selections.jsonl`
- `answer_source_uses.jsonl` if needed

Do not use `case_store.py` for this layer.

### Phase 2B — Owner source selection UI

Add non-technical Vietnamese UI for:

- `Nguồn trong sổ`
- `Nguồn tạm trong cuộc trò chuyện`
- `Chọn nguồn cho cuộc trò chuyện này`
- `Thêm vào sổ tài liệu`
- `Tạm không dùng`
- `Nguồn AIOS đã dùng`

Default recommendation:

- Newly pasted temporary source: enabled in current conversation.
- Notebook sources: owner should explicitly choose for a new conversation unless owner approves auto-enable.

### Phase 2C — Excel direct ingest MVP

Implement `.xlsx` first through a thin local adapter, likely `src/aios_habit/workspace_chat_excel.py`.

MVP should extract:

- filename;
- sheet names;
- row/column bounds;
- capped preview;
- readable text under a safe size limit;
- extraction status.

MVP should not attempt:

- chart interpretation;
- comments/shapes/text boxes;
- formula recalculation;
- full semantic table interpretation;
- legacy `.xls` unless separately approved.

Recommended `.xls` copy:

```text
File .xls cũ chưa được hỗ trợ trong bản đầu. Vui lòng lưu lại thành .xlsx rồi thêm lại.
```

### Phase 2D — Honest source-use answer placeholder

Before live AI integration, keep response copy honest:

- show selected sources;
- show sources used by the placeholder response;
- show items owner must verify;
- do not claim deep analysis has happened if it has not.

Suggested placeholder wording:

```text
Bản thử nghiệm: AIOS mới ghi nhận nguồn và câu hỏi. Phần phân tích thật sẽ được nối ở bước sau.
```

## Source lifecycle

| Internal status | Owner label | Meaning |
|---|---|---|
| `notebook_source` | `Trong sổ tài liệu` | Long-term notebook source. |
| `conversation_only` | `Chỉ dùng trong cuộc trò chuyện này` | Temporary source scoped to one conversation. |
| `added_to_notebook` | `Đã thêm vào sổ tài liệu` | Temporary source promoted by owner. |
| `saved_to_case` | `Đã lưu vào hồ sơ` | Source attached to a case/handover. |
| `disabled_for_conversation` | `Tạm không dùng` | Source exists but is disabled for this conversation. |

Promotion must be explicit. Temporary sources should not automatically pollute long-term notebook sources.

## Proposed internal fields

### `NotebookSource`

- `id`
- `notebook_id`
- `title`
- `source_type`
- `filename`
- `file_type`
- `created_at`
- `updated_at`
- `privacy_label`
- `content_preview`
- `content_text`
- `extraction_status`
- `source_note`
- `origin_temporary_source_id`

### `ConversationSourceSelection`

- `id`
- `conversation_id`
- `source_id`
- `source_scope`
- `enabled`
- `enabled_at`
- `disabled_at`
- `used_in_last_answer`
- `last_used_at`
- `owner_note`

## UI wireframe copy

```text
📚 Nguồn trong sổ MOM / Opcenter
Nguồn này được giữ lại để dùng nhiều lần trong sổ.
[ + Thêm nguồn vào sổ ]

☑ MOM meeting note 2026-06-20
Loại: Tài liệu văn bản
Trạng thái: Đã đọc xong
[ Xem ] [ Tạm không dùng trong cuộc trò chuyện này ]
```

```text
📌 Nguồn tạm trong cuộc trò chuyện
Nguồn tạm chỉ dùng trong cuộc trò chuyện hiện tại.
Nếu thấy hữu ích lâu dài, hãy thêm vào sổ tài liệu.

☑ Log lỗi 14:32 hôm nay
Trạng thái: Chỉ dùng trong cuộc trò chuyện này
[ Xem nội dung ] [ Thêm vào sổ tài liệu ] [ Tạm không dùng ]
```

```text
✅ Chọn nguồn cho cuộc trò chuyện này

Nguồn trong sổ
[☑] MOM meeting note 2026-06-20
[☐] Checklist Opcenter restart

Nguồn tạm trong cuộc trò chuyện
[☑] Log lỗi 14:32 hôm nay

[ Lưu lựa chọn ] [ Hủy ]
```

## Tests and gates

### Phase 2A tests

Add/extend:

- `tests/test_workspace_chat_sources_models.py`
- `tests/test_workspace_chat_sources_store.py`
- `tests/test_workspace_chat_owner_flow.py`
- `tests/test_workspace_chat_architecture_boundary.py`

PASS:

- Can create/list/update notebook sources.
- Can create per-conversation source selections.
- Temporary source remains conversation-scoped.
- No `case_cockpit.py` import.
- Store remains under `local_cases/workspace_chat/`.

### Phase 2B tests

Add:

- `tests/test_workspace_chat_source_selection_ui_copy.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`

PASS:

- Vietnamese non-technical copy.
- Owner can select/deselect notebook and temporary sources.
- Owner can promote temporary source to notebook.
- No forbidden UI terms in Workspace Chat app/UI files.

### Phase 2C tests

Add:

- `tests/test_workspace_chat_excel_ingest.py`

PASS:

- Generated `.xlsx` test workbook extracts sheet names and preview.
- Empty and large sheets handled safely.
- `.xls` behavior is explicit and friendly.

### Phase 2D tests

Add:

- `tests/test_workspace_chat_answer_sources.py`

PASS:

- Placeholder answer source-use records match rendered UI.
- No fake deep-analysis claim.

## Risks

| Risk | Mitigation |
|---|---|
| Source model grows too fast | Keep Phase 2A minimal. |
| Owner UI becomes technical | Keep copy tests and forbidden term scan. |
| Temporary sources pollute notebook | Require explicit promotion. |
| Excel overpromises | Start with preview/status, not interpretation. |
| Legacy coupling returns | Keep architecture boundary tests. |
| Large files slow UI | Cap preview and full stored text. |

## Open questions for owner

1. Should notebook sources be enabled by default in a new conversation, or should owner explicitly choose them?
2. Should temporary sources remain until the conversation is deleted, or should AIOS offer cleanup later?
3. Is `.xlsx`-only acceptable for first Excel MVP, with a friendly `.xls` conversion message?
4. What is the initial safe maximum for full pasted/extracted text stored in JSONL?
5. Should this design report be committed before implementation starts?
6. Should every Phase 2D placeholder answer explicitly say `Bản thử nghiệm` until live AI is connected?

## Owner decisions before Phase 2A

Owner reviewed the Phase 2 design and approved these defaults:

1. Notebook sources are not auto-enabled for a new conversation; owner explicitly chooses them.
2. Newly added temporary sources are enabled automatically in the current conversation.
3. Temporary sources remain with their conversation until owner deletes or promotes them.
4. Excel MVP supports `.xlsx` first; `.xls` shows a friendly conversion message.
5. Initial full text cap: `200 KB/source`.
6. Initial preview cap: `2,000 characters/source`.
7. Placeholder answers must explicitly say `Bản thử nghiệm` until live AI is connected.
8. Phase 2A may start after this report is committed.

## Final recommendation

Proceed to Phase 2A only after owner review. Recommended defaults if owner accepts:

- Notebook sources are not auto-enabled for new conversations.
- Newly added temporary sources are enabled in their current conversation.
- Temporary sources remain with their conversation until owner promotes/deletes them.
- `.xlsx` first; `.xls` deferred with friendly message.
- Preview always stored; full text only below a safe cap.
- Commit this report before implementation.

Implementation must use exact-path staging, must not touch `.ai` or `local_cases/`, and must not modify or import `case_cockpit.py`.
