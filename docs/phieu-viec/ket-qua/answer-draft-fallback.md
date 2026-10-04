# Kết quả vé ANSWER-DRAFT-FALLBACK — RAG trả lời trước, bản thảo làm dự bị có nhãn

- Ngày: 2026-10-05 00:10 +07. Nhánh: `phieu-viec/rag-fix1`. Người làm: thợ opencode.
- Phạm vi: chỉ thêm module mới + test mới + báo cáo + trạng thái. Không sửa luồng RAG cũ, không đụng `main`, không ghi kho production hay index, không đụng `golden_answer_importer.py`.

## 1. Khảo sát luồng trả lời hiện tại

- Đường đi: `workspace_chat_app.py` (móc `chat_action.handle_chat_text` sau luồng ghi JIG, trước luồng agent/RAG) → `workspace_chat_rag_v2_adapter.py` (`pipeline.query` tạo gói bằng chứng) → `rag_v2/synthesis.py` (`synthesize_evidence`, đáp án trích xuất kèm nhãn `[N]`) → `workspace_chat_ai_answer.py` (`generate_workspace_ai_answer` + cổng Brain Gateway) → nhà cung cấp (cagent/router/gemini) hoặc đường dự phòng cục bộ.
- Ngưỡng hiện có: chưa có ngưỡng số. Chất lượng được suy ra từ `outcome_status` (`insufficient_evidence`, `provider_error`), `confidence_label` của gói bằng chứng và việc đáp án có chứa cụm thừa nhận thiếu thông tin hay không.
- Phản hồi tại chỗ: đã có sẵn và tái dùng nguyên vẹn — `answer_feedback.py` + `workspace_chat_ui.render_answer_feedback_row` (thích/không thích dưới câu trả lời, chê thì bắt nhập lý do, ghi vào `local_cases/answer_feedback.jsonl`, không ghi vào kho tri thức).
- Kho bản thảo: 54 tệp trong `docs/phieu-viec/chatgpt-enrichment-fixed/` (`mom/` + `lsu/`), đếm thật 2.398 cặp `## CÂU HỎI` + `Hỏi:/Đáp:`. Đọc trực tiếp dạng văn bản, không qua importer, không nhập index.

## 2. Thiết kế luồng a → b → c

```text
Câu hỏi
  → (a) RAG trả lời như cũ, giữ nguyên
  → RAG dùng được? (đủ cả: gọi được + có chữ + outcome tốt + độ tin cậy tốt + không tự nhận thiếu)
      → có: hiện đáp án RAG, không thêm nhãn
      → không: (b) tìm trong kho bản thảo (so từ khóa, cần ít nhất 2 từ chung hoặc khớp cụm)
          → có: hiện đáp án bản thảo + nhãn bắt buộc trong cùng câu trả lời
          → không: (c) trả lời thành thật "Tôi không tìm thấy trong tài liệu…", không bịa
```

- Định nghĩa "RAG không trả lời được" (`is_rag_usable`): `rag_ok` sai, hoặc bị từ chối trả lời, hoặc đáp án rỗng, hoặc `outcome_status` thuộc {thiếu bằng chứng, lỗi nhà cung cấp}, hoặc `confidence_label` thuộc {thấp, thiếu}, hoặc chính đáp án chứa cụm "không tìm thấy / chưa đủ thông tin / không đủ bằng chứng".
- Cách đọc kho bản thảo: `load_draft_entries` duyệt 54 tệp `.md`, `parse_draft_text` tách từng khối `## CÂU HỎI` thành cặp hỏi/đáp kèm tên tệp nguồn. `search_drafts` chấm điểm trùng từ khóa, không dùng embedding, không ghi gì.
- Vị trí gắn nhãn: nhãn nằm ngay trong câu chữ trả lời (`format_draft_answer`), không thêm nút hay ô nhập mới. Một ô nhập + một vùng trả lời giữ nguyên. Nhãn: `Bản thảo — chưa qua chuyên gia duyệt`.
- Cờ tính năng: `AIOS_FEATURE_ANSWER_DRAFT_FALLBACK`, mặc định BẬT theo yêu cầu người dùng ngày 2026-10-04 (ngoại lệ so với lệ thường mặc định tắt, đã ghi rõ trong code). Tắt cờ thì hàm `resolve_answer` trả nguyên đáp án RAG, hành vi đúng như cũ.

## 3. Code đã thêm

- Mới: `src/aios_habit/answer_draft_fallback.py` (thuần logic, tương thích Python 3.11):
  - `is_rag_usable`, `parse_draft_text`, `load_draft_entries`, `search_drafts`, `resolve_answer`, `format_draft_answer`.
  - Metric: `compute_fallback_metrics` (độ bao phủ, tỉ lệ dùng bản thảo, tỉ lệ nhãn bản thảo) + `review_recommendations` + hằng `REVIEW_GUIDE_VI` (cách xem lại định kỳ và ngưỡng cần cải thiện).
  - Phản hồi tại chỗ: không tạo kho mới, tái dùng `answer_feedback` (ghi `local_cases`, kèm `lane` = `rag` / `draft_fallback`).
- Mới: `tests/test_answer_draft_fallback.py` (9 bài).
- Không sửa tệp sản phẩm nào khác nên luồng RAG cũ nguyên vẹn.

## 4. Số liệu đo thật

- Kho thật: 54 tệp, 2.398 cặp hỏi/đáp (đếm bằng `load_draft_entries`, khớp số kiểm đếm vé trước).
- Thử mẫu 10 câu (6 RAG đúng + 3 phải dùng bản thảo + 1 ngoài phạm vi): độ bao phủ 1.0, tỉ lệ dùng bản thảo 0.3, tỉ lệ nhãn bản thảo 1.0 (đạt yêu cầu 100%).
- Vòng xem lại: ngưỡng cần cải thiện là độ bao phủ dưới 80%, tỉ lệ dùng bản thảo trên 30%, hoặc nhãn bản thảo dưới 100%. Chi tiết trong `REVIEW_GUIDE_VI` của module.

## 5. Kết quả kiểm tra

- `compileall src tests`: sạch.
- Test mới: 9/9 đạt (`tests/test_answer_draft_fallback.py`).
- Bộ liên quan: 100/100 đạt (`test_answer_draft_fallback` + `test_answer_feedback` + `test_feedback_loop` + `test_chat_action` + `test_rag_v2_synthesis`).
- `cli audit`: `{"status": "PASS"}`.
- `import aios_habit.workspace_chat_app`: thành công.
- Lưu ý trung thực: bộ toàn kho (`pytest -q`) chạy quá 10 phút trên máy này nên chưa xong, không báo đạt cho bộ toàn kho. Luồng RAG cũ được bảo vệ bằng bộ liên quan 100 bài đạt và việc không sửa tệp RAG nào.

## 6. Rào cứng đã giữ

- Luồng RAG hiện tại không đổi (chỉ thêm module mới; tắt cờ = trả nguyên RAG).
- Không đụng `main`, không force-push, không ghi kho production/index, không đụng `golden_answer_importer.py`.
- Không bịa đáp án: có bài test ngoài phạm vi → trả lời thành thật, không fallback bừa.
- Nhãn bản thảo luôn hiện trong câu trả lời bản thảo (test riêng).
- Đề nghị duyệt để Muse review độc lập bước tiếp theo.
