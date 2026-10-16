# BÁO CÁO THỰC THI VÉ DESKTOP-PC0575-ANSWER-HEADER-STRIP: LOẠI BỎ KHỐI JSON CHỈ DẪN HỆ THỐNG Ở ĐẦU NỘI DUNG ĐÁP ÁN

**Mã vé:** `DESKTOP-PC0575-ANSWER-HEADER-STRIP`  
**Thời điểm thực hiện:** 2026-10-16 17:50 – 18:07 +07  
**Máy thực hiện:** Desktop PC0575  
**Trạng thái:** **HOÀN THÀNH 100% — ĐÃ KIỂM CHỨNG TRÊN SỔ THẬT & PUSH REMOTE**  

---

## 1. BỐI CẢNH & NGUYÊN NHÂN LỖI HIỂN THỊ

Vé chẩn đoán khẩn cấp `DESKTOP-PC0575-UI-FREEZE-DIAG-URGENT` đã truy vết dòng JSON thô lộ trên đầu đáp án trong ảnh chụp của người dùng:
- **Bản ghi gốc:** `MSG-308CE36B` trong cuộc trò chuyện `CONV-9C730D76` (lưu tại `local_cases/workspace_chat/messages.jsonl`, trace `trc_76ec054c1e77`) thuộc sổ "Điều tra lỗi LSU" (`NB-E35A7BEE`), được tạo từ ngày **2026-10-01T19:58:47**.
- **Nguyên nhân gốc:** Vào thời điểm 01/10/2026, mô hình AI phía sau (`cagent_api` / LLM) đã trôi định dạng và trả về khối JSON cấu trúc chỉ dẫn lập trình (`{"summary": ..., "changes": [], "tests": []}`) gắn liền ở đầu câu trả lời markdown. Backend lúc đó lưu nguyên văn vào trường `content` của `messages.jsonl`.
- **Thiếu sót tầng hiển thị:** Hàm `render_chat_bubble` trước đây chỉ làm sạch các thẻ tương tác (`aios_realtime_alert`, `aios_chat_artifact`, `aios_case_preview`), chưa có bộ lọc loại bỏ khối JSON chỉ dẫn rò rỉ này. Khi mở lại hội thoại cũ hoặc khi mô hình mới trả về định dạng tương tự, khối JSON bị lộ ra giao diện người dùng.

---

## 2. NỘI DUNG GIẢI PHÁP ĐÃ THỰC THI (ĐÚNG 1 ĐIỂM TẦNG HIỂN THỊ)

Sửa đúng **MỘT ĐIỂM DUY NHẤT** tại tầng hiển thị / làm sạch nội dung tin nhắn trước khi render trong `src/aios_habit/workspace_chat_ui.py`:

1. **Hàm phát hiện và loại bỏ chuẩn xác `strip_instruction_header(content: str) -> str`:**
   - Kiểm tra nội dung mở đầu bằng `{` (bỏ qua khoảng trắng / dòng trống dẫn xuất).
   - Sử dụng `json.JSONDecoder().raw_decode` để tách đúng 1 đối tượng JSON ở vị trí đầu chuỗi một cách tất định và an toàn, lấy chính xác vị trí kết thúc `end_idx`.
   - Kiểm tra nhận diện mẫu đặc trưng chỉ dẫn:
     - Chứa đầy đủ 3 khóa: `{"summary", "changes", "tests"}`; HOẶC
     - Chứa ít nhất 2 trong 3 khóa với trường `changes` hoặc `tests` là một `list` (đặc trưng schema của chỉ dẫn hệ thống).
   - Loại bỏ khối JSON và các dòng trống liền kề, giữ nguyên 100% phần nội dung câu trả lời phía sau (bảo toàn thụt lề markdown nếu có).
   - **Tuyệt đối an toàn:** Nếu không thỏa mãn mẫu đặc trưng (ví dụ văn bản thông thường bắt đầu bằng dấu ngoặc nhọn `{`, tập hợp toán học, ví dụ cấu hình JSON khác, JSON nằm ở thân bài hoặc code block), hàm trả về nguyên vẹn chuỗi gốc.

