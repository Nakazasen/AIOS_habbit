Model thực hiện: Gemini 3.1 Pro (Thinking Level: High)

Da doc ghi chu bo sung 04:02 va ap dung cong nghiem thu bo sung.

# BÁO CÁO NGHIỆM THU VÉ `DESKTOP-HOME-MACHINE-SERIAL-DATE-FILTER`

- **Mã vé:** `DESKTOP-HOME-MACHINE-SERIAL-DATE-FILTER`
- **Máy đích:** Máy nhà (`H410ASROCK`)
- **Trạng thái:** `HOAN_THANH`
- **Xác nhận bắt buộc (Ghi chú bổ sung 04:02 & 04:07):** `Da doc ghi chu bo sung 04:02 va ap dung cong nghiem thu bo sung.`

---

## 1. Tóm tắt hạng mục đã triển khai

### 1.1. Bộ nhận diện thực thể (Entity Recognizer) phủ toàn bộ `machine_type` thật trong DB
- **Tên máy (`machine_type`):**
  - Triển khai hàm `_load_db_machine_registry(conn)` và `extract_machine_entities(text, conn)` trong [`src/aios_habit/chat_action_error_lookup.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/chat_action_error_lookup.py).
  - Tập nhận diện tên máy được dựng **trực tiếp từ truy vấn `SELECT DISTINCT TRIM(machine_type) FROM error_cases WHERE machine_type IS NOT NULL AND TRIM(machine_type) <> ''`** trên CSDL chuẩn `C:\tmp\kdtps_standard\error_cases_reconciled.db`, phủ toàn bộ **65 giá trị `machine_type` phân biệt** trong 30.075 ca lịch sử (`Iris`, `Iris2020`, `Iris2024`, `6thNext` / `6th Next`, `Virgo`, `Libra2` / `Libra 2`, `Sirius2` / `Sirius 2`, `Polaris Next`, `Caelum`, `Aries`, `Taurus`, `Leo`, ` Pegasus`, v.v.).
  - Hỗ trợ chuẩn hóa khoảng trắng (`REPLACE(machine_type, ' ', '')`) và chữ hoa/thường khi so khớp: gõ `Libra2` hay `Libra 2` đều khớp trọn 483 ca; gõ `Sirius2` hay `Sirius 2` đều khớp trọn 1.231 ca; gõ `6thNext` hay `6th Next` đều khớp trọn 1.068 ca; gõ `Iris` khớp họ máy Iris (6.961 ca).
- **Mẫu Serial (`raw_json['G']`):**
  - Triển khai hàm `extract_serial_entities(text)` nhận diện chuỗi chữ-số đặc trưng của số máy/serial KDTPS (ví dụ `WD72Z12772`, `3V2XM1930`, `110C0Y3NL0`, `H564624943`), loại trừ mã lỗi (`C7620`, `JAM4212`, `F000`) và tên model máy để không nhận diện nhầm.
- **Khoảng thời gian (`occurred_at`):**
  - Triển khai hàm `extract_date_entities(text)` nhận diện:
    1. Khoảng từ ngày đến ngày (`từ 2024-01-01 đến 2024-06-30`, `tu 01/01/2024 den 30/06/2024`)
    2. Ngày cụ thể (`2023-01-05`, `05/01/2023`)
    3. Tháng/năm (`tháng 5/2024`, `05/2024`, `2024-05`)
    4. Năm (`năm 2025`, `trong 2025`)

### 1.2. Bộ lọc cấu trúc SQL trên DB 30.075 ca & Định tuyến giao diện thật
- Cập nhật `_candidate_rows()` và `search_similar()` trong [`src/aios_habit/chat_action_error_lookup.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/chat_action_error_lookup.py):
  - Áp dụng điều kiện lọc cấu trúc SQL (`machine_type`, `json_extract(ec.raw_json, '$.G')`, `occurred_at`) kết hợp `AND` với điều kiện mã lỗi (`error_code_c` / `error_code_i`) hoặc từ khóa hiện tượng khi câu hỏi chứa cả hai.
  - Khi câu hỏi chỉ có bộ lọc máy / serial / ngày (hoặc mã lỗi kèm bộ lọc), hệ thống loại bỏ các từ nối (`các`, `ca`, `của`, `máy`, `dòng`, `serial`, `năm`...) và thực thể đã nhận diện khỏi danh sách từ khóa tự do để không làm lệch tập kết quả, đồng thời trả về **tổng số ca khớp chính xác (`COUNT(*)`)** và tuyên bố rõ bộ lọc đang áp dụng ở đầu câu trả lời.
