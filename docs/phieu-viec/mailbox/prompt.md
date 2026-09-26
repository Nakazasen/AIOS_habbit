# Ticket E4 — Chuyển default backend sang ONNX fp32 trên branch

Ngày viết: 2026-09-27 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- E3 (`6660e7e`, ĐẠT — Muse review 2026-09-27): extractor dọn XML sau flag
  `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` (mặc định tắt), 27 test extractor đạt,
  canary chỉ đọc `xmlns` 67→0, `<p:sld` 42→0, không ghi index.
- E2 (`a83f8ff4`, ĐẠT): synthesis đã fix claim budget + exact-identifier rescue;
  B1/B2/B3/B5 read-only ONNX đúng.
- FIX 2 vòng 3–4 (ĐẠT): ONNX fp32 nhanh 2.92x, recall 1.0, init ~4–10s (PyTorch
  ~45–97s). Migration bước B (23ca36e): 340/340 chunk đã có vector ONNX
  fingerprint `016c5255…` (PyTorch `ce7fb53f…` giữ nguyên, không xóa).
- Bước C (cc12d67): backend ONNX init 3.94s, pending 0, B1–B5+H3 không
  abstain/timeout, index read-only nguyên vẹn.
- Chế độ tự lái toàn phần (user 2026-09-26): tự quyết mọi quyết định kỹ thuật,
  không hỏi; sai thì revert commit và viết ticket sửa.

## Việc cần làm

1. **Đổi default backend sang ONNX fp32**: khi `BGE_BACKEND` không set (hoặc
   set `auto`) → backend mặc định là ONNX fp32 (`bge-m3-onnx-fp32`), không còn
   PyTorch.
2. **Giữ override**: `BGE_BACKEND=pytorch|onnx|onnx_int8` vẫn ép backend tường
   minh như cũ. `onnx_int8` giữ nguyên fingerprint/semantics riêng của nó.
3. **Fail-closed khi thiếu model**: nếu đường giải default cần ONNX fp32 mà
   thư mục model/checksum không đạt (file `model.onnx` thiếu, checksum
   sidecar/env `AIOS_BGE_ONNX_MODEL_CHECKSUM` không khớp) → RAISE lỗi rõ ràng
   (nói đúng đường model thiếu + cách override về `pytorch`), KHÔNG fallback
   lặng lẽ, KHÔNG treo, KHÔNG init nửa chừng.
4. **Fingerprint semantics không đổi**: đổi default không được làm thay đổi
   fingerprint của vector đã migrate (bước B/C đã verify 340/340 cả hai
   fingerprint). Kiểm tra: mở index thật ở `mode=ro`, không set
   `BGE_BACKEND`, đếm `pending == 0` cho backend default — nếu >0 thì DỪNG và
   báo lại, không tự re-embed hàng loạt.
5. **Test**: unit test giải backend (default→onnx, override pytorch/onnx_int8,
   model thiếu→raise fail-closed); chạy pytest liên quan + full suite (ghi
   trung thực lỗi môi trường cũ nếu có, không PASS giả).
6. **Đo trên index thật (chỉ đọc)**: init default (không env) đo thời gian;
   chạy 1–2 câu B (B1, B5) qua đường ONNX, ghi latency + không abstain;
   `PRAGMA integrity_check` và kích thước file index trước/sau giữ nguyên.

## Điều cấm

- KHÔNG merge vào `main`. KHÔNG ingest, KHÔNG `--apply`, KHÔNG ghi index thật,
  KHÔNG backfill — ticket này chỉ đổi default trong code + đo chỉ đọc.
- KHÔNG bật/tắt các flag khác (XML cleanup giữ mặc định tắt; drain flag giữ tắt).
- Nếu phát hiện default ONNX gây re-embed hàng loạt hoặc timeout (pending > 0) →
  DỪNG, revert phạm vi, báo cáo rõ số liệu.

## Bàn giao

- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
  (hostname, SHA code lúc chạy, chỗ đổi default, kết quả test, số pending
  before/after, latency init + B1/B5 qua default, integrity index).
- Commit **riêng** + push `phieu-viec/rag-fix1`, không đụng `main`.
- Cập nhật `trang-thai.md` → `xong-cho-duyet` (ghi commit SHA + đường dẫn báo cáo),
  rồi **DỪNG**.
