# Model: Gemini 2.5 Flash | Thinking: High

# BÁO CÁO THỰC THI VÉ DESKTOP-HOME-BAREQUERY-DICT-CLEANUP

- **Mã vé:** `DESKTOP-HOME-BAREQUERY-DICT-CLEANUP`
- **Trạng thái thực thi:** **HOÀN THÀNH**
- **Máy đích thực thi:** Máy nhà (`H410ASROCK`), Windows 10
- **Môi trường Python:** Python `3.11.14` (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`)
- **Model thực thi:** `Gemini 2.5 Flash | Thinking: High`
- **Thời điểm đóng phiên thật:** `2026-10-23T01:25:00+07:00`
- **Kho mã nguồn:** `D:\Sandbox\AIOS_habbit` (nhánh `phieu-viec/rag-fix1`)
- **Kho điều phối kết quả:** `D:\Sandbox\aios-dieu-phoi-desktop` (nhánh `main`)

---

## 1. BỐI CẢNH VÀ NGUYÊN NHÂN GỐC (ROOT CAUSE ANALYSIS)

### 1.1. Hiện tượng phát hiện từ ảnh r1-1 (2026-10-23)
Khi người dùng gõ câu thô `"Tra cứu mã lỗi JAM4212"` (đường bare query / tra cứu trực tiếp theo mã lỗi), đoạn tóm tắt từ điển ở đầu câu trả lời xuất hiện các lỗi sau:
1. Chứa tiếng Nhật nguyên văn chưa được dịch: `定着センサー滞留(カセット2給紙)` và `中間巻き付き検知センサーOFFから規定時間経過しても定着センサーをOFFしない`.
2. Bị **lặp nguyên đoạn 2 lần liên tiếp**:
   > `_Từ điển mã lỗi (JAM): 定着センサー滞留(カセット2給紙)_ — Nguyên nhân: 中間巻き付き検知センサーOFFから規定時間経過しても定着センサーをOFFしない · Nguồn: 02XC_機能定義書_JAM一覧 (1).xls`
   lặp lại y hệt một lần nữa ngay bên dưới.
3. Trong khi đó, đường tra cứu tương tự (câu hỏi tự nhiên: `"Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?"`) đã dịch sạch sẽ 100% đoạn định nghĩa này sang tiếng Việt (như đã kiểm chứng ở ảnh `r2-2`).

### 1.2. Phân tích nguyên nhân gốc trong mã nguồn
1. **Đoạn tóm tắt lấy từ đâu:**
   Đoạn tóm tắt được truy vấn từ bảng SQLite `error_glossary` thông qua hàm `lookup_glossary(conn, codes)` trong tệp `src/aios_habit/chat_action_error_lookup.py`.
2. **Vì sao bị lặp 2 lần:**
   Hàm `extract_codes("Tra cứu mã lỗi JAM4212")` trích xuất và chuẩn hóa mã lỗi thành danh sách gồm 2 phần tử: `['JAM4212', 'J4212']` (nhằm mục đích mở rộng khả năng so khớp linh hoạt với cả 2 định dạng mã trong CSDL). Khi gọi `lookup_glossary(conn, ['JAM4212', 'J4212'])`, cả 2 mã này đều trỏ về cùng một bản ghi duy nhất trong bảng `error_glossary` (bản ghi ID `1715`, mã `4212`, họ `JAM`).
   Trong hàm `_render_cards()`, vòng lặp `for code in codes:` lặp qua từng mã và append dòng `gloss` vào `lines` mà **không hề có cơ chế kiểm tra khử lặp (deduplication)** theo bản ghi từ điển đã xử lý. Do đó, cùng một nội dung tóm tắt bị render và nối vào văn bản 2 lần.
3. **Vì sao còn nguyên tiếng Nhật thô chưa dịch:**
   - Trong hàm `_render_cards()`, các trường `meaning` (`name_ja`), `cause`, `remedy` được lấy nguyên văn từ từ điển mà không gọi qua hàm chuyển ngữ `translate_kdtps_field()`.
   - Đồng thời, chuỗi tóm tắt lại ghép chung `· Nguồn: 02XC_... .xls` vào cuối cùng một dòng Markdown. Khi văn bản đi qua bộ lọc làm sạch ngôn ngữ `purify_markdown_text()`, bộ lọc thấy đuôi mở rộng `.xls` trên dòng nên coi toàn bộ dòng này là định danh tệp (`giu-dinh-danh`), dẫn tới việc các đoạn tiếng Nhật thô trong `meaning` và `cause` được giữ nguyên vẹn mà không được dịch sang tiếng Việt.
   - Ngược lại, ở đường tra cứu tự nhiên (`_render_synthesized_answer`), các trường được dịch riêng lẻ từng trường bằng `translate_kdtps_field` và tên tệp nguồn được tách riêng ở dòng `- **Tài liệu tham chiếu:**`, nên đường tự nhiên đạt độ thuần Việt 100%.

---

## 2. PHƯƠNG ÁN VÀ THỰC THI (ĐÚNG LUẬT TRIỂN KHAI NGANG)

Tuân thủ nghiêm ngặt **Luật triển khai ngang** (tái sử dụng tối đa cơ chế có sẵn, không viết cơ chế mới):
1. **Tái sử dụng cơ chế dịch sẵn có:**
   Nhập và sử dụng trực tiếp hàm `translate_kdtps_field` và `has_japanese` từ module `aios_habit.answer_language_policy`:
   - Dịch trường tên/hiện tượng: `translate_kdtps_field(raw_meaning, field_name="error_name")` -> ra tiếng Việt: `"Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)"`.
   - Dịch trường nguyên nhân/cơ chế: `translate_kdtps_field(raw_cause, field_name="cause")` -> ra tiếng Việt: `"Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt (OFF) nhưng cảm biến sấy vẫn chưa ngắt (OFF)"`.
   - Dịch trường đối sách: `translate_kdtps_field(raw_remedy, field_name="remedy")`.
2. **Khử lặp triệt để (Deduplication):**
   Thiết lập tập theo dõi `seen_entries = set()`. Với mỗi mã trong `codes`, xác định khóa định danh của bản ghi từ điển:
   `entry_key = entry.get("id") or (entry.get("code_family"), entry.get("code")) or code`
   Nếu `entry_key in seen_entries`: lập tức bỏ qua (`continue`). Nhờ đó, dù `codes` có cả `JAM4212` và `J4212`, đoạn tóm tắt từ điển chỉ xuất hiện **đúng 1 lần duy nhất**.
3. **Cơ chế Fallback an toàn (Fail-closed & Language Purity):**
   Nếu một mục từ điển sau khi dịch vẫn còn chứa ký tự tiếng Nhật thô (`has_japanese(meaning) == True`), hệ thống sẽ loại bỏ hoàn toàn đoạn tiếng Nhật thô đó khỏi thân câu trả lời để tránh ô nhiễm ngôn ngữ, và chỉ giữ lại dòng tham chiếu định danh tệp nguồn: `_Nguồn tham chiếu từ điển mã lỗi: {source}_`.
4. **Bảo toàn số liệu và cấu trúc câu trả lời:**
   Giữ nguyên 100% dòng đếm tổng số trung thực:
   `Tìm thấy **24** ca mã lỗi **JAM4212. J4212** trong **30.075** ca lịch sử (hiển thị 5 ca liên quan nhất):`
   Giữ nguyên danh sách 5 ca điều tra chi tiết bên dưới kèm đầy đủ nhãn Vụ, mã máy, số serial, ngày phát sinh, nguyên nhân và đối sách đã chuẩn hóa.

---

## 3. TỆP VÀ HÀM ĐÃ SỬA ĐỔI

1. **`src/aios_habit/chat_action_error_lookup.py`**:
   - Hàm sửa đổi: `_render_cards()`.
   - Bổ sung `seen_entries` để khử lặp đoạn tóm tắt từ điển.
   - Gọi `translate_kdtps_field` cho các trường `name`, `cause`, `remedy`.
   - Kiểm tra `has_japanese` để loại bỏ tiếng Nhật thô nếu chưa có bản dịch.
2. **`tests/test_barequery_dict_cleanup.py`**:
   - Tệp kiểm thử tự động mới viết bằng Python 3.11.
   - `test_bare_query_jam4212_deduplication_and_vietnamese_translation`: Kiểm tra bare query JAM4212 không bị lặp (xuất hiện đúng 1 lần), dịch sạch thuần Việt, giữ nguyên 24 ca và danh sách ca.
   - `test_similar_query_jam4212_pure_vietnamese`: Kiểm tra không hồi quy đường tra cứu tương tự.
3. **`scripts/verify_barequery_dict_cleanup.py`**:
   - Kịch bản tự động hóa Playwright chạy trên giao diện thật của ứng dụng Streamlit (cổng 8501).
   - Kiểm tra và ghi nhận bằng chứng cho cả 4 cổng nghiệm thu.

---

## 4. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (UNIT & REGRESSION TESTS)

Chạy kiểm thử bằng Python 3.11 của máy đích (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`):

