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

---

## 8. Phần 2: code + verify xong (chờ duyệt, chưa nhập kho chính)

- Ngày: 2026-10-05 (giờ máy khi ghi trạng thái).
- Commit code: `c868ee4` trên nhánh `phieu-viec/rag-fix1` (7 file, +974 dòng).
- Trạng thái: đã code xong theo đúng mục 5 + duyệt PLAN A của Muse (~07:15 +07). Chưa nhập kho chính, chưa ghi index production, chưa merge `main`.

### 8.1. Diff tóm tắt (điểm chạm tối thiểu)

- Mới: `src/aios_habit/draft_approval.py` (lõi duyệt: PIN 4–6 số băm SHA-256 + muối, mở khóa theo ca 8 giờ, khóa 15 phút sau 5 lần sai, log JSONL `local_cases/draft_approval_log.jsonl` đủ 3 trường mã cặp + tên người duyệt + thời gian, đổi nhãn đúng mẫu, gỡ duyệt, phiên bản hóa giữ bản cũ, metric theo mẻ, cờ riêng mặc định TẮT, hướng dẫn xem lại định kỳ).
- Mới: `src/aios_habit/chat_action_draft_approval.py` (lệnh `liệt kê bản thảo chưa duyệt [về X]`, render danh sách ngay trong vùng trả lời, chỉ đọc kho bản thảo + nhật ký).
- Sửa: `src/aios_habit/chat_action.py` (+1 dòng đăng ký action mới).
- Sửa: `src/aios_habit/workspace_chat_ui.py` (+133 dòng: `render_draft_approval_row` ngay dưới `render_answer_feedback_row` trong bong bóng chat — ô PIN + 3 nút Duyệt / Sửa rồi duyệt / Từ chối + nút Gỡ duyệt khi đã duyệt; toàn bộ chữ qua `t()`, không lộ traceback).
- Sửa: `src/aios_habit/i18n.py` (+54 dòng: 18 khóa tiếng Việt mới, giữ đủ 3 miền `vi`/`ja`/`zh-CN` để không vỡ kiểm tra đủ khóa).
- Mới: `tests/test_draft_approval.py` (10 test: cờ TẮT mặc định, PIN đúng/sai/khóa, đổi nhãn đúng mẫu, log đủ 3 trường, từ chối bắt buộc lý do, sửa giữ bản cũ, gỡ duyệt, metric theo mẻ, action tắt khi cờ tắt).
- Không sửa: `src/aios_habit/answer_draft_fallback.py` (0 dòng, luồng RAG giữ nguyên), không đụng kho chính hay index production. PIN và log chỉ ở `local_cases/` (đã bỏ qua git).

### 8.2. Đối chiếu tiêu chí ĐẠT trong prompt

- Nhập PIN đúng mở khóa theo ca; nhập sai báo lỗi tiếng Việt, không lộ gợi ý, khóa tạm sau 5 lần sai: đạt (test khóa + không lộ mã thật).
- Đủ 3 nút dưới câu trả lời bản thảo khi đã mở khóa + cờ bật; bấm Duyệt đổi nhãn đúng mẫu `Đã duyệt bởi [tên], ngày [date]`, log đủ 3 trường; Từ chối bắt buộc lý do; Sửa rồi duyệt tạo version mới, bản cũ còn nguyên: đạt (test đổi nhãn, log, phiên bản).
- Metric tỷ lệ duyệt theo mẻ tính được trên dữ liệu thật: đạt — kho thật 87 file / 3.377 cặp, hàm `compute_approval_metrics` cho 0 duyệt / 0 từ chối / 3.377 chờ, tỉ lệ 0.0, kèm gợi ý xem lại theo ngưỡng trong `REVIEW_GUIDE_VI`.
- Test + kiểm tra: test mới 10/10 đạt; cụm liên quan 42/42 đạt (`test_draft_approval` + `test_answer_draft_fallback` + `test_answer_feedback` + `test_i18n`); `compileall` sạch; `cli audit` PASS (`status: PASS`); `import workspace_chat_app` OK.
- Ghi chú trung thực: bộ toàn kho `pytest -q` chưa chạy xong trong 10 phút (ngắt do quá giờ, giống vé trước); 2 kiểm tra chống chữ cứng (`test_workspace_chat_ui_i18n` 1 lỗi dòng cũ `File nhị phân…` trong `render_chat_bubble`, `test_workspace_chat_app` 2 lỗi dòng cũ trong `module_root`) là code cũ có sẵn, diff vé này không chạm các dòng đó và toàn bộ chữ mới đều qua `t()`.

### 8.3. Cách dùng và hoàn tác

- Bật thử: đặt `AIOS_FEATURE_DRAFT_APPROVAL=1`, đặt PIN lần đầu bằng hàm đặt mã (chỉ lưu muối + băm ở `local_cases/`), nhập PIN 1 lần mỗi ca để mở nút Duyệt.
- Xem số liệu: đọc `local_cases/draft_approval_log.jsonl` rồi chạy `compute_approval_metrics`, đọc `approval_review_hints`.
- Hoàn tác: tắt cờ là ẩn toàn bộ nút duyệt, cặp vẫn nằm ở kho bản thảo, không ảnh hưởng luồng trả lời cũ.

### 8.4. Đề nghị duyệt vé

- Vé đạt ở mức chờ duyệt: đủ PIN + 3 nút trong chat + đổi nhãn 2 bước + metric + phiên bản hóa + action liệt kê, đúng rào (cờ TẮT, không nhập kho chính, không merge `main`).
- Nhờ Muse review độc lập rồi phát hành vé tiếp theo (Bước 2 nhập theo đợt là vé riêng).