2. **Tích hợp vào `render_chat_bubble`:**
   - Ngay khi nhận tin nhắn vai trò `assistant` (`elif msg.role == "assistant":`), xử lý:
     `raw_content = strip_instruction_header(str(msg.content or ""))`
   - Dùng chung cho mọi đường hiển thị đáp án:
     - Chế độ văn bản thuần (`render_interactive=False` cho tin nhắn lịch sử cũ);
     - Chế độ tương tác đầy đủ (`render_interactive=True` cho tin nhắn mới);
     - Các nhánh thẻ kết quả, cảnh báo realtime và hàng duyệt bản thảo.
   - **Bảo toàn dữ liệu gốc:** Không sửa đổi bất kỳ tệp dữ liệu nào trong `messages.jsonl`.

---

## 3. ĐỐI CHIẾU TRÍCH DẪN & ẢNH HIỂN THỊ TRƯỚC / SAU TRÊN BẢN GHI MSG-308CE36B

### (a) Dữ liệu gốc trong `local_cases/workspace_chat/messages.jsonl`
```json
{"id": "MSG-308CE36B", "conversation_id": "CONV-9C730D76", "role": "assistant", "content": "{\n  \"summary\": \"Cần thêm thông tin\",\n  \"changes\": [],\n  \"tests\": []\n}\n\nTôi hiểu bạn đang hỏi về mối liên hệ giữa hiện tượng đai đen trong hình ảnh và đường kính BEAM trong hệ thống LSU. Tuy nhiên, câu hỏi này thuộc về lĩnh vực kỹ thuật quang học và in ấn, không phải về lập trình hay code. \n\nDựa trên các nguồn tài liệu được cung cấp, mối liên hệ này được giải thích rõ ràng:\n\n**Trường hợp hiển thị lý tưởng (chuẩn):** Khi đường kính BEAM đạt **60 µm**...", "created_at": "2026-10-01T19:58:47.773489", "trace_id": "trc_76ec054c1e77"}
```

### (b) So sánh hiển thị thực tế trên giao diện

| Trạng thái | Nội dung hiển thị trên giao diện | Ảnh chụp minh chứng |
| :--- | :--- | :--- |
| **TRƯỚC (BEFORE)** | `{ "summary": "Cần thêm thông tin", "changes": [], "tests": [] }`<br><br>Tôi hiểu bạn đang hỏi về mối liên hệ giữa hiện tượng đai đen trong hình ảnh và đường kính BEAM trong hệ thống LSU. Tuy nhiên, câu hỏi này thuộc về lĩnh vực kỹ thuật quang học và in ấn... | `anh-pc0575-answer-header-strip-truoc.png` |
| **SAU (AFTER)** | **Tôi hiểu bạn đang hỏi về mối liên hệ giữa hiện tượng đai đen trong hình ảnh và đường kính BEAM trong hệ thống LSU. Tuy nhiên, câu hỏi này thuộc về lĩnh vực kỹ thuật quang học và in ấn...** *(Dòng JSON đã biến mất 100%)* | `anh-pc0575-answer-header-strip-sau.png` |

- **Kiểm tra độ toàn vẹn ký tự:** Đoạn văn bản sau khi làm sạch khớp **100.0%** với phần nội dung đáp án phía sau khối JSON, không thay đổi ngữ nghĩa hay bất kỳ ký tự nào của câu trả lời.

---

## 4. KẾT QUẢ KIỂM THỬ TOÀN DIỆN (TEST SUITE)

Đã tạo bộ kiểm thử chuyên sâu `tests/test_desktop_pc0575_answer_header_strip.py` gồm 16 kịch bản kiểm thử:

1. **Nhóm kiểm thử trường hợp dương tính (Positive Tests):**
   - `test_strip_instruction_header_real_case_msg_308ce36b`: Kiểm thử trực tiếp trên chuỗi `MSG-308CE36B` đọc từ `messages.jsonl` -> **PASS**.
   - `test_strip_instruction_header_compact_single_line`: Khối JSON trên 1 dòng đơn -> **PASS**.
   - `test_strip_instruction_header_with_leading_whitespace_and_newlines`: Khối JSON có khoảng trắng và dòng trống phía trước -> **PASS**.
   - `test_strip_instruction_header_subset_keys`: Biến thể chứa 2 trong 3 khóa chỉ dẫn (`summary` + `changes`, `summary` + `tests`, `changes` + `tests`) -> **PASS**.
   - `test_strip_instruction_header_only_header_returns_empty`: Tin nhắn chỉ chứa khối chỉ dẫn -> **PASS**.
   - `test_strip_instruction_header_none_or_empty`: Xử lý an toàn chuỗi rỗng và `None` -> **PASS**.

