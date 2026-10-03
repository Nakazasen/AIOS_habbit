# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `INDEX-SWITCH-APP` — [NHÀ] chuyển app sang 3 khối lĩnh vực + bật định tuyến (junction sang ổ D, không tốn chỗ ổ C). Prompt: `docs/phieu-viec/mailbox/prompt.md` (copy nguyên văn `prompt-queue-index-switch-app.md`).
- `hang-cho`: hết.
- `commit`: `726d791`
- `bao_cao`: (chưa có — worker khối LSU đang nạp index trên ổ D)
- `ghi_chu`: 2026-10-03 23:12 junction và đếm document đã khớp. App đã mở, cờ bật. Worker LSU đang đọc index qua junction (~1 MB/s, ổ D) sau khi worker kho cũ tranh đĩa. Đang chờ nạp xong rồi hỏi lại 4 câu. Không kẹt no-op.
