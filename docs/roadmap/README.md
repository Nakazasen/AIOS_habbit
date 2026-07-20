# Roadmap & Gate Card Convention

`ROADMAP.md` là **nguồn trạng thái canonical duy nhất**. Không dùng một roadmap
thứ hai để ghi lại cùng gate theo một trạng thái khác.

## Status vocabulary

- `ACTIVE` — gate được phép triển khai ngay.
- `PLANNED` — có scope nhưng chưa được mở.
- `DONE` — implementation + validation đã hoàn thành.
- `RECORDED` — bằng chứng read-only/local-only; không phải code delivery.
- `BLOCKED` — có blocker ghi rõ.
- `RETIRED` — không còn là work item active.

Không dùng `PASS` đơn lẻ để thay thế status lifecycle. `PASS` chỉ xuất hiện trong
bằng chứng command/test của Gate Card.

## Gate Card

Mỗi gate active hoặc planned gần phải có một file riêng gồm: mục tiêu/non-goals,
preconditions, allowlist, acceptance criteria, privacy constraints, verification,
rollback và evidence/status links.

- `active/`: chỉ gate đang mở.
- `backlog/`: scope đã biết nhưng chưa mở.
- `completed/`: tóm tắt gate đã đóng, liên kết evidence.
- Lịch sử design/audit dài thuộc archive theo [../archive/README.md](../archive/README.md).
