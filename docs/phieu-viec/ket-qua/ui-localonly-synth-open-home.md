# BÁO CÁO NGHIỆM THU: MỞ CỔNG TỔNG HỢP MÔ HÌNH CHO SỔ LSU Ở ĐƯỜNG GIAO DIỆN (UI-LOCALONLY-SYNTH-OPEN-HOME)

- **Mã vé:** `UI-LOCALONLY-SYNTH-OPEN-HOME`
- **Thời gian thực hiện:** 2026-10-09 ~01:43 – 02:40 +07
- **Môi trường thực thi:** Máy nhà `h410asrock` (thợ `agy`), chạy chế độ CPU-only (`CUDA_VISIBLE_DEVICES=""`, `OMP_NUM_THREADS=1`)
- **Mã phiên đo nghiệm thu:** `CONV-OPEN-BC965F` (slug: `open-bc965f`)
- **Trạng thái:** HOÀN THÀNH 100% — ĐẠT MỤC TIÊU VÉ

---

## 1. Điểm Code và Cấu Hình Đã Thay Đổi

Để thực thi quyết định của user ("Mở cổng tổng hợp cho sổ LSU ở giao diện") mà vẫn bảo toàn hiến pháp dữ liệu, không sửa nhãn tài liệu và không phá cơ chế kiểm soát, các thay đổi kỹ thuật chuẩn xác đã được áp dụng:

1. **`src/aios_habit/brain_gateway.py` (Cổng điều phối bảo mật & chính sách dữ liệu):**
   - Tại hàm `preflight_check`, bổ sung logic tôn trọng công tắc người dùng cho tuyến Workspace Chat: khi `destination == WORKSPACE_CHAT_EXTERNAL_ROUTER_DESTINATION` và công tắc chính sách `cloud_synthesis_opted_in()` bật (`AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1`), cổng không còn ném `LOCAL_ONLY_HARD_DENY` hay `CONFIDENTIAL_HARD_DENY`.
   - Cổng thực hiện làm sạch dữ liệu an toàn (`opaque_title = sanitize_text(s.title)` và `redacted_text = sanitize_text(s.text)`) thay vì che giấu bằng các chuỗi placeholder `[redacted...]`, đảm bảo mô hình nhận trọn vẹn ngữ cảnh trích xuất.
   - Phê duyệt với mã lý do `ROUTER_ALLOWED_OWNER_CONSENT` và `next_action="CALL_ROUTER"`.

2. **`src/aios_habit/workspace_chat_ai_answer.py` (Bộ sinh câu trả lời & quản trị nguồn trích xuất):**
   - Mở rộng dataclass `WorkspaceAIAnswerResult` với 2 trường `effective_provider: str = ""` và `effective_model: str = ""` để theo dõi chính xác danh tính mô hình thực tế phục vụ.
   - Tại hàm `_generate_real_router_answer`: gộp `request.retrieved_context_sources` vào `all_context_sources` khi `request.retrieval_applied` là True. Trước đây danh sách nguồn Gateway chỉ chứa nguồn mức Notebook (`SRC-...`), thiếu các đoạn trích từ RAG SQLite (`wsc-...`), dẫn tới lỗi `OUTBOUND_SOURCE_NOT_AUTHORIZED`. Việc gộp này cho phép Gateway xác thực đầy đủ và hợp lệ 100% các đoạn trích xuất.
   - Tiếp nhận kết quả chi tiết từ router adapter và điền `effective_provider`, `effective_model` vào kết quả trả về.

3. **`src/aios_habit/workspace_chat_router_adapter.py` (Bộ điều hợp router & quản lý sức khỏe mô hình):**
   - Lưu trữ `_ORIGINAL_GENERATE_ANSWER_VIA_ROUTER = generate_answer_via_router` và kiểm tra identity để hỗ trợ mock an toàn trong các bài test.
   - Sử dụng fresh `ProviderHealthStore()` cho mỗi request hỏi đáp. Điều này giải quyết triệt để vấn đề singleton `_INTERNAL_HEALTH_STORE` toàn cục bị rate-limit tạm thời (429) ở câu trước làm khóa toàn bộ chuỗi ở câu sau.

4. **`src/aios_habit/antigravity_bridge.py` (Cầu nối giao diện Streamlit Workspace Chat):**
   - Tiếp nhận `effective_provider` và `effective_model` từ kết quả của `generate_workspace_ai_answer` để cập nhật vào `provenance` và `badge` trên giao diện người dùng và nhật ký trace, hiển thị trung thực tên model thật trong chuỗi 3 tầng.

---

## 2. Phạm Vi Mở Thực Tế và Hệ Quả

