# BÁO CÁO THỰC THI VÉ DESKTOP-NAMED-DOC-REGEX-TOLERANCE-FIX-HOME (R2)

- **Mã vé:** `DESKTOP-NAMED-DOC-REGEX-TOLERANCE-FIX-R2-HOME` (Khôi phục `DESKTOP-NAMED-DOC-REGEX-TOLERANCE-FIX-HOME`)
- **Kho mã:** `AIOS_habbit`
- **Nhánh thực thi:** `phieu-viec/rag-fix1`
- **Tập tin sửa đổi:** `src/aios_habit/index_domain.py`
- **Tập tin kiểm thử:** `tests/test_desktop_named_doc_regex_tolerance_fix_home.py`

---

## 1. Kết quả kiểm tra phiên gốc trước khi tiếp quản (Mục 2a)

- **Trạng thái cây làm việc trước khi sửa:**
  - Nhánh `phieu-viec/rag-fix1` đồng bộ với `origin/phieu-viec/rag-fix1` tại commit `bf2d08e1`.
  - Cây làm việc sạch với các file được theo dõi (không có thay đổi chưa commit trong `index_domain.py` hay mã nguồn chính).
  - Có 2 file script chẩn đoán chưa được theo dõi do phiên trước để lại: `scripts/inspect_regex_cases.py` (tạo lúc 12:25:37) và `scripts/inspect_t71_t78.py` (tạo lúc 12:26:50). Phiên gốc đã chết im lặng sau khi ghi 2 file đọc này, không có commit hay thay đổi mã nguồn nào dở dang.
  - Không có tiến trình nào đang hoạt động trùng lặp. Đã dọn dẹp các script phân tích tạm trước khi nộp.

---

## 2. Bản chất nguyên nhân & Cơ chế sửa đổi (Mục 2b)

### 2.1. Nguyên nhân gốc
1. **Dính cụm mô tả / tên kho vào tên tệp:** Cụm từ tiếng Việt ("điều tra lỗi", "báo cáo", ...) trong câu hỏi đứng trước tên tệp khiến chuỗi bóc tách chứa cả tiền tố (ví dụ: `"điều tra lỗi Write DP Serial NG.xlsx"` và `"điều tra lỗi Không lên nguồn.xlsx"`). Khi đối chiếu thẳng vào kho, hệ thống không tìm thấy file nào có tên chứa cụm này nên kích hoạt nhầm nhánh từ chối trung thực `named_document_not_found`.
2. **Ký tự tiếng Nhật và ngoặc trong tên tệp email:** Tệp như `RE 「Iris2020下位」 エラー発生 Log QA.msg` chứa ngoặc tiếng Nhật `「」`, ký tự CJK và khoảng trắng khiến regex chỉ bắt từ trần cuối cùng `QA.msg`.
3. **Dung sai mã lỗi Cxxxx:** Người dùng đặt câu hỏi thường gõ `0650` thay vì `C0650`, hoặc `3501` thay vì `C3501`. Đồng thời, regex bóc tách không được phép tự ý rút gọn `QA_C0650` thành `QA_0650`.
4. **Tệp materialized (TANABAN):** Tệp `TANABAN_Master.xlsx` được lưu trữ dưới dạng văn bản materialized `wsc-ef0d393c086c7f07627ca8b8.txt` có dòng tiêu đề `File Excel: TANABAN_Master.xlsx` nhưng chưa có cơ chế tra cứu biệt danh.

### 2.2. Các cải tiến triển khai
1. **Làm sạch tiền tố & Tên kho (`clean_named_doc_token`):** Loại bỏ triệt để các tiền tố dẫn dụ (`tài liệu`, `file`, `tệp`, `báo cáo`, `văn bản`, `theo`, `email`, ...) và cụm từ định danh kho tri thức (`điều tra lỗi`, `điều tra`, `tổng hợp`, `tri thức`, `lsu`, `mom`) đứng liền trước tên tệp.
2. **Hỗ trợ đa ngôn ngữ trong regex (`extract_named_document_candidates`):** Mở rộng tập ký tự nhận diện bao gồm toàn bộ Unicode CJK/tiếng Nhật (`\u3000-\u30FF\u3400-\u4DBF\u4E00-\u9FFF`), các dấu ngoặc `()`, `[]`, `「」`, `【】` và định dạng đuôi tệp mở rộng (`pdf|xlsx?|xlsm|csv|docx?|pptx?|txt|msg`).
3. **Đối chiếu hậu tố dài nhất (`_get_named_doc_suffixes` & `match_named_documents`):**
   - Phân rã chuỗi ứng viên thành các hậu tố từ dài nhất đến ngắn nhất.
   - Ưu tiên hậu tố dài nhất khớp với tên thật hoặc hậu tố của tài liệu trong mục lục kho tri thức (`all_specs`).
   - Tự động gán điểm ưu tiên (disambiguation boost) khi các định danh khác trong câu hỏi (ví dụ số hiệu ca `05-0469`, `06-0639`, `08-0866`) trùng khớp với các thành phần trong tên file đích.
