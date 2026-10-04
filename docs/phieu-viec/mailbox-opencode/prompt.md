# Ticket: IMPORT-STAGING-ENRICH — Nhập cặp đã audit vào staging (chuyển từ hàng chờ OMP sang opencode 22:55)

> Điều kiện đã đủ: AUDIT-ENRICH-MOM ĐẠT (608 cặp) và AUDIT-ENRICH-LSU ĐẠT (1.790 cặp) — cả hai đều do opencode audit.
> Nguồn: `docs/phieu-viec/chatgpt-enrichment-fixed/mom/` + `lsu/` (CHỈ file đã audit, không dùng thư mục raw).

## Rào cứng (đọc kỹ trước khi làm)
- Chỉ nhập vào **DB staging**. TUYỆT ĐỐI KHÔNG nhập vào kho tri thức chính / DB production.
- Mỗi cặp nhập kèm nhãn `MOM` hoặc `LSU` + `Bản thảo — chưa qua chuyên gia duyệt`.
- Không gắn nhãn "kiến thức đã được đào tạo bổ sung".
- Không merge `main`.

## Việc cần làm
1. Dùng `src/aios_habit/golden_answer_importer.py` (chỉ ghi staging — module đã có rào này, xác nhận lại trước khi chạy) để nhập toàn bộ cặp đã audit vào DB staging.
2. Chạy dedup lần cuối trên staging (phòng cặp trùng lọt qua audit).
3. Chạy bộ metric M1–M5 (`golden_question_quality.py`) trên staging, báo số cặp/cụm và phân bố điểm.
4. Smoke test: truy vấn thử 5–10 câu trên staging, xác nhận cặp bản thảo trả về đúng nhãn (không lẫn vào luồng trả lời chính của app).

## Báo cáo
`docs/phieu-viec/ket-qua/import-staging-enrich.md`: số cặp đã nhập (MOM/LSU), metric M1–M5, kết quả smoke test, xác nhận DB production không đổi (ghi SHA hoặc mốc kiểm tra đã dùng). Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
