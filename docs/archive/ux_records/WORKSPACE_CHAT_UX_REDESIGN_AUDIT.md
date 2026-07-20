# WORKSPACE_CHAT_UX_REDESIGN_AUDIT

## 1. Kết luận ngắn

- Không nên sửa vặt UI hiện tại. UI đang gom quá nhiều luồng vào `case_cockpit.py`, khiến owner phải hiểu "Hồ sơ", "Sổ tri thức", prompt, bridge, map, provider và audit trước khi biết nên bắt đầu ở đâu.
- Nên thiết kế lại từ gốc theo mô hình: `Sổ tài liệu -> nhiều cuộc trò chuyện trong sổ -> nguồn tạm trong cuộc trò chuyện -> lưu vào hồ sơ -> xem vì sao AIOS kết luận`.
- Màn hình mặc định khi mở app nên là `Sổ tài liệu của tôi`, hoặc sổ owner mở gần nhất. Không nên mở thẳng vào Case Cockpit, audit, prompt/debug, hay bản đồ kỹ thuật.
- Kiến trúc triển khai khuyến nghị: **Option B - thêm lớp workspace chat mới song song với legacy, rồi chuyển dần owner flow sang UI mới**.
- Không code trong audit này. Chỉ tạo report trong `docs/ux`.

## 2. Baseline repo status

- Repo: `D:\Sandbox\AIOS_habbit`
- Branch: `main`
- Remote: `https://github.com/Nakazasen/AIOS_habbit`
- HEAD: `0f43d9d`
- Origin/main: `0f43d9d`
- `git status --short`: không có file thay đổi; có warning `could not open directory '.codex/': Permission denied`.
- `git status --short --ignored`: chỉ thấy file/thư mục ignored như `.pytest_cache/`, `.venv/`, `local_cases/`, `local_runs/`, `API Key.txt`, `src/aios_habit.egg-info/`, `__pycache__/`.
- 20 commit gần nhất bắt đầu từ:
  - `0f43d9d feat(visual-map): commit visual_map_ui.py helper module`
  - `2bda53d feat(visual-map): implement table-first visual map UI with safe mermaid preview`
  - `197d0b2 Study Visual Map UI reference patterns`
  - `5ad3c25 Document owner retrial on same case`
  - `5da6f74 Fix owner trial pain points`
  - `161d9c3 Document one real case owner trial`
  - `b8a3af8 Audit Visual Knowledge Map MVP core`
