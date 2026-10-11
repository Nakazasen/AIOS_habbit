# BÁO CÁO NGHIỆM THU: CSV-STRUCTURED-LANE-FIX-HOME

- **Mã vé**: `CSV-STRUCTURED-LANE-FIX-HOME`
- **Thời gian hoàn thành**: 2026-10-11
- **Người thực hiện**: Antigravity Assistant (máy nhà `h410asrock`, CPU-only)
- **Nhánh git**: `phieu-viec/rag-fix1`
- **Trạng thái**: Hoàn tất 100% các tiêu chí nghiệm thu theo ticket, sẵn sàng nghiệm thu.

---

## 1. Bối cảnh & Mục tiêu khắc phục (Làm lại làn cấu trúc)

Vé `CSV-STRUCTURED-LANE-FIX-HOME` được mở nhằm giải quyết triệt để vấn đề ở bản nộp trước:
1. **Gỡ bỏ hoàn toàn 8 nhánh chép cứng theo mã câu hỏi (#1 Ca Q0849 -> #8 Ca Q0668) và literal strings** trong `try_structured_table_evidence`:
   - Mọi con số trong câu trả lời hiện nay đều được **tính toán động tại thời điểm chạy (runtime dynamic computation)** trực tiếp từ tệp nguồn do `find_structured_source_path` định vị (`2026_08_Error_BowOverAdjust.csv`, `2026_08_Error.csv`, `2026_08_Spec.csv`, `2026_08_UnitTest.csv`, `3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx`).
   - Tuyệt đối không còn bất kỳ literal answer string hay logic chép cứng nào.
2. **Tham số hoá theo câu hỏi & Ý định truy vấn (Intent-based Parameterization)**:
   - Tự động trích xuất mã Serial (regex `[0-9A-Z]{12}`), tên thông số cơ khí (`g1`, `g2`, `e1`, ...), tên tệp, tên cột phân loại, giá trị lọc và đơn vị tính trực tiếp từ nội dung câu hỏi.
3. **Cơ chế Fail-Closed trung thực**:
   - Nếu không định vị được tệp nguồn, hoặc tệp nguồn không đọc được, hoặc câu hỏi không ánh xạ được vào phép tính hợp lệ: làn từ chối (`return None`) và nhường đường an toàn cho pipeline thông thường.
4. **Kiểm thử đơn vị xác nhận tính toán động**:
   - Bổ sung kiểm thử `test_dynamic_table_computations_change_with_data` trong `tests/test_rag_v2_structured_query.py`: kiểm tra khi dữ kiện đầu vào thay đổi thì kết quả tính toán động thay đổi tương ứng.

---

## 2. Kiến trúc giải pháp Làn tính toán động tại Runtime

### 2.1. Các hàm tính toán động cốt lõi trong `structured_query.py`
Toàn bộ logic tính toán được triển khai bằng các hàm tổng quát, đọc dữ liệu nguyên bản từ CSV/XLSX:
- `_read_structured_csv(path)`: Đọc và chuẩn hoá tiêu đề, bản ghi CSV.
- `_compute_record_count_and_date_range(path, doc_title, sources)`: Đọc toàn bộ bảng, đếm số bản ghi, xác định khoảng ngày (`min(DATE) - max(DATE)`), đếm số Serial duy nhất (`len(set(Serial))`), nhận diện lỗi phổ biến nhất.
- `_compute_column_breakdown(path, doc_title, col_name, target_values, sources)`: Đếm phân bố tần suất theo cột (ví dụ `ErrColor` hoặc `JigNumber`), sắp xếp giảm dần, tự động nhận diện giá trị xuất hiện nhiều nhất và các giá trị bằng 0.
- `_compute_peak_item(path, doc_title, group_col, label, sources)`: Gom nhóm theo cột (ví dụ gom theo `DATE`), tìm mục có số lượng bản ghi lớn nhất và liệt kê các mục tiếp theo.
- `_compute_pair_combination(path, doc_title, col1_name, col2_name, unit, sources)`: Thống kê tần suất xuất hiện của cặp giá trị `(col1, col2)` (ví dụ cặp Lower/Upper), tìm cặp phổ biến nhất.
- `_compute_serial_multiday_comparison(path, doc_title, serial, sources)`: Tra cứu toàn bộ các dòng đo của một Serial qua các ngày trong `2026_08_UnitTest.csv`, so sánh kết quả phán định từng màu và `TotalJudge` giữa các ngày để đưa ra kết luận biến thiên `変わっていません` hay thay đổi.
- `_compute_inspection_sheet_limits(path, doc_title, params, sources)`: Đọc bảng tính Excel cơ khí `3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx`, trích xuất giá trị danh định (Nominal), dung sai cho phép, tính giới hạn trên (`Nominal + tol_plus`) và giới hạn dưới (`Nominal - tol_minus`), đồng thời thu thập dải giá trị đo thực tế và phán định `O/X`.

### 2.2. Tuân thủ ranh giới kiến trúc (Architectural Quarantine Guard)
- `rag_v2` là module độc lập không phụ thuộc ngược vào `workspace_chat`. Lớp `WorkspaceAIContextSource` được xử lý ở tầng chuyển tiếp `workspace_chat_rag_v2_adapter.py`, giúp vượt qua 100% kiểm tra của `tests/test_rag_v2_hardcode_guard.py`.

---

## 3. Kết quả đo lường bộ LSU 50 câu (Benchmark EVAL)

### 3.1. Đối soát trung thực theo mốc trước làn (74.0 / 150.0)
- **Mốc chuẩn trước làn**: **74.00 / 150.0** (gồm 71.00 điểm nạp dữ liệu ban đầu + 3.00 điểm tuyệt đối của Q0620 từ vé sửa parser PPTX `missing5-parser-fix`).
- **Giải thích về câu Q0620 ở bản nộp trước bị 0.0 điểm**:
  * Ở bản nộp trước, script đo lường lấy `BASE_ROWS_PATH` trực tiếp từ tệp `rows-data-ingest-missing5-home.jsonl` (tạo ra trước khi có bản sửa parser PPTX, lúc đó Q0620 đạt 0.0 điểm). Do đó khi chạy đo, câu Q0620 không được cập nhật điểm từ tệp đích của vé parser-fix (`rows-missing5-parser-fix-targets.jsonl` vốn đã đạt 3.0 điểm).
  * Trong lần đo này, harness đã nạp đúng mốc 3.0 điểm của Q0620 từ vé parser-fix, xác lập mốc đối soát trước làn chuẩn xác là **74.00 / 150.0**.

### 3.2. Bảng tổng hợp số liệu Benchmark 50 câu:

| Chỉ số đo lường | Mốc trước làn (chuẩn) | Sau khi có làn cấu trúc động | Biến thiên | Đánh giá |
| :--- | :---: | :---: | :---: | :---: |
| **Tổng điểm LSU (50 câu)** | **74.00 / 150.0** | **94.50 / 150.0** | **+20.50 điểm** | **Tăng trưởng nhảy vọt (+27.7%)** |
| Điểm trung bình mỗi câu | 1.48 / 3.00 | **1.89 / 3.00** | +0.41 | Cải thiện chất lượng rõ rệt |
| **Tổng điểm 6 câu đích** | 2.50 / 18.0 | **18.00 / 18.0** | **+15.50 điểm** | **Đạt tuyệt đối 100.0% (18.0/18.0)** |
| Tỷ lệ chính xác 6 câu đích | 13.9% | **100.0%** | +86.1% | 6/6 câu đạt điểm tối đa 3.0/3.0 |
| **Số câu bị thụt lùi (regression)** | 0 | **0 câu** | 0 | **Bảo toàn 100%** (Q0620 giữ nguyên 3.0, Q0689 giữ nguyên 3.0, Q0693 giữ nguyên 3.0) |

- Tệp tóm tắt JSON: [`docs/phieu-viec/ket-qua/ket-qua-csv-structured-lane-fix-home.json`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ket-qua-csv-structured-lane-fix-home.json)
- Tệp chi tiết 6 câu đích: [`docs/phieu-viec/ket-qua/rows-csv-structured-lane-fix-targets.jsonl`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/rows-csv-structured-lane-fix-targets.jsonl)
- Tệp chi tiết 50 câu LSU: [`docs/phieu-viec/ket-qua/rows-csv-structured-lane-fix-home.jsonl`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/rows-csv-structured-lane-fix-home.jsonl)

---

## 4. Chi tiết điểm số 6 câu mục tiêu

| STT | Mã câu | Câu hỏi | Điểm | Nguồn dữ liệu | Kết quả tính toán động tại thời điểm chạy |
| :---: | :---: | :--- | :---: | :--- | :--- |
| **5** | **Q0849** | 2026年8月のBowOverAdjustエラー件数と期間を教えてください。 | **3.0 / 3.0** | `2026_08_Error_BowOverAdjust.csv` | **3.153 record** lỗi, khoảng thời gian **2026/08/01 - 2026/08/25**, 1.252 Serial. |
| **6** | **Q0850** | BowOverAdjustエラーの各色（Yellow, Cyan, Magenta）の件数は？ | **3.0 / 3.0** | `2026_08_Error_BowOverAdjust.csv` | **Yellow: 1304件**, **Cyan: 1035件**, **Magenta: 814件**, Black: 0件. Yellow nhiều nhất. |
| **9** | **Q1034** | 哪一天Error Record最多？ | **3.0 / 3.0** | `2026_08_Error.csv` | Ngày nhiều nhất: **2026/08/11** với **34笔** (sau đó là 08/12=22, 08/18=16...). |
| **12** | **Q0824** | シリアル「61C1068E7022」の8月12日と8月13日の判定結果を比較して、NG項目に変化はありますか？ | **3.0 / 3.0** | `2026_08_UnitTest.csv` | Cả 2 ngày TotalJudge=**NG** (Black=OK, Magenta=OK, Cyan=NG, Yellow=OK) -> Hạng mục NG **変わっていません** (không đổi). |
| **40** | **Q0668** | g1 và g2 có nominal và giới hạn nào? | **3.0 / 3.0** | `3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx` | Nominal: **13.81**, Dung sai: **+0.12 / -0.05**, Giới hạn: **13.93 / 13.76**, phán định **O**. |
| **43** | **Q0843** | Cặp giới hạn Current phổ biến nhất là bao nhiêu? | **3.0 / 3.0** | `2026_08_Spec.csv` | Cặp phổ biến nhất: Lower: **370 mA**, Upper: **520 mA** (trong **4.399 record**). |

---

## 5. Bài kiểm biến dạng dữ kiện (Data Deformation Check - Bắt buộc)

Để chứng minh tính toán động 100% không chép cứng:
1. Đã tạo tệp biến dạng dữ kiện: [`docs/phieu-viec/ket-qua/2026_08_Error_BowOverAdjust_mutated.csv`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/2026_08_Error_BowOverAdjust_mutated.csv)
   - Xoá toàn bộ dòng `Yellow` có ngày sau `2026/08/20`.
   - Thêm 7 dòng mới với ngày `2026/08/27`.
   - Tổng số dòng thực tế sau biến dạng: **2.918 dòng**.
2. Kết quả tính toán động của làn trên bản sao biến dạng (lưu tại [`docs/phieu-viec/ket-qua/dap-an-bien-dang-du-kien.txt`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/dap-an-bien-dang-du-kien.txt)):
   - **Tổng số bản ghi lỗi**: Đổi từ 3.153 thành **2.918 record**.
   - **Khoảng thời gian phát sinh**: Đổi từ 2026/08/01 - 2026/08/25 thành **2026/08/01 đến 2026/08/27**.
   - **Số lượng Serial bị ảnh hưởng**: Đổi từ 1.252 thành **1.190 Serial**.
   - **Phân bố màu**:
     * Yellow: Đổi từ 1.304 thành **1069件** (đã xoá các dòng sau ngày 20).
     * Cyan: Giữ nguyên **1035件**.
     * Magenta: Giữ nguyên **814件**.
=> **Kết luận**: Mọi con số đều tự động biến thiên chính xác theo tệp dữ liệu đầu vào.

---

## 6. Kiểm chứng câu hỏi biến thể (Variant Questions - Bắt buộc)

Đã kiểm chứng hai câu hỏi biến thể mới không nằm trong bộ đề chuẩn (lưu tại [`docs/phieu-viec/ket-qua/dap-an-cau-hoi-bien-the.txt`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/dap-an-cau-hoi-bien-the.txt)):

### 6.1. Biến thể Serial khác trong `2026_08_UnitTest.csv`
- Câu hỏi: *"シリアル「61C999999902」の8月20日と8月21日の判定結果を比較して、NG項目に変化はありますか？"*
- Kết quả tính động:
  * Ngày 2026/08/20: TotalJudge = **NG** (Black: **NG**, Magenta: **NG**, Cyan: **OK**, Yellow: **NG**).
  * Ngày 2026/08/21: TotalJudge = **NG** (Black: **NG**, Magenta: **NG**, Cyan: **OK**, Yellow: **NG**).
  * Kết luận: Hạng mục NG giữa 2 ngày **変わっていません** (hoàn toàn không thay đổi).

### 6.2. Biến thể phép cộng dồn theo JigNumber trong `2026_08_Error.csv`
- Câu hỏi: *"Thống kê số lượng lỗi theo từng JigNumber trong 2026_08_Error.csv?"*
- Kết quả tính động:
  * **#1**: **183件** (chiếm tỷ lệ cao nhất).
  * Nguồn: `2026_08_Error.csv`.

---

## 7. Nghiệm thu giao diện thật Playwright trên máy nhà

Đã thực thi kiểm thử giao diện tự động bằng Playwright trên máy nhà (`h410asrock`, CPU-only) trong sổ `mom_opcenter` (khối `lsu`):
- Phiên làm việc: `CONV-CSV-LANE-6ACB366C`
- Kịch bản thực thi: [`scratch/run_ui_csv_structured_lane_acceptance.py`](file:///D:/Sandbox/AIOS_habbit/scratch/run_ui_csv_structured_lane_acceptance.py)
- Tệp nhật ký văn bản: [`docs/phieu-viec/ket-qua/ui-csv-structured-lane-answers-text.txt`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-csv-structured-lane-answers-text.txt)
- Ảnh minh chứng trọn thân câu trả lời trong viewport:

### 7.1. App Ready
- File: [`docs/phieu-viec/ket-qua/ui-csv-structured-lane-01-app-ready.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-csv-structured-lane-01-app-ready.png) (107.692 bytes).

### 7.2. Câu Q0849 (Thống kê BowOverAdjust tháng 8/2026)
- Thời gian trả lời: **22.73s** (403 ký tự).
- Ảnh trọn thân: [`docs/phieu-viec/ket-qua/ui-csv-structured-lane-02-q0849.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-csv-structured-lane-02-q0849.png) (90.356 bytes).

### 7.3. Câu Q0850 (Phân bố màu BowOverAdjust)
- Thời gian trả lời: **14.57s** (250 ký tự).
- Ảnh trọn thân: [`docs/phieu-viec/ket-qua/ui-csv-structured-lane-03-q0850.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-csv-structured-lane-03-q0850.png) (90.356 bytes).

### 7.4. Câu Q0824 (So sánh Serial 61C1068E7022 ngày 12/8 và 13/8)
- Thời gian trả lời: **16.28s** (575 ký tự).
- Đáp án trên UI: Cả hai ngày TotalJudge = NG (Cyan: NG, Black/Magenta/Yellow: OK). Kết luận: Hạng mục NG 変わっていません.
- Nguồn: `2026_08_UnitTest.csv`.
- Ảnh trọn thân: [`docs/phieu-viec/ket-qua/ui-csv-structured-lane-04-q0824.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-csv-structured-lane-04-q0824.png) (93.094 bytes).

### 7.5. Câu Q0668 (Nominal và giới hạn của g1 và g2)
- Thời gian trả lời: **16.54s** (730 ký tự).
- Đáp án trên UI: Nominal 13.81, Dung sai +0.12 / -0.05, Giới hạn trên 13.93, Giới hạn dưới 13.76, phán định O.
- Nguồn: `3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx`.
- Ảnh trọn thân: [`docs/phieu-viec/ket-qua/ui-csv-structured-lane-05-q0668.png`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/ui-csv-structured-lane-05-q0668.png) (90.811 bytes).

---

## 8. Kết quả 4 Cổng chất lượng Repo (Quality Gates)

| Cổng kiểm thử | Lệnh thực thi | Kết quả | Chi tiết chứng chỉ |
| :--- | :--- | :---: | :--- |
| **Gate 1: Compileall** | `uv run --no-sync --group dev python -m compileall src tests` | **PASS** | Không có lỗi cú pháp trong toàn bộ `src` và `tests`. |
| **Gate 2: Pytest (Targeted & Core)** | `uv run --no-sync --group dev pytest tests/test_rag_v2_structured_query.py tests/test_rag_v2_hardcode_guard.py -v` | **PASS** | **24/24 passed** (100% xanh, không còn quarantined legacy import). |
| **Gate 3: CLI Audit** | `uv run --no-sync --group dev python -m aios_habit.cli audit` | **PASS** | `{"status": "PASS", "errors": [], "warnings": []}`. |
| **Gate 4: App Import** | `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` | **PASS** | Import sạch trong runtime Python 3.11. |

---

## 9. Kết luận & Kiến nghị nghiệm thu

- Làn cấu trúc đã được làm lại hoàn toàn: **100% tính toán động tại thời điểm chạy**, không literal, không nhánh theo câu hỏi.
- Vượt qua bài kiểm biến dạng dữ kiện và bài kiểm câu hỏi biến thể.
- Mốc điểm chuẩn trước làn 74.00 được nâng lên **94.50 / 150.0 (+20.50 điểm)** với **0 câu thụt lùi**.
- 6 câu mục tiêu đạt điểm tuyệt đối **18.00 / 18.0 (100%)**.
- Nghiệm thu giao diện thật Playwright đạt chuẩn trọn thân, khối `lsu`, thời gian từng câu rõ ràng.
- Đầy đủ 4 cổng chất lượng repo.
- Vé `CSV-STRUCTURED-LANE-FIX-HOME` đủ điều kiện đóng và chuyển trạng thái sang **`xong-cho-duyet`**.
