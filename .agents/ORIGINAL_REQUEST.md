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

## Follow-up — 2026-09-09T11:26:45Z

This is a single self-contained fix; keep it small and focused. Triển khai với đội ngũ tinh gọn (Small, focused team) tập trung xử lý tuần tự từng cụm theo thứ tự: (1) Sửa ranh giới dữ liệu chép lời thô & khắc phục 37 bài kiểm thử thất bại, (2) Tinh gọn cờ tính năng Goal 010 thành 1 cờ duy nhất, (3) Nối đủ 4 chặng giao diện tiếp nhận tri thức tại workspace_case_ui.py, (4) Tối ưu 3 cụm điều hướng Workspace Chat và chuẩn hóa 100% tiếng Việt giao diện.

Working directory: d:/Sandbox/AIOS_habbit
Integrity mode: development

---

## Requirements

### R1. Ranh giới dữ liệu & Xử lý chép lời minh bạch
- Chuyển toàn bộ nội dung chép lời thô từ `workspace_cases.sqlite` sang vùng lưu trữ cục bộ `local_only`. Cơ sở dữ liệu điều phối chỉ lưu trữ mã băm (SHA-256), siêu dữ liệu, đường dẫn tham chiếu và dữ liệu đã làm sạch.
- Loại bỏ cơ chế fallback giả lập chép lời khi `whisper.cpp` không chạy trong `local_transcription.py`. Hiển thị thông báo lỗi rõ ràng bằng tiếng Việt và cho phép nhập văn bản thủ công.

### R2. Tinh gọn cờ tính năng Goal 010 & Đồng bộ tài liệu
- Gom 5 cờ Goal 010 phân mảnh thành **một cờ duy nhất** để bật/tắt toàn bộ tính năng Goal 010 tại `feature_flags.py`. Loại bỏ các cờ giả lập không được code đọc.
- Đồng bộ lại tài liệu lưu trữ `PERSISTED_DATA_COMPATIBILITY.md` phản ánh đúng việc `production_prediction.sqlite` đã được sử dụng; cập nhật `README.md` sang tiếng Việt duy nhất theo quy định UI/Doc; cập nhật ma trận truy xuất `TRACEABILITY_MATRIX.md`.

### R3. Kết nối đầy đủ 4 chặng giao diện Tiếp nhận Tri thức (Goal 010)
- Nối hai màn hình kiểm tra/phê duyệt (`workspace_case_ui.py:1684`) và đưa vào thư viện (`workspace_case_ui.py:1778`) vào luồng vận hành chính thức, hoàn thiện chu trình 4 chặng: Phỏng vấn → Trích xuất/Biên tập → Kiểm tra/Phê duyệt → Đưa vào thư viện.
- Đảm bảo tính toàn vẹn giao dịch (atomic) khi xuất bản và thu hồi tri thức: trạng thái thành công phải khớp chính xác với dữ liệu lưu trữ cuối cùng, có kiểm thử lỗi giữa chừng và rollback.

### R4. Tối ưu cấu trúc điều hướng Workspace Chat & Chuẩn hóa hiển thị tiếng Việt
- Phân tách màn hình Workspace Chat thành 3 nhóm điều hướng mạch lạc:
  1. **Hỏi tài liệu** (Mặc định)
  2. **Hồ sơ và tri thức**
  3. **Công cụ nâng cao** (Thu gọn, bao gồm LSU shadow mode, C-AGENT, Agent IDE)
- Rà soát và chuyển đổi toàn bộ thuật ngữ kỹ thuật rò rỉ trên UI (`fixture`, `SHA-256 Digest`, `Claims`, `approved`...) sang tiếng Việt thân thiện với người dùng cuối, ẩn chi tiết kỹ thuật ở chế độ hiển thị mặc định.

### R5. Khắc phục dứt điểm 37 bài kiểm thử thất bại & Đạt chuẩn kiểm toán
- Điều tra nguyên nhân gốc rễ và khắc phục toàn bộ 37 ca kiểm thử thất bại trong tổng số 2.662 bài kiểm thử hiện có mà không xóa hay vô hiệu hóa bất kỳ assertion/test case nào.
- Hoàn tất các nhiệm vụ T083–T109 thuộc Goal 010 theo đúng đặc tả và kế hoạch tại `specs/010-expert-knowledge-acquisition/`.

---

## Acceptance Criteria

### Tính đúng đắn của dữ liệu & Bảo mật
- [ ] Không còn dữ liệu chép lời thô (raw transcript) lưu trực tiếp trong `workspace_cases.sqlite`.
- [ ] Khi engine `whisper.cpp` vắng mặt hoặc lỗi, hệ thống hiển thị thông báo lỗi tiếng Việt và kích hoạt giao diện nhập tay, không giả mạo kết quả chép lời.
- [ ] Quy trình xuất bản/thu hồi tri thức có cơ chế kiểm soát lỗi giữa chừng, đảm bảo tính nguyên tử (atomic) và khôi phục khi gặp sự cố.

