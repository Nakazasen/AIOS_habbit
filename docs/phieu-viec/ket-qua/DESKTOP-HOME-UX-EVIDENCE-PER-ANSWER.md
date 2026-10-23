# BÁO CÁO KẾT QUẢ THỰC HIỆN VÉ: DESKTOP-HOME-UX-EVIDENCE-PER-ANSWER

- **Model thực hiện:** Gemini 3.8 Flash
- **Mức thinking:** Deep Thinking / Agentic Reasoning (Active)
- **Thời điểm hoàn thành:** 2026-10-23T19:55:00Z (2026-10-24 02:55:00 GMT+7)
- **Nhánh Git:** `phieu-viec/rag-fix1`
- **Commit hash:** `2d44b33501a35560946282eb5d86241a8a252277` (đã push thành công lên `origin/phieu-viec/rag-fix1`)
- **Kho lưu trữ:** `https://github.com/Nakazasen/AIOS_habbit.git`

---

## 1. Bối cảnh & Vấn đề xử lý
- **Vấn đề phản ánh từ người dùng thực tế:** Khi trò chuyện qua nhiều lượt câu hỏi trong cùng một phiên chat, bằng chứng tài liệu không gắn liền với câu trả lời tương ứng mà dồn xuống một expander tập trung duy nhất ở chân trang (`📌 Kết quả & bằng chứng`). Hậu quả là khi hỏi càng nhiều câu, bằng chứng các câu trước bị trôi xa và bị ghi đè bởi câu mới nhất, người dùng không thể tự kiểm chứng nguồn tài liệu của các câu hỏi trước đó.
- **Giải pháp triệt để:**
  1. Gắn khối bằng chứng tài liệu (`🔍 Trích dẫn từ tài liệu (N)`) trực tiếp dưới từng bong bóng phản hồi của trợ lý.
  2. Hỗ trợ mở bảng đối chiếu tài liệu nguồn tại chỗ (`render_source_viewer_panel`) khi nhấn vào từng nguồn trong khối bằng chứng của câu đó.
  3. Cơ chế trích xuất độc lập theo từng tin nhắn (Message Metadata -> Trace Metadata -> Trace Nodes -> Fallback Citations Text), đảm bảo Zero Leakage (không rò rỉ bằng chứng câu khác, không hiển thị khối expander rỗng nếu câu không có nguồn).
  4. Loại bỏ hoàn toàn khối expander tập trung `📌 Kết quả & bằng chứng` ở chân trang (cả ở chế độ mặc định `full` và chế độ `split`).

---

## 2. Các thay đổi mã nguồn chính

### `src/aios_habit/workspace_chat_ui.py`
- Bổ sung hàm `extract_evidence_items_for_message(msg, display_content, trace, badge_data, notebook_id)`:
  - Trích xuất danh sách trích dẫn/bằng chứng gắn riêng cho từng tin nhắn trợ lý.
  - Phân tích đa tầng từ metadata tin nhắn, `EvidenceTrace` metadata, danh sách nodes trong trace (`source`, `chunk`, `evidence`).
  - Hỗ trợ fallback trích xuất nguồn từ văn bản câu trả lời (`extract_citations_from_text`) đối với các tin nhắn lịch sử cũ không có trace.
  - Kiểm soát phạm vi chặt chẽ: `badge_data` chỉ được kích hoạt nếu khớp chính xác `trace_id` hoặc `message_id`.
- Bổ sung hàm `render_per_answer_evidence_block(evidence_items, conversation_id, message_id, notebook_id, locale, display_content)`:
  - Kết xuất khối expander thu gọn `🔍 {t('citations_from_docs', locale=locale)} ({count})` dưới câu trả lời.
  - Hiển thị danh sách nguồn có gắn nhãn phân loại (Báo cáo gốc / Tài liệu tham chiếu / Đoạn trích).
  - Tích hợp nút xem nguồn tại chỗ gọi trực tiếp `render_source_viewer_panel` từ `citation_source_viewer.py` mà không làm thay đổi nội dung câu trả lời.
- Cập nhật hàm `render_chat_bubble`:
  - Tích hợp gọi `render_per_answer_evidence_block` cho cả luồng tin nhắn tương tác (interactive) và luồng tin nhắn tĩnh/lịch sử (non-interactive).

### `src/aios_habit/workspace_chat_app.py`
- Cập nhật vòng lặp kết xuất tin nhắn chat: Chỉ truyền `badge_data` cho tin nhắn trợ lý mới nhất (`badge_data=badge_data if is_latest_ans else None`) để ngăn rò rỉ bằng chứng sang các tin nhắn khác.
- Gỡ bỏ hoàn toàn khối expander chân trang:
  - Loại bỏ khối `with st.expander(f"📌 {t('results_and_evidence', ...)}", expanded=False): _render_workspace_results_and_evidence()` ở cuối cột chat.
  - Loại bỏ cột hiển thị bằng chứng tĩnh ở chế độ `split`.

---

## 3. Kết quả kiểm thử tự động (Unit Tests)

Bộ kiểm thử đơn vị chuyên biệt cho tính năng gắn bằng chứng theo câu trả lời được thực hiện bằng Python 3.11.14:

