# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé E2 vòng 2 — Fix chọn dòng: ưu tiên mã trường + mã tệp (theo bằng chứng rớt B5 và thoái lui B2 của E2).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: `dd393ed` (vé E2 vòng 2, đầu nhánh lúc nhận). **CHƯA có `e2v2_fix_commit`** → cổng Phase B còn đóng; OMP chỉ chạy pre-flight read-only, chưa chạy B1–B5.
- `ghi_chu`: 2026-09-29 00:40 +07 (h410asrock) — OMP nhận vé E2 vòng 2, đặt `dang-lam`. Cổng Phase B CÒN ĐÓNG: `git ls-remote` = HEAD = `dd393ed`, cả hai commit sau vé (`e9bf579`, `dd393ed`) chỉ sửa mailbox, chưa có commit code vòng 2, mailbox chưa có dòng `e2v2_fix_commit`. Đang làm: pre-flight read-only (kiểm SHA bản copy C, cổng an toàn fail-closed, dựng harness chấm vòng 2 có luật chấm B5 theo ngữ cảnh `HOUSE_METHOD` + `倉庫`/`検査`).
- Verdict E2 vòng 1 (Muse, 2026-09-29 00:35 +07): **CHƯA ĐẠT** (rớt 1 trong 2 dòng kiểm then chốt: B5 không nêu được định nghĩa HOUSE_METHOD; điểm mới: B2 thoái lui so với P1.4 — mất YY2-Z151.exe/YY2-Z152.exe). B3 đã qua (nvarchar(4000)). Các tiêu chí còn lại ĐẠT: chạy xong 52,75/21,55/17,51/24,92s, grounded, provider_used=false, không ghi D (SHA 062ec090… không đổi, 2 snapshot 0 thay đổi), fail-closed chứng minh được (6 khóa cloud còn trong env, create_synthesis_provider() → None, 44 mẫu mạng = 0 kết nối).
- Ticket trước: E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại), verdict CHƯA ĐẠT (báo cáo `docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md`, commit `4aa6d68`).

