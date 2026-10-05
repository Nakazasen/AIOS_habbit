# Báo cáo audit mẻ 88 — Điều-tra-lỗi Q3392–Q3406 (vé AUDIT-BATCH88-PC0575)

- Ngày làm: 2026-10-05 (máy KDTVN-PC0575, thợ opencode).
- Nguồn đọc: `docs/phieu-viec/chatgpt-enrichment-raw/dieuchinh/batch-88.md` (15 cặp, mẻ vét cuối: vi 5 / zh 5 / ja 5).
- Đích đã ghi: `docs/phieu-viec/chatgpt-enrichment-fixed/dieuchinh/batch-88.md` (giữ nguyên mẫu các file fixed batch 55–87: đầu file tóm tắt nguồn, sau đó các cặp xếp theo số thứ tự, mỗi cặp đúng 6 dòng).
- Nguyên tắc giữ: chỉ ghi trong thư mục fixed, không đụng thư mục raw; mọi cặp giữ nhãn khối Điều-tra-lỗi và dòng bản thảo chưa qua chuyên gia duyệt; giá trị raw (mã 79248313, U155, điện áp JIG, tỷ lệ thập phân dài Q3405) giữ nguyên, không tự gán nghĩa OK/NG; chỉ dùng OK/NG khi chính nguồn file định nghĩa; không nhập vào kho tri thức chính; không gộp vào nhánh main.

## Kết quả tổng

- Số cặp trước kiểm tra: 15 (Q3392–Q3406).
- Số cặp sau kiểm tra: 15 (giữ đủ, không loại cặp nào).
- Số cặp đã sửa nội dung: 0 (kiểm bằng script so từng dòng 6 trường raw với fixed: VERBATIM 15/15; fixed chỉ xếp lại theo số thứ tự và thay đầu file theo mẫu, vì raw xếp theo file 2/5→5/5→1/5→3/5→4/5).
- Số cặp loại bỏ: 0.
- Kiểm tra 6 trường: 15/15 đủ (Khối, Ngôn ngữ, Bối cảnh, Cách hỏi, Hỏi, Đáp kèm nguồn file). Ngôn ngữ: Việt 5 (Q3392, Q3395, Q3398, Q3401, Q3404), Trung 5 (Q3393, Q3396, Q3399, Q3402, Q3405), Nhật 5 (Q3394, Q3397, Q3400, Q3403, Q3406). Cách hỏi: trực tiếp 3 (Q3392, Q3397, Q3401), tình huống 4 (Q3393, Q3398, Q3403, Q3404), so sánh 2 (Q3399, Q3405), xử lý sự cố 3 (Q3395, Q3400, Q3406), hỏi ngược kiểm tra hiểu 3 (Q3394, Q3396, Q3402) — khớp đúng đầu file raw.

## Lỗi tìm thấy

- Không phát hiện lỗi bịa đáp: mọi đáp đều bám chi tiết nguồn (mã U, số đo, tên sheet, số trang chương 7-3). Bộ ba Maintenance Mode (Q3395–Q3397) nhất quán nội bộ (U201 hiệu chỉnh X/Y, U207 kiểm tra phím, U000 xuất báo cáo, U001 thoát).
- OK/NG trong đáp đều là trạng thái do nguồn ghi (thay YF2 rồi máy thực nghiệm OK, Main mới OK / Main cũ NG, I/F sau thay U1 OK, tháo lắp DUMMY 20 lần OK) — không tự gán OK/NG ngoài nguồn.
- Raw value được giữ đúng: Q3405 giữ nguyên tỷ lệ thập phân dài, Q3398 giữ nguyên U155 Non/EMTY/FULL từng máy, Q3400 giữ nguyên 3 lần đo V1–V4, Q3395 giữ nguyên mã 79248313.
- Câu từ chối suy diễn đúng chuẩn: Q3404 ghi rõ nguyên nhân đứt YF2 chưa xác định, Q3399 ghi rõ VN None/Empty có chồng lấn và năng lực nhận biết vốn thấp — không nâng thành kết luận chắc chắn.
- Văn phong đúng ngôn ngữ từng cặp (Việt/Trung/Nhật), đáp Trung/Nhật xen thuật ngữ gốc (U-code, tên linh kiện) đúng kiểu các mẻ trước.

## Trùng lặp nội dung

- Trùng nguyên văn cả Hỏi + Đáp với 979 cặp fixed batch 55–87: 0 cặp (quét bằng script trên toàn bộ fixed, trừ chính batch-88).
- Trùng nguyên văn chỉ câu Hỏi với fixed cũ: 0 cặp.
- Lưu ý trung thực: Q3394 (ja, từ bảng C-call) và Q3402 (zh, từ service manual chương 7-3) cùng chủ đề điều kiện判定 C0150, nhưng nguồn độc lập, ngôn ngữ và cách diễn đạt khác nhau. Giữ cả hai theo đúng tiền lệ báo cáo tổng (8 nhóm mẫu câu tái dùng vẫn giữ vì Đáp và nguồn khác nhau).
- Nhật ký cặp loại bỏ: không có.

## Đối chiếu chuẩn format

- Fixed batch-88 theo đúng mẫu batch 55–87: đầu file có Ngày/Nguồn/Model/Ngôn ngữ/Cách hỏi/Quy tắc Raw value/Điểm phân biệt case/Nhãn bản thảo; 15 cặp xếp Q3392→Q3406; mỗi cặp đúng 6 dòng; mỗi Đáp có dòng nguồn file; đã bỏ các mục `File x/5` và `Báo cáo kiểm tra file` khỏi thân fixed (thông tin nguồn đã gom lên đầu file).
- Thư mục raw không có thay đổi nào (chỉ thêm mới 1 file fixed + 1 báo cáo này).

## Kiểm tra cổng kỹ thuật

- Thay đổi trong vòng này chỉ là tài liệu (1 file fixed + 1 báo cáo + `trang-thai.md`), không sửa mã nguồn (`git status` không có file `src/` nào).
- Kết quả chạy thật: `compileall src tests` xong không lỗi; `python -m aios_habit.cli audit` → `"status": "PASS"`; `import aios_habit.workspace_chat_app` thành công.
- `pytest -q` toàn bộ (4112 tests) chạy quá 10 phút chưa xong nên dừng (bộ test nặng, không liên quan vì vé không đụng code); chạy mẫu `tests/test_workspace_paths.py` → 4 passed. Không báo PASS giả cho toàn bộ pytest.
- Không nhập kho chính, không gộp nhánh main, không force-push, không đụng file raw hay file của thợ khác.
