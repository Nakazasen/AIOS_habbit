# WORKSPACE_CHAT_PHASE2C_XLSX_INGEST_DESIGN_GATE

## 1. Kết luận ngắn

**Final status: `PASS_READY_FOR_GEMINI_PHASE2C_IMPLEMENTATION`.**

Phase 2C có thể triển khai bằng một adapter local nhỏ dựa trên `openpyxl` đã có sẵn. Không cần thêm dependency, không cần sửa Case Cockpit, không cần nối AI và không cần thay đổi store/model Phase 2A.

Flow mặc định:

1. owner chọn một file `.xlsx` trong cuộc trò chuyện;
2. adapter đọc workbook từ bytes, tạo text dễ đọc và áp dụng cap hiện có;
3. app lưu kết quả thành `TemporaryConversationSource`;
4. app auto-enable nguồn mới trong conversation hiện tại;
5. owner có thể dùng flow Phase 2B hiện có để thêm nguồn đó vào sổ.

`.xls` không được parse trong Phase 2C. UI chỉ hướng dẫn owner lưu lại thành `.xlsx`.

## 2. Baseline

Baseline trước khi tạo report:

| Mục | Kết quả |
|---|---|
| Repo | `D:\Sandbox\AIOS_habbit` |
| Branch | `main` |
| HEAD | `9d47986` |
| `origin/main` | `9d47986` |
| Worktree | sạch |
| Commit mới nhất | `9d47986 Implement Workspace Chat Phase 2B source selection UI` |

Phase 2B đã ổn định trên `origin/main`. Không có dirty file, `.ai`, `local_cases` hoặc artifact agent-local trước design gate.

## 3. Existing source model/store summary

### Model hiện có

`TemporaryConversationSource` đã đủ cho MVP nguồn Excel tạm:

- `conversation_id`;
- `source_type`;
- `title`;
- `content_preview`;
- `content_text`;
- lifecycle status và privacy label.

`NotebookSource` có thêm `filename`, `file_type`, `extraction_status` và `source_note`. Flow promote hiện sao chép title, source type, privacy, preview và text từ nguồn tạm; nó không xóa nguồn tạm và không auto-enable notebook source mới.

Không cần sửa model trong Phase 2C. Với nguồn tạm Excel:

- `source_type="xlsx"`;
- `title` dùng tên file an toàn để owner nhận diện;
- filename, sheet và cell coordinates nằm trong extracted text;
- `content_preview` và `content_text` do adapter cap trước khi tạo model.

### Cap hiện có

`workspace_chat_models.py` đã định nghĩa:

- `WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT = 2000` ký tự;
- `WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES = 200 * 1024` bytes UTF-8.

`NotebookSource` tự áp dụng cap trong `__post_init__`, nhưng `TemporaryConversationSource` chưa tự cap. Vì Phase 2C lưu vào nguồn tạm trước, adapter bắt buộc áp dụng cả hai cap trước khi app gọi `save_temporary_source()`. Không được dựa vào bước promote để cap muộn.

### Store API dùng lại

Không cần API store mới:

```python
save_temporary_source(temporary_source)
set_source_enabled(
    conversation_id,
    SOURCE_SCOPE_TEMPORARY,
    temporary_source.id,
    True,
)
```

Thứ tự bắt buộc là extract thành công → save → auto-enable → `safe_rerun()`. Không rerun giữa hai write.

## 4. Existing Phase 2B UI integration point

Phase 2B đã có:

- danh sách nguồn tạm trong sidebar;
- selection source of truth từ store;
- widget keys có conversation/scope/source ID;
- flow paste text: tạo nguồn tạm → save → enable → rerun;
- flow promote nguồn tạm vào sổ.

Điểm cắm nhỏ nhất là vùng main chat, cạnh khung “Dán văn bản dài”. Thêm một uploader/form riêng cho Excel; không đặt uploader bên trong source list helper và không để extractor gọi Streamlit/store.

Proposed app flow:

```python
uploaded_file = st.file_uploader(
    "Thêm file Excel .xlsx",
    type=["xlsx", "xls"],
    key=f"wsc_excel_upload_{active_conversation.id}",
)

if submitted:
    result = extract_xlsx_text(uploaded_file.getvalue(), uploaded_file.name)
    if result.ok:
        temporary_source = TemporaryConversationSource(
            id=...,
            conversation_id=active_conversation.id,
            source_type="xlsx",
            title=result.filename,
            content_preview=result.preview,
            content_text=result.text,
        )
        save_temporary_source(temporary_source)
        set_source_enabled(
            active_conversation.id,
            SOURCE_SCOPE_TEMPORARY,
            temporary_source.id,
            True,
        )
        safe_rerun()
    else:
        st.error(result.owner_message)
```

