# BÁO CÁO NGHIỆM THU: STRUCTURED-LANE-TEST-FIXTURE-HOME
## CHUYỂN CÁC BÀI KIỂM LÀN CẤU TRÚC SANG DỮ KIỆN TỔNG HỢP TỰ CHỨA

---

### 1. Thông tin tổng quan
- **Mã vé:** `STRUCTURED-LANE-TEST-FIXTURE-HOME` (Liên kết vé desktop: `DESKTOP-STRUCTURED-LANE-TEST-FIXTURE-HOME`)
- **Tên nhiệm vụ:** Chuyển các bài kiểm của làn cấu trúc sang dữ kiện tổng hợp tự chứa, giữ nguyên ý nghĩa kiểm tra và khả năng chạy độc lập trên môi trường sạch / CI / PC0575.
- **Thời điểm hoàn thành:** `2026-10-12T16:55:00+07:00` (UTC: `2026-10-12T09:55:00Z`)
- **Trạng thái:** `HOAN_THANH`
- **Máy thực hiện:** `May nha - h410asrock`
- **Kho nguồn mã ứng dụng:** `D:\Sandbox\AIOS_habbit` (nhánh `phieu-viec/rag-fix1`)
- **Commit chứa mã nguồn và bài kiểm của vé:** `8498fed93d0c46c9d19bd3c891ff3b5a6ee65418` (nằm trong dải commit chữ chạy `592b49db..7fe20c93`).

---

### 2. Khai báo cấu hình hiệu lực theo biên bản BB-CONFIG-PARITY-01
- **Phần cứng:**
  - **CPU:** Intel Core i3-10100 (4 nhân / 8 luồng, 3.60 GHz)
  - **RAM:** 16 GB DDR4
  - **GPU:** NVIDIA GeForce GTX 1060 3GB
  - **Chế độ phân bổ tài nguyên:** **Chỉ-CPU (CPU-only)** theo quy định của biên bản `BB-CONFIG-PARITY-01`.
  - **Hệ điều hành:** Windows 10 Pro x64.
