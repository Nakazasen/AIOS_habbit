# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé E2 vòng 2 — Fix chọn dòng: ưu tiên mã trường + mã tệp (theo bằng chứng rớt B5 và thoái lui B2 của E2).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: mốc 1 (nhận vé) `2895e0c`; mốc 2 (pre-flight + harness vòng 2) = tip nhánh sau lượt push này. **CHƯA có dòng `e2v2_fix_commit`** → cổng Phase B vẫn đóng, OMP chưa chạy B1–B5.
- `ghi_chu`: 2026-09-29 00:47 +07 (h410asrock) — Mốc 2 XONG: pre-flight read-only + harness vòng 2 sẵn sàng; cổng Phase B vẫn ĐÓNG, lý do chặn duy nhất = mailbox chưa có dòng `e2v2_fix_commit`. Bằng chứng (`C:\AIOS_p1_4\out\e2v2\preflight.json`, chạy 00:45): bản copy index trên C SHA `062ec090…` khớp nguồn D (2.552.659.968 byte); cache xác minh model fp32 tươi (không ghi D); tập nguồn read-only **74/496 document, 1.064 đoạn** đúng như P1.4 (422 loại: 421 `file_changed_since_ingest` + 1 `no_single_fingerprint`); 6 khóa cloud còn nguyên trong env nhưng `create_synthesis_provider()` → `None`. Cổng mới của harness vòng 2 đã tự kiểm 6 ca (mailbox hiện tại → ĐÓNG; chỉ MỞ khi SHA thật nằm trong lịch sử HEAD). Bộ chấm vòng 2 theo ngữ cảnh đã tự kiểm 9 ca: dựng lại đúng verdict vòng 1 (B1 ĐẠT, B3 ĐẠT, B2 RỚT, B5 RỚT) và bác đúng dương tính giả `'1'` của `RECEIVE_TYPE`.
- Verdict E2 vòng 1 (Muse, 2026-09-29 00:35 +07): **CHƯA ĐẠT** (rớt 1 trong 2 dòng kiểm then chốt: B5 không nêu được định nghĩa HOUSE_METHOD; điểm mới: B2 thoái lui so với P1.4 — mất YY2-Z151.exe/YY2-Z152.exe). B3 đã qua (nvarchar(4000)). Các tiêu chí còn lại ĐẠT: chạy xong 52,75/21,55/17,51/24,92s, grounded, provider_used=false, không ghi D (SHA 062ec090… không đổi, 2 snapshot 0 thay đổi), fail-closed chứng minh được (6 khóa cloud còn trong env, create_synthesis_provider() → None, 44 mẫu mạng = 0 kết nối).
- Ticket trước: E2 — Fix synthesis theo E1 + chạy lại B1–B5 (B4 loại), verdict CHƯA ĐẠT (báo cáo `docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md`, commit `4aa6d68`).

