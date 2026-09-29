# Ticket XẾP HÀNG: TOOL-2 — Khung action trong chat

## Bối cảnh
Theo kết quả TOOL-1. Cần khung chung để mọi tool chui vào câu trả lời chat
thay vì phơi nút riêng.

## Việc cần làm
1. Thiết kế `chat_action` framework: tool đăng ký action → chat gọi theo ngữ cảnh
   câu hỏi → render kết quả giàu (bảng, biểu đồ) trong vùng trả lời.
2. Viết code khung + 1 tool mẫu tích hợp thử (chọn tool đơn giản nhất từ TOOL-1).
3. Test: hỏi thử → action kích hoạt đúng → kết quả render đúng.
4. Không mỗi tính năng thêm một nút — đúng luật UI đã chốt.

## Cấm
- Không ghi index. Chỉ code + test.
- Không merge `main`. Không đụng ổ D.

## Báo cáo
`docs/phieu-viec/ket-qua/tool2-khung-action.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.