Uploader key phải chứa `conversation_id` để file/widget state không rò sang conversation khác. Nên có nút submit rõ ràng để rerun không ingest cùng upload nhiều lần.

Khung chat, hỏi đáp và paste text vẫn ở main area. Summary và source lists tiếp tục nằm trong `with st.sidebar:`.

## 5. XLSX ingest design

### Files nên thêm/sửa

Allowed implementation files:

- mới: `src/aios_habit/workspace_chat_excel.py`;
- sửa: `src/aios_habit/workspace_chat_app.py`;
- mới: `tests/test_workspace_chat_excel_ingest.py`;
- có thể sửa tối thiểu: `tests/test_workspace_chat_source_selection_owner_flow.py` để kiểm app wiring;
- có thể sửa tối thiểu: `tests/test_workspace_chat_ui_copy.py` hoặc `tests/test_workspace_chat_source_selection_ui_copy.py` để kiểm owner copy/forbidden terms.

Không cần sửa:

- `src/aios_habit/workspace_chat_models.py`;
- `src/aios_habit/workspace_chat_store.py`;
- `src/aios_habit/workspace_chat_ui.py`, trừ khi tách một helper upload thuần UI thật sự làm test rõ hơn;
- `src/aios_habit/case_cockpit.py` và mọi Case Cockpit module;
- dependency manifests.

### Dependency và reuse audit

`pyproject.toml` đã có:

```text
openpyxl>=3.1.0
pandas>=2.0.0
```

Môi trường audit có `openpyxl 3.1.5`. Không cần dependency mới; `pandas` cũng không cần cho adapter MVP.

Repo có ba nhóm code Excel:

- `case_ingest.py` và `source_ingest.py`: dựa trên pandas, gắn với flow/path khác và có hành vi `.xls`; không reuse vì Phase 2C cấm coupling Case Cockpit.
- `mom_local_index.py`: đọc preview bằng pandas nhưng gắn với indexing/chunking, không phù hợp Workspace Chat.
- `document_extractors._extract_excel(path)`: dùng `openpyxl`, giới hạn 12 sheet/25 row và đã chứng minh cách đọc local hoạt động. Tuy nhiên nó nhận filesystem `Path`, trả nhiều `ExtractionResult`, hỗ trợ `.xlsm` và còn đọc shapes/text boxes. Import trực tiếp sẽ kéo contract rộng hơn Phase 2C và buộc ghi file tạm.

Kết luận reuse: dùng cùng thư viện và các guard/giới hạn đã được chứng minh, nhưng tạo adapter bytes riêng cho Workspace Chat. Không copy phần shapes/OCR/indexing và không import Case Cockpit. Adapter dự kiến nhỏ, không phải extractor framework mới.

### Proposed module

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ExtractedWorkspaceSource:
    ok: bool
    filename: str
    file_type: str = "xlsx"
    sheet_names: tuple[str, ...] = ()
    text: str = ""
    preview: str = ""
    truncated: bool = False
    owner_message: str = ""

def extract_xlsx_text(
    file_bytes: bytes,
    filename: str,
) -> ExtractedWorkspaceSource:
    ...
```

Public function không ném raw `openpyxl` exception ra UI. Nó trả friendly result cho extension sai, workbook hỏng, workbook rỗng hoặc vượt giới hạn.

### Validation và safety limits

Khuyến nghị constants trong module:

- chỉ nhận extension `.xlsx` (case-insensitive);
- `.xls` trả unsupported result trước khi parse;
- từ chối bytes rỗng;
- max upload bytes: `10 * 1024 * 1024`;
- max sheets đọc: `12`;
- max worksheet rows duyệt: `1000` mỗi sheet;
- max non-empty cells: `20_000` toàn workbook;
- dừng tích lũy text khi chạm `WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES`;
- preview là `text[:WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT]`.

Giới hạn là guard MVP, không phải tuyên bố đã đọc toàn bộ workbook. Nếu bỏ bớt sheet/row/cell hoặc text bị cap, `truncated=True` và text/owner message phải nói rõ nội dung chỉ được đọc một phần.

Nên preflight `.xlsx` như ZIP bằng standard-library `zipfile` trước `openpyxl`: từ chối container lỗi và tổng uncompressed members quá lớn (khuyến nghị 50 MiB). Đây là guard chống workbook nén nhỏ nhưng bung quá lớn; không cần dependency mới.

Không ghi upload xuống `local_cases` hoặc temp path trong extractor. Dùng `io.BytesIO(file_bytes)` và:

```python
openpyxl.load_workbook(
    BytesIO(file_bytes),
    read_only=True,
    data_only=False,
    keep_links=False,
)
```

Luôn `close()` workbook trong `finally`.

### Text format

Output owner-readable, deterministic và có cell coordinates:

```text
File Excel: Ke_hoach_san_xuat.xlsx

