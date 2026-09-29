# Ticket XẾP HÀNG: P5 — Deploy máy công ty với model ONNX đúng

## Bối cảnh
Model ONNX chuẩn (`9f81075f…`) đã upload lên Drive AIOS_Data từ máy nhà.

## Việc cần làm
1. Tải file zip model từ Drive về, giải nén vào `models\bge-m3-onnx-fp32`.
2. Verify checksum = `9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`
   bằng `resolve_onnx_checksum`. Lệch → dừng, đặt `cho-muse`.
3. Đặt env `AIOS_BGE_ONNX_MODEL_CHECKSUM=sha256:9f81075f…`.
4. Copy index production từ máy nhà (hoặc Drive) — KHÔNG embed lại.
5. Smoke test B1–B5 (B4 loại). Mở LAN cho cả phòng dùng.
6. Báo cáo: link LAN, kết quả B1–B5.

## Cấm
- Không embed lại trên PC0575 (CPU yếu).
- Không merge `main`. Không đụng ổ D máy nhà.