- File đã đọc chính: `README.md`, `ROADMAP.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `AGENT_RULES.md`, `src/aios_habit/case_cockpit.py`, `workspace_models.py`, `case_models.py`, `case_store.py`, `source_ingest.py`, `notebook_qa.py`, `ai_router.py`, `provider_catalog.py`, `visual_map_ui.py`, `strong_answer_ui.py`, `ide_handoff_bridge.py`, các test UI liên quan.
- Xác nhận: chỉ tạo tài liệu audit/thiết kế trong `docs/ux`; không sửa source code, không sửa tests, không commit.

## 3. UI hiện tại đang hỏng ở đâu

| Vấn đề | Bằng chứng trong repo | Ảnh hưởng owner | Mức độ |
|---|---|---|---|
| App vẫn tự giới thiệu là Case Cockpit | `README.md` nói launch `AIOS Case Cockpit`; `case_cockpit.py` dùng sidebar title `AIOS Case Cockpit` | Owner nghĩ đây là công cụ xử lý case, không phải nơi mở sổ tài liệu và chat | Cao |
| Màn hình chính chia theo kỹ thuật nội bộ | `case_cockpit.py` có Quick Intake, Hồ sơ, Prompt Pack, IDE handoff, Visual Map, Audit, Learning, Notebook | Owner phải hiểu cấu trúc sản phẩm trước khi làm việc thật | Cao |
| Một file UI quá lớn | `case_cockpit.py` chứa nhiều trang, provider panel, NotebookLM bridge, map, MOM pilot | Mọi cải tiến sau dễ thành vá chắp vá | Cao |
| Thiếu khái niệm cuộc trò chuyện trong sổ | `workspace_models.py` có Workspace và KnowledgeNotebook; `notebook_qa.py` chỉ lưu question/answer history theo notebook | Không hỗ trợ rõ nhiều chat riêng trong cùng một sổ | Cao |
| Thiếu nguồn tạm theo cuộc trò chuyện | `source_ingest.py` lưu source vào notebook; `case_store.py` lưu evidence vào case | Log/file dán trong chat không có vòng đời "nguồn tạm dùng trong cuộc trò chuyện này" | Cao |
| Có thuật ngữ kỹ thuật trong owner UI | `case_cockpit.py` hiện label như Prompt, Mermaid, Node, Edge, Provider, Model, local_only, chunk xuất hiện ở nhiều nơi | Owner không kỹ thuật dễ mất hướng | Cao |
| Notebook và Case bị tách như hai khu vực khác nhau | UI có `Sổ tri thức` trong Settings/Audit tab, còn `Hồ sơ sự việc` là khu riêng | Owner phải tự hiểu khi nào dùng sổ, khi nào tạo hồ sơ | Trung bình-cao |
| Excel được hỗ trợ, nhưng không phải như nguồn chat tự nhiên | `case_ingest.py`, `source_ingest.py`, Quick Intake và Add Evidence có `.xlsx/.xls` | Có năng lực đọc Excel, nhưng UX chưa đặt nó vào flow "thêm nguồn khi đang hỏi" | Trung bình |
| Kiểm chứng kết luận đã có lõi, nhưng UI gọi bằng thuật ngữ graph | `visual_map_ui.py`, `visual_map_models.py`, `visual_map_export.py` | Nên biến thành "Xem vì sao AIOS kết luận" thay vì "node/edge/Mermaid" | Trung bình |

Kết luận: sản phẩm có nhiều module đúng hướng, nhưng không có một "đường ray owner" rõ ràng. Owner mở app chưa thấy ngay sổ nào, chat ở đâu, nguồn nào đang dùng, và kết quả lưu vào đâu.

## 4. Bảng phân loại file hiện tại

| File/module | Vai trò hiện tại | Phân loại khuyến nghị | Owner thấy? | Dùng lại cho UI mới | Rủi ro nếu sửa trực tiếp | Ghi chú cho Gemini implementation |
|---|---|---|---|---|---|---|
| `src/aios_habit/case_cockpit.py` | Streamlit app chính, chứa gần như mọi màn hình | VIẾT LẠI UI | Có, nhưng qua shell mới | Chỉ mượn logic gọi helper | Rất cao, dễ vỡ nhiều luồng | Không nhồi thêm vào file này; tạo shell mới rồi gọi service/helper |
| `src/aios_habit/visual_map_ui.py` | Helper table-first cho Visual Map | GIỮ NHƯNG ẨN KHỎI OWNER | Không trực tiếp | Có, dùng cho màn "Xem vì sao..." | Trung bình | Đổi label owner, giữ payload kỹ thuật phía sau |
| `src/aios_habit/ide_handoff_bridge.py` | Full-bundle handoff qua IDE/Antigravity | ĐƯA VÀO LEGACY / ADVANCED | Không mặc định | Có cho chế độ nâng cao | Trung bình | Owner flow mới chỉ hiển thị "Hỏi bằng model mạnh" nếu cần |
| `src/aios_habit/strong_answer_ui.py` | Chuẩn bị evidence pack và lưu câu trả lời AI mạnh | GIỮ LẠI LÀM LÕI | Không trực tiếp | Có | Thấp-trung bình | Bọc thành action "Hỏi tiếp bằng nguồn đã chọn" |
| `src/aios_habit/case_models.py` | Case và EvidenceItem | GIỮ LẠI LÀM LÕI | Không | Có | Trung bình | Cần thêm model Conversation và TemporarySource ở phase sau |
| `src/aios_habit/case_store.py` | Lưu case/evidence local JSONL | GIỮ LẠI LÀM LÕI | Không | Có | Trung bình | Không dùng làm store cho mọi loại nguồn tạm; thêm store riêng |
| `src/aios_habit/learning_models.py` | Bài học sau case | GIỮ NHƯNG ẨN KHỎI OWNER | Không mặc định | Có | Thấp | Chỉ hiện sau khi lưu hồ sơ/kết thúc xử lý |
| `src/aios_habit/visual_map_models.py` | Schema graph evidence-grounded | GIỮ LẠI LÀM LÕI | Không | Có | Thấp | Dùng làm lõi kiểm chứng, không lộ từ "node/edge/claim" |
| `src/aios_habit/visual_map_builder.py` | Dựng graph từ case/evidence/answer | GIỮ LẠI LÀM LÕI | Không | Có | Thấp | Nguồn cho màn "vì sao kết luận" |
| `src/aios_habit/visual_map_export.py` | Export local/safe graph | GIỮ NHƯNG ẨN KHỎI OWNER | Không | Có | Thấp | Owner chỉ thấy "Tải bản kiểm chứng an toàn" |
| `src/aios_habit/workspace_models.py` | Workspace và KnowledgeNotebook | GIỮ LẠI LÀM LÕI | Có qua UI sổ | Có | Trung bình | Đổi wording từ Workspace sang "Không gian" hoặc ẩn bớt |
| `src/aios_habit/source_ingest.py` | Nạp tài liệu vào sổ | GIỮ LẠI LÀM LÕI | Có | Có | Trung bình | Cần hỗ trợ thêm nguồn tạm trong conversation |
| `src/aios_habit/notebook_qa.py` | Hỏi đáp trong notebook, lưu history đơn giản | VIẾT LẠI/BAO LẠI | Có gián tiếp | Có một phần | Trung bình-cao | Cần Conversation model; history theo notebook là chưa đủ |
| `src/aios_habit/ai_router.py` | Chọn provider/model an toàn | CẦN ĐỒNG BỘ VỚI translation_app | Không trực tiếp | Có | Trung bình | UI mới chỉ gọi qua "Chọn model AI" |
| `src/aios_habit/provider_catalog.py` | Catalog provider AIOS | CẦN ĐỒNG BỘ VỚI translation_app | Có trong cài đặt | Có | Trung bình | Không bịa model; lấy từ catalog thật |
| `tests/test_case_cockpit_ui_copy.py` | Test copy UI hiện tại | ĐƯA VÀO LEGACY / ADVANCED | Không | Có tham khảo | Thấp | Sau UI mới cần test copy owner mới |
| `tests/test_notebook_in_app_qa.py` | Test Q&A notebook | GIỮ LẠI LÀM LÕI | Không | Có | Thấp | Bổ sung test conversation scoped source |
| `tests/test_visual_map_ui.py` | Test helper map UI | GIỮ NHƯNG ẨN KHỎI OWNER | Không | Có | Thấp | Rename owner copy trong test mới |
| `README.md`, `ROADMAP.md`, `CHANGELOG.md` | Định hướng sản phẩm | GIỮ LẠI LÀM LÕI | Không | Có | Thấp | Sau implementation cập nhật naming khỏi Case Cockpit |

## 5. Bài học từ sản phẩm tương tự

### NotebookLM

- Nguồn tham khảo: Google NotebookLM Help, `https://support.google.com/notebooklm/`.
- Bài học phù hợp: notebook là đơn vị làm việc dễ hiểu; user thêm source vào notebook, hỏi trong phạm vi source, và xem câu trả lời có nguồn chứng minh.
- Không copy: không biến AIOS thành bản sao NotebookLM. AIOS cần nhiều cuộc trò chuyện trong một sổ, nguồn tạm trong từng cuộc trò chuyện, lưu kết quả thành hồ sơ, local-first cho dữ liệu công việc.

