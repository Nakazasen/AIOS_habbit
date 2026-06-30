# WORKSPACE_CHAT_PHASE2B_UI_DESIGN_GATE

## 1. Kết luận ngắn

**Final status: `PASS_READY_FOR_GEMINI_PHASE2B_IMPLEMENTATION`.**

Phase 2A đã có đủ model và store API để Gemini triển khai UI chọn nguồn ở Phase 2B mà không cần sửa backend, nối AI thật, làm Excel ingest hoặc chạm Case Cockpit.

Phase 2B chỉ quản lý nguồn và lựa chọn nguồn của owner:

- hiển thị `Nguồn trong sổ`;
- hiển thị `Nguồn tạm trong cuộc trò chuyện`;
- bật/tắt từng nguồn cho cuộc trò chuyện hiện tại;
- thêm một nguồn tạm vào sổ tài liệu;
- hiển thị tóm tắt `Nguồn đang dùng`.

Trong report này, `Nguồn đang dùng` chỉ có nghĩa là nguồn owner đang bật cho cuộc trò chuyện. Nó không có nghĩa là AIOS đã đọc, phân tích, trích dẫn hoặc dùng nguồn đó để tạo câu trả lời.

Không cần owner quyết định thêm trước khi Gemini code. Các quyết định đã chốt đủ rõ.

## 2. Baseline

Baseline kiểm tra trước khi tạo report:

| Mục | Kết quả |
|---|---|
| Repo | `D:\Sandbox\AIOS_habbit` |
| Branch | `main` |
| HEAD | `a0b318a` |
| origin/main | `a0b318a` |
| Worktree trước design gate | sạch |
| Commit mới nhất | `a0b318a Implement Workspace Chat Phase 2A source backend` |

Năm commit gần nhất:

```text
a0b318a Implement Workspace Chat Phase 2A source backend
4470fc7 Document Workspace Chat Phase 2 design
1166afc Document AI metadata cleanup audit
31dc2d5 Hygiene visual map redaction scan
89d9016 Add Workspace Chat Phase 1 UI shell
```

Baseline đạt gate; không có lý do trả về `FAIL_DIRTY_TREE` hoặc `FAIL_PHASE2A_NOT_STABLE`.

## 3. Phase 2A API summary

### Model sẵn có

`src/aios_habit/workspace_chat_models.py` đã có:

- `NotebookSource`: nguồn dài hạn thuộc một notebook;
- `ConversationSourceSelection`: trạng thái bật/tắt một nguồn trong một conversation;
- `TemporaryConversationSource`: nguồn tạm hiện có từ Phase 1;
- `SOURCE_SCOPE_NOTEBOOK = "notebook"`;
- `SOURCE_SCOPE_TEMPORARY = "temporary"`.

UI không nên tự tạo hoặc sửa trực tiếp `ConversationSourceSelection`. Mọi thao tác bật/tắt phải đi qua store.

### Store API UI nên dùng

`src/aios_habit/workspace_chat_store.py` đã có:

| Nhu cầu UI | API |
|---|---|
| Danh sách nguồn trong sổ | `load_notebook_sources(notebook_id)` |
| Danh sách nguồn tạm | `load_temporary_sources(conversation_id)` |
| Trạng thái lựa chọn hiện tại | `load_conversation_source_selections(conversation_id)` |
| Chỉ lấy nguồn đang bật | `load_enabled_sources_for_conversation(conversation_id)` |
| Bật/tắt một nguồn | `set_source_enabled(conversation_id, source_scope, source_id, enabled)` |
| Thêm nguồn tạm vào sổ | `promote_temporary_source_to_notebook(conversation_id, temporary_source_id, notebook_id)` |

Promotion hiện có các semantics đúng với quyết định owner:

- nguồn tạm không bị xóa;
- nguồn tạm được đánh dấu đã thêm vào sổ;
- một `NotebookSource` mới được tạo;
- nguồn trong sổ mới không tự bật;
- lựa chọn nguồn tạm hiện tại không bị thay đổi.

`save_temporary_source()` hiện không tự tạo selection. Khi owner thêm một nguồn tạm mới qua UI, app phải gọi tiếp:

```python
set_source_enabled(
    conversation_id,
    SOURCE_SCOPE_TEMPORARY,
    temporary_source.id,
    True,
)
```

Đây là bước cần thiết để thực thi quyết định “nguồn tạm tự bật trong cuộc trò chuyện hiện tại”.

### Giới hạn backend cần giữ nguyên

