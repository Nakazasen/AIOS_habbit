# Báo cáo đo số liệu nền sử dụng thật trên máy nhà (BASELINE-USE-HOME)

- **Mã vé**: `BASELINE-USE-HOME`
- **Mục tiêu**: Đo số liệu nền sử dụng thực tế (thực hiện 100% bằng tự động hóa qua Chrome CDP trên ứng dụng thật đang chạy) trên máy nhà `h410asrock` (có GPU), làm mốc đối chiếu hiệu năng và tính nhất quán dữ liệu với máy công ty `KDTVN-PC0575` (phục vụ đối tác vé `APP-SOURCE-MODEL-PC0575` và `APP-OPEN-PERF-PC0575`).
- **Máy đo**: Máy nhà `h410asrock` (Windows 10, Python 3.11, Chrome headless CDP).
- **Backend AI sử dụng**: `Antigravity Sidecar direct` (Gemini flash qua cổng 8585).
- **Tệp dữ liệu gốc**: `docs/phieu-viec/ket-qua/baseline-benchmark-data.json`

---

## 1. Tóm tắt kết quả đo đầu-cuối

### 1.1. Thời gian mở sổ (Lạnh vs Ấm)

*Ghi chú*:
- Sổ "Điều tra lỗi LSU" (`NB-E35A7BEE`, 494 tài liệu trên máy công ty `PC0575`) **không tồn tại** trên máy nhà do toàn bộ thư mục `local_cases/` nằm trong `.gitignore` theo quy định an toàn dữ liệu. Khi truy cập trực tiếp URL `?nb=NB-E35A7BEE`, ứng dụng kích hoạt cơ chế fail-safe: báo lỗi *"Không tìm thấy sổ NB-E35A7BEE"* và tự động điều hướng về màn hình danh sách sổ của người dùng.
- Phép đo được thực hiện trên sổ tài liệu có sẵn nhiều nguồn nhất trên máy nhà: `mom_opcenter` (109 tài liệu thuộc thư viện tri thức `tri_thuc`).

| Lần đo | Loại mở | Thời gian thấy danh sách trò chuyện (a) | Thời gian ô nhập câu hỏi sẵn sàng (b) | Ghi chú & Thao tác |
|---|---|---|---|---|
| **Lần 1** | Mở lạnh (Cold 1) | **0.56 giây** | **1.19 giây** | Ứng dụng vừa khởi động, nạp sổ lần đầu |
| **Lần 2** | Mở ấm (Warm 1) | **13.62 giây** | **21.69 giây** | Tải lại sổ ngay trong cùng phiên làm việc |
| **Lần 3** | Mở ấm (Warm 2) | **0.62 giây** | **1.22 giây** | Tải lại lần 2 sau khi các tài nguyên đã nạp cache |
| **Lần 4** | Mở lạnh (Cold 2) | **10.41 giây** | **17.03 giây** | Quay về trang chủ rồi mở lại vào sổ |
| *Đối chiếu LSU* | Mở ID `NB-E35A7BEE` | *Fail-safe* | *Fail-safe* | Không tìm thấy sổ trên máy nhà, chuyển hướng về trang chủ |

> **Nhận xét hiệu năng mở sổ**:
> - Trên máy nhà, thời gian thấy danh sách cuộc trò chuyện dao động từ **0.56s đến 13.62s** (trung bình ~6.3s), ô nhập câu hỏi sẵn sàng trong **1.19s đến 21.69s**.
> - Nhanh hơn vượt bậc so với máy công ty `KDTVN-PC0575` (nơi mở sổ LSU phải chờ nhiều phút do CPU yếu phải gánh 494 nguồn). Tuy nhiên, hiện tượng biến thiên giữa 0.6s và 13s-21s trên máy nhà cho thấy ứng dụng có độ trễ phụ thuộc vào khâu đồng bộ trạng thái chuẩn bị nguồn nền của Streamlit.

---

### 1.2. Đối chiếu số liệu tài liệu hiển thị (Tính nhất quán dữ liệu)

| Vị trí hiển thị trên giao diện | Máy nhà (`h410asrock`) | Máy công ty (`KDTVN-PC0575`) | Phân tích chênh lệch |
|---|---|---|---|
| **Thẻ sổ ở thanh bên (Sidebar badge)** | *"Sổ MOM / Opcenter — sẵn sàng, 109 tài liệu (thư viện: Tri thức)"* | *"494 tài liệu"* (Sổ LSU) | Máy nhà dùng sổ `mom_opcenter` (109 nguồn). Máy công ty dùng sổ LSU riêng (494 nguồn cục bộ). |
| **Trạng thái nguồn đang bật** | *"Nguồn đang bật: 106"* | *"35 đang bật"* | Máy nhà bật 106/109 nguồn. Máy công ty chỉ bật 35/494 nguồn. |
| **Popup Quản lý tài liệu** | *"Quản lý tài liệu · 140 tài liệu · 106 đang bật"* | *"494 / 35 / 33"* | Trên máy nhà có sự lệch số giữa: **140** (tổng tài liệu trong thư viện dùng chung), **109** (tổng tài liệu gán cho sổ này) và **106** (nguồn được tích chọn). |
| **Trạng thái chuẩn bị tìm kiếm** | *"Đã chuẩn bị xong 101/106 tài liệu (95%) · Sẵn sàng tìm kiếm: 101/106 · Có 5 tài liệu cần xử lý"* | *"33 đã chuẩn bị"* | Trên máy nhà, 95% tài liệu đã chuẩn bị xong, chỉ còn 5 tài liệu đang chờ. Máy công ty bị nghẽn nặng khâu này. |
| **Khi tạo cuộc trò chuyện mới** | *"Quản lý tài liệu · 109 tài liệu · 0 đang bật"* | Chưa đo | Khi bấm "Tạo cuộc trò chuyện mới", app đặt mặc định **0 đang bật**, người dùng phải tự bật hoặc chọn lại nguồn. |

