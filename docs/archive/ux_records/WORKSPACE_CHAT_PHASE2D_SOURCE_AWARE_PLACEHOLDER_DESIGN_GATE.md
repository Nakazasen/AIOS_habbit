# WORKSPACE_CHAT_PHASE2D_SOURCE_AWARE_PLACEHOLDER_DESIGN_GATE

## 1. Kết luận ngắn

Final status: `PASS_READY_FOR_GEMINI_PHASE2D_IMPLEMENTATION`.

Phase 2D nên thêm một helper thuần dữ liệu để tạo bản xem trước câu trả lời có nhận biết đúng các nguồn đang bật, rồi nối helper này vào luồng gửi câu hỏi hiện có. Đây vẫn là placeholder local-only: không gọi AI, không phân tích nội dung, không đối chiếu, không tạo citation và không tuyên bố kết luận.

Không cần model/store mới. Có thể lưu nội dung placeholder như một `ChatMessage` assistant hiện có để lịch sử hội thoại ổn định, nhưng không lưu source snapshot hoặc source-use record riêng trong Phase 2D.

## 2. Baseline

Baseline trước khi tạo report:

- Repo: `D:\Sandbox\AIOS_habbit`
- Branch: `main`
- HEAD: `d562bb5`
- `origin/main`: `d562bb5`
- `HEAD == origin/main`: có
- Worktree: sạch
- Commit gần nhất: `d562bb5 Implement Workspace Chat Phase 2C XLSX ingest`
- Full pytest gần nhất theo yêu cầu: `608 passed`
- CLI audit gần nhất theo yêu cầu: `PASS`

Không có code/test nào được sửa. Không stage, commit, push, tạo branch hoặc thay đổi Git state.

## 3. Existing Phase 2A/2B/2C summary

### Phase 2A

Backend hiện có đủ dữ liệu cần dùng:

- `NotebookSource` giữ `title`, `source_type`, `content_preview`, `content_text`.
- `TemporaryConversationSource` giữ cùng phần nội dung cần thiết và bị giới hạn theo conversation.
- `ConversationSourceSelection` giữ `conversation_id`, `source_scope`, `source_id`, `enabled`.
- Text nguồn được giới hạn ở `200 KiB/source`; preview ở tối đa `2.000` ký tự.

Store hiện có:

- `load_notebook_sources(notebook_id)`
- `load_temporary_sources(conversation_id)`
- `load_enabled_sources_for_conversation(conversation_id)`

`load_enabled_sources_for_conversation()` chỉ trả selection, không trả source object. App phải resolve selection theo cặp `(source_scope, source_id)` và bỏ qua selection mồ côi một cách an toàn.

### Phase 2B

Owner đã có UI bật/tắt riêng:

- `Nguồn trong sổ`
- `Nguồn tạm trong cuộc trò chuyện`

Notebook source không tự bật. Temporary source mới được tự bật trong conversation hiện tại. Việc promote vẫn là hành động tường minh.

### Phase 2C

`.xlsx` đã được đọc local một lần và lưu thành `TemporaryConversationSource(source_type="xlsx")`. Phase 2D chỉ đọc `content_preview`/`content_text` đã lưu; không gọi lại `extract_xlsx_text()`, không mở lại workbook và không đọc file upload lần hai.

### Khoảng trống hiện tại

Luồng chat hiện:

- lấy toàn bộ temporary sources thay vì chỉ nguồn đang bật;
- bỏ qua notebook sources đang bật;
- lưu placeholder assistant có nội dung chung;
- panel phải dùng các nhãn/copy cũ dễ bị hiểu là bằng chứng hoặc kết quả phân tích.

Phase 2D chỉ sửa khoảng trống này, không mở rộng sang AI thật.

## 4. Phase 2D scope

### Files nên thêm/sửa

Allowed implementation files:

