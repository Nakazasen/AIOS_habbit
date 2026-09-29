# Vé P5 — Mang cây ONNX fp32 từ máy nhà sang PC0575 + bật readiness (KDTVN-PC0575)

## Bối cảnh (verdict P4 của Muse, 2026-09-29 ~17:35 +07)

- P4 **ĐẠT**: bộ hằng số deploy đã chứng minh tái tạo đúng fingerprint
  `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`
  (Muse verify độc lập: recompute sha256 tiền ảnh JSON khớp chuỗi mục tiêu;
  commit `1c74ea6` chứa báo cáo + script + output; chuỗi commit tuyến tính).
- Bộ hằng số: checksum `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`,
  cây `models/bge-m3-onnx-fp32` (máy nhà `h410asrock`, FIX2 vòng 3), onnxruntime `1.28.0`
  (PC0575 đang cài đúng bản này), device `cpu`, model `BAAI/bge-m3` rev `5617a9f6…81`;
  cơ chế đặt checksum = sidecar `models\bge-m3-onnx-fp32.sha256` (khớp sẵn mã,
  không cần đụng env).
- **Sự thật quan trọng:** cây đúng hiện **CHỈ có trên máy nhà**. Bản cây mà Muse kiểm
  được trên Drive (`hf_models/bge-m3-5617a9f/onnx`) hash `6a8d3a65…` — **khác**;
  cây local PC0575 hash `728c9eb7…` — **khác**. BẮT BUỘC mang đúng bytes từ máy nhà.
  **Cấm** "cho chạy được" bằng checksum cây local (`728c9eb7…` → fingerprint
  `8274fbb0…` ≠ sealed → app coi 107.331 vector hết hạn → embed lại hàng loạt
  ~74 giờ, ghi lên production index).

## Nhiệm vụ OMP

### Phase 0 — Gate nhận cây (nhanh, chỉ đọc/tải)

1. User sẽ upload lên Drive AIOS_Data hai thứ (lấy từ máy nhà):
   - `model/bge-m3-onnx-fp32.zip` — nén từ thư mục `models\bge-m3-onnx-fp32`
     trên máy nhà (gồm `model.onnx`, `model.onnx_data`, tokenizer,
     `sparse_linear.npy` + bias — nguồn FIX2 vòng 3);
   - `model/bge-m3-onnx-fp32.sha256` — file text chứa
     `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`.
2. Kiểm tra Drive: nếu **CHƯA có** → cập nhật mailbox
   `Trạng thái: \`cho-muse\``, ghi chú "P5 Phase 0: chờ user upload cây ONNX từ
   máy nhà lên Drive AIOS_Data/model/; dừng đúng gate, không làm gì thêm",
   rồi **DỪNG**. (Cron Muse sẽ thấy cờ và báo user.)
3. Nếu có: tải về, giải nén vào `models\bge-m3-onnx-fp32` trong repo
   `D:\Sandbox\AIOS_habbit` (tạo thư mục `models\` nếu chưa có), rồi tính
   `sha256_model_tree` của cây vừa giải nén — **PHẢI** bằng
   `9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`.
   Lệch → **DỪNG** + `cho-muse` (cấm đặt checksum bừa).

### Phase 1 — Đặt sidecar + bật readiness

4. Kiểm tra env **CHỈ ĐỌC** (`[Environment]::GetEnvironmentVariable(...,"Machine")`
   và `"User"`): nếu `AIOS_BGE_ONNX_MODEL_PATH` / `AIOS_BGE_ONNX_MODEL_CHECKSUM`
   đang được đặt ở mức Machine/User → **DỪNG ở gate**, báo `cho-muse` kèm giá trị
   đọc được. (Env thắng sidecar trong `resolve_onnx_checksum` — không tự
   xóa/sửa env persistent của máy.)
5. Đặt sidecar `models\bge-m3-onnx-fp32.sha256` chứa đúng
   `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`.
   Không đặt/không sửa bất kỳ biến môi trường nào khác.
6. Snapshot SHA-256 file index production
   (`local_runs\workspace_chat_rag_v2_production\...\library.sqlite`) **trước**
   khi chạm app.
7. Khởi động lại app/worker (vé này **được phép restart** — mục tiêu là bật
   readiness), kiểm tra:
   - BGE worker khởi động được (`verify_model_tree` pass, không
     `local model checksum mismatch`);
   - `_expected_backend_fingerprint` trong log/config PHẢI =
     `016c5255…` (khớp sealed). Nếu ra mã khác → **DỪNG NGAY**, cấm mọi embed,
     báo `cho-muse`.
   - readiness: mong **171/171** nguồn `temporary` chuyển `ready` (ghi số thực
     tế; chênh thì giải thích).
8. Snapshot SHA-256 index **sau**: PHẢI khớp trước (chứng minh không ghi ngoài
   ý muốn khi bật readiness). Nếu app ingest thêm chunk mới trong lúc readiness
   → ghi rõ số lượng + lý do, không giấu.
9. Báo cáo `docs/phieu-viec/ket-qua/p5-bao-cao.md` (gồm: hash cây đo được, nội
   dung sidecar, log worker + fingerprint kỳ vọng, readiness trước/sau, SHA
   index trước/sau), commit riêng trên `phieu-viec/rag-fix1`, **KHÔNG** merge
   `main`.

## Tiêu chí ĐẠT

- Cây đúng hash `9f81075f…`; sidecar đúng vị trí + nội dung; worker khởi động;
  fingerprint kỳ vọng = sealed `016c5255…`; readiness 171/171 (hoặc chênh có
  giải thích); SHA index trước/sau khớp (mọi thay đổi được giải thích); không
  đổi env máy; không merge `main`.

## Xong việc

OMP cập nhật `docs/phieu-viec/mailbox-pc0575/trang-thai.md`:
`Trạng thái: \`xong-cho-duyet\``, `Ticket hiện tại: p5-mang-cay-onnx`,
đường dẫn báo cáo, commit SHA. Cron Muse sẽ review.
