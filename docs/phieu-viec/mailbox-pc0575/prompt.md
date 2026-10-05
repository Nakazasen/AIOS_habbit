# Vé RECOVER-RUNTIME-PC0575 — Khôi phục dữ liệu runtime production đã mất

**Mức ưu tiên:** cao nhất (chặn toàn bộ vé đo/app trên máy công ty).
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Role OMP gợi ý:** SMOL/TINY (vé kiểm tra nhanh, chủ yếu đọc + liệt kê).
**Xếp hàng:** vé này xong → phát hành lại `SPEED-COLDSTART-PC0575` (file vé gốc: `docs/phieu-viec/mailbox-pc0575/prompt-queue-speed-coldstart-pc0575.md`) để đo phần còn thiếu.

## Bối cảnh

Sáng 2026-10-05 user dọn ổ C và D → thư mục `D:\Sandbox\AIOS_habbit\local_runs\` bị mất, gồm:
- `local_runs\workspace_chat_rag_v2_production\` — index production SHA `e54c7745…`, **2.842.415.104 byte**, mtime 2026-10-01 15:46 (kèm ledger + log worker).
- `local_runs\retrieval_models\bge-m3-5617a9f` — model embedding.

Audit chính thức `python -B -m aios_habit.workspace_chat_rag_v2_deployment` → `Status: FAIL` / `deployment_model_unavailable`.
Bản còn lại `C:\AIOS_p5\library.sqlite.bak-20260930` (2.552.659.968 byte, SHA `062ec090…`) là bản cũ 29–30/09, **KHÔNG phải production** — cấm dùng thay.

Chi tiết: `docs/phieu-viec/ket-qua/speed-coldstart-pc0575.md` (mục cập nhật 15:32).

## Việc cần làm (theo thứ tự)

### Bước 1 — Kiểm tra Recycle Bin (làm ĐẦU TIÊN, ~5 phút)
- Mở Recycle Bin của **cả ổ C và ổ D**, tìm: file `*.sqlite*` cỡ ~2,8 GB, thư mục `retrieval_models\bge-m3-5617a9f`, thư mục `local_runs\workspace_chat_rag_v2_production`.
- Nếu tìm thấy file khớp (size ≈ 2.842.415.104 byte): tính SHA-256, đối chiếu 8 ký tự đầu với `e54c7745`.
  - Khớp → **khôi phục về đúng path cũ** `D:\Sandbox\AIOS_habbit\local_runs\...`, verify lại SHA + `Test-Path`, chạy audit deployment → PASS thì sang Bước 5.
  - Không khớp → ghi lại path + size + SHA vào báo cáo, KHÔNG khôi phục mù.

### Bước 2 — Kiểm tra antivirus/quarantine
- Kiểm tra Windows Defender Protection History + quarantine của AV đang dùng: có file nào trong `local_runs` bị cách ly sáng nay không. Nếu có → ghi tên file + thời gian, KHÔNG tự restore khi chưa rõ (ghi vào báo cáo để Muse quyết).

### Bước 3 — Quét toàn máy tìm bản copy khác
- Quét C, D và mọi ổ USB/ổ ngoài đang cắm: tìm mọi file `*.sqlite*` ≥ 1 GB. Với mỗi file ghi: path đầy đủ, size (byte), SHA-256 (8 ký tự đầu).
- Đối chiếu với 2 dấu vân tay đã biết: `e54c7745…` (production cần tìm), `062ec090…` (backup cũ — đã biết ở `C:\AIOS_p5\`).
- Kiểm tra thêm các path từng chứa index: `C:\AIOS_workspace_chat_rag_v2_production\`, `C:\AIOS_habit_index_ve03\`, `C:\AIOS_p5\`.

### Bước 4 — Kiểm tra khả năng tải lại model (chỉ kiểm tra, CHƯA tải)
- Kiểm tra kết nối tới Hugging Face + ước tính tải được model `bge-m3` đúng revision `5617a9f` không. Chỉ báo kết quả, chưa tải vội (chờ Muse quyết sau khi rõ tình trạng index).

### Bước 5 — Báo cáo + verdict
- Viết `docs/phieu-viec/ket-qua/recover-runtime-pc0575.md`: liệt kê từng bước đã làm + bằng chứng (path, size, SHA).
- **KHÔI PHỤC ĐƯỢC** (index đúng SHA `e54c7745…` đã về đúng path + audit deployment PASS) → `xong-cho-duyet`.
- **KHÔNG KHÔI PHỤC ĐƯỢC** → `cho-muse`, kèm danh sách đầy đủ mọi nguồn còn lại trên máy (backup cũ, file Drive đã tải dở, v.v.) để Muse quyết hướng tiếp theo (dùng backup cũ tạm / tải lại từ Drive / rebuild).

## Cấm kỵ
- **Không xóa thêm bất cứ file/thư mục nào** trên máy trong vé này.
- Không đụng tới `C:\AIOS_p5\library.sqlite.bak-20260930`.
- Không copy backup cũ đè lên path production rồi gọi là "đã khôi phục".
- Không rebuild/nhúng lại index khi chưa có lệnh của Muse.

## Điều kiện nghiệm thu
- Báo cáo liệt kê đủ 4 bước với bằng chứng cụ thể (path + size + SHA).
- Nếu khôi phục: SHA index sau khôi phục = `e54c7745…` (8 ký tự đầu), audit deployment `Status: PASS`.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`, không force-push.
