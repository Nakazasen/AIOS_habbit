# Original User Request

## Initial Request — 2026-08-21T09:49:45Z

Add a local folder document batch import feature to AIOS Habit Workspace Chat, allowing users to enter a directory path on their machine to scan and ingest all supported documents (.pdf, .docx, .xlsx, .xls, .pptx, .txt, .md, .csv, images) into a notebook or conversation in one click.

Requirements:
- R1. Local Directory Scanner & Validator: backend utility to scan a local folder path for supported document formats (with optional recursive subfolder scan), reporting total file count, supported vs unsupported files, and total size. Validate security and path existence.
- R2. Workspace Chat UI Integration: Add "📁 Nhập từ thư mục" (Import from Folder) option inside "Thêm nguồn" (Add Sources) in `src/aios_habit/workspace_chat_app.py`. Include path input field, "Quét thư mục" (Scan Folder) button with preview table/list, and "Nhập tất cả tài liệu vào sổ" (Ingest All) button. Privacy level settings and progress bar / status summary.
- R3. Batch Ingestion Execution & Error Resilience: Process files sequentially or in bounded batches through existing extraction and storage pipeline (`source_ingest.py` / `workspace_chat_store.py`). Gracefully handle corrupted or locked files.
- Automated tests covering directory scanning, validation, and batch ingestion.

## Follow-up — 2026-08-21T23:28:43Z

Xây dựng cầu nối trung thực (Truthful Bridge) cho Antigravity IDE trong repo `D:\Sandbox\AIOS_habbit`, loại bỏ hoàn toàn cơ chế facade/giả lập, ưu tiên direct adapter nếu có giao thức xác minh được và tự động chuyển sang handoff bất đồng bộ (Outbox/Inbox) an toàn khi direct không khả dụng.

Working directory: D:\Sandbox\AIOS_habbit
Integrity mode: development

## Requirements

### R1. Antigravity IDE Protocol Verification & Honest Health Status
- Kiểm tra giao thức tích hợp Antigravity IDE thực tế trên môi trường máy cục bộ; tuyệt đối không suy đoán, không reverse-engineer token/credential, không gọi API cloud chưa cấu hình.
- Nếu không có giao thức direct được hỗ trợ chính thức, direct mode phải báo `unavailable`; tuyệt đối không giả lập.
- Thay thế health "ok" chung chung bằng trạng thái máy hữu hạn rõ ràng: `unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed`.
- Endpoint `/health` phải trả về mode thực tế và lý do failure/unavailable đã được sanitize.
- Không quảng cáo các capability (`reasoning`, `large_context`, `excel_sql`) nếu chưa được kiểm tra runtime.
- Sidecar daemon (`scripts/antigravity_sidecar_daemon.py`) tuyệt đối không được gọi vòng lại `RealWorkspaceAIProviderClient` để giả danh Antigravity.

### R2. Asynchronous Handoff & Outbox/Inbox Lifecycle
- Handoff mode sử dụng cơ chế file Outbox/Inbox có sẵn: tạo request bundle có ID duy nhất, theo dõi trạng thái vòng đời, timeout rõ ràng.
- Đảm bảo kiểm tra schema (`RESPONSE_SCHEMA_VERSION`), kiểm soát tính toàn vẹn và trích dẫn citation của response trước khi import.
- Xử lý các trạng thái chờ (`handoff_pending`), hoàn thành (`completed`), hoặc quá hạn/lỗi (`failed`) một cách rõ ràng.

### R3. Workspace Chat Integration & Strict Fail-Closed Behavior
- Khi gửi câu hỏi qua kênh Antigravity: ưu tiên direct mode (nếu `direct_ready`). Nếu direct không sẵn sàng, tự động chuyển sang handoff mode và cập nhật UI "Đang chờ Antigravity IDE xử lý".
- Khi handoff hoàn tất: hiển thị câu trả lời, model/source thực tế từ bundle, và trạng thái hoàn thành.
- Nếu bridge/IDE gặp lỗi hoặc timeout: báo lỗi rõ ràng trực tiếp cho người dùng, tuyệt đối KHÔNG âm thầm fallback sang Smart Router.
- Chỉ hiển thị nhãn "Nguồn AI: Antigravity IDE" khi câu trả lời thực sự đến từ Antigravity (direct hoặc handoff). Trạng thái global hiển thị "Cầu nối sẵn sàng" kèm mode hoạt động.
- Giữ phân biệt rõ ràng giữa cảnh báo "chưa bật nguồn tài liệu" (RAG context) và trạng thái của AI provider bridge.
- Nút/luồng Refresh UI sau khi bật bridge phải phản ánh đúng trạng thái thực tế từ health check.

