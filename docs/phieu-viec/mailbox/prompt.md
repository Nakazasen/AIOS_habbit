# VÉ: FEEDBACK-LOOP-HOME (nút like/dislike + máy tự học thói quen, không cần tài khoản)

- Mã vé: `FEEDBACK-LOOP-HOME`
- Role OMP gợi ý: DEFAULT (code UI + store + học thói quen)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/feedback-loop-home.md`

## Bối cảnh

User chốt 2026-10-03: mọi tính năng phải có vòng lặp cải thiện liên tục
(feedback tại chỗ → metric đo được → vòng xem lại). Hai yêu cầu "đừng quên":
(a) feedback câu trả lời ngay trên khung chat (thumbs + lý do khi chê);
(b) đã có sẵn `answer_feedback` + UI từ vé ANSWER-DRAFT-FALLBACK — vé này
mở rộng nó thành vòng lặp đầy đủ + máy tự học thói quen.

Ràng buộc user 2026-10-05: **không quản lý theo tài khoản người dùng**.
Định danh bằng mã máy (device ID) lưu local, không đăng nhập.

## Việc cần làm

1. **Nút like/dislike + lý do** ngay dưới mỗi câu trả lời trong khung chat.
   - UI tiếng Việt, gọn trong câu trả lời (đúng luật chat-first: không thêm
     đống nút toolbar).
   - Bấm dislike bắt buộc chọn lý do (ngắn gọn, vài lựa chọn + ô tự ghi).
2. **Feedback store theo mã máy**: mỗi máy có ID ngẫu nhiên lưu local.
   - Ghi vào `local_cases/` (tuyệt đối không ghi vào kho tri thức chung).
   - Mỗi record: mã máy + mã câu hỏi + câu trả lời + like/dislike + lý do + thời gian.
3. **Hai tác dụng** (đều không cần biết tên người dùng):
   - (a) Sửa chung: nhiều máy cùng dislike một câu → đánh dấu để đội ngũ sửa gốc.
   - (b) Học thói quen từng máy: chủ đề hay hỏi, độ dài ưa thích, giờ hay dùng.
4. **"Càng dùng càng hiểu mình"**: hồ sơ thói quen theo mã máy, app dùng để
   điều chỉnh (vd hay hỏi LSU buổi sáng → ưu tiên tìm đống LSU; hay chê dài
   → trả lời súc tích hơn cho máy đó). Lịch sử chat hiện có là một phần trí nhớ.
5. **Metric + vòng xem lại**: hàm tính tỷ lệ dislike theo câu trả lời / theo
   chủ đề; báo cáo định kỳ câu nào bị chê nhiều để sửa gốc.
6. Cờ tính năng riêng (mặc định TẮT), theo đúng luật repo.

## Tiêu chí nghiệm thu

- Nút like/dislike + lý do hiện dưới câu trả lời, UI tiếng Việt, không vỡ layout chat.
- Feedback ghi đúng `local_cases/`, có mã máy, không lọt vào kho tri thức.
- Test đủ 3: ghi feedback, tính metric, vòng học thói quen (dữ liệu giả lập nhiều máy).
- `compileall` sạch, `pytest -q` đạt, `cli audit` PASS, import app OK.
- Không nút thừa, không ghi index, không merge `main`, không secret.
- Báo cáo `feedback-loop-home.md` có ảnh/số đo demo vòng lặp chạy thật.

