# WORKSPACE_CHAT_PHASE2G_FIX_OWNER_USABILITY_DESIGN_GATE

## 1. Kết luận ngắn

Final status: `PASS_READY_FOR_GEMINI_PHASE2G_FIX_IMPLEMENTATION`.

Pilot thật đã chứng minh luồng chính hoạt động và không phát hiện lỗi crash, privacy bypass hoặc hỏng dữ liệu. Bảy phản hồi của owner chủ yếu là khoảng trống về khả năng tìm thấy chức năng, copy và mật độ hiển thị. Có thể xử lý bằng một Phase 2G-fix nhỏ, dùng lại store/model và source-selection semantics hiện có, không mở rộng answer engine.

Scope nên gồm:

- thêm luồng tạo sổ tài liệu mới bằng `save_notebook()` đã có;
- giải thích rõ chế độ xem trước trên máy và định dạng đầu vào đang hỗ trợ;
- làm rõ checkbox bật nguồn;
- thu gọn preview dài mặc định;
- bỏ phần câu trả lời bị lặp ở panel phải, giữ panel này làm tóm tắt nguồn/trạng thái/hành động.

Không triển khai ảnh/PDF/Word/PPTX, OCR, RAG, vector, citation/source-use thật hoặc thay đổi provider.

## 2. Baseline

Baseline được kiểm tra trước khi audit:

| Kiểm tra | Kết quả |
|---|---|
| Branch | `main` |
| HEAD | `049d58d` |
| `origin/main` | `049d58d` |
| HEAD == `origin/main` | YES |
| Worktree trước audit | sạch |
| `py -3 -m pytest -q` | PASS, `668 passed in 9.90s` |
| `py -3 -m aios_habit.cli audit` | PASS, không có error hoặc warning |

Baseline đúng với mốc pilot yêu cầu. Audit này không sửa product code, test, `.ai`, `local_cases`, schema hoặc dependency.

## 3. Pilot findings from owner

### F01 — Không có nút tạo sổ tài liệu mới

Màn danh sách chỉ render các sổ do `load_notebooks()` trả về. Store đã có `save_notebook()` và model `DocumentNotebook`; `init_chat_store()` cũng dùng đúng đường này để tạo bốn sổ mặc định. Vì vậy có thể thêm form tạo sổ nhỏ mà không đổi schema hay store semantics.

### F02 — “Chỉ xem trước trên máy” chưa tự giải thích

Chế độ local-preview là mặc định và không gọi provider, nhưng phần chọn chế độ chưa nói ngay lợi ích và giới hạn. Giải thích dài hiện chỉ xuất hiện trong kết quả hoặc nút giải thích, tức là đến quá muộn cho owner mới.

### F03 — Panel phải lặp câu trả lời chính

Chat giữa đã render toàn bộ assistant message. `render_right_result_panel()` lại render cùng `answer_text`, sau đó mới render nguồn, mục cần kiểm tra và việc tiếp theo. Đây là lặp nội dung thật, đặc biệt tốn chỗ trên màn hình hẹp.

### F04 — Không dán được ảnh vào ô hỏi

`st.chat_input()` hiện chỉ nhận chữ. Không có image-upload/OCR pipeline và đây không phải lỗi của luồng Phase 2 hiện tại. UI chưa nói rõ giới hạn nên owner có thể tưởng thao tác paste ảnh bị lỗi.

### F05 — Cách bật nguồn trong sổ chưa rõ

Control đã có cho từng nguồn và gọi `set_source_enabled()` đúng scope. Label hiện là `Dùng trong cuộc trò chuyện này`, trong khi phần tổng hợp dùng khái niệm `Nguồn đang bật`; hai cách gọi làm owner khó nối control với con số `0`.

### F06 — Preview Excel quá dài

Answer-preview helper đã giới hạn mỗi nguồn 300 ký tự và tối đa 20 nguồn. Tuy nhiên source card trong sidebar render trực tiếp `content_preview`, có thể dài đến 2.000 ký tự, cho cả nguồn trong sổ và nguồn tạm. Đây là nguyên nhân chính làm sidebar dài và scroll mệt.

### F07 — UI chỉ cho thêm Excel, không giải thích định dạng khác

Màn hình hiện hỗ trợ dán văn bản dài, dữ liệu test không mật và file `.xlsx`; `.xls` được chọn để trả thông báo không hỗ trợ. Không có adapter trực tiếp cho PDF/Word/ảnh trong Workspace Chat Phase 2. Khoảng trống cần sửa lúc này là copy phạm vi, không phải thêm extractor/upload.

