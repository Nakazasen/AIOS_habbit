# WORKSPACE_CHAT_PHASE2D_IMPLEMENTATION_AUDIT

## 1. Kết luận ngắn

Final status: `FAIL_NEEDS_GEMINI_FIX`.

Implementation helper và luồng submit chính bám phần lớn design gate; focused tests, full pytest và CLI audit đều pass. Tuy nhiên Phase 2D chưa commit-ready vì còn hai lỗi production UI:

1. Panel `Nguồn đang bật cho cuộc trò chuyện` vẫn lấy toàn bộ temporary sources, gồm cả nguồn đang tắt, đồng thời bỏ qua notebook sources đang bật.
2. Popup giải thích vẫn overclaim rằng đã “phân tích đối chiếu” và các ý “khớp hoàn toàn với nguồn tạm”, trái với gate chưa có AI/grounding thật.

Blocker lớn nhất là semantics panel và copy owner-facing không trung thực. Test hiện tại không bắt được hai lỗi này.

## 2. Baseline / dirty files

Baseline trước audit:

- Branch: `main`.
- HEAD: `16834da`.
- `origin/main`: `16834da`.
- `HEAD == origin/main`: có.
- Dirty tree có đúng sáu file Gemini reported:
  - `src/aios_habit/workspace_chat_answer_preview.py`
  - `src/aios_habit/workspace_chat_app.py`
  - `src/aios_habit/workspace_chat_ui.py`
  - `tests/test_workspace_chat_answer_preview.py`
  - `tests/test_workspace_chat_source_selection_owner_flow.py`
  - `tests/test_workspace_chat_ui_copy.py`
- Không có dirty entry cho `.ai`, `local_cases`, `task.md`, `walkthrough.md` hoặc `implementation_plan.md`.
- `task.md`, `walkthrough.md`, `implementation_plan.md` không phải tracked files.

Không có unexpected dirty file trước khi chạy test.

## 3. Answer preview helper audit

File: `src/aios_habit/workspace_chat_answer_preview.py`

### Public API

PASS:

- Có immutable `WorkspaceTrialSourcePreview`.
- Có immutable `WorkspaceTrialAnswerPreview`.
- Có immutable `WorkspaceTrialSourceInput`.
- Có `build_trial_answer_preview(...)`.

### Pure/local-only boundary

PASS:

- Không import Streamlit, store, Excel adapter hoặc `openpyxl`.
- Không import provider/router/network/cloud module.
- Không gọi AI.
- Không đọc/ghi filesystem.
- Không có side effect.

### Required copy

PASS:

- `Bản thử nghiệm`
- `AIOS chưa nối AI thật ở bước này.`
- `Nguồn đang bật cho cuộc trò chuyện`
- `Đây chưa phải câu trả lời phân tích cuối cùng.`
- Trường hợp rỗng có `Chưa có nguồn nào đang bật cho cuộc trò chuyện này.`

### Preview behavior

PASS:

- Ưu tiên `content_preview`.
- Fallback sang `content_text` khi preview rỗng.
- Normalize whitespace.
- Cap `300` ký tự/source.
- Cap `20` source hiển thị.
- Có thông báo số nguồn còn lại.
- Không nối full `content_text`.
- Giữ Unicode Việt/Nhật.

### Source display

PASS:

- `xlsx` → `Excel`.
- `text`, `pasted_text`, `plain_text` → `Văn bản`.
- Type khác → `Nguồn`.
- Không đưa source ID hoặc scope enum vào `answer_text`.

`enabled_sources` output vẫn giữ ID/scope nội bộ, nhưng đây là structured return cho code chứ không phải owner-facing copy; hợp lệ.

### No overclaim

PASS trong helper:

- Không có forbidden claim/citation wording.
- Không tạo citation marker.
- Không diễn giải hoặc kết luận từ source.

## 4. App wiring audit

### Submit flow

PASS:

Luồng khi owner gửi câu hỏi đúng thứ tự:

1. tạo và save user `ChatMessage`;
2. gọi `load_enabled_sources_for_conversation(active_conversation.id)`;
3. load notebook sources của notebook hiện tại;
4. load temporary sources của conversation hiện tại;
5. resolve theo `source_scope` và `source_id`;
6. bỏ qua selection mồ côi;
7. gọi `build_trial_answer_preview(user_input, enabled_preview_sources)`;
8. save assistant `ChatMessage(content=preview.answer_text)`;
9. `safe_rerun()`.

