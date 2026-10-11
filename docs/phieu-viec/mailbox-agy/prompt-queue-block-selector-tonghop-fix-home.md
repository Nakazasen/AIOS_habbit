# Vé BLOCK-SELECTOR-TONGHOP-FIX-HOME (agy, máy nhà) — khối tong_hop không có trong bộ chọn khối của giao diện

**Nguồn gốc (đã kiểm chứng bằng ảnh chụp giao diện thật, vé DESKTOP-BLOCK-SMOKE-HOME 2026-10-11):** menu chọn khối tri thức ở khung soạn thảo chỉ có 4 lựa chọn — "Tự động (894 tài liệu)", "LSU (99 tài liệu)", "Điều tra lỗi (679 tài liệu)", "MOM (44 tài liệu)" — **thiếu hẳn khối `tong_hop` (72 tài liệu)** dù khối này có đầy đủ trong bản đồ miền (`domain_document_map.json`: lsu 99 / dieu_tra_loi 679 / mom 44 / tong_hop 72). Hệ quả: người dùng KHÔNG THỂ ghim câu hỏi vào 72 tài liệu của khối Tổng hợp; khối này chỉ tới được qua chế độ Tự động — và chế độ Tự động lại định tuyến sai (xem vé AUTO-ROUTE-NAMED-DOC-FIX-HOME). Đây là nguyên nhân gốc khiến phần tong_hop của vé nghiệm thu khói không đạt.

## Việc phải làm
1. Tìm nơi dựng danh sách lựa chọn của bộ chọn khối (đầu mối UI + nguồn dữ liệu miền nó đọc) và xác định vì sao `tong_hop` vắng mặt.
2. Sửa để bộ chọn liệt kê ĐỦ mọi khối có trong bản đồ miền, với số tài liệu đếm động như các khối hiện nay; giữ nguyên thứ tự/nhãn của các khối đang có.
3. **Test hồi quy bắt buộc:** một test khẳng định tập lựa chọn của bộ chọn == tập khối trong bản đồ miền, để một khối tương lai không thể lặng lẽ biến mất khỏi giao diện lần nữa.
4. Đủ 4 cổng chất lượng của repo (compileall, pytest liên quan, cli audit, import app). Nghiệm thu trên giao diện thật sẽ do làn desktop chạy ở vé BLOCK-SMOKE-R3 ngay sau vé này.
Báo cáo tại `docs/phieu-viec/ket-qua/block-selector-tonghop-fix-home.md`: điểm dựng danh sách, nguyên nhân thiếu, điểm sửa, test hồi quy. KHÔNG đụng chỉ mục production.

## BỔ SUNG PHẠM VI (điều phối, 2026-10-11 ~23:3x — từ bản nộp BLOCK-SMOKE-R3)
Thợ desktop đã chỉ rõ gốc rễ ở HAI lớp, vé này phải xử lý cả hai:
1. **Lớp giao diện:** danh sách `block_choices` trong `workspace_chat_app.py` không định nghĩa lựa chọn cho `tong_hop` (theo ghi nhận của thợ: một quyết định thiết kế cũ — Round 5 — từng chặn khối này; hướng hiện hành của dự án là phủ đủ 4/4 khối, quyết định cũ hết hiệu lực).
2. **Lớp adapter:** adapter RAG V2 có danh sách trắng chỉ gồm 3 khối (lsu, dieu_tra_loi, mom) — dù giao diện có nút mà adapter không nhận khối thì truy hồi vẫn không vào được tong_hop.
Test hồi quy phải phủ cả hai lớp: tập lựa chọn của bộ chọn == tập khối trong bản đồ miền, VÀ adapter chấp nhận truy vấn cho từng khối trong tập đó.