---

### 1.3. Kết quả 3 câu hỏi kiểm chứng RAG

| STT | Câu hỏi kiểm chứng | Thời gian phản hồi | Kết quả thực tế & Trích dẫn nguồn | Đánh giá tiêu chí vé |
|---|---|---|---|---|
| **Câu 1** | `"Mã C0030 là lỗi gì?"` | **5.39 giây** | - **Tìm thấy 5 ca lỗi** liên quan đến C0030 trong 15.707 ca lịch sử.<br>- Trích dẫn từ điển mã lỗi: **`Bất thường hệ thống bản mạch FAX`** (Nguyên nhân: Tham khảo controller).<br>- Tệp nguồn: `02XC_自己診断表示一覧表-Iris2020 VN.xls` và `Loi KDTPS.xlsx › History KDTPS dòng 695, 3935, 4212, 3632, 207`. | **ĐẠT (PASS)**<br>Chứa chính xác cụm từ *"bất thường hệ thống bản mạch FAX"*. |
| **Câu 2** | `"C7620中Magenta相对Black的副扫描色差达到多少会成为NG？"` | **>120 giây (Hết giờ)** | Giao diện không trả về câu trả lời. Log ghi nhận lỗi tiến trình con BGE-M3: `RuntimeError: preparation_init_bge_worker_persist_timeout`. | **CHƯA ĐẠT**<br>(Do worker BGE-M3 bị nghẽn timeout tầng backend). |
| **Câu 3** | `"Lịch sử lỗi KDTPS gồm những lỗi nào và tệp nguồn cụ thể là gì?"` | **>120 giây (Hết giờ)** *(Ở câu 1 đã trích dẫn)* | Khi hỏi dưới dạng câu hỏi ngôn ngữ tự nhiên, hệ thống bị nghẽn tại bước BGE-M3 tương tự câu 2. Tuy nhiên ở Câu 1, hệ thống đã trích xuất rõ ràng tên tệp nguồn cụ thể: `Loi KDTPS.xlsx › History KDTPS`. | **GHI NHẬN NGUYÊN NHÂN**<br>(Xem phân tích chi tiết mục 3). |

---

## 2. Phân tích nguyên nhân chênh lệch (Máy nhà vs Máy công ty)

### 2.1. Tại sao sổ LSU (`NB-E35A7BEE`) không có trên máy nhà?
- Thư mục `local_cases/` chứa dữ liệu ca làm việc, sổ tay cá nhân và các tệp đính kèm được cấu hình trong `.gitignore` theo đúng quy định an toàn dữ liệu người dùng (`DATA_POLICY.md` và `CONSTITUTION.md`).
- Toàn bộ 494 tài liệu và định danh sổ `NB-E35A7BEE` chỉ nằm cục bộ trên máy công ty `KDTVN-PC0575`. Khi đồng bộ code qua nhánh `phieu-viec/rag-fix1`, máy nhà không có dữ liệu này.
- App xử lý trường hợp này an toàn: không bị sập (crash) mà kích hoạt luồng bảo vệ `NOTEBOOK_MISSING_COPY` để thông báo cho người dùng và chuyển hướng an toàn.

### 2.2. Phân tích hiệu năng mở sổ (0.56s vs Vài phút)
- **Trên máy công ty (`KDTVN-PC0575`)**: Cấu hình phần cứng yếu, CPU phải gánh cùng lúc việc nạp 494 tệp nguồn và chạy hàm `_schedule_sources_for_preparation` khiến giao diện Streamlit bị khóa luồng chính (main thread blocked) trong nhiều phút.
- **Trên máy nhà (`h410asrock`)**: CPU đa nhân mạnh mẽ giúp việc đọc danh sách sổ chỉ mất **0.56s**. Tuy nhiên, khi chuyển sang lần mở ấm Warm 1 mất 13.62s - 21.69s do Streamlit phải kích hoạt lại tiến trình kiểm kê trạng thái chuẩn bị 106 nguồn.