### Giao diện & Trải nghiệm người dùng
- [ ] Cả 4 chặng tiếp nhận tri thức chuyên gia đều có thể truy cập và hoàn tất tuần tự từ giao diện người dùng.
- [ ] Giao diện Workspace Chat phân định rõ 3 khu vực điều hướng, không gây rối cho người dùng thông thường.
- [ ] 100% văn bản giao diện hiển thị bằng tiếng Việt chuẩn mực, không rò rỉ từ ngữ kỹ thuật tiếng Anh hoặc traceback thô.
- [ ] Chỉ 1 cờ tính năng duy nhất điều khiển toàn bộ Goal 010.

### Kiểm thử & Kiểm toán mã nguồn
- [ ] `uv run --no-sync --group dev python -m compileall src tests` kết thúc không có lỗi cú pháp.
- [ ] Toàn bộ bộ kiểm thử `uv run --no-sync --group dev pytest -q` đạt 100% PASS (0 failures, 0 errors).
- [ ] `uv run --no-sync --group dev python -m aios_habit.cli audit` trả về kết quả `"status": "PASS"`.
- [ ] Lệnh nhập kiểm tra `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` thực thi thành công.

## Follow-up — 2026-09-09T12:50:06Z

CHỈ THỊ KIỂM TOÁN KHẨN CẤP TỪ USER (AUDIT BLOCKER):

Kết luận kiểm toán độc lập song song: KHÔNG CHẤP NHẬN, KHÔNG COMMIT VÀ KHÔNG ĐÓNG GOAL 010.
Các vòng phản biện trước đã bỏ lọt hoặc tự tạo nguy cơ Fake PASS.

YÊU CẦU THỰC THI NGAY LẬP TỨC:
1. Dừng ngay việc đánh dấu hoàn thành. Trả toàn bộ các công việc T083–T109 trong specs/010-expert-knowledge-acquisition/tasks.md về trạng thái chưa hoàn thành `[ ]`.
2. Dỡ bỏ toàn bộ logic tự sinh fixture thiếu hoặc nuốt lỗi trong tests/conftest.py (vi phạm quy tắc Không Fake PASS của repo).
3. Xử lý triệt để 8 blocker sau đây theo thứ tự nghiêm ngặt:
   - Blocker 1 (Lỗi Runtime): Sửa `NameError: name 'hashlib' is not defined` tại src/aios_habit/expert_interview_repository.py:594.
   - Blocker 2 (Lỗi Runtime): Sửa crash luồng phỏng vấn do truy cập `service.repository` không tồn tại tại src/aios_habit/workspace_case_ui.py:628.
   - Blocker 3 (Bảo toàn dữ liệu): Sửa migration v8 tại src/aios_habit/workspace_case_migrations.py:497. Tuyệt đối không để mất dữ liệu; JSON lỗi không được đổi thành danh sách rỗng rồi xóa dữ liệu gốc (phải fail-closed hoặc xử lý an toàn).
   - Blocker 4 (Cờ tính năng): Bật Goal 010 không được liên quan hoặc kích hoạt lại phân quyền cũ thông qua alias `FEATURE_EXPERT_MULTI_USER` tại src/aios_habit/feature_flags.py:19.
   - Blocker 5 (Rollback/Thu hồi xuất bản): Tại src/aios_habit/knowledge_publication.py:462, rollback xuất bản phải an toàn, thu hồi phải xóa file thật, không nuốt lỗi rồi trả PASS giả.
   - Blocker 6 (Chuẩn hóa UX 4 chặng): Đơn giản hóa giao diện đúng 4 chặng (bỏ menu 5 lựa chọn, bỏ âm thanh mẫu, bỏ chọn chuyên gia/scope/ngân sách, bỏ mã băm, mã sao lưu và nhập mã gói trên UI thường).
   - Blocker 7 (Kiểm thử thực chất): Khắc phục dứt điểm các ca kiểm thử đang fail (27 PASS 5 FAIL ở nhánh transcript/migration, 63 PASS 3 FAIL ở nhánh UI/xuất bản, 1 FAIL ở E2E Goal 010).
   - Blocker 8 (Quy trình nghiệm thu): Chỉ được tick `[x]` từng task sau khi test tương ứng thực sự PASS và Audit Specialist độc lập xác nhận có bằng chứng lệnh. Không mở thêm phạm vi.

Hãy chuyển tiếp chỉ thị này ngay đến Orchestrator và đội ngũ thực thi để khắc phục.
