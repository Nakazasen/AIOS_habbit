# WORKSPACE_CHAT_PHASE2C_IMPLEMENTATION_AUDIT

## 1. Kết luận ngắn

- Final status: `PASS_WITH_WARNINGS_NEEDS_TEST_HARDENING`.
- Implementation bám design gate và không thấy bug functional cần Gemini sửa.
- Chưa commit-ready theo gate test nghiêm ngặt: test chưa thực sự kích hoạt giới hạn `20_000` non-empty cells, chưa test `.xlsm` riêng, và app failure flow mới được kiểm bằng source inspection thay vì callback/runtime test.
- Blocker lớn nhất chỉ là độ kín của test, không phải implementation.

## 2. Baseline / dirty files

Baseline trước audit:

- Branch: `main`.
- HEAD: `725a378`.
- `origin/main`: `725a378`.
- Dirty tree có đúng bốn file dự kiến:
  - `src/aios_habit/workspace_chat_excel.py`
  - `src/aios_habit/workspace_chat_app.py`
  - `tests/test_workspace_chat_excel_ingest.py`
  - `tests/test_workspace_chat_source_selection_owner_flow.py`
- Không có dirty entry cho `.ai`, `local_cases`, `task.md`, `walkthrough.md` hoặc `implementation_plan.md`.
- `task.md`, `walkthrough.md` và `implementation_plan.md` không phải tracked files.

## 3. Excel adapter audit

### Public API và support boundary

- Có immutable dataclass `ExtractedWorkspaceSource`.
- Có `extract_xlsx_text(file_bytes: bytes, filename: str)`.
- `.xlsx` được nhận case-insensitive.
- `.xls` bị từ chối trước `openpyxl` với đúng copy:

```text
File .xls chưa được hỗ trợ. Vui lòng mở file bằng Excel và lưu lại dạng .xlsx.
```

- `.xlsm` và extension khác bị từ chối thân thiện vì chỉ `.xlsx` đi qua parser.
- Raw `openpyxl`, ZIP hoặc traceback details không được trả ra owner message.

### Local-only và side effects

- Không import Streamlit, store, Case Cockpit, AI/RAG/retrieval/vector/embedding module.
- Không ghi filesystem.
- Không có network/cloud call.
- Dùng `BytesIO`.
- Dùng:

```python
openpyxl.load_workbook(
    BytesIO(file_bytes),
    read_only=True,
    data_only=False,
    keep_links=False,
)
```

- Workbook được đóng trong `finally`; lỗi khi close cũng không leak.

### Safety limits

Implementation có đúng:

- upload limit: `10 * 1024 * 1024`;
- ZIP uncompressed guard: `50 * 1024 * 1024`;
- max sheets: `12`;
- max rows/sheet: `1000`;
- max non-empty cells: `20_000`;
- corrupt ZIP trả friendly failure.

ZIP preflight chỉ tính metadata `file_size`; không đưa member name/path vào output.

### Text extraction

- Header có `File Excel: <filename>`.
- Mỗi sheet có `Trang tính: <sheet>`.
- Cell có format `A1=value`.
- Giữ thứ tự sheet/row.
- Bỏ `None` và whitespace-only.
- Giữ `0` và `False`.
- Normalize whitespace nội bộ.
- Giữ Unicode Việt/Nhật.
- Date/time được serialize ổn định bằng ISO format.
- Formula được giữ dưới dạng biểu thức nhờ `data_only=False`; không recalculate.
- Merged cells chỉ giữ anchor có value; các `MergedCell` rỗng bị bỏ qua.
- Không có code đọc chart/image/comment/shape/macro hoặc external link.

### Cap và truncation

- Preview được cắt theo `WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT`.
- Text được cap UTF-8 theo `WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES`.
- Cap xảy ra trong extractor trước khi app tạo/save `TemporaryConversationSource`.
- Khi hit sheet/row/cell/text limits, `truncated=True`.
- Owner message nói rõ chỉ đọc một phần.