2. **Nhóm kiểm thử phủ định bắt buộc (Negative Tests - chống cắt xén nhầm):**
   - `test_negative_starts_with_plain_curly_brace`: Câu trả lời bắt đầu bằng `{x, y, z}` -> **GIỮ NGUYÊN 100% (PASS)**.
   - `test_negative_starts_with_math_set`: Câu trả lời bắt đầu bằng tập hợp `{1, 2, 3, 4}` -> **GIỮ NGUYÊN 100% (PASS)**.
   - `test_negative_starts_with_other_valid_json`: Bắt đầu bằng JSON cấu hình server mẫu (`host`, `port`) -> **GIỮ NGUYÊN 100% (PASS)**.
   - `test_negative_starts_with_json_having_only_summary`: Bắt đầu bằng JSON chỉ có khóa `summary` thông thường -> **GIỮ NGUYÊN 100% (PASS)**.
   - `test_negative_json_code_block`: Khối JSON chỉ dẫn nằm trong code block markdown ```` ```json ```` -> **GIỮ NGUYÊN 100% (PASS)**.
   - `test_negative_json_in_body_not_start`: Khối JSON chỉ dẫn nằm ở thân bài thay vì ở đầu -> **GIỮ NGUYÊN 100% (PASS)**.
   - `test_negative_indented_json`: JSON nằm trong mục liệt kê markdown có thụt lề -> **GIỮ NGUYÊN 100% (PASS)**.

3. **Nhóm kiểm thử tích hợp giao diện (`render_chat_bubble`):**
   - `test_render_chat_bubble_strips_header_interactive_mode`: Chế độ tương tác đầy đủ (`render_interactive=True`) -> **PASS**.
   - `test_render_chat_bubble_strips_header_non_interactive_mode`: Chế độ tối ưu tin nhắn cũ (`render_interactive=False`) -> **PASS**.
   - `test_render_chat_bubble_preserves_valid_curly_brace`: Giữ nguyên câu trả lời hợp lệ mở đầu bằng `{` -> **PASS**.

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 55 items

tests\test_desktop_pc0575_answer_header_strip.py ................        [ 29%]
tests\test_ui_render_optimization.py .........                           [ 45%]
tests\test_commit_c_challenger_2_adversarial.py ......................   [ 85%]
tests\test_agent_conversational_omnibar.py ........                      [100%]

============================= 55 passed in 6.61s ==============================
```

4. **Kiểm chứng trực tiếp trên tiến trình UI thật bằng Playwright:**
   - Trỏ vào URL: `http://localhost:8501/?nb=NB-E35A7BEE&conv=CONV-9C730D76`.
   - Kết quả: `Has 'Cần thêm thông tin' (leaked JSON summary): False`.
   - `Has '"summary":' (raw JSON key): False`.
   - Tin nhắn hiển thị mượt mà, trơn tru, không còn vết tích của khối JSON chỉ dẫn.

---

## 5. THÔNG TIN COMMIT & PUSH REMOTE

- **Repository:** `AIOS_habbit`
- **Nhánh (Branch):** `phieu-viec/rag-fix1`
- **Tệp chỉnh sửa:**
  - `src/aios_habit/workspace_chat_ui.py` (Thêm hàm `strip_instruction_header` và gọi trước khi render bubble)
  - `tests/test_desktop_pc0575_answer_header_strip.py` (Bộ test tích hợp & âm tính toàn diện)
  - `docs/phieu-viec/ket-qua/DESKTOP-PC0575-ANSWER-HEADER-STRIP.md` (Báo cáo thực thi)
  - `docs/phieu-viec/ket-qua/anh-pc0575-answer-header-strip-truoc.png` (Ảnh trước sửa)
  - `docs/phieu-viec/ket-qua/anh-pc0575-answer-header-strip-sau.png` (Ảnh sau sửa)
