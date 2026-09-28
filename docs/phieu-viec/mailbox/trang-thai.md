# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé P1.4 — B1–B5 smoke test kho production (tuyến nội bộ).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: 05a1ba7
- `bao_cao`: chưa có (đang chạy lại B1–B5 sau khi chặn provider cloud)
- `ghi_chu`: 2026-09-28 23:45 +07 (h410asrock) — phát hiện quan trọng: worker BGE tự dựng provider cloud (gemini/openrouter/groq/mistral/chatanywhere/deepseek) từ **biến môi trường máy** và đã **thử gọi** trong lượt 1 (log `bge_worker_stderr_run1_cloud_attempts.log`; 4 dòng "All synthesis providers failed"), làm mỗi câu chậm thêm ~90s và làm B4 quá hạn 180s. Đã chặn bằng cách blank toàn bộ khóa provider trong env tiến trình chạy (loader `.env` không ghi đè biến đã tồn tại); guard `create_synthesis_provider() is None` bắt buộc trước khi chạy. Đang chạy lại B1–B5 (lượt hợp lệ, mỗi câu có re-init worker nếu chết).
- Ticket trước: P1.3 — sao lưu + chép kho production ĐẠT, B1–B5 chưa chạy (báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md`).