Trang tính: Kế hoạch
A1=Mã lệnh | B1=Sản phẩm | C1=Số lượng
A2=MO-001 | B2=ABC-10 | C2=120

Trang tính: Ghi chú
A1=Cần xác nhận lịch giao
```

Rules:

- giữ thứ tự sheet và row trong workbook;
- bỏ cell `None` hoặc chuỗi chỉ có whitespace;
- mỗi value có prefix coordinate (`A1=...`) để không mất vị trí;
- normalize newline/control whitespace trong cell thành khoảng trắng;
- giữ Unicode Việt/Nhật;
- date/datetime dùng ISO-like text ổn định;
- không diễn giải bảng, không suy đoán header, không tạo chunk/RAG metadata.

### Formula behavior

Dùng `data_only=False`, do đó formula được giữ dưới dạng biểu thức như `C2==SUM(A2:B2)` theo format `coordinate=value`. `openpyxl` không tính lại formula và adapter không được tuyên bố giá trị đã được cập nhật.

Không dùng `data_only=True` làm mặc định vì workbook không có cached result có thể trả `None` và làm mất formula. Test phải document behavior này.

### Merged cells và các feature ngoài MVP

- Merged cells: chỉ ô neo/top-left thường có value; các ô còn lại rỗng và được bỏ qua.
- Hidden sheet/row/column: MVP đọc như dữ liệu thường; không suy đoán ý nghĩa visibility.
- Charts, images, comments, macros, external links và text boxes: không đọc.
- `.xlsm`, `.xls`, password-protected/encrypted workbooks: không support.
- Encoding: `.xlsx` là XML/ZIP và `openpyxl` xử lý Unicode; adapter vẫn phải cap theo UTF-8 bytes.

### Temporary hay notebook?

Mặc định ingest thành `TemporaryConversationSource` trước vì:

- đúng vị trí owner đang làm việc;
- nguồn mới tự bật theo quyết định Phase 2;
- tránh tự động làm bẩn sổ dài hạn;
- owner đã có nút “Thêm vào sổ tài liệu”.

Không tạo đồng thời cả temporary và notebook source. Không auto-promote. Nếu sau này có nút “Thêm thẳng vào sổ”, đó là flow explicit riêng và notebook source mới vẫn không auto-enable nếu owner chưa bật.

## 6. Owner UI copy

Copy đề xuất:

```text
Thêm file Excel .xlsx
Chọn file Excel cho cuộc trò chuyện này
Đọc và thêm vào nguồn tạm
Đã đọc nội dung Excel và thêm vào nguồn tạm của cuộc trò chuyện.
Nguồn Excel mới đã được bật cho cuộc trò chuyện này.
File .xls chưa được hỗ trợ. Vui lòng mở file bằng Excel và lưu lại dạng .xlsx.
Không thể đọc file Excel này. Vui lòng kiểm tra lại file hoặc thử file nhỏ hơn.
File Excel này không có ô dữ liệu nào có thể đọc.
File Excel lớn nên AIOS chỉ đọc một phần nội dung. Bạn có thể chia file nhỏ hơn nếu cần.
```

Không hiển thị raw exception, stack trace, ZIP member name hoặc path local.

Không dùng trong owner UI:

- RAG;
- vector;
- embedding;
- chunk;
- retrieval;
- citation;
- claim;
- provider router;
- Mermaid.

Không nói AIOS đã phân tích, đối chiếu, hiểu bảng hoặc dùng workbook để tạo câu trả lời. `Nguồn đang dùng` vẫn chỉ nghĩa là nguồn owner đã bật cho conversation.

## 7. Test plan

### `tests/test_workspace_chat_excel_ingest.py`

Tạo workbook trong memory bằng `openpyxl`; không dùng fixture thật hoặc dữ liệu nhạy cảm.

1. Một sheet đơn giản:
   - extract thành công;
   - có filename, sheet name, coordinates và values.
2. Nhiều sheet:
   - giữ thứ tự/tên sheet;
   - text của từng sheet tách rõ.
3. Cell rỗng:
   - bỏ `None` và whitespace-only;
   - không bỏ số `0` hoặc boolean `False`.
4. Unicode:
   - giữ tiếng Việt và tiếng Nhật.
5. Formula:
   - giữ formula text với `data_only=False`;
   - không tuyên bố đã tính formula.
6. Merged cells:
   - lấy value ô neo một lần;
   - không crash vì `MergedCell`.
7. Empty workbook:
   - trả friendly failure/empty result.
8. Invalid/corrupt `.xlsx`:
   - không leak raw exception;
   - trả owner message chuẩn.
9. `.xls`:
   - không gọi `openpyxl`;
   - trả đúng friendly unsupported message.
10. Extension khác và filename case:
    - `.XLSX` được nhận;
    - extension ngoài scope bị từ chối.
11. Limits:
    - upload quá lớn;
    - quá nhiều sheet/row/cell;
    - preview không quá 2.000 ký tự;
    - text không quá 200 KiB UTF-8;
    - truncation được báo rõ.
12. ZIP/container guard:
    - corrupt ZIP và uncompressed-size limit không làm crash.
13. Local-only:
    - không network, OCR, AI hoặc filesystem write.

### App/wiring tests

Thêm test cấu trúc hoặc callback-level đủ mạnh để chứng minh:

1. uploader key có conversation ID;
2. `.xlsx` thành công gọi đúng thứ tự:
   - `extract_xlsx_text(...)`;
   - `save_temporary_source(...)`;
   - `set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, source_id, True)`;
   - `safe_rerun()`;
3. extract lỗi không save, không enable, không rerun thành công giả;
4. `.xls` hiển thị copy thân thiện và không tạo source;
5. source mới có `source_type="xlsx"`, title/preview/text đúng result;
6. submit/rerun không ingest trùng ngoài ý muốn;
7. sidebar placement Phase 2B không regress;
8. promotion vẫn giữ temp source và không auto-enable notebook source mới.

### Architecture/safety tests

- mọi store path monkeypatch sang `tmp_path`;
- không ghi `local_cases` thật;
- `workspace_chat_excel.py` không import Streamlit, store, AI/RAG module hoặc `case_cockpit`;
- app/UI không import `case_cockpit`;
- forbidden owner UI copy vẫn absent;
- full test suite và CLI audit vẫn pass.

## 8. Risks / non-goals

### Risks và mitigation

| Risk | Mitigation |
|---|---|
| File lớn hoặc ZIP expansion làm chậm/mất RAM | Giới hạn upload, preflight ZIP, read-only workbook, cap sheet/row/cell/text |
| Sparse sheet khai báo dimension rất lớn | Giới hạn row duyệt và non-empty cell toàn workbook |
| Workbook nhiều sheet bị đọc thiếu | `truncated=True`, copy nói rõ chỉ đọc một phần |
| Formula cached value thiếu/cũ | Giữ formula với `data_only=False`; không recalculate |
| Merged cells gây duplicate/rỗng | Chỉ giữ non-empty anchor value |
| Unicode bị cắt giữa byte sequence | Cap UTF-8 bằng encode/slice/decode `errors="ignore"` |
| Upload bị ingest lại khi rerun | Form submit rõ ràng và widget key theo conversation |
| Raw exception/path lộ ra UI | Adapter map lỗi sang owner message cố định |
| Temporary JSONL phình lớn | Adapter cap trước `save_temporary_source()` |
| Owner hiểu nhầm ingest là phân tích | Copy chỉ nói “đã đọc nội dung” và “đã thêm nguồn”; không claim answer grounding |

### Non-goals Phase 2C

- `.xls` hoặc `.xlsm`;
- CSV;
- OCR;
- chart/image/comment/shape interpretation;
- formula calculation;
- semantic table detection hoặc nhiều table trong một sheet;
- hidden/filtered data semantics;
- cloud upload;
- AI thật;
- retrieval, answer grounding hoặc source-use records;
- trực tiếp thêm vào Case Cockpit;
- sửa Case Cockpit;
- dependency mới.

## 9. Gemini implementation prompt

```text
Bạn đang implement WORKSPACE_CHAT_PHASE2C_XLSX_INGEST_DESIGN_GATE trong repo:
D:\Sandbox\AIOS_habbit

