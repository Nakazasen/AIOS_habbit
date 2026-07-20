# WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL_DESIGN_GATE

## 1. Kết luận

Design date: `2026-07-04` (`Asia/Bangkok`).

Final status: `PASS_READY_FOR_GEMINI_PHASE2I_PRIVACY_SOURCE_CONTROL_IMPLEMENTATION`.

Khuyến nghị **Option C — Creation + compact edit**, giới hạn thành một lựa chọn nhị phân:

- `Có thể gửi AI`
- `Chỉ dùng trên máy / không gửi AI`

Lựa chọn xuất hiện khi tạo nguồn và trong một expander nhỏ `Quyền riêng tư nguồn` ở từng nguồn hiện có. Không hiển thị enum kỹ thuật, không thêm policy matrix, không thêm consent prompt theo từng nguồn, và không thay đổi backend Phase 2E.

Thiết kế dùng trường `privacy_label` và các hàm save hiện có. Không cần sửa model, store, schema hoặc `workspace_chat_ai_answer.py`.

## 2. Baseline

| Check | Evidence |
|---|---|
| Repo | `D:\Sandbox\AIOS_habbit` |
| Branch | `main` |
| HEAD | `475fabfd583f8bf8aa72c8ab328103bc94d6e6fd` |
| `origin/main` | `475fabfd583f8bf8aa72c8ab328103bc94d6e6fd` |
| Latest commit | `475fabf Document Workspace Chat Phase 2H owner smoke gaps` |
| Tracking state | `## main...origin/main` |
| Worktree before design | clean |
| Runtime paths before design | clean |

## 3. Owner problem

Phase 2H privacy block hoạt động ở backend và có automated tests, nhưng owner không thể tạo hoặc đổi một nguồn sang trạng thái bị chặn bằng UI. Vì mọi nguồn do Workspace Chat tạo hiện mặc định `machine_only`, owner chỉ thấy privacy-block state nếu test hoặc runtime data đã được tạo bằng code.

Hậu quả:

- owner không tự smoke-test được `Có nguồn không được gửi AI`;
- cảnh báo privacy có thể xuất hiện nhưng không có thao tác sửa trực tiếp;
- owner phải tắt nguồn thay vì có thể xác định rõ nguồn chỉ được dùng cục bộ;
- sửa JSON runtime bằng tay là không an toàn và không phải owner workflow.

Mục tiêu Phase 2I là cho owner kiểm soát một thuộc tính đã tồn tại, không thiết kế lại privacy engine.

## 4. Current privacy model evidence

### Labels hiện có

`NotebookSource` và `TemporaryConversationSource` đều có `privacy_label`, mặc định `machine_only`.

Backend chuẩn hóa bằng trim/lowercase và hiện phân loại:

| Internal label | AI sendable hiện tại | Owner UI hiện tại |
|---|---:|---|
| `machine_only` | YES | Không hiển thị enum; là default của nguồn mới |
| `cloud_allowed` | YES | Không có control tạo/gán |
| `local_only` | NO | Chỉ có cảnh báo nếu data đã mang label này |
| `confidential` | NO | Chỉ có cảnh báo nếu data đã mang label này |
| blank / whitespace / `None` | NO | Fail closed |
| unknown value | NO | Fail closed |

`is_privacy_label_cloud_allowed()` chỉ trả true cho `machine_only` và `cloud_allowed`. Một nguồn khác whitelist làm toàn bộ request bị chặn trước provider; không có partial send.

### Source creation paths

Nguồn tạm được tạo trong `workspace_chat_app.py` qua:

1. safe test data helper;
2. `Dán nhanh nhiều nguồn`;
3. form dán văn bản dài;
4. upload Excel `.xlsx`.

Nguồn notebook được tạo khi promote nguồn tạm. Store hiện copy `privacy_label` từ nguồn tạm sang nguồn notebook.

Không có source-edit UI. UI chỉ bật/tắt nguồn và promote nguồn tạm. Store đã có:

- `save_temporary_source(source)`;
- `save_notebook_source(source)`.

Vì vậy edit privacy có thể mutate object đã load rồi gọi save hiện có. Không cần API/store mới.