Edge concern trong prompt đã được xử lý đúng: sau khi nối `TRUNCATED_MESSAGE`, implementation gọi `_cap_utf8(...)` lần nữa, nên text cuối vẫn không vượt 200 KiB. Thông báo có thể bị cắt khỏi `text` nếu cap đã đầy, nhưng vẫn còn nguyên trong `owner_message`, đáp ứng yêu cầu “owner message hoặc text”.

Khi dừng vì sheet limit, `sheet_names` chỉ chứa 12 sheet thực sự đã xử lý; semantics này hợp lý và đã được test.

Workbook chỉ có sheet rỗng trả `EMPTY_WORKBOOK_MESSAGE`.

## 4. App wiring audit

### Uploader/form

- Có đủ copy:
  - `Thêm file Excel .xlsx`
  - `Chọn file Excel cho cuộc trò chuyện này`
  - `Đọc và thêm vào nguồn tạm`
- Form và uploader key chứa `active_conversation.id`.
- Ingest chỉ chạy khi submit; passive rerun không tự ingest.
- Uploader ở main chat area, cạnh paste-text flow.

### Success flow

Production order đúng:

1. `extract_xlsx_text(...)`;
2. tạo `TemporaryConversationSource(source_type="xlsx")`;
3. map filename/preview/text từ extraction result;
4. `save_temporary_source(...)`;
5. `set_source_enabled(..., SOURCE_SCOPE_TEMPORARY, ..., True)`;
6. `safe_rerun()`.

Không có rerun giữa save và enable. Cap đã hoàn tất trước khi source được tạo/save.

### Failure flow

- Nếu chưa chọn file hoặc extract thất bại, UI gọi `st.error(...)`.
- Không save, không enable và không success-rerun.
- Chỉ hiện friendly message, không raw exception.

### Scope preservation

- Không auto-promote.
- Không auto-enable notebook source mới.
- Ba source-selection helper Phase 2B vẫn nằm trong `with st.sidebar:`.
- Chat, paste và Excel uploader vẫn ở main area.
- Không thêm AI thật hoặc answer grounding.
- Copy Phase 2C không claim đã phân tích/đối chiếu/trích dẫn hoặc dùng Excel để trả lời.

## 5. XLSX behavior audit

| Behavior | Kết quả |
|---|---|
| `.xlsx` / `.XLSX` | PASS |
| `.xls` unsupported, không parse | PASS |
| `.xlsm` không parse | PASS qua đọc code |
| One/multi-sheet order | PASS |
| Empty/whitespace cells skipped | PASS |
| `0` / `False` retained | PASS |
| Unicode Việt/Nhật | PASS |
| Formula text preserved | PASS |
| Merged anchor once | PASS |
| Empty workbook friendly | PASS |
| Corrupt ZIP friendly | PASS |
| Upload/ZIP/sheet/row/text/preview limits | PASS |
| Cell-count limit implementation | PASS qua đọc code; thiếu dedicated test |
| UTF-8 final text cap after truncation notice | PASS |
| Temporary source auto-enabled | PASS qua code/wiring inspection |
| No duplicate ingest on passive rerun | PASS qua form structure |

## 6. Test coverage audit

### Đã cover

- one-sheet workbook;
- multi-sheet order;
- empty cells;
- giữ `0` và `False`;
- Unicode Việt/Nhật;
- formula preserved;
- merged anchor;
- empty workbook;
- corrupt `.xlsx`;
- `.xls` không gọi `openpyxl`;
- uppercase `.XLSX`;
- extension khác;
- upload quá lớn;
- ZIP uncompressed quá lớn;
- sheet limit;
- row/text/preview cap;
- no filesystem write/network attempt;
- uploader copy/key;
- source type/mapping;
- extract → save → enable temporary → rerun order;
- failure branch không có save/enable/rerun gần error call;
- không auto-promote/auto-enable notebook;
- sidebar placement regression.

### Cần harden

