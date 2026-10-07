# VÉ: BGE-WORKER-DIAG-HOME (chẩn đoán worker BGE không khởi động được trên app máy nhà)

- Mã vé: `BGE-WORKER-DIAG-HOME`
- Role gợi ý: DEFAULT (chẩn đoán chỉ-đọc + tái hiện, KHÔNG sửa code ở vé này)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/bge-worker-diag-home.md`

## Bối cảnh

Vé `BASELINE-USE-HOME` (ĐẠT 07/10) đo dùng thật trên máy nhà và phát hiện **chặn go-live**: câu hỏi tra cứu mã lỗi chạy đường tra từ điển thì trả lời đúng trong 5,39 giây, nhưng mọi câu hỏi ngữ nghĩa (đường RAG) đều chết ở khâu khởi động tiến trình con BGE: `RuntimeError: preparation_init_bge_worker_persist_timeout` (`workspace_chat_rag_v2_adapter.py` → `bge_subprocess_client.py`). Máy nhà có GPU GTX 1060 3GB — về lý thuyết khâu nhúng phải nhanh hơn máy công ty, nên timeout khi khởi động là bất thường cần chẩn đoán tận gốc trước khi sửa.

## Việc phải làm

0. **Bổ sung bằng chứng còn thiếu của vé trước:** commit 8 ảnh chụp đã nêu trong ghi_chu của `BASELINE-USE-HOME` vào `docs/phieu-viec/ket-qua/` (hoặc ghi rõ trong báo cáo vé này nếu ảnh đã mất/không tồn tại).
1. **Tái hiện trong điều kiện sạch:** khi máy không còn tiến trình nặng của thợ khác, mở app, hỏi lại câu C7620 (ngữ nghĩa). Ghi: lỗi còn xảy ra không, log worker đầy đủ, thời gian chờ tới khi lỗi.
2. **Đo thời gian khởi động worker thật:** worker nạp backend nào trên máy nhà (torch/CUDA hay ONNX), nạp model từ đường dẫn nào, khởi động thực tế mất bao lâu nếu chờ đủ lâu (đo bằng tiến trình độc lập, không qua app) — so với ngưỡng timeout trong code (ghi rõ giá trị + vị trí dòng).
3. **Loại trừ/ xác nhận các giả thuyết:** (a) tranh chấp tài nguyên lúc đo baseline (máy vừa chạy các việc nặng khác); (b) backend mặc định ở máy nhà chưa đúng (vé E4 đặt mặc định ONNX — kiểm tra thực tế app đang dùng gì); (c) VRAM 3GB không đủ cho đường torch nên worker chết/chậm; (d) worker chết một lần là độc cả phiên (câu sau có tự hồi không — hỏi liên tiếp 2 câu ngữ nghĩa và ghi kết quả).
4. Kết luận chẩn đoán + đề xuất hướng sửa (chưa sửa code ở vé này — điều phối ra vé sửa riêng theo kết luận).

## Rào cứng

- Chẩn đoán chỉ-đọc: không sửa code, không đổi cấu hình app, không ghi index. Đo độc lập được phép chạy tiến trình worker thử trên model thật nhưng không ghi đè gì.
- Mọi khẳng định phải có log/số đo kèm theo. Không merge `main`.
