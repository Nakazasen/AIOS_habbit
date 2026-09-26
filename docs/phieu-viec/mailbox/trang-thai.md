# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: E4 — chuyển bộ xử lý mặc định sang ONNX fp32; giữ lựa chọn `BGE_BACKEND`, dừng an toàn khi thiếu/sai mô hình.
- Mã nguồn E4: `3aa4280fe1e968da635e86ba7b28dff760c6dc40`
- Mã báo cáo và bàn giao: `575bdec2a0e8b4936eefaec391231870ac6fdebb`
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ticket trước: E3 — ĐẠT (commit `6660e7e`, Muse review 2026-09-27: extractor dọn XML sau flag `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` mặc định tắt, 27 test extractor đạt, canary chỉ đọc `xmlns` 67→0 / `<p:sld` 42→0 / thẻ XML 79→0, B1/B3/B5 giữ hạng 1/100, không ghi index, full suite 3.134 passed + 23 lỗi môi trường cũ không PASS giả)
- Báo cáo E1: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`
- Báo cáo E2: `docs/phieu-viec/ket-qua/FIX3_synthesis-E2-fix.md`
- Báo cáo E3: `docs/phieu-viec/ket-qua/FIX3_extractor-E3-xml.md`
- Ghi chú: OMP 2026-09-27 02:54 +0700 — kiểm thử liên quan 63 đạt; toàn bộ `pytest -q`: 3.146 đạt, 2 bỏ qua, 23 lỗi (chi tiết trong báo cáo). Chỉ mục chỉ đọc, chờ xử lý 0, kích thước không đổi; đã đẩy nhánh, không gộp `main`, dừng chờ Muse duyệt.
- Cập nhật lần cuối: 2026-09-27 02:54 +0700 (OMP h410asrock)
