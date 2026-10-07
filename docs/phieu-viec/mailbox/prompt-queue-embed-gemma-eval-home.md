# VÉ XẾP HÀNG: EMBED-GEMMA-EVAL-HOME (đánh giá EmbeddingGemma 2 làm embedder thay BGE-M3 — chỉ thí nghiệm bóng)

- Mã vé: `EMBED-GEMMA-EVAL-HOME`
- Role gợi ý: DEFAULT (benchmark/nhúng — máy nhà có GPU)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/embed-gemma-eval-home.md`
- Vị trí hàng chờ: #3 mailbox OMP nhà (sau ROUTER-POOL-COMMANDCODE-HOME, SRC-PACKAGE-511-HOME).

## Bối cảnh

User giới thiệu EmbeddingGemma 2 (Google, Apache 2.0, ~270M tham số cho text/code, vector 768 chiều cắt được 512/256/128, chạy local nhẹ ~0.5GB RAM cho phần text). Hiện hệ thống dùng BGE-M3: nặng, khởi động worker từng timeout trên máy nhà, encode trên CPU máy công ty rất chậm. Câu hỏi cần trả lời BẰNG SỐ CỦA CHÍNH HỆ THỐNG: đổi sang EmbeddingGemma 2 (chỉ phần text) thì chất lượng tìm kiếm trên kho thật + tốc độ ra sao so với BGE-M3?

## Việc phải làm (thí nghiệm bóng — TUYỆT ĐỐI không đụng chỉ mục production)

1. Kéo model EmbeddingGemma 2 bản text từ Hugging Face (ghi rõ model id + revision), kiểm tra license Apache 2.0 trên model card.
2. Nhúng lại toàn bộ 149.800 mảnh của kho tri_thuc vào một chỉ mục BÓNG riêng (thư mục local_runs, không ghi đè index thật) trên máy nhà (GPU). Ghi thời gian nhúng toàn phần + kích thước chỉ mục (768d; nếu thuận tay, thêm biến thể 256d Matryoshka để so kích thước/tốc độ).
3. Chạy cùng bộ đề 50 câu LSU + 7 câu nhóm A thực thể qua chỉ mục bóng: chấm GPA bằng rubric hiện hành + đối chiếu retrieval (tài liệu đích có vào top không) — so trực tiếp với các mốc BGE-M3 đã có (GPA 1,28 bản vá claim-budget ở nhà; 7/7 nhóm A rank 1–2 ở máy công ty).
4. Đo tốc độ trên cả hai máy nếu có thể: thời gian nạp model + encode 1 câu truy vấn (máy nhà GPU; ước lượng CPU từ số liệu công bố phải ghi rõ là ước lượng, không giả làm số đo).
5. Kết luận theo số: đạt/ngang/kém BGE-M3 ở chất lượng; nhanh hơn bao nhiêu ở các khâu đã đo; khuyến nghị có/không đáng đổi + chi phí đổi (nhúng lại, kiểm chứng lại) — điều phối quyết theo báo cáo.

## Rào cứng

- Chỉ mục bóng tách biệt hoàn toàn; không ghi/đổi/xoá chỉ mục production; không đổi cấu hình app.
- Chất lượng chấm trên đúng bộ đề + rubric của hệ thống, không dùng điểm benchmark bên ngoài thay thế.
- Không merge `main`.