## 4. Finding severity classification

| Finding | Phân loại | Lý do |
|---|---|---|
| F01 | `WARNING` | Không chặn pilot vì có sổ mặc định, nhưng cản owner tự tổ chức workspace. Store/model đã hỗ trợ fix nhỏ. |
| F02 | `WARNING` | Luồng an toàn đúng nhưng ý nghĩa control chưa rõ trước khi dùng. |
| F03 | `WARNING` | Không sai dữ liệu nhưng gây rối và chiếm diện tích đáng kể. |
| F04 | `OUT_OF_SCOPE` | Paste/upload ảnh và OCR là mở rộng nguồn dữ liệu, không thuộc Phase 2G-fix. Chỉ copy giới hạn thuộc scope. |
| F05 | `WARNING` | Toggle đã hoạt động và có test; vấn đề là label/placement, không phải semantics. |
| F06 | `WARNING` | Preview đã có cap nhưng cách render mặc định vẫn gây scroll nặng. |
| F07 | `OUT_OF_SCOPE` | Thêm PDF/Word/ảnh là ngoài scope; copy giải thích định dạng hiện có được phép làm trong fix. |

Không finding nào là `BLOCKER`: pilot đã chạy được, không crash và không có bằng chứng privacy/consent bị bypass. Không cần giữ một issue ở `FOLLOW_UP` nếu scope copy nhỏ có thể xử lý ngay; phần upload định dạng mới đã được ghi rõ là `OUT_OF_SCOPE`.

## 5. Proposed small fix scope

### 2G-fix.1 — Tạo sổ tài liệu mới bằng semantics có sẵn

- Trên màn `Sổ tài liệu của tôi`, thêm expander hoặc form `Tạo sổ tài liệu mới`.
- Nhận tên bắt buộc và mô tả tùy chọn.
- Tạo `DocumentNotebook` với ID mới và gọi `save_notebook()`.
- Sau khi lưu, mở sổ mới hoặc rerun để sổ xuất hiện ngay.
- Hiển thị lỗi thân thiện khi tên trống.
- Không đổi schema, file layout hoặc default notebooks.

### 2G-fix.2 — Giải thích local preview ngay tại control

- Đặt help/caption ngay dưới lựa chọn `Chỉ xem trước trên máy`.
- Copy phải nói rõ không gửi dữ liệu ra ngoài và chế độ này chỉ kiểm tra nguồn/đoạn xem trước, chưa phải phân tích cuối cùng.
- Không đổi default mode và không chạm Phase 2E consent gate.

### 2G-fix.3 — Giải thích đầu vào đang hỗ trợ

- Đặt một đoạn hướng dẫn ngắn trước nhóm thêm nguồn.
- Nêu đúng ba đường hiện có: dán văn bản dài, Excel `.xlsx`, dữ liệu test không mật.
- Nói rõ ô hỏi chỉ nhận chữ; ảnh/PDF/Word chưa được thêm trực tiếp trong màn này.
- Không thêm uploader, parser hoặc dependency mới.

### 2G-fix.4 — Làm rõ bật/tắt nguồn

- Đổi checkbox cho từng source card thành `Bật nguồn này cho cuộc trò chuyện`.
- Đổi trạng thái phụ thành `Đang bật cho cuộc trò chuyện` hoặc `Đang tắt`.
- Giữ nguyên widget key, callback và `set_source_enabled()` semantics.
- Giữ nguyên consent fingerprint: thay đổi tập nguồn vẫn bắt buộc xác nhận cloud lại.

### 2G-fix.5 — Thu gọn source preview mặc định

- Source card luôn hiện title, trạng thái, cảnh báo privacy/truncation và checkbox.
- Đưa nội dung preview vào expander đóng mặc định, ví dụ `Xem trước nguồn`.
- Bên trong chỉ hiển thị preview đã lưu; không reparse Excel.
- Áp dụng nhất quán cho nguồn trong sổ và nguồn tạm.
- Không đổi extractor, giới hạn lưu trữ hoặc nội dung nguồn.

### 2G-fix.6 — Dọn panel phải theo phương án metadata-only

Chọn phương án B: panel phải chỉ hiển thị tóm tắt nguồn đang bật, mục cần kiểm tra, việc nên làm tiếp và action hiện có.