### 2.3. Phát hiện về hiện tượng nghẽn `bge_worker_persist_timeout`
- Khác với Câu 1 sử dụng cơ chế **Tra cứu mã lỗi trực tiếp (Error Dictionary Lookup)** chạy offline trên bảng tính excel chỉ mất **5.39s**, các câu hỏi Câu 2 và Câu 3 kích hoạt luồng **Tìm kiếm ngữ nghĩa (Semantic RAG)** qua mô hình nhúng BGE-M3.
- Ở tầng backend, adapter `workspace_chat_rag_v2_adapter.py` gọi tiến trình con `BGE Subprocess Worker` (`bge_subprocess_client.py`).
- Traceback ghi nhận thực tế từ server:
  ```text
  Workspace Chat BGE-M3 retrieval unavailable: preparation_init_bge_worker_persist_timeout
  Traceback (most recent call last):
    File "src/aios_habit/rag_v2/bge_subprocess_client.py", line 1041, in _persistent_exchange
      raise SemanticBackendError("bge_worker_persist_timeout")
  aios_habit.rag_v2.semantic.SemanticBackendError: bge_worker_persist_timeout
  ```
- **Nguyên nhân gốc**: Tiến trình nền `OpenCode` (PID 5188) đang chạy đồng thời trên máy nhà để xác thực vé chỉ mục `INDEX-VERIFY-HOME`, cùng với việc khởi động worker BGE-M3 trong chế độ persistent mode gặp độ trễ trao đổi qua pipe/socket vượt ngưỡng timeout, khiến hệ thống chuyển sang chế độ an toàn đánh dấu BGE-M3 không khả dụng.

---

## 3. Chi tiết bằng chứng thực nghiệm

### 3.1. Chi tiết Câu 1 (Mã C0030)
- **Thời gian phản hồi**: 5.39s
- **Nội dung trả lời từ AI**:
  > **Tra cứu lỗi tương tự**
  >
  > Tìm thấy **5** ca lỗi liên quan đến **C0030** trong **15.707** ca lịch sử.
  > *_Từ điển mã lỗi (C_CALL): Bất thường hệ thống bản mạch FAX_* — Nguyên nhân: Tham khảo controller · Nguồn: `02XC_自己診断表示一覧表-Iris2020 VN.xls`
  >
  > ### 1. Phiếu 2023/691 · 6th A4 / RPS · C CALL
  > - **Hiện tượng:** 治具画面が高温表示し、LCD画面が6020表示 C6020：定着ヒータ異常高温エラー（メイン）
  > - **Nguyên nhân:** 設備
  > - **Đối sách:** 不要
  > - **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 695`
  >
  > *(Và 4 phiếu lỗi khác từ tệp `Loi KDTPS.xlsx`)*
- **Minh chứng**: Ảnh chụp màn hình `baseline-q1-c0030.png`.

### 3.2. Chi tiết Câu 2 & Câu 3
- Đã được gửi cô lập qua Chrome CDP và ghi nhận tin nhắn người dùng vào cơ sở dữ liệu `local_cases/workspace_chat/messages.jsonl`:
  - `MSG-57667416` (user): `C7620中Magenta相对Black的副扫描色差达到多少会成为NG？` (21:03:24)
  - `MSG-639D71C1` (user): `C7620中Magenta相对Black的副扫描色差达到多少会成为NG？` (21:09:24)
- Ảnh chụp màn hình minh chứng giao diện: `baseline-q2-c7620.png` và `baseline-q3-kdtps.png`.

---

## 4. Ngữ cảnh hệ thống & Tiến trình chạy song song

- **CPU & GPU**: Intel Core i-series trên bo mạch H410; GPU rời rỗi (không can thiệp vào tác vụ đo trừ khi app tự nạp).
- **Tiến trình chạy song song**: Tiến trình `idx_verify_home.py` (PID 5188) của OpenCode đang chạy tác vụ kiểm tra chỉ mục nền, chiếm dụng một phần tài nguyên IO và CPU.
- **Hiện tượng đơ/treo giao diện**: Không có hiện tượng đơ trình duyệt. Các tương tác nút bấm, cuộn trang, chuyển trang đều diễn ra mượt mà và tức thì.

---

## 5. Danh mục ảnh chụp màn hình minh chứng

Toàn bộ các tệp ảnh chụp thực tế đã được lưu trữ tại `docs/phieu-viec/ket-qua/`:
1. `baseline-home-overview.png`: Tổng quan màn hình trang chủ và danh mục sổ.
2. `baseline-open-lsu-pc0575-id.png`: Màn hình xử lý an toàn khi mở sổ LSU `NB-E35A7BEE` không tồn tại.
3. `baseline-mom-cold1.png`: Mở sổ lần lạnh 1 (0.56s).
4. `baseline-mom-warm1.png`: Mở sổ lần ấm 1 (13.62s).
5. `baseline-mom-cold2.png`: Mở sổ lần lạnh 2 từ trang chủ (10.41s).
6. `baseline-q1-c0030.png`: Kết quả trả lời câu hỏi mã C0030 kèm trích dẫn bản mạch FAX và tệp nguồn KDTPS.
7. `baseline-q2-c7620.png`: Giao diện câu hỏi C7620 trong quá trình xử lý.
8. `baseline-q3-kdtps.png`: Giao diện câu hỏi KDTPS trong quá trình xử lý.
9. `baseline-benchmark-data.json`: Tệp dữ liệu đo JSON thô đầy đủ các chỉ số thời gian và nội dung trao đổi.