### Open WebUI

- Nguồn tham khảo: Open WebUI docs, `https://docs.openwebui.com/`.
- Bài học phù hợp: có khái niệm knowledge/workspace và chat nhiều lượt với model; có quản lý model/backend.
- Điểm không phù hợp owner non-tech: nhiều cấu hình model/backend có thể gây quá tải nếu đưa ra màn chính.

### AnythingLLM

- Nguồn tham khảo: AnythingLLM docs, `https://docs.anythingllm.com/`.
- Bài học rất phù hợp: phân biệt tài liệu gắn vào thread tạm thời với tài liệu embed vào workspace lâu dài. Đây gần đúng với `Nguồn tạm trong cuộc trò chuyện` và `Thêm vào sổ tài liệu`.
- Khuyến nghị cho AIOS: dùng cùng nguyên tắc vòng đời, nhưng wording owner là "Chỉ dùng trong cuộc trò chuyện này" và "Thêm vào sổ tài liệu".

### Dify

- Nguồn tham khảo: Dify docs, `https://docs.dify.ai/`.
- Bài học phù hợp: tách app, knowledge base, workflow, model provider; giúp kiến trúc sạch.
- Điểm không phù hợp owner: nếu lộ quá nhiều khái niệm app/workflow/dataset/provider, owner sẽ thấy như công cụ builder chứ không phải đồng nghiệp AI.

### RAGFlow

- Nguồn tham khảo: RAGFlow GitHub, `https://github.com/infiniflow/ragflow`.
- Bài học phù hợp: dataset-backed Q&A, parsing tài liệu, trích nguồn, và chat dựa trên tài liệu.
- Điểm cần tránh: không dùng thuật ngữ RAG/dataset/chunk trong UI owner.

### Open Notebook / SurfSense

- Nguồn tham khảo tìm kiếm web/GitHub. Chưa dùng làm nguồn chính vì mức official/source stability thấp hơn các nguồn trên trong audit này.
- Bài học giả định, cần kiểm lại ở sprint sau: personal research workspace thường gom nguồn, ghi chú, chat, và lưu insight. Không được coi đây là grounding chính.

### translation_app

- Nguồn tham khảo local: `D:\Sandbox\translation_app`.
- Repo state: branch `wip/phase-5n-f-ocr-benchmark`, HEAD `f105ffb`, dirty do untracked `.vscode/`; không sửa gì trong repo này.
- File đã đọc: `core/providers/profiles.py`, `core/provider_router.py`, `core/ai_service.py`, `ui/ai_settings_dialog.py`, `config.py`.
- Bài học phù hợp:
  - Có provider profile thật: Gemini, Google Translate, ChatAnyWhere, DeepSeek, NVIDIA NIM, OpenAI-compatible, Groq, Cerebras, OpenRouter, Mistral, SambaNova, Cloudflare Workers AI, HuggingFace, GitHub Models, AI21.
  - Có model pool, API key pool, waterfall priority, health/cooldown, auth/quota handling.
  - Có secret masking và tách secret config.
