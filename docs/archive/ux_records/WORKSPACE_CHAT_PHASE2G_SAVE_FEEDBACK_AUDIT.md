# WORKSPACE_CHAT_PHASE2G_SAVE_FEEDBACK_AUDIT

## 1. Kết luận

Final status: `PASS_NEEDS_GEMINI_SAVE_FEEDBACK_MICROFIX`.

Nút `Lưu vào hồ sơ` hiện chỉ là placeholder. Không có hồ sơ, nguồn, answer draft, timestamp hoặc `saved_case_id` nào được tạo/cập nhật. Owner không thấy phản hồi ngay vì callback chỉ đổi session state sau khi vùng thông báo của lượt render hiện tại đã chạy xong, nhưng không gọi rerun.

Không được sửa copy thành một thông báo “đã lưu thành công”, vì hiện không có thao tác lưu thật để chứng minh. Microfix an toàn nhất là hiển thị ngay một thông báo trung thực rằng chức năng đang mô phỏng và chưa lưu dữ liệu. Lưu hồ sơ thật cần một design gate riêng.

## 2. Baseline

Audit trên pushed state:

- Branch: `main`
- HEAD: `9deb3b8d8998129bc7436987fc9c20f6539f90b1`
- `origin/main`: `9deb3b8d8998129bc7436987fc9c20f6539f90b1`
- Commit: `9deb3b8 Improve Workspace Chat Phase 2G owner usability`
- HEAD == `origin/main`: YES
- Worktree trước audit: sạch
- `.ai`, `local_cases`, `task.md`, `walkthrough.md`, `implementation_plan.md`: sạch

## 3. Current save behavior

Luồng hiện tại:

1. `workspace_chat_ui.py` render nút từ label `Lưu vào hồ sơ`.
2. Khi click, `render_right_result_panel()` gọi callback `on_save_case()`.
3. Callback `on_save_case_cb()` trong `workspace_chat_app.py` chỉ chạy:

   ```python
   st.session_state.wsc_show_save_placeholder = True
   ```

4. Không gọi `save_conversation()`, `save_message()`, Case API hoặc một persistence helper nào.
5. Không gán `WorkspaceConversation.saved_case_id`.
6. Không tạo object đại diện cho hồ sơ.
7. Không ghi source summary, preview, answer draft hoặc timestamp.

### Trả lời tám câu audit

1. **Functional hay placeholder?** Placeholder.
2. **Object/data nào được lưu?** Không có object/data nào được lưu.
3. **Lưu ở đâu?** Không lưu xuống file/store; chỉ có cờ boolean tạm trong `st.session_state`.
4. **Có success confirmation?** Có một `st.success()` placeholder trong source, nhưng không hiện ngay sau click vì callback không rerun và vị trí render thông báo nằm trước button.
5. **Có failure confirmation?** Không. Không có thao tác persistence hoặc `try/except`, nên cũng không có failure path.
6. **Có test save feedback?** Không. Test chỉ kiểm tra label/cờ khởi tạo; không chứng minh click tạo phản hồi ngay hoặc dữ liệu được lưu.
7. **Smallest safe fix?** Rerun ngay và thay fake-success bằng thông báo owner-safe, trung thực rằng chưa lưu dữ liệu vì chức năng đang mô phỏng.
8. **Exact files Gemini được sửa?** Ghi tại mục 8.

## 4. Owner gap and root cause

### Owner gap

Owner click `Lưu vào hồ sơ` nhưng không biết:

- action có chạy hay không;
- có dữ liệu nào được lưu hay không;
- dữ liệu được lưu ở đâu;
- lỗi có xảy ra hay không.

### Root cause

Có hai nguyên nhân độc lập:

1. **Không có save implementation.** Callback chỉ set `wsc_show_save_placeholder`.
2. **Feedback render trễ.** Khối kiểm tra `wsc_show_save_placeholder` nằm phía trên panel/button. Trong lượt render có click, khối đó đã chạy trước khi callback set cờ. Callback không gọi `safe_rerun()`, nên thông báo chỉ có thể xuất hiện ở một interaction/rerun sau.

Thông báo hiện tại:

```text
🎉 [Tính năng mô phỏng] Đã kích hoạt lưu cuộc trò chuyện này thành hồ sơ sự việc mới thành công!
```

Copy có marker mô phỏng nhưng vẫn dùng ngôn ngữ “thành công”, dễ làm owner hiểu rằng hồ sơ thật đã được tạo.

## 5. Persistence and safety assessment

- `WorkspaceConversation` có field `saved_case_id`, nhưng path hiện tại không gán field này.
- Store có thể persist conversation, nhưng không có save-to-case operation trong callback.
- Không có Case object hoặc target schema được chọn trong Workspace Chat save path.
- Không có error sanitization vì không có operation có thể fail.
- Việc audit/test hiện tại không kích hoạt UI save callback và không ghi `.ai`/`local_cases`.
- Normal app startup gọi `init_chat_store()` và có thể sử dụng `local_cases/workspace_chat` theo thiết kế hiện có, nhưng microfix feedback không cần thêm write path.