```
============================= test session starts =============================
platform win32 -- Python 3.11.14, pytest-8.4.2, pluggy-1.6.0 -- D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Sandbox\AIOS_habbit
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 7 items

tests/test_barequery_dict_cleanup.py::test_bare_query_jam4212_deduplication_and_vietnamese_translation PASSED [ 14%]
tests/test_barequery_dict_cleanup.py::test_similar_query_jam4212_pure_vietnamese PASSED [ 28%]
tests/test_structured_lookup_truth_fix.py::test_count_exact_cases_c0060_and_c7620 PASSED [ 42%]
tests/test_structured_lookup_truth_fix.py::test_c0060_honest_count_and_family_badges PASSED [ 57%]
tests/test_structured_lookup_truth_fix.py::test_c7620_honest_total_and_translated_fields PASSED [ 71%]
tests/test_structured_lookup_truth_fix.py::test_step5_recurrence_c7620_translated_remedy PASSED [ 85%]
tests/test_structured_lookup_truth_fix.py::test_explain_case_number_float_cleaning PASSED [100%]

============================== 7 passed in 7.37s ==============================
```

Toàn bộ 7/7 test liên quan đến tra cứu mã lỗi và lọc ngôn ngữ đều đạt **PASS 100%**.

---

## 5. BẰNG CHỨNG NGHIỆM THU TRÊN GIAO DIỆN THẬT (4 CỔNG)