## 5. Options evaluated

| Option | Ưu điểm | Hạn chế | Kết luận |
|---|---|---|---|
| A — Creation only | UI nhẹ | Không sửa được nguồn cũ; không giải quyết dead end | Không chọn |
| B — Source-list edit only | Sửa được mọi nguồn cũ; smoke được | Owner dễ quên privacy lúc tạo | Khả thi nhưng chưa đủ |
| C — Creation + compact edit | Rõ từ đầu và sửa được nguồn cũ; owner smoke đầy đủ | Thêm một control ở form và một expander nhỏ | **Chọn** |
| D — Dev-only blocked source | Smoke nhanh | Không giải quyết owner workflow thật | Chỉ là test helper, không chọn làm solution |

Option C không đồng nghĩa một settings system mới. Nó là cùng một radio hai lựa chọn được dùng lại ở các create forms và một collapsed editor ở source list.

## 6. Proposed owner-facing UX

### Shared choice

Label:

`Nguồn này được dùng thế nào?`

Choices:

1. `Có thể gửi AI`
2. `Chỉ dùng trên máy / không gửi AI`

Help copy:

`Bạn vẫn cần bấm Hỏi AI để gửi. Nguồn chỉ dùng trên máy sẽ không được gửi AI.`

Không dùng các từ `privacy_label`, `machine_only`, `cloud_allowed`, `local_only`, `confidential`, `provider`, `cloud consent` trong owner UI.

### Why a radio, not a toggle

Hai trạng thái cần được đọc như hai lựa chọn có ý nghĩa, không phải một switch kỹ thuật. Radio cũng tránh câu phủ định kép kiểu “tắt cho phép gửi”. Giá trị phải được snapshot khi form submit; thay đổi widget không tự save source và không gọi AI.

### Placement

- Quick paste: đặt dưới content textarea, trước submit.
- Long text paste: đặt dưới content textarea, trước submit.
- Excel upload: đặt dưới file picker, trước submit.
- Safe test data: giữ behavior hiện tại; không mở rộng helper này thành privacy fixture trong production UI.
- Existing source: expander collapsed `Quyền riêng tư nguồn` dưới title/preview và trước checkbox bật nguồn.

Không thêm global privacy settings. Mỗi source mang lựa chọn riêng.

## 7. Exact Vietnamese copy

| Purpose | Exact copy |
|---|---|
| Field label | `Nguồn này được dùng thế nào?` |
| Sendable choice | `Có thể gửi AI` |
| Blocked choice | `Chỉ dùng trên máy / không gửi AI` |
| Help | `Bạn vẫn cần bấm Hỏi AI để gửi. Nguồn chỉ dùng trên máy sẽ không được gửi AI.` |
| Existing-source editor | `Quyền riêng tư nguồn` |
| Sendable status | `Có thể gửi AI khi bạn bấm Hỏi AI` |
| Blocked status | `Nguồn này sẽ không được gửi AI` |
| Save button | `Lưu lựa chọn` |
| Saved feedback | `Đã cập nhật quyền riêng tư nguồn.` |
| AI hard block | `Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi lựa chọn quyền riêng tư.` |

Không nói `AI đã dùng` hoặc `AI đã nhận` trước provider success.

## 8. Owner choice to internal mapping

| Owner choice | Internal value to persist |
|---|---|
| `Có thể gửi AI` | `machine_only` |
| `Chỉ dùng trên máy / không gửi AI` | `local_only` |

Rationale:

- `machine_only` là default hiện hành và đã được backend whitelist.
- Dùng lại `machine_only` giữ behavior và regression expectations hiện tại; Phase 2I không cần migrate nguồn cũ sang `cloud_allowed`.
- `local_only` đã là giá trị bị chặn có automated coverage và có nghĩa phù hợp nhất với lựa chọn owner-facing.
- `cloud_allowed`, `confidential` và invalid labels vẫn được đọc an toàn theo backend hiện tại, nhưng UI Phase 2I không tạo các giá trị này.

UI phải xác định trạng thái sendable bằng cùng whitelist hiện tại:

- `machine_only`/`cloud_allowed` hiển thị trạng thái sendable;
- mọi giá trị khác hiển thị trạng thái local-only/blocked.

Không tự rewrite legacy/unknown label khi render. Chỉ persist `machine_only` hoặc `local_only` sau khi owner bấm `Lưu lựa chọn`.

## 9. Default recommendation

Default cho nguồn mới: `Có thể gửi AI`.

Lý do:

- giữ nguyên behavior Phase 2H của tất cả create paths;
- không âm thầm biến nguồn mới thành blocked sau upgrade;
- tránh làm primary `Hỏi AI` flow luôn dead-end cho owner chưa biết privacy control;
- “có thể” không phải automatic consent: typing, paste, upload và source check vẫn không gọi provider; owner vẫn phải bấm `Hỏi AI`;
- exact-source action và backend privacy validation vẫn chạy.

Đây là compatibility default, không phải tuyên bố rằng dữ liệu tự động được gửi. Help copy phải xuất hiện ngay cạnh control.

Nếu owner muốn đổi system-wide default thành local-only, đó là một product-policy decision riêng và cần owner approval; không gộp vào implementation này.

## 10. Source creation behavior

Khi submit thành công:

1. app đọc radio của chính form;
2. map sang `machine_only` hoặc `local_only`;
3. gán `privacy_label` khi khởi tạo source;
4. save bằng existing store function;
5. auto-enable source như behavior hiện tại;
6. không gọi AI.

Áp dụng cho quick paste, long-text paste và successful Excel extraction.

Excel privacy choice không được kích hoạt extraction lần hai. AI submit tiếp tục dùng `content_text` đã lưu và không gọi extractor.

Promote giữ nguyên privacy label qua existing `promote_temporary_source_to_notebook()`. Không thêm lựa chọn lần hai trong promote.

Safe test helper giữ default hiện tại và không trở thành đường tắt tạo blocked source; owner có thể dùng editor để đổi nguồn test sau khi tạo.

## 11. Existing-source edit behavior

Mỗi notebook source và temporary source có expander collapsed `Quyền riêng tư nguồn`.

Trong expander:

- hiển thị radio hai lựa chọn, initialized từ label hiện tại;
- hiển thị status copy;
- chỉ persist khi bấm `Lưu lựa chọn`;
- callback/app handler chỉ nhận source ID + owner choice, resolve source trong đúng notebook/conversation, mutate `privacy_label`, gọi đúng existing save function, set feedback rồi rerun.

Boundary requirements:

- temporary source chỉ được resolve trong active conversation;
- notebook source chỉ được resolve trong active notebook;
- ID không tìm thấy: owner-safe error, không tạo record mới;
- đổi privacy không tự bật/tắt source;
- đổi privacy không gọi provider;
- đổi privacy không thay content, extraction status, promotion status hoặc selection record;
- nguồn promoted sau đó vẫn kế thừa label hiện tại.

Widget key phải gồm scope, conversation/notebook context và source ID để tránh collision.

## 12. Source-list display

Collapsed state vẫn phải cho owner biết trạng thái:

- sendable: `Có thể gửi AI khi bạn bấm Hỏi AI`;
- blocked/invalid: `Nguồn này sẽ không được gửi AI`.

Blocked status nên dùng `st.warning` hoặc caption/warning nhỏ, không dùng success. Không hiển thị enum.

Checkbox `Bật nguồn này cho cuộc trò chuyện` vẫn hoạt động độc lập. Owner được phép bật blocked source để:

- dùng source checker local;
- quan sát AI hard-block;
- smoke-test privacy behavior.

Không disable checkbox và không tự tắt blocked source, vì việc đó sẽ che mất all-or-nothing gate.

## 13. AI action with an enabled blocked source

Khi một hoặc nhiều enabled sources bị blocked:

1. request giữ toàn bộ exact enabled-source snapshot;
2. backend kiểm tra privacy trên toàn bộ source set;
3. toàn bộ AI request bị chặn trước provider;
4. không loại riêng source bị chặn;
5. không gửi phần còn lại;
6. không tạo user/assistant message;
7. không hiển thị `AI đã trả lời`;
8. UI hiển thị:

`Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi lựa chọn quyền riêng tư.`

Không thêm per-request override như “vẫn gửi”. Muốn tiếp tục, owner phải tắt source hoặc explicit edit privacy rồi bấm `Hỏi AI` lại. Click mới tạo exact-source action mới.

Source check vẫn đọc local content và hiển thị `AI chưa trả lời`; nó không gọi provider bất kể privacy choice.

## 14. Owner smoke-test path

Không cần sửa runtime JSON:

1. mở Workspace Chat, notebook và conversation;
2. dùng `Dán nhanh nhiều nguồn`;
3. chọn `Chỉ dùng trên máy / không gửi AI`;
4. nhập synthetic text và thêm source;
5. xác nhận source tự bật và hiển thị `Nguồn này sẽ không được gửi AI`;
6. bấm `Kiểm tra nguồn trước`;
7. xác nhận source check hiển thị nội dung và `AI chưa trả lời`;
8. nhập câu hỏi, bấm `Hỏi AI với nguồn đang bật`;
9. xác nhận UI hiển thị exact hard-block copy;
10. xác nhận không có assistant answer, `AI đã trả lời`, hoặc provider call;
11. mở `Quyền riêng tư nguồn`, chọn `Có thể gửi AI`, bấm `Lưu lựa chọn`;
12. xác nhận status đổi; không yêu cầu chạy provider success smoke nếu provider chưa cấu hình.

Mixed-source smoke:

1. bật một sendable source và một local-only source;
2. bấm Hỏi AI;
3. xác nhận toàn bộ request bị chặn, không partial send.

## 15. Phase 2E compatibility

| Phase 2E invariant | Design result |
|---|---|
| Typing does not call provider | Preserved |
| Paste/upload does not call provider | Preserved |
| Source check does not call provider | Preserved |
| Explicit AI action only | Preserved |
| Exact enabled-source snapshot | Preserved |
| Source change requires fresh action | Preserved |
| One blocked source blocks all | Preserved and now owner-smokeable |
| No partial send | Preserved |
| Blank/unknown/invalid fail closed | Preserved |
| Provider errors sanitized | Unchanged |
| No `.xlsx` reparse on AI submit | Unchanged |
| No automatic/hidden send | Preserved |

No change to `workspace_chat_ai_answer.py` is needed. Existing backend tests remain the authority for fail-closed behavior.

## 16. Minimal Gemini implementation scope

Production:

1. Add small UI constants/helpers for owner choices and status rendering.
2. Extend the two source-list render functions with one privacy-save callback and compact editor.
3. Add app callbacks that resolve sources in active scope, update the existing field and call existing save functions.
4. Add the shared choice to quick paste, long-text paste and Excel forms.
5. Set `privacy_label` explicitly on successfully created sources.
6. Update privacy-block copy to the exact approved text.

No generic privacy service, settings object, migration, schema, new store API or backend-policy change.

## 17. Exact allowed files for Gemini

Production:

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`

Tests:

- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`

Docs:

- `docs/ux/WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL_DESIGN_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL_IMPLEMENTATION_AUDIT.md`

`tests/test_workspace_chat_ai_answer.py` must be run but does not need modification because backend semantics are unchanged and already covered.

## 18. Forbidden files and capabilities

Forbidden without a new owner decision:

- `src/aios_habit/workspace_chat_models.py`
- `src/aios_habit/workspace_chat_store.py`
- `src/aios_habit/workspace_chat_ai_answer.py`
- provider/router/network modules;
- dependency and schema files;
- Excel extractor files;
- Case Cockpit files/tests.

Strongly forbidden:

- `.ai`;
- `local_cases`;
- `task.md`;
- `walkthrough.md`;
- `implementation_plan.md`;
- manual runtime JSON edits;
- real provider/cloud setup;
- notebook delete/archive;
- partial send or per-source send override;
- RAG/vector/embedding/retrieval/citation;
- OCR or new file formats;
- stage, commit or push.

## 19. Tests to add or update

### UI copy tests

- exact two owner choices and help copy exist;
- internal enums do not appear in rendered owner copy;
- exact blocked/status/save feedback copy;
- privacy editor is collapsed and has stable unique keys.