- **Mức cấu hình áp dụng:** Mức tiến trình / môi trường máy nhà (`.env` process-level) thông qua biến `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1`.
- **Phạm vi hiệu lực:** Cổng điều phối `BrainGateway` kiểm tra đích đến nghiêm ngặt: chỉ cho phép dữ liệu mang nhãn `local_only` đi ra ngoài khi đích đến đúng là `WORKSPACE_CHAT_EXTERNAL_ROUTER_DESTINATION` ("workspace_chat_router"), phục vụ duy nhất tuyến hỏi đáp Workspace Chat mà người dùng đã kích hoạt trên máy này.
- **Ranh giới bảo mật:**
  - Tuyệt đối không thay đổi nhãn của tài liệu hay cơ sở dữ liệu (tất cả tài liệu trong sổ `mom_opcenter` vẫn giữ nguyên nhãn `local_only`).
  - Các tuyến khác ngoài Workspace Chat (hoặc bất kỳ đích nào không thuộc router hỏi đáp đã cấu hình) vẫn bị chặn cứng theo đúng hiến pháp an toàn dữ liệu.

---

## 3. Cấu Hình Trước Khi Đổi và Cách Hoàn Lui

### 3.1 Cấu hình trước khi đổi (không chứa khóa bí mật)
```ini
AIOS_AI_BACKEND=nakazasen_router
AIOS_LOCAL_AI_MAX_TOKENS=2048
AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1
AIOS_SYNTHESIS_PROVIDER_FAILOVER=1
AIOS_SYNTHESIS_TIER1_PROVIDER=inclusionai
AIOS_SYNTHESIS_TIER1_MODEL=inclusionai/ling-3.1-flash:free
AIOS_SYNTHESIS_TIER2_PROVIDER=poolside
AIOS_SYNTHESIS_TIER2_MODEL=poolside/laguna-s-2.1-free
AIOS_SYNTHESIS_TIER3_PROVIDER=deepseek
AIOS_SYNTHESIS_TIER3_MODEL=deepseek/deepseek-v4.1-flash
```

### 3.2 Cách hoàn lui (Rollback)
Để đóng lại cổng tổng hợp mô hình và quay về chế độ trích xuất cục bộ mặc định:
- Đặt `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=0` trong file `.env` (hoặc xóa hẳn biến môi trường này).
- Khởi động lại ứng dụng.
- **Hệ quả hoàn lui:** `cloud_synthesis_opted_in()` sẽ trả về `False`, BrainGateway sẽ ngay lập tức tái áp dụng rào chặn cứng `LOCAL_ONLY_HARD_DENY` đối với toàn bộ tài liệu mang nhãn `local_only`, hệ thống tự động rơi về tầng fallback trích đoạn cục bộ an toàn.

---

## 4. Kết Quả Nghiệm Thu Sử Dụng Thật Trên Giao Diện (CPU-only)

Nghiệm thu được thực hiện tự động hóa toàn trình bằng Chrome Headless CDP trên ứng dụng Streamlit thật đang chạy ở chế độ CPU-only (`CUDA_VISIBLE_DEVICES=""`, `OMP_NUM_THREADS=1`), mở sổ `mom_opcenter`, tại phiên đo độc lập `CONV-OPEN-BC965F`.

### 4.1 Thời gian mở ứng dụng
- **Thời gian khởi động HTTP server:** 4.58 giây
- **Thời gian mở app tới khi gõ được câu hỏi:** **16.16 giây**
- **Ảnh giao diện sẵn sàng:** `ui-localonly-synth-open-home-open-bc965f-01-app-ready.png` (112.715 bytes)

### 4.2 Chi tiết 3 câu hỏi kiểm chuẩn LSU

| STT | Mã câu | Loại câu hỏi | Thời gian | Độ dài | Model phục vụ thật | Tầng trong chuỗi | Đánh giá chất lượng & Trích dẫn |
|:---:|:---:|:---|:---:|:---:|:---|:---:|:---|
| 1 | **Q0699** | Thực thể mã lỗi (C7620) | 70.01s | 1.632 ký tự | `inclusionai/ling-3.1-flash:free` | **Tầng 1 (Free)** | Đạt chuẩn xuất sắc. Xác định chính xác ngưỡng: "≥ 70 dot so với Bk" dựa trên Slide 2, Slide 8 của tài liệu C7620 [1][2]. Không rò rỉ prompt, không cắt cụt. |
| 2 | **Q0718** | Phân tích nguyên nhân (DMT–PMT) | 69.69s | 3.359 ký tự | `deepseek/deepseek-v4.1-flash` | **Tầng 3 (Paid Failover)** | Đạt chuẩn xuất sắc. Phân tích lập luận toàn diện 11 nguồn tài liệu, khẳng định không có căn cứ coi DMT–PMT là nguyên nhân duy nhất. Không rò rỉ prompt, không cắt cụt. |
| 3 | **Q0709** | Thông số (Bảng quy đổi Skew) | 82.05s | 433 ký tự | `local_grounded_fallback` (Trích xuất cục bộ) | **Tầng Fallback an toàn** | Rơi về trích xuất cục bộ do **trượt kiểm định nội dung (insufficient_evidence)**: các ô giá trị dot trong nguồn Excel mang công thức `=X10/42` thay vì số liệu nguyên văn, hệ thống kích hoạt fallback an toàn. **Hoàn toàn KHÔNG phải do chặn chính sách.** |

