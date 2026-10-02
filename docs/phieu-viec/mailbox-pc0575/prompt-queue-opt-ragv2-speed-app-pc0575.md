# Vé: OPT-RAGV2-SPEED-APP-PC0575 — đo tốc độ hỏi đáp app thật + hồ sơ nút thắt còn lại

Lane: [CTY] OMP đo và báo cáo trên KDTVN-PC0575 (CPU-only, index production chỉ đọc). Muse dùng báo cáo này để code tối ưu trên VM; OMP không tự sửa code trong vé này.
Không merge `main`; không force-push; không ghi index production; không chạy `--apply`; không tạo bảng/index mới trong production.

## Lý do phát hành

User chốt 2026-10-02 12:07 +07: **tốc độ phản hồi câu hỏi là ưu tiên số 1**. Mở LAN/tường lửa không làm câu trả lời nhanh hơn, nên hoãn sau vé này.

Vé `OPT-RAGV2-LEXICAL` đã ĐẠT parity nhưng mốc stretch <60s/câu chưa đạt. Số đo probe gần nhất trên PC0575: E2 55,4s; L1 61,7s; các câu còn lại khoảng 129–146s. Nút thắt đã tách được: quét eligibility trên 120.452 dòng + `chunks_fts MATCH` bm25 khoảng 19–52s/câu. Dense/sparse không còn nạp lại giữa câu.

## Việc cần làm

1. Chạy trên chính PC0575 ở chế độ local, không cần LAN và không chờ admin mở tường lửa.
2. Đo tốc độ hỏi đáp bằng đúng đường app đang chạy sau deploy Bước 0–5. Ghi rõ cách đo là qua giao diện app thật hay probe cùng pipeline; không gọi probe là app thật nếu không đi qua giao diện.
3. Bộ câu: 6 câu L1–L3/E1–E3 đã dùng ở các vé PYLOOPS/LEXICAL. Đo câu lạnh sau restart và câu ấm lặp lại. Ghi từng câu: tổng thời gian, phần tìm kiếm, phần viết trả lời nếu tách được, và trạng thái cache.
4. So hai chế độ nếu app cho phép đổi an toàn bằng biến môi trường khi restart: `AIOS_RAGV2_LEXICAL_V2=0` và `AIOS_RAGV2_LEXICAL_V2=1`. Nếu không đổi được qua app thật, ghi rõ và dùng probe cùng cấu hình để đối chứng.
5. Kiểm parity top-15 so với baseline `opt_ragv2_verify_new.json`: phải khớp 100%, riêng E1 phải đủ 15/15 đúng thứ tự. Nếu lệch, dừng và báo rõ câu lệch.
6. Nếu còn câu trên 60s, lập hồ sơ nút thắt bằng số đo: thời gian eligibility, `chunks_fts MATCH`, phần khác; kèm `EXPLAIN QUERY PLAN` hoặc bằng chứng tương đương cho truy vấn chậm nhất. Không tự sửa code, không tự tạo index mới.
7. Đo SHA-256 và mtime của index production trước/sau; phải không đổi. Kiểm `/_stcore/health` = `ok` trước/sau.

## Đầu ra

- Báo cáo `docs/phieu-viec/ket-qua/opt-ragv2-speed-app-pc0575.md` gồm bảng 6 câu lạnh/ấm, so sánh v2off/v2on nếu đo được, parity, nút thắt lớn nhất kèm bằng chứng, và đề xuất hướng tối ưu cho Muse code.
- Cập nhật `docs/phieu-viec/mailbox-pc0575/trang-thai.md` thành `xong-cho-duyet`.

## Tiêu chí ĐẠT của vé đo này

- Có số đo app thật trên PC0575, tách lạnh/ấm, không dùng số của máy khác.
- Parity top-15 giữ nguyên; E1 đủ 15/15.
- Index production không đổi; health `ok`.
- Nếu chưa câu nào về dưới 60s ngoài E2, báo cáo phải chỉ rõ nút thắt còn lại bằng số đo để Muse viết vé code tiếp theo. Không tuyên bố đã đạt tốc độ chỉ vì parity đạt.
