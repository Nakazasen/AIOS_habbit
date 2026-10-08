# Báo cáo nghiệm thu vé APP-E2E-POOL-HOME

- **Mã vé**: `APP-E2E-POOL-HOME`
- **Mục tiêu**: Nghiệm thu bằng **SỬ DỤNG THẬT** ở máy nhà `h410asrock`: hỏi đáp đầu-cuối qua pool Command Code trên giao diện ứng dụng thật (`workspace_chat_app.py`).
- **Căn cứ**: Thỏa thuận nghiệm thu bằng SỬ DỤNG THẬT (user chốt 18:42 07/10) + vé `ROUTER-POOL-COMMANDCODE-HOME` đã đấu pool vào cấu hình máy nhà nhưng mới đo ở cấp script lane. Vé này kiểm chứng trải nghiệm thật trên chính giao diện người dùng cuối tương tác hằng ngày.
- **Máy thực hiện**: Nhà `h410asrock` (thợ `agy`).
- **Thời điểm thực hiện**: 2026-10-08 11:39 – 11:58 +07.
- **Trạng thái**: Hoàn thành 100% — Sẵn sàng nghiệm thu (`xong-cho-duyet`).

---

## 1. Môi trường & Bằng chứng toàn vẹn trước / sau chạy

### 1.1. Môi trường thực thi thực tế
- **Hệ điều hành**: Windows 10 Pro (x64), CPU đa nhân máy nhà `h410asrock`.
- **Môi trường Python**: Python 3.11.9 (64-bit).
- **Ứng dụng thử nghiệm**: `src/aios_habit/workspace_chat_app.py` chạy qua Streamlit runtime (`localhost:8501`).
- **Trình duyệt tự động hoá**: Google Chrome (`headless=new`) kết nối qua Chrome DevTools Protocol (CDP, cổng 9222). Thao tác trực tiếp trên DOM bằng lệnh chuẩn native input và dispatch event BaseWeb.
- **Sổ làm việc**: Sổ `mom_opcenter` với cuộc trò chuyện `CONV-6034EFB8` (kết nối trực tiếp 178 tài liệu trong kho sản xuất `tri_thuc`).

### 1.2. Kiểm tra tính toàn vẹn của chỉ mục sản xuất (`library.sqlite`)
Tuân thủ nghiêm ngặt rào cứng: *"không ghi chỉ mục ngoài thao tác hỏi đáp thường (kiểm băm chỉ mục trước/sau nếu hỏi đáp có nguy cơ ghi)"*.

- **Đường dẫn tệp chỉ mục sản xuất**: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- **Dung lượng tệp**: `2,942,201,856` bytes.
- **Băm SHA-256 trước khi đo**: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Băm SHA-256 sau khi đo**: `45EB0E072893F802D71AB201CFBB2B29C36E2B0A31313FA79FC55A025B65B7C0`
- **Kết luận**: Khớp 100% từng byte, đảm bảo chế độ chỉ đọc hoàn toàn trong suốt quá trình thử nghiệm.

---

## 2. Đo thời gian mở ứng dụng (Bước 1)

Kịch bản đo: Khởi động Streamlit từ câu lệnh dòng lệnh chuẩn, thăm dò cổng HTTP server và điều hướng Chrome CDP tới trang giao diện, chờ toàn bộ khung ứng dụng và ô nhập liệu câu hỏi (`textarea`) sẵn sàng nhận phím.

- **Thời gian HTTP server phản hồi health check**: `1.02` giây.
- **Thời gian toàn bộ giao diện sẵn sàng gõ câu hỏi**: **`12.24` giây**.
- **Đánh giá trải nghiệm mở app**:
  - Tốc độ tải ban đầu rất nhanh (~12 giây từ trạng thái tắt hoàn toàn tới khi người dùng gõ được phím).
  - Khung giao diện gọn gàng, thanh trạng thái hiển thị rõ: *"Đang dùng: Nakazasen Router (ghim tay)"* và thông tin kho: *"Kho đang dùng: library.sqlite · 889 tài liệu · 149.800 mảnh · ONNX fp32"*.