- Thêm `src/aios_habit/workspace_chat_answer_preview.py`
- Sửa `src/aios_habit/workspace_chat_app.py`
- Sửa tối thiểu `src/aios_habit/workspace_chat_ui.py` nếu cần helper render/copy
- Thêm `tests/test_workspace_chat_answer_preview.py`
- Sửa tối thiểu `tests/test_workspace_chat_source_selection_owner_flow.py`
- Sửa tối thiểu `tests/test_workspace_chat_source_selection_ui_copy.py`

Không cần sửa:

- `src/aios_habit/workspace_chat_models.py`
- `src/aios_habit/workspace_chat_store.py`
- `src/aios_habit/workspace_chat_excel.py`
- tests Phase 2C, trừ khi một regression thực tế bắt buộc phải điều chỉnh

### Forbidden files và phạm vi

Không sửa hoặc import:

- `case_cockpit.py`
- Case Cockpit, case ingest hoặc case store
- `.ai`
- `local_cases`
- dependency manifest
- file ngoài exact Phase 2D scope

Không thêm AI/provider/router/cloud/network, answer grounding thật, citation thật, RAG/vector/embedding/chunk/retrieval framework hoặc dependency mới.

## 5. Placeholder answer design

### Module và kiểu dữ liệu

Ưu tiên module nhỏ, thuần dữ liệu:

```python
@dataclass(frozen=True)
class WorkspaceTrialSourcePreview:
    source_id: str
    source_scope: str
    source_type: str
    title: str
    preview: str


@dataclass(frozen=True)
class WorkspaceTrialAnswerPreview:
    question: str
    answer_text: str
    enabled_sources: tuple[WorkspaceTrialSourcePreview, ...]


def build_trial_answer_preview(
    question: str,
    enabled_sources: list[NotebookSource | TemporaryConversationSource],
) -> WorkspaceTrialAnswerPreview:
    ...
```

Nếu cần giữ scope khi hai loại source có thể trùng ID, app nên resolve thành một input nội bộ có cả `source_scope` trước khi gọi builder. Không đổi model persisted chỉ để phục vụ placeholder.

Helper phải:

- normalize câu hỏi để hiển thị, nhưng không diễn giải hoặc trả lời câu hỏi;
- giữ thứ tự ổn định: thứ tự source đang hiển thị trong sổ trước, nguồn tạm sau;
- chỉ nhận source đã resolve và đang bật;
- dùng `content_preview`; nếu preview rỗng thì tạo đoạn xem trước ngắn từ `content_text`;
- giới hạn đoạn xem trước hiển thị, đề xuất tối đa `300` ký tự/source;
- không đưa toàn bộ `content_text` tối đa 200 KiB vào UI;
- không gọi store, Streamlit, filesystem, Excel parser, network hoặc AI;
- không mutate source;
- không sinh citation marker, kết luận hoặc câu chữ ngụ ý đã phân tích.

### Cách lấy đúng nguồn đang bật

Trong app:

1. Gọi `load_enabled_sources_for_conversation(active_conversation.id)`.
2. Lập lookup từ `load_notebook_sources(active_nb_id)` và `load_temporary_sources(active_conversation.id)`.
3. Với mỗi enabled selection:
   - scope `notebook`: chỉ resolve trong notebook hiện tại;
   - scope `temporary`: chỉ resolve trong conversation hiện tại.
4. Bỏ qua selection không còn source tương ứng; không crash và không hiển thị ID nội bộ.
5. Truyền danh sách đã resolve vào `build_trial_answer_preview(...)`.

Không dùng `WorkspaceConversation.selected_source_ids`, vì selection source chính thức của Phase 2B là `ConversationSourceSelection`.

### Hiển thị trong UI

Sau khi owner gửi câu hỏi:

- lưu user message như hiện tại;
- build preview từ snapshot nguồn đang bật tại thời điểm submit;
- lưu `preview.answer_text` thành một assistant `ChatMessage`;
- rerun và render bằng bubble assistant hiện có;
- panel bên phải dùng nhãn trung tính, không dùng nhãn hàm ý “bằng chứng”, “đối chiếu” hoặc “kết luận”.