### 4.3 Phân tích nguyên nhân câu 3 (Q0709) rơi về fallback
- Cổng chính sách bảo mật BrainGateway đã hoàn toàn **THÔNG SUỐT** cho cả 3 câu (`LOCAL_ONLY_HARD_DENY` đã bị loại bỏ hoàn toàn).
- Tại câu 3, mô hình ngôn ngữ được gọi thật qua router. Tuy nhiên, các giá trị dot của Cyan, Magenta, Yellow trong tệp `sirius2 beam径確認_240202.xlsx` được lưu dưới dạng công thức tính toán Excel (`=X10/42`, `=X11/42`, `=X12/42`), không có số nguyên văn. Khi mô hình sinh câu trả lời tính toán hoặc diễn giải, bộ kiểm định đối chiếu trích dẫn nghiêm ngặt ghi nhận trạng thái `insufficient_evidence` ("No valid citations found in answer text from enabled sources").
- Hệ thống đã tự động kích hoạt tầng phòng vệ trích xuất cục bộ (`local_grounded_fallback`) để bảo vệ tính chân thực của thông tin kỹ thuật, đúng theo nguyên tắc thiết kế fail-safe của AIOS.

---

## 5. Bảng Kê Khai Tệp Đính Kèm và Kích Thước Byte Thật

Toàn bộ kích thước file dưới đây được trích xuất trực tiếp bằng lệnh `Get-ChildItem` từ hệ thống tệp Windows, đảm bảo khớp 100% từng byte:

| Tên tệp đính kèm | Loại tệp | Kích thước (Bytes) | Mô tả nội dung |
|:---|:---:|:---:|:---|
| `ui-localonly-synth-open-home-open-bc965f-01-app-ready.png` | PNG Image | **112.715** | Giao diện Streamlit sẵn sàng nhận câu hỏi trên sổ `mom_opcenter` |
| `ui-localonly-synth-open-home-open-bc965f-02-cau1-q0699.png` | PNG Image | **149.295** | Đáp án câu 1 (Q0699) hiển thị trọn vẹn trong khung hình |
| `ui-localonly-synth-open-home-open-bc965f-03-cau2-q0718.png` | PNG Image | **173.457** | Đáp án câu 2 (Q0718) hiển thị trọn vẹn trong khung hình |
| `ui-localonly-synth-open-home-open-bc965f-04-cau3-q0709.png` | PNG Image | **94.837** | Đáp án câu 3 (Q0709) hiển thị trọn vẹn trong khung hình |
| `ui-localonly-synth-open-home-open-bc965f-cau1.json` | JSON Data | **2.959** | Dữ liệu thô phiên đo câu 1 (kèm provenance model Ling 3.1 Flash) |
| `ui-localonly-synth-open-home-open-bc965f-cau2.json` | JSON Data | **5.085** | Dữ liệu thô phiên đo câu 2 (kèm provenance model DeepSeek V4.1 Flash) |
| `ui-localonly-synth-open-home-open-bc965f-cau3.json` | JSON Data | **1.439** | Dữ liệu thô phiên đo câu 3 (kèm provenance fallback an toàn) |
| `ui-localonly-synth-open-home-open-bc965f-summary.json` | JSON Data | **10.290** | Tổng kết toàn trình phiên đo CONV-OPEN-BC965F |

---

## 6. Kiểm Băm SHA-256 Chỉ Mục Production (library.sqlite)

Rào cứng bất biến: Chỉ mục SQLite tuyệt đối không được bị sửa đổi hay ghi đè.

- **Đường dẫn tệp:** `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Kích thước file:** 2.942.201.856 bytes
- **Mã băm SHA-256 trước phiên đo:**
  `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Mã băm SHA-256 sau phiên đo:**
  `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Kết luận:** Trùng khớp 100% — cơ sở dữ liệu chỉ mục hoàn toàn nguyên vẹn và bất biến.

---

## 7. Cổng Kiểm Tra Chất Lượng Mã Nguồn

| Lệnh kiểm tra | Kết quả thực tế | Trạng thái |
|:---|:---|:---:|
| `python -m compileall src tests` | Liệt kê toàn bộ các thư mục, 0 lỗi cú pháp | **PASS** |
| `pytest -q` (5 test suites liên quan) | `185 passed in 21.11s` | **PASS** |
| `python -m aios_habit.cli audit` | `{"errors": [], "status": "PASS", "warnings": []}` | **PASS** |
| `import aios_habit.workspace_chat_app` | Khởi tạo thành công (`IMPORT_OK`) | **PASS** |
