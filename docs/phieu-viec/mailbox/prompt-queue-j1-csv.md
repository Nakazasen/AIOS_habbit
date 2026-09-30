# Vé J1-CSV — JIG: nhập cả file CSV + chọn biểu đồ, tự gửi mail

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Bước 1 JIG (phần tay) đã chạy thật: CSV→SQLite chống trùng, 9 biểu đồ, cảnh báo
ngưỡng/xu hướng, mail kèm biểu đồ, 21 vi phạm ngưỡng trên dữ liệu Iris thật (jig 1035).
Còn thiếu: nhập cả file CSV log jig một lần + cho phép chọn biểu đồ (áp dụng luôn);
tự chọn biểu đồ user đã setup → tự động gửi email đính kèm biểu đồ đó khi cảnh báo.

## Việc cần làm
1. Kiểm kê code hiện tại: phần nào đã có thì không làm lại (ghi rõ trong báo cáo).
2. Bổ sung phần thiếu: import cả file CSV một lần; UI chọn biểu đồ; cấu hình
   "biểu đồ nào gửi kèm mail khi cảnh báo".
3. Code + test trên VM với file log jig thật.

## Tiêu chí ĐẠT
- OMP verify: nhập 1 file CSV log jig thật → chọn biểu đồ → ra biểu đồ đúng;
  bắn cảnh báo test → mail đi kèm đúng biểu đồ đã setup.
