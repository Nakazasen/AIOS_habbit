# Ticket hiện tại — Migration vector offline sang ONNX fp32 (Bước B: apply)

> OMP đọc kỹ `QUY-UOC.md` trước. Ticket này CHỈ LÀM Bước B. Xong Bước B thì
> commit + push + cập nhật `trang-thai.md` thành `xong-cho-duyet`, rồi DỪNG.
> Bước A đã ĐẠT (commit `ea195c1`, đã review). Không tự ý làm Bước C
> (chạy worker với `BGE_BACKEND=onnx` để verify hết timeout) — đó là ticket riêng.

## Bối cảnh

- Branch: `phieu-viec/rag-fix1`. Không đụng `main`.
- Script: `scripts/migrate_vectors_to_onnx.py` (Bước A). Dry-run đã xong:
  340 pending / 340 retrievable / 0 đã migrate, fingerprint ONNX `016c5255…`,
  PyTorch `ce7fb53f…`, index 9.764.864 byte. Ước tính cold ~2,15 giờ,
  warm ~10,2 phút.
- User đã duyệt chạy `--apply` trên index thật (2026-09-26).

## Bước B — Backup mới + --apply, rồi DỪNG chờ duyệt

### B1. Backup mới (bắt buộc, trước mọi lần ghi)

- Copy index canary thật sang file sibling:
  `library.sqlite.bak-<YYYYMMDD-HHMM>` (giờ máy local), đặt cạnh index.
- Chạy `PRAGMA integrity_check` trên file backup → phải ra `ok`.
  Không `ok` thì DỪNG, báo lỗi, không chạy tiếp.
- Ghi tên file backup + kết quả integrity vào báo cáo.

### B2. Chạy `--apply`

- Lệnh (đúng thứ tự):
  ```
  BGE_BACKEND=onnx PYTHONPATH=D:/Sandbox/AIOS_habbit/src \
  .venv/Scripts/python.exe scripts/migrate_vectors_to_onnx.py \
  local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --apply
  ```
- Batch 10, commit từng batch, progress từng batch (script đã làm sẵn).
- Giám sát tốc độ: nếu chậm gấp 2 lần ước tính warm (~20 phút tổng) thì DỪNG,
  giữ nguyên hiện trạng (resume được), báo cáo tình hình, chờ chỉ đạo.
- Nếu bị ngắt giữa chừng: chạy lại cùng lệnh, script tự resume bỏ qua chunk
  đã migrate.

### B3. Verify sau apply

- Chạy lại dry-run (không `--apply`): pending phải = 0.
- Đếm vector fingerprint ONNX `016c5255…` = 340; vector PyTorch `ce7fb53f…`
  vẫn còn đủ 340 (không bị ghi đè/xóa).
- `PRAGMA integrity_check` trên index thật → `ok`.

### B4. Báo cáo + bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX2_migrate-onnx-apply.md`, gồm:
  hostname, đường dẫn index, tên file backup + integrity, thời gian chạy từng
  batch (hoặc tổng), số chunk đã migrate, số liệu verify B3.
- Commit RIÊNG cho Bước B, push branch `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md`: `xong-cho-duyet` + ghi commit SHA + đường dẫn báo cáo.
- DỪNG. Chờ review xong mới có Bước C.

## Dọn kèm (không bắt buộc, nếu tiện thì làm trong cùng commit)

3 nit từ review Bước A:
- Xóa 2 hằng số chết `BGE_M3_MODEL_PATH` / `BGE_M3_CHECKSUM` trong script
  (code thực tế dùng `resolve_onnx_checksum`).
- Thêm comment giải thích chỗ check `resolve_bge_backend_name(...) != "onnx_int8"`
  (tên nội bộ legacy của backend fp32).

## Ngoài phạm vi Bước B

- Chạy worker/chat với `BGE_BACKEND=onnx` (Bước C, ticket riêng sau duyệt).
- Mọi thay đổi fingerprint semantics hay runtime.