- Khuyến nghị: AIOS không tự bịa model. Màn `Chọn model AI` phải đọc catalog thật từ AIOS hoặc đồng bộ có kiểm soát với translation_app.

## 6. Product direction mới

AIOS mới nên được hiểu như:

```text
Sổ tài liệu
  -> nhiều cuộc trò chuyện trong sổ
  -> nguồn trong sổ + nguồn tạm trong cuộc trò chuyện
  -> câu trả lời có nguồn chứng minh
  -> lưu kết quả thành hồ sơ sự việc hoặc thêm nguồn vào sổ
  -> xem vì sao AIOS kết luận
```

AIOS học từ NotebookLM ở mô hình "nguồn + hỏi đáp có chứng minh", nhưng khác ở:

- một sổ có nhiều cuộc trò chuyện;
- cuộc trò chuyện có nguồn tạm riêng;
- nguồn tạm tồn tại cả cuộc trò chuyện, không chỉ một câu hỏi;
- kết quả có thể lưu thành hồ sơ sự việc;
- Excel `.xlsx/.xls`, log, email, ảnh màn hình, đoạn chat dài là nguồn công việc thật;
- dữ liệu công việc ưu tiên local-first;
- có phần kiểm chứng kết luận và việc nên làm tiếp.

## 7. Luồng người dùng mới

1. Owner mở app.
2. App hiện `Sổ tài liệu của tôi`.
3. Owner mở sổ gần nhất, ví dụ `MOM / Opcenter`, trong tối đa 2 click.
4. Owner thấy danh sách cuộc trò chuyện trong sổ.
5. Owner mở cuộc trò chuyện cũ hoặc bấm `Tạo cuộc trò chuyện mới`.
6. Owner chọn nguồn trong sổ: dùng toàn bộ sổ, chỉ nguồn đã chọn, hoặc loại trừ vài nguồn.
7. Owner hỏi AIOS bằng câu tự nhiên.
8. Nếu đang điều tra, owner dán log/email/chat hoặc đính kèm Excel/ảnh ngay trong khung chat.
9. AIOS đánh dấu các thứ vừa dán là `Nguồn tạm trong cuộc trò chuyện`.
10. Câu hỏi tiếp theo trong cùng cuộc trò chuyện tự động dùng nguồn tạm đó.
11. AIOS trả lời bằng `Trả lời chính`, `Nguồn chứng minh`, `Cần kiểm lại`, `Việc nên làm tiếp`.
12. Nếu kết quả đáng giữ, owner bấm `Lưu vào hồ sơ`.
13. Nếu nguồn tạm nên dùng lâu dài, owner bấm `Thêm vào sổ tài liệu`.
14. Nếu muốn kiểm sâu, owner bấm `Xem vì sao AIOS kết luận như vậy`.

## 8. Màn hình đề xuất

1. `Sổ tài liệu của tôi`
2. `Chat trong sổ`
3. `Nguồn trong sổ`
4. `Nguồn tạm trong cuộc trò chuyện`
5. `Hồ sơ sự việc`
6. `Xem vì sao AIOS kết luận như vậy`
7. `Cài đặt / Chọn model AI`

Các màn hình legacy như Prompt Pack, NotebookLM Bridge, Mermaid, Visual Map kỹ thuật, Audit chi tiết nên chuyển vào `Nâng cao` hoặc chỉ dành cho developer.

## 9. Thiết kế nhiều cuộc trò chuyện trong một sổ

Mỗi sổ cần có nhiều cuộc trò chuyện. Một cuộc trò chuyện có:

- tiêu đề;
- ngày tạo;
- sổ tài liệu đang dùng;
- nguồn trong sổ được chọn;
- nguồn tạm riêng;
- lịch sử hỏi/trả lời riêng;
- trạng thái đã lưu hồ sơ hay chưa.

Không thiết kế một chat dài vô tận cho cả sổ. Ví dụ trong sổ `MOM / Opcenter`:

- `Lỗi Manual Supply hôm nay`
- `Kiểm tra BOP change`
- `Viết mail hỏi IT`
- `So sánh InterStock và Opcenter`

Trạng thái cần có:

- chưa có cuộc trò chuyện;
- có cuộc trò chuyện gần đây;
- cuộc trò chuyện có nguồn tạm chưa lưu;
- cuộc trò chuyện đã lưu vào hồ sơ.

## 10. Thiết kế nguồn tạm trong cuộc trò chuyện

