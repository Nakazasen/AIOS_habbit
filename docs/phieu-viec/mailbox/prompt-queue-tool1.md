# Ticket XẾP HÀNG: TOOL-1 — Kiểm kê tool chưa nối vào chat

## Bối cảnh
Tầm nhìn: 1 ô nhập + 1 vùng trả lời, mọi tính năng chui vào câu trả lời.
Nhiều module còn đứng riêng lẻ.

## Việc cần làm
1. Quét toàn bộ `src/aios_habit/`: liệt kê mọi module tính năng.
2. Với mỗi module: đã nối vào chat (`workspace_chat_ui.py` / `workspace_chat_app.py`)
   hay chưa. Kiểm tra bằng import/reference thực tế, không đoán.
3. Phân nhóm: RAG, benchmark, interview, prediction, visual, extract, memory, khác.
4. Báo cáo bảng: module | nhóm | đã nối (có/không) | ghi chú.

## Cấm
- Chỉ đọc và báo cáo. Không sửa code.
- Không đụng ổ D.

## Báo cáo
`docs/phieu-viec/ket-qua/tool1-kiem-ke.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.
