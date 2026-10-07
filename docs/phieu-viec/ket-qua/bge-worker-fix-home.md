# Báo cáo nghiệm thu vé BGE-WORKER-FIX-HOME

- **Mã vé**: `BGE-WORKER-FIX-HOME`
- **Mục tiêu**: Sửa timeout khởi động tiến trình con BGE Worker và thiết kế cơ chế tự phục hồi sau lỗi khởi động trên máy nhà (`h410asrock`), đảm bảo chức năng tìm kiếm ngữ nghĩa (Semantic RAG) hoạt động ổn định và nghiệm thu DÙNG THẬT trên ứng dụng.
- **Máy thực hiện**: `h410asrock` (Windows 10, Python 3.11, CPU đa nhân).
- **Căn cứ kỹ thuật**: Báo cáo chẩn đoán `docs/phieu-viec/ket-qua/bge-worker-diag-home.md` (Muse verdict ĐẠT ngày 07/10/2026).
- **Trạng thái**: Hoàn thành 100% — Sẵn sàng nghiệm thu (`xong-cho-duyet`).

---

## 1. Tóm tắt giải pháp kỹ thuật đã triển khai

### 1.1. Nới trần timeout khởi động worker theo số đo thực tế
Dựa trên kết quả đo đạc phân rã thời gian khởi động worker ONNX fp32 trên CPU tại báo cáo chẩn đoán (tổng thời gian nạp mô hình và preload cache dao động từ 245.8s đến 302.2s):
- **Trong `src/aios_habit/rag_v2/bge_subprocess_client.py`**:
  - Nâng `_INIT_TIMEOUT_SECONDS`: từ `300.0` lên **`420.0`** giây (dư dôi an toàn ~118s so với mức đỉnh 302s).
  - Nâng `_PERSIST_SPAWN_WAIT_SECONDS`: từ `120.0` lên **`360.0`** giây (đảm bảo client không ngắt pipe trước khi worker nạp xong mô hình 188s–214s).
  - Bổ sung comment chỉ dẫn kỹ thuật dẫn chứng số đo chẩn đoán 246–302s để ngăn ngừa việc hạ trần tùy tiện sau này.
- **Trong `RUN_AIOS_WORKSPACE_CHAT.bat`**:
  - Cập nhật biến môi trường: `set "AIOS_BGE_INIT_TIMEOUT=420"`.

### 1.2. Cơ chế tự phục hồi (Self-Healing) chống độc phiên hỏi đáp
Ở phiên bản cũ, khi worker BGE gặp timeout khởi động, cờ `_last_failure_reason` bị ghim vĩnh viễn trong client khiến toàn bộ các câu hỏi tiếp theo bị chặn fail-fast trong 0.01s.
- **Trong `src/aios_habit/rag_v2/bge_subprocess_client.py`**:
  - Bổ sung hàm `clear_failure_reason()` cho phép xóa cờ lỗi khi phát hiện lỗi quá hạn tạm thời.
- **Trong `src/aios_habit/workspace_chat_rag_v2_adapter.py`**:
  - Bổ sung các mã lỗi khởi động/quá hạn worker (`preparation_init_bge_worker_persist_timeout`, `bge_worker_persist_timeout`, `bge_worker_init_timeout`) vào danh mục lỗi có thể thử lại `_RETRYABLE_PREPARATION_ERRORS`.
  - Khi bắt gặp lỗi timeout khởi động trong quá trình chuẩn bị hoặc truy vấn, adapter tự động gọi `_SUBPROCESS_CLIENT.clear_failure_reason()` và đặt trạng thái nguồn về cho phép kích hoạt lại ở lượt hỏi tiếp theo thay vì khóa chết toàn bộ phiên.
  - Vẫn giữ nguyên cơ chế báo lỗi rõ ràng, minh bạch cho lượt đang chạy (không treo im lặng, không bịa đặt nội dung).

---

## 2. Kết quả kiểm thử tự động & Cổng chất lượng Repo

### 2.1. Bộ unit test mới (`tests/test_bge_worker_self_healing.py`)
Đã xây dựng bộ test tự động kiểm thử toàn diện các yêu cầu kỹ thuật mới:
- `test_timeout_constants_match_ticket_requirement`: Xác thực chính xác giá trị `_INIT_TIMEOUT_SECONDS == 420.0` và `_PERSIST_SPAWN_WAIT_SECONDS == 360.0`.
- `test_clear_failure_reason_allows_retry`: Xác thực việc xóa cờ `_last_failure_reason` khôi phục khả năng khởi động của client.
- `test_worker_self_healing_retry_flow`: Giả lập worker thất bại lần 1 do timeout -> tự phục hồi -> lần 2 khởi động thành công và phục vụ truy vấn bình thường.
- `test_adapter_retries_on_transient_worker_timeout`: Xác thực adapter phân loại chính xác lỗi timeout là lỗi thử lại được (`retryable`).
- `test_non_retryable_errors_still_fail`: Đảm bảo các lỗi nghiêm trọng (hỏng tệp mô hình, sai định dạng) vẫn kích hoạt fail-safe đúng quy chuẩn an toàn.