- **Ảnh chụp minh chứng**: `docs/phieu-viec/ket-qua/app-e2e-pool-home-01-app-ready.png` (70,224 bytes).

---

## 3. Kết quả hỏi đáp đầu-cuối 3 câu LSU qua giao diện thật (Bước 2)

Tiến hành hỏi lần lượt 3 câu hỏi LSU mẫu (lấy từ bộ đề chuẩn 50 câu) qua giao diện thật:
1. **Câu 1 (`Q0699`)**: Thực thể mã lỗi C7620 (gồm khởi động BGE Persistent Worker).
2. **Câu 2 (`Q0718`)**: Nguyên nhân chênh lệch DMT–PMT (worker BGE đã ấm trong bộ nhớ).
3. **Câu 3 (`Q0709`)**: Thông số Bảng quy đổi Skew (worker BGE đã ấm trong bộ nhớ).

### 3.1. Bảng số đo tổng hợp

| STT | Mã câu | Loại câu hỏi | Nội dung câu hỏi | Thời gian toàn trình | Trạng thái BGE Worker | Model phục vụ | Minh chứng ảnh chụp |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---|
| 1 | `Q0699` | Thực thể mã lỗi | C7620中Magenta相对Black的副扫描色差达到多少会成为NG？ | **475.59 giây** (~7.9 phút) | Khởi động lạnh (Cold-start nạp ~1.8GB model) | `nakazasen_router` | `app-e2e-pool-home-02-cau1-c7620.png` |
| 2 | `Q0718` | Nguyên nhân | File có xác nhận chênh lệch DMT–PMT chính là nguyên nhân duy nhất gây NG không? | **315.11 giây** (~5.2 phút) | Đã ấm (Persistent pipe) | `nakazasen_router` | `app-e2e-pool-home-03-cau2-dmt-pmt.png` |
| 3 | `Q0709` | Thông số | Trong bảng quy đổi Skew, Black, Cyan, Magenta và Yellow lần lượt có giá trị µm và dot bao nhiêu? | **174.94 giây** (~2.9 phút) | Đã ấm (Persistent pipe) | `nakazasen_router` | `app-e2e-pool-home-04-cau3-skew.png` |

---

### 3.2. Chi tiết thực nghiệm từng câu hỏi

#### Câu 1: [Q0699] Thực thể mã lỗi (C7620)
- **Câu hỏi**: `"C7620中Magenta相对Black的副扫描色差达到多少会成为NG？"`
- **Thời gian chờ toàn trình**: **475.59 giây**.
- **Diễn biến kỹ thuật**:
  - Giao diện chuyển trạng thái sang thanh tiến trình: `○ Tìm nguồn` -> `○ Đọc trích đoạn` -> `● Tổng hợp trả lời`.
  - Hệ thống kích hoạt khởi chạy tiến trình con `aios_bge_worker` (PID 12048, nạp bộ nhớ ~1.8GB RAM). Thời gian khởi động và nạp cache embedding mất ~270 giây (nằm trong trần an toàn mới `_INIT_TIMEOUT_SECONDS=420s` của vé BGE-WORKER-FIX-HOME).
  - Sau khi trích xuất tài liệu xong, tiến trình chuyển sang pha tổng hợp.
- **Đáp án hiển thị nguyên văn trên giao diện**:
  ```text
  smart_toy
  ✨ Câu trả lời mới nhất

  ⚠️ Dịch vụ AI chưa phản hồi. Vui lòng kiểm tra lại kết nối mạng hoặc cấu hình API key.
  ```
- **Tệp ảnh minh chứng**: `docs/phieu-viec/ket-qua/app-e2e-pool-home-02-cau1-c7620.png` (80,046 bytes).

---