- **Môi trường Python:** Python 3.11.14 (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`).
- **Cờ môi trường:** `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `KMP_DUPLICATE_LIB_OK=TRUE`, `AIOS_RAG_V2_NUMPY_DENSE=1`.

---

### 3. Phân tích bối cảnh và tách bạch commit trong dải `592b49db..7fe20c93`
- **Hiện tượng gốc:** Trước khi chuyển đổi, bài kiểm `test_structured_table_lane_targets` trong `tests/test_rag_v2_structured_query.py` gọi hàm `try_structured_table_evidence(question)` không truyền `custom_source_path`, do đó phụ thuộc vào các tệp production staging thật trên máy tại `local_runs/structured_staging/` (`2026_08_Error_BowOverAdjust.csv`, `2026_08_Error.csv`, `2026_08_Spec.csv`, `2026_08_UnitTest.csv`, `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx`). Khi chạy trên máy sạch/CI hoặc PC0575 không có dữ kiện thật, test bị rớt (fail-closed đúng thiết kế nhưng gây trượt cổng kiểm thử).
- **Tách bạch commit trong dải `592b49db..7fe20c93`:**
  - `592b49db`: Mốc xếp hàng trước khi thực hiện vé.
  - `8498fed93d0c46c9d19bd3c891ff3b5a6ee65418`: **Commit duy nhất chứa mã của vé này**. Khi thợ agy commit tính năng streaming SSE, toàn bộ phần sửa đổi làn cấu trúc (`src/aios_habit/rag_v2/structured_query.py`) và chuyển đổi test fixture (`tests/test_rag_v2_structured_query.py`) đã được hoàn thành và đưa vào cây git trong commit này.
  - Các commit tiếp theo (`35f4c6c9`, `000d5626`, `7fe20c93`): Chỉ chỉnh sửa stdout logging markers và bộ mã hóa UTF-8 an toàn cho streaming trong `src/aios_habit/workspace_chat_app.py`, hoàn toàn không chạm vào `rag_v2/structured_query.py` hay tệp test.

---

### 4. Chi tiết triển khai kỹ thuật & Danh mục dữ kiện tổng hợp

#### 4.1. Hàm tạo dữ kiện tổng hợp tự chứa (`_create_synthetic_structured_fixtures`)
Được tạo trong thư mục tạm `tmp_path`, hoàn toàn độc lập với hệ thống tệp bên ngoài:
1. **`synthetic_bowoveradjust.csv`** (20 dòng dữ liệu):
   - Phạm vi ngày: `2026/08/01` đến `2026/08/25`.
   - Phân bố màu lỗi: Yellow: 10, Cyan: 6, Magenta: 4, Black: 0.
2. **`synthetic_error.csv`** (8 dòng dữ liệu):
   - Phân bố theo ngày: `2026/08/11` (5 lỗi - ngày cao điểm) và `2026/08/12` (3 lỗi).
   - Thiết bị: JigNumber `#1`, 4 số serial duy nhất.
3. **`synthetic_spec.csv`** (6 dòng dữ liệu):
   - Cặp giá trị: 4 bản ghi `Lower = 370 mA, Upper = 520 mA`; 2 bản ghi `Lower = 350 mA, Upper = 500 mA`.
4. **`synthetic_unittest.csv`** (2 dòng dữ liệu):
   - Serial `61C1068E7022` qua 2 ngày `2026/08/12` và `2026/08/13`. Cả hai ngày đều có kết quả `TotalJudge = NG`, `Judge:Cyan = NG`, `Judge:Black = OK`.
5. **`synthetic_inspection.xlsx`** (Bảng tính Excel sheet `18.08.2026`):
   - Mount LD block cho `g1` và `g2`: Nominal `13.81`, Dung sai `+0.12 -0.05`, Giới hạn trên `13.93`, Giới hạn dưới `13.76`, Phán định kết quả `O`.

#### 4.2. Chuyển đổi các bài kiểm thử
1. **`test_structured_table_lane_targets(tmp_path)`**:
   - Chuyển 8 ca kiểm thử sang gọi `try_structured_table_evidence(question, custom_source_path=fixtures[key])`.
   - Bảo toàn 100% các khẳng định về từ khóa kết quả tính toán, đếm bản ghi, phân bố giá trị và trích dẫn nguồn tài liệu.
2. **`test_dynamic_table_computations_change_with_data(tmp_path)`**:
   - Khẳng định ít nhất một ca "đổi dữ kiện thì kết quả đổi theo" trên toàn bộ 5 nhóm hành vi:
     - **Hành vi 1 (Đếm bản ghi, khoảng ngày, phân bố màu):** Ban đầu 4 record (Yellow 2, Cyan 1, Magenta 1, Black 0); sau khi thêm dữ liệu tăng lên 10 record (Magenta 6, Yellow 2, Black 1).
     - **Hành vi 2 (Ngày đông nhất & Tổng thống kê):** Ban đầu cao điểm `2026/08/11` (2筆, tổng 3); sau khi thêm 5 lỗi ngày `2026/08/15` chuyển thành cao điểm `2026/08/15` (5筆, tổng 8).
     - **Hành vi 3 (Tra serial đa ngày):** Ban đầu giữ nguyên NG ("変わっていません"); sau khi sửa dữ liệu ngày 2 thành OK, kết quả nhận biết thay đổi ("có sự thay đổi").
     - **Hành vi 4 (Cặp giới hạn Lower/Upper phổ biến nhất):** Ban đầu là `370 mA / 520 mA` (3 record); sau khi thêm 5 record của `400 mA / 600 mA`, kết quả đổi thành `400 mA / 600 mA` (5 record).
     - **Hành vi 5 (Nominal và giới hạn đo bảng kiểm):** Ban đầu nominal `13.81` (giới hạn `13.93 / 13.76`); sau khi đổi sang nominal `15.50` (dung sai `+0.20 / -0.10`), kết quả đổi tương ứng `15.5 / 15.7 / 15.4`.
3. **`test_structured_table_lane_clean_machine_simulation(monkeypatch, tmp_path)`**:
   - Sử dụng `monkeypatch` giả lập `find_structured_source_path` luôn trả về `None` (môi trường CI hoàn toàn sạch).
   - Kiểm chứng thiết kế fail-closed: Khi không có dữ liệu thật và không truyền `custom_source_path`, hàm trả về `None` an toàn.
   - Khi truyền dữ kiện tổng hợp qua `custom_source_path`, test chạy đạt tất định 100%.

---

### 5. Bằng chứng kiểm thử trong môi trường sạch không có dữ liệu thật
- **Phương pháp kiểm chứng:** Tạm thời đổi tên thư mục dữ liệu thật `D:\Sandbox\AIOS_habbit\local_runs\structured_staging` thành `structured_staging_TEMP_HIDDEN`, chạy toàn bộ bộ kiểm thử `tests/test_rag_v2_structured_query.py`, sau đó hoàn nguyên tên thư mục.
- **Kết quả:**
  ```text
  tests/test_rag_v2_structured_query.py ........................ [100%]
  ============================= 24 passed in 0.58s ==============================
  ```
  Bộ kiểm thử đạt 100% (24/24 passed), hoàn toàn độc lập với tệp dữ liệu trên đĩa.

---

### 6. Kết quả 4 Cổng chất lượng của repo
1. **Cổng 1 (`compileall`):**
   - Lệnh: `python -m compileall src tests`
   - Kết quả: **PASS (Exit code 0)** — toàn bộ tệp nguồn và test biên dịch sạch.
2. **Cổng 2 (`cli audit`):**
   - Lệnh: `python -m aios_habit.cli audit`
   - Kết quả: **PASS** (`{"errors": [], "status": "PASS", "warnings": []}`).
3. **Cổng 3 (`import app`):**
   - Lệnh: `python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`
   - Kết quả: **`IMPORT_OK`**.
4. **Cổng 4 (`pytest`):**
   - Lệnh: `pytest tests/test_rag_v2_structured_query.py -v`
   - Kết quả: **24/24 PASS (100%)** trong `0.71s`.

---

### 7. Kết luận
Vé `STRUCTURED-LANE-TEST-FIXTURE-HOME` đã hoàn thành trọn vẹn mọi tiêu chí: chuyển đổi toàn bộ bài kiểm sang dữ kiện tổng hợp tự chứa, giữ nguyên độ phủ hành vi, kiểm chứng đầy đủ cơ chế tính toán động khi đổi dữ liệu, và vượt qua toàn bộ 4 cổng chất lượng của repo.
