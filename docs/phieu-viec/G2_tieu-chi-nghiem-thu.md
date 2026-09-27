# G2 — Tiêu chí nghiệm thu

Ngày lập: 2026-09-27 (Muse, theo lệnh user).
Không merge `main` khi chưa có đèn xanh của user.

## 1. Điều kiện vào G2

- G1 migration sạch: 99.003/99.003 vector ONNX, pending 0, `integrity_check=ok`,
  fingerprint ONNX `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`.
- Vé 0.3 đã duyệt.

## 2. Phạm vi G2

1. Commit riêng 3 fix retrieval của OMP (đang local, chưa commit):
   - spawn worker kèm `PYTHONPATH=<root>/src` (`.venv` mất editable-install),
   - `.env` thêm `BGE_BACKEND=pytorch` tường minh (không đụng default ONNX),
   - `RouterRequest` thiếu `safety_mode_label` → router chặn mọi provider.
2. Cổng "chuẩn bị" kiểm tra fingerprint theo backend (đổi backend là liệt
   thì phải tự phát hiện, không liệt âm thầm).
3. Backfill 3/74 tài liệu thiếu embedding + production `tri_thuc`.
4. Query thật dưới default ONNX: ~10 câu (5 LSU + 5 case lỗi/bảng mã);
   không XML thô; synthesis giữ mã/số/tên file/trích dẫn;
   có latency/timeout/abstain và phân loại retrieval/synthesis.
5. UI ghi rõ source/document/chunk/vector/index.
6. Mọi vé đụng backend đều có test "tắt GPU vẫn chạy".
7. Production/MOM tách khỏi G1; không trộn trạng thái hai index.

## 3. Mẫu deploy chuẩn (áp dụng mọi deploy sau này)

Theo lệnh user 2026-09-27, mọi lần deploy kho/app sau này tuân đúng 2 vé mẫu:

- **Vé P1 "đóng dấu kho thử thành kho thật"** (`VE_P1_ve-mau-dong-dau-kho-that.md`):
  kiểm toàn vẹn kho canary → copy sang production
  (`workspace_chat_rag_v2_production/workspace_chat.sqlite`) → app đọc thử
  B1–B5 đạt → mới đóng dấu là "kho chạy thật". Cấm app đọc kho đang nhúng dở.
- **Vé P2 "mang sang máy công ty"** (`VE_P2_ve-mau-may-cong-ty.md`):
  copy đúng 1 file sqlite + pin đúng 3 thứ (mã code đúng commit,
  `onnxruntime==1.28.0`, model BGE-M3 đúng revision
  `5617a9f61b028005a4858fdac845db406aefb181` kéo mạng) → chạy CPU-only,
  không GPU → smoke test B1–B5 đạt trên máy công ty mới đóng vé.

Tóm tắt một dòng: **đóng dấu → copy + pin 3 thứ + smoke test**.
