# Ticket XẾP HÀNG: E4 — Chuyển default backend sang ONNX fp32

## Bối cảnh
Chuỗi E hoàn thiện trả lời. E4 chuyển backend mặc định sang ONNX fp32.

## Việc cần làm
1. Đổi default backend trong config/code sang `onnx_fp32` (hoặc tên tương đương
   trong `aios_habit.rag_v2.bge_onnx_backend`).
2. GIỮ nguyên biến môi trường `BGE_BACKEND` làm override — nếu user đặt thì dùng
   theo user, không ép.
3. Fail-closed: nếu thiếu model ONNX thì báo lỗi rõ ràng, KHÔNG fallback lén
   sang backend khác.
4. Viết test:
   - Test default là ONNX fp32 khi không đặt `BGE_BACKEND`.
   - Test override `BGE_BACKEND` có hiệu lực.
   - Test fail-closed khi thiếu model (không crash mù, message rõ).
   - Test "tắt GPU đi vẫn chạy" (CPU-only, theo ràng buộc 2026-09-27).
5. Chạy full test liên quan, tất cả pass.

## Cấm
- Không ghi index, không embed. Chỉ code + test.
- Không merge `main`. Không đụng ổ D.
- Không hardcode GPU.

## Báo cáo
`docs/phieu-viec/ket-qua/e4-default-onnx-fp32.md`: mô tả đổi + số test pass/fail.
Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