Nguồn tạm là file hoặc text owner thêm trong lúc chat:

- đoạn log dài;
- đoạn chat hỗ trợ;
- email;
- ảnh màn hình;
- Excel `.xlsx/.xls`;
- ghi chú điều tra.

Vòng đời:

1. Khi thêm vào chat: trạng thái `Chỉ dùng trong cuộc trò chuyện này`.
2. Trong cùng cuộc trò chuyện: AIOS dùng nó cho các câu hỏi sau.
3. Khi đóng/mở app: vẫn hiển thị trong cuộc trò chuyện, nhưng gắn nhãn `Chưa lưu lâu dài`.
4. Nếu owner bấm `Lưu vào hồ sơ`: nguồn trở thành bằng chứng của hồ sơ.
5. Nếu owner bấm `Thêm vào sổ tài liệu`: nguồn trở thành nguồn lâu dài của sổ.
6. Nếu owner không lưu: nguồn không làm bẩn sổ tài liệu lâu dài.

## 11. Thiết kế chọn nguồn trong sổ

Owner cần chọn nguồn theo ba chế độ:

- `Dùng toàn bộ sổ`
- `Chỉ dùng nguồn đã chọn`
- `Loại trừ nguồn này`

Với sổ lớn:

- có tìm kiếm nguồn;
- có lọc theo loại file;
- có lọc theo ngày thêm;
- có nhóm theo thư mục/chủ đề;
- có cảnh báo nếu quá nhiều nguồn làm câu trả lời loãng.

Không dùng label `chunk`, `retrieval`, `RAG`, `vector`. Thay bằng:

- `Nguồn đã tìm thấy`
- `Nguồn đang dùng`
- `Nguồn không được dùng`
- `Đoạn liên quan`

## 12. Thiết kế Excel trực tiếp

AIOS phải hỗ trợ `.xlsx/.xls` như nguồn thật:

- thêm Excel vào sổ tài liệu;
- thêm Excel vào cuộc trò chuyện như nguồn tạm;
- không bắt owner chuyển Google Sheets/CSV;
- khi trả lời, hiển thị tên file, sheet, dòng/cột nếu có;
- với file nhiều sheet, hỏi owner chọn sheet hoặc tự ghi rõ sheet đã dùng;
- nếu Excel bẩn hoặc nhiều bảng trong một sheet, báo `Cần kiểm lại vùng dữ liệu`.

## 13. Thiết kế câu trả lời của AIOS

Câu trả lời không nên luôn là form cứng. Với câu hỏi đơn giản, trả lời tự nhiên. Với câu hỏi điều tra, dùng cấu trúc:

- `Trả lời chính`
- `Nguồn chứng minh`
- `Cần kiểm lại`
- `Việc nên làm tiếp`
- Nút `Lưu vào hồ sơ`
- Nút `Xem vì sao AIOS kết luận như vậy`
- Nút `Tạo email trả lời`
- Nút `Tạo checklist kiểm tra`

Nếu thiếu bằng chứng, AIOS phải nói ngắn: `Chưa đủ nguồn để kết luận chắc. Cần thêm ...`

## 14. Wireframe text

```text
[Màn hình: Sổ tài liệu của tôi]

Trái:
- Danh sách sổ tài liệu
- Nút: Mở sổ
- Nút: Tạo sổ mới

Giữa:
- Sổ mở gần đây
- Sổ: MOM / Opcenter
- Sổ: InterStock / WMS
- Sổ: Email Nhật - Việt
- Trạng thái: số nguồn, số cuộc trò chuyện, hồ sơ đã tạo

Phải:
- Hỏi AIOS ở đâu
- Việc nên làm đầu tiên
- Nguồn đang chờ kiểm tra

Trống:
- Hiện nút "Tạo sổ tài liệu đầu tiên"

Có dữ liệu:
- Mở sổ gần nhất trong 1 click
```

```text
[Màn hình: Chat trong sổ]

Trái:
- Tên sổ
- Danh sách cuộc trò chuyện
- Nút: Tạo cuộc trò chuyện mới
- Nguồn trong sổ
- Nguồn tạm trong cuộc trò chuyện

Giữa:
- Lịch sử chat
- Ô nhập câu hỏi
- Khu vực dán log/email/chat
- Nút đính kèm file
- Checkbox: dùng nguồn tạm trong câu hỏi tiếp theo

Phải:
- Trả lời chính
- Nguồn chứng minh
- Cần kiểm lại
- Việc nên làm tiếp
- Nút: Lưu vào hồ sơ
- Nút: Xem vì sao AIOS kết luận như vậy
```