- Xóa `NotebookSource` không cascade selection; dangling selection là non-goal Phase 2A.
- JSONL malformed line được bỏ qua theo pattern hiện tại.
- Không thêm API mới nếu các API trên đã đủ.
- Không đọc/ghi trực tiếp `notebook_sources.jsonl` hoặc `conversation_source_selections.jsonl` từ UI.

## 4. Phase 2B UI scope

### File được sửa khi implementation

- `src/aios_habit/workspace_chat_ui.py`
- `src/aios_habit/workspace_chat_app.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py` (mới)
- `tests/test_workspace_chat_source_selection_owner_flow.py` (mới)
- Có thể mở rộng:
  - `tests/test_workspace_chat_owner_flow.py`
  - `tests/test_workspace_chat_architecture_boundary.py`
  - `tests/test_workspace_chat_ui_copy.py`

Không cần sửa `workspace_chat_models.py` hoặc `workspace_chat_store.py` cho scope đã chốt.

### Component/helper đề xuất trong `workspace_chat_ui.py`

Tên helper có thể điều chỉnh nhẹ, nhưng trách nhiệm nên tách rõ:

```python
render_source_summary(...)
render_notebook_source_list(...)
render_temporary_source_list(...)
render_source_status(...)
```

Mỗi list nhận dữ liệu và callback từ app; helper UI không tự gọi store. Cách tách này giúp test rendering/copy độc lập với JSONL.

`render_source_summary(...)` hiển thị:

- tổng số nguồn đang bật;
- số nguồn trong sổ đang bật;
- số nguồn tạm đang bật;
- empty state khi chưa bật nguồn nào.

`render_notebook_source_list(...)` hiển thị:

- tiêu đề;
- preview ngắn nếu có;
- trạng thái bật/tắt trong conversation hiện tại;
- control `Dùng trong cuộc trò chuyện này`.

`render_temporary_source_list(...)` hiển thị:

- tiêu đề và preview;
- trạng thái bật/tắt;
- control `Dùng trong cuộc trò chuyện này`;
- nút `Thêm vào sổ tài liệu`;
- trạng thái `Đã thêm vào sổ tài liệu` nếu đã promote.

`render_source_status(...)` ánh xạ trạng thái nội bộ sang copy owner-facing. Không hiển thị enum hoặc `source_scope`.

### Vị trí hiển thị

Giữ luồng điều hướng và chat hiện tại. Trong sidebar của conversation:

1. `Nguồn đang dùng` (summary);
2. `Nguồn trong sổ`;
3. `Nguồn tạm trong cuộc trò chuyện`.

Khung dán văn bản dài hiện tại vẫn ở vùng chat. Sau khi lưu thành công, nguồn tạm phải được bật ngay bằng `set_source_enabled(...)`.

### Callback app đề xuất

```python
def set_source_enabled_callback(conversation_id, source_scope, source_id, enabled):
    set_source_enabled(conversation_id, source_scope, source_id, enabled)
    safe_rerun()

def promote_temporary_source_callback(conversation_id, temporary_source_id, notebook_id):
    promote_temporary_source_to_notebook(
        conversation_id,
        temporary_source_id,
        notebook_id,
    )
    safe_rerun()
```

Promotion không được gọi `set_source_enabled(..., SOURCE_SCOPE_NOTEBOOK, ..., True)`.

### Hành vi chính xác

| Tình huống | Hành vi |
|---|---|
| Conversation mới | Không nguồn trong sổ nào tự bật |
| Dán nguồn tạm mới | Lưu nguồn tạm, rồi tự bật nguồn tạm đó |
| Bật/tắt nguồn trong sổ | Persist bằng `set_source_enabled(..., SOURCE_SCOPE_NOTEBOOK, ...)` |
| Bật/tắt nguồn tạm | Persist bằng `set_source_enabled(..., SOURCE_SCOPE_TEMPORARY, ...)` |
| Promote nguồn tạm | Giữ nguồn tạm; tạo nguồn trong sổ; không tự bật nguồn trong sổ mới |
| Reload/rerun | UI dựng lại từ store, không dựa vào checkbox state cũ |
| Selection dangling | Không render như một nguồn nếu source record không còn; không tự sửa store |

## 5. Owner UI copy

### Copy bắt buộc

