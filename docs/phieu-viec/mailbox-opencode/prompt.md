# Ticket: ANSWER-DRAFT-FALLBACK — RAG trả lời trước, bản thảo làm dự bị có nhãn

> Bối cảnh: user chốt phương án 1 (không sách vở): RAG giữ làm luồng trả lời duy nhất như hiện tại; bản thảo enrichment (54 file `.md` đã audit, 2.398 cặp, kho ở `docs/phieu-viec/chatgpt-enrichment-fixed/`, quyết định phương án B ở vé `ENRICH-STAGING-FILESTORE`) chỉ làm **dự bị khi RAG không trả lời được**. Ngoài phạm vi tài liệu → nói thẳng "không tìm thấy", không bịa.

## Quyết định kỹ thuật (user chốt, Muse ghi)

1. **Thứ tự ưu tiên:** (a) RAG trả lời như hiện tại, không đổi; (b) chỉ khi RAG không có kết quả đạt ngưỡng tự tin → fallback sang kho bản thảo; (c) cả hai đều không có → trả lời thành thật "tôi không tìm thấy trong tài liệu có…", KHÔNG bịa đáp án.
2. **Nhãn không thương lượng:** mọi câu trả lời lấy từ bản thảo BẮT BUỘC hiển thị nhãn `Bản thảo — chưa qua chuyên gia duyệt` ngay trong câu trả lời, không giấu.
3. **Rào kho:** bản thảo KHÔNG nhập kho chính, KHÔNG nhập index production, KHÔNG gắn nhãn đã duyệt. Tính năng nằm sau feature flag mặc định TẮT; bật flag mới chạy luồng mới.

## Việc cần làm

1. **Khảo sát (chỉ đọc):** tìm điểm tích hợp luồng trả lời hiện tại (lane RAG) trong code app; xác định ngưỡng tự tin hiện có (nếu chưa có thì đề xuất một ngưỡng đơn giản, có lý do).
2. **Thiết kế (viết ngắn vào báo cáo):** vẽ luồng quyết định a→b→c; định nghĩa chính xác "RAG không trả lời được" (ngưỡng nào, đo ở đâu); cách đọc kho bản thảo (file `.md`, không qua `golden_answer_importer`); vị trí gắn nhãn bản thảo trong UI chat (một ô nhập + một vùng trả lời, không thêm đống nút).
3. **Code:** implement sau flag, tương thích **Python 3.11** (máy nhà, không dùng syntax 3.12+).
4. **Ba điểm bắt buộc (quy tắc 2026-10-03):**
   - (a) **Feedback tại chỗ:** nút thích/không thích ngay dưới câu trả lời trong khung chat; khi chê phải hỏi lý do (gợi ý vài lý do chọn nhanh + ô tự ghi); feedback ghi vào `local_cases`, KHÔNG ghi vào kho tri thức.
   - (b) **Metric đo được:** hàm tính coverage = % câu hỏi mẫu (kể cả câu hỏi dị dạng/paraphrase) được trả lời đúng; fallback rate = % câu phải dùng bản thảo; draft label rate = % câu trả lời bản thảo có nhãn đúng (phải 100%). Báo số liệu thật khi chạy.
   - (c) **Vòng xem lại:** test + tài liệu ngắn mô tả cách xem lại metric định kỳ và ngưỡng cần cải thiện.
5. **Test:** unit test cho luồng a→b→c (mock RAG), test nhãn bản thảo luôn hiện, test flag tắt = hành vi cũ nguyên vẹn; chạy full liên quan trên VM với `TMPDIR=~/workspace/.pytest-tmp`; `py_compile` tương thích 3.11.
6. Ghi báo cáo `docs/phieu-viec/ket-qua/answer-draft-fallback.md`: thiết kế, số liệu metric, kết quả test, vị trí flag. Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.

## Rào cứng

- Không sửa luồng RAG hiện tại khi flag tắt (test phải chứng minh hành vi cũ nguyên vẹn).
- Không đụng `main`, không force-push, không ghi production DB/index, không đụng `golden_answer_importer.py`.
- Không bịa đáp án: test phải có case "ngoài phạm vi" → trả lời thành thật, không fallback bừa.
- Commit sớm, push qua Git Data API ngay khi có commit hoàn chỉnh (không dồn cuối).
- Role gợi ý: PLAN (thiết kế trước) rồi code; vé verify nhanh sau này dùng SMOL/TINY.