```text
[Màn hình: Nguồn trong sổ]

Trái:
- Bộ lọc loại file
- Bộ lọc ngày thêm
- Bộ lọc trạng thái riêng tư

Giữa:
- Bảng nguồn: tên, loại, ngày thêm, có thể dùng hay không
- Nút: Thêm tài liệu
- Nút: Thêm Excel

Phải:
- Xem trước nguồn
- Sheet/dòng/cột nếu là Excel
- Nút: Dùng trong cuộc trò chuyện hiện tại
- Nút: Không dùng nguồn này
```

```text
[Màn hình: Nguồn tạm trong cuộc trò chuyện]

Trái:
- Danh sách nguồn tạm
- Trạng thái: chưa lưu lâu dài / đã lưu hồ sơ / đã thêm vào sổ

Giữa:
- Xem nội dung tóm tắt
- Nơi nguồn được dùng trong các câu trả lời

Phải:
- Nút: Lưu vào hồ sơ
- Nút: Thêm vào sổ tài liệu
- Nút: Bỏ khỏi cuộc trò chuyện này
```

```text
[Màn hình: Hồ sơ sự việc]

Trái:
- Danh sách hồ sơ
- Lọc theo sổ tài liệu
- Lọc theo trạng thái

Giữa:
- Tình huống
- Bằng chứng đã lưu
- Câu trả lời đã lưu
- Việc cần làm

Phải:
- Bài học rút ra
- Tạo bàn giao
- Tạo email trả lời
- Mở lại cuộc trò chuyện gốc
```

```text
[Màn hình: Xem vì sao AIOS kết luận như vậy]

Trái:
- Câu trả lời đang kiểm tra
- Nguồn đã dùng

Giữa:
- Từng ý chính của câu trả lời
- Nguồn chứng minh cho từng ý
- Ý nào còn thiếu nguồn

Phải:
- Cần kiểm lại
- Nguồn mâu thuẫn
- Nút: Quay lại chat
- Nút: Lưu ghi chú kiểm chứng
```

```text
[Màn hình: Cài đặt / Chọn model AI]

Trái:
- Chế độ dữ liệu: trong máy / tài liệu thường
- Danh sách nguồn AI khả dụng

Giữa:
- Chọn model AI
- Trạng thái kết nối
- Gợi ý dùng model theo việc

Phải:
- Vì sao nguồn AI này được chọn
- Có gửi ra ngoài không
- Cảnh báo dữ liệu riêng tư
```

## 15. Bộ thuật ngữ UI tiếng Việt

| Thuật ngữ nội bộ | Không dùng trong UI owner | Từ thay thế | Ví dụ UI |
|---|---|---|---|
| RAG | Có | Hỏi từ nguồn tài liệu | `Hỏi AIOS từ nguồn trong sổ` |
| node | Có | mục / ý / nguồn | `Chọn một mục để xem chi tiết` |
| edge | Có | quan hệ / vì sao liên quan | `Vì sao nguồn này liên quan` |
| claim | Có | ý kết luận | `Ý này cần kiểm lại` |
| citation | Có | nguồn chứng minh | `Nguồn chứng minh` |
| provider router | Có | AIOS tự chọn nguồn AI | `AIOS tự chọn model phù hợp` |
| vector | Có | không hiển thị | Không đưa ra UI |
| Mermaid | Có | bản xem kiểm chứng | `Tải bản kiểm chứng an toàn` |
| local_only | Có | dữ liệu chỉ lưu trên máy này | `Dữ liệu chỉ lưu trên máy này` |
| embedding | Có | không hiển thị | Không đưa ra UI |
| chunk | Có | đoạn liên quan | `Đoạn liên quan trong nguồn` |
| retrieval | Có | tìm nguồn liên quan | `AIOS đã tìm nguồn liên quan` |
| prompt pack | Có | gói gửi cho AI | `Tạo gói hỏi model mạnh` trong nâng cao |

## 16. Provider/model design dựa trên translation_app

Provider/model grounded từ `translation_app`:

- `gemini`
- `google`
- `chatanywhere`
- `deepseek`
- `nvidia_nim`
- `openai_compatible`
- `groq`
- `cerebras`
- `openrouter`
- `mistral`
- `sambanova`
- `cloudflare`
- `huggingface`
- `github`
- `ai21`

Thiết kế `Chọn model AI`:

- Owner thấy nhóm: `AI trong máy`, `AI cho tài liệu thường`, `Nguồn tự cấu hình`.
- Với dữ liệu công ty/mật: chỉ hiện hoặc ưu tiên nguồn trong máy/nội bộ đã tin cậy.
- Với tài liệu thường: có thể dùng nguồn cloud đã cấu hình.
- Không hiển thị API key raw.
- Không tự bịa model. Model list lấy từ catalog/config thật.
- Nếu chưa có grounding đủ: hiển thị `Danh sách model sẽ lấy từ cấu hình provider thật sau`.

Phần cần đồng bộ tương lai:

