# Ticket XẾP HÀNG: OMP-MODEL-REPORT — Báo cáo model OMP đang chạy

> Role OMP gợi ý: SMOL/TINY (việc đọc cấu hình ~2 phút). Không code.

## Việc cần làm
Chủ sở hữu muốn biết chính xác thợ OMP máy nhà đang chạy model nào.
Trả lời trực tiếp bằng cách kiểm tra cấu hình của chính bạn:

1. Mở file cấu hình roles/model mà OMP đọc khi khởi động (hoặc lệnh status
   nếu có, hoặc log khởi động gần nhất) — đọc bằng thực tế, không đoán.
2. Báo cáo rõ: **provider** (vd xai-oauth), **model** (vd grok-4.7),
   **mức/tham số** (vd medium), và mapping roles hiện tại
   (DEFAULT / SMOL / TINY / PLAN / review-audit đang trỏ model nào).
3. Nếu có nhiều model cho nhiều role, liệt kê đủ.

## Báo cáo
- Ghi vào `docs/phieu-viec/ket-qua/omp-model-report.md`.
- Cập nhật dòng `bao_cao` trong `trang-thai.md` với đúng 1 dòng:
  `Model OMP máy nhà: <provider>/<model>:<mức> (DEFAULT=..., SMOL=...)`.
- Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
