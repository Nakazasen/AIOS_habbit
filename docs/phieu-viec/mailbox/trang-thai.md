# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: E4 — chuyển default backend sang ONNX fp32 trên branch (giữ BGE_BACKEND override, fail-closed khi thiếu model)
- Ticket trước: E3 — ĐẠT (commit `6660e7e`, Muse review 2026-09-27: extractor dọn XML sau flag `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` mặc định tắt, 27 test extractor đạt, canary chỉ đọc `xmlns` 67→0 / `<p:sld` 42→0 / thẻ XML 79→0, B1/B3/B5 giữ hạng 1/100, không ghi index, full suite 3.134 passed + 23 lỗi môi trường cũ không PASS giả)
- Báo cáo E1: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`
- Báo cáo E2: `docs/phieu-viec/ket-qua/FIX3_synthesis-E2-fix.md`
- Báo cáo E3: `docs/phieu-viec/ket-qua/FIX3_extractor-E3-xml.md`
- Ghi chú: OMP 2026-09-27 02:34 +0700 — khởi tạo ONNX fp32 mặc định trên 74 nguồn mất 2,406s; B1 0,675s và B5 0,677s, đều không abstain; bằng chứng có dữ kiện đích nhưng câu trả lời không nêu đủ mã. Index `integrity_check=ok`, kích thước giữ 29.851.648 byte. Full suite: 3.145 đạt, 2 bỏ qua, 23 lỗi môi trường/tiến trình con; đang hoàn thiện báo cáo và cổng còn lại.
- Cập nhật lần cuối: 2026-09-27 02:34 +0700 (OMP h410asrock)