- Nối thông luồng giao diện thật (`Sổ Điều tra lỗi` — `NB-LAZY-DTL`) trong [`src/aios_habit/final_answer_composer.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/final_answer_composer.py) và [`src/aios_habit/workspace_chat_app.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_app.py) (`_run_chat_turn_async`) để mọi câu hỏi tra cứu mã lỗi hoặc lọc theo máy/serial/ngày trong `Sổ Điều tra lỗi` truy vấn trực tiếp CSDL 30.075 ca mà không bị chỉ mục tài liệu chung làm nhiễu.

### 1.3. Dòng thông tin Máy / Serial / Ngày phát sinh trên thẻ tóm tắt ca lỗi
- Cập nhật `_case_dict()` và `_render_cards()` / `_render_synthesized_answer()` trong [`src/aios_habit/chat_action_error_lookup.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/chat_action_error_lookup.py):
  - Trích xuất chính xác `serial` từ `raw_json['G']` (cột G của bản đồ A-Y trong `error_cases_reconciled.db`, hoặc `'không ghi'` nếu ca đó không ghi serial) và `occurred_at` từ cột `occurred_at` (fallback `raw_json['C']`).
  - Hiển thị đúng 1 dòng chuẩn trên mọi thẻ ca lỗi:
    `- **Máy:** <machine_type> | **Serial:** <serial, hoặc 'không ghi'> | **Ngày phát sinh:** <occurred_at>`
  - Khớp 100% nguyên văn với bản ghi mở trong panel **"Xem hồ sơ gốc"** (`citation_source_viewer.py`).

### 1.4. Chỉ mục biểu thức (Expression Index) tối ưu tốc độ truy vấn Serial
- Đã thêm chỉ mục biểu thức `idx_error_cases_machine_serial` trên `C:\tmp\kdtps_standard\error_cases_reconciled.db`:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_error_cases_machine_serial
  ON error_cases(machine_type, json_extract(raw_json, '$.G'));
  ```
- **Hiệu quả đo thực tế:** Thời gian truy vấn theo serial giảm từ **140,79 ms** xuống **7,84 ms** (nhanh hơn **17,9 lần**).
- **Bảo toàn dữ liệu tuyệt đối:** Không sửa, không xóa, không thêm bất kỳ dòng dữ liệu nào (`SELECT COUNT(*) FROM error_cases` giữ nguyên `30.075` dòng).

### 1.5. Vòng lặp cải thiện liên tục (Continuous Improvement Logging)
- Triển khai hàm `log_filter_event()` trong [`src/aios_habit/chat_action_error_lookup.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/chat_action_error_lookup.py) ghi sự kiện mỗi lần bộ lọc cấu trúc được kích hoạt vào tệp `D:\Sandbox\AIOS_habbit\local_cases\machine_serial_date_filter_events.jsonl` (gồm `timestamp`, `question`, `entities`, `matched_count`, `sample_no_dvd`, `conversation_id`).

---

## 2. Bảng đối chiếu kết quả trên Giao diện thật với Số nền SQL độc lập

| STT | Câu hỏi thử nghiệm trên giao diện thật (`Sổ Điều tra lỗi`) | Thực thể nhận diện | Số ca trả về trên Giao diện | Số đếm SQL độc lập trên DB 30.075 ca | Đối chiếu chi tiết & Kết luận |
| :--- | :--- | :--- | :---: | :---: | :---: |
| 1 | `cac ca cua may Iris` | `machine: Iris` (họ máy Iris) | **6.961 ca** | **6.961 ca** (`machine_type LIKE '%Iris%'`) | Mọi ca hiển thị đều thuộc họ Iris (`Iris2020 下位`, `Iris2020 上位`...). **KHỚP 100%** |
| 2 | `cac ca cua may 6thNext` / `cac ca cua may 6th Next` | `machine: 6thNext` (chuẩn hóa khoảng trắng) | **1.068 ca** | **1.068 ca** (`REPLACE(machine_type,' ','') LIKE '%6thNext%'`) | Gồm cả `6thNext` (193 ca) và `6th Next` (862 ca) + biến thể. **KHỚP 100%** |
| 3 | `cac ca cua may Virgo` *(Dòng máy ngoài 2 ví dụ - #1)* | `machine: Virgo` | **3.182 ca** | **3.182 ca** (`REPLACE(machine_type,' ','') LIKE '%Virgo%'`) | Mọi ca hiển thị đều thuộc dòng máy `Virgo` (`Phiếu 2024/1241`, `2024/1099`, `2024/136`...). **KHỚP 100%** |
| 4 | `cac ca cua may Libra2` *(Dòng máy ngoài 2 ví dụ - #2)* | `machine: Libra 2` | **483 ca** | **483 ca** (`REPLACE(machine_type,' ','') LIKE '%Libra2%'`) | Mọi ca hiển thị đều thuộc dòng máy `Libra2` / `Libra 2` (`Phiếu 2026/1277`, `2026/4313`...). **KHỚP 100%** |
| 5 | `cac ca cua may Sirius2` *(Dòng máy ngoài 2 ví dụ - #3)* | `machine: Sirius 2` | **1.231 ca** | **1.231 ca** (`REPLACE(machine_type,' ','') LIKE '%Sirius2%'`) | Mọi ca hiển thị đều thuộc dòng máy `Sirius2` / `Sirius 2`. **KHỚP 100%** |
| 6 | `cac ca cua may Polaris Next` *(Dòng máy ngoài 2 ví dụ - #4)* | `machine: Polaris Next` | **1.174 ca** | **1.174 ca** (`REPLACE(machine_type,' ','') LIKE '%PolarisNext%'`) | Mọi ca hiển thị đều thuộc dòng máy `Polaris Next`. **KHỚP 100%** |
| 7 | `serial WD72Z12772` | `serial: WD72Z12772` | **1 ca** | **1 ca** (`json_extract(raw_json,'$.G') LIKE '%WD72Z12772%'`) | Trả đúng duy nhất **Phiếu 2023/1**, Máy `6th Next`, Serial `110C0Y3NL0 WD72Z12772`, Ngày `2023-01-05`, dòng 5. Khớp tuyệt đối với panel "Xem hồ sơ gốc". **KHỚP 100%** |
| 8 | `C7620 nam 2025` | `codes: ['C7620']`, `date_range: năm 2025` | **60 ca** | **60 ca** (`error_code='C7620' AND occurred_at LIKE '2025%'`) | Mọi ca hiển thị đều có mã lỗi `C7620` và `occurred_at` trong năm `2025` (`2025-06-30`, `2025-12-05`, `2025-12-04`, `2025-08-14`). **KHỚP 100%** |
| 9 | `C6770`, `C7620`, `JAM4212` (Hỏi thường không kèm lọc) | `codes: ['C6770']` / `['C7620']` / `['JAM4212']` | **33 ca** (`C6770`), **85 ca** (`C7620`), **63 ca** (`JAM4212`) | **33 / 85 / 63 ca** | Giữ nguyên hoàn toàn hành vi tra cứu từ điển + ca lịch sử trước vé này, bổ sung thêm dòng `Máy | Serial | Ngày phát sinh` trên từng thẻ. **ĐẠT** |

---

## 3. Bằng chứng ảnh chụp Giao diện thật (Playwright Chromium Headless)

Tất cả ảnh nghiệm thu dưới đây được chụp trực tiếp từ giao diện Streamlit thật (`http://127.0.0.1:52820/?nb=NB-LAZY-DTL`) bằng kịch bản `scripts/verify_machine_serial_date_filter.py` và lưu tại `D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\`:

| STT | Tên tệp ảnh | Dung lượng (bytes) | Mã băm SHA-256 (tính từ đúng tệp nộp) | Nội dung hiển thị trong ảnh |
| :---: | :--- | :---: | :--- | :--- |
| 1 | `anh-filter-01-may-iris.png` | `243149` | `136CBADD84BB46CE49508610A3D8A0BEF3EF12D1CEC4A16E09F6F1DA975BA4BD` | Hỏi `"cac ca cua may Iris"`: Hiển thị rõ thông báo đang lọc theo dòng máy **Iris (họ máy Iris)**, tổng số **6.961 ca** phù hợp, và danh sách thẻ ca lỗi có dòng `Máy: Iris2020 下位 | Serial: ... | Ngày phát sinh: ...`. |
| 2 | `anh-filter-02-serial-wd72z12772.png` | `212856` | `21B0BEBC0A9070F688CAB6EBAF2C683D24F2426B61FADBBB198A7599A134F8F8` | Hỏi `"serial WD72Z12772"`: Trả đúng **1 ca** (**Phiếu 2023/1**, `Máy: 6th Next | Serial: 110C0Y3NL0 WD72Z12772 | Ngày phát sinh: 2023-01-05`) kèm mở trực tiếp panel **"Hồ sơ ca điều tra lịch sử: Phiếu 2023/1 (Dòng 5)"** đối chiếu khớp 100% nguyên văn. |
| 3 | `anh-filter-03-ma-loi-c7620-nam-2025.png` | `223436` | `80056D37D0D2105F403FDB25DC3ECE8EC6CAC89BD649163B69166F401CB55184` | Hỏi `"C7620 nam 2025"`: Hiển thị rõ đang lọc theo **năm 2025, mã lỗi C7620**, tìm thấy đúng **60 ca**, toàn bộ các ca hiển thị đều có ngày phát sinh trong năm `2025` (`2025-06-30`, `2025-12-05`, `2025-12-04`, `2025-08-14`). |
| 4 | `anh-filter-04-may-virgo.png` | `240729` | `8B71B4B5AAD96D39B013C0EA246D0C84AA09C60CC6FB176F513F2F71375E4D8D` | Hỏi `"cac ca cua may Virgo"` (dòng máy ngoài 2 ví dụ): Hiển thị rõ đang lọc theo dòng máy **Virgo**, tìm thấy đúng **3.182 ca**, mọi thẻ ca đều thuộc máy `Virgo` kèm Serial và Ngày phát sinh. |
| 5 | `anh-filter-05-may-libra2.png` | `235379` | `AB1B132F08ECA2151129BBDC4AED38A4FD9DCFB119C3236CD7F7F7D41D94356C` | Hỏi `"cac ca cua may Libra2"` (dòng máy thứ 2 ngoài 2 ví dụ): Hiển thị rõ đang lọc theo dòng máy **Libra 2**, tìm thấy đúng **483 ca**, mọi thẻ ca đều thuộc máy `Libra2` kèm Serial và Ngày phát sinh. |

---

## 4. Kết quả chạy kiểm thử tự động trên Python 3.11.14 của máy nhà

Chạy trực tiếp trên môi trường ảo Python 3.11.14 (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`):
- Bộ kiểm thử mới [`tests/test_machine_serial_date_filter.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_machine_serial_date_filter.py): **9/9 PASS** (kiểm tra độ phủ toàn bộ 65 `machine_type` trong DB, lọc `Iris`, `6thNext`, `Virgo`, `Libra2`, `Sirius2`, lọc serial `WD72Z12772`, lọc `C7620 nam 2025`, dòng `Máy | Serial | Ngày phát sinh` trên thẻ, không hồi quy `C6770`/`C7620`/`JAM4212`, và ghi log `local_cases/machine_serial_date_filter_events.jsonl`).
- Các bộ kiểm thử hồi quy liên quan (`test_chat_action_error_lookup.py`, `test_error_code_chat_route_fix.py`, `test_citation_source_viewer.py`): **42/42 PASS (0 lỗi)**.

```json
{
  "ma_ve": "DESKTOP-HOME-MACHINE-SERIAL-DATE-FILTER",
  "trang_thai": "HOAN_THANH",
  "xac_nhan_bo_sung_0402": "Da doc ghi chu bo sung 04:02 va ap dung cong nghiem thu bo sung.",
  "model_thuc_hien": "Gemini 3.1 Pro (Thinking Level: High)",
  "ket_qua_chinh": {
    "distinct_machine_types_loaded": 65,
    "iris_family_cases": 6961,
    "6thnext_normalized_cases": 1068,
    "virgo_cases": 3182,
    "libra2_cases": 483,
    "sirius2_cases": 1231,
    "polaris_next_cases": 1174,
    "serial_wd72z12772_cases": 1,
    "c7620_year_2025_cases": 60,
    "expression_index_added": "idx_error_cases_machine_serial",
    "continuous_improvement_log": "local_cases/machine_serial_date_filter_events.jsonl"
  },
  "anh_nghiem_thu": [
    {
      "ten_tep": "anh-filter-01-may-iris.png",
      "dung_luong_bytes": 243149,
      "sha256": "136CBADD84BB46CE49508610A3D8A0BEF3EF12D1CEC4A16E09F6F1DA975BA4BD"
    },
    {
      "ten_tep": "anh-filter-02-serial-wd72z12772.png",
      "dung_luong_bytes": 212856,
      "sha256": "21B0BEBC0A9070F688CAB6EBAF2C683D24F2426B61FADBBB198A7599A134F8F8"
    },
    {
      "ten_tep": "anh-filter-03-ma-loi-c7620-nam-2025.png",
      "dung_luong_bytes": 223436,
      "sha256": "80056D37D0D2105F403FDB25DC3ECE8EC6CAC89BD649163B69166F401CB55184"
    },
    {
      "ten_tep": "anh-filter-04-may-virgo.png",
      "dung_luong_bytes": 240729,
      "sha256": "8B71B4B5AAD96D39B013C0EA246D0C84AA09C60CC6FB176F513F2F71375E4D8D"
    },
    {
      "ten_tep": "anh-filter-05-may-libra2.png",
      "dung_luong_bytes": 235379,
      "sha256": "AB1B132F08ECA2151129BBDC4AED38A4FD9DCFB119C3236CD7F7F7D41D94356C"
    }
  ]
}
```