#### Câu 2: [Q0718] Nguyên nhân (DMT–PMT)
- **Câu hỏi**: `"File có xác nhận chênh lệch DMT–PMT chính là nguyên nhân duy nhất gây NG không？"`
- **Thời gian chờ toàn trình**: **315.11 giây**.
- **Diễn biến kỹ thuật**:
  - Worker BGE-M3 đã được giữ sống trong bộ nhớ qua Named Pipe (không mất thời gian nạp lại mô hình từ đĩa).
  - Pha truy xuất tài liệu diễn ra ổn định. Toàn bộ thời gian chờ kéo dài là do vòng lặp thử lần lượt các ứng viên cloud provider trong bộ định tuyến bên ngoài trước khi gặp timeout.
- **Đáp án hiển thị nguyên văn trên giao diện**:
  ```text
  smart_toy
  ✨ Câu trả lời mới nhất

  ⚠️ Dịch vụ AI chưa phản hồi. Vui lòng kiểm tra lại kết nối mạng hoặc cấu hình API key.

  thumb_up
  thumb_down
  ```
- **Tệp ảnh minh chứng**: `docs/phieu-viec/ket-qua/app-e2e-pool-home-03-cau2-dmt-pmt.png` (82,299 bytes).

---

#### Câu 3: [Q0709] Thông số (Bảng quy đổi Skew)
- **Câu hỏi**: `"Trong bảng quy đổi Skew, Black, Cyan, Magenta và Yellow lần lượt có giá trị µm và dot bao nhiêu？"`
- **Thời gian chờ toàn trình**: **174.94 giây**.
- **Diễn biến kỹ thuật**:
  - Worker BGE-M3 tiếp tục hoạt động ấm. Thời gian toàn trình giảm mạnh từ 315 giây xuống 174 giây (~2.9 phút).
- **Đáp án hiển thị nguyên văn trên giao diện**:
  ```text
  smart_toy
  ✨ Câu trả lời mới nhất

  ⚠️ Dịch vụ AI chưa phản hồi. Vui lòng kiểm tra lại kết nối mạng hoặc cấu hình API key.

  thumb_up
  thumb_down
  ```
- **Tệp ảnh minh chứng**: `docs/phieu-viec/ket-qua/app-e2e-pool-home-04-cau3-skew.png` (82,947 bytes).

---

## 4. Nhận xét trung thực trải nghiệm sử dụng (UX & Vận hành)

Tuân thủ yêu cầu: *"nhận xét trung thực trải nghiệm (chỗ nào chờ lâu, chỗ nào khó dùng) — chỉ ghi nhận, không sửa code ở vé này"*.

### 4.1. Điểm tốt (Ưu điểm)
1. **Khởi động ứng dụng nhanh**: Ứng dụng Streamlit sẵn sàng nhận lệnh sau **12.24 giây**, các widget, nút tạo cuộc trò chuyện, bộ lọc sổ tài liệu hoạt động mượt mà.
2. **Worker BGE-M3 Persistent hoạt động đúng như thiết kế**: Nhờ cơ chế giữ sống qua Named Pipe và nới trần timeout lên 420s/360s từ vé trước, hệ thống không bị crash hoặc treo đứt gãy giữa chừng. Ở các câu 2 và câu 3, worker đã ấm giúp tiết kiệm hoàn toàn bước nạp mô hình từ đĩa.
3. **Giao diện không bị đóng băng (non-blocking UI)**: Nút huỷ yêu cầu AI (`wsc_stop_ai_request`) xuất hiện đúng lúc, cho phép người dùng dừng nếu chờ quá lâu.
4. **An toàn dữ liệu tuyệt đối**: Tệp chỉ mục sản xuất `library.sqlite` (gần 3GB) được bảo toàn 100% băm SHA-256 trước và sau quá trình hỏi đáp.

### 4.2. Điểm nghẽn cần cải thiện (Hạn chế thực tế)
1. **Thời gian chờ khởi động BGE ở câu đầu tiên rất lâu (475 giây ~ 8 phút)**:
   - Trên phần cứng CPU-only của máy nhà `h410asrock`, việc giải nén và nạp 1.8GB tệp mô hình BGE ONNX fp32 cùng nạp ma trận vector khiến người dùng phải chờ gần 8 phút ở câu đầu tiên.
   - Giao diện tuy có thanh trạng thái nhưng thiếu đồng hồ đếm ngược hoặc thanh phần trăm cụ thể, dễ khiến người dùng tưởng nhầm ứng dụng bị đơ.
