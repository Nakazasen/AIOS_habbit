# B8 — Báo cáo nghiệm thu P2 (máy công ty KDTVN-PC0575)

- Ngày: 2026-09-29
- Máy: `KDTVN-PC0575` (CPU-only, không GPU)
- Repo: `D:\Sandbox\AIOS_habbit`, nhánh `phieu-viec/rag-fix1`
- Kết luận: **P2 ĐẠT** — kho production chạy được trên máy công ty, CPU-only.

## 1. Index production (không đổi suốt P2)

- File: `local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- Size: `2552659968` byte
- SHA-256: `062EC090644FB4EC09D2FB6388F3175E988E48D63061B04E6C27BBED334EF8CA`
- SHA trước smoke = SHA sau smoke = SHA seal → smoke không ghi gì vào index.

## 2. Manifest (B5)

- `config\workspace_chat_rag_v2.local.json`
- `activation_state=activated`, `run_id=P2-KDTVN-PC0575-2026-09-29`
- CPU-only, fail-closed, không fallback.

## 3. Môi trường (B2)

- Python `3.11.15`, `onnxruntime==1.28.0` (đồng bộ với seal).

## 4. Fingerprint (B6)

- Dense/sparse cùng `107671` dòng; fingerprint `016c5255...`: `107331` dòng/bảng.
- 340 dòng/bảng mang fingerprint `ce7fb53f...` (backend PyTorch cũ) = **dead weight**,
  trùng `chunk_id` 100% với bản ONNX, mọi query lọc theo `model_fingerprint` → vô hại.
  Không xóa (xóa = ghi lên index production, không đáng).

## 5. Pending (B7a)

- `chunks total=133144`; ONNX distinct `107331`.
- `25813` chunk thiếu ONNX đều `retrievable=0`; chunk `retrievable=1` thiếu ONNX: `0`.
- Không re-embed trên máy công ty.

## 6. Vector equivalence (thay cho fingerprint seal)

- Fingerprint seal không tái tạo được trên PC0575 (cây file phụ khác máy nhà).
- Kiểm tương đương vector trực tiếp: 5/5 chunk cosine = **1.0** (ngưỡng 0.999).
- Model PC0575 cho vector giống hệt vector đã seal → không cần lôi cây model từ máy nhà.

## 7. Smoke B7b — ĐẠT

- Exit `0`, `status: OK`, thời gian ~456s.
- B1/B2/B3/B5 đều `pass: true`, `missing: []`, `eligible_chunks: 106982`.
- Sparse head: `sparse_linear.npy` (1024,) + bias `0.04519653`, trích từ
  `sparse_linear.pt` gốc HF rev 5617a9f, SHA-256 verify khớp.
- Checksum cây model sau khi thêm sparse head:
  `sha256:728c9eb7ee48a66ac4b6d567e3408433398911a6abcce9685d8a048eb8766baa`
  (chứng minh chỉ đổi vì thêm 2 file: hash 8 file cũ = checksum cũ).
- `verify_model_tree()` đã chạy thật và chấp nhận checksum mới.

## 8. Provider gate

- `provider_guard: create_synthesis_provider() is None` — tuyến nội bộ,
  không gửi dữ liệu công ty ra ngoài (DATA_POLICY local_only).

## 9. Ghi chú deploy LAN

- Các hằng checksum pin trong code (`BGE_M3_CHECKSUM`, `EXPECTED_MODEL_CHECKSUM`…)
  KHÔNG nằm trên đường verify của backend ONNX (smoke chứng minh) → không cần sửa code.
- Nhánh ONNX đọc checksum từ env `AIOS_BGE_ONNX_MODEL_CHECKSUM`.
  Khi deploy LAN chính thức, set env này persistent (system env hoặc launcher),
  giá trị: `sha256:728c9eb7ee48a66ac4b6d567e3408433398911a6abcce9685d8a048eb8766baa`.
