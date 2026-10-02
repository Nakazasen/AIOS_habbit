# Vé: KNOWLEDGE-ENRICH-PILOT — làm giàu tri thức theo lô bằng Copilot (thí điểm 5 hiện tượng F CALL)

Lane: [VM] Muse code+test trên VM → [USER] chạy batch Copilot trên máy có Copilot 365 Premium → [NHÀ] OMP verify trên máy nhà (dữ liệu thật, chỉ đọc DB chính).
Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user chốt 2026-10-02)

- Dùng Copilot/LLM làm "đào tạo đi tắt" cho AIOS: Copilot 365 đóng vai chuyên gia vì luồng phỏng vấn chuyên gia chưa vận hành; chuyên gia thật duyệt sau.
- Copilot 365 Premium không trần hạn mức → khai thác theo lô, càng tự động càng tốt.
- Không lưu vết LLM trong kho; chỉ dùng nhãn trạng thái: `Copilot đóng vai chuyên gia — chờ duyệt` / `chuyên gia đã duyệt`.
- AIOS hiện tại dùng Sonnet 4 qua gói C-Agent trả phí của công ty.

## Việc Muse làm trên VM

1. **Form chuẩn Q&A điều tra** (schema, có test): mỗi form gồm `gap_id`, chủ đề, mã lỗi, hiện tượng, câu hỏi, khía cạnh kỳ vọng, bằng chứng tham chiếu, ô trả lời, độ tự tin, cờ "cần chuyên gia xác nhận". Form dùng chung cho cả 3 việc: Copilot trả lời theo lô, chuyên gia duyệt, và nạp vào kho.
2. **Script xuất batch**: từ knowledge gaps 6 loại (`missing_threshold`, `missing_condition`, `missing_exception`, `missing_example`, `conflict`, `stale_knowledge`) + ca lỗi thiếu trường → file batch (JSONL/Markdown), mỗi gap một form đã điền sẵn câu hỏi. Thí điểm: 5 hiện tượng F CALL.
3. **Script nhập batch**: đọc file câu trả lời của Copilot → ghi vào staging DB với nhãn `Copilot đóng vai chuyên gia — chờ duyệt`. Cấm nhập thẳng vào DB chính / luồng trả lời chính khi chưa duyệt.
4. **Nối câu hỏi vàng vào interview engine**: bộ câu hỏi từ form trở thành seed questions cho `adaptive_interview_engine` (theo loại gap đã có).
5. **Bộ đo trước/sau**: cùng một bộ câu hỏi về 5 hiện tượng, chấm độ sâu (có nêu nguyên nhân khả thi không, có biết cần kiểm tra gì không, có dẫn được ca tương tự không) + đo thời gian trả lời.
6. Test + `compileall` + `pytest` + `cli audit` PASS theo luật repo; không ghi index production; không đụng ổ D.

## Việc user làm (máy có Copilot 365)

- Chạy batch 5 hiện tượng F CALL qua Copilot theo file xuất, trả file câu trả lời về; duyệt nhanh đợt đầu (đánh dấu mục nào đạt/mục nào cần sửa).

## Việc OMP verify [NHÀ]

- Chạy script xuất/nhập trên dữ liệu thật: staging DB đúng schema, nhãn trạng thái đúng, DB chính và index production không đổi (đo SHA trước/sau).
- Báo cáo `docs/phieu-viec/ket-qua/knowledge-enrich-pilot.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Form schema có test bao phủ; xuất/nhập batch chạy được trên dữ liệu thật.
- Nhãn trạng thái đúng 2 mức; không có bản chưa duyệt nào lọt vào luồng trả lời chính.
- Bộ đo trước/sau chạy được; index production `library.sqlite` không đổi.
- Commit riêng trên branch `phieu-viec/rag-fix1`, không đụng `main`.