4. **Dung sai mã lỗi (`_strip_model_code_prefix`):** Hỗ trợ đối chiếu linh hoạt tiền tố `C` trong các mã lỗi dạng `[cC]\d{4}` mà vẫn bảo toàn 100% tiền tố `C` nguyên vẹn khi câu hỏi có chứa (giữ đúng `QA_C0650_08_Dec.msg`).
5. **Ánh xạ biệt danh tệp materialized (`_get_spec_original_alias`):** Tự động đọc tiêu đề gốc `File <type>: <name>` từ các tệp văn bản `wsc-*.txt`, cho phép `TANABAN_Master.xlsx` khớp trực tiếp vào `wsc-ef0d393c086c7f07627ca8b8.txt`.

---

## 3. Bảng kết quả kiểm thử bộ test đặc tính

| Case ID | Câu hỏi mẫu | Tên tệp bóc tách / Khớp thực tế | Kết quả khớp | Trạng thái missing |
|---|---|---|:---:|:---:|
| **T071 (gốc)** | `Trong email FW IRIS2020 (High Model) QA_0650_08_Dec.msg...` | `FW    IRIS2020 (High Model) QA_C0650_08_Dec.msg` | **PASS (100%)** | Rỗng (`()`) |
| **T071 (có C)** | `Trong email FW IRIS2020 (High Model) QA_C0650_08_Dec.msg...` | `FW    IRIS2020 (High Model) QA_C0650_08_Dec.msg` (giữ đúng C) | **PASS (100%)** | Rỗng (`()`) |
| **T072** | `Trong email RE 「Iris2020下位」 エラー発生 Log QA.msg... (mã lỗi 6900)` | `RE  「Iris2020下位」　C6900 エラー発生RE  Log C6900_QA.msg` | **PASS (100%)** | Rỗng (`()`) |
| **T076** | `Theo báo cáo điều tra lỗi Write DP Serial NG.xlsx trên cụm DP Iris2020...` | `KTD-2025-08-0866-DP Iris2020-C2B- Write DP Serial NG.xlsx` | **PASS (100%)** | Rỗng (`()`) |
| **T077** | `Trong báo cáo điều tra lỗi Không lên nguồn.xlsx... (số hiệu 05-0469)` | `KTD-2025-05-0469-Iris2024-C34-A2-Không lên nguồn.xlsx` | **PASS (100%)** | Rỗng (`()`) |
| **T078** | `Trong báo cáo điều tra lỗi Không lên nguồn.xlsx... (số hiệu 06-0639)` | `KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx` | **PASS (100%)** | Rỗng (`()`) |
| **T087** | `Trong email RE IRIS2020 (Low model)... LCD displayed 3501.msg` | `RE    IRIS2020(Low model) -C22 A1-... LCD displayed C3501.msg` | **PASS (100%)** | Rỗng (`()`) |
| **T110** | `Trong tệp TANABAN_Master.xlsx (Sheet TANABAN_TSUIKA)...` | `wsc-ef0d393c086c7f07627ca8b8.txt` (alias match) | **PASS (100%)** | Rỗng (`()`) |
| **Hà Tùng (hợp lệ)** | `Theo tài liệu Tab led cam ung.pdf...` | `Tab led cam ung.pdf` | **PASS (100%)** | Rỗng (`()`) |
| **Hà Tùng (từ chối)** | `Theo tài liệu khong_ton_tai_123.pdf...` | Từ chối trung thực (`confidence = 0.0`) | **PASS (100%)** | `('khong_ton_tai_123.pdf',)` |

- **Số kết quả `named_document_not_found` sai trên các câu mẫu:** **0 / 10 (0%)**
- **Toàn bộ bộ test đặc tính & hồi quy (`test_index_domain.py`, `test_desktop_named_doc_regex_tolerance_fix_home.py`, `test_block_pin_lane_precedence.py`, `test_desktop_named_doc_streaming_marker_fix_home.py`, `test_rag_v2_structured_query.py`):** **92 / 92 tests PASS**.
