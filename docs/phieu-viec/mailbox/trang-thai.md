# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: E3 — dọn XML thô ở extractor (code + test, không ghi index)
- Ticket trước: E2 — ĐẠT (commit `a83f8ff4`, Muse review 2026-09-26)
- Báo cáo E1: `docs/phieu-viec/ket-qua/FIX3_synthesis-E1-dieu-tra.md`
- Báo cáo E2: `docs/phieu-viec/ket-qua/FIX3_synthesis-E2-fix.md`
- Báo cáo E3: `docs/phieu-viec/ket-qua/FIX3_extractor-E3-xml.md`
- Ghi chú: OMP mốc 2026-09-27 00:10 +0700: đã xong phần E3 có thể làm — mã dọn XML sau cờ tắt mặc định, 27 kiểm thử trích xuất đạt, đo trên bản sao chỉ mục thử: `xmlns` 67→0, `<p:sld` 42→0, thẻ XML 79→0, B1/B3/B5 giữ hạng 1/100; toàn bộ `pytest -q` vẫn còn 23 lỗi môi trường (không báo PASS giả), không ghi chỉ mục, không đụng `main`. Chờ Muse duyệt từ git.
- Cập nhật lần cuối: 2026-09-27 00:10 +0700 (OMP)
