# Vé P4 — Chốt "bộ hằng số deploy" tái tạo đúng fingerprint `016c5255…` (KDTVN-PC0575)

## Bối cảnh (verdict P3 của Muse, 2026-09-29)

- P3 **ĐẠT** ở vai chẩn đoán: app đọc **đúng** index production
  (`local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`,
  SHA-256 `062ec090…ef8ca` khớp P2); readiness 0/171 do thiếu biến môi trường ONNX
  (`AIOS_BGE_ONNX_MODEL_PATH`, `AIOS_BGE_ONNX_MODEL_CHECKSUM`) khiến BGE worker không
  khởi động được → cổng fail-closed → mọi nguồn `failed` (`preparation_init_bge_worker_model_verify_failed`).
- "68 tài liệu cần xử lý" là ảnh chụp **giữa lượt chạy** (16:45→16:48 hỏng dần 68→171,
  cùng một đợt lỗi). 171 nguồn `temporary` **thật sự chưa có vector** trong index
  (`retrievable=1` = 0) — không liên quan 25.813 chunk `retrievable=0` đã biết ở P2.
- **Nguy cơ lớn (P3 mục 6):** vector ONNX trong index mang định danh `016c5255…`;
  đặt env "cho chạy được" bừa thì `_expected_backend_fingerprint` ra `8274fbb0…`
  (khác) → app coi **toàn bộ 107.331 vector cũ là hết hạn** → embed lại hàng loạt,
  ghi vào production index. **Cấm đặt env trước khi chốt được hằng số đúng.**
- OMP đã thử {checksum manifest `b1d887e0…`, checksum cây hiện tại `728c9eb7…`, rỗng}
  × {onnxruntime `1.28.0`, `1.29.0`} → **không tổ hợp nào tái tạo được `016c5255…`**.
  Lưu ý: hàm `SemanticModelDescriptor.fingerprint`
  (`src/aios_habit/rag_v2/semantic.py`) băm **9 trường**
  (artifact_checksum, device, dimension, distance, model_id, normalized,
  revision, runtime, runtime_version) — OMP mới chỉ quét 2 trường.

## Nhiệm vụ OMP — CHỈ ĐỌC + TÍNH TOÁN, CẤM ĐỔI ENV MÁY, CẤM GHI INDEX, CẤM EMBED

1. Đọc fingerprint **đầy đủ** (64 ký tự hex) từ một dòng đã seal
   (`model_fingerprint = '016c5255%'`) trong production index — truy vấn **read-only**
   (`mode=ro`), không chạm index.
2. Tìm provenance lịch sử FIX2: kiểm tra các bảng metadata/manifest trong
   `library.sqlite` (read-only) xem có lưu `artifact_checksum` / `device` /
   `runtime_version` / `model_id` / `revision` của lượt migration không.
   Nếu không có → ghi rõ "không có provenance trong DB", không đoán.
3. Tái tạo bằng `SemanticModelDescriptor.fingerprint` (thuần tính toán Python,
   không cần model): quét các ứng viên cho từng trường —
   `artifact_checksum` ∈ {`sha256:b1d887e0…`, `sha256:728c9eb7…`, rỗng, mọi checksum
   tìm được ở bước 2}, `runtime_version` ∈ {`1.28.0`, `1.29.0`, rỗng, version thực tế
   của `onnxruntime` đang cài}, `device` ∈ {`cpu`, `cuda`, rỗng},
   `model_id` ∈ {`BAAI/bge-m3`, các biến thể trong code},
   `revision` ∈ {đầy đủ `5617a9f61b028005a4858fdac845db406aefb181`, rút gọn, rỗng},
   `dimension` = 1024, `distance`/`normalized` mặc định.
   Mục tiêu: ra **đúng chuỗi 64 ký tự** ở bước 1. Ghi lại tổ hợp thắng + script.
4. Làm rõ mâu thuẫn manifest: `src/aios_habit/bge_m3_manifest.json` và
   `packaging/models/bge_m3_manifest.json` đang giữ `b1d887e0…` trong khi cây onnx
   hiện tại checksum `728c9eb7…` (đổi sau khi P2-B7b thêm `sparse_linear.npy`) —
   manifest này là của bản int8 hay fp32? Ghi rõ trong báo cáo.
5. **Không đổi bất kỳ biến môi trường nào trên máy; không restart app; không ghi
   index; không embed; không merge `main`.**

## Tiêu chí ĐẠT

- Báo cáo `docs/phieu-viec/ket-qua/p4-bao-cao.md` gồm:
  - bộ hằng số deploy đầy đủ: {đường dẫn thư mục onnx, checksum đúng định dạng
    `sha256:<hex>`, phiên bản onnxruntime, device, model_id/revision} **đã chứng minh
    tái tạo đúng fingerprint 64 ký tự** (kèm script + output);
  - cơ chế đặt checksum sẽ dùng ở vé sau: env `AIOS_BGE_ONNX_MODEL_CHECKSUM`
    hay sidecar `local_runs\retrieval_models\bge-m3-5617a9f\onnx.sha256`
    (ưu tiên cách khớp sẵn cơ chế sidecar của mã);
  - kết luận manifest ở bước 4.
- Nếu không tìm được provenance và quét hết không ra: báo cáo ghi rõ đã thử
  những gì, kết luận "chưa xác định được", đề xuất bước tiếp theo (ví dụ lấy log
  FIX2 từ máy nhà) — **không được đoán một checksum "cho chạy được"**.

## Xong việc

OMP cập nhật `docs/phieu-viec/mailbox-pc0575/trang-thai.md`:
`Trạng thái: \`xong-cho-duyet\``, `Ticket hiện tại: p4-deploy-constants`,
đường dẫn báo cáo, commit SHA. Cron Muse sẽ review.
