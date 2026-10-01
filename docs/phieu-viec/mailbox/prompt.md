# Vé B3 — Gợi ý hướng điều tra (cây 4M + Why-Why)

LANE: [VM] — Muse thực hiện code+test trên VM. OMP KHÔNG làm vé này, chỉ verify trên máy nhà với dữ liệu thật khi Muse báo code xong + commit rõ ràng.

## Bối cảnh
Nhập hiện tượng → AI sinh cây điều tra theo 4M + Why-Why, kèm hạng mục cần xác nhận
và dữ liệu/hiện vật cần thu thập. Output khớp đúng format báo cáo điều tra hiện dùng
(xuất ra file để dán thẳng vào báo cáo). Mong muốn: người mới (G3 trở xuống) tự chạy
được bước điều tra đầu tiên.

## Việc cần làm
1. Trích format báo cáo điều tra thật từ dữ liệu Bước 0 (trường Nội dung điều tra /
   Nguyên nhân / Đối sách trong 15.707 ca thật) → làm template xuất file.
2. Sinh cây điều tra: đủ 4M (Man/Machine/Material/Method) + Why-Why sâu ≥3 tầng,
   hạng mục cần xác nhận cụ thể, danh sách dữ liệu/hiện vật cần thu thập.
3. Xuất file đúng template (md/docx) để dán thẳng vào báo cáo.
4. Code + test trên VM: 3 hiện tượng thật → cây đủ 4M, why-why ≥3 tầng, hạng mục cụ thể
   (không chung chung kiểu "kiểm tra lại máy").

## Tiêu chí ĐẠT
- OMP verify: 3 hiện tượng thật → cây điều tra + file xuất đúng format báo cáo công ty.
