# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: `UX-CHAT-CORE` — [VM] Muse code+test trên VM → [NHÀ] OMP verify trên app thật: chat nhiều ý định, biểu đồ trong chat, hết đổi luồng tay, hết báo lỗi ảo.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: `7aa5218`
- `bao_cao`: `docs/phieu-viec/ket-qua/ux-chat-core.md`
- `ghi_chu` (verdict Muse): 2026-10-03 ~11:10 +07 — **ĐẠT** (báo cáo `5269d8c`). Đủ tiêu chí vé PI-SPIKE-HOME: pi 1.0.0; đường sống Gemini Flash Lite, 7 đường chết có lý do; tạo file ĐẠT, sửa file ĐẠT ở lần 2 (lần 1 model hỏi lại nội dung — ghi nhận trung thực); RPC 15 event ổn định 1 lệnh, chưa thử hàng đợi/ngắt giữa chừng; rào giữ (không dữ liệu công ty, không đụng index production, không merge main, telemetry tắt). Digest batch tạm đỗ, checkpoint 847/889 còn nguyên.
- `ghi_chu` (điều phối Muse): 2026-10-03 ~11:10 +07 — Phát hành vé hàng chờ #1 `UX-CHAT-CORE` (copy `prompt-queue-ux-chat-core.md` → `prompt.md`), `trang-thai` → `moi`. Còn lại hàng chờ: UX-INTERVIEW-FEEDBACK → UX-AGENT-REPORT → UX-E2E-APP → SCAN-O-D. Lưu ý: phase [VM] do Muse đảm nhận trước (code+test trên VM; phương án UI công khai trình user duyệt theo AGENTS.md 4.1); OMP [NHÀ] verify sau khi code đã push lên branch.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; user chèn thêm KNOWLEDGE-DIGEST-HOME 2026-10-03 ~00:45 +07 — ưu tiên làm trong 2 ngày cuối tuần):
  1. `UX-INTERVIEW-FEEDBACK` (`prompt-queue-ux-interview-feedback.md`) — [VM code + NHÀ verify] phỏng vấn chuyên gia chạy được trong app + feedback theo từng gợi ý (sai/một phần bắt buộc nhập lý do, nguyên nhân thật, nội dung nắn lại) + vòng lặp tự cải thiện.
  2. `UX-AGENT-REPORT` (`prompt-queue-ux-agent-report.md`) — [VM code + NHÀ verify] agent tạo/sửa báo cáo (docx/pptx/md) bằng lệnh lời trong chat, có backup trước khi ghi đè.
  3. `UX-E2E-APP` (`prompt-queue-ux-e2e-app.md`) — [NHÀ] kiểm thử đầu-cuối app thật sau loạt UX mới đêm 2026-10-03 (multi-intent, lane tự động, feedback chat, SMA(20)/trend, radio LSU gate); user duyệt viết vé 2026-10-03.
  4. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.


- `ghi_chu` (Muse): 2026-10-03 ~07:20 +07 — user quyết đổi provider (không chờ cầu nối). Phát hành vé PROVIDER-SWITCH: thứ tự probe cầu nối → sửa khóa Router → resume batch. Giữ nguyên rào bản thảo/không nhập kho.
