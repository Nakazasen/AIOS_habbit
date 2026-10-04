# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `ROUND4B-DOUBLE-BUBBLE` — [NHÀ] sửa lỗi 2 bubble khi hỏi kèm ảnh (truyền id tin nhắn đã lưu xuống cầu nối; cấm so khớp tiền tố). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `hang-cho`: prompt-queue-round5-ux-composer.md (sửa xô lệch composer + công tắc khối — phát hành sau khi ROUND4B ĐẠT).
- `commit`: `9c7732f`
- `bao_cao`: `docs/phieu-viec/ket-qua/round4b-double-bubble.md` (tạo khi xong)
- `ghi_chu`: 2026-10-04 11:03 +07 mã xong (truyền `user_message_id` xuống cầu nối + `reuse_message_id`), test mới pass 3/3, compileall OK. Full pytest 44F/19E nghi lỗi sẵn môi trường — đang chạy lại baseline (stash) đối chiếu. Sau đó: audit + import + verify app thật.