### Source-list UI tests

- notebook sendable source renders sendable status and correct initial choice;
- notebook blocked/unknown source renders blocked status and local-only initial choice;
- temporary source covers the same states;
- save callback receives source ID and normalized owner choice;
- toggling enabled state remains independent;
- editor render does not call save callback.

### Owner-flow tests

- quick paste maps both choices and still creates exactly one auto-enabled source;
- long text paste maps both choices;
- Excel success maps both choices and extractor remains called only on upload submit;
- creation does not call provider;
- notebook-source edit persists through existing `save_notebook_source`;
- temporary-source edit persists through existing `save_temporary_source`;
- edit is scoped to active notebook/conversation;
- missing/cross-scope ID fails safely;
- edit does not change enabled selection;
- promote preserves privacy label;
- source check with local-only source does not call provider;
- enabled local-only source yields privacy-block badge/copy and no saved messages;
- mixed enabled set remains all-or-nothing.

### Regression tests to run unchanged

- all `tests/test_workspace_chat_ai_answer.py`, including local/confidential/blank/unknown/`None` cases;
- answer preview tests;
- full suite and CLI audit.

## 20. Risks and anti-overengineering guardrails

| Risk | Guardrail |
|---|---|
| UI becomes dense | Editor collapsed; one status line and two choices only |
| Owner assumes automatic send | Use `Có thể` and explicit help that Hỏi AI is still required |
| Legacy invalid value gets accidentally allowed | Treat all non-whitelisted values as blocked; no render-time rewrite |
| Privacy edit weakens exact consent | Edit does not submit AI; next explicit click builds fresh snapshot |
| Mixed sources partially sent | Keep backend unchanged; one blocked source blocks all |
| Duplicate policy logic drifts | UI classification mirrors the two-value whitelist only for display; backend remains authority |
| Source ID edits cross scope | Resolve only from active notebook/conversation |
| Excel gets reparsed | Privacy edit mutates metadata only; AI path uses saved text |
| Scope grows into settings/provider work | No global settings, provider setup or policy matrix |

## 21. Gemini implementation prompt

```text
TASK: IMPLEMENT_WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL

Implement only the approved design in:
docs/ux/WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL_DESIGN_GATE.md

Baseline gate:
- branch main;
- HEAD == origin/main at the owner-approved design commit;
- worktree/runtime paths clean except the explicit implementation allowlist;
- stop on unexpected dirty files; do not reset, clean or stash.

Implement Option C in its minimal form:
- exact owner choices:
  - Có thể gửi AI
  - Chỉ dùng trên máy / không gửi AI
- map internally:
  - Có thể gửi AI -> machine_only
  - Chỉ dùng trên máy / không gửi AI -> local_only
- default new sources to Có thể gửi AI;
- add the choice to quick paste, long-text paste and Excel create forms;
- add a collapsed Quyền riêng tư nguồn editor to notebook and temporary source lists;
- persist edits with existing save functions only;
- show owner-safe status without enum names;
- update hard-block copy exactly as designed;
- preserve source enablement independently.

Safety:
- do not modify models, store, workspace_chat_ai_answer, provider/router/network,
  dependencies, extractor, Case Cockpit, .ai or local_cases;
- do not add partial send, override prompts, provider setup, notebook lifecycle,
  schema changes, RAG/citation/OCR/new formats;
- typing, paste, upload, privacy edit and source check must not call provider;
- one blocked source blocks the whole request;
- no XLSX reparse during AI submit.

Allowed files:
- src/aios_habit/workspace_chat_app.py
- src/aios_habit/workspace_chat_ui.py
- tests/test_workspace_chat_ui_copy.py
- tests/test_workspace_chat_source_selection_ui_copy.py
- tests/test_workspace_chat_source_selection_owner_flow.py
- docs/ux/WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL_DESIGN_GATE.md
- docs/ux/WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL_IMPLEMENTATION_AUDIT.md

Run:
py -3 -m pytest tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_answer_preview.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md

Create an implementation audit with evidence, test counts, scope check and runtime
dirty check.

Do not stage.
Do not commit.
Do not push.
```