- `AIOS_habbit/src/aios_habit/provider_catalog.py`
- `AIOS_habbit/src/aios_habit/ai_router.py`
- `translation_app/core/providers/profiles.py`
- `translation_app/core/provider_router.py`
- `translation_app/core/ai_service.py`
- UI settings cho API key pool, model pool, health/cooldown.

## 17. Recommended architecture

### Option A - Sửa tiếp `case_cockpit.py`

- Ưu điểm: nhanh.
- Nhược điểm: tiếp tục nhồi UI vào file đã quá lớn; owner flow vẫn bị legacy kéo lại.
- Kết luận: không chọn.

### Option B - Tạo lớp UI mới song song, giữ lõi cũ

- Ý tưởng: tạo `workspace_chat` models/store/service/UI mới; dùng lại case/evidence/notebook/provider/visual-map lõi; legacy Case Cockpit chuyển vào `Nâng cao`.
- Ưu điểm: giảm rủi ro, giữ được lõi đã test, không đập bỏ dữ liệu cũ.
- Nhược điểm: cần mapping migration giữa Notebook/Case/Evidence và Conversation/TemporarySource.
- Kết luận: **khuyến nghị chọn**.

### Option C - Viết lại toàn bộ app

- Ưu điểm: sạch nhất về UI.
- Nhược điểm: rủi ro mất các guard privacy, evidence, provider, visual-map đã có.
- Kết luận: không chọn ở giai đoạn này.

Rollback plan:

- Giữ `case_cockpit.py` legacy chạy được.
- UI mới chỉ đọc/ghi qua store mới có test.
- Nếu UI mới fail, sidebar có link `Mở giao diện cũ`.
- Không xóa module legacy trước khi owner pilot pass.

File/khu vực sẽ tạo/sửa ở implementation sau:

- `src/aios_habit/workspace_chat_models.py`
- `src/aios_habit/workspace_chat_store.py`
- `src/aios_habit/workspace_chat_service.py`
- `src/aios_habit/workspace_chat_ui.py`
- `src/aios_habit/case_cockpit.py` chỉ làm shell/router nhẹ hoặc legacy entry
- tests mới cho conversation, temporary source, source selection, save-to-case, explain answer.

## 18. Owner test tasks

| Task | Thiết kế mới hỗ trợ? | PASS/FAIL |
|---|---|---|
| Mở app và mở sổ `MOM / Opcenter` trong tối đa 2 click | Màn `Sổ tài liệu của tôi` + sổ gần đây | PASS_DESIGN |
| Hỏi một câu trong sổ mà không nạp lại tài liệu thủ công | Chat trong sổ dùng nguồn đã lưu | PASS_DESIGN |
| Dán log dài vào chat, câu hỏi tiếp theo dùng log đó | Nguồn tạm theo cuộc trò chuyện | PASS_DESIGN |
| Lưu kết quả đáng giữ thành hồ sơ sự việc | Nút `Lưu vào hồ sơ` | PASS_DESIGN |
| Mở `Xem vì sao AIOS kết luận như vậy` để kiểm nguồn | Màn kiểm chứng riêng | PASS_DESIGN |

Task mở rộng:

- Tạo cuộc trò chuyện mới trong cùng sổ: PASS_DESIGN.
- Mở lại cuộc trò chuyện cũ: PASS_DESIGN.
- Chọn vài nguồn cụ thể trong sổ: PASS_DESIGN.
- Thêm Excel vào cuộc trò chuyện: PASS_DESIGN.
- Thêm Excel vào sổ tài liệu: PASS_DESIGN.
- Tạo email Nhật từ kết quả điều tra: PASS_DESIGN, cần implementation action.
- Tạo checklist lần sau: PASS_DESIGN, cần reuse learning/action helpers.

## 19. Roadmap triển khai sau audit

### Phase 0 - Không code

- Mục tiêu: chốt report này, naming, data flow, wireframe, file classification.
- File: `docs/ux/WORKSPACE_CHAT_UX_REDESIGN_AUDIT.md`.
- Test: review report bằng 5 owner tasks.
- PASS: owner đồng ý hướng Option B.
- Model: Codex GPT-5.5.

### Phase 1 - Khung UI mới

- Mục tiêu: `Sổ tài liệu của tôi`, nhiều cuộc trò chuyện trong sổ, Chat trong sổ.
- File tương lai: `workspace_chat_models.py`, `workspace_chat_store.py`, `workspace_chat_ui.py`.
- Test: tạo/mở/đổi tên conversation; mở sổ trong 2 click.
- Rủi ro: đụng nhiều trạng thái Streamlit.
- Model: Gemini 3.x Pro High hoặc Gemini 3.5 Flash High.

### Phase 2 - Chọn nguồn và Excel trực tiếp

