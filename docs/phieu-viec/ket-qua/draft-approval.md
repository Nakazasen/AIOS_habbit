# Báo cáo vé DRAFT-APPROVAL — phần 1: khảo sát + phương án (chờ duyệt, chưa code)

- Ngày: 2026-10-05 (giờ máy khi ghi trạng thái)
- Vé: `DRAFT-APPROVAL` — cơ chế duyệt bản thảo (Bước 2 vòng phản hồi)
- Prompt: `docs/phieu-viec/mailbox-opencode/prompt.md`
- Trạng thái: trình phương án, chờ duyệt. Chưa sửa code, chưa ghi kho.

## 1. Khảo sát lane hiện có (điểm chạm tối thiểu)

- `src/aios_habit/answer_draft_fallback.py`: luồng trả lời a→b→c (RAG trước, bản thảo dự bị kèm nhãn bắt buộc `Bản thảo — chưa qua chuyên gia duyệt`, cờ `AIOS_FEATURE_ANSWER_DRAFT_FALLBACK` mặc định BẬT theo lệnh user). Nhãn nằm trong thân câu trả lời (`format_draft_answer`). Metric `compute_fallback_metrics` + gợi ý xem lại `review_recommendations` đã có.
- `src/aios_habit/answer_feedback.py`: phản hồi tại chỗ (thích / chưa thích + lý do bắt buộc khi chê), lưu `local_cases/answer_feedback.jsonl`, không ghi kho tri thức. Tái dùng được cho log duyệt.
- `src/aios_habit/workspace_chat_ui.py` (`render_answer_feedback_row`, khoảng dòng 360): hàng phản hồi nhỏ dưới mỗi câu trả lời. Đây là vị trí đặt thêm 3 nút duyệt (chỉ hiện khi đã mở khóa PIN + câu trả lời là bản thảo).
- `src/aios_habit/chat_action.py` (khung TOOL-2): action đăng ký một lần, khớp câu hỏi không dấu, render ngay trong bong bóng trả lời, sau cờ `AIOS_FEATURE_CHAT_ACTION`. Dùng cho lệnh `liệt kê bản thảo chưa duyệt`.
- Kho bản thảo: `docs/phieu-viec/chatgpt-enrichment-fixed/` (đọc trực tiếp, không qua importer, không nhập kho chính trong vé này).
- An toàn dữ liệu: `local_cases/`, `.env` đã nằm trong `.gitignore` (đã kiểm). PIN và log duyệt chỉ lưu local, không commit.

## 2. Phương án A (đề xuất): module duyệt riêng + chạm tối thiểu

- Thêm mới `src/aios_habit/draft_approval.py`: kiểm tra PIN (so hàm băm SHA-256, PIN 4–6 số, sai báo lỗi tiếng Việt không gợi ý), phiên mở khóa theo ca (`unlock_until`), log duyệt append-only JSONL tại `local_cases/draft_approval_log.jsonl` (đủ 3 trường: id cặp, tên người duyệt, thời gian + quyết định + lý do khi từ chối), đổi nhãn `Bản thảo — chưa qua chuyên gia duyệt` → `Đã duyệt bởi [tên], ngày [date]`, gỡ duyệt (ghi log), phiên bản hóa (`Sửa rồi duyệt` tạo version mới, giữ bản cũ), metric tỷ lệ duyệt theo mẻ (đã duyệt / chưa duyệt / từ chối).
- Cờ riêng `AIOS_FEATURE_DRAFT_APPROVAL`, mặc định TẮT. Nút chỉ hiện khi cờ bật + PIN đã mở khóa + câu trả lời là bản thảo.
- Chạm `answer_draft_fallback.py` tối thiểu: thêm hàm đổi nhãn + hàm kiểm tra câu trả lời có phải bản thảo không (ghi rõ diff trong báo cáo phần 2).
- Giao diện: thêm `render_draft_approval_row` ngay dưới `render_answer_feedback_row` trong bong bóng chat (3 nút Duyệt / Sửa rồi duyệt / Từ chối, ô tên người duyệt + lý do khi từ chối). Nhãn, lỗi, hướng dẫn 100% tiếng Việt, không lộ traceback.
- Chat action mới `liet_ke_ban_thao_chua_duyet`: khớp câu `liệt kê bản thảo chưa duyệt [về X]`, render danh sách ngay trong vùng trả lời.
- PIN do user đặt, lưu ở `local_cases/draft_approval_config.json` (chỉ hàm băm) hoặc biến môi trường, KHÔNG commit.
- Ưu: đúng thiết kế đã chốt (PIN thay tài khoản, duyệt trong chat, đổi nhãn 2 bước), đủ 3 điểm bắt buộc (feedback tại chỗ, metric, phiên bản hóa), dễ hoàn tác (tắt cờ).
- Nhược: thêm 1 module + 1 file log + test mới (khoảng 300–400 dòng).
- Khi dùng: chọn luôn vì vé yêu cầu đủ cả 3 điểm bắt buộc.

