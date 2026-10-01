# Vé hodap-home — Hỏi đáp 6 câu L1–E3 trên máy nhà

LANE: [NHÀ] — OMP thực hiện toàn bộ trên máy nhà h410asrock. Chạy SAU khi J1-RT xong (không chen ngang verify đang chạy).

## Bối cảnh
User muốn hỏi đáp RAG trên máy nhà như máy công ty. Vé `hodap-lsu-loi-rerun` đã chạy 6 câu (L1–L3/E1–E3) trên PC0575; chạy lại đúng 6 câu đó trên index máy nhà.

## Việc cần làm
1. Ghi nhận định danh index máy nhà: đường dẫn file, SHA-256/dung lượng, số chunk/document, các delta đã merge.
2. Lấy đúng 6 câu hỏi L1–L3/E1–E3 từ vé `hodap-lsu-loi-rerun` (`docs/phieu-viec/mailbox-pc0575/prompt-queue-hodap-lsu-loi-rerun.md`).
3. Chạy từng câu, ghi: thời gian/câu, câu trả lời, top-15, citation/trace (valid/insufficient_evidence).
4. Báo cáo `docs/phieu-viec/ket-qua/hodap-home.md`.

## Ràng buộc
- Index máy nhà KHÁC production PC0575 → kết quả chỉ để tham khảo và phục vụ hỏi đáp tại nhà, KHÔNG so trực tiếp với số đo PC0575.
- Vé này chỉ đọc + hỏi đáp, không ghi index.
- Không đụng `main`, ổ D.

## Tiêu chí ĐẠT
- 6/6 câu có trả lời; báo cáo đầy đủ thời gian + trace/citation từng câu; định danh index rõ ràng.
