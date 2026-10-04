# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: `ROUND4B-DOUBLE-BUBBLE` — [NHÀ] sửa lỗi 2 bubble khi hỏi kèm ảnh (truyền id tin nhắn đã lưu xuống cầu nối; cấm so khớp tiền tố). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `hang-cho`: prompt-queue-round5-ux-composer.md (sửa xô lệch composer + công tắc khối — phát hành sau khi ROUND4B ĐẠT).
- `commit`: `316a34d`
- `bao_cao`: `docs/phieu-viec/ket-qua/round4b-double-bubble.md`
- `ghi_chu`: 2026-10-04 12:00 +07 XONG: đủ 5 điểm nghiệm thu trên app thật (hỏi kèm ảnh = đúng 1 bubble, 2 lần độc lập; trace trỏ đúng bubble gộp OCR; câu không ảnh + cặp câu giống nhau giữ hành vi cũ). Mã `e900f0c`, 3 test mới pass, full pytest đối chiếu baseline 0 fail mới, audit PASS, index SHA không đổi. Bằng chứng ảnh `round4b-double-bubble-anh/01–03` + báo cáo.
