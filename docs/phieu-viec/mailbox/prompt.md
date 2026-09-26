# Ticket D2 — Ingest apply 83 file + embed vector ONNX (ghi index thật, có backup)

Ngày viết: 2026-09-26 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- D1 (`e3eafc8`, ĐẠT): 83 file missing = 6 failed + 77 chưa từng ingest.
  Dry-run +1765 chunk / 1467 retrievable. B1/B2/B3/B5 có đáp án trong file
  missing; B4 không có mã ví dụ trong bất kỳ file nào (ground truth lệch).
- User đã duyệt apply (autopilot 2026-09-26: dry-run + backup là đủ, không cần
  duyệt từng bước).

## Phase 1 — Backup (fail-closed)

1. Backup `library.sqlite` → `library.sqlite.bak-<timestamp>` (file sibling,
   cùng thư mục với index canary trong D1).
2. `integrity_check` trên backup phải `ok`, dung lượng > 0.
   Không đạt → DỪNG ngay, báo lỗi, không làm tiếp.

## Phase 2 — Ingest text (dedupe)

1. Ingest 83 file vào index canary (đường dẫn như D1, máy `h410asrock`).
2. **Dedupe**: D1 phát hiện 580 chunk trùng text với index cũ (33%) —
   không insert trùng (so theo text hash). Ghi số đã skip vào báo cáo.
3. **6 file failed** (`bge_worker_prepare_stdout_eof`, gồm file đáp án B1
   fail 34 lần): điều tra nguyên nhân, retry với fix; file nào vẫn fail thì
   liệt kê riêng, không để crash cả batch.
4. Ca lẻ `wsc-927d7635…` (ledger `ready` nhưng không trong index): đối chiếu
   khi ingest, ghi kết quả vào báo cáo.
5. Batch + resume: ngắt giữa chừng chạy lại không ingest trùng.

## Phase 3 — Embed vector cho chunk mới (ONNX fp32)

1. Embed các chunk mới bằng backend ONNX fp32 (`BGE_BACKEND=onnx`,
   fingerprint `016c5255…`) — khớp với 340 vector đã migrate ở Bước B.
2. Batch + resume theo mẫu `scripts/migrate_vectors_to_onnx.py`.
3. Không đụng vector cũ (PyTorch lẫn ONNX).

## Phase 4 — Verify

- Document count ~108 (25 cũ + 83 mới, trừ ca lẻ); chunk/retrievable khớp
  kỳ vọng D1 (trừ dedupe).
- Pending vector = 0. `integrity_check` trên live = ok.
- **Không dọn XML** trong ticket này (lấy baseline B trên corpus đầy đủ trước).

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_ingest-D2-apply.md`
  (hostname, SHA, số liệu từng phase: backup bytes, chunk thêm/skip, file
  failed còn lại, pending).
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi commit SHA + đường dẫn
  báo cáo), rồi **DỪNG**.