```text
Nguồn đang dùng
Nguồn trong sổ
Nguồn tạm trong cuộc trò chuyện
Dùng trong cuộc trò chuyện này
Tạm không dùng
Thêm vào sổ tài liệu
Đã thêm vào sổ tài liệu
Chưa có nguồn nào đang dùng.
Chưa có nguồn trong sổ.
Chưa có nguồn tạm trong cuộc trò chuyện này.
```

Copy giải thích ngắn:

```text
Nguồn đang dùng là những nguồn bạn đã bật cho cuộc trò chuyện này.
Nguồn trong sổ được giữ lại để dùng trong nhiều cuộc trò chuyện.
Nguồn tạm chỉ thuộc cuộc trò chuyện hiện tại.
```

Thông báo sau thao tác:

```text
Đã cập nhật nguồn cho cuộc trò chuyện này.
Đã thêm nguồn vào sổ tài liệu. Nguồn mới chưa được tự động bật.
Không thể thêm nguồn vào sổ tài liệu. Vui lòng thử lại.
```

### Copy không được dùng trong owner UI

- `RAG`
- `vector`
- `embedding`
- `chunk`
- `retrieval`
- `citation`
- `claim`
- `provider router`
- `Mermaid`
- `prompt pack`

Không hiển thị các internal value như `notebook`, `temporary`, `conversation_only`, `added_to_notebook` hoặc ID kỹ thuật.

### Ranh giới “không fake AI”

Phase 2B không thêm `Nguồn AIOS đã dùng`, không đưa nguồn đã chọn vào `Nguồn chứng minh`, và không tuyên bố AIOS đã đọc, phân tích, đối chiếu hoặc trả lời dựa trên các nguồn đó.

Copy `Nguồn đang dùng` phải luôn được giải thích là “đang bật cho cuộc trò chuyện”. Answer grounding thật và placeholder `Bản thử nghiệm` thuộc Phase 2D, không thực hiện trong Phase 2B.

## 6. State/rerun risks

### Session key

Tiếp tục prefix hiện có:

```text
wsc_
```

Widget key đề xuất:

```text
wsc_source_notebook_{conversation_id}_{source_id}
wsc_source_temporary_{conversation_id}_{source_id}
wsc_promote_temporary_{conversation_id}_{source_id}
```

Phải có cả `conversation_id`, `source_scope` và `source_id` trong logical key để tránh widget state rò sang conversation khác hoặc đụng ID giữa hai scope.

### Store là source of truth

Mỗi rerun phải:

1. load notebook sources;
2. load temporary sources;
3. load selections của conversation;
4. dựng map `(source_scope, source_id) -> enabled`;
5. render widget từ map đó.

Không duy trì một bản selection riêng lâu dài trong `st.session_state`.

### Khi nào gọi `safe_rerun()`

Gọi đúng một lần sau khi:

- `set_source_enabled(...)` thành công;
- promotion thành công;
- lưu nguồn tạm và auto-enable thành công.

Không rerun trước khi cả save nguồn tạm và selection đã persist. Không vừa dùng callback `on_change` có rerun vừa xử lý lại cùng thao tác ở thân app.

Với checkbox/toggle, ưu tiên callback nhận giá trị boolean rõ ràng hoặc xử lý giá trị trả về một lần. Tránh pattern “đọc state cũ rồi đảo lại”, vì rerun có thể làm click đầu tiên trông như không đổi.

### Promotion idempotency ở tầng UI

Backend helper có thể tạo thêm notebook source nếu bị gọi lại. UI phải:

- không hiện nút promote khi `long_term_saved` đã là `True`;
- hiện `Đã thêm vào sổ tài liệu`;
- dùng key ổn định;
- không thực thi promotion chỉ vì widget render lại.

Nếu helper ném `ValueError` vì nguồn tạm không còn tồn tại, hiển thị lỗi thân thiện và không tạo state giả.

## 7. Test plan

### File mới

`tests/test_workspace_chat_source_selection_ui_copy.py`:

1. Có đầy đủ copy tiếng Việt bắt buộc.
2. Không có các từ cấm trong app/UI owner-facing.
3. Empty summary đúng khi có 0 nguồn.
4. Summary đúng khi chỉ có nguồn trong sổ, chỉ có nguồn tạm, hoặc có cả hai.
5. Status nội bộ được đổi sang copy owner-facing.
6. Không có copy tuyên bố AIOS đã dùng/phân tích nguồn.

`tests/test_workspace_chat_source_selection_owner_flow.py`:

1. Bật nguồn trong sổ gọi `set_source_enabled()` đúng `conversation_id`, scope, source ID và `True`.
2. Tắt nguồn trong sổ gọi đúng API với `False`.
3. Bật/tắt nguồn tạm gọi đúng API với `SOURCE_SCOPE_TEMPORARY`.
4. Thêm nguồn tạm mới gọi `save_temporary_source()`, sau đó auto-enable nguồn đó.
5. Promote gọi `promote_temporary_source_to_notebook()` đúng tham số.
6. Promote không xóa nguồn tạm.
7. Notebook source mới sau promote không auto-enable.
8. Sau rerun, selection được đọc lại từ store.
9. Nút promote không còn hoạt động sau khi nguồn đã được thêm vào sổ.
10. Mọi store path được monkeypatch sang `tmp_path`.

### Test mở rộng

- `test_workspace_chat_owner_flow.py`: thêm flow đổi conversation và xác nhận selection không rò state.
- `test_workspace_chat_architecture_boundary.py`: tiếp tục assert app/UI không import `case_cockpit.py`.
- `test_workspace_chat_ui_copy.py`: giữ scan từ cấm; nếu scan toàn source gây false positive từ tên hằng/internal import thì chuyển sang scan owner-facing label/render strings, không nới danh sách từ cấm.

### Cách test khuyến nghị

Helper render nên nhận callback để tests có thể spy/mock callback. App-level flow nên monkeypatch:

- store file paths sang `tmp_path`;
- `st.session_state`;
- `safe_rerun()` hoặc `st.rerun()`;
- store functions khi chỉ cần kiểm tra wiring.

Tests không được ghi vào `local_cases` thật.

## 8. Gemini implementation prompt

```text
Bạn đang implement WORKSPACE_CHAT_PHASE2B_UI_DESIGN_GATE trong repo:
D:\Sandbox\AIOS_habbit

Baseline bắt buộc trước khi sửa:
- branch: main
- HEAD: a0b318a
- origin/main: a0b318a
- worktree sạch (có thể bỏ qua warning quy ước .codex/ nếu không tracked)

Chạy:
git branch --show-current
git rev-parse --short HEAD
git rev-parse --short origin/main
git status --short
git log --oneline -5

Nếu worktree không sạch, STOP và báo:
FAIL_DIRTY_TREE_BEFORE_PHASE2B_IMPLEMENTATION

Đọc đầy đủ:
- docs/ux/WORKSPACE_CHAT_PHASE2B_UI_DESIGN_GATE.md
- docs/ux/WORKSPACE_CHAT_PHASE2_RESEARCH_FIRST_DESIGN_AUDIT.md
- docs/ux/WORKSPACE_CHAT_PHASE2A_IMPLEMENTATION_AUDIT.md
- src/aios_habit/workspace_chat_models.py
- src/aios_habit/workspace_chat_store.py
- src/aios_habit/workspace_chat_ui.py
- src/aios_habit/workspace_chat_app.py
- tests/test_workspace_chat_sources_models.py
- tests/test_workspace_chat_sources_store.py
- tests/test_workspace_chat_owner_flow.py
- tests/test_workspace_chat_architecture_boundary.py
- tests/test_workspace_chat_ui_copy.py

Mục tiêu Phase 2B:
1. Hiển thị Nguồn trong sổ.
2. Hiển thị Nguồn tạm trong cuộc trò chuyện.
3. Owner bật/tắt từng nguồn cho conversation hiện tại.
4. Owner thêm nguồn tạm vào sổ tài liệu.
5. Hiển thị Nguồn đang dùng, với nghĩa là nguồn owner đã bật.
6. Nguồn tạm mới tự bật.
7. Notebook source không tự bật.
8. Promote giữ nguồn tạm và không auto-enable notebook source mới.

Allowed files:
- src/aios_habit/workspace_chat_ui.py
- src/aios_habit/workspace_chat_app.py
- tests/test_workspace_chat_source_selection_ui_copy.py
- tests/test_workspace_chat_source_selection_owner_flow.py
- tests/test_workspace_chat_owner_flow.py (chỉ khi cần)
- tests/test_workspace_chat_architecture_boundary.py (chỉ khi cần)
- tests/test_workspace_chat_ui_copy.py (chỉ khi cần)

Không sửa:
- src/aios_habit/workspace_chat_models.py
- src/aios_habit/workspace_chat_store.py
- src/aios_habit/case_cockpit.py
- mọi file .ai
- mọi file dưới local_cases
- file ngoài allowed list

Tuyệt đối không:
- import từ case_cockpit.py;
- nối AI thật;
- làm answer grounding thật;
- thêm placeholder Phase 2D;
- làm Excel ingest;
- thêm dependency;
- stage, commit, push;
- tạo branch;
- reset, checkout, stash, clean hoặc update-index.

Dùng API sẵn có:
- load_notebook_sources(notebook_id)
- load_temporary_sources(conversation_id)
- load_conversation_source_selections(conversation_id)
- load_enabled_sources_for_conversation(conversation_id)
- set_source_enabled(conversation_id, source_scope, source_id, enabled)
- promote_temporary_source_to_notebook(conversation_id, temporary_source_id, notebook_id)

Không đọc/ghi JSONL trực tiếp từ UI.

Copy bắt buộc:
- Nguồn đang dùng
- Nguồn trong sổ
- Nguồn tạm trong cuộc trò chuyện
- Dùng trong cuộc trò chuyện này
- Tạm không dùng
- Thêm vào sổ tài liệu
- Đã thêm vào sổ tài liệu

Không dùng trong owner UI:
RAG, vector, embedding, chunk, retrieval, citation, claim,
provider router, Mermaid, prompt pack.

Không tuyên bố AIOS đã đọc, phân tích, đối chiếu hoặc dùng nguồn để trả lời.
Không đưa nguồn được chọn vào Nguồn chứng minh. Nguồn đang dùng chỉ là nguồn đang bật.

Yêu cầu test:
- Tạo tests/test_workspace_chat_source_selection_ui_copy.py
- Tạo tests/test_workspace_chat_source_selection_owner_flow.py
- Cover empty/source summary, notebook toggle, temporary toggle,
  auto-enable temporary source mới, promotion, giữ temp source,
  promoted notebook source không auto-enable, rerun persistence,
  no case_cockpit import và tmp_path isolation.

Chạy focused tests:
py -3 -m pytest tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_owner_flow.py tests/test_workspace_chat_architecture_boundary.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_sources_models.py tests/test_workspace_chat_sources_store.py -v

Chạy full tests:
py -3 -m pytest -q

Chạy CLI audit:
py -3 -m aios_habit.cli audit

Kiểm tra cuối:
git status --short
git diff --check
git diff --name-only

Final response đúng format:
FINAL_STATUS: PASS_PHASE2B_IMPLEMENTED | FAIL_PHASE2B
FILES_CHANGED:
- ...
FOCUSED_TESTS: <result>
FULL_TESTS: <result>
CLI_AUDIT: <result>
SCOPE_CHECK:
- AI thật: NO
- Excel ingest: NO
- Answer grounding: NO
- case_cockpit.py touched/imported: NO
- .ai touched: NO
- local_cases touched: NO
- dependency mới: NO
GIT_ACTIONS:
- staged: NO
- committed: NO
- pushed: NO
WARNINGS:
- ...
```