```
tests/test_evidence_per_answer.py::test_extract_evidence_from_trace_metadata PASSED [ 14%]
tests/test_evidence_per_answer.py::test_extract_evidence_from_trace_nodes_fallback PASSED [ 28%]
tests/test_evidence_per_answer.py::test_extract_evidence_legacy_text_fallback PASSED [ 42%]
tests/test_evidence_per_answer.py::test_zero_leakage_when_no_sources PASSED [ 57%]
tests/test_evidence_per_answer.py::test_scoped_badge_data_only_used_when_matching PASSED [ 71%]
tests/test_evidence_per_answer.py::test_render_per_answer_evidence_block_empty PASSED [ 85%]
tests/test_evidence_per_answer.py::test_footer_results_and_evidence_expander_removed PASSED [100%]
============================== 7 passed in 0.76s ==============================
```

Bộ kiểm thử hồi quy giao diện chat và composer:
```
======================= 95 passed, 2 warnings in 16.73s =======================
```

---

## 4. Nghiệm thu giao diện thực tế (Live UI 5-Turn Verification)

Quy trình nghiệm thu tự động mô phỏng nhịp người dùng thật qua Playwright (`scripts/verify_evidence_per_answer.py`) với hội thoại 5 lượt hỏi đáp (`CONV-EV5Q-97E117B8`):
1. **Lượt 1:** Câu hỏi C6770 kèm 2 nguồn tài liệu (`Loi KDTPS.xlsx › dòng 9609` và `02XC_自己診断表示一覧表-Iris2020 VN.xls`).
2. **Lượt 2:** Câu hỏi C7620 kèm nguồn `Loi KDTPS.xlsx › dòng 10530`.
3. **Lượt 3:** Câu hỏi C2152 kèm nguồn `Loi KDTPS.xlsx › dòng 9918`.
4. **Lượt 4:** Câu hỏi bảo trì máy in kèm nguồn `quy_trinh_bao_tri_may_in.pdf`.
5. **Lượt 5:** Câu hỏi C6400 kèm 2 nguồn tài liệu riêng biệt (`Loi KDTPS.xlsx › dòng 9609` và `huong_dan_an_toan_dien.docx`).

### Kết quả các cổng nghiệm thu:
- **Cổng 1 (Gate 1 - PASS):** Mở khối bằng chứng của Câu 1 tại chỗ, hiển thị `🔍 Trích dẫn từ tài liệu (2)`, bấm nút mở nguồn mở thành công bảng chi tiết `02XC_自己診断表示一覧表-Iris2020 VN.xls` ngay dưới câu trả lời.
- **Cổng 2 (Gate 2 - PASS):** Mở khối bằng chứng của Câu 5 tại chỗ, hiển thị đúng nguồn của Câu 5 (`Loi KDTPS.xlsx`), xác nhận tuyệt đối không có rò rỉ mã `02XC_` từ Câu 1.
- **Cổng 3 (Gate 3 - PASS):** Quét toàn bộ chân trang và vùng nhập liệu, xác nhận số lượng expander tập trung `📌 Kết quả & bằng chứng` bằng 0.
- **Cổng 4 (Gate 4 - PASS):** Tải lại toàn bộ trang (F5 / Reload), mở lại hội thoại đã lưu, xác nhận khối bằng chứng của Câu 1 vẫn hiển thị đầy đủ và mở ra đối chiếu tại chỗ bình thường.

---

## 5. Bảng kê khai ảnh nghiệm thu thực tế

Mọi tệp hình ảnh nghiệm thu được lưu trữ đồng thời tại:
- Repo ứng dụng: `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\`
- Hộp thư điều phối: `D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\`

| Tên tệp ảnh | Dung lượng | SHA-256 Checksum | Chú thích nội dung khung hình |
| :--- | :--- | :--- | :--- |
| `anh-ev-01-cau1-evidence-in-place.png` | 145,387 bytes | `C11BCE0F8F5FB78AE0158B79E1EEC56E7CDA8B6709C1A2E2D5093457C5236D4A` | Khối bằng chứng Câu 1 mở tại chỗ kèm panel xem nguồn 02XC_ dưới câu trả lời |
| `anh-ev-02-cau5-evidence-in-place.png` | 103,083 bytes | `91A504773C2B3B274667F8FB4D4CF54AC8D34F53B99AE07833296FAA2CF75254` | Khối bằng chứng riêng biệt của Câu 5 mở tại chỗ, không rò rỉ nguồn của Câu 1 |
| `anh-ev-03-footer-no-centralized-expander.png` | 101,166 bytes | `0130980D5E51B9C3B30BB0CFD5AD848CE0EE264802C27E9752E893EFB3339D26` | Chân trang sau câu trả lời cuối, xác nhận không còn expander tập trung Kết quả & bằng chứng |
| `anh-ev-04-reloaded-saved-conversation.png` | 126,026 bytes | `36DF626E1AD0CFCE27C1808BC872552DD14374351A040AF93AC6F3E15E4D73A6` | Tải lại trang hội thoại đã lưu, khối bằng chứng từng câu vẫn mở và hiển thị tại chỗ |

Tệp manifest kết quả: `ket-qua-do-evidence-per-answer.json` (đã nộp kèm).

---

```json
{
  "ma_ve": "DESKTOP-HOME-UX-EVIDENCE-PER-ANSWER",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-23T19:55:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
