# Dữ liệu thô ChatGPT enrichment — CHƯA AUDIT (user duyệt commit 2026-10-04 18:11 +07)

Nguồn: các mẻ hỏi–đáp do ChatGPT Plus (GPT-5.6 Sol) sinh từ tài liệu Drive MOM/LSU, thu thập bởi Muse trên VM (xem MANIFEST.md).

- `mom/`: 15 file batch, 608 cặp.
- `lsu/`: 30 file batch, 1.390 cặp (qua mẻ 45, Q2008).
- Tổng: 1.998 cặp.

## Rào cứng (user chốt)
- Đây là **bản thảo — chưa qua chuyên gia duyệt**.
- Mọi vé audit/import chỉ được ghi vào **staging**, TUYỆT ĐỐI KHÔNG nhập vào kho tri thức chính, không gắn nhãn "kiến thức đã được đào tạo bổ sung".
- Không merge `main`.

## Quy trình
1. Vé `AUDIT-ENRICH-MOM` / `AUDIT-ENRICH-LSU`: sửa lỗi đã biết, kiểm tra numbering/format, dedup, chấm M1–M5 bằng 6 module `src/aios_habit/golden_question_*.py`, sửa/loại cặp điểm thấp → ghi file đã sửa vào `docs/phieu-viec/chatgpt-enrichment-fixed/` (cùng cấu trúc mom/lsu).
2. Vé `IMPORT-STAGING-ENRICH`: chỉ dùng file đã audit trong `chatgpt-enrichment-fixed/`, dùng `golden_answer_importer.py` nhập vào DB staging, chạy metric, báo cáo.

Không ai được dùng thư mục raw này để import trực tiếp vào kho chính.