- Không render lại toàn bộ `answer_text` ở panel phải.
- Câu trả lời vẫn nằm nguyên trong lịch sử chat giữa.
- Đổi heading từ `Bản xem trước câu trả lời` sang `Tóm tắt nguồn đang dùng` hoặc copy tương đương.
- Giữ danh sách nguồn, cảnh báo kiểm tra và các nút hiện có.
- Đây là phương án ít rủi ro hơn responsive hiding và hữu ích hơn việc chỉ bọc nội dung lặp trong một expander.

## 6. Non-goals

Phase 2G-fix không làm:

- paste/upload ảnh từ clipboard;
- OCR ảnh;
- upload hoặc extract PDF, Word, PPTX;
- thêm định dạng ngoài `.xlsx` và văn bản dài;
- viết lại Excel extractor;
- RAG, vector, embedding, chunk, retrieval;
- citation hoặc source-use provenance thật;
- thay đổi provider, cloud hoặc network path;
- thay đổi Phase 2E privacy/consent semantics;
- Case Cockpit redesign hoặc import `case_cockpit.py`;
- Memory learning engine, Today Brief hoặc Work Stream Map;
- schema migration hoặc database mới;
- dependency mới;
- sửa `.ai` hoặc `local_cases`;
- dùng dữ liệu mật/công ty thật trong test hoặc report.

## 7. UX copy proposal

Copy đề xuất, có thể chỉnh nhẹ nhưng không được đổi nghĩa:

### Tạo sổ

- Heading: `Tạo sổ tài liệu mới`
- Field: `Tên sổ`
- Optional field: `Mô tả ngắn`
- Submit: `Tạo sổ tài liệu`
- Empty error: `Vui lòng nhập tên sổ tài liệu.`
- Success: `Đã tạo sổ tài liệu mới.`

### Local preview

`Không gửi dữ liệu ra ngoài. Dùng để kiểm tra nguồn đang bật và đoạn xem trước an toàn trên máy; đây chưa phải câu trả lời phân tích cuối cùng.`

### Đầu vào hỗ trợ

`Hiện tại màn hình này hỗ trợ dán văn bản dài, thêm Excel .xlsx và tạo dữ liệu test không mật. Ô hỏi chỉ hỗ trợ nhập chữ; chưa hỗ trợ dán ảnh hoặc thêm PDF/Word trực tiếp. Các định dạng này sẽ được xem xét ở giai đoạn mở rộng nguồn dữ liệu.`

Không nói `.xls` là định dạng hỗ trợ; nếu owner chọn `.xls`, giữ thông báo chuyển sang `.xlsx` hiện có.

### Source toggle

- Checkbox: `Bật nguồn này cho cuộc trò chuyện`
- Enabled: `Đang bật cho cuộc trò chuyện`
- Disabled: `Đang tắt`
- Preview expander: `Xem trước nguồn`

### Panel phải

- Heading: `Tóm tắt nguồn đang dùng`
- Empty state: `Chưa có nguồn nào đang bật cho cuộc trò chuyện này.`

Copy cấm tiếp tục gồm các claim như `Nguồn chứng minh`, `AIOS đã chứng minh`, `AIOS đã xác minh`, hoặc ngôn ngữ ngụ ý local preview đã phân tích/citation thật.

## 8. Test plan

### UI copy

- Assert có giải thích `Không gửi dữ liệu ra ngoài`.
- Assert có mô tả văn bản dài, Excel `.xlsx`, dữ liệu test không mật.
- Assert có copy ô hỏi chỉ nhận chữ và ảnh/PDF/Word chưa hỗ trợ trực tiếp.
- Assert có label `Bật nguồn này cho cuộc trò chuyện`.
- Assert có heading panel metadata mới và không còn heading gây hiểu rằng câu trả lời bị render lần hai.
- Tiếp tục scan forbidden technical/overclaim copy.

### Notebook creation

- Test helper/UI dùng `DocumentNotebook` và `save_notebook()` hiện có.
- Tên trống không tạo sổ.
- Tên hợp lệ tạo đúng một sổ, giữ Unicode tiếng Việt/Nhật.
- Không tạo schema/file path mới và không thay đổi default notebook initialization.

### Source preview

- Notebook source và temporary source đều dùng preview expander đóng mặc định.
- Title, status, privacy warning, truncation warning và checkbox vẫn hiện ngoài expander.
- Long preview không bị dump trực tiếp khi card render mặc định.
- Excel preview dùng nội dung persisted, không gọi lại extractor.

### Source enable/disable và consent regression

- Existing notebook/temporary source toggle tests vẫn PASS.
- Widget key và callback scope vẫn đúng.
- Enabled/disabled state vẫn persisted qua `set_source_enabled()`.
- Tập nguồn thay đổi sau consent vẫn bị chặn và buộc xác nhận lại.
- Default local preview vẫn không gọi provider.
- Privacy hard-block Phase 2E vẫn nguyên.