Baseline bắt buộc trước khi sửa:
- branch: main
- HEAD: 9d47986
- origin/main: 9d47986
- worktree sạch

Chạy:
git branch --show-current
git rev-parse --short HEAD
git rev-parse --short origin/main
git status --short

Nếu worktree không sạch hoặc baseline lệch, STOP và báo:
FAIL_DIRTY_TREE_BEFORE_PHASE2C_IMPLEMENTATION

Đọc đầy đủ:
- docs/ux/WORKSPACE_CHAT_PHASE2C_XLSX_INGEST_DESIGN_GATE.md
- docs/ux/WORKSPACE_CHAT_PHASE2_RESEARCH_FIRST_DESIGN_AUDIT.md
- docs/ux/WORKSPACE_CHAT_PHASE2B_UI_DESIGN_GATE.md
- docs/ux/WORKSPACE_CHAT_PHASE2B_IMPLEMENTATION_AUDIT.md
- src/aios_habit/workspace_chat_models.py
- src/aios_habit/workspace_chat_store.py
- src/aios_habit/workspace_chat_ui.py
- src/aios_habit/workspace_chat_app.py
- tests/test_workspace_chat_sources_models.py
- tests/test_workspace_chat_sources_store.py
- tests/test_workspace_chat_source_selection_ui_copy.py
- tests/test_workspace_chat_source_selection_owner_flow.py