PASS thêm:

- Notebook source chỉ resolve trong lookup notebook hiện tại.
- Temporary source chỉ resolve trong lookup conversation hiện tại.
- Không dùng `WorkspaceConversation.selected_source_ids`.
- Không parse lại `.xlsx` trong submit branch.
- Không gọi `openpyxl`.
- Không cập nhật `used_in_last_answer`/`last_used_at`.
- Không tạo model/source snapshot mới.
- Passive rerun không nằm trong submit branch nên không tự tạo placeholder.
- Một submit có đúng một save user và một save assistant theo code path.

### Functional defect: right result panel

FAIL:

Sau submit, panel có nhãn mới `Nguồn đang bật cho cuộc trò chuyện`, nhưng dữ liệu vẫn được dựng từ:

```python
temp_sources_list = load_temporary_sources(active_conversation.id)
```

Sau đó app append mọi temporary source vào danh sách, không kiểm selection enabled. Hậu quả:

- temporary source đang tắt vẫn được hiển thị như đang bật;
- notebook source đang bật không được hiển thị;
- panel và placeholder chat có thể mâu thuẫn nhau;
- empty message nói không có nguồn tạm, không nói đúng trạng thái enabled sources.

Gemini cần dùng cùng resolved enabled-source snapshot/logic trung thực cho panel, hoặc render danh sách từ structured preview tương ứng với assistant placeholder. Không được quay lại lấy toàn bộ temporary sources.

### Functional defect: explain popup overclaim

FAIL:

Production app vẫn có owner-facing popup:

```text
[Tính năng mô phỏng] Gợi ý phân tích đối chiếu nguồn tài liệu: Các ý chính trong câu trả lời đều khớp hoàn toàn với nguồn tạm.
```

Copy này tuyên bố đã đối chiếu và khớp hoàn toàn khi Phase 2D chưa có AI/grounding thật. Đây là real overclaim, không phải comment hoặc false positive.

Popup phải được thay bằng copy trung tính về đoạn xem trước/nguồn đang bật, hoặc action giải thích phải bị vô hiệu hóa trong placeholder phase. Không được nói đã phân tích, đối chiếu, xác minh hoặc khớp nguồn.

## 5. UI copy audit

### Labels

PASS:

- `Bản xem trước câu trả lời`
- `Nguồn đang bật cho cuộc trò chuyện`
- `Điều owner cần kiểm tra`
- Action mới dùng `Xem đoạn xem trước sẽ dùng ở bước sau`

Các owner-facing copy cũ sau đã được bỏ khỏi `workspace_chat_ui.py`:

- `Trả lời chính`
- `Nguồn chứng minh`
- `Ý cần kiểm lại`
- `Xem vì sao AIOS kết luận như vậy`

### Remaining risks

FAIL:

- Popup trong `workspace_chat_app.py` vẫn overclaim như mục 4.
- Panel label đã trung tính nhưng data semantics vẫn sai.
- Panel vẫn tạo các next action cố định về lỗi vận hành/kiểm chứng dù không dựa trên câu hỏi; đây không phải blocker độc lập, nhưng nên đổi sang hướng dẫn trung tính hoặc bỏ trong placeholder phase để tránh tạo cảm giác hệ thống đã suy luận.

Warning:

- Hai comment production còn dùng cụm `nguồn chứng minh`. Comment không owner-facing nên không phải functional fail, nhưng nên đổi để code semantics không tiếp tục gây nhầm.
- Tên parameter/key nội bộ `proven_sources` có thể giữ để giảm scope, nhưng đổi sang neutral naming sẽ dễ bảo trì hơn.

## 6. Test coverage audit

### Đã cover tốt

- Không có source.
- Notebook source trong builder.
- Temporary pasted-text source trong builder.
- `.xlsx` dùng persisted preview, không parse lại.
- Blank preview fallback và cap 300.
- Unicode Việt/Nhật.
- Cap 20 source và remaining count.
- Forbidden copy trong helper.
- Pure helper architecture.
- Submit source inspection xác nhận gọi enabled selections.
- Submit order bằng source position inspection.
- Không re-parse `.xlsx` trong submit block.
- Không cập nhật fake source-use metadata.
- Không import Case Cockpit trong app.
- Existing store tests dùng isolated paths; post-test không phát sinh `local_cases`.

