# Vé J1-RT — JIG realtime: spec API + prototype + yêu cầu hạ tầng

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng. (phần hạ tầng thật cần phía công ty — xem mục 3)

## Bối cảnh
Mục tiêu cuối của tool JIG: AI phân tích dữ liệu realtime từ server và cảnh báo khi có
xu hướng dẫn đến phát sinh NG. Cần: cổng API (đầu nhận/chuyển thông tin) để jig đẩy
dữ liệu lên server realtime; server đẩy về AI realtime. Hạ tầng cần chuẩn bị:
(1) log jig đẩy dòng/cột dữ liệu lên server; (2) server đẩy ngược dữ liệu về AI.

## Việc cần làm
1. Thiết kế spec API: endpoint nhận dòng log jig (format bản tin, tần suất, auth),
   endpoint server→AI (push/pull, format, retry).
2. Prototype AI nhận realtime: mô phỏng bằng dữ liệu jig thật phát lại theo đúng dòng
   thời gian, gắn mác SIMULATED_REALTIME (không bịa dữ liệu).
3. Liệt kê yêu cầu hạ tầng phía công ty (server, mạng, agent thu log trên jig) thành
   danh sách cụ thể để user quyết.
4. Code + test prototype trên VM.

## Tiêu chí ĐẠT
- Spec API hoàn chỉnh + prototype chạy được với dữ liệu phát lại + danh sách yêu cầu
  hạ tầng rõ ràng. Triển khai hạ tầng thật là việc khác, không thuộc vé này.
