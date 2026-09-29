# Trạng thái mailbox — máy công ty KDTVN-PC0575

- Máy: `KDTVN-PC0575`
- Trạng thái: `dang-lam`
- Ticket hiện tại: `p2-b7b-smoke-ticket.md` (P2 B7b — smoke test, sparse head)
- `prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
- B7b: `dang-lam`
- Ghi chú: [2026-09-29 15:40 +07] OMP PC0575 nhận vé P2-B7b (sparse head smoke). Bắt đầu bước 1: pull agent-mailbox + verify SHA-256.

Mailbox này chỉ dành cho máy công ty KDTVN-PC0575 (CPU-only, máy deploy LAN).
Watcher trên PC0575 poll riêng thư mục này; watcher máy nhà không nhìn vào đây.
Muse viết vé vào đây khi có việc cho máy công ty (verify deploy, smoke test, kiểm tra).
