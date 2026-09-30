# Vé B0-DICT — Từ điển thuật ngữ + số hóa bảng mã lỗi còn thiếu

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Bước 0 yêu cầu 1 database duy nhất + từ điển thuật ngữ; số hóa bảng mã lỗi, thông số
thiết kế, sơ đồ mạch điện / báo cáo lỗi hiện có. Vé buoc0-deploy đã số hóa 4 bảng mã lỗi
(3.820 mục) — còn phần chưa số hóa.

## Việc cần làm
1. Rà soát thư mục Drive Dieu-tra-loi: bảng mã / thông số nào chưa vào từ điển → số hóa
   bổ sung (lấy đúng mã thật, không bịa).
2. Chuẩn hóa tên gọi: cùng 1 hiện tượng viết nhiều kiểu → ánh xạ về 1 thuật ngữ chuẩn,
   giữ lại tên gốc để truy vết.
3. Từ điển phục vụ 3 nơi: gợi ý khi nhập form (B0-FORM), tra cứu Bước 1, phân loại Bước 5.
4. Code + test trên VM.

## Tiêu chí ĐẠT
- Đo được: % mã lỗi xuất hiện trong DB tra được trong từ điển (báo con số).
- Test: tra mã có → ra nghĩa + link nguồn; tra mã chưa có → báo "chưa có trong từ điển".
- OMP verify trên máy nhà với DB thật.
