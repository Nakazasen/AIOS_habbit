# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong-cho-duyet`
Ticket hiện tại: p4-deploy-constants
Ghi chú: [2026-09-29 17:28 +07] MỐC 3 (XONG): báo cáo `docs/phieu-viec/ket-qua/p4-bao-cao.md` + script `p4-tai-tao-fingerprint.py` + output `p4-ket-qua-tai-tao.json` đã commit. Bộ hằng số deploy tái tạo `016c5255…6274fb`: checksum `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093` (sidecar cây ONNX fp32 máy nhà), device cpu, dim 1024, cosine, model_id BAAI/bge-m3, normalized true, revision 5617a9f6…81, runtime onnxruntime-int8, runtime_version 1.28.0 (bản đang cài trên PC0575). Cơ chế đặt: sidecar `onnx.sha256` cạnh thư mục model (khớp sẵn cơ chế mã; không cần env). CẢNH BÁO: cây onnx PC0575 hiện hash 728c9eb7 → fingerprint 8274fbb0 (khác) → vé sau PHẢI mang đúng cây máy nhà `models/bge-m3-onnx-fp32` sang (verify 9f81075f), không đặt checksum bừa. Manifest pin b1d887e0 = gói PyTorch fp32 (không phải int8, không phải cây ONNX). | MỐC 1+2: [2026-09-29 17:27 +07] fingerprint đầy đủ `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` lấy từ index (mode=ro, 107.331 dense + 107.331 sparse; DB có runtime/runtime_version/model_id/revision nhưng KHÔNG lưu artifact_checksum/device); quét 648 tổ hợp 9 trường → đúng 1 bộ giá trị hiệu dụng tái tạo khớp.
Commit mới nhất: `1c74ea6`
Đường dẫn báo cáo P4: `docs/phieu-viec/ket-qua/p4-bao-cao.md`
Đường dẫn prompt P4: `docs/phieu-viec/mailbox-pc0575/prompt.md`