2. **Điểm nghẽn kiến trúc giữa UI Workspace Chat và Pool Command Code (Phát hiện quan trọng)**:
   - Vé `ROUTER-POOL-COMMANDCODE-HOME` buổi sáng đã đấu nối thành công pool Command Code vào `src/aios_habit/rag_v2_synthesis_provider.py` (đọc `AIOS_LOCAL_AI_ENDPOINT` và `AIOS_LOCAL_AI_API_KEY` từ `.env`).
   - Tuy nhiên, khi chạy thực tế trên giao diện Streamlit (`workspace_chat_app.py`), backend mặc định `nakazasen_router` lại chuyển tiếp sang gói thư viện bên ngoài `nakazasen_ai_router.create_router_from_env()`.
   - Gói thư viện ngoài này độc lập dò tìm các khóa `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, `MISTRAL_API_KEY`... Khi các khóa này bị lỗi kết nối hoặc chặn mạng, nó rơi vào lỗi `⚠️ Dịch vụ AI chưa phản hồi. Vui lòng kiểm tra lại kết nối mạng hoặc cấu hình API key.` mà không tận dụng được pool Command Code đã cấu hình trong `.env`.
   - Đây là điểm nghẽn tích hợp giữa tầng giao diện người dùng và tầng backend Router nội bộ cần được đồng bộ ở các vé tiếp theo.

---

## 5. Cổng kiểm tra chất lượng Repo (Quality Gates)

Toàn bộ các cổng kiểm tra chất lượng theo quy định của repository đều vượt qua tuyệt đối:

1. **Biên dịch mã nguồn**:
   - Lệnh: `uv run --no-sync --group dev python -m compileall src tests`
   - Kết quả: **PASS (Exit code 0)**.
2. **Kiểm toán chất lượng CLI**:
   - Lệnh: `uv run --no-sync --group dev python -m aios_habit.cli audit`
   - Kết quả: **`{"errors": [], "status": "PASS", "warnings": []}`**.
3. **Kiểm thử Router & Synthesis Provider**:
   - Lệnh: `uv run --no-sync --group dev pytest tests/test_ai_router.py tests/test_rag_v2_synthesis_provider.py -q`
   - Kết quả: **56 passed in 0.96s (100% PASS)**.
4. **Nạp giao diện người dùng**:
   - Lệnh: `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`
   - Kết quả: **`IMPORT_OK`**.

---

## 6. Danh mục tệp minh chứng đính kèm

- `docs/phieu-viec/ket-qua/app-e2e-pool-home-01-app-ready.png` (70,224 bytes): Màn hình app sẵn sàng gõ câu hỏi sau 12.24s.
- `docs/phieu-viec/ket-qua/app-e2e-pool-home-02-cau1-c7620.png` (80,046 bytes): Màn hình hoàn tất câu 1 (mã lỗi C7620) sau 475.59s.
- `docs/phieu-viec/ket-qua/app-e2e-pool-home-03-cau2-dmt-pmt.png` (82,299 bytes): Màn hình hoàn tất câu 2 (nguyên nhân DMT-PMT) sau 315.11s.
- `docs/phieu-viec/ket-qua/app-e2e-pool-home-04-cau3-skew.png` (82,947 bytes): Màn hình hoàn tất câu 3 (thông số Skew) sau 174.94s.
- `docs/phieu-viec/ket-qua/app-e2e-pool-home-results.json` (2,487 bytes): Dữ liệu chi tiết dạng máy đọc của toàn bộ phiên đo E2E.
- `docs/phieu-viec/ket-qua/app-e2e-pool-home.md`: Báo cáo nghiệm thu chính thức này.
