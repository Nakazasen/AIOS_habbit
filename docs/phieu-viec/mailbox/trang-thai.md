# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: `INDEX-SPLIT-R3` — [NHÀ] tách thật với khối dự phòng Tổng hợp, ra ổ D (không bật routing trong vé này). Prompt: `docs/phieu-viec/mailbox/prompt.md` (copy nguyên văn `prompt-queue-index-split-r3.md`).
- commit: `a7a005c`
- bao_cao: `docs/phieu-viec/ket-qua/index-split-r3.md`
- Ghi chú: `2026-10-03 21:52 +07` Phát hành sau escalation R2 (72 document confidence < 0,40 — dừng đúng cổng). Quyết định kỹ thuật Muse: khối dự phòng `tong_hop` cho 72 document nghèo tín hiệu (không ép sai khối), code Phase A3 đã push ở tip `a7a005c` (test VM: 11/11 chia kho + 54/54 domain). Ổ C chỉ còn ~2,0 GB → tách ra ổ D (`D:\Sandbox\AIOS_index_split_new`), fail-closed nếu D trống < 3,5 GB.
- `hang-cho`: hết.