Nội dung assistant được lưu để lịch sử không biến đổi khi owner bật/tắt nguồn sau đó. Không lưu thêm source snapshot riêng ở Phase 2D. Danh sách title/preview đã nằm trong nội dung placeholder tại thời điểm gửi, đủ cho gate thử nghiệm này.

Không cập nhật `used_in_last_answer` hoặc `last_used_at`: chưa có answer thật, nên đánh dấu “used” sẽ overclaim.

### Trường hợp không có nguồn bật

Vẫn tạo placeholder, nói rõ chưa có nguồn đang bật. Không tự bật source và không lấy source đang tắt.

### Trường hợp source text dài

- Persisted source vẫn tuân theo cap hiện có: preview `2.000` ký tự, text `200 KiB/source`.
- UI chỉ render title, type thân thiện và preview tối đa khoảng `300` ký tự/source.
- Nên giới hạn số source render trong một placeholder, đề xuất `20`; nếu vượt thì ghi “Còn N nguồn đang bật chưa hiển thị trong bản xem trước”.
- Không nối toàn bộ source text vào `ChatMessage`.
- Việc dựng context thật, tổng token budget và ưu tiên/cắt context là non-goal của Phase 2D.

## 6. Owner UI copy

Copy đề xuất:

```text
Bản thử nghiệm

AIOS chưa nối AI thật ở bước này.

Câu hỏi hiện tại:
<câu hỏi của owner>

Nguồn đang bật cho cuộc trò chuyện:
- <Tiêu đề nguồn> · <loại nguồn thân thiện>
  Đoạn xem trước sẽ dùng khi nối AI ở bước sau: <preview ngắn>

Đây chưa phải câu trả lời phân tích cuối cùng.
```

Khi không có nguồn:

```text
Bản thử nghiệm

AIOS chưa nối AI thật ở bước này.

Câu hỏi hiện tại:
<câu hỏi của owner>

Chưa có nguồn nào đang bật cho cuộc trò chuyện này.

Đây chưa phải câu trả lời phân tích cuối cùng.
```

Nhãn panel đề xuất:

- `Bản xem trước câu trả lời`
- `Nguồn đang bật cho cuộc trò chuyện`
- `Đoạn xem trước sẽ dùng ở bước sau`
- `Điều owner cần kiểm tra`

Copy bắt buộc xuất hiện:

- `Bản thử nghiệm`
- `AIOS chưa nối AI thật ở bước này.`
- `Nguồn đang bật cho cuộc trò chuyện`
- `Đây chưa phải câu trả lời phân tích cuối cùng.`

Cấm trong owner UI copy Phase 2D:

- `RAG`
- `vector`
- `embedding`
- `chunk`
- `retrieval`
- `citation`
- `claim`
- `provider router`
- `Mermaid`
- `Nguồn AIOS đã dùng`
- `Nguồn chứng minh`
- `AIOS đã phân tích`
- `AIOS đã đối chiếu`
- `AIOS đã trích dẫn`
- `Kết luận từ tài liệu`

Ngoài danh sách literal trên, cũng tránh mọi biến thể có nghĩa AIOS đã đọc hiểu, xác minh, chứng minh hoặc kết luận. `Nguồn đang bật` chỉ là lựa chọn của owner, không phải citation và không phải bằng chứng.

## 7. Test plan

### Unit tests cho builder

1. Không có nguồn bật:
   - có câu hỏi;
   - có `Bản thử nghiệm`;
   - nói chưa có nguồn đang bật;
   - nói chưa nối AI thật;
   - nói đây chưa phải câu trả lời phân tích cuối cùng.
2. Notebook source:
   - hiện title, type thân thiện và preview ngắn;
   - không hiện ID/scope enum nội bộ.
3. Temporary pasted text:
   - hiện title và preview ngắn;
   - không đưa toàn bộ text dài vào output.
