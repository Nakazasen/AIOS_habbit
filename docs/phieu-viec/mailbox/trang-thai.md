# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `SPEED-COLDSTART-HOME-R1` — [NHÀ] chạy lại câu E3 qua lane 1, bù tiêu chí 6/6 còn thiếu của SPEED-COLDSTART-HOME (verdict CHƯA ĐẠT toàn vé 2/3: E3 không qua cổng nhãn lane 1 sau 3 lần; 3/3 gắn lại worker + init 112,1 s + SHA index đã đạt).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `ghi_chu`: 2026-10-03 00:18 +07 — OMP nhận vé. Gate ĐẠT: watcher LAUNCH 1/4 lúc 00:17:22 (`launchStallCount=1`), không phải 4 lần kẹt. Điều kiện mở đã tới (vé [NHÀ] đo lại E3, không chờ mã VM). Tiếp: kiểm worker PID 11896 + cầu nối Gemini, rồi chạy E3.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  1. `KNOWLEDGE-ENRICH-PILOT` (`prompt-queue-knowledge-enrich-pilot.md`) — làm giàu tri thức theo lô bằng Copilot 365 (thí điểm 5 hiện tượng F CALL); form Q&A chuẩn + xuất/nhập batch + đo trước/sau. Đã bổ sung phụ lục: máy không có Copilot thì dùng Gemini Web qua cầu nối / Nakazasen Router soạn thảo, không dùng ChatGPT cá nhân cho dữ liệu công ty.
  2. `UX-CHAT-CORE` (`prompt-queue-ux-chat-core.md`) — [VM code + NHÀ verify] chat nhiều ý định trong một câu, nhúng log + vẽ biểu đồ ngay trong câu trả lời, lane tự động (hết đổi tay), hết báo lỗi ảo.
  3. `UX-INTERVIEW-FEEDBACK` (`prompt-queue-ux-interview-feedback.md`) — [VM code + NHÀ verify] phỏng vấn chuyên gia chạy được trong app + feedback theo từng gợi ý (sai/một phần bắt buộc nhập lý do, nguyên nhân thật, nội dung nắn lại) + vòng lặp tự cải thiện.
  4. `UX-AGENT-REPORT` (`prompt-queue-ux-agent-report.md`) — [VM code + NHÀ verify] agent tạo/sửa báo cáo (docx/pptx/md) bằng lệnh lời trong chat, có backup trước khi ghi đè.
