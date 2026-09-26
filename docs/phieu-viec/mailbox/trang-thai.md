# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: E3 — dọn XML thô ở extractor (code + test, không ghi index)
- Ticket trước: E2 — ĐẠT (commit `a83f8ff4`, Muse review 2026-09-26)
- Báo cáo E1: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`
- Báo cáo E2: `docs/phieu-viec/ket-qua/FIX3_synthesis-E2-fix.md`
- Báo cáo E3: `docs/phieu-viec/ket-qua/FIX3_extractor-E3-xml.md`
- Commit: `6660e7e` (mã E3 `6079808` + `40b2a04` đã có trên nhánh, kiểm tra lại và tài liệu ở `2ffd531` + `6660e7e`)
- Ghi chú: OMP mốc 2026-09-27 00:12 +0700: xong E3 chờ duyệt — cờ dọn XML mặc định tắt, 27 kiểm thử đạt, bản sao chỉ mục thử `xmlns` 67→0, `<p:sld` 42→0, thẻ XML 79→0, B1/B3/B5 giữ hạng 1/100; toàn bộ `pytest -q` còn 23 lỗi môi trường (không báo PASS giả), không ghi chỉ mục, không đụng `main`.
- Cập nhật lần cuối: 2026-09-27 00:12 +0700 (OMP)