### Thiếu hoặc chưa đủ mạnh

1. Không có runtime/callback test thực sự đưa enabled + disabled sources vào app resolution và assert disabled source bị loại.
2. Không có runtime test selection mồ côi.
3. Không có runtime test source khác conversation/notebook bị loại.
4. Không có runtime test kết hợp notebook enabled và temporary enabled.
5. Không test panel `Nguồn đang bật` dùng đúng resolved enabled sources.
6. Không test popup/action không overclaim.
7. Forbidden production-copy test chỉ scan danh sách technical words cũ, không scan các semantic overclaim như `phân tích đối chiếu` hoặc `khớp hoàn toàn`.
8. App tests Phase 2D chủ yếu là source-string/position inspection, nên implementation có thể đúng hình dạng nhưng sai runtime semantics.

Vì thiếu test đi kèm bug production thật, verdict không phải `PASS_WITH_WARNINGS_NEEDS_TEST_HARDENING`; cần `FAIL_NEEDS_GEMINI_FIX`.

## 7. Architecture / safety scan

### Legitimate/false-positive hits

- `extract_xlsx_text` trong `workspace_chat_app.py` thuộc uploader Phase 2C, không nằm trong Phase 2D submit path.
- `extract_xlsx_text`/`openpyxl` trong tests là monkeypatch/guard hoặc Phase 2C tests.
- Forbidden terms trong `FORBIDDEN_COPY` và architecture assertions là test data, không phải production UI.
- `case_cockpit` trong architecture tests là boundary/smoke test.
- `open(` hit ở `on_open(...)` là substring match, không phải filesystem call.
- `Nguồn chứng minh` trong hai production comments không owner-facing.

### Real risks

- Popup production overclaim nêu ở mục 4.
- Panel production dùng toàn bộ temporary sources thay vì enabled sources.

### Boundary verdict

PASS:

- Helper/app/UI Phase 2D không import Case Cockpit, case ingest hoặc case store.
- Không có AI/provider/router/cloud/network addition.
- Không có RAG/vector/embedding/chunk/retrieval framework.
- Không có dependency mới.
- Không ghi `.ai` hoặc `local_cases` trong audit.

## 8. Test results

Focused command:

```powershell
py -3 -m pytest tests/test_workspace_chat_answer_preview.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_owner_flow.py tests/test_workspace_chat_architecture_boundary.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_excel_ingest.py tests/test_workspace_chat_sources_models.py tests/test_workspace_chat_sources_store.py -v
```

Result:

```text
87 passed in 3.07s
```

Full command:

```powershell
py -3 -m pytest -q
```

Result:

```text
621 passed in 8.08s
```

CLI audit:

```powershell
py -3 -m aios_habit.cli audit
```

Result:

```json
{
  "errors": [],
  "status": "PASS",
  "warnings": []
}
```

Green tests do not override the two uncovered production defects.

## 9. Post-test git status

Ngay sau tests và trước khi tạo report:

- Dirty tree vẫn có đúng sáu implementation/test files dự kiến.
- Không phát sinh `.ai`, `local_cases`, runtime/generated data, `task.md`, `walkthrough.md`, `implementation_plan.md` hoặc file ngoài scope.
- `git diff --check` không có whitespace error; chỉ có LF→CRLF working-copy warnings.

Sau audit, report này là file mới duy nhất do Codex tạo theo yêu cầu.

## 10. Commit recommendation

Chưa commit-ready. Không stage file nào trước khi Gemini sửa hai lỗi và bổ sung regression tests.

Hiện tại không có file Phase 2D nào được khuyến nghị stage như một commit hoàn chỉnh.

Exact implementation/test files cần được giữ trong scope để Gemini sửa và re-audit:

- `src/aios_habit/workspace_chat_answer_preview.py`
- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`
- `tests/test_workspace_chat_answer_preview.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`

Report audit có thể được lưu riêng nếu quy trình yêu cầu:

- `docs/ux/WORKSPACE_CHAT_PHASE2D_IMPLEMENTATION_AUDIT.md`

Không safe to stage:

- `.ai`
- `local_cases`
- `task.md`
- `walkthrough.md`
- `implementation_plan.md`
- mọi file ngoài exact Phase 2D scope

Gemini fix bắt buộc:

1. Panel phải render đúng notebook + temporary sources đang enabled, loại disabled/orphan/cross-scope sources.
2. Xóa/thay popup overclaim `phân tích đối chiếu` / `khớp hoàn toàn`.
3. Thêm runtime regression tests cho resolution và panel; thêm production-copy test cho semantic overclaim.
4. Chạy lại focused/full/CLI audit và báo exact dirty files.

Suggested commit message sau khi fix và re-audit pass:

```text
Implement Workspace Chat Phase 2D source-aware placeholder
```

Final status: `FAIL_NEEDS_GEMINI_FIX`.

## 11. Gemini fix after FAIL_NEEDS_GEMINI_FIX

Codex audit found two production UI defects:

1. The right panel rendered all temporary sources instead of enabled notebook + temporary sources.
2. The explain popup overclaimed analysis/grounding.

Fix summary:

- Panel now resolves and renders only sources enabled by `ConversationSourceSelection`.
- Enabled notebook and temporary sources are both represented.
- Disabled/orphan/cross-scope sources are excluded safely.
- Empty panel state now reflects enabled-source semantics.
- Overclaiming popup/copy was removed or replaced with neutral Phase 2D wording.
- Regression tests were added for panel semantics and overclaim copy.

Final fix result: `PASS after tests`.
Updated commit readiness: `PASS_READY_FOR_PHASE2D_REAUDIT`.

## 12. Final re-audit after Gemini fix

Final re-audit status: `FAIL_NEEDS_GEMINI_FIX`.

Verification summary:

- Panel enabled-source semantics: `PASS`.
- Popup/action overclaim removed: `PASS`.
- Regression tests sufficient: `PASS`.
- Focused tests: `90 passed in 3.44s`.
- Full pytest: `624 passed in 9.48s`.
- CLI audit: `PASS`, không errors/warnings.
- Runtime dirty data: `NO`.
- Scope violation: `NO`.
- `git diff --check`: `FAIL`.

Hai defect functional từ audit trước đã được sửa:

- Panel resolve đúng notebook + temporary sources đang enabled.
- Disabled, orphan, cross-notebook và cross-conversation sources bị loại.
- Empty state dùng đúng semantics enabled-source.
- Popup/action không còn tuyên bố đã phân tích, đối chiếu, khớp nguồn hoặc kết luận.

Regression tests hiện cover đủ hai defect. Có một warning bảo trì nhỏ: test panel lặp lại logic resolution production thay vì gọi một helper dùng chung; warning này không phải functional blocker.

Blocker commit còn lại là 17 trailing-whitespace errors do `git diff --check` phát hiện:

- 4 dòng trong `src/aios_habit/workspace_chat_app.py`.
- 13 dòng trong `tests/test_workspace_chat_source_selection_owner_flow.py`.

Gemini chỉ cần xóa trailing whitespace trong hai file trên, chạy lại focused/full/CLI audit và xác nhận `git diff --check` pass. Không cần thay đổi thiết kế hoặc logic functional.

Commit readiness: `NOT_READY` cho tới khi `git diff --check` pass.

## 13. Final whitespace-fix verification

Final status: `PASS_READY_FOR_PHASE2D_COMMIT`.

Verification:

- Panel enabled-source semantics: `PASS`.
- Popup/action overclaim removed: `PASS`.
- Regression test hardening: `PASS`.
- Trailing whitespace cleanup: `PASS`.
- `git diff --check`: `PASS`.
- Focused tests: `90 passed in 3.56s`.
- Full pytest: `624 passed in 9.24s`.
- CLI audit: `PASS`, không errors/warnings.
- Runtime dirty data: `NO`.
- Scope violation: `NO`.

Warning duy nhất là Git LF→CRLF working-copy warning cho `workspace_chat_ui.py`; đây không phải whitespace error và không chặn commit.

Các file safe to stage bằng exact path:

- `src/aios_habit/workspace_chat_answer_preview.py`
- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`
- `tests/test_workspace_chat_answer_preview.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_ui_copy.py`
- `docs/ux/WORKSPACE_CHAT_PHASE2D_IMPLEMENTATION_AUDIT.md`

Suggested commit message:

```text
Implement Workspace Chat Phase 2D source-aware placeholder
```