### Panel cleanup

- Test panel không render `answer_text` lần hai.
- Test vẫn render nguồn, mục cần kiểm tra, việc tiếp theo và action buttons.
- Test empty state thân thiện.

### Regression commands

```powershell
py -3 -m pytest tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_answer_preview.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short
```

Kỳ vọng: focused tests PASS, full `668+` tests PASS, CLI audit PASS, không có runtime data nhạy cảm bị dirty.

## 9. Files likely allowed

Exact implementation allowlist đề xuất:

- `src/aios_habit/workspace_chat_app.py`
- `src/aios_habit/workspace_chat_ui.py`
- `tests/test_workspace_chat_ui_copy.py`
- `tests/test_workspace_chat_source_selection_ui_copy.py`
- `tests/test_workspace_chat_source_selection_owner_flow.py`
- `tests/test_workspace_chat_answer_preview.py`
- `docs/ux/WORKSPACE_CHAT_PHASE2G_FIX_OWNER_USABILITY_DESIGN_GATE.md`
- `docs/ux/WORKSPACE_CHAT_PHASE2G_FIX_IMPLEMENTATION_AUDIT.md`

`tests/test_workspace_chat_answer_preview.py` chỉ được sửa nếu cần cập nhật copy/khẳng định preview regression; không cần đổi production `workspace_chat_answer_preview.py` cho scope đề xuất.

Không cần sửa `workspace_chat_store.py` hoặc `workspace_chat_models.py`: `save_notebook()`, `DocumentNotebook` và source selection semantics đã đủ. Nếu implementation phát hiện bắt buộc phải đổi hai file này, phải dừng và báo owner thay vì tự mở rộng allowlist.

Forbidden:

- `case_cockpit.py` và mọi Case Cockpit redesign;
- `.ai`;
- `local_cases`;
- `requirements.txt`;
- `pyproject.toml`;
- ROADMAP/ARCHITECTURE;
- provider/router/network modules;
- Excel extractor implementation.

## 10. Risks

1. **Streamlit rerun/form state:** tạo sổ rồi rerun có thể làm mất success message. Dùng session-state message hoặc mở sổ mới ngay, nhưng không tạo state machine mới.
2. **Duplicate notebook names:** store không có uniqueness rule. Phase 2G-fix không nên tạo schema/rule mới; ID phải unique, còn tên trùng có thể được phép hoặc báo nhẹ trong UI.
3. **Expander test mocks:** test double hiện chưa có `expander()`. Cần bổ sung mock context manager nhỏ và assert `expanded=False`, không test bằng substring source code đơn thuần nếu có thể render helper.
4. **Consent regression:** chỉ đổi copy/placement của source checkbox; không đổi key/callback/fingerprint.
5. **Panel contract:** `answer_text` có thể còn trong function signature để giảm patch size, nhưng phải không được render lần hai. Có thể bỏ parameter chỉ khi cập nhật mọi caller/test trong allowlist.
6. **Small-screen layout:** metadata-only giảm duplication nhưng không giải quyết responsive toàn diện. Responsive redesign là follow-up, không mở scope.
7. **Scope wording:** copy không được hứa ngày hỗ trợ ảnh/PDF/Word và không được ám chỉ `.xls` đã hỗ trợ.

## 11. Gemini implementation prompt

