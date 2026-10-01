# Vé B0-MEASURE — Đo ≥90% đủ 5 trường bắt buộc (đóng Bước 0)

LANE: [NHÀ] — OMP thực hiện toàn bộ trên máy nhà.

## Bối cảnh
Điều kiện hoàn thành Bước 0 trong file đích: ≥90% bản ghi đủ 5 trường bắt buộc
(error code, hiện tượng, nguyên nhân, đối sách, công đoạn).

## Việc cần làm
1. Chạy đo trên DB thật: cả list điều tra lỗi (15.707 ca, vé buoc0-deploy) và list LSU
   (sau vé LSU-1). Đếm % bản ghi đủ 5 trường, chi tiết từng trường thiếu bao nhiêu %.
2. Nếu <90%: liệt kê trường thiếu nhiều nhất + nguồn nào bù được / nguồn nào chịu
   (đề xuất backfill cụ thể, không chung chung).
3. Ghi kết quả vào báo cáo `docs/phieu-viec/ket-qua/b0-measure.md`, commit riêng.

## Tiêu chí ĐẠT
- Có con số % đo được trên dữ liệu thật. ≥90% → Bước 0 đóng; <90% → có danh sách
  backfill cụ thể để ra vé tiếp theo (Muse quyết).
