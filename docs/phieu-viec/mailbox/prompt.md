# Ticket hiện tại — Migration vector offline sang ONNX fp32 (Bước A)

> OMP đọc kỹ `QUY-UOC.md` trước. Ticket này CHỈ LÀM Bước A. Xong Bước A thì
> commit + push + cập nhật `trang-thai.md` thành `xong-cho-duyet`, rồi DỪNG.
> Không tự ý làm Bước B (apply) hay Bước C (worker verification).

## Bối cảnh

- Branch: `phieu-viec/rag-fix1`. Không đụng `main`.
- Diagnostic ONNX worker timeout (commit `1488e77`, đã ĐẠT) kết luận: index hiện
  có 340 vector fingerprint PyTorch (`ce7fb53f…`), backend ONNX fp32 có fingerprint
  khác (`016c5255…`, runtime `onnxruntime-int8`) → worker coi cả 340 là pending và
  re-embed toàn index trong init, vượt timeout 300s.
- Hướng sửa đã chốt: migration vector offline riêng (như backfill provenance),
  dry-run trước, batch + resume, backup mới bắt buộc vì có ghi index.
- KHÔNG được trộn/nới fingerprint PyTorch và ONNX (dù fp32 cosine = 1.0 với PyTorch).

## Bước A — Viết script + test + dry-run, rồi DỪNG chờ duyệt

### A1. Script `scripts/migrate_vectors_to_onnx.py`

- Mặc định **dry-run** (không có flag `--apply`):
  - Đếm số vector pending theo fingerprint ONNX hiện tại.
  - In fingerprint cũ (PyTorch) và fingerprint mới (ONNX fp32).
  - Ước tính thời gian migrate (dựa trên tốc độ đo được hoặc hằng số thận trọng).
  - **KHÔNG ghi bất kỳ byte nào vào index.**
- Với `--apply` (Bước B mới dùng, Bước A chỉ viết code, KHÔNG chạy):
  - Chỉ chạy khi `BGE_BACKEND=onnx` được đặt tường minh (fail-closed nếu không).
  - Batch khoảng 10 chunk, commit từng batch.
  - Có progress log + resume (chạy lại bỏ qua chunk đã đúng fingerprint).
  - Bỏ qua vector đã đúng fingerprint ONNX.
- Trước mọi lần ghi thật: script phải tự kiểm tra backup mới của index tồn tại,
  thiếu backup thì từ chối chạy.

### A2. Unit test

- Test đếm pending đúng theo fingerprint.
- Test dry-run không ghi index (so checksum/size index trước-sau).
- Test resume: chạy lần 2 bỏ qua chunk đã migrate.

### A3. Dry-run trên index thật

- Chạy dry-run trên index canary thật của máy (read-only, không `--apply`).
- Ghi báo cáo vào `docs/phieu-viec/ket-qua/FIX2_migrate-onnx-dryrun.md`:
  hostname, đường dẫn index, kích thước index, số pending, fingerprint cũ/mới,
  ước tính thời gian.

### A4. Bàn giao

- Commit RIÊNG cho Bước A, push branch `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md`: `xong-cho-duyet` + ghi commit SHA + tóm tắt số liệu.
- DỪNG. Chờ Muse review xong mới có Bước B.

## Ngoài phạm vi Bước A

- `--apply` trên index thật (Bước B, cần duyệt riêng).
- Chạy worker với `BGE_BACKEND=onnx` để verify hết timeout (Bước C).
- Mọi thay đổi fingerprint semantics.
