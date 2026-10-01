# Vé J2 — JIG: xác nhận chức năng trước khi đưa người dùng thử

LANE: [NHÀ] — OMP thực hiện toàn bộ trên máy nhà. (+ Muse hỗ trợ review)

## Bối cảnh
Pha kiểm tra lại toàn bộ chức năng đã triển khai ở Bước 1 JIG trước khi đưa cho người
dùng thử. Cần: J1-CSV và J1-RT (prototype) xong.

## Việc cần làm
1. Lập checklist từ spec các vé J1: import CSV, 9 biểu đồ, cảnh báo ngưỡng/xu hướng,
   mail kèm biểu đồ, API realtime prototype.
2. Chạy lại từng mục trên dữ liệu thật, ghi PASS/FAIL từng mục.
3. Lỗi phát hiện → liệt kê cụ thể để ra vé sửa (không tự sửa ngoài vé).

## Tiêu chí ĐẠT
- Biên bản checklist đầy đủ PASS/FAIL trên dữ liệu thật, commit báo cáo
  `docs/phieu-viec/ket-qua/j2.md`.