**Kết quả test mới**: `5/5 passed` (100% PASS).

### 2.2. Kiểm tra hồi quy bộ test hiện hữu
- Suite `tests/test_bge_subprocess_worker.py`: `12/12 passed`.
- Tổng cộng các test suite liên quan đến RAG v2 và Adapter: `98/98 passed` (không phát sinh bất kỳ hồi quy nào).

### 2.3. Cổng kiểm chứng bắt buộc của Repository
- **Xác nhận môi trường**: Python 3.11.9 (64-bit).
- **Biên dịch mã nguồn**:
  `uv run --no-sync --group dev python -m compileall src tests` -> **PASS** (100% tệp biên dịch sạch).
- **Kiểm toán chất lượng CLI**:
  `uv run --no-sync --group dev python -m aios_habit.cli audit` -> **`{"status": "PASS"}`**.
- **Kiểm tra nạp ứng dụng**:
  `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"` -> **`IMPORT_OK`**.

---

## 3. Kết quả nghiệm thu DÙNG THẬT trên máy nhà (`h410asrock`)

Tiến hành nghiệm thu sử dụng thật theo đúng kịch bản người dùng cuối với sổ `mom_opcenter` (106 nguồn tri thức đang bật), kết nối trực tiếp với tiến trình con BGE Subprocess Worker persistent và cầu nối Antigravity Sidecar trên cổng 8585.

### 3.1. Lượt hỏi 1 (Turn 1): Câu hỏi ngữ nghĩa C7620
- **Câu hỏi**:
  `"C7620中Magenta相对Black的副扫描色差达到多少会成为NG？"`
  *(Trong dòng C7620, sai lệch màu theo phương quét phụ của Magenta so với Black đạt bao nhiêu thì thành NG?)*
- **Hành vi thực tế**:
  1. Ứng dụng kích hoạt khởi động BGE Persistent Worker (`models/bge-m3-onnx-fp32`). Nhờ trần timeout mới 420s/360s, tiến trình con khởi động thành công, tạo Named Pipe `\\.\pipe\aios_bge_worker_...` và giữ sống trong bộ nhớ.
  2. BGE RAG v2 trích xuất chính xác **3 đoạn tài liệu cốt lõi** từ tệp `Sirius 2 _ C7620_報告版 4.pptx` (`wsc-3862a76468aee5575cd502c5`):
     - Đoạn 1: *"...色補正後に、Bkに対する副走査方向の色差値が 70dot 以上 発生 LINE ： C23/24..."*
     - Đoạn 2: *"...BOWSKEW 治具で Bk と光路高さの差分 ... 上限 70 Dot に対して、C7620 エラーが発生しないための余裕範囲は約 5.9Dot..."*
     - Đoạn 3: *"...色補正後に、Bkに対する副走査方向の色差値が 70dot 以内なら OK..."*
  3. Trợ lý AIOS WorkLens tổng hợp câu trả lời chính xác, mạch lạc:
     > *"Theo tài liệu đính kèm, trong dòng máy C7620, nếu giá trị sai lệch màu theo phương quét phụ (副走査方向の色差値) của Magenta so với Black đạt từ **70dot trở lên** (vượt quá giới hạn 70Dot) thì sẽ trở thành NG và phát sinh lỗi C7620 [1], [2].*
     >
     > *Chi tiết các thông số kỹ thuật được xác định:*
     > - *Mức tiêu chuẩn: Sau khi hiệu chỉnh màu, nếu sai lệch màu Magenta so với Bk nằm trong 70dot trở xuống thì OK [3].*
     > - *Ngưỡng lỗi NG: Khi giá trị này đạt từ 70dot trở lên (vượt ngưỡng trần 70Dot), lỗi C7620 sẽ xảy ra [1], [2].*
     > - *Biên độ an toàn: Máy thông thường lệch 64.09 dot, biên độ dự phòng đạt 5.9 dot so với trần 70 dot [2].*
     >
     > *Nguồn trích dẫn: Sirius 2 _ C7620_報告版 4.pptx (Trang 2 & Trang 3)."*
