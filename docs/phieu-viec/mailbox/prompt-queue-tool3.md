# Ticket XẾP HÀNG: TOOL-3 — Nối benchmark vào chat

## Bối cảnh
Theo khung TOOL-2. Nối `mom_benchmark`, `rag_benchmark`, `rag_evaluator` vào chat.

## Việc cần làm
1. Đăng ký benchmark làm chat action theo khung TOOL-2.
2. User hỏi "đánh giá chất lượng trả lời" → chạy benchmark → hiện bảng điểm
   trong câu trả lời.
3. Test đầy đủ.

## Cấm
- Không ghi index production. Chỉ code + test.
- Không merge `main`. Không đụng ổ D.

## Báo cáo
`docs/phieu-viec/ket-qua/tool3-benchmark-chat.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.
