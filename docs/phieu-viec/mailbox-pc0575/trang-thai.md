# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: p4-deploy-constants
Ghi chú: [2026-09-29 17:33 +07] MỐC 2: TÁI TẠO ĐƯỢC fingerprint — quét 648 tổ hợp 9 trường (script `docs/phieu-viec/ket-qua/p4-tai-tao-fingerprint.py`): duy nhất 1 bộ hiệu dụng {checksum `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093` (sidecar FIX2 máy nhà), device cpu, dim 1024, cosine, model_id BAAI/bge-m3, normalized true, revision 5617a9f6…81, runtime onnxruntime-int8, runtime_version 1.28.0} → `016c5255…6274fb`. Đối chứng: checksum cây onnx PC0575 (728c9eb7) → 8274fbb0… (khác); cây onnx PC0575 đo tươi = 728c9eb7. | MỐC 1: [2026-09-29 17:20 +07] fingerprint đầy đủ từ index (mode=ro) `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` (107.331 dense+sparse); DB lưu runtime=onnxruntime-int8, runtime_version=1.28.0, model_id=BAAI/bge-m3, revision 5617a9f6…, created 2026-09-26T04:43:25Z; KHÔNG lưu artifact_checksum/device. | MỐC 0: [2026-09-29 17:16 +07] OMP nhận P4 (chỉ đọc + tính toán; cấm đổi env máy, cấm ghi index, cấm embed).
Commit mới nhất: `489f3ff`
Đường dẫn báo cáo P3: `docs/phieu-viec/ket-qua/p3-bao-cao.md`
Đường dẫn prompt P4: `docs/phieu-viec/mailbox-pc0575/prompt.md`
