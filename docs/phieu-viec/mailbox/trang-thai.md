# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Vé E2 vòng 2 — Fix chọn dòng: ưu tiên mã trường + mã tệp (theo bằng chứng rớt B5 và thoái lui B2 của E2).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: (Muse ghi `e2v2_fix_commit` khi Phase A code xong — OMP chỉ sang Phase B khi thấy dòng này)
- `ghi_chu`: 2026-09-29 00:35 +07 (Muse VM) — Verdict E2: **CHƯA ĐẠT** (rớt 1 trong 2 dòng kiểm then chốt: B5 không nêu được định nghĩa HOUSE_METHOD; điểm mới: B2 thoái lui so với P1.4 — mất YY2-Z151.exe/YY2-Z152.exe). B3 đã qua (nvarchar(4000)). Các tiêu chí còn lại ĐẠT: chạy xong 52,75/21,55/17,51/24,92s, grounded, provider_used=false, không ghi D (SHA 062ec090… không đổi, 2 snapshot 0 thay đổi), fail-closed chứng minh được (6 khóa cloud còn trong env, create_synthesis_provider() → None, 44 mẫu mạng = 0 kết nối).
- Ticket trước: E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại), verdict CHƯA ĐẠT (báo cáo `docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md`, commit `4aa6d68`).

