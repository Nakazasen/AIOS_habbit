# Vé B5 — Phân loại tự động + cảnh báo tái phát

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Khi nhập lỗi mới, AI tự gán: công đoạn / phân loại nguyên nhân
(lắp ráp – thiết kế – linh kiện – khác) / bộ phận phụ trách, rồi đối chiếu lịch sử để
cảnh báo "lỗi này đã phát sinh N lần, đã có đối sách X".
Điều kiện hoàn thành: độ chính xác phân loại ≥80% trên tập kiểm tra;
100% lỗi mới được đối chiếu với lịch sử.
Phụ thuộc: vé f3b-backfill (chất lượng trường fix/đối sách).

## Việc cần làm
1. Bộ phân loại trên dữ liệu thật có nhãn (15.707 ca): rule-based trước, đo accuracy
   trên tập kiểm tra giữ lại (không dùng tập train để chấm).
2. Đối chiếu tái phát: lỗi mới → tìm lịch sử cùng (error code/hiện tượng) → đếm N lần
   + đối sách đã áp dụng.
3. Tích hợp vào form B0-FORM: nhập xong hiện tượng → hiện cảnh báo tái phát ngay nếu có.
4. Code + test trên VM.

## Tiêu chí ĐẠT
- Số đo accuracy thật ≥80% trên tập kiểm tra; demo nhập 3 lỗi mới → cảnh báo tái phát
  đúng N lần + đối sách X. OMP verify trên máy nhà.