Triển khai save thật bằng cách tự chọn Case schema/store sẽ vượt microfix và có nguy cơ mở rộng sang Case Cockpit. Không làm trong Phase 2G save-feedback patch.

## 6. Test coverage

Coverage hiện có:

- `tests/test_workspace_chat_ui_copy.py` chỉ assert label `Lưu vào hồ sơ`.
- `tests/test_workspace_chat_owner_flow.py` assert `wsc_show_save_placeholder` được reset khi mở sổ.
- `tests/test_workspace_chat_source_selection_owner_flow.py` khởi tạo cờ placeholder trong fixture.
- Không có test click/callback save.
- Không có test rerun sau click.
- Không có test thông báo save/simulation.
- Không có test persistence hoặc owner-safe failure.

Tests audit đã chạy:

```text
py -3 -m pytest tests/test_workspace_chat_answer_preview.py tests/test_workspace_chat_source_selection_owner_flow.py -q
31 passed in 1.12s
```

```text
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
41 passed in 0.33s
```

```text
py -3 -m aios_habit.cli audit
PASS, errors=[], warnings=[]
```

`git diff --check`: PASS.

Các test PASS chứng minh không có regression đã biết; chúng không chứng minh `Lưu vào hồ sơ` hoạt động.

## 7. Recommended Phase 2G microfix

### Scope được khuyến nghị

1. Giữ action là placeholder; không tạo Case persistence trong microfix.
2. Khi click:
   - set một feedback state rõ nghĩa;
   - gọi `safe_rerun()` để feedback xuất hiện ngay.
3. Thay `st.success()` giả thành `st.info()` hoặc `st.warning()` với copy trung thực, ví dụ:

   ```text
   Chưa lưu dữ liệu. Tính năng “Lưu vào hồ sơ” hiện đang ở chế độ mô phỏng.
   ```

4. Có thể đổi button thành `Thử lưu vào hồ sơ` hoặc thêm caption `Chức năng mô phỏng` nếu owner cần nhận biết trước khi click.
5. Test:
   - callback set feedback state;
   - callback gọi rerun;
   - feedback copy xuất hiện;
   - không gọi bất kỳ store/Case/provider function nào;
   - `.ai` và `local_cases` không bị test làm dirty.

### Không được làm

- Không nói `Đã lưu vào hồ sơ cuộc trò chuyện.` khi không có persistence.
- Không hiển thị source summary/answer/timestamp như “đã lưu” khi chúng chưa được lưu.
- Không tự nối vào Case Cockpit hoặc tự chọn Case schema.

### Follow-up riêng cho save thật

Nếu owner muốn chức năng save thật, cần design gate mới định nghĩa tối thiểu:

- object nào là hồ sơ;
- ID và target store;
- chính xác source summary/answer/timestamp nào được persist;
- idempotency và behavior khi bấm lại;
- success evidence và owner-safe failure;
- test isolation khỏi real `local_cases`;
- quan hệ với `saved_case_id` và Case Cockpit.

## 8. Allowed files for Gemini

Exact allowlist cho feedback-only microfix:

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`
- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `docs/ux/WORKSPACE_CHAT_PHASE2G_SAVE_FEEDBACK_AUDIT.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2G_SAVE_FEEDBACK_IMPLEMENTATION_AUDIT.md`

`workspace_chat_ui.py` chỉ cần sửa nếu đổi button label/caption hoặc thêm testable presentation helper. Nếu chỉ sửa callback/rerun/copy trong app, nên để file này unchanged.

## 9. Forbidden files and capabilities

- `.ai`
- `local_cases`
- `task.md`
- `walkthrough.md`
- `implementation_plan.md`
- `case_cockpit.py`
- Case Cockpit modules/tests
- `workspace_chat_store.py`
- `workspace_chat_models.py`
- provider/router/network modules
- `requirements.txt`
- `pyproject.toml`
- Excel extractor files
- image/PDF/Word/PPTX/OCR work
- RAG/vector/embedding/chunk/retrieval
- citation/source-use provenance
- schema rewrite

Phase 2E local-preview, consent fingerprint, privacy hard-block, no-partial-send and provider-error rules phải giữ nguyên.

## 10. Validation plan

Implementation microfix phải chạy:

```powershell
py -3 -m pytest tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py -q
py -3 -m pytest tests/test_workspace_chat_answer_preview.py tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md
```

Acceptance:

- feedback xuất hiện ngay sau click;
- copy không claim đã persist;
- không tạo Case/store write path;
- no raw exception;
- Phase 2E tests PASS;
- full tests và CLI audit PASS;
- runtime dirty check sạch;
- không stage/commit/push.

## 11. Git actions

- Product code modified: NO
- Tests modified: NO
- Audit note created: YES
- Staged: NO
- Committed: NO
- Pushed: NO