- Mục tiêu: chọn nguồn trong sổ, nguồn tạm, Excel `.xlsx/.xls` trực tiếp.
- File tương lai: `source_ingest.py`, `notebook_index.py`, `workspace_chat_service.py`.
- Test: Excel nhiều sheet, nguồn tạm còn hiệu lực trong câu hỏi tiếp theo.
- Rủi ro: Excel bẩn, nhiều bảng, privacy.
- Model: Gemini implementation, Codex audit.

### Phase 3 - Lưu tri thức

- Mục tiêu: lưu câu trả lời vào hồ sơ; thêm nguồn tạm vào sổ.
- File tương lai: `case_store.py`, `case_models.py`, `workspace_chat_store.py`.
- Test: lưu hồ sơ không mất nguồn; mở lại cuộc trò chuyện gốc.
- Rủi ro: duplicate evidence.

### Phase 4 - Kiểm chứng

- Mục tiêu: `Xem vì sao AIOS kết luận như vậy`.
- File tương lai: `visual_map_builder.py`, `visual_map_ui.py`, wrapper owner copy.
- Test: thiếu nguồn, nguồn mâu thuẫn, nguồn chứng minh.
- Rủi ro: lộ thuật ngữ kỹ thuật.

### Phase 5 - Tích hợp model/provider

- Mục tiêu: chọn model AI dựa trên catalog thật, không bịa provider.
- File tương lai: `provider_catalog.py`, `ai_router.py`, settings UI.
- Test: local/company data không gửi cloud; normal docs chọn provider đã cấu hình.
- Rủi ro: drift với translation_app.

### Phase 6 - Pilot owner

- Mục tiêu: chạy việc thật: MOM/Opcenter, InterStock/WMS, email Nhật-Việt, log, ảnh lỗi, Excel.
- Test: 5 owner tasks bắt buộc + task mở rộng.
- PASS: owner làm được không cần agent đứng cạnh.

## 20. PASS/FAIL criteria cho thiết kế

- Owner mở app biết bấm đâu đầu tiên: PASS_DESIGN.
- Mở sổ `MOM / Opcenter` trong tối đa 2 click: PASS_DESIGN.
- Một sổ có nhiều cuộc trò chuyện: PASS_DESIGN.
- Chat nhiều lượt trong một sổ: PASS_DESIGN.
- Nguồn tạm tồn tại trong cả cuộc trò chuyện: PASS_DESIGN.
- Nguồn tạm sau khi đóng/mở app được đánh dấu `Chưa lưu lâu dài`: PASS_DESIGN.
- Có thể chọn nguồn trong sổ cho lần chat này: PASS_DESIGN.
- Có thể thêm Excel `.xlsx/.xls` trực tiếp: PASS_DESIGN.
- Có thể lưu kết quả vào hồ sơ: PASS_DESIGN.
- Có thể xem vì sao AIOS kết luận: PASS_DESIGN.
- Không lộ thuật ngữ kỹ thuật ra UI owner: PASS_DESIGN, cần test copy ở implementation.
- Không bịa provider/model: PASS_DESIGN, dựa translation_app và AIOS catalog.
- Không ép mọi câu trả lời thành form cứng: PASS_DESIGN.
- Có phân loại file hiện tại: PASS.
- Có kiến trúc khuyến nghị: PASS.
- Có rollback plan: PASS.

## 21. Việc KHÔNG làm trong audit này

- Không code.
- Không xóa file.
- Không sửa logic.
- Không sửa test.
- Không commit.
- Không tạo branch.
- Không dùng stash.
- Không dùng checkout/reset/clean để hủy thay đổi.
- Không benchmark 12Q.
- Không claim NotebookLM replacement.
- Không claim global parity.
- Không mở P1.0.

## 22. Lệnh kiểm tra cuối

Kết quả sau khi tạo report:

```powershell
git status --short
git diff --name-only
git diff --stat
```

Kết quả:

- `git status --short`: `?? docs/ux/` và warning `could not open directory '.codex/': Permission denied`.
- `git diff --name-only`: rỗng vì report mới đang untracked.
- `git diff --stat`: rỗng vì report mới đang untracked.
- `git diff --name-only -- src tests`: rỗng.
- `git ls-files docs/ux`: rỗng, xác nhận chưa commit/stage.
- Scan token shape trong report: không thấy token OpenAI-style, Google-style, NVIDIA-style, bearer header, hoặc private-key marker.
- Literal `API Key.txt` chỉ xuất hiện trong baseline ignored-file summary, không phải secret.

Xác nhận:

- không có file trong `src/` bị sửa;
- không có file trong `tests/` bị sửa;
- không có `local_cases/`, `local_runs/`, screenshot, raw data mới ngoài vùng ignore;
- không có API key hoặc secret trong report;
- repo dirty chỉ vì report mới trong `docs/ux`;
- không có file bị xóa;
- không commit;
- không tạo branch;
- không dùng stash/checkout/reset/clean.