Tất cả các ảnh chụp được xuất ra đồng thời tại cả 2 thư mục:
- `D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\`
- `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\`

Mỗi mục nghiệm thu sử dụng một khung hình độc lập, không dùng chung ảnh:

| STT | Tên tệp ảnh | Dung lượng (bytes) | SHA-256 | Chú thích nội dung khung hình |
|---|---|---|---|---|
| **1** | `anh-barequery-dict-cleanup-01-jam4212-24ca.png` (mirror: `anh-r1-1-jam4212-cautruc-24ca.png`) | 163.474 | `A602EE4CE55D3D2D8A944ED03307190BF293F7D032C4377805151A002DFB2AB3` | **Cổng 1 (Bare query JAM4212):** Giao diện thật hiển thị tiêu đề đếm đúng 24 ca. Tóm tắt từ điển chỉ xuất hiện đúng 1 lần duy nhất, định nghĩa và nguyên nhân đã được dịch sạch thuần Việt: *"Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)"*, cơ chế phát sinh thuần Việt, tên tệp nguồn `02XC_機能定義書_JAM一覧 (1).xls` giữ nguyên làm định danh tham chiếu. |
| **2** | `anh-barequery-dict-cleanup-02-jam4212-tuongtu.png` (mirror: `anh-r2-2-tracuu-tuongtu-dinhnghia-thuanviet.png`) | 147.812 | `AE78D83BB2F0FD232D1FB2846B41C91DB3947666C7AD50CE5471C52F8D23A1AB` | **Cổng 2 (Natural query JAM4212):** Giao diện thật đường tra cứu tương tự tổng hợp, Mục 1 Định nghĩa kỹ thuật & Mô tả mã lỗi dịch thuần Việt 100%, không bị hồi quy. |
| **3** | `anh-barequery-dict-cleanup-03-gui-cho-60s.png` | 117.629 | `7BAF5D0706EA5751A0542ACC7AFA13D9BEEA2026B40DEA91F08AAF4435CB31A2` | **Cổng 3 (Hồi quy gửi chờ 60s):** Gửi 1 câu hỏi và để yên 62 giây, kết quả trong DOM và DB đúng 1 tin nhắn user và 1 tin nhắn assistant, không bị gửi kép hoặc nhân đôi câu trả lời. |
| **4** | `anh-barequery-dict-cleanup-04-chip-goi-y.png` | 98.539 | `6B27F85B6EEA829114F0B0657EB748B65526FEB8163253344F54D2D8E4190B1A` | **Cổng 4 (Hồi quy chip gợi ý):** Tương tác chip gợi ý trên sổ nạp hoạt động mượt mà, trả lời đúng phạm vi tài liệu. |

---

## 6. VÒNG LẶP CẢI THIỆN LIÊN TỤC

Ghi nhận rà soát bổ sung theo Mục 5 của vé:
- Toàn bộ các đường hiển thị của `tra_cuu_loi_tuong_tu` (cả đường thô `_render_cards` lẫn đường tự nhiên `_render_synthesized_answer`) hiện tại đều đã được bao bọc qua hàm dịch chuẩn hóa `translate_kdtps_field` và thanh lọc cuối bằng `purify_markdown_text`.
- Không phát hiện thêm đường hiển thị nào khác bị lọt tiếng Nhật thô chưa dịch trong phạm vi tra cứu mã lỗi. Điểm phản hồi trên khung chat và hàng đợi chuyên gia hoạt động bình thường.

---

```json
{
  "ma_ve": "DESKTOP-HOME-BAREQUERY-DICT-CLEANUP",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-23T01:25:00+07:00",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
