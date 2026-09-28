# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: 58ec138
- `e2_fix_commit`: 58ec138
- `bao_cao`: chưa có (Phase B đang chạy)
- `ghi_chu`: 2026-09-29 01:00 +07 (h410asrock) — Cổng Phase B đã mở (`e2_fix_commit` = 58ec138) → OMP BẮT ĐẦU Phase B. Đã pull 3 commit Phase A (dd1e7a7 E1 đợt 2 vào repo, 725c40f fix synthesis, 58ec138 fail-closed provider). Đã chuẩn bị sẵn từ trước: harness `scratch/e2_smoke.py` (giữ nguyên khóa provider trong env, cổng an toàn chặn TRƯỚC mọi bước nặng, kiểm SHA bản copy C khớp `062ec090…`, quét `bge_worker.stderr.log`), bản copy C dùng lại (C chỉ còn 2,7 GB), kho D đã đối chiếu SHA `062ec090…` khớp P1.4. Bước kế: probe fail-closed trên mã đã vá → snapshot D trước chạy → chạy B1–B5 → snapshot + SHA sau chạy → viết `VE_E2_fix-synthesis.md`.
- Ticket trước: P1.4 — B1–B5 smoke test kho production ĐẠT, P1.3 đóng (báo cáo `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`).