```text
Bạn là Gemini, implement WORKSPACE_CHAT_PHASE2G_FIX_OWNER_USABILITY theo design gate:
docs/ux/WORKSPACE_CHAT_PHASE2G_FIX_OWNER_USABILITY_DESIGN_GATE.md

Baseline bắt buộc trước khi sửa:
- branch phải là main
- HEAD phải là 049d58d
- origin/main phải là 049d58d
- worktree phải sạch
- py -3 -m pytest -q phải PASS (baseline hiện tại 668 passed)
- py -3 -m aios_habit.cli audit phải PASS

Nếu bất kỳ baseline nào sai hoặc worktree dirty:
- STOP
- không sửa gì
- báo FAIL_BASELINE_NOT_READY

Mục tiêu:
1. Thêm form/expander "Tạo sổ tài liệu mới" ở màn danh sách sổ.
   - Dùng DocumentNotebook và save_notebook() đã có.
   - Tên bắt buộc, mô tả tùy chọn, ID unique.
   - Không đổi store/schema/default notebooks.
2. Thêm help text ngay dưới chế độ "Chỉ xem trước trên máy":
   "Không gửi dữ liệu ra ngoài. Dùng để kiểm tra nguồn đang bật và đoạn xem trước an toàn trên máy; đây chưa phải câu trả lời phân tích cuối cùng."
3. Thêm copy phạm vi input:
   - hỗ trợ dán văn bản dài;
   - Excel .xlsx;
   - dữ liệu test không mật;
   - ô hỏi chỉ nhận chữ;
   - chưa hỗ trợ dán ảnh hoặc thêm PDF/Word trực tiếp trong màn này.
4. Đổi source checkbox thành "Bật nguồn này cho cuộc trò chuyện".
   - trạng thái: "Đang bật cho cuộc trò chuyện" / "Đang tắt".
   - giữ nguyên widget keys, callbacks, source scopes và set_source_enabled semantics.
5. Thu gọn preview của cả notebook source và temporary source.
   - title/status/privacy/truncation/toggle vẫn hiện ngay.
   - preview nằm trong st.expander("Xem trước nguồn", expanded=False).
   - không reparse Excel và không đổi limits/extractor.
6. Dọn panel phải theo phương án metadata-only.
   - không render lại answer_text đã có trong chat giữa;
   - heading "Tóm tắt nguồn đang dùng";
   - vẫn giữ nguồn đang bật, mục cần kiểm tra, việc tiếp theo và hai action hiện có.
7. Thêm/cập nhật tests cho notebook creation, copy, collapsed preview, toggle regression và panel không lặp answer.
8. Tạo docs/ux/WORKSPACE_CHAT_PHASE2G_FIX_IMPLEMENTATION_AUDIT.md ghi rõ diff, tests, warnings và git status.

Exact allowed files:
- src/aios_habit/workspace_chat_app.py
- src/aios_habit/workspace_chat_ui.py
- tests/test_workspace_chat_ui_copy.py
- tests/test_workspace_chat_source_selection_ui_copy.py
- tests/test_workspace_chat_source_selection_owner_flow.py
- tests/test_workspace_chat_answer_preview.py
- docs/ux/WORKSPACE_CHAT_PHASE2G_FIX_OWNER_USABILITY_DESIGN_GATE.md
- docs/ux/WORKSPACE_CHAT_PHASE2G_FIX_IMPLEMENTATION_AUDIT.md

Không sửa workspace_chat_store.py hoặc workspace_chat_models.py. Nếu thật sự cần, STOP và báo owner.

Forbidden:
- không sửa file ngoài allowlist;
- không stage, commit, push, tạo branch;
- không reset, checkout, stash, clean, update-index;
- không sửa .ai hoặc local_cases;
- không import/sửa case_cockpit.py;
- không thêm dependency;
- không thêm RAG/vector/embedding/chunk/retrieval;
- không thêm citation/source-use thật;
- không thêm image/PDF/Word/PPTX upload hoặc OCR;
- không rewrite Excel extractor;
- không đổi provider/cloud/network;
- không dùng dữ liệu mật/công ty thật;
- không làm yếu Phase 2E consent/privacy gate.

Copy phải là tiếng Việt dễ hiểu, UTF-8 đúng dấu. Không dùng technical jargon hoặc claim rằng AIOS đã phân tích/chứng minh/trích dẫn nguồn trong local preview.

Tests bắt buộc:
py -3 -m pytest tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_answer_preview.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short

Acceptance:
- tất cả tests và audit PASS;
- no new dependency;
- no runtime sensitive dirty data;
- source toggle semantics và cloud consent fingerprint nguyên vẹn;
- answer không còn lặp đầy đủ ở panel phải;
- long source preview không bung mặc định;
- tạo sổ mới dùng store/model sẵn có;
- implementation audit được tạo;
- staged/committed/pushed đều NO.
```

## 12. Final recommendation

`PASS_READY_FOR_GEMINI_PHASE2G_FIX_IMPLEMENTATION`

Gemini có thể implement với allowlist ở mục 9 và prompt ở mục 11. Không cần owner quyết định thêm trước khi bắt đầu vì:

- phương án panel đã chốt là metadata-only, ít rủi ro;
- notebook creation dùng function/model sẵn có;
- upload ảnh/PDF/Word/PPTX đã loại khỏi scope;
- Phase 2E privacy/consent gate được giữ nguyên;
- test plan bao phủ copy, toggle, preview, notebook creation và regression.

Nếu implementation cần sửa store/model, dependency, provider hoặc extractor thì phải dừng và xin quyết định owner; đó không còn là Phase 2G-fix nhỏ đã duyệt.
