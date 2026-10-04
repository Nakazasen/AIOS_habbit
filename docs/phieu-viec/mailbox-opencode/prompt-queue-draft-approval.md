# Vé xếp hàng: DRAFT-APPROVAL — Cơ chế duyệt bản thảo (Bước 2 vòng phản hồi)

> Role gợi ý: PLAN (thiết kế trước) rồi code. Lane: thợ opencode code + test + verify (opencode vừa xây module `answer_draft_fallback.py`, hiểu code nhất).

## Bối cảnh (user chốt 2026-10-05 ~05:47 +07, lệnh làm nhanh)

- Vé ANSWER-DRAFT-FALLBACK đã xong: RAG trả lời trước, bản thảo enrichment làm dự bị có nhãn "Bản thảo — chưa qua chuyên gia duyệt".
- Còn thiếu: cơ chế để chuyên gia duyệt bản thảo → nếu không làm, bản thảo mãi mãi "chưa duyệt", không có đường lên "đã duyệt". Đây chính là Bước 2 (vòng phản hồi) trong lộ trình Bước 0–5.
- User chốt thiết kế: **PIN thay tài khoản, duyệt trong chat thay màn hình riêng, đổi nhãn thay vì nhập kho ngay.**

## Thiết kế (không thương lượng)

1. **Ai được duyệt**: mã PIN 4–6 số do user đặt (lưu ở config local, KHÔNG commit lên repo), chỉ 2–3 chuyên gia biết. Nhập 1 lần mỗi phiên/ca làm việc → mở khóa nút Duyệt. Khi bấm Duyệt: hỏi tên người duyệt (tự khai), ghi log đủ 3 trường: id cặp, tên người duyệt, thời gian.
2. **Duyệt ở đâu**: ngay dưới câu trả lời bản thảo trong khung chat — 3 nút Duyệt / Sửa rồi duyệt / Từ chối. KHÔNG màn hình riêng, KHÔNG thêm đống nút (đúng triết lý chat-first: 1 ô nhập + 1 vùng trả lời). Thêm chat action: user hỏi "liệt kê bản thảo chưa duyệt [về X]" → render danh sách ngay trong vùng trả lời.
3. **Duyệt xong thì sao** (2 bước tách riêng):
   - Bước 1 (vé này): đổi nhãn "Bản thảo — chưa qua chuyên gia duyệt" → "Đã duyệt bởi [tên], ngày [date]". Cặp vẫn nằm ở kho bản thảo. Cho phép gỡ duyệt (ghi log).
   - Bước 2 (vé riêng sau, KHÔNG làm ở đây): nhập theo đợt vào kho chính — có backup, quyết định riêng.
4. **Ba điểm bắt buộc** (quy tắc 2026-10-03):
   - (a) Feedback tại chỗ: 3 nút ngay dưới câu trả lời bản thảo, chỉ hiện khi đã mở khóa PIN.
   - (b) Metric đo được: tỷ lệ duyệt theo mẻ, số cặp đã duyệt / chưa duyệt / từ chối; hàm tính + nơi xem số liệu.
   - (c) Vòng xem lại: phiên bản hóa — "Sửa rồi duyệt" tạo version mới, giữ bản cũ để đối chiếu; tài liệu ngắn mô tả cách xem lại định kỳ và ngưỡng cần cải thiện.

## Rào cứng

- Feature flag riêng cho cơ chế duyệt, mặc định TẮT (luật repo). Nút duyệt chỉ hiện khi flag bật + PIN đã mở khóa + câu trả lời là bản thảo.
- Không đụng luồng RAG; chỉ chạm `answer_draft_fallback.py` ở điểm tích hợp tối thiểu (ghi rõ diff trong báo cáo).
- Không nhập kho chính, không ghi index production trong vé này.
- Python 3.11 (không dùng syntax 3.12+); không merge `main`; không force-push. Commit sớm, push qua Git Data API ngay khi có commit hoàn chỉnh.

## Tiêu chí ĐẠT

- Nhập PIN đúng → mở khóa; nhập sai → báo lỗi tiếng Việt, không lộ gợi ý.
- Dưới câu trả lời bản thảo hiện đủ 3 nút khi đã mở khóa; bấm Duyệt → nhãn đổi đúng mẫu "Đã duyệt bởi [tên], ngày [date]", log đủ 3 trường; Từ chối → bắt buộc ghi lý do; Sửa rồi duyệt → tạo version mới, bản cũ còn nguyên.
- Metric tỷ lệ duyệt/mẻ tính được trên dữ liệu thật.
- Test: unit cho PIN (đúng/sai), log duyệt, đổi nhãn, phiên bản hóa; `compileall` + `pytest` + `cli audit` PASS; `import workspace_chat_app` OK.
- Báo cáo `docs/phieu-viec/ket-qua/draft-approval.md`; commit lên `phieu-viec/rag-fix1`; `trang-thai.md` → `xong-cho-duyet`.