4. Temporary `.xlsx`:
   - hiện title/type Excel và preview đã lưu;
   - spy/monkeypatch bảo đảm không gọi `extract_xlsx_text()` hoặc `openpyxl`.
5. Preview rỗng:
   - fallback từ `content_text` được normalize và cap an toàn.
6. Unicode:
   - giữ tiếng Việt/Nhật đúng UTF-8.
7. Nguồn dài/nhiều:
   - cap preview/source;
   - cap số source hiển thị;
   - có thông báo số nguồn còn lại.
8. Không overclaim:
   - output không chứa toàn bộ cụm cấm ở mục 6, kiểm tra case-insensitive.
9. Pure/local-only:
   - không import Streamlit/store/Excel/AI/network trong module helper;
   - không filesystem write hoặc network call.

### App/wiring tests

10. Question + enabled notebook/temporary selections tạo đúng preview.
11. Source tồn tại nhưng disabled không xuất hiện.
12. Selection mồ côi bị bỏ qua, không crash và không leak ID.
13. Selection khác conversation/notebook không xuất hiện.
14. `.xlsx` dùng nội dung đã persist, không parse lại file.
15. Thứ tự submit:
    - save user message;
    - load/resolve enabled sources;
    - build preview;
    - save assistant placeholder;
    - `safe_rerun()`.
16. Passive rerun không tạo thêm placeholder.
17. Một submit chỉ lưu một user message và một assistant placeholder.
18. Không sửa `used_in_last_answer`/`last_used_at`.
19. Không lưu model/source snapshot mới và không ghi thật vào `local_cases` trong tests; monkeypatch mọi store path về `tmp_path`.
20. Không import hoặc sửa `case_cockpit.py`.
21. Owner-copy scan khóa các cụm cấm trong phần UI Phase 2D.
22. Existing focused tests, full `pytest -q` và `py -3 -m aios_habit.cli audit` đều pass.

Ưu tiên callback/helper runtime tests hơn source-string position inspection. Source inspection chỉ nên khóa architecture boundary hoặc forbidden imports.

## 8. Risks / non-goals

### Risks

- Selection mồ côi có thể tồn tại sau khi source bị xóa: bỏ qua an toàn.
- Hai scope có thể có cùng source ID: luôn resolve bằng `(scope, id)`.
- Bật/tắt nguồn sau khi gửi có thể khác snapshot lúc gửi: nội dung placeholder đã lưu phải phản ánh thời điểm submit.
- Source preview có thể chứa dữ liệu nhạy cảm: chỉ hiển thị ngắn, không log và không gửi ra ngoài máy.
- Source text dài có thể làm UI/message phình lớn: không nối full text vào placeholder.
- Copy panel Phase 1 hiện có chỗ overclaim: Phase 2D phải thay copy liên quan trực tiếp đến answer preview, không mở rộng thành refactor Case Cockpit.

### Non-goals

- AI inference hoặc provider integration.
- Answer grounding, semantic analysis, fact checking hoặc source ranking.
- Citation/source-use provenance thật.
- Context/token packing thật.
- RAG/vector/embedding/chunk/retrieval.
- Re-parse `.xlsx`.
- Model/store migration hoặc `AnswerSourceUse`.
- Cloud/network.
- Case Cockpit.

## 9. Gemini implementation prompt

