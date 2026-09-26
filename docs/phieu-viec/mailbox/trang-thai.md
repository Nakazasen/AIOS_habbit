# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: E4 — chuyển default backend sang ONNX fp32 trên branch (giữ BGE_BACKEND override, fail-closed khi thiếu model)
- Ticket trước: E3 — ĐẠT (commit `6660e7e`, Muse review 2026-09-27: extractor dọn XML sau flag `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` mặc định tắt, 27 test extractor đạt, canary chỉ đọc `xmlns` 67→0 / `<p:sld` 42→0 / thẻ XML 79→0, B1/B3/B5 giữ hạng 1/100, không ghi index, full suite 3.134 passed + 23 lỗi môi trường cũ không PASS giả)
- Báo cáo E1: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`
- Báo cáo E2: `docs/phieu-viec/ket-qua/FIX3_synthesis-E2-fix.md`
- Báo cáo E3: `docs/phieu-viec/ket-qua/FIX3_extractor-E3-xml.md`
- Ghi chú: OMP 2026-09-27 01:05 +0700 — đã đổi default sang ONNX fp32 (không BGE_BACKEND → onnx_int8), giữ override pytorch/onnx/onnx_int8/auto, fail-closed khi thiếu model/checksum; 16 test backend+migrate đạt, chuẩn bị đo index thật chỉ đọc.
- Cập nhật lần cuối: 2026-09-27 01:05 +0700 (OMP h410asrock)
