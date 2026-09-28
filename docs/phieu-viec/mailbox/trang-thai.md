# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Vé E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: 58ec138
- `e2_fix_commit`: 58ec138
- `bao_cao`: chưa có (vé 2 phase — Phase B chưa chạy)
- `ghi_chu`: 2026-09-29 00:36 +07 (VM) — Phase A xong — OMP chạy Phase B theo prompt.md. 3 commit đã push fast-forward: dd1e7a7 (E1 report vào repo), 725c40f (fix synthesis E2: chọn claim theo giá trị + quota summary 2 + facet nhiều claim + prioritize_body_evidence mặc định cho lookup/diagnosis/câu hỏi có mã-số + repair contract nén thay vì xóa + validation loại dòng lỗi giữ dòng đúng), 58ec138 (fail-closed: create_synthesis_provider() mặc định TẮT, chỉ dựng provider cloud khi allow_cloud=True hoặc AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1). Test: 42 passed (test_rag_v2_synthesis.py), 19 passed (test_rag_v2_synthesis_provider.py), 88 passed (pipeline/summary/index/eval_harness) trên Linux Python 3.12.3. OMP chạy Phase B: giữ nguyên khóa cloud trong env để kiểm chứng fail-closed (probe phải ra is_none=true).
- Ticket trước: P1.4 — B1–B5 smoke test kho production ĐẠT, P1.3 đóng (báo cáo `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`).