```text
Bạn là Gemini. Hãy implement WORKSPACE_CHAT_PHASE2D_SOURCE_AWARE_PLACEHOLDER theo design gate:
docs/ux/WORKSPACE_CHAT_PHASE2D_SOURCE_AWARE_PLACEHOLDER_DESIGN_GATE.md

Baseline bắt buộc:
- Repo D:\Sandbox\AIOS_habbit
- Branch main
- HEAD == origin/main == d562bb5
- Worktree phải sạch trước khi bắt đầu.
- Nếu baseline sai hoặc tree không sạch: STOP, báo lỗi, không sửa gì.

Allowed files:
- ADD src/aios_habit/workspace_chat_answer_preview.py
- MODIFY src/aios_habit/workspace_chat_app.py
- MODIFY tối thiểu src/aios_habit/workspace_chat_ui.py nếu cần render/copy
- ADD tests/test_workspace_chat_answer_preview.py
- MODIFY tối thiểu tests/test_workspace_chat_source_selection_owner_flow.py
- MODIFY tối thiểu tests/test_workspace_chat_source_selection_ui_copy.py

Không sửa models/store/excel hoặc tests Phase 2C trừ khi có blocker thực tế; nếu có, STOP và báo owner trước.

Forbidden:
- Không sửa/import case_cockpit.py, Case Cockpit, case_ingest hoặc case_store.
- Không sửa .ai hoặc local_cases.
- Không thêm dependency.
- Không stage, commit, push, tạo branch, reset, checkout, stash, clean hoặc update-index.
- Không nối AI thật, provider/router/cloud/network.
- Không tạo answer grounding/citation thật.
- Không tạo RAG/vector/embedding/chunk/retrieval framework.
- Không parse lại .xlsx.

Implementation:
1. Tạo helper thuần dữ liệu build_trial_answer_preview(...), cùng immutable output dataclasses.
2. Dùng đúng enabled selections từ load_enabled_sources_for_conversation().
3. Resolve selection theo (source_scope, source_id) vào notebook hiện tại hoặc conversation hiện tại; bỏ qua selection mồ côi.
4. Hiện câu hỏi, nguồn đang bật, title/type thân thiện và preview ngắn.
5. Preview tối đa 300 ký tự/source, tối đa 20 nguồn hiển thị; không nối full content_text vào message.
6. Với xlsx, dùng content_preview/content_text đã persist; không gọi extractor/openpyxl.
7. Lưu placeholder text thành assistant ChatMessage hiện có để lịch sử ổn định.
8. Không tạo model/store/source snapshot mới.
9. Không cập nhật used_in_last_answer hoặc last_used_at.
10. Passive rerun không ingest hoặc tạo duplicate message.

Exact required owner copy:
- Bản thử nghiệm
- AIOS chưa nối AI thật ở bước này.
- Nguồn đang bật cho cuộc trò chuyện
- Đây chưa phải câu trả lời phân tích cuối cùng.

Forbidden owner copy, case-insensitive:
- RAG
- vector
- embedding
- chunk
- retrieval
- citation
- claim
- provider router
- Mermaid
- Nguồn AIOS đã dùng
- Nguồn chứng minh
- AIOS đã phân tích
- AIOS đã đối chiếu
- AIOS đã trích dẫn
- Kết luận từ tài liệu

Exact tests cần có:
- no enabled sources;
- enabled notebook source;
- enabled temporary pasted-text source;
- enabled xlsx source without re-parsing;
- disabled source excluded;
- orphan/cross-conversation selection excluded;
- blank preview fallback and cap;
- Unicode preserved;
- long/many-source caps;
- forbidden-copy scan;
- no AI/cloud/network/filesystem side effect;
- app submit flow and order;
- no duplicate on passive rerun;
- no fake source-use metadata update;
- no real local_cases writes;
- no case_cockpit import.

Verification:
- Chạy focused Phase 2D và source-selection tests.
- Chạy py -3 -m pytest -q.
- Chạy py -3 -m aios_habit.cli audit.
- Chạy git diff --check.
- Báo exact git status/diff files và kết quả test.
- Không stage/commit/push.
```

## 10. Final recommendation

Gemini có thể code Phase 2D sau khi design report này được owner chấp nhận.

Không cần owner quyết định thêm để bắt đầu. Các quyết định đã được khóa trong gate:

- dùng model/store hiện có;
- lưu placeholder trong assistant `ChatMessage`;
- không lưu source snapshot/source-use model riêng;
- chỉ hiển thị preview ngắn;
- không đánh dấu nguồn là “đã dùng”;
- không có AI/citation/grounding thật.

Final status: `PASS_READY_FOR_GEMINI_PHASE2D_IMPLEMENTATION`.
