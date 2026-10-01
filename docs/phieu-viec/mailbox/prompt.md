# Vé B4 — Phân tích xu hướng & cảnh báo sớm

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Phân tích khuynh hướng theo model / line / công đoạn / loại giấy / máy cấp thấp /
dữ liệu jig. Đầu ra: biểu đồ xu hướng + cảnh báo tự động (ngưỡng định sẵn) + báo cáo
định kỳ tự động. Tái dùng engine biểu đồ/cảnh báo của tool JIG (9 biểu đồ, cảnh báo
ngưỡng/xu hướng, mail kèm biểu đồ — đã chạy thật trên dữ liệu Iris).
Phụ thuộc: vé date-map (cột ngày thật X/Y).

## Việc cần làm
1. Trend engine trên DB ca lỗi: tỉ lệ phát sinh theo model/line/công đoạn/loại giấy/
   máy cấp thấp theo ngày phát sinh (dùng cột ngày thật từ date-map).
2. Cảnh báo ngưỡng: vượt ngưỡng tỉ lệ phát sinh → cảnh báo (ngưỡng do user thiết lập,
   cơ chế như JIG).
3. Báo cáo định kỳ tự động (mail + biểu đồ đính kèm, như JIG đã làm).
4. Code + test trên VM: tỉ lệ tính tay khớp số máy tính trên mẫu kiểm tra.

## Tiêu chí ĐẠT
- OMP verify trên DB thật: biểu đồ xu hướng chạy được, cảnh báo bắn đúng khi vượt
  ngưỡng test, báo cáo định kỳ sinh được file.