Mục tiêu:
1. Upload và extract local file .xlsx trong Workspace Chat.
2. Lưu kết quả thành TemporaryConversationSource.
3. Auto-enable nguồn mới trong conversation hiện tại.
4. Giữ cap preview 2.000 ký tự và text 200 KiB UTF-8.
5. .xls chỉ trả thông báo chuyển sang .xlsx.
6. Không AI, không answer grounding, không Case Cockpit.

Allowed files:
- src/aios_habit/workspace_chat_excel.py (new)
- src/aios_habit/workspace_chat_app.py
- tests/test_workspace_chat_excel_ingest.py (new)
- tests/test_workspace_chat_source_selection_owner_flow.py (chỉ wiring tests cần thiết)
- tests/test_workspace_chat_ui_copy.py hoặc tests/test_workspace_chat_source_selection_ui_copy.py (chỉ copy tests cần thiết)

Không sửa nếu chưa chứng minh blocker:
- src/aios_habit/workspace_chat_models.py
- src/aios_habit/workspace_chat_store.py
- src/aios_habit/workspace_chat_ui.py
- pyproject.toml hoặc dependency manifests
- mọi file ngoài allowed list

Tuyệt đối không:
- sửa/import src/aios_habit/case_cockpit.py;
- import case_ingest.py hoặc case_store.py;
- ghi trực tiếp local_cases từ extractor;
- thêm dependency;
- support .xls/.xlsm thật;
- OCR hoặc cloud call;
- nối AI thật;
- làm retrieval/answer grounding;
- stage, commit, push;
- tạo branch;
- reset, checkout, stash, clean hoặc update-index;
- sửa .ai hoặc local_cases.

Tạo adapter:
- src/aios_habit/workspace_chat_excel.py
- public API tương đương:
  extract_xlsx_text(file_bytes: bytes, filename: str) -> ExtractedWorkspaceSource
- dùng io.BytesIO và openpyxl đã có;
- load_workbook(read_only=True, data_only=False, keep_links=False);
- close workbook trong finally;
- không import Streamlit/store trong extractor;
- không ghi filesystem;
- không expose raw exception.

Behavior:
- chỉ .xlsx, case-insensitive;
- .xls trả:
  File .xls chưa được hỗ trợ. Vui lòng mở file bằng Excel và lưu lại dạng .xlsx.
- empty/corrupt/oversized trả friendly result;
- giữ tên sheet;
- mỗi non-empty cell có coordinate=value;
- bỏ None/whitespace-only nhưng giữ 0/False;
- giữ Unicode;
- formula giữ nguyên biểu thức, không recalculate;
- merged cell chỉ lấy anchor value;
- không đọc charts/images/comments/shapes/macros/external links;
- giới hạn 10 MiB upload, 50 MiB ZIP uncompressed, 12 sheets,
  1.000 rows/sheet, 20.000 non-empty cells/workbook;
