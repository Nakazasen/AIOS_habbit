# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `ROUND5-UX-COMPOSER` — [NHÀ] sửa xô lệch composer + công tắc chọn khối tri thức. Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `hang-cho`: (hết — sau ROUND5 tính bước tiếp theo).
- `commit`: 19f89fb
- `bao_cao`: 
- `ghi_chu`: 2026-10-04 12:31 +07 — Khảo sát xong: layout 6 cột ở composer dòng 4198–4403, định tuyến khối ở `_select_domain_route`, badge "Đang tra cứu khối X" dựng ở `_run_chat_turn_async`, sidebar quanh `render_source_library`. Chốt thiết kế: 2 dòng dưới ô nhập (dòng mờ trạng thái/thuộc tính + dòng nút), công tắc khối kiểu popover mờ, cờ `forced_domain` xuyên composer→adapter, dòng "Thư viện chung · 3 khối · luôn bật" gập sẵn. Bắt đầu code.
