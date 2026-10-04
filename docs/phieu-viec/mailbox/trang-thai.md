# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `ROUND4B-DOUBLE-BUBBLE` — [NHÀ] sửa lỗi 2 bubble khi hỏi kèm ảnh (truyền id tin nhắn đã lưu xuống cầu nối; cấm so khớp tiền tố). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `hang-cho`: prompt-queue-round5-ux-composer.md (sửa xô lệch composer + công tắc khối — phát hành sau khi ROUND4B ĐẠT).
- `commit`: `e900f0c`
- `bao_cao`: `docs/phieu-viec/ket-qua/round4b-double-bubble.md` (tạo khi xong)
- `ghi_chu`: 2026-10-04 11:47 +07 cổng repo XONG: compileall OK, audit PASS, import OK, pytest đối chiếu baseline 0 fail mới (3 test mới pass, 44F/19E lỗi sẵn y hệt). Verify app: S1/S2 gửi ảnh mỗi lần đúng 1 bubble; phát hiện worker BGE không spawn do app được mở với PYTHONPATH tương đối (lỗi thao tác phiên, không phải lỗi mã) — đang restart app với PYTHONPATH tuyệt đối rồi chạy tiếp 2 lượt độc lập + câu không ảnh.