## 9. Risks / non-goals

### Risks

- Checkbox state không đồng bộ với persisted selection sau rerun.
- Widget key đụng nhau giữa conversation hoặc source scope.
- Temp source được lưu nhưng auto-enable thất bại giữa hai writes.
- Double-click promotion tạo notebook source trùng.
- UI hiểu nhầm selected source là source AI đã dùng.
- Selection dangling được render dù source record đã bị xóa.
- Tests vô tình ghi vào `local_cases` thật.

Mitigation chính: store là source of truth; key đầy đủ scope/conversation/source; callback nhỏ; rerun đúng một lần; promotion button biến mất sau thành công; tmp-path isolation.

### Non-goals

- AI thật.
- Excel `.xlsx` hoặc `.xls` ingest.
- Answer grounding hoặc source-use record.
- `Nguồn AIOS đã dùng`.
- Thay đổi answer placeholder Phase 2D.
- Xóa nguồn hoặc cascade cleanup.
- Sửa model/store Phase 2A.
- Sửa hoặc import Case Cockpit.
- Dependency mới.

## 10. Final recommendation

Cho Gemini code Phase 2B theo prompt ở mục 8.

Không cần owner quyết định thêm. Điểm bắt buộc khi review implementation là xác nhận ba invariant:

1. nguồn tạm mới tự bật;
2. notebook source và notebook source mới sau promotion không tự bật;
3. `Nguồn đang dùng` không bị trình bày như bằng chứng hoặc nguồn AIOS đã thật sự dùng để trả lời.

Final status: `PASS_READY_FOR_GEMINI_PHASE2B_IMPLEMENTATION`.
