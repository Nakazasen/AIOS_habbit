# Trạng thái mailbox — máy công ty KDTVN-PC0575

- Máy: `KDTVN-PC0575`
- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: `p2-b7b-smoke-ticket.md` (P2 B7b — smoke test, sparse head)
- `prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
- B7b: `xong`
- Báo cáo: `docs/phieu-viec/ket-qua/p2_b7b_smoke_2026-09-29.md`
- Ghi chú: [2026-09-29 15:40 +07] OMP PC0575 nhận vé P2-B7b (sparse head smoke). Bắt đầu bước 1: pull agent-mailbox + verify SHA-256.
- Ghi chú: [2026-09-29 15:49 +07] Mốc 2 xong: SHA-256 2 file .npy khớp 100%; đã copy vào `onnx/`; tính lại checksum cây model = `sha256:728c9eb7ee48a66ac4b6d567e3408433398911a6abcce9685d8a048eb8766baa` (bằng chứng: bỏ 2 file .npy ra thì hash 8 file = `sha256:dad14a24…e4bd4` đúng bằng cache verify cũ ⇒ cây chỉ đổi vì thêm sparse head). Tiếp: chạy smoke.
- Ghi chú: [2026-09-29 15:58 +07] Mốc 3 xong: **smoke ĐẠT — exit 0**, `status: OK`, cả 4 câu B1/B2/B3/B5 `pass: true` (không thiếu chuỗi bắt buộc), `sparse_head` đã nạp. Report: `docs/phieu-viec/ket-qua/p2_b7b_smoke_2026-09-29.md`. Tiếp: chốt báo cáo + đóng vé.
- Ghi chú: [2026-09-29 16:05 +07] Mốc 4 — đóng vé: báo cáo đã ghi (exit code, JSON nguyên văn, checksum mới, SHA index trước/sau đều `062ec090…ef8ca` khớp `corpus_fingerprint`). `B7b: xong`. Chờ Muse review. Điểm cần Muse quyết: có cập nhật hằng checksum `b1d887e0…`/`697a97c3…` cho bản deploy LAN không (nhánh ONNX dùng env/sidecar nên smoke vẫn ĐẠT).

Mailbox này chỉ dành cho máy công ty KDTVN-PC0575 (CPU-only, máy deploy LAN).
Watcher trên PC0575 poll riêng thư mục này; watcher máy nhà không nhìn vào đây.
Muse viết vé vào đây khi có việc cho máy công ty (verify deploy, smoke test, kiểm tra).