### R4. Security, Privacy & Logging Sanitization
- Tuyệt đối không gửi dữ liệu `local_only` hoặc tài liệu nội bộ sang bất kỳ endpoint cloud nào.
- Tuyệt đối không ghi log nội dung tài liệu, prompt đầy đủ, API key, private path hoặc credentials.

### R5. Governance & Repository Standards
- Tuân thủ nghiêm ngặt `.antigravityrules`.
- Chạy `graphify query` trước khi sửa đổi và `graphify update .` sau khi cập nhật mã nguồn.
- Tạo và cập nhật đầy đủ bộ Spec Kit artifacts (`spec.md`, `plan.md`, `tasks.md`).

## Verification Plan & Test Resources

### Programmatic Automated Tests (pytest)
- `tests/test_antigravity_bridge.py` & `tests/test_antigravity_handoff_ui_flow.py` (cùng các test suite mới):
  1. **Status & Health**: Kiểm thử endpoint `/health` trả về chính xác tất cả các trạng thái: `unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed`.
  2. **Direct Mode**: Test direct-ready với mock verified adapter trả về phản hồi hợp lệ.
  3. **Direct Unavailable -> Handoff Transition**: Test khi direct unavailable tự động chuyển sang tạo handoff bundle.
  4. **Handoff Lifecycle**: Test tạo request pending -> watcher/IDE xử lý -> bundle completed -> validate schema & import response thành công.
  5. **Fail-Closed Policy**: Test khi bridge lỗi/timeout -> raise/báo lỗi rõ ràng, kiểm chứng `RealWorkspaceAIProviderClient` / Smart Router KHÔNG hề được gọi.
  6. **UI Attribution & Mode**: Test UI render đúng nhãn nguồn AI và trạng thái cầu nối.
  7. **Privacy & Sanitization**: Test không rò rỉ context `local_only` và log không chứa sensitive data.
- Toàn bộ suite pytest liên quan phải pass 100% với `.venv\Scripts\python.exe -m pytest`.
- Kiểm tra cú pháp `git diff --check` và import checks.

## Acceptance Criteria

### Bridge & Sidecar Core
- [ ] Endpoint `/health` trả về đúng struct trạng thái chi tiết, không trả về `capabilities` ảo.
- [ ] `scripts/antigravity_sidecar_daemon.py` không chứa bất kỳ lệnh gọi nào đến `RealWorkspaceAIProviderClient`.
- [ ] Direct mode chỉ kích hoạt khi có adapter thật đã xác minh.

### Handoff & UI Flow
- [ ] Handoff mode tạo request hợp lệ vào outbox và theo dõi trạng thái đến khi hoàn tất hoặc timeout.
- [ ] Giao diện Workspace Chat hiển thị rõ "Đang chờ Antigravity IDE xử lý" trong thời gian pending.
- [ ] Khi timeout/lỗi, hiển thị thông báo lỗi trung thực, không tự ý chuyển sang Smart Router.
- [ ] Nhãn "Nguồn AI: Antigravity IDE" chỉ xuất hiện trên câu trả lời thực sự nhận từ Antigravity.

### Quality & Governance
- [ ] 100% automated unit & integration tests pass cleanly.
- [ ] Spec Kit artifacts được tạo/cập nhật đầy đủ.
- [ ] Graphify graph được cập nhật (`graphify update .`).
- [ ] Báo cáo kết quả đầy đủ: giao thức direct (hoặc lý do unavailable), bằng chứng handoff, kết quả test, file thay đổi.