1. Test tên `test_row_cell_preview_and_text_limits` chỉ tạo khoảng 1.049 non-empty cells trong một cột. Row limit dừng ở 1.000, nên nhánh `MAX_NON_EMPTY_CELLS > 20_000` không được kích hoạt.
2. Chưa có test `.xlsm` riêng để khóa boundary `.xlsx` only.
3. App tests dùng source-string/position inspection; chưa gọi callback/form flow với mocked Streamlit để chứng minh failure `.xls`/corrupt file không save, không enable và passive rerun không ingest.
4. Chưa có boundary test dành riêng cho trường hợp text gần đúng 200 KiB rồi nối truncation notice, dù implementation hiện cap lại đúng.
5. Chưa monkeypatch/spy `workbook.close()` để khóa cleanup contract.

Vì implementation đúng nhưng checklist test chưa kín, status là `PASS_WITH_WARNINGS_NEEDS_TEST_HARDENING`, không phải `FAIL_NEEDS_GEMINI_FIX`.

## 7. Architecture / safety scan

Scan có các hit:

- `src/aios_habit/workspace_chat_app.py`: `Nguồn chứng minh` chỉ nằm trong comment Phase 1 có sẵn, không phải Phase 2C addition.
- `tests/test_workspace_chat_excel_ingest.py`: `socket` chỉ dùng để chặn network trong test; đây là safety guard, không phải network call của production.
- Architecture test có tên/comment/import smoke liên quan `case_cockpit`; production Phase 2C không import nó.

Không có production hit cho:

- `case_cockpit`, `case_ingest`, `case_store`;
- `.ai` hoặc `local_cases` direct write;
- git action;
- AI/RAG/retrieval/vector/embedding;
- `requests`, `urllib`, `httpx`, `socket` hoặc `open(...)`.

Không sửa model/store Phase 2A, Case Cockpit hoặc dependency manifest.

## 8. Test results

- Focused tests: `65 passed in 2.50s`.
- Full pytest: `599 passed in 7.77s`.
- CLI audit: `PASS`, không errors/warnings.
- `git diff --check`: pass; chỉ có Git LF/CRLF warnings cho hai tracked files.

## 9. Post-test git status

Ngay sau test và trước khi tạo report:

- Dirty tree vẫn chỉ có đúng bốn implementation/test files dự kiến.
- Không phát sinh `.ai`, `local_cases`, runtime/generated data, `task.md`, `walkthrough.md`, `implementation_plan.md` hoặc file ngoài scope.

Sau audit, report này là file mới duy nhất do Codex tạo theo yêu cầu.

## 10. Commit recommendation

- Chưa stage hoặc commit file nào.
- Chưa khuyến nghị commit cho tới khi harden các test nêu ở mục 6.
- Exact implementation files sẽ safe to stage sau test hardening/re-audit:
  - `src/aios_habit/workspace_chat_excel.py`
  - `src/aios_habit/workspace_chat_app.py`
  - `tests/test_workspace_chat_excel_ingest.py`
  - `tests/test_workspace_chat_source_selection_owner_flow.py`
- Report có thể stage riêng nếu quy trình lưu audit:
  - `docs/ux/WORKSPACE_CHAT_PHASE2C_IMPLEMENTATION_AUDIT.md`
- Không safe to stage:
  - `.ai`
  - `local_cases`
  - `task.md`
  - `walkthrough.md`
  - `implementation_plan.md`
  - file ngoài exact scope.

Suggested commit message sau hardening và re-audit:

```text
Implement Workspace Chat Phase 2C XLSX ingest
```

Final status: `PASS_WITH_WARNINGS_NEEDS_TEST_HARDENING`.
## 11. Post-audit test hardening

Codex audit returned `PASS_WITH_WARNINGS_NEEDS_TEST_HARDENING`.

Additional tests were hardened for:

- Real `MAX_NON_EMPTY_CELLS` limit activation.
- `.xlsm` rejected without parsing.
- Near-200 KiB text cap after truncation notice.
- Workbook close cleanup contract.
- App failure flow: failed Excel extract does not save, enable, or success-rerun.
- Passive rerun does not ingest duplicate uploads.
- Success flow remains extract -> save temp -> enable temporary -> safe_rerun.

Final hardening result: `PASS after tests`.

Updated commit readiness: `PASS_READY_FOR_PHASE2C_COMMIT`.