- preview <= WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT;
- text UTF-8 <= WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES;
- báo truncated nếu chạm giới hạn.

App flow bắt buộc:
extract thành công
-> tạo TemporaryConversationSource(source_type="xlsx")
-> save_temporary_source(...)
-> set_source_enabled(
     active_conversation.id,
     SOURCE_SCOPE_TEMPORARY,
     temporary_source.id,
     True,
   )
-> safe_rerun()

Không rerun giữa save và enable.
Không auto-promote.
Không auto-enable notebook source mới.
Uploader/form ở main area cạnh paste-text flow.
Uploader key phải có active conversation ID.
Source summary/lists vẫn ở with st.sidebar.

Owner copy:
- Thêm file Excel .xlsx
- Đã đọc nội dung Excel và thêm vào nguồn tạm của cuộc trò chuyện.
- File .xls chưa được hỗ trợ. Vui lòng mở file bằng Excel và lưu lại dạng .xlsx.
- Không thể đọc file Excel này. Vui lòng kiểm tra lại file hoặc thử file nhỏ hơn.

Không dùng trong owner UI:
RAG, vector, embedding, chunk, retrieval, citation, claim,
provider router, Mermaid.
Không claim AIOS đã phân tích/đối chiếu/trích dẫn hoặc dùng file để trả lời.

Tests bắt buộc:
- tests/test_workspace_chat_excel_ingest.py:
  one sheet, multi-sheet, empty cells, 0/False, Unicode, formula,
  merged cells, empty workbook, corrupt xlsx, .xls unsupported,
  uppercase extension, upload/ZIP/sheet/row/cell/text/preview limits,
  no filesystem/network/AI side effects.
- app wiring:
  extract -> save temp -> enable temporary -> rerun;
  failure does not save/enable;
  uploader key conversation-scoped;
  no duplicate ingest from passive rerun.
- architecture:
  no case_cockpit import;
  no real local_cases writes;
  Phase 2B sidebar/source-selection tests remain green.

Focused tests:
py -3 -m pytest tests/test_workspace_chat_excel_ingest.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_owner_flow.py tests/test_workspace_chat_architecture_boundary.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_sources_models.py tests/test_workspace_chat_sources_store.py -v

Full tests:
py -3 -m pytest -q

CLI audit:
py -3 -m aios_habit.cli audit

Final checks:
git status --short
git diff --check
git diff --name-only
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md

Expected changed files only:
- src/aios_habit/workspace_chat_excel.py
- src/aios_habit/workspace_chat_app.py
- tests/test_workspace_chat_excel_ingest.py
- optional exact allowed test files actually needed

Final response:
FINAL_STATUS: PASS_PHASE2C_IMPLEMENTED | FAIL_PHASE2C
FILES_CHANGED:
- ...
FOCUSED_TESTS: <result>
FULL_TESTS: <result>
CLI_AUDIT: <result>
SCOPE_CHECK:
- .xlsx only: YES
- .xls parsing: NO
- AI thật: NO
- Answer grounding: NO
- Case Cockpit touched/imported: NO
- local_cases touched: NO
- dependency mới: NO
GIT_ACTIONS:
- staged: NO
- committed: NO
- pushed: NO
WARNINGS:
- ...
```

## 10. Final recommendation

Cho Gemini implement Phase 2C theo prompt ở mục 9.

Không cần owner quyết định thêm. Các quyết định đã đủ:

- `.xlsx` only;
- `.xls` chỉ có conversion message;
- temporary-first và auto-enable;
- explicit promotion vào sổ;
- cap 2.000 ký tự preview / 200 KiB text;
- local `openpyxl`, không dependency mới;
- formula giữ biểu thức, không recalculate;
- giới hạn MVP trung thực cho workbook lớn.

Sau implementation, Codex nên audit riêng:

1. cap được áp dụng trước khi save nguồn tạm;
2. không có filesystem/network side effect trong extractor;
3. save → enable → rerun đúng thứ tự;
4. UI không overclaim “đã phân tích”;
5. không import hoặc sửa Case Cockpit.

Final status: `PASS_READY_FOR_GEMINI_PHASE2C_IMPLEMENTATION`.