## 3. Phương án B (nhẹ, không đề xuất): tái dùng feedback + hồ sơ có sẵn

- Không tạo module mới. Nhét quyết định duyệt vào `answer_feedback.jsonl` (thêm trường) và dùng `workspace_cases.sqlite` làm log.
- Ưu: ít file mới, xong nhanh.
- Nhược: thiếu phiên bản hóa thật (bản cũ khó đối chiếu), metric theo mẻ phải vá thêm, trộn log duyệt chuyên gia với feedback người dùng thường (khó tách số liệu, khó gỡ duyệt sạch). Không đạt tiêu chí (c) vòng xem lại.
- Khi dùng: chỉ khi user chấp nhận bỏ phiên bản hóa — vé này không cho phép.

## 4. Rủi ro và cách chặn

- Lộ PIN: chỉ lưu hàm băm local, so sánh hằng số thời gian, khóa sau vài lần sai, không log PIN.
- Nhập nhầm kho chính: vé này KHÔNG nhập kho, KHÔNG ghi index production; cặp vẫn nằm kho bản thảo sau khi duyệt.
- Đụng luồng RAG: không sửa luồng RAG, chỉ thêm hàm nhãn trong module bản thảo.
- Quyền riêng tư: log duyệt ở `local_cases` (đã ignore), không đưa lên mây, không commit.

## 5. Đường thực hiện (sau khi được duyệt PLAN)

1. Tạo `draft_approval.py` + unit test (PIN đúng/sai, log đủ 3 trường, đổi nhãn đúng mẫu, từ chối bắt buộc lý do, sửa tạo version giữ bản cũ).
2. Thêm `render_draft_approval_row` + action liệt kê bản thảo + chuỗi tiếng Việt trong `i18n.py` (nếu thiếu).
3. Chạy `compileall` + `pytest -q` + `cli audit` + `import workspace_chat_app`, đo metric trên dữ liệu thật.
4. Ghi báo cáo phần 2 (diff, số liệu, bằng chứng lệnh), `trang-thai.md` → `xong-cho-duyet`, commit + push.

## 6. Tiêu chí nghiệm thu (nhắc lại từ prompt)

- PIN đúng mở khóa, sai báo lỗi tiếng Việt không gợi ý.
- Đủ 3 nút dưới câu trả lời bản thảo khi đã mở khóa; Duyệt đổi nhãn đúng mẫu + log đủ 3 trường; Từ chối bắt buộc lý do; Sửa rồi duyệt giữ bản cũ.
- Metric tỷ lệ duyệt theo mẻ tính được trên dữ liệu thật.
- Test + 4 lệnh kiểm tra đạt; báo cáo + commit lên `phieu-viec/rag-fix1`.

## 7. Đề nghị duyệt

- Chốt phương án A. Sau khi Muse ra verdict ĐẠT cho PLAN này và user đồng ý, thợ mới bắt đầu bước code (mục 5).