- **Đánh giá tiêu chí**: **ĐẠT 100%** (khởi động 1 lần thành công, có câu trả lời chính xác ngưỡng **70 dot**).
- **Minh chứng hình ảnh**: `docs/phieu-viec/ket-qua/bge-worker-fix-c7620.png`.

---

### 3.2. Lượt hỏi 2 (Turn 2): Câu hỏi ngữ nghĩa tiếp theo (Lỗi KDTPS)
- **Câu hỏi**:
  `"Lịch sử lỗi KDTPS gồm những lỗi nào và tệp nguồn cụ thể là gì?"`
- **Hành vi thực tế**:
  1. Do worker BGE-M3 đã được giữ sống trong persistent mode, hệ thống **không phải khởi động lại mô hình** (không tốn 246s–302s).
  2. Thời gian phản hồi hoàn tất cực nhanh: **15.25 giây** (thay vì bị treo >120s timeout như ở baseline).
  3. BGE RAG v2 trích xuất chính xác 4 đoạn tài liệu liên quan đến lịch sử lỗi trạm và bảng mã lỗi.
  4. Trợ lý AIOS WorkLens trả lời đầy đủ:
     - Nêu rõ các lỗi cụ thể: Lỗi ngắt kết nối điều khiển trạm 0 (mã -1306), lỗi nhiệt độ/mạch sấy (C6000, C6020), lỗi quang học LSU (C7620, C6400).
     - Trích dẫn cụ thể tên 2 tệp nguồn: `Loi KDTPS.xlsx › History KDTPS` và `Log điều tra (nghi ngờ, chưa chẩn đoán)`.
- **Đánh giá tiêu chí**: **ĐẠT 100%** (truy vấn nhanh tức thì, worker giữ sống hoàn hảo, trích dẫn đúng tệp nguồn).
- **Minh chứng hình ảnh**: `docs/phieu-viec/ket-qua/bge-worker-fix-kdtps.png`.

---

## 4. Bảng đối chiếu hiệu quả trước và sau khi sửa lỗi

| Chỉ số / Tiêu chí | Trước khi sửa (`BASELINE-USE-HOME`) | Sau khi sửa (`BGE-WORKER-FIX-HOME`) | Kết luận |
|---|---|---|---|
| **Trần `_INIT_TIMEOUT_SECONDS`** | `300.0s` (hẹp, bị tràn 2.2s khi máy bận) | **`420.0s`** (dư dôi an toàn 118s) | Giải quyết dứt điểm timeout khởi động |
| **Trần `_PERSIST_SPAWN_WAIT_SECONDS`** | `120.0s` (nhỏ hơn thời gian nạp model 188s) | **`360.0s`** (lớn hơn toàn bộ pha init) | Khắc phục lỗi client bỏ cuộc sớm |
| **Cơ chế khi worker timeout** | Ghim cờ lỗi vĩnh viễn, độc phiên (fail-fast 0.01s) | **Tự phục hồi (`clear_failure_reason`)**, cho phép thử lại ở lượt sau | Hết hiện tượng độc phiên hỏi đáp |
| **Lượt 1: Câu hỏi C7620** | **CHƯA ĐẠT** (>120s timeout, không có đáp án) | **ĐẠT** (khởi động thành công, trả lời đúng ngưỡng **70 dot**) | Đạt tiêu chí nghiệm thu cốt lõi |
| **Lượt 2: Câu hỏi KDTPS** | **CHƯA ĐẠT** (fail-fast hoặc timeout >120s) | **ĐẠT** (hoàn tất trong **15.25s**, trích dẫn tệp nguồn) | Tái sử dụng worker sống mượt mà |
| **Bằng chứng hình ảnh** | Chỉ có ảnh ô nhập câu hỏi bị nghẽn | Đầy đủ 2 ảnh giao diện trả lời chi tiết và thẻ trạng thái xanh | Đầy đủ bằng chứng thực tế |

---

## 5. Xác nhận tuân thủ rào cứng

- [x] Không đổi backend, không đổi mô hình, không ghi index sản xuất.
- [x] Không can thiệp vào `src/aios_habit/rag_v2/index.py` hoặc `pipeline.py`.
- [x] Toàn bộ mã nguồn mới có type hints, xử lý lỗi chặt chẽ, không có placeholder (`TODO`, `pass`).
- [x] Cổng chất lượng repo: Python 3.11, compileall PASS, 103 test PASS, `cli audit` PASS, import app sạch sẽ.
- [x] Không merge vào nhánh `main`.
